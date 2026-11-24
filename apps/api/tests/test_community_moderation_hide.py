"""A human remove hides the post. A flag does not. Restore brings it back."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community.moderation import router as moderation_router
from app.community.routes import router as community_router
from tests.fixtures.community.bind import install


def _clients(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "hide.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(moderation_router)
    install(app, store, tmp_path)
    author = TestClient(app)
    author.get("/api/session")
    reader = TestClient(app)
    reader.get("/api/session")
    author.put("/api/community/profiles/me", json={"handle": "mod_author", "age_band": "18+", "privacy": "public"})
    reader.put("/api/community/profiles/me", json={"handle": "mod_reader", "age_band": "18+", "privacy": "public"})
    return author, reader


def _flag_and_resolve(author, reader, post_id, decision):
    report = reader.post("/api/community/reports", json={"target_type": "post", "target_id": post_id, "reason": "review this"})
    assert report.status_code == 200, report.text
    event_id = report.json()["event"]["id"] if "event" in report.json() else report.json()["moderation_event"]["id"]
    resolved = author.post(f"/api/community/moderation/{event_id}/resolve", json={"decision": decision})
    assert resolved.status_code == 200, resolved.text
    return resolved


def test_community_removed_post_hidden_and_restore(tmp_path, monkeypatch):
    author, reader = _clients(tmp_path, monkeypatch)
    reader.post("/api/community/follows/mod_author")
    group = author.post("/api/community/groups", json={"name": "Hide group", "handle": "hide-group", "visibility": "public"})
    gid = group.json()["group"]["id"]
    reader.post(f"/api/community/groups/{gid}/join")
    posted = author.post("/api/community/posts", json={"text": "Visible marina note @mod_reader", "group_id": gid})
    assert posted.status_code == 200, posted.text
    pid = posted.json()["post"]["id"]
    assert pid in [item["id"] for item in reader.get("/api/community/feed").json()["posts"]]
    _flag_and_resolve(author, reader, pid, "remove")
    assert reader.get(f"/api/community/posts/{pid}").status_code == 404
    assert pid not in [item["id"] for item in reader.get("/api/community/feed").json()["posts"]]
    found = reader.get("/api/community/search", params={"q": "marina"})
    assert pid not in [item["id"] for item in found.json()["posts"]]
    notes = reader.get("/api/community/inbox").json()["notifications"]
    assert pid not in [item.get("post_id") for item in notes]
    page = reader.get(f"/api/community/groups/{gid}/posts").json()["posts"]
    assert pid not in [item["id"] for item in page]
    _flag_and_resolve(author, reader, pid, "restore")
    assert reader.get(f"/api/community/posts/{pid}").status_code == 200
    assert pid in [item["id"] for item in reader.get("/api/community/feed").json()["posts"]]


def test_community_flag_alone_does_not_hide(tmp_path, monkeypatch):
    author, reader = _clients(tmp_path, monkeypatch)
    reader.post("/api/community/follows/mod_author")
    pid = author.post("/api/community/posts", json={"text": "Still visible after a flag"}).json()["post"]["id"]
    report = reader.post("/api/community/reports", json={"target_type": "post", "target_id": pid, "reason": "check"})
    assert report.status_code == 200, report.text
    assert reader.get(f"/api/community/posts/{pid}").status_code == 200
    assert pid in [item["id"] for item in reader.get("/api/community/feed").json()["posts"]]
