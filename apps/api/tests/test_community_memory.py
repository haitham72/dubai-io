"""CM-B8: interest features only, consent default-off, forget, leakage canaries."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import actions, db as db_mod
from app.actions import ActionEngine, ActionStore
from app.community.agents import router as agents_router
from app.community.memory_routes import router as memory_router
from app.community.routes import router as community_router
from app.identity.models import APP_CAPABILITIES, VerifiedPrincipal
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from app.memory_bridge.models import MemoryRecordInput
from tests.fixtures.community.bind import install

CANARY = "RAW_QUEST_SECRET_canary"
SENSITIVE = "my diabetes medication dose"


def _client(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    mem = db_mod.connect(tmp_path / "memory.sqlite3")
    fake = FakeTemporalMemoryClient()
    bridge = MemoryBridge(mem, fake)
    app = FastAPI()
    app.state.memory_bridge = bridge
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(agents_router)
    app.include_router(memory_router)
    install(app, store, tmp_path)
    client = TestClient(app)
    client.get("/api/session")
    return client, bridge, fake


def _me(client):
    saved = client.put("/api/community/profiles/me", json={"handle": "rana_mem", "age_band": "18+", "interests": ["food"], "privacy": "public"})
    assert saved.status_code == 200, saved.text
    return saved.json()["profile"]["owner"]


def _principal(user_id):
    return VerifiedPrincipal(
        user_id=user_id,
        app_id="community",
        capabilities=APP_CAPABILITIES["community"],
        auth_mode="verified_app_session",
        age_band="adult_18_plus",
    )


def test_community_memory_default_off_writes_nothing(tmp_path, monkeypatch):
    client, _bridge, fake = _client(tmp_path, monkeypatch)
    owner = _me(client)
    posted = client.post("/api/community/posts", json={"text": "A public note about the marina"})
    assert posted.status_code == 200, posted.text
    assert fake.records.get(owner, {}) == {}


def test_community_save_join_and_post_write_with_provenance(tmp_path, monkeypatch):
    client, bridge, fake = _client(tmp_path, monkeypatch)
    owner = _me(client)
    principal = _principal(owner)
    bridge.set_source_consent(principal, "community", enabled=True, allow_interest_export=True)
    bridge.set_app_consent(principal, "community", read_enabled=True, write_enabled=True, allow_interest_export_to_community=True)
    other = TestClient(client.app)
    other.get("/api/session")
    other.put("/api/community/profiles/me", json={"handle": "layla_mem", "age_band": "18+", "privacy": "public"})
    post = other.post("/api/community/posts", json={"text": "Layla on the marina walk"})
    pid = post.json()["post"]["id"]
    assert client.post(f"/api/community/posts/{pid}/bookmarks").status_code == 200
    mine = client.post("/api/community/posts", json={"text": "My own public marina note"})
    assert mine.status_code == 200, mine.text
    group = other.post("/api/community/groups", json={"name": "Marina walks", "handle": "marina-walks", "visibility": "public"})
    gid = group.json()["group"]["id"]
    assert client.post(f"/api/community/groups/{gid}/join").status_code == 200
    records = fake.records[owner]
    assert any(key.startswith("cmsave:") for key in records)
    assert any(key.startswith("cmpost:") for key in records)
    assert any(key.startswith("cmjoin:") for key in records)
    own = next(row for key, row in records.items() if key.startswith("cmpost:"))
    assert str(own.source).startswith("community:")


def test_community_discovery_why_chip_and_leakage_canaries(tmp_path, monkeypatch):
    client, bridge, fake = _client(tmp_path, monkeypatch)
    owner = _me(client)
    principal = _principal(owner)
    quest = VerifiedPrincipal(
        user_id=owner,
        app_id="quest",
        capabilities=APP_CAPABILITIES["quest"],
        auth_mode="verified_app_session",
        age_band="adult_18_plus",
    )
    bridge.set_source_consent(quest, "quest", enabled=True, allow_interest_export=True)
    bridge.set_app_consent(quest, "quest", read_enabled=True, write_enabled=True, allow_interest_export_to_community=True)
    bridge.set_app_consent(principal, "community", read_enabled=True, write_enabled=False, allow_interest_export_to_community=True)
    bridge.write_consented(
        quest,
        MemoryRecordInput(
            record_id="qmsg:marina",
            source_kind="quest",
            source_id="quest:thread-marina",
            host_app="quest",
            author_id=owner,
            text=CANARY,
            valid_time="2026-11-23T10:00:00+00:00",
            subject_path="marina",
            explicit_user_confirm=True,
        ),
    )
    try:
        bridge.write_consented(
            principal,
            MemoryRecordInput(
                record_id="qmsg:health",
                source_kind="quest",
                source_id="quest:thread-health",
                host_app="quest",
                author_id=owner,
                text=SENSITIVE,
                valid_time="2026-11-23T10:00:00+00:00",
                subject_path="health",
                explicit_user_confirm=True,
            ),
        )
    except Exception:
        pass
    other = TestClient(client.app)
    other.get("/api/session")
    other.put("/api/community/profiles/me", json={"handle": "omar_mem", "age_band": "18+", "privacy": "public"})
    other.post("/api/community/posts", json={"text": "Saturday marina loop"})
    found = client.get("/api/community/discovery")
    assert found.status_code == 200, found.text
    body = found.json()
    assert body["source"] == "interest_feature"
    assert body["why_chip"] == "Why this?"
    dumped = str(body).lower()
    assert CANARY.lower() not in dumped
    assert "diabetes" not in dumped
    assert "minor" not in dumped
    if body["items"]:
        assert body["items"][0]["why_this"]
        assert "Why this?" == body["items"][0]["why_chip"]
    assert owner not in fake.records or CANARY not in str(body)


def test_community_forget_source_propagates(tmp_path, monkeypatch):
    client, bridge, fake = _client(tmp_path, monkeypatch)
    owner = _me(client)
    principal = _principal(owner)
    bridge.set_source_consent(principal, "community", enabled=True)
    bridge.set_app_consent(principal, "community", read_enabled=True, write_enabled=True)
    posted = client.post("/api/community/posts", json={"text": "Remember this public note"})
    assert posted.status_code == 200
    assert any(key.startswith("cmpost:") for key in fake.records[owner])
    forgotten = client.post("/api/community/memory/forget")
    assert forgotten.status_code == 200, forgotten.text
    record = next(iter(fake.records[owner].values()))
    assert record.erased_at
    still = client.get(f"/api/community/posts/{posted.json()['post']['id']}")
    assert still.status_code == 200
