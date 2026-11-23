"""CM-B7 moderation: flags only, human resolves. Spam/sensitive folded here."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community import moderation
from app.community.moderation import router as moderation_router
from app.community.routes import router as community_router
from tests.fixtures.community.bind import install


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(moderation_router)
    install(app, store, tmp_path)
    c = TestClient(app)
    c.get("/api/session")
    yield c, store
    store.db.close()


def other(c):
    o = TestClient(c.app)
    o.get("/api/session")
    return o


def profile(c, handle):
    r = c.put("/api/community/profiles/me", json={"handle": handle, "age_band": "18+", "bio": "x", "area": "JLT"})
    assert r.status_code == 200, r.text
    return r.json()["profile"]


def group_with_members(c):
    """Owner (moderator) + bob author + carol reporter in a private group."""
    profile(c, "owner_a")
    gid = c.post("/api/community/groups", json={"name": "Secret Foodies", "handle": "secret-foodies", "visibility": "private"}).json()["group"]["id"]
    bob, carol = other(c), other(c)
    profile(bob, "bob_b")
    profile(carol, "carol_c")
    for u, h in ((bob, "bob_b"), (carol, "carol_c")):
        assert c.post(f"/api/community/groups/{gid}/invite", json={"handle": h}).status_code == 200
        assert c.post(f"/api/community/groups/{gid}/members/{h}/approve").status_code == 200
    pid = bob.post(f"/api/community/groups/{gid}/posts", json={"text": "Best shawarma in Marina"}).json()["post"]["id"]
    return gid, bob, carol, pid


# ---------------------------------------------------------------- happy path
def test_report_queue_human_keep_remove_author_restore(client):
    c, _ = client
    gid, bob, carol, pid = group_with_members(c)
    # Carol reports Bob's post
    r = carol.post("/api/community/reports", json={"target_type": "post", "target_id": pid, "reason": "spam"})
    assert r.status_code == 200, r.text
    ev1 = r.json()["event"]["id"]
    assert r.json()["report"]["status"] == "pending"
    assert r.json()["event"]["status"] == "flagged" and r.json()["event"]["target_state"] == "flagged"
    # Queue: moderator (owner) and author see it; flagged post still visible
    assert ev1 in [e["id"] for e in c.get("/api/community/moderation/queue").json()["events"]]
    assert ev1 in [e["id"] for e in bob.get("/api/community/moderation/queue").json()["events"]]
    assert bob.get(f"/api/community/posts/{pid}").status_code == 200
    # Human keep
    kept = c.post(f"/api/community/moderation/{ev1}/resolve", json={"decision": "keep"})
    assert kept.status_code == 200 and kept.json()["target_state"] == "kept"
    t = bob.get(f"/api/community/moderation/target/post/{pid}")
    assert t.status_code == 200 and t.json()["target_state"] == "kept"
    # Second report -> human remove (state only; routes filtering is follow-up)
    ev2 = carol.post("/api/community/reports", json={"target_type": "post", "target_id": pid, "reason": "abuse"}).json()["event"]["id"]
    removed = c.post(f"/api/community/moderation/{ev2}/resolve", json={"decision": "remove"})
    assert removed.status_code == 200 and removed.json()["target_state"] == "removed"
    assert bob.get(f"/api/community/moderation/target/post/{pid}").json()["target_state"] == "removed"
    # Author appeal restore
    restored = bob.post(f"/api/community/moderation/{ev2}/resolve", json={"decision": "restore"})
    assert restored.status_code == 200 and restored.json()["target_state"] == "restored"
    assert bob.get(f"/api/community/moderation/target/post/{pid}").json()["target_state"] == "restored"
    assert bob.get(f"/api/community/posts/{pid}").status_code == 200


# ---------------------------------------------------------------- failure paths
def test_model_flag_alone_never_removes_or_hides(client):
    c, store = client
    gid, bob, carol, pid = group_with_members(c)
    with store.lock:
        moderation._setup(store)
        ev = moderation.record_model_flag(store, target_type="post", target_id=pid,
                                          label="harsh", evidence="sentiment harsh=0.9", categories=["harsh"])
        store.db.commit()
    assert ev["source"] == "model" and ev["target_state"] == "flagged"
    t = bob.get(f"/api/community/moderation/target/post/{pid}")
    assert t.json()["target_state"] == "flagged" and t.json()["removed"] is False
    assert bob.get(f"/api/community/posts/{pid}").status_code == 200  # still visible


def test_non_moderator_resolve_403_and_outsider_queue_empty(client):
    c, _ = client
    gid, bob, carol, pid = group_with_members(c)
    ev = carol.post("/api/community/reports", json={"target_type": "post", "target_id": pid, "reason": "spam"}).json()["event"]["id"]
    # Carol is a plain member, Bob is author: neither can keep/remove
    assert carol.post(f"/api/community/moderation/{ev}/resolve", json={"decision": "keep"}).status_code == 403
    assert bob.post(f"/api/community/moderation/{ev}/resolve", json={"decision": "remove"}).status_code == 403
    outsider = other(c)
    profile(outsider, "outsider_d")
    assert ev not in [e["id"] for e in outsider.get("/api/community/moderation/queue").json()["events"]]
    assert outsider.get(f"/api/community/moderation/target/post/{pid}").status_code == 403
    # Still unresolved
    assert bob.get(f"/api/community/moderation/target/post/{pid}").json()["target_state"] == "flagged"


def test_report_missing_target_404_and_resolve_missing_404(client):
    c, _ = client
    profile(c, "alice_dxb")
    assert c.post("/api/community/reports", json={"target_type": "post", "target_id": "nope", "reason": "x"}).status_code == 404
    assert c.post("/api/community/moderation/nope/resolve", json={"decision": "keep"}).status_code == 404
    bad = c.post("/api/community/reports", json={"target_type": "dm", "target_id": "x", "reason": "x"})
    assert bad.status_code == 422  # no messenger target exists


# ---------------------------------------------------------------- sensitive (folded)
def test_sensitive_model_down_fail_closed_blocks():
    def boom(labels):
        raise RuntimeError("model down")
    out = moderation.flag_text("hello neighbours", _screen_fn=boom)
    assert out["blocked"] is True and out["flagged"] is True
    assert "unscreened" in out["categories"] and out["verdict"] is None


def test_sensitive_unavailable_module_fail_closed(monkeypatch):
    monkeypatch.setattr(moderation, "_load_sensitive", lambda: None)
    out = moderation.flag_text("anything at all")
    assert out["blocked"] is True and out["categories"] == ["unavailable"]


def test_sensitive_keyword_flag_and_clean_pass():
    clean = moderation.flag_text("Saturday walk around the lake", _screen_fn=lambda labels: {})
    assert clean["flagged"] is False and clean["categories"] == []
    hit = moderation.flag_text("my password is hunter2", _screen_fn=lambda labels: {})
    assert hit["flagged"] is True and "credential" in hit["categories"]
    # Model-judged category also flags
    judged = moderation.flag_text("clinic visit notes", _screen_fn=lambda labels: {labels[0]: "health"})
    assert judged["flagged"] is True and judged["categories"] == ["health"]


def test_is_minor_fail_closed_no_admission():
    assert moderation.is_minor_age_band("18+") is False
    assert moderation.is_minor_age_band("under-18") is True
    assert moderation.is_minor_age_band("") is True
    assert moderation.is_minor_age_band("unknown-band") is True


# ---------------------------------------------------------------- spam (folded)
def test_duplicate_spam_flagged_not_banned(client):
    c, store = client
    profile(c, "alice_dxb")
    for _ in range(3):
        assert c.post("/api/community/posts", json={"text": "BUY NOW cheap watches"}).status_code == 200
    owner_id = c.get("/api/community/profiles/me").json()["profile"]["owner"]
    with store.lock:
        moderation._setup(store)
        chk = moderation.check_spam(store, owner_id, "BUY NOW cheap watches")
    assert chk["flagged"] is True and chk["banned"] is False and chk["count"] >= 3
    # Not banned: author can still post and profile resolves
    assert c.post("/api/community/posts", json={"text": "A different normal post"}).status_code == 200
    assert c.get("/api/community/profiles/me").status_code == 200
    # Below threshold not flagged
    with store.lock:
        chk2 = moderation.check_spam(store, owner_id, "unique thought once")
    assert chk2["flagged"] is False
