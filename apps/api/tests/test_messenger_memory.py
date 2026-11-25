"""MG-B5 memory through the bridge. The fake client stands in until temporal_note is live."""

from pathlib import Path

import pytest

from app import db as db_mod
from app.identity.models import APP_CAPABILITIES, VerifiedPrincipal
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from app.messenger.memory_client import forget_chat, model_may_read, save_approved
from app.messenger.store import ChatStore


def _principal(user_id: str) -> VerifiedPrincipal:
    return VerifiedPrincipal(
        user_id=user_id,
        app_id="messenger",
        capabilities=APP_CAPABILITIES["messenger"],
        auth_mode="verified_app_session",
        age_band="adult_18_plus",
    )


def _ready(tmp_path: Path):
    db = db_mod.connect(tmp_path / "memory.db")
    client = FakeTemporalMemoryClient()
    bridge = MemoryBridge(db, client)
    chat = ChatStore(tmp_path / "chat.sqlite3")
    rana, layla = _principal("usr_rana"), _principal("usr_layla")
    conv = chat.create_conversation(rana.user_id, [layla.user_id], kind="direct")
    for person in (rana, layla):
        bridge.set_source_consent(person, "messenger", enabled=True)
        bridge.set_app_consent(person, "messenger", read_enabled=True, write_enabled=True)
        bridge.set_conversation_consent(person, conv, ai_mode="save")
        chat.set_ai_mode(conv, person.user_id, "save")
    return db, client, bridge, chat, conv, rana


def test_messenger_save_writes_record_with_evidence(tmp_path):
    _db, client, bridge, chat, conv, rana = _ready(tmp_path)
    message = chat.send(conv, rana.user_id, "m1", "Friday deadline for the kiosk panels.")
    receipt = save_approved(chat, bridge, rana, conv, message, confirmed=True)
    assert receipt.ok is True
    assert f"mgmsg:{message['id']}" in client.records[rana.user_id]


def test_messenger_ai_default_off(tmp_path):
    _db, client, bridge, chat, conv, rana = _ready(tmp_path)
    chat.set_ai_mode(conv, rana.user_id, "off")
    message = chat.send(conv, rana.user_id, "m2", "Do not save this.")
    with pytest.raises(PermissionError):
        save_approved(chat, bridge, rana, conv, message, confirmed=True)
    assert client.records.get(rana.user_id, {}) == {}


def test_messenger_group_off_blocks_model(tmp_path):
    _db, client, bridge, chat, conv, rana = _ready(tmp_path)
    chat.set_ai_mode(conv, "usr_layla", "off")
    before = dict(client.records.get(rana.user_id, {}))
    with pytest.raises(PermissionError):
        model_may_read(chat, conv, rana.user_id)
    assert client.records.get(rana.user_id, {}) == before


def test_messenger_forget_keeps_messages(tmp_path):
    _db, client, bridge, chat, conv, rana = _ready(tmp_path)
    message = chat.send(conv, rana.user_id, "m3", "Remember the Friday deadline.")
    save_approved(chat, bridge, rana, conv, message, confirmed=True)
    forget_chat(bridge, rana, conv, key="forget-conv-1")
    assert chat.count_messages(conv) == 1
    assert chat.since(conv, rana.user_id, 0)[0]["body"] == "Remember the Friday deadline."
    assert client.records[rana.user_id][f"mgmsg:{message['id']}"].erased_at is None


def test_messenger_delete_keeps_facts_until_forget(tmp_path):
    _db, client, bridge, chat, conv, rana = _ready(tmp_path)
    message = chat.send(conv, rana.user_id, "m4", "The panel order is Friday.")
    save_approved(chat, bridge, rana, conv, message, confirmed=True)
    chat.delete(conv, rana.user_id, message["id"])
    assert chat.since(conv, rana.user_id, 0)[0]["deleted"] is True
    assert f"mgmsg:{message['id']}" in client.records[rana.user_id]
    assert client.records[rana.user_id][f"mgmsg:{message['id']}"].erased_at is None is None
    forget_chat(bridge, rana, conv, key="forget-conv-2")
    assert client.records[rana.user_id][f"mgmsg:{message['id']}"].erased_at is None
