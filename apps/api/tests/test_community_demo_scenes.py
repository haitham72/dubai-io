"""CM-B11: scenes A–D, three clean runs, restart continuity, two-user isolation."""

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
SOURCE = {
    "title": "RTA service page",
    "url": "https://www.rta.ae/service",
    "publisher": "RTA",
    "as_of": "2026-11-23",
}


def _open(root, monkeypatch, *, bridge=None, fake=None, session=True):
    monkeypatch.setenv("CM_SOURCE_ALLOWLIST", "example.com,gov.ae,rta.ae")
    store = ActionStore(root / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    if bridge is None:
        mem = db_mod.connect(root / "memory.sqlite3")
        fake = FakeTemporalMemoryClient()
        bridge = MemoryBridge(mem, fake)
    app = FastAPI()
    app.state.memory_bridge = bridge
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(agents_router)
    app.include_router(memory_router)
    install(app, store, root)
    client = TestClient(app)
    if session:
        client.get("/api/session")
    return client, bridge, fake, store


def _profile(client, handle, *, interests=None, privacy="public"):
    saved = client.put("/api/community/profiles/me", json={
        "handle": handle,
        "age_band": "18+",
        "interests": ["marina"] if interests is None else interests,
        "privacy": privacy,
    })
    assert saved.status_code == 200, saved.text
    return saved.json()["profile"]


def _principal(user_id, app_id):
    return VerifiedPrincipal(
        user_id=user_id,
        app_id=app_id,
        capabilities=APP_CAPABILITIES[app_id],
        auth_mode="verified_app_session",
        age_band="adult_18_plus",
    )


def _post_ids(store):
    return {row[0] for row in store.db.execute("SELECT id FROM cm_posts").fetchall()}


def _run_scenes(root, monkeypatch, run_n):
    client, bridge, fake, store = _open(root, monkeypatch)
    me = _profile(client, "rana_b11", interests=["marina"], privacy="public")
    owner = me["owner"]
    seeded = store.db.execute("SELECT provenance FROM cm_posts WHERE owner='demo'").fetchall()
    assert seeded and {row[0] for row in seeded} == {"demo_fixture"}

    other = TestClient(client.app)
    other.get("/api/session")
    _profile(other, "layla_b11", interests=["food"], privacy="public")
    group = other.post("/api/community/groups", json={
        "name": "Marina neighbours",
        "handle": "marina-neighbours",
        "description": "Public group for the marina",
        "visibility": "public",
    })
    assert group.status_code == 200, group.text
    group_id = group.json()["group"]["id"]
    posted = other.post("/api/community/posts", json={"text": "A public post about the marina for newcomers."})
    assert posted.status_code == 200, posted.text
    public_post_id = posted.json()["post"]["id"]

    found = client.get("/api/community/discovery")
    assert found.status_code == 200, found.text
    scene_a = found.json()
    assert scene_a["source"] == "local_cm_profile", scene_a
    groups = [item for item in scene_a["items"] if item.get("kind") == "group" or item.get("type") == "group"]
    marina_groups = [item for item in groups if "marina" in (item.get("why_this") or "").lower()]
    assert marina_groups, scene_a
    assert marina_groups[0]["why_this"]

    joined = client.post(f"/api/community/groups/{group_id}/join")
    assert joined.status_code == 200, joined.text
    commented = client.post(f"/api/community/posts/{public_post_id}/comments", json={"text": "Joining the marina conversation."})
    assert commented.status_code == 200, commented.text
    comment_id = commented.json()["comment"]["id"]
    assert comment_id

    quest = _principal(owner, "quest")
    community = _principal(owner, "community")
    bridge.set_source_consent(quest, "quest", enabled=True, allow_interest_export=True)
    bridge.set_app_consent(
        quest, "quest",
        read_enabled=True, write_enabled=True, allow_interest_export_to_community=True,
    )
    bridge.set_app_consent(
        community, "community",
        read_enabled=True, write_enabled=False, allow_interest_export_to_community=True,
    )
    bridge.write_consented(
        quest,
        MemoryRecordInput(
            record_id=f"qmsg:marina:run{run_n}",
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
    consent = client.post("/api/community/memory/consent", json={
        "read_enabled": True, "write_enabled": True, "allow_interest_export": True,
    })
    assert consent.status_code == 200, consent.text
    crossed = client.get("/api/community/discovery")
    assert crossed.status_code == 200, crossed.text
    scene_b = crossed.json()
    assert scene_b["source"] == "local_cm_profile+interest_feature", scene_b
    assert scene_b["why_chip"] == "Why this?", scene_b
    dumped = str(scene_b)
    assert CANARY not in dumped
    assert "diabetes" not in dumped.lower()
    matched = [item for item in scene_b["items"] if item.get("id") == public_post_id or item.get("post_id") == public_post_id]
    assert matched, scene_b
    assert all("with consent" in (item.get("why_this") or "") for item in matched)
    assert all("You picked marina when you joined" in (item.get("why_this") or "") for item in matched)

    draft_body = {
        "question": "How can I find the public RTA service page?",
        "text": "Start from the published RTA service page.",
        "sources": [SOURCE],
        "group_id": group_id,
    }
    drafted = client.post("/api/community/answers/draft", json=draft_body)
    assert drafted.status_code == 200, drafted.text
    draft = drafted.json()["draft"]
    draft_id = draft["id"]
    old_revision = draft["revision"]
    old_hash = draft["snapshot_hash"]
    edited_text = "Edited: use the published RTA service page and check the date."
    edited = client.put(f"/api/community/answers/{draft_id}", json={"text": edited_text})
    assert edited.status_code == 200, edited.text
    current = edited.json()["draft"]
    before = _post_ids(store)
    stale = client.post(f"/api/community/answers/{draft_id}/approve", json={
        "revision": old_revision, "snapshot_hash": old_hash,
    })
    assert stale.status_code == 409, stale.text
    assert _post_ids(store) == before
    still_draft = client.get(f"/api/community/answers/{draft_id}")
    assert still_draft.status_code == 200, still_draft.text
    assert still_draft.json()["draft"]["status"] != "published"
    approved = client.post(f"/api/community/answers/{draft_id}/approve", json={
        "revision": current["revision"], "snapshot_hash": current["snapshot_hash"],
    })
    assert approved.status_code == 200, approved.text
    post_id = approved.json()["post_id"]
    assert post_id
    published = client.get(f"/api/community/posts/{post_id}")
    assert published.status_code == 200, published.text
    assert published.json()["post"]["text"] == edited_text

    saved = client.post(f"/api/community/posts/{public_post_id}/bookmarks")
    assert saved.status_code == 200, saved.text
    records = fake.records[owner]
    save_key = next(key for key in records if key.startswith("cmsave:"))
    saved_record = records[save_key]
    assert saved_record.source
    forgotten = client.post("/api/community/memory/forget")
    assert forgotten.status_code == 200, forgotten.text
    assert forgotten.json()["forgotten"] is True
    assert saved_record.erased_at
    still_public = client.get(f"/api/community/posts/{public_post_id}")
    assert still_public.status_code == 200, still_public.text

    token = client.cookies.get(actions.COOKIE)
    assert token
    store.db.close()
    client, _bridge, _fake, store = _open(root, monkeypatch, bridge=bridge, fake=fake, session=False)
    client.cookies.set(actions.COOKIE, token)
    comments = client.get(f"/api/community/posts/{public_post_id}/comments")
    assert comments.status_code == 200, comments.text
    assert comment_id in [row["id"] for row in comments.json()["comments"]]
    members = client.get(f"/api/community/groups/{group_id}/members")
    assert members.status_code == 200, members.text
    assert any(row["owner"] == owner and row["status"] == "active" for row in members.json()["members"])

    private = client.put("/api/community/profiles/me", json={
        "handle": "rana_b11", "age_band": "18+", "interests": ["marina"], "privacy": "private",
    })
    assert private.status_code == 200, private.text
    stranger = TestClient(client.app)
    stranger.get("/api/session")
    _profile(stranger, "omar_b11", interests=["food"], privacy="public")
    hidden_profile = stranger.get("/api/community/profiles/rana_b11")
    assert hidden_profile.status_code == 404, hidden_profile.text
    hidden_draft = stranger.get(f"/api/community/answers/{draft_id}")
    assert hidden_draft.status_code == 404, hidden_draft.text
    marks = stranger.get("/api/community/bookmarks")
    assert marks.status_code == 200, marks.text
    payload = marks.json()
    assert isinstance(payload["bookmarks"], list) and isinstance(payload["posts"], list)
    assert public_post_id not in {row["id"] for row in payload["bookmarks"]}
    store.db.close()


def test_community_demo_scenes_three_clean_runs(tmp_path, monkeypatch):
    for n in range(3):
        _run_scenes(tmp_path / f"run{n}", monkeypatch, n)


def test_second_user_cannot_approve_draft_without_a_flag(tmp_path, monkeypatch):
    client, _bridge, _fake, store = _open(tmp_path, monkeypatch)
    _profile(client, "rana_b11", interests=["marina"], privacy="public")
    drafted = client.post("/api/community/answers/draft", json={
        "question": "How can I find the public RTA service page?",
        "text": "Start from the published RTA service page.",
        "sources": [SOURCE],
    })
    assert drafted.status_code == 200, drafted.text
    draft = drafted.json()["draft"]
    other = TestClient(client.app)
    other.get("/api/session")
    _profile(other, "layla_b11", interests=["food"], privacy="public")
    denied = other.post(f"/api/community/answers/{draft['id']}/approve", json={
        "revision": draft["revision"], "snapshot_hash": draft["snapshot_hash"],
    })
    assert denied.status_code == 404, denied.text
    store.db.close()


def test_discovery_bridge_error_keeps_local_results(tmp_path, monkeypatch):
    client, bridge, _fake, store = _open(tmp_path, monkeypatch)
    _profile(client, "rana_b11", interests=["marina"], privacy="public")
    other = TestClient(client.app)
    other.get("/api/session")
    _profile(other, "layla_b11", interests=["food"], privacy="public")
    assert other.post("/api/community/groups", json={
        "name": "Marina neighbours", "handle": "marina-neighbours",
        "description": "Public group for the marina", "visibility": "public",
    }).status_code == 200

    def explode(*_args, **_kwargs):
        raise RuntimeError("bridge down RAW_QUEST_SECRET_canary")

    monkeypatch.setattr(bridge, "read_community_interest_features", explode)
    found = client.get("/api/community/discovery")
    assert found.status_code == 200, found.text
    body = found.json()
    assert body["source"] == "local_cm_profile", body
    assert any("marina" in (item.get("why_this") or "").lower() for item in body["items"])
    assert "RAW_QUEST_SECRET_canary" not in str(body)
    assert "bridge down" not in str(body)
    store.db.close()
