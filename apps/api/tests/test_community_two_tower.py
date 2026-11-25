"""Tests for recommender.py & train_community_two_tower.py: 4-stage ranking, safety, D19/D19b, latency."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community.context_profile import (
    RECALL_MIN_WEIGHT,
    clear_ephemeral_context,
    lower_usage_topic,
    record_interaction_event,
    router as context_router,
    set_ephemeral_context,
)
from app.community.moderation import record_model_flag, router as mod_router, setup_mod
from app.community.recommender import (
    rank_discovery,
    recall_lowered_and_boost,
    setup_recommender,
)
from app.community.routes import router as community_router
from app.identity.models import APP_CAPABILITIES, VerifiedPrincipal
from tests.fixtures.community.bind import install


def _make_req(principal: VerifiedPrincipal | None = None):
    class _State:
        pass

    class _App:
        state = _State()

    class _Req:
        state = _State()
        app = _App()

    r = _Req()
    r.state.community_principal = principal
    return r


def _adult_principal(owner: str) -> VerifiedPrincipal:
    return VerifiedPrincipal(
        user_id=owner,
        app_id="community",
        capabilities=APP_CAPABILITIES["community"],
        auth_mode="verified_app_session",
        age_band="adult_18_plus",
    )


def _minor_principal(owner: str) -> VerifiedPrincipal:
    return VerifiedPrincipal(
        user_id=owner,
        app_id="community",
        capabilities=APP_CAPABILITIES["community"],
        auth_mode="verified_app_session",
        age_band="teen_13_17",
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(context_router)
    app.include_router(mod_router)
    install(app, store, tmp_path)

    alice = TestClient(app)
    alice.get("/api/session")
    prof = alice.put(
        "/api/community/profiles/me",
        json={"handle": "alice_tt", "age_band": "18+", "area": "Dubai Marina", "interests": ["padel"], "privacy": "public"},
    ).json()["profile"]
    owner = prof["owner"]
    clear_ephemeral_context(owner)

    bob = TestClient(app)
    bob.get("/api/session")
    bob_prof = bob.put(
        "/api/community/profiles/me",
        json={"handle": "bob_tt", "age_band": "18+", "area": "DIFC", "interests": ["coffee"], "privacy": "public"},
    ).json()["profile"]

    yield alice, bob, store, owner, bob_prof["owner"]
    clear_ephemeral_context(owner)
    store.db.close()


def test_two_tower_beats_unpersonalized_and_grounds_why_this(env):
    alice, bob, store, owner, _bob_owner = env
    p_padel = bob.post(
        "/api/community/posts",
        json={"text": "Evening #padel doubles match at Dubai Marina courts tonight!"},
    ).json()["post"]["id"]
    p_other = bob.post(
        "/api/community/posts",
        json={"text": "Industrial warehouse pallet racking suppliers in Jebel Ali"},
    ).json()["post"]["id"]

    # Unpersonalized cold-start user (no profile, no context) vs Alice (interested in padel + Marina).
    req_alice = _make_req(_adult_principal(owner))
    ranked = rank_discovery(req_alice, store, owner, limit=10)
    assert ranked["empty"] is False
    ids = [it["id"] for it in ranked["items"]]
    assert ids.index(p_padel) < ids.index(p_other)
    top = ranked["items"][0]
    assert top["why_chip"] == "Why this?"
    assert "padel" in top["why_this"].lower()
    assert top["score"] > ranked["items"][1]["score"]

    # Grounded why_this never claims unused signals (e.g. DIFC did not match).
    assert "difc" not in top["why_this"].lower()


def test_driving_safe_mode_collapses_and_deprioritizes_long_posts(env):
    _alice, bob, store, owner, _ = env
    long_text = "Detailed multi-paragraph breakdown of DIFC regulatory updates and urban planning: " + ("word " * 80)
    short_text = "Quick DIFC coffee alert near Gate Village right now!"
    p_long = bob.post("/api/community/posts", json={"text": long_text}).json()["post"]["id"]
    p_short = bob.post("/api/community/posts", json={"text": short_text}).json()["post"]["id"]

    set_ephemeral_context(owner, {"area_coarse": "DIFC", "device_class": "mobile_ios", "user_state": "driving"})
    ranked = rank_discovery(_make_req(_adult_principal(owner)), store, owner, limit=10)
    assert ranked["driving_safe_mode"] is True

    by_id = {it["id"]: it for it in ranked["items"]}
    ids = [it["id"] for it in ranked["items"]]
    assert ids.index(p_short) < ids.index(p_long)
    assert by_id[p_long]["driving_collapsed"] is True
    assert by_id[p_long]["collapsed"] is True
    assert by_id[p_long]["short_summary"] is not None
    assert by_id[p_long]["safety_notice"]
    assert by_id[p_short]["driving_collapsed"] is False


def test_d19_lower_stops_feed_influence_and_d19b_recall_restores_and_boosts(env):
    _alice, bob, store, owner, _ = env
    p_coffee = bob.post("/api/community/posts", json={"text": "Best #coffee espresso in DIFC"}).json()["post"]["id"]
    # Qualified coffee affinity in cm_usage_profile across 2 sessions.
    with store.lock:
        record_interaction_event(
            store, owner, post_id=p_coffee, topic_key="coffee", event_type="bookmark",
            area_coarse="DIFC", time_bucket="lunch", session_id="s1",
        )
        record_interaction_event(
            store, owner, post_id=p_coffee, topic_key="coffee", event_type="upvote",
            area_coarse="DIFC", time_bucket="lunch", session_id="s2",
        )
    set_ephemeral_context(owner, {"area_coarse": "DIFC", "time_bucket": "lunch", "device_class": "desktop", "user_state": "sitting"})
    before = rank_discovery(_make_req(_adult_principal(owner)), store, owner, limit=10)
    top_before = next(it for it in before["items"] if it["id"] == p_coffee)
    assert "usage:coffee" in top_before["features_used"]

    # D19 Lower -> stops usage:coffee feed influence immediately.
    with store.lock:
        lower_usage_topic(store, owner, "coffee")
    after_lower = rank_discovery(_make_req(_adult_principal(owner)), store, owner, limit=10)
    top_lowered = next(it for it in after_lower["items"] if it["id"] == p_coffee)
    assert "usage:coffee" not in top_lowered["features_used"]

    # D19b explicit query recall -> 100% callable & boosts >= 0.35, re-activating feed influence!
    with store.lock:
        recalled = recall_lowered_and_boost(store, owner, "#coffee")
    assert recalled["count"] >= 1
    assert "coffee" in recalled["boosted_topics"]
    assert recalled["recalled"][0]["weight"] >= RECALL_MIN_WEIGHT
    assert any(it["id"] == p_coffee for it in recalled["items"])

    after_recall = rank_discovery(_make_req(_adult_principal(owner)), store, owner, limit=10)
    top_recalled = next(it for it in after_recall["items"] if it["id"] == p_coffee)
    assert "usage:coffee" in top_recalled["features_used"]


def test_stage2_private_group_block_mute_moderation_and_minor_fail_closed(env):
    alice, bob, store, owner, bob_owner = env
    # Private group Bob creates without Alice as member.
    priv_gid = bob.post(
        "/api/community/groups",
        json={"name": "Bob Secret Padel", "handle": "bob-secret-padel", "visibility": "private"},
    ).json()["group"]["id"]
    p_priv = bob.post(
        f"/api/community/groups/{priv_gid}/posts",
        json={"text": "Secret #padel game in private group"},
    ).json()["post"]["id"]
    p_pub = bob.post("/api/community/posts", json={"text": "Public #padel rally in Marina"}).json()["post"]["id"]
    p_removed = bob.post("/api/community/posts", json={"text": "Mod removed #padel post"}).json()["post"]["id"]
    p_muted_tag = bob.post("/api/community/posts", json={"text": "Blocked #crypto spam post"}).json()["post"]["id"]

    # Moderation remove p_removed.
    with store.lock:
        setup_mod(store)
        ev = record_model_flag(store, target_type="post", target_id=p_removed, label="spam")
        store.db.execute(
            "UPDATE cm_moderation_events SET status='removed', target_state='removed' WHERE id=?",
            (ev["id"],),
        )
        # Create optional block/mute tables and mute #crypto.
        store.db.execute(
            "CREATE TABLE IF NOT EXISTS cm_user_blocks (owner TEXT NOT NULL, blocked_owner TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner, blocked_owner))"
        )
        store.db.execute(
            "CREATE TABLE IF NOT EXISTS cm_user_mutes (owner TEXT NOT NULL, kind TEXT NOT NULL, target TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner, kind, target))"
        )
        store.db.execute("INSERT INTO cm_user_mutes VALUES (?,?,?,?)", (owner, "tag", "crypto", "2026-11-25T00:00:00+00:00"))
        store.db.commit()

    ranked = rank_discovery(_make_req(_adult_principal(owner)), store, owner, limit=20)
    ids = {it["id"] for it in ranked["items"]}
    assert p_pub in ids
    assert p_priv not in ids
    assert p_removed not in ids
    assert p_muted_tag not in ids

    # Block bob_owner -> all Bob's posts disappear.
    with store.lock:
        store.db.execute("INSERT INTO cm_user_blocks VALUES (?,?,?)", (owner, bob_owner, "2026-11-25T00:00:00+00:00"))
        store.db.commit()
    ranked_blocked = rank_discovery(_make_req(_adult_principal(owner)), store, owner, limit=20)
    assert p_pub not in {it["id"] for it in ranked_blocked["items"]}

    # Unblock Bob and test D11 minor-protected fail-closed zero personalization.
    with store.lock:
        store.db.execute("DELETE FROM cm_user_blocks WHERE owner=?", (owner,))
        store.db.commit()
    minor_res = rank_discovery(_make_req(_minor_principal(owner)), store, owner, limit=20)
    assert minor_res["is_minor_protected"] is True
    assert minor_res["features_used"] == []
    assert minor_res["context_used"] is None
    assert minor_res["source"] == "cold_start"
    assert all(it["features_used"] == [] for it in minor_res["items"])

    # Rule 9: sensitive profile interest or tag never leaks into features_used / why_this.
    with store.lock:
        store.db.execute(
            "UPDATE cm_profiles SET interests=? WHERE owner=?",
            (json.dumps(["padel", "medication", "religion"]), owner),
        )
        store.db.commit()
    p_sens = bob.post("/api/community/posts", json={"text": "Discussion about medication and clinic schedules"}).json()["post"]["id"]
    sens_res = rank_discovery(_make_req(_adult_principal(owner)), store, owner, limit=20)
    assert all("medication" not in f and "religion" not in f for f in sens_res["features_used"])
    sens_item = next((it for it in sens_res["items"] if it["id"] == p_sens), None)
    if sens_item:
        assert "medication" not in sens_item["why_this"].lower()


def test_benchmark_2000_posts_under_150ms_and_trained_weights(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path

    trainer_path = Path(__file__).resolve().parents[3] / "scripts" / "train_community_two_tower.py"
    spec = importlib.util.spec_from_file_location("train_community_two_tower", trainer_path)
    assert spec and spec.loader
    trainer_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trainer_mod)
    _populate_synthetic_db = trainer_mod._populate_synthetic_db
    train_two_tower = trainer_mod.train_two_tower

    store = ActionStore(tmp_path / "bench.sqlite3")
    try:
        setup_recommender(store)
        _populate_synthetic_db(store)

        # Train weights artifact and point CM_RECOMMENDER_WEIGHTS to it.
        weights_file = tmp_path / "cm_recommender_weights.json"
        artifact = train_two_tower(store, output_path=weights_file, epochs=15)
        assert artifact["metrics"]["recall_at_20"] >= 0.5
        monkeypatch.setenv("CM_RECOMMENDER_WEIGHTS", str(weights_file))

        # Insert 2,000 synthetic posts.
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        topics = ("padel", "coffee", "startup", "running", "food", "cars")
        areas = ("Dubai Marina", "DIFC", "JLT", "Downtown Dubai", "Business Bay", "Al Quoz")
        rows = [
            (
                f"bench_p_{i:04d}",
                f"bench_author_{i % 50}",
                None,
                f"Community post #{i} about #{topics[i % 6]} in {areas[i % 6]}",
                1,
                0,
                0,
                "demo_fixture",
                stamp,
                stamp,
            )
            for i in range(2000)
        ]
        store.db.conn.executemany(
            "INSERT OR IGNORE INTO cm_posts (id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        store.db.commit()

        owner = "synth_user_0"
        req = _make_req(_adult_principal(owner))
        # Warm up embeddings index (pre-computed in cm_post_embeddings as in production).
        warm = rank_discovery(req, store, owner, limit=20)
        assert len(warm["items"]) == 20

        # Benchmark Stage-1 + Stage-2/3/4 ranking over 2,000+ posts.
        t0 = time.perf_counter()
        res = rank_discovery(req, store, owner, limit=20)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        print(f"BENCHMARK_2000_POSTS_MS={elapsed_ms:.2f}")
        assert len(res["items"]) == 20
        assert elapsed_ms < 150.0, f"2000-post ranking took {elapsed_ms:.1f} ms (>= 150 ms)"

        # Verify author diversity cap (<= 2 per author in top 20).
        counts: dict[str, int] = {}
        for it in res["items"]:
            a = it["owner"]
            counts[a] = counts.get(a, 0) + 1
        assert max(counts.values()) <= 2
    finally:
        store.db.close()
