"""CLI wiring tests for `tm import takeout` and `tm import chatgpt` (WP-L).

Synthetic data only. Errors must be clean: SystemExit(2) with `error:` on
stderr and no traceback (the tm contract in cli.main).
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import zipfile

import pytest

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema
from temporal_memory.ingest import cli
from temporal_memory.models import Owner

AI_FIXTURE = Path(__file__).with_name("fixtures") / "ai_exports" / "conversations.json"
DAY = "2026-10-21"
ALL_KINDS = ["whatsapp", "mbox", "eml", "notes", "gmail", "youtube", "gmail-json",
             "dev-sessions", "temporal-note", "agent-sessions", "browser",
             "takeout", "chatgpt"]


@pytest.fixture()
def pg_db():
    db, schema = create_test_schema()
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


def _seed_owner(db, owner_id="karim-cli2"):
    return PostgresGraphStore(db).create_owner(
        Owner(id=owner_id, label="Karim CLI", kind="simulated",
              display_name="Karim Haddad", timezone="Asia/Dubai"))


def _rows(db, owner):
    with db.connection() as conn:
        return conn.execute(
            "SELECT id, source, at, text, content_hash FROM records WHERE owner=%s ORDER BY source, at",
            (owner,)).fetchall()


def _jobs(db, owner):
    with db.connection() as conn:
        return conn.execute(
            "SELECT day, input_ref FROM jobs WHERE owner=%s", (owner,)).fetchall()


def _run_ok(capsys, argv, db):
    assert cli.main(argv, db=db) == 0
    return json.loads(capsys.readouterr().out)


def _assert_clean_error(capsys, exc):
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error:" in captured.err and "Traceback" not in captured.err


def _usec(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1_000_000)


def _takeout_zip(path: Path, *, sensitive=False) -> Path:
    watch = [{"header": "YouTube", "title": "Watched Python FastAPI Tutorial RAW_TITLE_991",
              "titleUrl": "https://www.youtube.com/watch?v=SECRETVID123",
              "subtitles": [{"name": "Fireship"}], "time": f"{DAY}T09:15:33.000Z",
              "products": ["YouTube"]}]
    if sensitive:
        watch.append({"header": "YouTube", "title": "Watched Quran Recitation RAW_SENS_1",
                      "titleUrl": "https://www.youtube.com/watch?v=faith1",
                      "subtitles": [{"name": "Ordinary Channel"}],
                      "time": f"{DAY}T10:00:00.000Z", "products": ["YouTube"]})
    members = {
        "Takeout/YouTube and YouTube Music/history/watch-history.json": watch,
        "Takeout/Chrome/BrowserHistory.json": {"Browser History": [
            {"title": "Python docs", "url": "https://docs.python.org/3/tutorial/",
             "time_usec": _usec(f"{DAY}T13:47:29.000Z")}]},
        "Takeout/My Activity/Gemini Apps/MyActivity.json": [
            {"header": "Gemini Apps",
             "title": "Prompted prayer times for Ramadan" if sensitive
                      else "Prompted Summarise my meeting notes",
             "subtitles": [{"name": "RAW_RESPONSE_993"}], "time": f"{DAY}T08:00:00.000Z",
             "products": ["Gemini Apps"]}],
        "Takeout/Gmail/ignored.json": [{"canary": "IGNORED_CANARY"}],
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in members.items():
            zf.writestr(name, json.dumps(payload).encode())
    return path


# ------------------------------------------------------------------- exports

def test_ingest_package_exports():
    from temporal_memory import ingest

    assert ingest.takeout_records is not None and ingest.chatgpt_records is not None
    assert {"takeout_records", "chatgpt_records", "TakeoutError"} <= set(ingest.__all__)
    assert issubclass(ingest.TakeoutError, ValueError)


# ------------------------------------------------------------------- takeout

def test_takeout_zip_e2e_and_reimport_dedupe(pg_db, tmp_path, capsys):
    _seed_owner(pg_db)
    archive = _takeout_zip(tmp_path / "takeout.zip")

    summary = _run_ok(capsys, ["import", "takeout", str(archive), "--owner", "karim-cli2"], pg_db)
    assert summary["kind"] == "takeout"
    assert summary["imported"] == 3 and summary["jobs_enqueued"] == 1
    rows = _rows(pg_db, "karim-cli2")
    assert {r["source"] for r in rows} == {"youtube:interests", "takeout:chrome", "takeout:gemini-apps"}
    assert all(r["content_hash"] for r in rows)
    jobs = _jobs(pg_db, "karim-cli2")
    assert len(jobs) == 1 and jobs[0]["day"] == DAY and len(jobs[0]["input_ref"]) == 3
    blob = "\n".join(r["text"] for r in rows)
    assert "RAW_TITLE_991" not in blob and "IGNORED_CANARY" not in blob

    again = _run_ok(capsys, ["import", "takeout", str(archive), "--owner", "karim-cli2"], pg_db)
    assert again["imported"] == 0 and again["deduped"] == 3 and again["jobs_enqueued"] == 0
    assert len(_rows(pg_db, "karim-cli2")) == 3 and len(_jobs(pg_db, "karim-cli2")) == 1


def test_takeout_no_split_enqueues_no_jobs(pg_db, tmp_path, capsys):
    _seed_owner(pg_db)
    archive = _takeout_zip(tmp_path / "takeout.zip")
    summary = _run_ok(capsys, ["import", "takeout", str(archive), "--owner", "karim-cli2",
                               "--no-split"], pg_db)
    assert summary["imported"] == 3 and summary["jobs_enqueued"] == 0
    assert _jobs(pg_db, "karim-cli2") == []


def test_takeout_since_and_rule9_holdback(pg_db, tmp_path, capsys):
    _seed_owner(pg_db)
    archive = _takeout_zip(tmp_path / "takeout.zip", sensitive=True)
    summary = _run_ok(capsys, ["import", "takeout", str(archive), "--owner", "karim-cli2",
                               "--since", DAY], pg_db)
    assert summary["imported"] == 2  # chrome + youtube(1 clean video); Gemini held entirely
    blob = "\n".join(r["text"] for r in _rows(pg_db, "karim-cli2"))
    assert "1 videos watched" in blob
    for held in ("RAW_SENS_1", "Quran", "prayer", "Ramadan", "RAW_TITLE_991"):
        assert held not in blob


@pytest.mark.parametrize("kind", ["traversal", "bomb", "badjson", "nonzip", "missing"])
def test_takeout_unsafe_or_bad_clean_exit(pg_db, tmp_path, capsys, kind):
    _seed_owner(pg_db)
    if kind == "traversal":
        target = tmp_path / "evil.zip"
        with zipfile.ZipFile(target, "w") as zf:
            zf.writestr("../../Takeout/Chrome/BrowserHistory.json", b"{}")
    elif kind == "bomb":
        target = tmp_path / "bomb.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Takeout/Chrome/BrowserHistory.json",
                        json.dumps({"Browser History": "A" * 2_000_000}).encode())
    elif kind == "badjson":
        target = tmp_path / "bad.zip"
        with zipfile.ZipFile(target, "w") as zf:
            zf.writestr("Takeout/Chrome/BrowserHistory.json", b"{[ not json")
    elif kind == "nonzip":
        target = tmp_path / "not.zip"
        target.write_bytes(b"hello")
    else:
        target = tmp_path / "missing.zip"
    with pytest.raises(SystemExit) as exc:
        cli.main(["import", "takeout", str(target), "--owner", "karim-cli2"], db=pg_db)
    _assert_clean_error(capsys, exc)
    assert _rows(pg_db, "karim-cli2") == [] and _jobs(pg_db, "karim-cli2") == []


# ------------------------------------------------------------------- chatgpt

def test_chatgpt_json_e2e(pg_db, capsys):
    _seed_owner(pg_db)
    summary = _run_ok(capsys, ["import", "chatgpt", str(AI_FIXTURE), "--owner", "karim-cli2"], pg_db)
    assert summary["kind"] == "chatgpt"
    assert summary["imported"] == 3 and summary["jobs_enqueued"] == 2
    rows = _rows(pg_db, "karim-cli2")
    assert {r["source"] for r in rows} == {"ai:chatgpt"} and all(r["content_hash"] for r in rows)


def test_chatgpt_zip_since_and_reimport_dedupe(pg_db, tmp_path, capsys):
    _seed_owner(pg_db)
    archive = tmp_path / "chatgpt.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(AI_FIXTURE, "conversations.json")
        zf.writestr("user.json", "SYNTHETIC_OTHER_ACCOUNT_DATA")
    argv = ["import", "chatgpt", str(archive), "--owner", "karim-cli2", "--since", "2026-11-18"]
    summary = _run_ok(capsys, argv, pg_db)
    assert summary["imported"] == 2 and summary["jobs_enqueued"] == 1
    rows = _rows(pg_db, "karim-cli2")
    assert all(r["at"].startswith("2026-11-18") for r in rows)
    assert "ceramic bowl" not in "\n".join(r["text"] for r in rows)

    again = _run_ok(capsys, argv, pg_db)
    assert again["imported"] == 0 and again["deduped"] == 2 and again["jobs_enqueued"] == 0
    assert len(_rows(pg_db, "karim-cli2")) == 2


@pytest.mark.parametrize("contents", ["{", "{}", "[null]",
                                      '[{"title":"missing mapping","create_time":1}]'])
def test_chatgpt_malformed_clean_exit(pg_db, tmp_path, capsys, contents):
    _seed_owner(pg_db)
    target = tmp_path / "conversations.json"
    target.write_text(contents, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        cli.main(["import", "chatgpt", str(target), "--owner", "karim-cli2"], db=pg_db)
    _assert_clean_error(capsys, exc)
    assert _rows(pg_db, "karim-cli2") == []


def test_chatgpt_bad_zip_clean_exit(pg_db, tmp_path, capsys):
    _seed_owner(pg_db)
    target = tmp_path / "export.zip"
    target.write_bytes(b"This is not a ZIP archive.")
    with pytest.raises(SystemExit) as exc:
        cli.main(["import", "chatgpt", str(target), "--owner", "karim-cli2"], db=pg_db)
    _assert_clean_error(capsys, exc)


# ------------------------------------------------------------- cross-checks

@pytest.mark.parametrize("kind", ["takeout", "chatgpt"])
def test_unknown_owner_clean_exit(pg_db, tmp_path, capsys, kind):
    archive = _takeout_zip(tmp_path / "takeout.zip")
    target = str(archive if kind == "takeout" else AI_FIXTURE)
    with pytest.raises(SystemExit) as exc:
        cli.main(["import", kind, target, "--owner", "ghost"], db=pg_db)
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "Owner not found" in captured.err and "Traceback" not in captured.err


def test_import_parser_lists_all_kinds_and_export_help(capsys):
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["import", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for kind in ALL_KINDS:
        assert kind in out
    with pytest.raises(SystemExit) as exc2:
        parser.parse_args(["export", "--help"])
    assert exc2.value.code == 0
    out2 = capsys.readouterr().out
    assert "--owner" in out2 and "--out" in out2
    with pytest.raises(SystemExit) as exc3:
        parser.parse_args(["--help"])
    assert exc3.value.code == 0
    assert "import" in capsys.readouterr().out


def test_import_parser_accepts_every_kind():
    parser = cli.build_parser()
    for kind in ALL_KINDS:
        args = parser.parse_args(["import", kind, "some-path", "--owner", "o1"])
        assert args.kind == kind
