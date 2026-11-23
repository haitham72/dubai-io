"""Desktop import privacy and filesystem regression tests using fictional data."""
from __future__ import annotations

import builtins
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
from functools import wraps
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest

from temporal_memory.ingest.desktop import browser
from temporal_memory.ingest.desktop.agent_sessions import agent_session_records
from temporal_memory.models import Owner

FIXTURES = Path(__file__).with_name("fixtures") / "desktop"
OWNER = Owner("desktop-fixture", "Desktop fixture", kind="simulated", timezone="Asia/Dubai")


def _install_read_guards(monkeypatch, forbidden):
    attempts = []

    def guard(read):
        @wraps(read)
        def wrapped(path, *args, **kwargs):
            if isinstance(path, (str, bytes, os.PathLike)):
                candidate = Path(os.fsdecode(path))
                if forbidden(candidate):
                    attempts.append(candidate)
                    raise AssertionError(f"unexpected filesystem read: {candidate}")
            return read(path, *args, **kwargs)

        return wrapped

    for module, name in (
        (builtins, "open"),
        (io, "open"),
        (os, "open"),
        (shutil, "copy"),
        (shutil, "copy2"),
        (shutil, "copyfile"),
    ):
        monkeypatch.setattr(module, name, guard(getattr(module, name)))
    return attempts


def _copy_fixture(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / source, destination)


def _make_symlink(link, target, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")


def test_agent_sessions_are_deterministic_per_local_day_and_filter_payloads(tmp_path):
    projects = tmp_path / "claude" / "projects"
    sessions = tmp_path / "codex" / "sessions"
    _copy_fixture("claude-session.jsonl", projects / "project-a" / "session.jsonl")
    _copy_fixture(
        "codex-rollout.jsonl",
        sessions / "2026" / "11" / "17" / "rollout-2026-11-17T15-00-00-fixture.jsonl",
    )
    roots = {"claude-code": projects, "codex": sessions}
    records = list(agent_session_records(OWNER, roots))
    assert records == list(agent_session_records(OWNER, dict(reversed(list(roots.items())))))
    assert len(records) == len({record.id for record in records}) == 3

    by_key = {(record.source, record.at[:10]): record for record in records}
    claude_first = by_key["agent:claude-code", "2026-11-17"].text
    claude_second = by_key["agent:claude-code", "2026-11-18"].text
    codex = by_key["agent:codex", "2026-11-17"].text
    assert "reading list about interface design" in claude_first
    assert "Try a short book on interface typography" in claude_first
    assert "Tomorrow I want to prototype the typography" in claude_second
    assert codex.count("I want to learn about coastal birds") == 1
    assert codex.count("Start with a guide to shorebirds") == 1
    payload = json.dumps([asdict(record) for record in records])
    assert "discard" not in payload
    assert "DISCARD_FILE_DUMP_FIXTURE" not in payload
    assert "PRIVATE_HEALTH_FIXTURE" not in payload
    assert "PRIVATE_LEGAL_FIXTURE" not in payload
    assert list(agent_session_records(OWNER, roots, since="2026-11-18")) == [
        by_key["agent:claude-code", "2026-11-18"]
    ]


def test_agent_discovery_never_reads_credentials_or_non_project_depths(tmp_path, monkeypatch):
    projects = tmp_path / "claude" / "projects"
    sessions = tmp_path / "codex" / "sessions"
    _copy_fixture("claude-session.jsonl", projects / "project-a" / "session.jsonl")
    _copy_fixture("codex-rollout.jsonl", sessions / "2026" / "rollout-fixture.jsonl")
    forbidden = {
        projects.parent / ".credentials.json",
        projects / "project-a" / ".credentials.json",
        projects / "project-a" / ".credentials.jsonl",
        projects / "bad-depth.jsonl",
        projects / "project-a" / "session" / "subagents" / "subagent.jsonl",
        sessions.parent / "auth.json",
        sessions / "2026" / "auth.json",
    }
    for path in forbidden:
        _copy_fixture("claude-session.jsonl", path)
    attempts = _install_read_guards(monkeypatch, lambda candidate: candidate in forbidden)

    records = list(agent_session_records(OWNER, {"claude-code": projects, "codex": sessions}))

    assert not attempts
    assert {record.source for record in records} == {"agent:claude-code", "agent:codex"}


def test_agent_secrets_are_redacted_before_truncation(tmp_path):
    projects = tmp_path / "projects"
    session = projects / "fixture" / "session.jsonl"
    session.parent.mkdir(parents=True)
    inside_limit = "a" * 433 + " sk-ZYXWVUTSRQPONMLKJIHGFEDCBA finish"
    crossing_limit = "b" * 390 + " sk-" + "Z" * 180 + " retain these words"
    quoted = r'Test rejected token="first\"QUOTED_SUFFIX_FIXTURE" and keep this context'
    messages = [
        {
            "type": "user",
            "timestamp": "2026-11-17T10:00:00Z",
            "sessionId": "redaction-fixture",
            "message": {"content": prompt},
        }
        for prompt in (inside_limit, crossing_limit, quoted)
    ]
    session.write_text("\n".join(map(json.dumps, messages)), encoding="utf-8")

    [record] = agent_session_records(OWNER, {"claude-code": projects})

    assert "sk-" not in record.text
    assert "ZYXWV" not in record.text
    assert "retain these words" in record.text
    assert "a" * 433 in record.text
    assert "QUOTED_SUFFIX_FIXTURE" not in record.text
    assert "keep this context" in record.text


def test_agent_discovery_never_reads_hardlinked_credential_alias(tmp_path, monkeypatch):
    projects = tmp_path / "claude" / "projects"
    target = projects.parent / ".credentials.json"
    _copy_fixture("claude-session.jsonl", target)
    alias = projects / "project-a" / "innocent.jsonl"
    alias.parent.mkdir(parents=True)
    try:
        os.link(target, alias)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hard links unavailable: {error}")
    attempts = _install_read_guards(monkeypatch, lambda path: path in {alias, target})

    assert list(agent_session_records(OWNER, {"claude-code": projects})) == []
    assert not attempts


@pytest.mark.parametrize("directory", [False, True], ids=["transcript", "project-directory"])
def test_agent_discovery_never_reads_symlink_targets_outside_roots(tmp_path, monkeypatch, directory):
    projects = tmp_path / "projects"
    project = projects / "trusted"
    project.mkdir(parents=True)
    target = tmp_path / "outside" / "escape.jsonl"
    _copy_fixture("claude-session.jsonl", target)
    if directory:
        _make_symlink(projects / "linked-project", target.parent, directory=True)
    else:
        _make_symlink(project / target.name, target)
    attempts = _install_read_guards(
        monkeypatch, lambda candidate: candidate.resolve() == target
    )

    assert list(agent_session_records(OWNER, {"claude-code": projects})) == []
    assert not attempts


def _chrome_timestamp(value):
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    return int((datetime.fromisoformat(value) - epoch).total_seconds()) * 1_000_000


def _make_history(profile, rows):
    profile.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(profile / "History")) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT, title TEXT, visit_count INTEGER);
            CREATE TABLE visits (id INTEGER PRIMARY KEY, url INTEGER, visit_time INTEGER);
            """
        )
        for url_id, (url, title, visits) in enumerate(rows, start=1):
            connection.execute("INSERT INTO urls VALUES (?, ?, ?, 9000)", (url_id, url, title))
            connection.executemany(
                "INSERT INTO visits (url, visit_time) VALUES (?, ?)",
                [(url_id, _chrome_timestamp(visit)) for visit in visits],
            )


DAY_ONE = "2026-11-17T19:59:00+00:00"
DAY_TWO = "2026-11-17T20:01:00+00:00"


@pytest.fixture()
def browser_profile(tmp_path):
    profile = tmp_path / "Synthetic Profile"
    _make_history(
        profile,
        [
            ("https://research.example/RAW_VISIT_PATH_FIXTURE?sort=RAW_QUERY_FIXTURE",
             "RAW_VISIT_TITLE_FIXTURE", [DAY_ONE, DAY_ONE, DAY_TWO]),
            ("https://credentials.example/a?token=RAW_CREDENTIAL_QUERY_FIXTURE",
             "Credential URL", [DAY_ONE]),
            ("https://restricted.example/a", "DENIED_TITLE_FIXTURE", [DAY_ONE]),
            ("https://sub.restricted.example/b", "DENIED_TITLE_FIXTURE", [DAY_ONE]),
            ("https://notrestricted.example/c", "BOUNDARY_TITLE_FIXTURE", [DAY_ONE]),
            ("https://youtube.com/watch?v=SAFE_ID_001",
             "RAW_YOUTUBE_TITLE_FIXTURE - YouTube", [DAY_ONE]),
            ("https://youtube.com/watch?v=HEALTH_0001",
             "My sister has cancer RAW_PRIVATE_WATCH_FIXTURE - YouTube", [DAY_ONE]),
            ("https://agency.example.gov/a", "Government", [DAY_ONE]),
            ("https://service.example.internal/a", "Intranet", [DAY_ONE]),
        ],
    )
    _copy_fixture("Bookmarks", profile / "Bookmarks")
    for name in (
        "Cookies",
        "Login Data",
        "Web Data",
        "Local State",
        "Preferences",
        "Secure Preferences",
        "Network/Cookies",
        "Local Storage/leveldb/000003.log",
    ):
        path = profile / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("CREDENTIAL_STORE_FIXTURE", encoding="utf-8")
    return profile


def test_browser_preview_exposes_counts_only_and_reads_allowlisted_stores(
    browser_profile, monkeypatch
):
    allowed = {"History", "History-wal", "Bookmarks"}
    attempts = _install_read_guards(
        monkeypatch,
        lambda path: path.is_absolute()
        and path.is_relative_to(browser_profile)
        and path.relative_to(browser_profile).as_posix() not in allowed,
    )
    sqlite_opens = []
    connect = sqlite3.connect

    def spy(database, *args, **kwargs):
        sqlite_opens.append((os.fsdecode(database), kwargs.get("uri")))
        return connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", spy)

    def fail_on_record(*args, **kwargs):
        pytest.fail("preview constructed a Record")

    with monkeypatch.context() as preview_patch:
        preview_patch.setattr(browser, "Record", fail_on_record)
        counts = browser.preview(browser_profile)
    records = list(browser.browser_records(OWNER, browser_profile))

    assert not attempts
    assert counts["research.example"] == 3
    assert counts["youtube.com"] == 1
    assert "credentials.example" not in counts
    assert "agency.example.gov" not in counts
    assert "service.example.internal" not in counts
    assert all(isinstance(count, int) for count in counts.values())
    assert records and "RAW_" not in json.dumps(counts)
    assert sqlite_opens
    for database, uri in sqlite_opens:
        assert uri and "mode=ro" in database
        assert "Synthetic%20Profile" not in database and "Synthetic Profile" not in database


def test_browser_daily_aggregation_filters_domain_suffix_and_private_watch(
    browser_profile,
):
    records = list(browser.browser_records(OWNER, browser_profile, deny_domains={"restricted.example"}))
    assert records == list(browser.browser_records(OWNER, browser_profile, deny_domains={"restricted.example"}))
    assert len(records) == len({record.id for record in records}) == 2
    days = {record.at[:10]: record for record in records}
    assert "research.example" in days["2026-11-17"].text
    assert "research.example" in days["2026-11-18"].text
    assert "notrestricted.example" in days["2026-11-17"].text
    assert "YouTube topic Programming: 1" in days["2026-11-17"].text
    assert "YouTube watch interest" not in days["2026-11-17"].text
    assert "credentials.example" not in days["2026-11-17"].text
    assert "sub.restricted.example" not in days["2026-11-17"].text
    assert "restricted.example" not in days["2026-11-17"].text.replace("notrestricted.example", "")
    payload = json.dumps([asdict(record) for record in records])
    assert "https://" not in payload
    assert "RAW_" not in payload
    assert "SAFE_ID_001" not in payload
    assert "HEALTH_0001" not in payload
    assert "987654321" not in payload
    assert "bookmarks.example" not in payload
    assert "DENIED_TITLE_FIXTURE" not in payload
    assert list(browser.browser_records(
        OWNER, browser_profile, since="2026-11-18", deny_domains={"restricted.example"}
    )) == [days["2026-11-18"]]


def test_browser_uses_title_attribution_for_youtube_channels(tmp_path):
    profile = tmp_path / "profile"
    _make_history(profile, [
        ("https://youtube.com/watch?v=SAFE_ID_001&creator=@FakeChannel",
         "An introduction by @StudioExample", [DAY_ONE]),
        ("https://youtube.com/watch?v=SAFE_ID_002&creator=@FakeChannel",
         "An unlabelled lesson", [DAY_ONE]),
        ("https://youtube.com/watch?v=SAFE_ID_003",
         "An introduction by @DailyCancerAdvice", [DAY_ONE]),
    ])

    assert browser.preview(profile) == {"youtube.com": 2}
    [record] = browser.browser_records(OWNER, profile)
    assert record.text.splitlines() == [
        "Browser visits to youtube.com: 2",
        "YouTube channel @studioexample: 1",
        "YouTube watch interest: 1",
    ]


def test_browser_snapshot_includes_committed_wal_visits(tmp_path):
    profile = tmp_path / "profile"
    _make_history(profile, [("https://research.example/a", "Reading", [DAY_ONE])])
    with closing(sqlite3.connect(profile / "History")) as writer:
        assert writer.execute("PRAGMA journal_mode = WAL").fetchone() == ("wal",)
        writer.execute("PRAGMA wal_autocheckpoint = 0")
        with writer:
            writer.execute("INSERT INTO visits (url, visit_time) VALUES (?, ?)",
                           (1, _chrome_timestamp(DAY_TWO)))
        wal = profile / "History-wal"
        assert wal.stat().st_size > 0
        before = wal.read_bytes()

        assert browser.preview(profile) == {"research.example": 2}
        assert wal.read_bytes() == before


def test_browser_never_reads_symlinked_history(tmp_path, monkeypatch):
    external = tmp_path / "outside"
    _make_history(external, [("https://research.example/a", "Private", [DAY_ONE])])
    profile = tmp_path / "profile"
    profile.mkdir()
    target = (external / "History").resolve()
    _make_symlink(profile / "History", target)
    attempts = _install_read_guards(
        monkeypatch, lambda candidate: candidate.resolve() == target
    )

    with pytest.raises(browser.BrowserProfileError):
        browser.preview(profile)

    assert not attempts


@pytest.mark.parametrize("action", ["preview", "records"])
def test_browser_missing_or_locked_history_reports_safe_error(tmp_path, monkeypatch, action):
    profile = tmp_path / "Synthetic Profile"
    profile.mkdir()

    def import_history():
        if action == "preview":
            return browser.preview(profile)
        return list(browser.browser_records(OWNER, profile))

    with pytest.raises(browser.BrowserProfileError) as missing:
        import_history()
    assert "history" in str(missing.value).lower()

    _make_history(profile, [("https://research.example/a", "Private", [DAY_ONE])])
    open_fd = os.open
    attempts = []

    def locked_history(path, *args, **kwargs):
        if Path(path) == profile / "History":
            attempts.append(path)
            raise PermissionError("SYNTHETIC_OS_DETAILS")
        return open_fd(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", locked_history)
    with pytest.raises(browser.BrowserProfileError) as locked:
        import_history()
    assert attempts
    message = str(locked.value).lower()
    assert "history" in message
    assert any(term in message for term in ("locked", "inaccessible", "unavailable"))
    assert "synthetic_os_details" not in message
