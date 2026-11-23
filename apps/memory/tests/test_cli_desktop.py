"""CLI wiring tests for `tm import agent-sessions` and `tm import browser`."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema
from temporal_memory.ingest import cli
from temporal_memory.models import Owner

FIXTURES = Path(__file__).with_name("fixtures") / "desktop"


@pytest.fixture()
def pg_db():
    db, schema = create_test_schema()
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


def _seed_owner(db, owner_id: str = "karim-desktop") -> Owner:
    return PostgresGraphStore(db).create_owner(
        Owner(
            id=owner_id,
            label="Karim Desktop",
            kind="simulated",
            display_name="Karim Haddad",
            timezone="Asia/Dubai",
        )
    )


def _copy_fixture(name: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / name, destination)


def _chrome_timestamp(value: str) -> int:
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    return int((datetime.fromisoformat(value) - epoch).total_seconds()) * 1_000_000


def _make_history(profile: Path, rows: list[tuple[str, str, list[str]]]) -> None:
    profile.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(profile / "History")) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT, title TEXT, visit_count INTEGER);
            CREATE TABLE visits (id INTEGER PRIMARY KEY, url INTEGER, visit_time INTEGER);
            """
        )
        for url_id, (url, title, visits) in enumerate(rows, start=1):
            connection.execute("INSERT INTO urls VALUES (?, ?, ?, 1)", (url_id, url, title))
            connection.executemany(
                "INSERT INTO visits (url, visit_time) VALUES (?, ?)",
                [(url_id, _chrome_timestamp(visit)) for visit in visits],
            )


def test_cli_agent_sessions_happy_path(pg_db, tmp_path: Path, capsys):
    _seed_owner(pg_db)
    projects = tmp_path / "claude" / "projects"
    _copy_fixture("claude-session.jsonl", projects / "project-a" / "session.jsonl")

    rc = cli.main(
        [
            "import",
            "agent-sessions",
            str(projects),
            "--owner",
            "karim-desktop",
            "--tool",
            "claude-code",
            "--no-split",
        ],
        db=pg_db,
    )
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["kind"] == "agent-sessions"
    assert summary["imported"] == 2
    assert summary["jobs_enqueued"] == 0

    with pg_db.connection() as conn:
        rows = conn.execute(
            "SELECT id, source FROM records WHERE owner = %s ORDER BY at ASC",
            ("karim-desktop",),
        ).fetchall()
    assert len(rows) == 2
    assert {r["source"] for r in rows} == {"agent:claude-code"}


def test_cli_browser_happy_path(pg_db, tmp_path: Path, capsys):
    _seed_owner(pg_db)
    profile = tmp_path / "Synthetic Profile"
    _make_history(
        profile,
        [
            (
                "https://research.example/notes",
                "Reading notes",
                ["2026-11-17T10:00:00+00:00", "2026-11-18T10:00:00+00:00"],
            ),
        ],
    )

    rc = cli.main(
        [
            "import",
            "browser",
            str(profile),
            "--owner",
            "karim-desktop",
            "--no-split",
        ],
        db=pg_db,
    )
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["kind"] == "browser"
    assert summary["imported"] == 2
    assert summary["jobs_enqueued"] == 0

    with pg_db.connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM records WHERE owner = %s AND source = 'browser'",
            ("karim-desktop",),
        ).fetchone()["n"]
    assert count == 2


def test_cli_browser_preview_writes_zero_records(pg_db, tmp_path: Path, capsys):
    _seed_owner(pg_db)
    profile = tmp_path / "Synthetic Profile"
    _make_history(
        profile,
        [
            (
                "https://research.example/notes",
                "Reading notes",
                ["2026-11-17T10:00:00+00:00"],
            ),
            (
                "https://docs.example/guide",
                "Guide",
                ["2026-11-17T11:00:00+00:00", "2026-11-17T12:00:00+00:00"],
            ),
        ],
    )

    rc = cli.main(
        [
            "import",
            "browser",
            str(profile),
            "--owner",
            "karim-desktop",
            "--preview",
        ],
        db=pg_db,
    )
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["kind"] == "browser"
    assert summary["preview"] is True
    assert summary["imported"] == 0
    assert summary["jobs_enqueued"] == 0
    assert summary["domain_counts"]["research.example"] == 1
    assert summary["domain_counts"]["docs.example"] == 2

    with pg_db.connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM records WHERE owner = %s",
            ("karim-desktop",),
        ).fetchone()["n"]
    assert count == 0


def test_cli_browser_missing_profile_dir_errors(pg_db, tmp_path: Path, capsys):
    _seed_owner(pg_db)
    missing = tmp_path / "does-not-exist"

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "import",
                "browser",
                str(missing),
                "--owner",
                "karim-desktop",
            ],
            db=pg_db,
        )
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "does not exist" in err.lower() or "missing" in err.lower()
    assert "does-not-exist" in err or str(missing) in err
