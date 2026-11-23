from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community.routes import router as community_router
from app.community import server as community_server


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
    r = c.put("/api/community/profiles/me", json={"handle": handle, "age_band": "18+"})
    assert r.status_code == 200, r.text


def test_reply_notifies_post_owner_and_mark_read(client):
    c, _ = client
    profile(c, "alice_n")
    pid = c.post("/api/community/posts", json={"text": "Alice post"}).json()["post"]["id"]
    bob = other(c)
    profile(bob, "bob_n")
    assert bob.post(f"/api/community/posts/{pid}/comments", json={"text": "Nice post"}).status_code == 200
    inbox = c.get("/api/community/inbox").json()
    assert inbox["unread_count"] == 1
    note = inbox["notifications"][0]
    assert note["kind"] == "reply" and note["post_id"] == pid
    # Bob gets no self-notification
    assert bob.get("/api/community/inbox").json()["unread_count"] == 0
    assert c.post(f"/api/community/notifications/{note['id']}/read").status_code == 200
    assert c.get("/api/community/inbox").json()["unread_count"] == 0
    assert c.get("/api/community/inbox").json()["notifications"][0]["read"] is True


def test_mention_notifies_mentioned_user(client):
    c, _ = client
    profile(c, "alice_n")
    bob = other(c)
    profile(bob, "bob_n")
    bob.post("/api/community/posts", json={"text": "Hey @alice_n check this"})
    kinds = [n["kind"] for n in c.get("/api/community/notifications").json()["notifications"]]
    assert "mention" in kinds


def test_notification_dedupe_key_unique(client):
    c, store = client
    profile(c, "alice_n")
    bob = other(c)
    profile(bob, "bob_n")
    pid = c.post("/api/community/posts", json={"text": "Dedupe target"}).json()["post"]["id"]
    bob.post(f"/api/community/posts/{pid}/comments", json={"text": "one reply"})
    with store.lock:
        rows = store.db.execute("SELECT dedupe_key, COUNT(*) FROM cm_notifications GROUP BY dedupe_key HAVING COUNT(*)>1").fetchall()
        assert rows == []
        # Direct duplicate insert with same dedupe key is ignored by the helper path
        from app.community.store import notify
        before = store.db.execute("SELECT COUNT(*) FROM cm_notifications").fetchone()[0]
        key = store.db.execute("SELECT dedupe_key FROM cm_notifications LIMIT 1").fetchone()[0]
        notify(store, "someone", "bob", "reply", key, text="dup")
        store.db.commit()
        after = store.db.execute("SELECT COUNT(*) FROM cm_notifications").fetchone()[0]
        assert after == before


def test_group_activity_notification_on_invite_and_approve(client):
    c, _ = client
    profile(c, "alice_n")
    gid = c.post("/api/community/groups", json={"name": "Priv", "handle": "priv-n", "visibility": "private"}).json()["group"]["id"]
    bob = other(c)
    profile(bob, "bob_n")
    c.post(f"/api/community/groups/{gid}/invite", json={"handle": "bob_n"})
    assert any(n["kind"] == "group_activity" for n in bob.get("/api/community/inbox").json()["notifications"])
    c.post(f"/api/community/groups/{gid}/members/bob_n/approve")
    notes = bob.get("/api/community/inbox").json()["notifications"]
    assert len([n for n in notes if n["kind"] == "group_activity"]) >= 2


def test_no_dm_or_composer_route_absent(client):
    c, _ = client
    paths = set(c.get("/openapi.json").json()["paths"].keys())
    server_paths = set(TestClient(community_server.app).get("/openapi.json").json()["paths"].keys())
    for paths_set in (paths, server_paths):
        assert not any("dm" in p.lower() or "direct-message" in p.lower() or "/messages" in p.lower() or "composer" in p.lower() for p in paths_set), paths_set
    # Probing a DM endpoint is 404, never a fabricated composer
    assert c.post("/api/community/dm", json={"text": "hi"}).status_code == 404
    assert c.post("/api/community/messages", json={"text": "hi"}).status_code == 404


def test_mark_read_other_owner_404_and_read_all(client):
    c, _ = client
    profile(c, "alice_n")
    pid = c.post("/api/community/posts", json={"text": "Hi"}).json()["post"]["id"]
    bob = other(c)
    profile(bob, "bob_n")
    bob.post(f"/api/community/posts/{pid}/comments", json={"text": "reply"})
    note_id = c.get("/api/community/inbox").json()["notifications"][0]["id"]
    assert bob.post(f"/api/community/notifications/{note_id}/read").status_code == 404
    assert c.post("/api/community/notifications/read-all").status_code == 200
    assert c.get("/api/community/inbox").json()["unread_count"] == 0
