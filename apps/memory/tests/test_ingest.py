"""Tests for WP-D ingest parsers, deterministic triage, routing, and `tm` CLI."""
from __future__ import annotations

from email.message import EmailMessage
import json
import mailbox
from pathlib import Path
import subprocess
import sys

import pytest

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema
from temporal_memory.ingest import (
    cli,
    email as email_mod,
    triage,
    whatsapp as wa_mod,
)
from temporal_memory.models import Owner, Record

GOLD_SOURCES = Path(r"G:\Haitham\lab-data\memory-bakeoff\gold\sources")


@pytest.fixture()
def pg_db():
    db, schema = create_test_schema()
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


def _make_email(
    *,
    subject: str,
    sender: str,
    date: str,
    body: str,
    headers: dict[str, str] | None = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = "karim@example.com"
    msg["Date"] = date
    for k, v in (headers or {}).items():
        msg[k] = v
    msg.set_content(body)
    return msg


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


def test_whatsapp_formats_marks_multiline_arabizi_and_deterministic_ids(tmp_path: Path):
    sample = (
        "\u200e[20/10/2026, 08:30:15\u202fAM] Karim: Messages and calls are end-to-end encrypted\n"
        "\u200e[20/10/2026, 08:35:12\u202fAM] Omar Farouk: Salam Kimo\nLine 2 of message\n"
        "20/10/2026, 09:15 - Karim: \u200fتمام يا عمر، 3amel eh?\n"
        "20/10/2026, 09:45 - Omar Farouk: <Media omitted>\n"
        "20/10/2026, 10:00 - You were added\n"
    )
    chat_file = tmp_path / "Best Friends.txt"
    chat_file.write_text(sample, encoding="utf-8")

    parsed = wa_mod.parse_chat(sample, "Best Friends")
    assert parsed.date_order == "dmy"
    assert parsed.system_lines == 2
    assert len(parsed.messages) == 3
    assert parsed.messages[0].text == "Salam Kimo\nLine 2 of message"
    assert "3amel eh" in parsed.messages[1].text
    assert parsed.messages[2].kind == "media"

    # Copy-paste format defaults to mdy
    paste_sample = "[09:45 PM, 10/20/2026] Omar Farouk: Karak tonight?\n"
    paste_parsed = wa_mod.parse_chat(paste_sample, "Paste Chat")
    assert paste_parsed.date_order == "mdy"
    assert paste_parsed.messages[0].ts == "2026-10-20T21:45:00"

    recs = wa_mod.parse_whatsapp_file(chat_file, "karim")
    assert [r.id for r in recs] == [
        "wa-best-friends-0000",
        "wa-best-friends-0001",
        "wa-best-friends-0002",
    ]
    assert all(r.source == "whatsapp:Best Friends" for r in recs)
    assert triage.is_noise_whatsapp(recs[0]) is False
    assert triage.is_noise_whatsapp(recs[2]) is True


def test_email_notes_and_gmail_parsers(tmp_path: Path):
    # Test clean_body stripping quotes/signatures/footers
    raw = (
        "Confirmed for Thursday at 10am.\n"
        "Unsubscribe anytime here\n"
        "-- \n"
        "Sent from my iPhone\n"
        "On Mon, Oct 20, 2026 at 9:00 AM Huda wrote:\n"
        "> Previous message\n"
    )
    assert email_mod.clean_body(raw) == "Confirmed for Thursday at 10am."

    # Test .eml folder + .mbox
    eml_dir = tmp_path / "eml_box"
    eml_dir.mkdir()
    e1 = _make_email(
        subject="DIFC interview",
        sender="Huda Mansour <huda@tawzef.example>",
        date="Tue, 20 Oct 2026 10:00:00 +0400",
        body="See you Thursday 10am at Gate Village.",
    )
    e2 = _make_email(
        subject="Weekly AI digest",
        sender="Digest <news@aiweekly.example>",
        date="Tue, 20 Oct 2026 11:00:00 +0400",
        body="Top stories this week.",
        headers={"List-Unsubscribe": "<mailto:unsub@aiweekly.example>"},
    )
    (eml_dir / "01.eml").write_bytes(e1.as_bytes())
    (eml_dir / "02.eml").write_bytes(e2.as_bytes())

    eml_msgs = email_mod.parse_mailbox(eml_dir)
    assert len(eml_msgs) == 2
    assert triage.is_noise_email(eml_msgs[0]) is False
    assert triage.is_noise_email(eml_msgs[1]) is True

    mbox_path = tmp_path / "mail.mbox"
    box = mailbox.mbox(str(mbox_path))
    box.add(e1)
    box.add(e2)
    box.close()
    mbox_msgs = email_mod.parse_mailbox(mbox_path)
    assert len(mbox_msgs) == 2

    # Test plain dated notes + tagged notes
    notes_file = tmp_path / "plain_notes.md"
    notes_file.write_text(
        "[n001] 2026-10-20 | Started backend prototype\n"
        "2026-10-21 | Long run 12km in Barsha Pond Park\n"
        "## 2026-10-22\n"
        "- Met Nour for Flutter sync\n",
        encoding="utf-8",
    )
    notes = email_mod.parse_notes(notes_file)
    assert len(notes) == 3
    assert [n.ts for n in notes] == [
        "2026-10-20T00:00:00",
        "2026-10-21T00:00:00",
        "2026-10-22T00:00:00",
    ]
    note_recs = email_mod.notes_to_records(notes, "karim")
    assert note_recs[0].id == "n001"
    assert note_recs[1].id == "note-notes-0001"


def test_happy_path_gold_slices_and_cross_source_day_packets(pg_db, tmp_path: Path):
    _seed_owner(pg_db, "karim")

    # 1) Gold WhatsApp slice (first 25 lines of whatsapp_best.txt -> includes 2026-10-20..22 + <Media omitted>)
    wa_slice = tmp_path / "whatsapp_best.txt"
    wa_lines = (GOLD_SOURCES / "whatsapp_best.txt").read_text(encoding="utf-8").splitlines()[:25]
    wa_slice.write_text("\n".join(wa_lines) + "\n", encoding="utf-8")
    wa_raw = wa_mod.parse_whatsapp_file(wa_slice, "karim")
    wa_kept = [r for r in wa_raw if not triage.is_noise_whatsapp(r)]
    assert len(wa_kept) < len(wa_raw)  # drops <Media omitted>

    # 2) Gold Notes slice (first 10 lines -> 2026-10-20..29)
    notes_slice = tmp_path / "notes.md"
    notes_lines = (GOLD_SOURCES / "notes.md").read_text(encoding="utf-8").splitlines()[:10]
    notes_slice.write_text("\n".join(notes_lines) + "\n", encoding="utf-8")
    note_recs = email_mod.notes_to_records(email_mod.parse_notes(notes_slice), "karim")

    # 3) Gold Gmail slice (first 30 lines -> includes OTP g009, promos, alerts, plus real emails g012, g018, g022, g027)
    gmail_slice = tmp_path / "gmail.jsonl"
    gmail_lines = (GOLD_SOURCES / "gmail.jsonl").read_text(encoding="utf-8").splitlines()[:30]
    gmail_slice.write_text("\n".join(gmail_lines) + "\n", encoding="utf-8")
    gmail_items = email_mod.parse_gold_gmail(gmail_slice)
    gmail_kept_items = [(m, row) for m, row in gmail_items if not triage.is_noise_email(m)]
    gmail_dropped = len(gmail_items) - len(gmail_kept_items)
    assert gmail_dropped >= 15
    gmail_kept_ids = {row["id"] for _, row in gmail_kept_items}
    assert {"g012", "g018", "g022", "g027"} <= gmail_kept_ids
    assert "g009" not in gmail_kept_ids  # Security code OTP dropped
    assert "g003" not in gmail_kept_ids  # Promo dropped
    assert "g005" not in gmail_kept_ids  # Newsletter dropped
    gmail_recs = email_mod.gmail_to_records(gmail_kept_items, "karim")

    # 4) In-test temp .mbox + .eml folder
    eml_dir = tmp_path / "temp_eml"
    eml_dir.mkdir()
    (eml_dir / "msg1.eml").write_bytes(
        _make_email(
            subject="Coffee catchup",
            sender="Omar Farouk <omar@example.com>",
            date="Tue, 20 Oct 2026 16:00:00 +0400",
            body="Let's meet at DIFC at 5pm.",
        ).as_bytes()
    )
    (eml_dir / "noise.eml").write_bytes(
        _make_email(
            subject="Notification",
            sender="No Reply <noreply@example.com>",
            date="Tue, 20 Oct 2026 17:00:00 +0400",
            body="Automated alert.",
        ).as_bytes()
    )
    eml_msgs = [m for m in email_mod.parse_mailbox(eml_dir) if not triage.is_noise_email(m)]
    eml_recs = email_mod.email_to_records(eml_msgs, "karim", slug="eml")

    mbox_path = tmp_path / "temp.mbox"
    box = mailbox.mbox(str(mbox_path))
    box.add(
        _make_email(
            subject="Project kickoff",
            sender="Nour El-Din <nour@example.com>",
            date="Wed, 21 Oct 2026 12:00:00 +0400",
            body="Backend repo is live.",
        )
    )
    box.close()
    mbox_msgs = [m for m in email_mod.parse_mailbox(mbox_path) if not triage.is_noise_email(m)]
    mbox_recs = email_mod.email_to_records(mbox_msgs, "karim", slug="mbox")

    all_records = [*wa_kept, *note_recs, *gmail_recs, *eml_recs, *mbox_recs]
    res = triage.ingest_records(pg_db, "karim", all_records, split=True)

    assert res["imported"] == len(all_records)
    assert res["deduped"] == 0
    assert res["blocked_forgotten"] == 0
    assert res["days"] == sorted(res["days"])
    assert res["jobs_enqueued"] == len(res["days"])

    with pg_db.connection() as conn:
        jobs = conn.execute(
            "SELECT kind, priority, pool, day, input_ref FROM jobs WHERE owner = 'karim' ORDER BY created_at ASC, id ASC"
        ).fetchall()

    assert len(jobs) == len(res["days"])
    assert [j["day"] for j in jobs] == res["days"]  # oldest -> newest
    assert all(j["kind"] == "extract.day" and j["priority"] == 1 for j in jobs)
    # 2026-10-20 packet combines WhatsApp + notes + eml
    day_20_refs = set(jobs[0]["input_ref"])
    assert "n001" in day_20_refs
    assert "wa-whatsapp-best-0000" in day_20_refs
    assert "em-eml-0000" in day_20_refs


def test_routing_owner_device_vs_sensitive_internal(pg_db):
    _seed_owner(pg_db, "karim")
    with pg_db.transaction() as conn:
        conn.execute(
            "INSERT INTO tokens (id, token_hash, role, owner, label) VALUES (%s, %s, %s, %s, %s)",
            ("tok-dev-1", "hash-dev-1", "owner-device", "karim", "Karim Laptop"),
        )
    assert triage.owner_has_active_device(pg_db, "karim") is True

    recs = [
        Record(
            id="r-ordinary",
            owner="karim",
            source="notes",
            at="2026-10-20T10:00:00",
            author="owner",
            text="Worked on backend architecture for Raseef.",
        ),
        Record(
            id="r-sensitive",
            owner="karim",
            source="gmail",
            at="2026-10-21T10:00:00",
            author="Mostafa Rizk",
            text="Building wifi\nHi Karim, the building lobby wifi password is BarshaL0bby!2026",
        ),
    ]
    res = triage.ingest_records(pg_db, "karim", recs, split=True)
    assert res["jobs_enqueued"] == 2

    with pg_db.connection() as conn:
        jobs = conn.execute(
            "SELECT day, pool, sensitive_flag FROM jobs WHERE owner = 'karim' ORDER BY day ASC"
        ).fetchall()

    assert jobs[0]["day"] == "2026-10-20"
    assert jobs[0]["pool"] == "owner-device"
    assert jobs[0]["sensitive_flag"] is False

    assert jobs[1]["day"] == "2026-10-21"
    assert jobs[1]["pool"] == "internal"
    assert jobs[1]["sensitive_flag"] is True

    # Revoking device token routes new ordinary days to internal
    with pg_db.transaction() as conn:
        conn.execute("UPDATE tokens SET revoked_at = now() WHERE id = 'tok-dev-1'")
    assert triage.owner_has_active_device(pg_db, "karim") is False

    res2 = triage.ingest_records(
        pg_db,
        "karim",
        [
            Record(
                id="r-ord-2",
                owner="karim",
                source="notes",
                at="2026-10-22T10:00:00",
                author="owner",
                text="Ran 10km along Jumeirah Beach.",
            )
        ],
        split=True,
    )
    assert res2["jobs"][0]["pool"] == "internal"


def test_dedupe_and_forgotten_reimport_blocked(pg_db):
    _seed_owner(pg_db, "o1")
    rec1 = Record(
        id="wab-0001",
        owner="o1",
        source="whatsapp:fam",
        at="2026-10-26T10:00:00",
        author="mom",
        text="Dinner at 8pm tonight",
    )
    rec2 = Record(
        id="n001",
        owner="o1",
        source="notes",
        at="2026-10-26T11:00:00",
        author="owner",
        text="Secret phrase alpha",
    )

    first = triage.ingest_records(pg_db, "o1", [rec1, rec2], split=True)
    assert first["imported"] == 2
    assert first["jobs_enqueued"] == 1

    # Duplicate content_hash re-import is deduped
    dup = triage.ingest_records(
        pg_db,
        "o1",
        [
            Record(
                id="wab-0001-copy",
                owner="o1",
                source="whatsapp:fam",
                at="2026-10-26T10:00:00",
                author="mom",
                text="Dinner at 8pm tonight",
            )
        ],
        split=True,
    )
    assert dup["imported"] == 0
    assert dup["deduped"] == 1
    assert dup["jobs_enqueued"] == 0

    # Mark wab-0001 erased + generation bumped + forget_rules (item, source, text)
    with pg_db.transaction() as conn:
        conn.execute(
            "UPDATE records SET erased_at = now(), generation = generation + 1 WHERE owner = 'o1' AND id = 'wab-0001'"
        )
        conn.execute(
            "INSERT INTO forget_rules (owner, kind, value) VALUES "
            "('o1', 'item', 'wab-0001'), "
            "('o1', 'source', 'whatsapp:blocked'), "
            "('o1', 'text', 'secret phrase')"
        )

    assert triage.is_forgotten("o1", "wab-0001", db=pg_db) is True
    assert triage.is_forgotten("o1", "wa-x-0000", source="whatsapp:blocked", db=pg_db) is True
    assert triage.is_forgotten("o1", "n999", text="Contains secret phrase inside", db=pg_db) is True
    assert triage.is_forgotten("o1", "n888", source="notes", text="Completely ordinary note", db=pg_db) is False

    reimport = triage.ingest_records(
        pg_db,
        "o1",
        [
            rec1,
            Record(
                id="wa-blocked-0000",
                owner="o1",
                source="whatsapp:blocked",
                at="2026-10-27T10:00:00",
                author="friend",
                text="Should be blocked by source rule",
            ),
            Record(
                id="n999",
                owner="o1",
                source="notes",
                at="2026-10-27T11:00:00",
                author="owner",
                text="My secret phrase note",
            ),
        ],
        split=True,
    )
    assert reimport["imported"] == 0
    assert reimport["blocked_forgotten"] == 3
    assert reimport["jobs_enqueued"] == 0


def test_cli_owner_create_and_import_end_to_end(pg_db, tmp_path: Path, capsys):
    rc = cli.main(
        [
            "owner",
            "create",
            "--id",
            "karim-cli",
            "--label",
            "Karim CLI",
            "--kind",
            "simulated",
            "--display-name",
            "Karim Haddad",
            "--alias",
            "Kimo",
            "--alias",
            "كريم",
        ],
        db=pg_db,
    )
    assert rc == 0
    owner_out = json.loads(capsys.readouterr().out)
    assert owner_out["id"] == "karim-cli"
    assert owner_out["self_aliases"] == ["Kimo", "كريم"]

    # Import WhatsApp slice
    wa_slice = tmp_path / "whatsapp_best.txt"
    wa_slice.write_text(
        "\n".join((GOLD_SOURCES / "whatsapp_best.txt").read_text(encoding="utf-8").splitlines()[:20]) + "\n",
        encoding="utf-8",
    )
    assert cli.main(["import", "whatsapp", str(wa_slice), "--owner", "karim-cli"], db=pg_db) == 0
    wa_summary = json.loads(capsys.readouterr().out)
    assert wa_summary["imported"] == 19  # line 14 is <Media omitted>
    assert wa_summary["dropped_triage"] == 1
    assert wa_summary["jobs_enqueued"] == 2

    # Import Gmail slice
    gmail_slice = tmp_path / "gmail.jsonl"
    gmail_slice.write_text(
        "\n".join((GOLD_SOURCES / "gmail.jsonl").read_text(encoding="utf-8").splitlines()[:15]) + "\n",
        encoding="utf-8",
    )
    assert cli.main(["import", "gmail", str(gmail_slice), "--owner", "karim-cli"], db=pg_db) == 0
    gmail_summary = json.loads(capsys.readouterr().out)
    assert gmail_summary["imported"] >= 1
    assert gmail_summary["dropped_triage"] >= 10
    assert gmail_summary["jobs_enqueued"] >= 1

    # Import Notes slice
    notes_slice = tmp_path / "notes.md"
    notes_slice.write_text(
        "\n".join((GOLD_SOURCES / "notes.md").read_text(encoding="utf-8").splitlines()[:6]) + "\n",
        encoding="utf-8",
    )
    assert cli.main(["import", "notes", str(notes_slice), "--owner", "karim-cli"], db=pg_db) == 0
    notes_summary = json.loads(capsys.readouterr().out)
    assert notes_summary["imported"] == 6
    assert notes_summary["jobs_enqueued"] >= 1

    # Verify `python -m temporal_memory.ingest.cli --help` runs cleanly as a subprocess
    proc = subprocess.run(
        [sys.executable, "-m", "temporal_memory.ingest.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "owner" in proc.stdout and "import" in proc.stdout
