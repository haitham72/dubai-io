from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community.routes import router as community_router


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(community_router)
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


def make_private(c):
    r = c.post("/api/community/groups", json={"name": "Secret Foodies", "handle": "secret-foodies", "visibility": "private"})
    assert r.status_code == 200, r.text
    return r.json()["group"]["id"]


def test_private_group_invisible_to_nonmember(client):
    c, _ = client
    profile(c, "owner_a")
    gid = make_private(c)
    assert c.get(f"/api/community/groups/{gid}").status_code == 200
    o = other(c)
    profile(o, "outsider_b")
    assert gid not in [g["id"] for g in o.get("/api/community/groups").json()["groups"]]
    assert o.get(f"/api/community/groups/{gid}").status_code == 404
    assert o.get(f"/api/community/groups/{gid}/posts").status_code == 404
    assert o.get(f"/api/community/groups/{gid}/members").status_code == 404
    assert o.get(f"/api/community/groups/{gid}/search?q=secret").status_code == 404
    assert gid not in [g["id"] for g in o.get("/api/community/search?q=Secret").json()["groups"]]


def test_private_invite_then_moderator_approves_happy(client):
    c, _ = client
    profile(c, "owner_a")
    gid = make_private(c)
    bob = other(c)
    profile(bob, "bob_b")
    inv = c.post(f"/api/community/groups/{gid}/invite", json={"handle": "bob_b"})
    assert inv.status_code == 200 and inv.json()["status"] == "pending"
    # Pending is not active: still invisible
    assert bob.get(f"/api/community/groups/{gid}").status_code == 404
    approved = c.post(f"/api/community/groups/{gid}/members/bob_b/approve")
    assert approved.status_code == 200 and approved.json()["member"]["status"] == "active"
    assert bob.get(f"/api/community/groups/{gid}").status_code == 200
    post = bob.post(f"/api/community/groups/{gid}/posts", json={"text": "Hello secret group"})
    assert post.status_code == 200, post.text
    assert bob.get(f"/api/community/groups/{gid}/posts").json()["posts"]


def test_inviteless_join_private_refused(client):
    c, _ = client
    profile(c, "owner_a")
    gid = make_private(c)
    o = other(c)
    profile(o, "outsider_b")
    assert o.post(f"/api/community/groups/{gid}/join").status_code in (403, 404)


def test_public_group_join_and_post(client):
    c, _ = client
    profile(c, "owner_a")
    gid = c.post("/api/community/groups", json={"name": "Open Walks", "handle": "open-walks", "visibility": "public"}).json()["group"]["id"]
    o = other(c)
    profile(o, "walker_b")
    assert o.post(f"/api/community/groups/{gid}/join").status_code == 200
    assert o.post(f"/api/community/groups/{gid}/posts", json={"text": "Walk Saturday"}).status_code == 200


def test_moderator_pin_and_nonmod_403_and_log_reversal(client):
    c, _ = client
    profile(c, "owner_a")
    gid = make_private(c)
    bob = other(c)
    profile(bob, "bob_b")
    carol = other(c)
    profile(carol, "carol_c")
    for u in (bob, carol):
        c.post(f"/api/community/groups/{gid}/invite", json={"handle": u.get("/api/community/profiles/me").json()["profile"]["handle"]})
        c.post(f"/api/community/groups/{gid}/members/{u.get('/api/community/profiles/me').json()['profile']['handle']}/approve")
    # Owner names Bob moderator
    named = c.post(f"/api/community/groups/{gid}/moderators", json={"handle": "bob_b"})
    assert named.status_code == 200, named.text
    post = bob.post(f"/api/community/groups/{gid}/posts", json={"text": "Pin me"})
    pid = post.json()["post"]["id"]
    # Carol is a plain member -> cannot pin
    assert carol.post(f"/api/community/groups/{gid}/pin", json={"post_id": pid}).status_code == 403
    # Non-owner cannot name moderators
    assert bob.post(f"/api/community/groups/{gid}/moderators", json={"handle": "carol_c"}).status_code == 403
    pinned = bob.post(f"/api/community/groups/{gid}/pin", json={"post_id": pid})
    assert pinned.status_code == 200, pinned.text
    log_id = pinned.json()["log_id"]
    assert c.get(f"/api/community/groups/{gid}/posts").json()["posts"][0]["pinned"] is True
    logs = c.get(f"/api/community/groups/{gid}/moderation-log").json()["logs"]
    assert any(x["id"] == log_id and x["action"] == "pin" for x in logs)
    # Moderator cannot undo (owner-reversible only); owner can
    assert bob.post(f"/api/community/groups/{gid}/moderation/{log_id}/undo").status_code == 403
    undone = c.post(f"/api/community/groups/{gid}/moderation/{log_id}/undo")
    assert undone.status_code == 200 and undone.json()["undone"] is True
    assert c.get(f"/api/community/groups/{gid}/posts").json()["posts"][0]["pinned"] is False
    assert c.post(f"/api/community/groups/{gid}/moderation/{log_id}/undo").status_code == 409


def test_remove_member_logged_and_owner_reversible(client):
    c, _ = client
    profile(c, "owner_a")
    gid = make_private(c)
    bob = other(c)
    profile(bob, "bob_b")
    c.post(f"/api/community/groups/{gid}/invite", json={"handle": "bob_b"})
    c.post(f"/api/community/groups/{gid}/members/bob_b/approve")
    removed = c.post(f"/api/community/groups/{gid}/members/bob_b/remove")
    assert removed.status_code == 200
    assert bob.get(f"/api/community/groups/{gid}").status_code == 404
    undone = c.post(f"/api/community/groups/{gid}/moderation/{removed.json()['log_id']}/undo")
    assert undone.status_code == 200
    assert bob.get(f"/api/community/groups/{gid}").status_code == 200
