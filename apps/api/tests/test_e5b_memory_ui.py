"""E5b: Community consent/Forget routes and Messenger Save-to-memory routes. Synthetic accounts, fake memory client."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import db as db_mod
from app.identity import IdentityConfig, IdentityService, IdentityStore, JWTVerifier, create_identity_router
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from app.messenger.routes_chat import router as chat_router
from app.messenger.routes_memory import router as memory_ui_router
from app.messenger.store import ChatStore
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_AUDIENCE, TEST_HS256_SECRET, TEST_ISSUER, default_claims, sign_hs256_jwt,
)
from tests.test_community_memory import _client as community_client, _me


# ------------------------------------------------------------------ Community
def test_community_consent_get_post_roundtrip_and_off_does_not_forget(tmp_path, monkeypatch):
    client, bridge, fake = community_client(tmp_path, monkeypatch)
    owner = _me(client)
    first = client.get("/api/community/memory/consent").json()
    assert first["default_off"] is True and first["read_enabled"] is False
    on = client.post("/api/community/memory/consent", json={"read_enabled": True, "write_enabled": True, "allow_interest_export": False})
    assert on.status_code == 200 and on.json()["write_enabled"] is True and on.json()["as_of"]
    client.post("/api/community/posts", json={"text": "A public note about the marina"})
    assert fake.records[owner], "consented post must be remembered"
    before = dict(fake.records[owner])
    off = client.post("/api/community/memory/consent", json={"read_enabled": False, "write_enabled": False, "allow_interest_export": False})
    assert off.status_code == 200 and off.json()["default_off"] is True
    assert dict(fake.records[owner]) == before, "turning a toggle off must not erase anything"
    assert all(not r.erased_at for r in fake.records[owner].values())
    assert client.get("/api/community/memory/consent").json()["write_enabled"] is False


def test_community_forget_returns_server_counts_and_erases(tmp_path, monkeypatch):
    client, bridge, fake = community_client(tmp_path, monkeypatch)
    owner = _me(client)
    client.post("/api/community/memory/consent", json={"read_enabled": True, "write_enabled": True})
    client.post("/api/community/posts", json={"text": "A public note about the marina"})
    res = client.post("/api/community/memory/forget")
    assert res.status_code == 200
    body = res.json()
    assert body["records_forgotten"] >= 1 and body["as_of"]
    assert all(r.erased_at for r in fake.records[owner].values())


def test_community_consent_failure_paths(tmp_path, monkeypatch):
    client, bridge, _fake = community_client(tmp_path, monkeypatch)
    _me(client)
    bad = client.post("/api/community/memory/consent", json={"read_enabled": True, "surprise": 1})
    assert bad.status_code == 422
    client.app.state.memory_bridge = None
    assert client.get("/api/community/memory/consent").status_code == 503
    assert client.post("/api/community/memory/forget").status_code == 503


# ------------------------------------------------------------------ Messenger
@pytest.fixture()
def mg(tmp_path: Path):
    verifier = JWTVerifier(issuer=TEST_ISSUER, audience=TEST_AUDIENCE, hs256_secret=TEST_HS256_SECRET)
    ident = IdentityStore(tmp_path / "identity.sqlite3")
    svc = IdentityService(ident, verifier, config=IdentityConfig(jwt_issuer=TEST_ISSUER, jwt_audience=TEST_AUDIENCE, jwt_hs256_secret=TEST_HS256_SECRET))
    app = FastAPI()
    app.state.identity_service = svc
    app.state.chat_store = ChatStore(tmp_path / "chat.sqlite3")
    fake = FakeTemporalMemoryClient()
    app.state.memory_bridge = MemoryBridge(db_mod.connect(tmp_path / "memory.sqlite3"), fake)
    app.include_router(create_identity_router())
    app.include_router(chat_router)
    app.include_router(memory_ui_router)
    client = TestClient(app)

    def session(sub):
        tok = sign_hs256_jwt(default_claims(sub=sub))
        body = client.post("/api/identity/sessions", headers={"Authorization": f"Bearer {tok}"}, json={"app_id": "messenger"}).json()
        client.post("/api/identity/age-band", headers={"X-App-Session": body["session_token"]}, json={"age_band": "adult_18_plus"})
        return {"X-App-Session": body["session_token"]}, body["user_id"]

    ha, ua = session("e5b-a")
    hb, ub = session("e5b-b")
    conv = client.post("/api/messenger/conversations", headers=ha, json={"kind": "direct", "member_ids": [ub]}).json()["id"]
    yield client, fake, ha, hb, conv, ua, ub
    ident.close()


def _send(client, h, conv, cid, text):
    return client.post(f"/api/messenger/conversations/{conv}/messages", headers=h, json={"client_msg_id": cid, "text": text}).json()


def _turn_on(client, ha, hb, conv):
    for h in (ha, hb):
        assert client.put("/api/messenger/memory/consent", headers=h, json={"enabled": True}).json()["enabled"] is True
        assert client.put(f"/api/messenger/conversations/{conv}/memory-mode", headers=h, json={"mode": "save"}).json()["mode"] == "save"


def _mem(conv, mid):
    return f"/api/messenger/conversations/{conv}/messages/{mid}/memory"


def test_messages_are_not_memories_until_the_tap_and_preview_lists_fields(mg):
    client, fake, ha, hb, conv, ua, _ub = mg
    msg = _send(client, ha, conv, "m1", "Kiosk panels are due Friday.")
    assert fake.records.get(ua, {}) == {}
    prev = client.get(_mem(conv, msg["id"]) + "-preview", headers=ha).json()
    assert prev["offerable"] is True and prev["can_save_now"] is False  # consent still off
    assert {b["code"] for b in prev["blockers"]} >= {"ai_default_off", "source_off"}
    assert [f["name"] for f in prev["fields"]] == ["Message text", "Written by", "Sent at", "Scope"]
    _turn_on(client, ha, hb, conv)
    prev = client.get(_mem(conv, msg["id"]) + "-preview", headers=ha).json()
    assert prev["can_save_now"] is True and prev["provenance"] == "user_supplied"
    assert fake.records.get(ua, {}) == {}, "previewing must not write"
    no_tap = client.post(_mem(conv, msg["id"]), headers=ha, json={})
    assert no_tap.status_code == 403 and no_tap.json()["detail"]["code"] == "confirm_required"
    assert fake.records.get(ua, {}) == {}
    ok = client.post(_mem(conv, msg["id"]), headers=ha, json={"confirmed": True, "text": "FORGED"})
    assert ok.status_code == 200 and ok.json()["saved"] is True
    rec = fake.records[ua][f"mgmsg:{msg['id']}"]
    assert "FORGED" not in str(rec) and "Friday" in str(rec)


def test_saved_list_comes_from_server_and_forget_removes_it(mg):
    client, fake, ha, hb, conv, ua, _ub = mg
    _turn_on(client, ha, hb, conv)
    msg = _send(client, ha, conv, "m2", "Order the panels on Monday.")
    client.post(_mem(conv, msg["id"]), headers=ha, json={"confirmed": True})
    state = client.get("/api/messenger/memory", headers=ha).json()
    assert state["enabled"] is True and [i["text"] for i in state["items"]] == ["Order the panels on Monday."]
    assert state["items"][0]["provenance"] == "user_supplied"
    assert client.get("/api/messenger/memory", headers=hb).json()["items"] == []
    res = client.post("/api/messenger/memory/forget", headers=ha, json={"record_id": state["items"][0]["record_id"]})
    assert res.status_code == 200 and res.json()["records_forgotten"] == 1
    assert client.get("/api/messenger/memory", headers=ha).json()["items"] == []
    assert client.post("/api/messenger/memory/forget", headers=ha, json={}).status_code == 422


def test_sensitive_message_is_never_offered_or_saved(mg):
    client, fake, ha, hb, conv, ua, _ub = mg
    _turn_on(client, ha, hb, conv)
    msg = _send(client, ha, conv, "m3", "My password is hunter2hunter2 for the portal")
    prev = client.get(_mem(conv, msg["id"]) + "-preview", headers=ha).json()
    assert prev["offerable"] is False and prev["fields"] == []
    res = client.post(_mem(conv, msg["id"]), headers=ha, json={"confirmed": True})
    assert res.status_code == 422 and res.json()["detail"]["held_back"] is True
    assert fake.records.get(ua, {}) == {}


def test_revoking_consent_blocks_saves_but_keeps_items_until_forget(mg):
    client, fake, ha, hb, conv, ua, _ub = mg
    _turn_on(client, ha, hb, conv)
    msg = _send(client, ha, conv, "m4", "Meet the vendor at ten.")
    client.post(_mem(conv, msg["id"]), headers=ha, json={"confirmed": True})
    off = client.put("/api/messenger/memory/consent", headers=ha, json={"enabled": False}).json()
    assert off["enabled"] is False
    state = client.get("/api/messenger/memory", headers=ha).json()
    assert state["enabled"] is False and len(state["items"]) == 1
    msg2 = _send(client, ha, conv, "m5", "Another note about the vendor.")
    again = client.post(_mem(conv, msg2["id"]), headers=ha, json={"confirmed": True})
    assert again.status_code in (403, 409) and again.json()["detail"]["code"]
    assert f"mgmsg:{msg2['id']}" not in fake.records.get(ua, {})
    assert client.put("/api/messenger/memory/consent", headers=ha, json={"enabled": "yes"}).status_code == 422


def test_other_member_off_blocks_save_and_anonymous_is_refused(mg):
    client, fake, ha, hb, conv, ua, _ub = mg
    client.put("/api/messenger/memory/consent", headers=ha, json={"enabled": True})
    client.put(f"/api/messenger/conversations/{conv}/memory-mode", headers=ha, json={"mode": "save"})  # b stays off
    msg = _send(client, ha, conv, "m6", "Plans for the booth layout.")
    res = client.post(_mem(conv, msg["id"]), headers=ha, json={"confirmed": True})
    assert res.status_code == 403 and res.json()["detail"]["code"] == "group_off"
    assert fake.records.get(ua, {}) == {}
    assert client.get("/api/messenger/memory").status_code == 401
