"""Tests for synthetic YouTube, Gmail JSON, dev_sessions, and temporal_note importers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema, fold_text
from temporal_memory.ingest import (
    import_temporal_note,
    ingest_records,
    parse_dev_sessions,
    parse_entity_aliases_md,
    parse_gmail_json,
    parse_timeline_md,
    parse_youtube_history,
    redact,
    seed_entity_aliases,
)
from temporal_memory.models import Owner


@pytest.fixture()
def pg_db():
    db, schema = create_test_schema()
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


def _seed_owner(db, owner_id: str = "karim") -> Owner:
    return PostgresGraphStore(db).create_owner(
        Owner(
            id=owner_id,
            label="Karim",
            kind="simulated",
            display_name="Karim Haddad",
            self_aliases=["Kimo", "كريم"],
            timezone="Asia/Dubai",
        )
    )


def test_youtube_daily_aggregation_and_rule9_holdback(tmp_path: Path):
    items = [
        {
            "title": "PostgreSQL 17 Indexing Deep Dive",
            "url": "https://youtube.com/watch?v=vid1",
            "channel": "Fireship",
            "watched_at": "2026-10-21T09:15:00Z",
            "source": "watch-history",
        },
        {
            "title": "Blender 4.2 Geometry Nodes Tutorial",
            "url": "https://youtube.com/watch?v=vid2",
            "channel": "Blender Guru",
            "watched_at": "2026-10-21T14:00:00Z",
            "source": "watch-history",
        },
        {
            "title": "Building AI Agents with Python",
            "url": "https://youtube.com/watch?v=vid3",
            "channel": "Fireship",
            "watched_at": "2026-10-21T18:30:00Z",
            "source": "watch-history",
        },
        {
            "title": "RTX 5090 Laptop Benchmark Review",
            "url": "https://youtube.com/watch?v=vid4",
            "channel": "Dave2D",
            "watched_at": "2026-10-20T20:00:00Z",
            "source": "watch-history",
        },
        {
            "title": "Elden Ring Seamless Co-op Gameplay",
            "url": "https://youtube.com/watch?v=vid5",
            "channel": "VaatiVidya",
            "watched_at": "2026-10-20T21:10:00Z",
            "source": "watch-history",
        },
        # Sensitive items across Rule 9 categories — must all be held back
        {
            "title": "Understanding Diabetes Blood Sugar Lab Tests",
            "url": "https://youtube.com/watch?v=sens1",
            "channel": "MedClinic",
            "watched_at": "2026-10-21T22:00:00Z",
            "source": "watch-history",
        },
        {
            "title": "Friday Mosque Khutbah Reflections",
            "url": "https://youtube.com/watch?v=sens2",
            "channel": "FaithChannel",
            "watched_at": "2026-10-22T12:00:00Z",
            "source": "watch-history",
        },
        {
            "title": "Parliament Election Debate Highlights",
            "url": "https://youtube.com/watch?v=sens3",
            "channel": "NewsDesk",
            "watched_at": "2026-10-22T13:00:00Z",
            "source": "watch-history",
        },
        {
            "title": "Never share your OTP verification code",
            "url": "https://youtube.com/watch?v=sens4",
            "channel": "SecTips",
            "watched_at": "2026-10-22T14:00:00Z",
            "source": "watch-history",
        },
        {
            "title": "My brother is dealing with a legal lawsuit",
            "url": "https://youtube.com/watch?v=sens5",
            "channel": "DailyTalk",
            "watched_at": "2026-10-22T15:00:00Z",
            "source": "watch-history",
        },
    ]
    yt_path = tmp_path / "youtube_history.json"
    yt_path.write_text(json.dumps(items), encoding="utf-8")

    records, held_back = parse_youtube_history(yt_path, "karim")

    # 2026-10-22 had only sensitive items -> no record emitted for that day
    assert [r.id for r in records] == ["yt-day-2026-10-20", "yt-day-2026-10-21"]
    assert all(r.source == "youtube:interests" and r.author == "owner" for r in records)
    assert records[0].at == "2026-10-20T00:00:00"
    assert records[1].at == "2026-10-21T00:00:00"

    # Held back counts cover sensitive items
    assert sum(held_back.values()) == 5
    assert held_back.get("health", 0) == 1
    assert held_back.get("religion", 0) == 1
    assert held_back.get("politics", 0) == 1
    assert held_back.get("credential", 0) == 1
    assert held_back.get("family_third_party", 0) == 1

    # Aggregated counts present; zero video titles or watch URLs anywhere
    assert "3 videos watched" in records[1].text
    assert "Fireship=2" in records[1].text
    assert "ai/coding=2" in records[1].text
    assert "design/3d=1" in records[1].text
    assert "tech/hardware=1" in records[0].text
    assert "gaming=1" in records[0].text

    combined_text = "\n".join(r.text for r in records)
    for item in items:
        assert item["title"] not in combined_text
        assert item["url"] not in combined_text
        assert "watch?v=" not in combined_text


def test_gmail_json_triage_thread_and_timestamps(tmp_path: Path):
    rows = [
        {
            "id": "gm-keep-1",
            "thread_id": "thr-difc-99",
            "date": "Tue, 20 Oct 2026 10:15:00 +0000",
            "from": "Huda Mansour <huda@tawzef.example>",
            "subject": "DIFC Interview Confirmation",
            "snippet": "Looking forward to meeting at 10am Thursday &amp; reviewing architecture.",
            "internal_date": "1792491300000",
            "est_tokens": 35,
        },
        {
            "id": "gm-keep-2",
            "thread_id": "thr-raseef-42",
            "date": "",
            "from": "Omar Farouk <omar@raseef.example>",
            "subject": "Raseef Beta Notes",
            "snippet": "Pushed the schema update for day packets.",
            "internal_date": "1792584000000",  # 2026-10-21T12:00:00Z
            "est_tokens": 22,
        },
        {
            "id": "gm-drop-otp",
            "thread_id": "thr-otp-1",
            "date": "Tue, 20 Oct 2026 11:00:00 +0000",
            "from": "CloudAuth <security@cloud.example>",
            "subject": "Security code",
            "snippet": "Your verification code is 491820. Never share this code.",
            "internal_date": "1792494000000",
            "est_tokens": 18,
        },
        {
            "id": "gm-drop-promo",
            "thread_id": "thr-promo-2",
            "date": "Tue, 20 Oct 2026 12:00:00 +0000",
            "from": "Deals <deals@shop.example>",
            "subject": "Flash sale today!",
            "snippet": "Limited-time offer! Unsubscribe anytime.",
            "internal_date": "1792497600000",
            "est_tokens": 20,
        },
        {
            "id": "gm-drop-noreply",
            "thread_id": "thr-news-3",
            "date": "Tue, 20 Oct 2026 13:00:00 +0000",
            "from": "Digest <noreply@digest.example>",
            "subject": "Weekly digest",
            "snippet": "Read the full digest in your browser.",
            "internal_date": "1792501200000",
            "est_tokens": 15,
        },
    ]
    gm_path = tmp_path / "gmail.json"
    gm_path.write_text(json.dumps(rows), encoding="utf-8")

    records, dropped = parse_gmail_json(gm_path, "karim")
    assert dropped == 3
    assert [r.id for r in records] == ["gm-keep-1", "gm-keep-2"]
    assert all(r.source == "gmail" for r in records)
    assert records[0].at == "2026-10-20T10:15:00"
    assert records[0].author == "Huda Mansour"
    assert "[thread:thr-difc-99]" in records[0].text
    assert "DIFC Interview Confirmation" in records[0].text
    assert "& reviewing architecture." in records[0].text

    assert records[1].at == "2026-10-21T12:00:00"
    assert "[thread:thr-raseef-42]" in records[1].text


def test_dev_sessions_secret_and_path_redaction(tmp_path: Path):
    sample_payload = {
        "extracted_at": "2026-10-21T16:00:00Z",
        "claude_sessions": [
            {
                "source": "claude-code",
                "title": "Fix auth using sk-proj-abcdefghijklmnopqrstuvwxyz1234 and C:\\Users\\karim\\repo\\.env.local",
                "project": "raseef-backend",
                "cwd": "C:\\Users\\karim\\Documents\\raseef-backend",
                "git_branch": "feat/day-packets",
                "session_file": "/home/karim/.claude/projects/raseef/sess-99.jsonl",
                "timestamp": "2026-10-20T15:30:00Z",
                "prompts_sample": [
                    "RAW_PROMPT_MUST_NOT_LEAK Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                ],
                "total_prompts": 14,
            }
        ],
        "recent_git_commits": [
            {
                "hash": "abcdef1234567890",
                "author": "Karim Haddad",
                "date": "2026-10-21T09:00:00+00:00",
                "message": "Load config from /Users/karim/dev/app and rotate ghp_1234567890abcdefghij1234",
            }
        ],
    }
    dev_path = tmp_path / "dev_sessions.json"
    dev_path.write_text(json.dumps(sample_payload), encoding="utf-8")

    # Direct redact() checks
    red = redact(
        "OPENAI_API_KEY=sk-1234567890abcdef1234\n"
        "token: secretvalue123 at C:\\dev\\work\\file.py and /var/log/app.log"
    )
    assert "sk-1234567890abcdef1234" not in red
    assert "secretvalue123" not in red
    assert "C:\\dev\\work\\file.py" not in red
    assert "/var/log/app.log" not in red
    assert "[redacted]" in red
    assert "[redacted-path]" in red

    records = parse_dev_sessions(dev_path, "karim")
    assert len(records) == 2
    assert all(r.source == "dev_sessions" for r in records)

    sess_rec, commit_rec = records[0], records[1]
    assert sess_rec.at == "2026-10-20T15:30:00"
    assert "project=raseef-backend" in sess_rec.text
    assert "branch=feat/day-packets" in sess_rec.text
    assert "prompts=14" in sess_rec.text
    assert "sk-proj-" not in sess_rec.text
    assert ".env" not in sess_rec.text
    assert "C:\\Users\\karim" not in sess_rec.text
    assert "sess-99.jsonl" not in sess_rec.text
    assert "RAW_PROMPT_MUST_NOT_LEAK" not in sess_rec.text
    assert "[redacted]" in sess_rec.text
    assert "[redacted-path]" in sess_rec.text

    assert commit_rec.id == "dev-commit-abcdef123456"
    assert commit_rec.at == "2026-10-21T09:00:00"
    assert "ghp_" not in commit_rec.text
    assert "/Users/karim/dev/app" not in commit_rec.text
    assert "[redacted]" in commit_rec.text
    assert "[redacted-path]" in commit_rec.text


def test_temporal_note_parsing_and_postgres_integration(
    pg_db, tmp_path: Path
):
    _seed_owner(pg_db, "karim")

    note_dir = tmp_path / "temporal_note"
    note_dir.mkdir()

    aliases_md = note_dir / "ENTITY_ALIASES.md"
    aliases_md.write_text(
        "# Entity Aliases\n\n"
        "## `Omar`\n"
        "- **Canonical name:** Omar Farouk\n"
        "- **Role:** close friend\n"
        '- **Also referred to as:** "3omar", "عمر"\n\n'
        "## Raseef\n"
        "- **Canonical name:** Raseef Platform\n"
        "- **Role:** software project\n"
        "- **Also referred to as:** Raseef, raseef-app\n\n"
        "## Huda Mansour\n"
        "- **Role:** colleague at Tawzef\n"
        "- **Aliases:** Huda, هدى\n",
        encoding="utf-8",
    )

    timeline_md = note_dir / "timeline.md"
    timeline_md.write_text(
        "# Timeline\n\n"
        "```yaml\n"
        "date: 2026-10-20\n"
        'incident: "Raseef Prototype Kickoff"\n'
        "thread: raseef-launch\n"
        "location: DIFC\n"
        "severity: low\n"
        "emotion: energized\n"
        "entities:\n"
        "  - Omar Farouk\n"
        "  - Raseef Platform\n"
        "links:\n"
        '  - "[[Raseef Platform|Raseef]]"\n'
        "tags:\n"
        "  - engineering\n"
        "  - milestone\n"
        "```\n\n"
        "Met [[Omar Farouk|Omar]] at DIFC to align on the [[Raseef Platform]] beta scope.\n\n"
        "---\n\n"
        "```yaml\n"
        "retrospective: 2026-10-21\n"
        "incident: Secret Forget Me Note\n"
        "thread: private-drop\n"
        "note: should be blocked by forget_rules\n"
        "```\n\n"
        "This secret-forget-marker entry should be blocked by forget rules.\n",
        encoding="utf-8",
    )

    parsed_aliases = parse_entity_aliases_md(aliases_md)
    assert len(parsed_aliases) == 3
    assert parsed_aliases[0]["canonical_name"] == "Omar Farouk"
    assert "3omar" in parsed_aliases[0]["aliases"]
    assert "عمر" in parsed_aliases[0]["aliases"]
    assert "Omar" in parsed_aliases[0]["aliases"]
    assert parsed_aliases[1]["aliases"] == ["Raseef", "raseef-app"]

    parsed_timeline = parse_timeline_md(timeline_md, "karim")
    assert len(parsed_timeline) == 2
    assert parsed_timeline[0].source == "temporal_note"
    assert parsed_timeline[0].at == "2026-10-20T00:00:00"
    assert parsed_timeline[0].author == "owner"
    assert "[[" not in parsed_timeline[0].text
    assert "Raseef Prototype Kickoff" in parsed_timeline[0].text
    assert "DIFC" in parsed_timeline[0].text
    assert "Omar" in parsed_timeline[0].text

    # Add a forget rule before importing so tn-0001 is blocked
    with pg_db.transaction() as conn:
        conn.execute(
            "INSERT INTO forget_rules (owner, kind, value) VALUES (%s, %s, %s)",
            ("karim", "text", "secret-forget-marker"),
        )

    store = PostgresGraphStore(pg_db)
    v_before = store.alias_version("karim")
    summary = import_temporal_note(pg_db, "karim", note_dir, split=True)

    assert summary["aliases_seeded"] >= 8
    assert summary["imported"] == 1
    assert summary["blocked_forgotten"] == 1
    assert summary["days"] == ["2026-10-20"]

    v_after = store.alias_version("karim")
    assert v_after == v_before + 1

    # Verify entities & user_supplied aliases in Postgres
    entities = {e.name: e for e in store.list_entities("karim")}
    assert entities["Omar Farouk"].status == "active"
    assert entities["Omar Farouk"].relation_to_user == "friend"
    assert entities["Omar Farouk"].kind == "person"
    assert entities["Raseef Platform"].kind == "project"
    assert entities["Huda Mansour"].relation_to_user == "colleague"

    with pg_db.connection() as conn:
        alias_rows = conn.execute(
            "SELECT alias, alias_folded, source FROM entity_aliases WHERE owner = 'karim'"
        ).fetchall()
    assert alias_rows
    assert all(r["source"] == "user_supplied" for r in alias_rows)
    folded_set = {r["alias_folded"] for r in alias_rows}
    assert fold_text("عمر") in folded_set
    assert fold_text("3omar") in folded_set

    # Idempotent re-seeding adds 0 aliases and does not bump alias_version
    assert seed_entity_aliases(pg_db, "karim", aliases_md) == 0
    assert store.alias_version("karim") == v_after

    # Cross-source ingestion on 2026-10-20 & 2026-10-21 with content_hash dedupe
    yt_file = tmp_path / "yt.json"
    yt_file.write_text(
        json.dumps([
            {
                "title": "FastAPI Postgres Tips",
                "url": "https://youtube.com/watch?v=abc",
                "channel": "ArjanCodes",
                "watched_at": "2026-10-20T19:00:00Z",
                "source": "watch-history",
            }
        ]),
        encoding="utf-8",
    )
    gm_file = tmp_path / "gm.json"
    gm_file.write_text(
        json.dumps([
            {
                "id": "gm-cross-20",
                "thread_id": "thr-20",
                "date": "Tue, 20 Oct 2026 11:00:00 +0000",
                "from": "Huda Mansour <huda@tawzef.example>",
                "subject": "Followup",
                "snippet": "Confirmed slot for Tuesday.",
                "internal_date": "1792494000000",
                "est_tokens": 12,
            }
        ]),
        encoding="utf-8",
    )
    dev_file = tmp_path / "dev.json"
    dev_file.write_text(
        json.dumps({
            "extracted_at": "2026-10-20T22:00:00Z",
            "claude_sessions": [
                {
                    "source": "claude-code",
                    "title": "Wire importers",
                    "project": "temporal-memory",
                    "cwd": "C:\\Users\\karim\\tm",
                    "git_branch": "main",
                    "session_file": "/home/karim/s.jsonl",
                    "timestamp": "2026-10-20T20:00:00Z",
                    "prompts_sample": ["secret prompt"],
                    "total_prompts": 5,
                }
            ],
            "recent_git_commits": [],
        }),
        encoding="utf-8",
    )

    yt_recs, _ = parse_youtube_history(yt_file, "karim")
    gm_recs, _ = parse_gmail_json(gm_file, "karim")
    dev_recs = parse_dev_sessions(dev_file, "karim")
    cross_recs = [*yt_recs, *gm_recs, *dev_recs]

    res1 = ingest_records(pg_db, "karim", cross_recs, split=True)
    assert res1["imported"] == 3
    assert res1["deduped"] == 0
    assert res1["days"] == ["2026-10-20"]

    # Re-ingesting identical records dedupes via content_hash
    res2 = ingest_records(pg_db, "karim", [*parsed_timeline[:1], *cross_recs], split=True)
    assert res2["imported"] == 0
    assert res2["deduped"] == 4

    with pg_db.connection() as conn:
        rec_sources = {
            r["source"]
            for r in conn.execute("SELECT source FROM records WHERE owner = 'karim'").fetchall()
        }
        job_rows = conn.execute(
            "SELECT day, input_ref FROM jobs WHERE owner = 'karim' ORDER BY created_at ASC"
        ).fetchall()

    assert rec_sources == {"temporal_note", "youtube:interests", "gmail", "dev_sessions"}
    assert len(job_rows) == 2  # one from temporal_note, one from cross_recs (separate day packet batches)
    assert set(job_rows[1]["input_ref"]) == {"yt-day-2026-10-20", "gm-cross-20", "dev-sess-0000"}


def test_tm_cli_export_and_new_import_kinds(pg_db, tmp_path: Path, capsys):
    from temporal_memory.ingest import cli
    from temporal_memory.ingest.export_cli import find_repo_root

    assert cli.main(["owner", "create", "--id", "karim-f", "--label", "Karim F"], db=pg_db) == 0
    _ = capsys.readouterr()

    # 1) tm import youtube (holds back sensitive, imports daily interest summary)
    yt_path = tmp_path / "yt.json"
    yt_path.write_text(
        json.dumps([
            {
                "title": "PostgreSQL 17 Performance",
                "url": "https://youtube.com/watch?v=1",
                "channel": "Fireship",
                "watched_at": "2026-10-20T10:00:00Z",
                "source": "watch-history",
            },
            {
                "title": "Ramadan Prayer Times",
                "url": "https://youtube.com/watch?v=2",
                "channel": "FaithTube",
                "watched_at": "2026-10-20T11:00:00Z",
                "source": "watch-history",
            },
        ]),
        encoding="utf-8",
    )
    assert cli.main(["import", "youtube", str(yt_path), "--owner", "karim-f"], db=pg_db) == 0
    yt_summary = json.loads(capsys.readouterr().out)
    assert yt_summary["kind"] == "youtube"
    assert yt_summary["imported"] == 1
    assert yt_summary["held_back_count"] == 1

    # 2) tm import gmail-json
    gm_path = tmp_path / "gmail.json"
    gm_path.write_text(
        json.dumps([
            {
                "id": "gm-cli-1",
                "thread_id": "thr-cli-1",
                "date": "Tue, 20 Oct 2026 12:00:00 +0000",
                "from": "Omar <omar@example.com>",
                "subject": "Meetup",
                "snippet": "See you at 6pm",
                "internal_date": "1792497600000",
                "est_tokens": 10,
            },
            {
                "id": "gm-cli-2",
                "thread_id": "thr-cli-2",
                "date": "Tue, 20 Oct 2026 13:00:00 +0000",
                "from": "No Reply <noreply@example.com>",
                "subject": "Alert",
                "snippet": "Your verification code is 123456.",
                "internal_date": "1792501200000",
                "est_tokens": 10,
            },
        ]),
        encoding="utf-8",
    )
    assert cli.main(["import", "gmail-json", str(gm_path), "--owner", "karim-f"], db=pg_db) == 0
    gm_summary = json.loads(capsys.readouterr().out)
    assert gm_summary["kind"] == "gmail-json"
    assert gm_summary["imported"] == 1
    assert gm_summary["dropped_triage"] == 1

    # 3) tm import dev-sessions
    dev_path = tmp_path / "dev.json"
    dev_path.write_text(
        json.dumps({
            "extracted_at": "2026-10-20T14:00:00Z",
            "claude_sessions": [
                {
                    "source": "claude-code",
                    "title": "Add export CLI",
                    "project": "dubai-io",
                    "cwd": "C:\\secret\\path",
                    "git_branch": "mem-wpF",
                    "session_file": "/home/u/s.jsonl",
                    "timestamp": "2026-10-20T14:00:00Z",
                    "prompts_sample": ["secret"],
                    "total_prompts": 3,
                }
            ],
            "recent_git_commits": [],
        }),
        encoding="utf-8",
    )
    assert cli.main(["import", "dev-sessions", str(dev_path), "--owner", "karim-f"], db=pg_db) == 0
    dev_summary = json.loads(capsys.readouterr().out)
    assert dev_summary["kind"] == "dev-sessions"
    assert dev_summary["imported"] == 1

    # 4) tm import temporal-note
    tn_dir = tmp_path / "tn"
    tn_dir.mkdir()
    (tn_dir / "ENTITY_ALIASES.md").write_text(
        "## `Nour`\n- **Canonical name:** Nour El-Din\n- **Role:** teammate\n- **Also referred to as:** Nour, نور\n",
        encoding="utf-8",
    )
    (tn_dir / "timeline.md").write_text(
        "```yaml\ndate: 2026-10-20\nincident: Kickoff\n```\n\nMet [[Nour El-Din|Nour]] to review endpoints.\n",
        encoding="utf-8",
    )
    assert cli.main(["import", "temporal-note", str(tn_dir), "--owner", "karim-f"], db=pg_db) == 0
    tn_summary = json.loads(capsys.readouterr().out)
    assert tn_summary["kind"] == "temporal-note"
    assert tn_summary["aliases_seeded"] >= 2
    assert tn_summary["imported"] == 1

    # 5) tm export writes files outside repo and refuses in-repo target
    export_dir = tmp_path / "quest-export-out"
    assert cli.main(["export", "--owner", "karim-f", "--out", str(export_dir)], db=pg_db) == 0
    exp_summary = json.loads(capsys.readouterr().out)
    assert exp_summary["files_written"] >= 5
    assert (export_dir / "USER.md").is_file()
    assert (export_dir / "MEMORIES.md").is_file()

    in_repo_dir = find_repo_root() / "tmp-refuse-export"
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["export", "--owner", "karim-f", "--out", str(in_repo_dir)], db=pg_db)
    assert exc_info.value.code != 0
    assert not in_repo_dir.exists()
