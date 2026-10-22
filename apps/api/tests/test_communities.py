from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions, communities
from app.actions import ActionEngine, ActionStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "communities.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    for router in (actions.router, communities.router):
        app.include_router(router)
    c = TestClient(app); c.get("/api/session")
    yield c, store
    store.db.close()


def other(c):
    o = TestClient(c.app); o.get("/api/session")
    return o


def test_seeded_communities_are_labelled_demo_and_joining_is_per_owner(client):
    c, _ = client
    listed = c.get("/api/communities").json()["communities"]
    assert len(listed) == len(communities.load_seed()[1]) and all(x["provenance"] == "demo_fixture" and not x["joined"] for x in listed)
    food = next(x for x in listed if x["id"] == "marina-foodies")
    after = {x["id"]: x for x in c.post("/api/communities/marina-foodies/join").json()["communities"]}
    assert after["marina-foodies"]["joined"] and after["marina-foodies"]["members"] == food["members"] + 1
    assert not {x["id"]: x for x in other(c).get("/api/communities").json()["communities"]}["marina-foodies"]["joined"]
    assert c.post("/api/communities/nope/join").status_code == 404
    left = {x["id"]: x for x in c.post("/api/communities/marina-foodies/leave").json()["communities"]}
    assert not left["marina-foodies"]["joined"]


def test_feed_puts_joined_first_and_posts_stay_private_to_their_author(client):
    c, _ = client
    c.post("/api/communities/jlt-runners/join")
    feed = c.get("/api/feed").json()
    assert feed["posts"][0]["community"]["id"] == "jlt-runners" and all(p["kind"] == "post" for p in feed["posts"])
    assert feed["stories"][0]["community"]["id"] == "jlt-runners"
    assert feed["posts"][0]["author"]["emoji"] and feed["posts"][0]["author"]["handle"]
    assert c.post("/api/communities/marina-foodies/posts", json={"text": "hi"}).status_code == 409  # join first
    assert c.post("/api/communities/jlt-runners/posts", json={"text": "   "}).status_code == 422
    c.post("/api/communities/jlt-runners/posts", json={"text": "Lost grey cat near Cluster T"})
    mine = [p for p in c.get("/api/feed").json()["posts"] if p["mine"]]
    assert mine and mine[0]["provenance"] == "user_supplied" and mine[0]["author"]["name"] == "You"
    assert not [p for p in other(c).get("/api/feed").json()["posts"] if p["text"].startswith("Lost grey cat")]


def test_hiding_a_post_or_story_affects_only_that_owner(client):
    c, _ = client
    first = c.get("/api/feed").json()["posts"][0]
    c.post(f"/api/posts/{first['id']}/hide", json={"reason": "not relevant"})
    assert first["id"] not in [p["id"] for p in c.get("/api/feed").json()["posts"]]
    assert first["id"] in [p["id"] for p in other(c).get("/api/feed").json()["posts"]]
    frames = c.get("/api/communities/marina-foodies/stories").json()["frames"]
    assert frames and frames[0]["provenance"] == "demo_fixture" and frames[0]["emoji"]
    c.post(f"/api/posts/{frames[0]['id']}/hide", json={})
    assert len(c.get("/api/communities/marina-foodies/stories").json()["frames"]) == len(frames) - 1
    assert c.post("/api/posts/missing/hide", json={}).status_code == 404


def test_chats_filter_unread_and_are_owner_scoped(client):
    c, _ = client
    c.post("/api/communities/jlt-runners/join")
    everything = c.get("/api/chats").json()
    kinds = {t["kind"] for t in everything["threads"]}
    assert kinds == {"group", "community"} and everything["unread"] > 0
    assert {t["kind"] for t in c.get("/api/chats?filter=groups").json()["threads"]} == {"group"}
    assert [t["id"] for t in c.get("/api/chats?filter=communities").json()["threads"]] == ["community:jlt-runners"]
    tid = everything["threads"][0]["id"]
    c.get(f"/api/chats/{tid}/messages")  # opening marks it read
    assert tid not in [t["id"] for t in c.get("/api/chats?filter=unread").json()["threads"]]
    sent = c.post(f"/api/chats/{tid}/messages", json={"text": "On my way"})
    assert sent.status_code == 200
    assert c.get(f"/api/chats/{tid}/messages").json()["messages"][-1]["mine"]
    assert other(c).get(f"/api/chats/{tid}/messages").status_code in (200, 404)
    assert "On my way" not in str(other(c).get("/api/chats").json())
    assert c.get("/api/chats?filter=everything").status_code == 422


def test_contacts_and_call_log_are_private_and_deletable(client):
    c, _ = client
    assert c.post("/api/contacts", json={"name": "Ahmed", "phone": "call me"}).status_code == 422
    contact = c.post("/api/contacts", json={"name": "Ahmed", "phone": "+971 50 123 4567"}).json()
    assert c.post("/api/calls", json={"contact_id": contact["id"]}).json()["tel"] == "tel:+971501234567"
    [call] = c.get("/api/calls").json()["calls"]
    assert call["name"] == "Ahmed" and call["source"] == "started_in_dubai_io"
    o = other(c)
    assert o.get("/api/contacts").json()["contacts"] == [] and o.get("/api/calls").json()["calls"] == []
    assert o.post("/api/calls", json={"contact_id": contact["id"]}).status_code == 404
    assert o.delete(f"/api/contacts/{contact['id']}").status_code == 404
    assert c.delete(f"/api/contacts/{contact['id']}").status_code == 200
    c.delete("/api/calls")
    assert c.get("/api/calls").json()["calls"] == []


def test_comments_read_seeded_and_own_only(client):
    c, _ = client
    post = next(p for p in c.get("/api/feed").json()["posts"] if p["comments"])
    seeded = c.get(f"/api/posts/{post['id']}/comments").json()["comments"]
    assert len(seeded) == post["comments"] and all(m["provenance"] == "demo_fixture" for m in seeded)
    c.post(f"/api/posts/{post['id']}/comments", json={"text": "Count me in 🙌"})
    assert c.get(f"/api/posts/{post['id']}/comments").json()["comments"][-1]["mine"]
    assert len(other(c).get(f"/api/posts/{post['id']}/comments").json()["comments"]) == len(seeded)
    assert c.post("/api/posts/missing/comments", json={"text": "x"}).status_code == 404


def test_seed_files_are_valid_and_use_only_local_media():
    personas, groups = communities.load_seed()
    ids = {p["id"] for p in personas}
    for g in groups:
        assert g["image"] in communities.MEDIA
        for post in g["posts"]:
            assert post["author"] in ids and all(m["author"] in ids for m in post["comments"])
