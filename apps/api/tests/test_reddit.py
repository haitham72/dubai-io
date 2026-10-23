"""Reddit-section tests: votes, sort, my posts, mark-read. Offline."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions, communities
from app.actions import ActionEngine, ActionStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(communities.social.settings, "nararouter_api_key", "")
    store = ActionStore(tmp_path / "reddit.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    for router in (actions.router, communities.router):
        app.include_router(router)
    c = TestClient(app)
    c.get("/api/session")
    yield c, store
    store.db.close()


def other(c):
    o = TestClient(c.app)
    o.get("/api/session")
    return o


def _own_post(c):
    c.post("/api/communities/marina-foodies/join")
    return c.post("/api/communities/marina-foodies/posts", json={"text": "my post"}).json()["id"]


def test_vote_toggles_and_scores(client):
    c, _ = client
    pid = _own_post(c)
    base = c.get(f"/api/posts/{pid}").json()["post"]
    assert base["score"] == base["likes"] and base["my_vote"] == 0
    voted = c.post("/api/votes", json={"target_type": "post", "target_id": pid, "value": 1}).json()
    assert voted["score"] == base["likes"] + 1 and voted["my_vote"] == 1
    assert c.get(f"/api/posts/{pid}").json()["post"]["score"] == base["likes"] + 1
    toggled = c.post("/api/votes", json={"target_type": "post", "target_id": pid, "value": 1}).json()
    assert toggled["score"] == base["likes"] and toggled["my_vote"] == 0
    down = c.post("/api/votes", json={"target_type": "post", "target_id": pid, "value": -1}).json()
    assert down["score"] == base["likes"] - 1 and down["my_vote"] == -1


def test_votes_are_owner_scoped_and_validated(client):
    c, _ = client
    pid = _own_post(c)
    assert other(c).post("/api/votes", json={"target_type": "post", "target_id": pid, "value": 1}).status_code == 404
    assert c.post("/api/votes", json={"target_type": "post", "target_id": pid, "value": 5}).status_code == 422
    assert c.post("/api/votes", json={"target_type": "post", "target_id": pid, "value": 0}).status_code == 422
    assert c.post("/api/votes", json={"target_type": "user", "target_id": pid, "value": 1}).status_code == 422
    assert c.post("/api/votes", json={"target_type": "post", "target_id": "missing", "value": 1}).status_code == 404


def test_feed_sort_orders(client):
    c, _ = client
    top = c.get("/api/feed", params={"limit": 50, "sort": "top"}).json()["posts"]
    assert [p["score"] for p in top] == sorted([p["score"] for p in top], reverse=True)
    assert all("my_vote" in p for p in top)
    assert len(c.get("/api/feed", params={"limit": 5, "sort": "hot"}).json()["posts"]) == 5
    assert c.get("/api/feed", params={"sort": "bogus"}).status_code == 422


def test_comment_votes_and_top_sort(client):
    c, _ = client
    pid = _own_post(c)
    first = c.post(f"/api/posts/{pid}/comments", json={"text": "first"}).json()["id"]
    second = c.post(f"/api/posts/{pid}/comments", json={"text": "second"}).json()["id"]
    c.post("/api/votes", json={"target_type": "comment", "target_id": second, "value": 1})
    new = c.get(f"/api/posts/{pid}/comments").json()["comments"]
    assert [m["id"] for m in new] == [first, second]
    top = c.get(f"/api/posts/{pid}/comments", params={"sort": "top"}).json()["comments"]
    assert [m["id"] for m in top] == [second, first] and top[0]["my_vote"] == 1
    assert c.post("/api/votes", json={"target_type": "comment", "target_id": "missing", "value": 1}).status_code == 404


def test_my_posts_lists_only_mine(client):
    c, _ = client
    pid = _own_post(c)
    mine = c.get("/api/me/posts").json()["posts"]
    assert pid in [p["id"] for p in mine] and all(p["mine"] for p in mine)
    assert pid not in [p["id"] for p in other(c).get("/api/me/posts").json()["posts"]]


def test_mark_thread_read_clears_unread(client):
    c, _ = client
    threads = c.get("/api/chats").json()["threads"]
    tid = next(t["id"] for t in threads if t["unread"] > 0)
    assert c.post(f"/api/chats/{tid}/read").json() == {"thread": tid, "unread": 0}
    assert c.post(f"/api/chats/{tid}/read").json() == {"thread": tid, "unread": 0}
    assert c.post("/api/chats/missing/read").status_code == 404


def test_keypad_number_logs_without_contact(client):
    c, _ = client
    logged = c.post("/api/calls", json={"phone": "+971 50 123 4567", "name": "Keypad"}).json()
    assert logged["tel"] == "tel:+971501234567" and logged["logged"]
    [call] = c.get("/api/calls").json()["calls"]
    assert call["contact_id"] is None and call["phone"] == "+971 50 123 4567"
    assert c.post("/api/calls", json={}).status_code == 422
    assert c.post("/api/calls", json={"phone": "123"}).status_code == 422
