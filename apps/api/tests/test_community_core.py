from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community.routes import router as community_router
from tests.fixtures.community.bind import install


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(community_router)
    install(app, store, tmp_path)
    c = TestClient(app)
    c.get("/api/session")
    yield c, store
    store.db.close()


def other(c):
    o = TestClient(c.app)
    o.get("/api/session")
    return o


def profile(c, handle, **kw):
    body = {"handle": handle, "display_name": handle.title(), "bio": "Hello", "area": "JLT",
            "interests": ["food"], "age_band": "18+", "privacy": "public"}
    body.update(kw)
    r = c.put("/api/community/profiles/me", json=body)
    assert r.status_code == 200, r.text
    return r.json()["profile"]


def test_adult_profile_ok_and_unique_handle(client):
    c, _ = client
    p = profile(c, "alice_dxb")
    assert p["provenance"] == "user_supplied" and p["age_band"] == "18+"
    assert c.get("/api/community/profiles/me").json()["profile"]["handle"] == "alice_dxb"
    o = other(c)
    profile(o, "bob_dxb")
    r = o.put("/api/community/profiles/me", json={"handle": "alice_dxb", "age_band": "18+"})
    assert r.status_code == 409


def test_under18_profile_refused_403_honest_reason(client):
    c, _ = client
    r = c.put("/api/community/profiles/me", json={"handle": "kid_dxb", "age_band": "under-18"})
    assert r.status_code == 403
    assert "18+" in r.json()["detail"] or "adults-only" in r.json()["detail"].lower()
    no_profile = c.get("/api/community/profiles/me")
    assert no_profile.status_code == 200 and no_profile.json() == {"profile": None}


def test_follow_and_feed_happy_and_empty(client):
    c, _ = client
    profile(c, "alice_dxb")
    assert c.get("/api/community/feed").json()["posts"] == []
    o = other(c)
    profile(o, "bob_dxb")
    post = o.post("/api/community/posts", json={"text": "Bob post about Marina food"})
    assert post.status_code == 200, post.text
    pid = post.json()["post"]["id"]
    # Not followed yet -> not in Alice feed
    assert pid not in [p["id"] for p in c.get("/api/community/feed").json()["posts"]]
    assert c.post("/api/community/follows/bob_dxb").status_code == 200
    feed = c.get("/api/community/feed").json()
    assert pid in [p["id"] for p in feed["posts"]]
    assert c.delete("/api/community/follows/bob_dxb").json()["following"] is False
    assert pid not in [p["id"] for p in c.get("/api/community/feed").json()["posts"]]


def test_follow_failure_self_and_missing(client):
    c, _ = client
    profile(c, "alice_dxb")
    assert c.post("/api/community/follows/alice_dxb").status_code == 400
    assert c.post("/api/community/follows/nobody_here").status_code == 404


def test_post_crud_owner_vs_nonowner_404_and_revision(client):
    c, _ = client
    profile(c, "alice_dxb")
    pid = c.post("/api/community/posts", json={"text": "Original"}).json()["post"]["id"]
    edited = c.put(f"/api/community/posts/{pid}", json={"text": "Edited"})
    assert edited.status_code == 200 and edited.json()["post"]["revision"] == 2
    revs = c.get(f"/api/community/posts/{pid}/revisions").json()["revisions"]
    assert [r["text"] for r in revs] == ["Original", "Edited"]
    o = other(c)
    profile(o, "bob_dxb")
    assert o.put(f"/api/community/posts/{pid}", json={"text": "Hijack"}).status_code == 404
    assert o.delete(f"/api/community/posts/{pid}").status_code == 404
    assert c.get(f"/api/community/posts/{pid}").json()["post"]["text"] == "Edited"
    assert c.delete(f"/api/community/posts/{pid}").status_code == 200
    assert c.get(f"/api/community/posts/{pid}").status_code == 404


def test_threaded_comments_and_cross_post_parent_400(client):
    c, _ = client
    profile(c, "alice_dxb")
    p1 = c.post("/api/community/posts", json={"text": "Post one"}).json()["post"]["id"]
    p2 = c.post("/api/community/posts", json={"text": "Post two"}).json()["post"]["id"]
    parent = c.post(f"/api/community/posts/{p1}/comments", json={"text": "First"})
    assert parent.status_code == 200, parent.text
    cid = parent.json()["comment"]["id"]
    reply = c.post(f"/api/community/posts/{p1}/comments", json={"text": "Reply", "parent_id": cid})
    assert reply.status_code == 200 and reply.json()["comment"]["parent_id"] == cid
    cross = c.post(f"/api/community/posts/{p2}/comments", json={"text": "Cross", "parent_id": cid})
    assert cross.status_code == 400
    missing = c.post(f"/api/community/posts/{p1}/comments", json={"text": "X", "parent_id": "nope"})
    assert missing.status_code == 404


def test_reaction_toggle_and_bookmarks(client):
    c, _ = client
    profile(c, "alice_dxb")
    pid = c.post("/api/community/posts", json={"text": "React to me"}).json()["post"]["id"]
    r1 = c.post(f"/api/community/posts/{pid}/reactions", json={"kind": "like"})
    assert r1.json()["reacted"] is True and r1.json()["count"] == 1
    r2 = c.post(f"/api/community/posts/{pid}/reactions", json={"kind": "like"})
    assert r2.json()["reacted"] is False and r2.json()["count"] == 0
    assert c.post(f"/api/community/posts/{pid}/bookmarks").json()["bookmarked"] is True
    assert pid in [p["id"] for p in c.get("/api/community/bookmarks").json()["bookmarks"]]
    assert c.delete(f"/api/community/posts/{pid}/bookmarks").json()["bookmarked"] is False
    assert c.get("/api/community/bookmarks").json()["bookmarks"] == []


def test_demo_seed_labelled_and_no_fake_status(client):
    c, _ = client
    groups = c.get("/api/community/groups").json()["groups"]
    demo = [g for g in groups if g["id"] == "demo-marina-foodies"]
    assert demo and demo[0]["provenance"] == "demo_fixture"
    posts = c.get("/api/community/groups/demo-marina-foodies/posts").json()["posts"]
    assert posts and all(p["provenance"] == "demo_fixture" for p in posts)
    for p in posts:
        assert p.get("status") not in ("Confirmed", "Verified", "Booked")
