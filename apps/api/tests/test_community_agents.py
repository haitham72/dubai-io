from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community.routes import router as community_router
from app.community.agents import router as agents_router


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CM_SOURCE_ALLOWLIST", "example.com,gov.ae,rta.ae")
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(agents_router)
    c = TestClient(app)
    c.get("/api/session")
    yield c, store
    store.db.close()


def other(c):
    o = TestClient(c.app)
    o.get("/api/session")
    return o


def profile(c, handle, interests=None):
    r = c.put("/api/community/profiles/me", json={
        "handle": handle, "display_name": handle, "bio": "x", "area": "JLT",
        "interests": interests if interests is not None else ["food"], "age_band": "18+", "privacy": "public"})
    assert r.status_code == 200, r.text
    return r.json()["profile"]


def post_count(store):
    return store.db.execute("SELECT COUNT(*) FROM cm_posts").fetchone()[0]


# Discovery happy: scored only from own interests + follows, why names feature, log row
def test_discovery_happy_why_and_log(client):
    c, store = client
    profile(c, "alice_dxb", interests=["food"])
    o = other(c); profile(o, "bob_dxb", interests=["cars"])
    pid = o.post("/api/community/posts", json={"text": "Best food in Marina"}).json()["post"]["id"]
    o.post("/api/community/posts", json={"text": "Car meet Friday"})
    # followed author boost even without interest match on second? follow bob
    c.post("/api/community/follows/bob_dxb")
    r = c.get("/api/community/discovery")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items and all(i["why_this"] for i in items)
    food_items = [i for i in items if "food" in i["why_this"]]
    assert food_items and "interest:food" in food_items[0]["features_used"]
    assert r.json()["source"] == "local_cm_profile"
    n = store.db.execute("SELECT COUNT(*) FROM cm_recommendation_events WHERE owner IS NOT NULL").fetchone()[0]
    assert n >= 1
    ev = store.db.execute("SELECT features,why_this FROM cm_recommendation_events").fetchall()
    assert any("food" in (e[1] or "") for e in ev)


def test_discovery_no_interests_honest_empty(client):
    c, store = client
    profile(c, "alice_dxb", interests=[])
    r = c.get("/api/community/discovery")
    assert r.status_code == 200
    j = r.json()
    assert j["items"] == [] and j["empty"] is True and j["reason"]
    assert "B0" in j["reason"]


def test_discovery_excludes_private_and_no_cross_app(client):
    c, store = client
    profile(c, "alice_dxb", interests=["food"])
    o = other(c); profile(o, "bob_dxb")
    gid = o.post("/api/community/groups", json={"name": "Secret Food", "handle": "secret-food2", "visibility": "private"}).json()["group"]["id"]
    items = c.get("/api/community/discovery").json()["items"]
    assert gid not in [i["id"] for i in items]


# Organizer D14
def test_organizer_proposal_zero_notifications_for_others(client):
    c, store = client
    profile(c, "alice_dxb"); o = other(c); profile(o, "bob_dxb")
    gid = c.post("/api/community/groups", json={"name": "Walks", "handle": "walks-b9", "visibility": "public"}).json()["group"]["id"]
    o.post(f"/api/community/groups/{gid}/join")
    before_bob = o.get("/api/community/inbox").json()["unread_count"]
    before_all = store.db.execute("SELECT COUNT(*) FROM cm_notifications").fetchone()[0]
    r = c.post(f"/api/community/groups/{gid}/organizer/propose", json={"title": "Saturday walk", "checklist": ["Water", "Route"]})
    assert r.status_code == 200, r.text
    assert r.json()["proposal"]["title"] == "Saturday walk"
    after_all = store.db.execute("SELECT COUNT(*) FROM cm_notifications").fetchone()[0]
    assert after_all == before_all
    assert o.get("/api/community/inbox").json()["unread_count"] == before_bob
    # visible to members
    assert o.get(f"/api/community/groups/{gid}/organizer/proposals").json()["proposals"]
    # extra outbound fields rejected
    assert c.post(f"/api/community/groups/{gid}/organizer/propose", json={"title": "X", "checklist": [], "invites": ["bob_dxb"]}).status_code == 422


def test_organizer_nonmember_403(client):
    c, _ = client
    profile(c, "alice_dxb"); o = other(c); profile(o, "bob_dxb")
    gid = c.post("/api/community/groups", json={"name": "Walks2", "handle": "walks-b9b", "visibility": "public"}).json()["group"]["id"]
    assert o.post(f"/api/community/groups/{gid}/organizer/propose", json={"title": "X", "checklist": []}).status_code == 403


# Copilot: never hides
def test_copilot_flag_never_hides(client):
    c, store = client
    profile(c, "alice_dxb")
    pid = c.post("/api/community/posts", json={"text": "Flag me please"}).json()["post"]["id"]
    r = c.post("/api/community/copilot/flag", json={"post_id": pid, "label": "spam?"})
    assert r.status_code == 200 and r.json()["post_hidden"] is False
    assert c.get(f"/api/community/posts/{pid}").status_code == 200
    assert store.db.execute("SELECT COUNT(*) FROM cm_copilot_flags WHERE post_id=?", (pid,)).fetchone()[0] == 1
    assert c.post("/api/community/copilot/flag", json={"post_id": "nope", "label": "x"}).status_code == 404
