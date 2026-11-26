"""§7 acceptance for the community-demo-10-v1 seed cohort."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community import demo_10_users as demo
from app.community.context_profile import record_interaction_event
from app.community.moderation import router as mod_router
from app.community.routes import router as community_router
from tests.fixtures.community.bind import install


@pytest.fixture
def store(tmp_path):
    s = ActionStore(tmp_path / "community10.sqlite3")
    yield s
    s.db.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    s = ActionStore(tmp_path / "community10-api.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(s))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(mod_router)
    install(app, s, tmp_path)
    c = TestClient(app)
    c.get("/api/session")
    yield c, s
    s.db.close()


def other(c: TestClient) -> TestClient:
    o = TestClient(c.app)
    o.get("/api/session")
    return o


def test_plan_targets_and_seed_apply_verify(store):
    dry = demo.apply_seed(store, dry_run=True)
    assert dry["dry_run"] is True
    assert dry["users"] == 10 and dry["groups"] == 7 and dry["posts"] == 40
    before = demo.verify_counts(store)
    assert before["measured"]["users"] == 0

    applied = demo.apply_seed(store, dry_run=False)
    assert applied["verify"]["ok"] is True, applied["verify"]
    measured = applied["verify"]["measured"]
    assert measured["users"] == 10
    assert measured["groups"] == 7
    assert measured["posts"] >= 40
    assert measured["comments"] >= 90
    assert measured["reply_chains"] >= 15
    assert measured["reactions"] >= 120
    assert measured["follows"] >= 20
    assert measured["memberships"] >= 20
    assert measured["notifications"] >= 20
    assert measured["bookmarks"] >= 10
    assert measured["reports"] >= 2
    assert measured["media"] >= 4
    assert measured["min_posts_per_user"] >= 3

    # Idempotent re-apply does not double rows
    again = demo.apply_seed(store, dry_run=False)
    assert again["verify"]["measured"]["posts"] == measured["posts"]
    assert again["verify"]["measured"]["comments"] == measured["comments"]
    assert again["verify"]["measured"]["reactions"] == measured["reactions"]


def test_provenance_and_stable_ids(store):
    demo.apply_seed(store, dry_run=False)
    ns = f"{demo.NAMESPACE}%"
    bad = store.db.execute(
        "SELECT COUNT(*) FROM cm_posts WHERE id LIKE ? AND provenance <> ?",
        (ns, demo.PROVENANCE),
    ).fetchone()[0]
    assert bad == 0
    owners = [r[0] for r in store.db.execute("SELECT owner FROM cm_profiles WHERE owner LIKE ?", (ns,)).fetchall()]
    assert len(owners) == 10
    assert all(o.startswith(f"{demo.NAMESPACE}:") for o in owners)
    for i in range(1, 41):
        row = store.db.execute("SELECT id, owner, created_at, provenance FROM cm_posts WHERE id=?", (demo.post_id(i),)).fetchone()
        assert row is not None
        assert row[3] == "demo_fixture"
        assert row[2]  # timestamp present


def test_fk_integrity_comments_reactions_bookmarks_notifs(store):
    demo.apply_seed(store, dry_run=False)
    ns = f"{demo.NAMESPACE}%"
    orphan_c = store.db.execute(
        """SELECT COUNT(*) FROM cm_comments c
           WHERE c.id LIKE ? AND NOT EXISTS (SELECT 1 FROM cm_posts p WHERE p.id=c.post_id)""",
        (ns,),
    ).fetchone()[0]
    assert orphan_c == 0
    orphan_r = store.db.execute(
        """SELECT COUNT(*) FROM cm_reactions r
           WHERE r.target_id LIKE ? AND NOT EXISTS (SELECT 1 FROM cm_posts p WHERE p.id=r.target_id)""",
        (ns,),
    ).fetchone()[0]
    assert orphan_r == 0
    orphan_b = store.db.execute(
        """SELECT COUNT(*) FROM cm_bookmarks b
           WHERE b.post_id LIKE ? AND NOT EXISTS (SELECT 1 FROM cm_posts p WHERE p.id=b.post_id)""",
        (ns,),
    ).fetchone()[0]
    assert orphan_b == 0
    orphan_n = store.db.execute(
        """SELECT COUNT(*) FROM cm_notifications n
           WHERE n.dedupe_key LIKE ? AND n.kind='reply'
             AND NOT EXISTS (SELECT 1 FROM cm_posts p WHERE p.id=n.post_id)""",
        (f"{demo.NAMESPACE}:%",),
    ).fetchone()[0]
    assert orphan_n == 0
    # Recipients are demo owners
    bad_owner = store.db.execute(
        "SELECT COUNT(*) FROM cm_notifications WHERE dedupe_key LIKE ? AND owner NOT LIKE ?",
        (f"{demo.NAMESPACE}:%", ns),
    ).fetchone()[0]
    assert bad_owner == 0
    # No self-follows
    self_f = store.db.execute(
        "SELECT COUNT(*) FROM cm_follows WHERE follower=followee AND follower LIKE ?", (ns,)
    ).fetchone()[0]
    assert self_f == 0


def test_survives_store_reopen(tmp_path):
    path = tmp_path / "persist.sqlite3"
    s1 = ActionStore(path)
    demo.apply_seed(s1, dry_run=False)
    v1 = demo.verify_counts(s1)
    assert v1["ok"]
    s1.db.close()
    s2 = ActionStore(path)
    v2 = demo.verify_counts(s2)
    assert v2["ok"]
    assert v2["measured"]["posts"] == v1["measured"]["posts"]
    s2.db.close()


def test_cross_owner_bookmarks_private(client):
    c, store = client
    demo.apply_seed(store, dry_run=False)
    # Alice bookmarks a real post of her own; Bob cannot see Alice's saves.
    r = c.put(
        "/api/community/profiles/me",
        json={"handle": "alice_demo_view", "display_name": "Alice", "age_band": "18+", "privacy": "public"},
    )
    assert r.status_code == 200, r.text
    post = c.post("/api/community/posts", json={"text": "Alice private-ish note for bookmark scope"})
    assert post.status_code == 200, post.text
    pid = post.json()["post"]["id"]
    assert c.post(f"/api/community/posts/{pid}/bookmarks").status_code == 200
    alice_ids = [p["id"] for p in c.get("/api/community/bookmarks").json()["bookmarks"]]
    assert pid in alice_ids

    bob = other(c)
    bob.put(
        "/api/community/profiles/me",
        json={"handle": "bob_demo_view", "display_name": "Bob", "age_band": "18+", "privacy": "public"},
    )
    bob_ids = [p["id"] for p in bob.get("/api/community/bookmarks").json()["bookmarks"]]
    assert pid not in bob_ids


def test_demo_not_usage_profile_or_memory(store):
    from app.community.context_profile import setup_context_profile

    demo.apply_seed(store, dry_run=False)
    oid = demo.owner_id("sim-01")
    pid = demo.post_id(1)
    out = record_interaction_event(
        store,
        oid,
        post_id=pid,
        topic_key="react",
        event_type="react",
        value=1.0,
        dedupe_key=f"demo-skip-{pid}",
    )
    assert out.get("skipped") == "demo_fixture"
    setup_context_profile(store)
    assert store.db.execute(
        "SELECT COUNT(*) FROM cm_interaction_events WHERE owner=? OR post_id=?",
        (oid, pid),
    ).fetchone()[0] == 0

    # temporal_memory path: remember() returns None for demo authors
    from app.community import memory as cm_mem

    class _P:
        user_id = oid
        is_minor_protected = False

    class _Req:
        app = type("A", (), {"state": type("S", (), {"memory_bridge": object()})()})()
        state = type("St", (), {"community_principal": _P()})()

    assert (
        cm_mem.remember(
            _Req(),
            record_id=demo.post_id(2),
            source_id=pid,
            text="demo text",
            author_id=oid,
        )
        is None
    )


def test_group_feed_shows_demo_with_provenance(client):
    c, store = client
    demo.apply_seed(store, dry_run=False)
    c.put(
        "/api/community/profiles/me",
        json={"handle": "viewer_demo", "display_name": "Viewer", "age_band": "18+", "privacy": "public"},
    )
    gid = demo.group_id("dubai-developers")
    r = c.get(f"/api/community/groups/{gid}/posts")
    assert r.status_code == 200, r.text
    posts = r.json()["posts"]
    assert len(posts) >= 3
    assert all(p["provenance"] == "demo_fixture" for p in posts)
    # Search discovers demo profiles
    found = c.get("/api/community/search", params={"q": "nour"}).json()
    handles = [p["handle"] for p in found["profiles"]]
    assert "nour_fe_demo" in handles


def test_dry_run_writes_nothing_reset_scoped(store, tmp_path):
    # Organic row that must survive reset
    from app.community import store as cm

    cm.setup(store)
    stamp = "2026-11-01T00:00:00+00:00"
    store.db.execute(
        "INSERT INTO cm_profiles (owner,handle,display_name,bio,area,interests,age_band,privacy,provenance,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("organic-owner", "organic_user", "Organic", "", "", "[]", "18+", "public", "user_supplied", stamp, stamp),
    )
    store.db.execute(
        "INSERT INTO cm_posts (id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at,flair,repost_of_id) "
        "VALUES (?,?,NULL,?,1,0,0,'user_supplied',?,?,'',NULL)",
        ("organic-post-1", "organic-owner", "organic text", stamp, stamp),
    )
    store.db.commit()

    demo.apply_seed(store, dry_run=True)
    assert store.db.execute("SELECT COUNT(*) FROM cm_posts WHERE id LIKE ?", (f"{demo.NAMESPACE}%",)).fetchone()[0] == 0

    demo.apply_seed(store, dry_run=False)
    assert demo.verify_counts(store)["ok"]
    deleted = demo.reset_demo(store)
    assert deleted.get("cm_posts", 0) >= 40
    assert store.db.execute("SELECT COUNT(*) FROM cm_posts WHERE id LIKE ?", (f"{demo.NAMESPACE}%",)).fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM cm_profiles WHERE owner=?", ("organic-owner",)).fetchone()[0] == 1
    assert store.db.execute("SELECT COUNT(*) FROM cm_posts WHERE id=?", ("organic-post-1",)).fetchone()[0] == 1


def test_moderation_fixtures_flag_only_no_auto_ban(store):
    demo.apply_seed(store, dry_run=False)
    rows = store.db.execute(
        "SELECT id,status,target_state,label FROM cm_moderation_events WHERE id LIKE ?",
        (f"{demo.NAMESPACE}%",),
    ).fetchall()
    assert len(rows) >= 2
    labels = {r[3] for r in rows}
    assert "false_positive_candidate" in labels
    assert "spam_fixture" in labels
    for r in rows:
        assert r[1] == "flagged"
        assert r[2] == "flagged"
    # No ban status anywhere in demo moderation events
    banned = store.db.execute(
        "SELECT COUNT(*) FROM cm_moderation_events WHERE id LIKE ? AND (status LIKE '%ban%' OR target_state LIKE '%ban%')",
        (f"{demo.NAMESPACE}%",),
    ).fetchone()[0]
    assert banned == 0


def test_cli_guard_requires_env(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[3] / "scripts" / "seed_community_10_users.py"
    assert script.exists()
    spec = importlib.util.spec_from_file_location("seed_community_10_users_cli", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    monkeypatch.delenv("DEMO_SEED_ENABLED", raising=False)
    assert mod.main(["--apply"]) == 2

    monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
    monkeypatch.setattr(mod, "_store_target", lambda: tmp_path / "cli-seed.sqlite3")
    assert mod.main(["--apply", "--json"]) == 0
    assert mod.main(["--dry-run"]) == 0
    assert mod.main(["--reset-demo", "--verify"]) == 0
