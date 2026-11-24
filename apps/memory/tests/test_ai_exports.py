"""Synthetic ChatGPT export and ingestion tests."""

from datetime import datetime, timezone
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema
from temporal_memory.ingest import ai_exports, triage
from temporal_memory.ingest.ai_exports import chatgpt_records
from temporal_memory.models import Owner


FIXTURE = Path(__file__).with_name("fixtures") / "ai_exports" / "conversations.json"
OWNER = Owner("karim-chatgpt", "Karim", kind="simulated")


@pytest.fixture
def db():
    database, schema = create_test_schema()
    try:
        yield database
    finally:
        drop_test_schema(database, schema)


def _zip_export(path, *, split=False):
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        if split:
            first, second = json.loads(FIXTURE.read_text(encoding="utf-8"))
            archive.writestr("conversations-001.json", json.dumps([second]))
            archive.writestr("conversations-000.json", json.dumps([first]))
        else:
            archive.write(FIXTURE, "conversations.json")
        archive.writestr("user.json", "SYNTHETIC_OTHER_ACCOUNT_DATA")
    return path


@pytest.mark.parametrize("split", [False, True], ids=["plain-member", "numbered-members"])
def test_zip_and_json_produce_the_same_records(tmp_path, monkeypatch, split):
    source = _zip_export(tmp_path / "export.zip", split=split)
    open_member = ZipFile.open

    def only_conversations(archive, member, *args, **kwargs):
        name = member if isinstance(member, str) else member.filename
        assert name in {"conversations.json", "conversations-000.json", "conversations-001.json"}
        return open_member(archive, member, *args, **kwargs)

    monkeypatch.setattr(ZipFile, "open", only_conversations)
    assert chatgpt_records(OWNER, source) == chatgpt_records(OWNER, FIXTURE)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["export.zip"]


def test_records_preserve_the_visible_conversation_by_local_day():
    records = chatgpt_records(OWNER, FIXTURE)
    assert len(records) == len({record.id for record in records}) == 3
    assert {record.source for record in records} == {"ai:chatgpt"}
    assert {record.owner for record in records} == {OWNER.id}
    first = next(record for record in records if record.at.startswith("2026-11-17"))
    second = next(record for record in records if "weekend outline" in record.text)
    other = next(record for record in records if "shorebirds" in record.text)

    assert "Karim's pottery project" in first.text and "glaze a ceramic bowl" in first.text
    assert "[redacted]" in first.text
    assert second.at.startswith("2026-11-18")
    assert "I have two hours on Saturday." in second.text
    assert "Test one glaze on a small tile" in second.text
    assert "Bring a shorebird field guide." in other.text
    assert "Include `sandpipers`." in other.text
    assert "Assistant:" not in first.text
    all_text = "\n".join(record.text for record in records)
    assert "fixture-private-value" not in all_text
    assert "SYNTHETIC_" not in all_text


def test_assistant_excerpt_and_prompts_are_bounded(tmp_path):
    conversation = json.loads(FIXTURE.read_text(encoding="utf-8"))[1]
    conversation["title"] = "Clay " * 90
    conversation["mapping"]["prompt"]["message"]["content"]["parts"] = ["Practice ceramics. " * 120]
    conversation["mapping"]["answer"]["message"]["content"]["parts"] = ["Use a glaze test tile. " * 120]
    source = tmp_path / "conversations.json"
    source.write_text(json.dumps([conversation]), encoding="utf-8")

    [record] = chatgpt_records(OWNER, source)
    lines = record.text.splitlines()
    title = next(line.removeprefix("Conversation: ") for line in lines if line.startswith("Conversation: "))
    prompt = next(line.removeprefix("User: ") for line in lines if line.startswith("User: "))
    summary = next(line.removeprefix("Assistant: ") for line in lines if line.startswith("Assistant: "))
    assert 0 < len(title) < 450
    assert 0 < len(prompt) < 1_000
    assert 0 < len(summary) <= 300


def test_since_uses_message_times_and_the_owner_day():
    after_midnight = chatgpt_records(OWNER, FIXTURE, since="2026-11-18")
    assert len(after_midnight) == 2
    assert all(record.at.startswith("2026-11-18") for record in after_midnight)
    assert all("ceramic bowl" not in record.text for record in after_midnight)

    cutoff = datetime(2026, 11, 18, 11, tzinfo=timezone.utc)
    [record] = chatgpt_records(OWNER.id, FIXTURE, since=cutoff)
    assert "Which shorebirds" in record.text  # inclusive at the exact prompt timestamp


def test_reimport_from_zip_is_a_content_hash_no_op(tmp_path, db):
    PostgresGraphStore(db).create_owner(OWNER)
    initial = chatgpt_records(OWNER, FIXTURE)
    first = triage.ingest_records(db, OWNER.id, initial)
    assert (first["imported"], first["jobs_enqueued"]) == (3, 2)

    replayed = chatgpt_records(OWNER, _zip_export(tmp_path / "export.zip"))
    assert replayed == initial
    replay = triage.ingest_records(db, OWNER.id, replayed)
    assert (replay["imported"], replay["deduped"], replay["jobs_enqueued"]) == (0, 3, 0)


@pytest.mark.parametrize("contents", ["{", "{}", "[null]", '[{"title":"missing mapping","create_time":1}]'])
def test_malformed_export_is_refused(tmp_path, contents):
    source = tmp_path / "conversations.json"
    source.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError):
        chatgpt_records(OWNER, source)


def test_invalid_zip_is_refused(tmp_path):
    source = tmp_path / "export.zip"
    source.write_bytes(b"This is not a ZIP archive.")
    with pytest.raises(ValueError):
        chatgpt_records(OWNER, source)


def test_cyclic_conversation_is_refused(tmp_path):
    conversation = json.loads(FIXTURE.read_text(encoding="utf-8"))[0]
    conversation["mapping"]["root"]["parent"] = "prompt"
    source = tmp_path / "conversations.json"
    source.write_text(json.dumps([conversation]), encoding="utf-8")
    with pytest.raises(ValueError, match="cycle"):
        chatgpt_records(OWNER, source)


@pytest.mark.parametrize("limit", ["_MAX_JSON_BYTES", "_MAX_COMPRESSION_RATIO"])
def test_archive_safety_limits_refuse_before_decompression(tmp_path, monkeypatch, limit):
    source = _zip_export(tmp_path / "export.zip")
    # Exercise the guard with the ordinary fixture and a deliberately small cap.
    monkeypatch.setattr(ai_exports, limit, 1)

    def unexpected_read(*args, **kwargs):
        pytest.fail("An over-limit conversation member was opened")

    monkeypatch.setattr(ZipFile, "open", unexpected_read)
    with pytest.raises(ValueError, match="size|limit|compress"):
        chatgpt_records(OWNER, source)
