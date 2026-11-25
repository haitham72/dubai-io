"""E14a Community backend social parity: voting, sorts, hashtags/flairs, reposts, block/mute, split memory consent + D19 lower."""

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions, db as db_mod
from app.actions import ActionEngine, ActionStore
from app.community import store as cm_store
from app.community.memory_routes import router as memory_router
from app.community.moderation import router as moderation_router
from app.community.routes import router as community_router
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from tests.fixtures.community.bind import install


def _make_app(tmp_path, monkeypatch, *, with_memory=True):
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    fake = None
    bridge = None
    if with_memory:
        mem = db_mod.connect(tmp_path / "memory.sqlite3")
        fake = FakeTemporalMemoryClient()
        bridge = MemoryBridge(mem, fake)
        app.state.memory_bridge = bridge
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(moderation_router)
    if with_memory:
        app.include_router(memory_router)
    install(app, store, tmp_path)
    return app, store, bridge, fake


@pytest.fixture
def env(tmp_path, monkeypatch):
    app, store, bridge, fake = _make_app(tmp_path, monkeypatch, with_memory=True)
    alice = TestClient(app)
    alice.get("/api/session")
    yield alice, app, store, bridge, fake
    store.db.close()


def _new_user(app, handle: str):
    c = TestClient(app)
    c.get("/api/session")
    r = c.put(
        "/api/community/profiles/me",
        json={"handle": handle, "display_name": handle.title(), "age_band": "18+", "privacy": "public"},
    )
    assert r.status_code == 200, r.text
    return c, r.json()["profile"]["owner"]


# ---------------------------------------------------------------- Voting & Feed Sorts
def test_post_and_comment_voting_and_sorts(env):
    alice, app, store, _, _ = env
    _new_user(app, "alice_v")
    alice.put("/api/community/profiles/me", json={"handle": "alice_v", "display_name": "Alice", "age_band": "18+"})
    bob, _ = _new_user(app, "bob_v")
    carol, _ = _new_user(app, "carol_v")
    alice.post("/api/community/follows/bob_v")

    p1 = bob.post("/api/community/posts", json={"text": "First post #padel"}).json()["post"]["id"]
    p2 = bob.post("/api/community/posts", json={"text": "Second post #padel"}).json()["post"]["id"]
    p3 = bob.post("/api/community/posts", json={"text": "Controversial post #padel"}).json()["post"]["id"]

    # Invalid vote rejected with 422
    assert alice.post(f"/api/community/posts/{p1}/vote", json={"value": 2}).status_code == 422

    # Unvoted post with reaction falls back to likes count for score
    assert alice.post(f"/api/community/posts/{p1}/reactions", json={"kind": "like"}).status_code == 200
    fetched_p1 = alice.get(f"/api/community/posts/{p1}").json()["post"]
    assert fetched_p1["score"] == 1
    assert fetched_p1["vote_score"] == 0
    assert fetched_p1["my_vote"] == 0

    # Upvote p2 by 3 users -> p2 dominates hot & top
    for voter in (alice, bob, carol):
        rv = voter.post(f"/api/community/posts/{p2}/vote", json={"value": 1})
        assert rv.status_code == 200, rv.text
        assert rv.json()["my_vote"] == 1
    p2_data = alice.get(f"/api/community/posts/{p2}").json()["post"]
    assert p2_data["upvotes"] == 3 and p2_data["downvotes"] == 0
    assert p2_data["vote_score"] == 3 and p2_data["score"] == 3

    # p3 gets balanced votes (1 up, 1 down) -> controversial beats p1 & p2
    assert alice.post(f"/api/community/posts/{p3}/vote", json={"value": 1}).status_code == 200
    assert bob.post(f"/api/community/posts/{p3}/vote", json={"value": -1}).status_code == 200
    p3_data = alice.get(f"/api/community/posts/{p3}").json()["post"]
    assert p3_data["upvotes"] == 1 and p3_data["downvotes"] == 1 and p3_data["score"] == 0

    # Hot & Top rank p2 first
    hot_ids = [p["id"] for p in alice.get("/api/community/feed", params={"sort": "hot"}).json()["posts"]]
    top_ids = [p["id"] for p in alice.get("/api/community/feed", params={"sort": "top"}).json()["posts"]]
    assert hot_ids[0] == p2
    assert top_ids[0] == p2

    # Controversial ranks p3 first
    contro_ids = [p["id"] for p in alice.get("/api/community/feed", params={"sort": "controversial"}).json()["posts"]]
    assert contro_ids[0] == p3

    # Rising: backdate p2 by 48h and verify newer p1 with activity rises above stale p2
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(timespec="seconds")
    with store.lock:
        store.db.execute("UPDATE cm_posts SET created_at=? WHERE id=?", (old_ts, p2))
        store.db.commit()
    rising_ids = [p["id"] for p in alice.get("/api/community/feed", params={"sort": "rising"}).json()["posts"]]
    assert rising_ids.index(p1) < rising_ids.index(p2)

    # Vote = 0 clears vote
    cleared = alice.post(f"/api/community/posts/{p2}/vote", json={"value": 0}).json()
    assert cleared["my_vote"] == 0 and cleared["upvotes"] == 2 and cleared["score"] == 2

    # Comment voting
    cid = alice.post(f"/api/community/posts/{p1}/comments", json={"text": "Great point"}).json()["comment"]["id"]
    cv1 = bob.post(f"/api/community/comments/{cid}/vote", json={"value": 1}).json()
    assert cv1 == {"comment_id": cid, "score": 1, "my_vote": 1}
    cv2 = carol.post(f"/api/community/comments/{cid}/vote", json={"value": -1}).json()
    assert cv2 == {"comment_id": cid, "score": 0, "my_vote": -1}
    comments = alice.get(f"/api/community/posts/{p1}/comments").json()["comments"]
    assert comments[0]["score"] == 0 and comments[0]["my_vote"] == 0
    assert bob.post("/api/community/comments/missing-comment/vote", json={"value": 1}).status_code == 404


# ---------------------------------------------------------------- Hashtags, Flairs, Trending
def test_hashtags_flairs_trending_and_tag_feed(env):
    alice, app, _, _, _ = env
    alice.put("/api/community/profiles/me", json={"handle": "alice_t", "age_band": "18+"})
    bob, _ = _new_user(app, "bob_t")

    # Invalid flair fails 422
    bad = alice.post("/api/community/posts", json={"text": "Bad flair", "flair": "BogusFlair"})
    assert bad.status_code == 422

    # Auto-extracted hashtags + explicit tags capped at 10 + flair persisted
    many_tags = " ".join(f"#tag{i}" for i in range(12))
    r1 = alice.post(
        "/api/community/posts",
        json={"text": f"Best courts in #DubaiMarina #Padel {many_tags}", "flair": "Recommendation"},
    )
    assert r1.status_code == 200, r1.text
    p1 = r1.json()["post"]
    assert p1["flair"] == "Recommendation"
    assert len(p1["tags"]) == 10
    assert "dubaimarina" in p1["tags"] and "padel" in p1["tags"]

    # Bob posts public #padel without Alice following Bob
    p2 = bob.post(
        "/api/community/posts",
        json={"text": "Anyone playing #Padel tonight?", "flair": "Question", "tags": ["#jlt"]},
    ).json()["post"]
    assert "padel" in p2["tags"] and "jlt" in p2["tags"]

    # Private group hashtag must NOT leak into trending for non-members
    priv_gid = bob.post(
        "/api/community/groups",
        json={"name": "Secret Club", "handle": "secret-tags", "visibility": "private"},
    ).json()["group"]["id"]
    bob.post(
        f"/api/community/groups/{priv_gid}/posts",
        json={"text": "Secret #vip_only discussion"},
    )

    trending = alice.get("/api/community/tags/trending").json()["tags"]
    tag_map = {item["tag"]: item["count"] for item in trending}
    assert tag_map["padel"] == 2
    assert "vip_only" not in tag_map

    # Feed ?tag=#padel strips leading # and returns visible matching posts
    tag_feed = alice.get("/api/community/feed", params={"tag": "#Padel"}).json()["posts"]
    assert {p["id"] for p in tag_feed} == {p1["id"], p2["id"]}

    # Editing post updates tags & flair
    edited = alice.put(
        f"/api/community/posts/{p1['id']}",
        json={"text": "Switched to #running", "flair": "Event"},
    ).json()["post"]
    assert edited["flair"] == "Event"
    assert edited["tags"] == ["running"]


# ---------------------------------------------------------------- Reposts & Quote-Posts
def test_repost_public_and_reject_private_deleted_removed(env):
    alice, app, _, _, _ = env
    alice.put("/api/community/profiles/me", json={"handle": "alice_r", "age_band": "18+"})
    bob, _ = _new_user(app, "bob_r")

    pub_id = bob.post("/api/community/posts", json={"text": "Original public insight #dubai"}).json()["post"]["id"]
    rp = alice.post(f"/api/community/posts/{pub_id}/repost", json={"text": "Totally agree!"})
    assert rp.status_code == 200, rp.text
    rp_post = rp.json()["post"]
    assert rp_post["repost_of_id"] == pub_id
    assert rp_post["repost_preview"] is not None
    assert rp_post["repost_preview"]["id"] == pub_id
    assert rp_post["repost_preview"]["author"]["handle"] == "bob_r"

    # Deleting original hides repost_preview and blocks new reposts
    assert bob.delete(f"/api/community/posts/{pub_id}").status_code == 200
    after_del = alice.get(f"/api/community/posts/{rp_post['id']}").json()["post"]
    assert after_del["repost_preview"] is None
    assert alice.post(f"/api/community/posts/{pub_id}/repost", json={"text": "Late"}).status_code == 404

    # Private group post cannot be reposted by non-member (403/404) or reposted out to public feed by a member
    priv_gid = bob.post(
        "/api/community/groups",
        json={"name": "Priv Repost", "handle": "priv-repost", "visibility": "private"},
    ).json()["group"]["id"]
    priv_post = bob.post(f"/api/community/groups/{priv_gid}/posts", json={"text": "Secret info"}).json()["post"]["id"]
    assert alice.post(f"/api/community/posts/{priv_post}/repost", json={"text": "Leak"}).status_code in (403, 404)
    assert bob.post(f"/api/community/posts/{priv_post}/repost", json={"text": "Leak to public"}).status_code == 403

    # Moderation-removed post cannot be reposted
    pub_gid = bob.post(
        "/api/community/groups",
        json={"name": "Pub Mod", "handle": "pub-mod-repost", "visibility": "public"},
    ).json()["group"]["id"]
    mod_post = bob.post(f"/api/community/groups/{pub_gid}/posts", json={"text": "To be removed"}).json()["post"]["id"]
    rep = alice.post("/api/community/reports", json={"target_type": "post", "target_id": mod_post, "reason": "bad"})
    ev_id = rep.json()["event"]["id"]
    assert bob.post(f"/api/community/moderation/{ev_id}/resolve", json={"decision": "remove"}).status_code == 200
    assert alice.post(f"/api/community/posts/{mod_post}/repost", json={"text": "Repost removed"}).status_code == 404


# ---------------------------------------------------------------- Block & Mute
def test_block_and_mute_enforced_everywhere(env):
    alice, app, _, _, _ = env
    alice.put("/api/community/profiles/me", json={"handle": "alice_b", "age_band": "18+"})
    bob, bob_owner = _new_user(app, "bob_b")
    carol, _ = _new_user(app, "carol_b")
    alice.post("/api/community/follows/bob_b")
    alice.post("/api/community/follows/carol_b")

    # Self-block & missing handle
    assert alice.post("/api/community/blocks/alice_b").status_code == 400
    assert alice.post("/api/community/blocks/nobody_b").status_code == 404

    bob_post = bob.post("/api/community/posts", json={"text": "Bob searchable marina post"}).json()["post"]["id"]
    carol_post = carol.post("/api/community/posts", json={"text": "Carol post #padel"}).json()["post"]["id"]
    bob.post(f"/api/community/posts/{carol_post}/comments", json={"text": "Bob comment"})

    # Alice blocks Bob
    blk = alice.post("/api/community/blocks/bob_b")
    assert blk.status_code == 200 and blk.json()["blocked"] is True

    # Safety endpoint lists Bob
    safety = alice.get("/api/community/safety").json()
    assert any(b["handle"] == "bob_b" and b["owner"] == bob_owner for b in safety["blocks"])

    # Feed, search, post GET, comments, profile GET all exclude Bob
    assert bob_post not in [p["id"] for p in alice.get("/api/community/feed").json()["posts"]]
    s = alice.get("/api/community/search", params={"q": "bob_b"}).json()
    assert all(p["handle"] != "bob_b" for p in s["profiles"])
    assert bob_post not in [p["id"] for p in alice.get("/api/community/search", params={"q": "searchable"}).json()["posts"]]
    assert alice.get(f"/api/community/posts/{bob_post}").status_code == 404
    assert alice.get("/api/community/profiles/bob_b").status_code == 404
    carol_comments = alice.get(f"/api/community/posts/{carol_post}/comments").json()["comments"]
    assert all(c["author"]["handle"] != "bob_b" for c in carol_comments)

    # Blocked actor mentioning Alice produces zero notifications
    bob.post("/api/community/posts", json={"text": "Ping @alice_b while blocked"})
    notes = alice.get("/api/community/notifications").json()["notifications"]
    assert all(n["actor"] != bob_owner for n in notes)

    # Unblock restores access
    assert alice.delete("/api/community/blocks/bob_b").json()["blocked"] is False
    assert bob_post in [p["id"] for p in alice.get("/api/community/feed").json()["posts"]]

    # Mutes: mute tag #padel and mute owner carol_b
    assert alice.post("/api/community/mutes", json={"kind": "tag", "target": "#Padel"}).status_code == 200
    assert carol_post not in [p["id"] for p in alice.get("/api/community/feed").json()["posts"]]
    assert any(m == {"kind": "tag", "target": "padel"} for m in alice.get("/api/community/safety").json()["mutes"])
    assert alice.delete("/api/community/mutes", params={"kind": "tag", "target": "padel"}).json()["muted"] is False
    assert carol_post in [p["id"] for p in alice.get("/api/community/feed").json()["posts"]]


# ---------------------------------------------------------------- Split Memory Consent & D19 Lower
def test_split_memory_consent_and_lower_endpoint(env):
    alice, app, _, _, fake = env
    profile_resp = alice.put("/api/community/profiles/me", json={"handle": "alice_m", "age_band": "18+"})
    owner = profile_resp.json()["profile"]["owner"]
    bob, _ = _new_user(app, "bob_m")
    bob_post = bob.post("/api/community/posts", json={"text": "Bob discussion worth saving"}).json()["post"]["id"]

    # Default off preserves all legacy + split keys
    init = alice.get("/api/community/memory/consent").json()
    assert init["default_off"] is True
    assert init["remember_saved_discussions"] is False
    assert init["remember_public_posts"] is False
    assert {"read_enabled", "write_enabled", "allow_interest_export", "source_enabled", "generation", "as_of", "provenance"} <= set(init)

    # Enable ONLY remember_saved_discussions via PUT -> write_enabled syncs True
    updated = alice.put(
        "/api/community/memory/consent",
        json={"remember_saved_discussions": True, "remember_public_posts": False},
    ).json()
    assert updated["remember_saved_discussions"] is True
    assert updated["remember_public_posts"] is False
    assert updated["write_enabled"] is True
    assert updated["default_off"] is False

    # Bookmark writes cmsave:, but creating public post does NOT write cmpost:
    assert alice.post(f"/api/community/posts/{bob_post}/bookmarks").status_code == 200
    assert alice.post("/api/community/posts", json={"text": "My public post not remembered"}).status_code == 200
    records = fake.records.get(owner, {})
    assert any(k.startswith("cmsave:") for k in records)
    assert not any(k.startswith("cmpost:") for k in records)

    # Legacy payload still works seamlessly
    legacy = alice.post(
        "/api/community/memory/consent",
        json={"read_enabled": True, "write_enabled": True, "allow_interest_export": True},
    ).json()
    assert legacy["read_enabled"] is True and legacy["write_enabled"] is True and legacy["allow_interest_export"] is True

    # D19 lower endpoint lowers weight to 0.01 without erasing history
    lowered = alice.post("/api/community/memory/lower", json={"topic": "padel"}).json()
    assert lowered["lowered"] is True
    assert lowered["weight"] == 0.01
    assert lowered["provenance"] == "provider_confirmed"
    assert lowered["as_of"]
    assert any(not rec.erased_at for rec in fake.records[owner].values())

    # Forget continues to work
    forgotten = alice.post("/api/community/memory/forget").json()
    assert forgotten["forgotten"] is True


# ---------------------------------------------------------------- Idempotent Schema Upgrade
def test_preexisting_db_upgrades_cm_posts_cleanly(tmp_path):
    store = ActionStore(tmp_path / "legacy.sqlite3")
    with store.lock:
        # Simulate pre-E14a cm_posts without flair or repost_of_id
        store.db.execute(
            """CREATE TABLE cm_posts (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, group_id TEXT,
                text TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
                pinned INTEGER NOT NULL DEFAULT 0, deleted INTEGER NOT NULL DEFAULT 0,
                provenance TEXT NOT NULL DEFAULT 'user_supplied',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
        )
        store.db.commit()
        store._community_ready = False
        cm_store.setup(store)
        cols = {row[1] for row in store.db.execute("PRAGMA table_info(cm_posts)").fetchall()}
        assert "flair" in cols and "repost_of_id" in cols
        # Second setup is idempotent
        store._community_ready = False
        cm_store.setup(store)
    store.db.close()
