"""Tests for context_profile.py: geo snapping, TTL ephemeral context, Rule 9, D19, D19b."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions, db as db_mod
from app.actions import ActionEngine, ActionStore
from app.community.context_profile import (
    AGE_DECAY_FLOOR,
    CONTEXT_TTL_SECONDS,
    DUBAI_AREAS,
    RECALL_MIN_WEIGHT,
    SURFACE_THRESHOLD,
    WEIGHT_MIN,
    clear_ephemeral_context,
    compute_time_bucket,
    compute_usage_weight,
    get_ephemeral_context,
    record_interaction_event,
    router as context_router,
    set_ephemeral_context,
    snap_coordinates_to_area,
)
from app.community.routes import router as community_router
from app.identity.models import APP_CAPABILITIES, VerifiedPrincipal
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from tests.fixtures.community.bind import install


@pytest.fixture
def ctx_client(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    mem = db_mod.connect(tmp_path / "memory.sqlite3")
    fake = FakeTemporalMemoryClient()
    bridge = MemoryBridge(mem, fake)

    app = FastAPI()
    app.state.memory_bridge = bridge
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(context_router)
    install(app, store, tmp_path)

    c = TestClient(app)
    c.get("/api/session")
    prof = c.put(
        "/api/community/profiles/me",
        json={"handle": "alice_ctx", "age_band": "18+", "area": "DIFC", "interests": ["padel"], "privacy": "public"},
    )
    assert prof.status_code == 200, prof.text
    owner = prof.json()["profile"]["owner"]
    clear_ephemeral_context(owner)
    yield c, store, owner, bridge, fake
    clear_ephemeral_context(owner)
    store.db.close()


def test_coarse_snapping_and_zero_gps_persistence(ctx_client):
    c, store, owner, _bridge, _fake = ctx_client
    # Exact centroid tests across Dubai districts.
    for district, (lat, lng) in DUBAI_AREAS.items():
        assert snap_coordinates_to_area(lat, lng) == district

    # Slight offset near DIFC still snaps to DIFC and never persists raw lat/lng.
    raw_lat, raw_lng = 25.212345, 55.280987
    resp = c.post(
        "/api/community/context/heartbeat",
        json={
            "lat": raw_lat,
            "lng": raw_lng,
            "device_class": "mobile_ios",
            "user_state": "walking",
            "confidence": 0.88,
            "source": "expo_sensors",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["raw_coordinates_persisted"] is False
    assert body["ttl_seconds"] == CONTEXT_TTL_SECONDS
    assert body["context"]["area_coarse"] == "DIFC"
    assert "lat" not in body["context"] and "lng" not in body["context"]

    # Also test event with raw lat/lng snaps immediately and never stores GPS.
    ev_resp = c.post(
        "/api/community/events",
        json={
            "post_id": "p1",
            "topic_key": "padel",
            "event_type": "upvote",
            "lat": 25.0809,
            "lng": 55.1401,
            "device_class": "mobile_ios",
            "user_state": "running",
            "session_id": "s1",
            "dedupe_key": "d1",
        },
    )
    assert ev_resp.status_code == 200, ev_resp.text
    assert ev_resp.json()["event"]["area_coarse"] == "Dubai Marina"

    # Scan all SQL tables and ephemeral context for raw coordinate leakage.
    cur_ctx = c.get("/api/community/context/current").json()["context"]
    assert "lat" not in cur_ctx and "lng" not in cur_ctx
    dumped_ctx = json.dumps(cur_ctx)
    assert "25.212345" not in dumped_ctx and "55.280987" not in dumped_ctx

    rows = store.db.execute("SELECT * FROM cm_interaction_events WHERE owner=?", (owner,)).fetchall()
    assert "25.0809" not in json.dumps(rows) and "55.1401" not in json.dumps(rows)


def test_compute_time_bucket_dubai_tz():
    # Wednesday 2026-11-25 in Dubai (UTC+4).
    cases = [
        (datetime(2026, 11, 25, 2, 0, tzinfo=timezone.utc), ("early_morning", False)),   # 06:00 DXB Wed
        (datetime(2026, 11, 25, 4, 30, tzinfo=timezone.utc), ("commute_am", False)),     # 08:30 DXB Wed
        (datetime(2026, 11, 25, 7, 0, tzinfo=timezone.utc), ("workday", False)),         # 11:00 DXB Wed
        (datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc), ("lunch", False)),           # 13:00 DXB Wed
        (datetime(2026, 11, 25, 11, 0, tzinfo=timezone.utc), ("workday", False)),        # 15:00 DXB Wed
        (datetime(2026, 11, 25, 14, 0, tzinfo=timezone.utc), ("commute_pm", False)),     # 18:00 DXB Wed
        (datetime(2026, 11, 25, 17, 0, tzinfo=timezone.utc), ("evening", False)),        # 21:00 DXB Wed
        (datetime(2026, 11, 25, 20, 0, tzinfo=timezone.utc), ("late_night", False)),     # 00:00 DXB Thu
        (datetime(2026, 11, 28, 9, 0, tzinfo=timezone.utc), ("lunch", True)),            # 13:00 DXB Sat (weekend)
        (datetime(2026, 11, 29, 17, 0, tzinfo=timezone.utc), ("evening", True)),         # 21:00 DXB Sun (weekend)
    ]
    for dt_utc, expected in cases:
        assert compute_time_bucket(dt_utc) == expected


def test_ephemeral_ttl_and_redis_fallback(ctx_client, monkeypatch):
    c, _store, owner, _bridge, _fake = ctx_client
    # Unreachable Redis automatically falls back to in-process TTL cache.
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:63999/0")
    stored, backend = set_ephemeral_context(
        owner,
        {"area_coarse": "JLT", "user_state": "walking", "device_class": "mobile_android"},
        ttl_seconds=1,
    )
    assert backend == "memory_ttl"
    assert stored["area_coarse"] == "JLT"
    assert get_ephemeral_context(owner)["area_coarse"] == "JLT"

    # Simulate TTL expiry by advancing monotonic clock.
    import app.community.context_profile as cp

    real_mono = cp.time.monotonic
    monkeypatch.setattr(cp.time, "monotonic", lambda: real_mono() + 5.0)
    assert get_ephemeral_context(owner) is None


def test_rule9_zero_health_facts_from_user_state_and_sensitive_topics(ctx_client):
    c, store, owner, bridge, fake = ctx_client
    principal = VerifiedPrincipal(
        user_id=owner,
        app_id="community",
        capabilities=APP_CAPABILITIES["community"],
        auth_mode="verified_app_session",
        age_band="adult_18_plus",
    )
    bridge.set_source_consent(principal, "community", enabled=True, allow_interest_export=True)
    bridge.set_app_consent(principal, "community", read_enabled=True, write_enabled=True, allow_interest_export_to_community=True)

    # Send running/walking/driving heartbeats and events — NEVER written to temporal_memory.
    for state in ("running", "walking", "driving", "sitting"):
        assert c.post(
            "/api/community/context/heartbeat",
            json={"area_coarse": "Dubai Marina", "device_class": "mobile_ios", "user_state": state, "confidence": 0.9, "source": "expo_sensors"},
        ).status_code == 200
        assert c.post(
            "/api/community/events",
            json={"post_id": f"p_{state}", "topic_key": "padel", "event_type": "upvote", "user_state": state, "session_id": f"s_{state}"},
        ).status_code == 200

    assert fake.records.get(owner, {}) == {}
    # Also ensure user_state never leaks into cm_usage_profile.
    cols = [r[1] for r in store.db.execute("PRAGMA table_info(cm_usage_profile)").fetchall()]
    assert "user_state" not in cols

    # Sensitive topics are never projected into cm_usage_profile (Rule 9).
    for sens_topic in ("medication", "hospital", "religion"):
        c.post(
            "/api/community/events",
            json={"post_id": f"p_{sens_topic}_1", "topic_key": sens_topic, "event_type": "upvote", "session_id": "s_a"},
        )
        c.post(
            "/api/community/events",
            json={"post_id": f"p_{sens_topic}_2", "topic_key": sens_topic, "event_type": "upvote", "session_id": "s_b"},
        )
    topics = [e["topic_key"] for e in c.get("/api/community/profile/usage").json()["entries"]]
    for sens_topic in ("medication", "hospital", "religion"):
        assert sens_topic not in topics


def test_two_visit_qualification_and_dedupe(ctx_client):
    c, store, owner, _bridge, _fake = ctx_client
    # First visit in session s1 (plus duplicate dedupe_key ignored).
    r1 = c.post(
        "/api/community/events",
        json={"post_id": "p1", "topic_key": "coffee", "event_type": "upvote", "area_coarse": "DIFC", "time_bucket": "lunch", "session_id": "s1", "dedupe_key": "k1"},
    )
    assert r1.status_code == 200
    assert r1.json()["deduped"] is False
    r1_dup = c.post(
        "/api/community/events",
        json={"post_id": "p1", "topic_key": "coffee", "event_type": "upvote", "area_coarse": "DIFC", "time_bucket": "lunch", "session_id": "s1", "dedupe_key": "k1"},
    )
    assert r1_dup.status_code == 200
    assert r1_dup.json()["deduped"] is True

    entries = c.get("/api/community/profile/usage").json()["entries"]
    assert len(entries) == 1
    assert entries[0]["evidence_count"] == 1
    assert entries[0]["distinct_sessions"] == 1
    assert entries[0]["qualified"] is False
    assert entries[0]["active_in_feed"] is False

    # Same session s1 within 1 minute still does NOT qualify.
    c.post(
        "/api/community/events",
        json={"post_id": "p2", "topic_key": "coffee", "event_type": "bookmark", "area_coarse": "DIFC", "time_bucket": "lunch", "session_id": "s1", "dedupe_key": "k2"},
    )
    entries = c.get("/api/community/profile/usage").json()["entries"]
    assert entries[0]["qualified"] is False

    # Second distinct session s2 qualifies it!
    c.post(
        "/api/community/events",
        json={"post_id": "p3", "topic_key": "coffee", "event_type": "upvote", "area_coarse": "DIFC", "time_bucket": "lunch", "session_id": "s2", "dedupe_key": "k3"},
    )
    entries = c.get("/api/community/profile/usage").json()["entries"]
    assert entries[0]["distinct_sessions"] == 2
    assert entries[0]["qualified"] is True
    assert entries[0]["weight"] >= SURFACE_THRESHOLD
    assert entries[0]["active_in_feed"] is True

    # Also verify >= 6h separation qualifies even on single/empty session_id.
    t0 = datetime(2026, 11, 20, 8, 0, tzinfo=timezone.utc)
    with store.lock:
        record_interaction_event(
            store, owner, post_id="p4", topic_key="cycling", event_type="upvote",
            area_coarse="Al Quoz", time_bucket="early_morning", session_id="s_only",
            created_at=t0.isoformat(timespec="seconds"),
        )
        record_interaction_event(
            store, owner, post_id="p5", topic_key="cycling", event_type="upvote",
            area_coarse="Al Quoz", time_bucket="early_morning", session_id="s_only",
            created_at=(t0 + timedelta(hours=7)).isoformat(timespec="seconds"),
        )
    cyc = [e for e in c.get("/api/community/profile/usage").json()["entries"] if e["topic_key"] == "cycling"][0]
    assert cyc["qualified"] is True


def test_d19_age_decay_lower_restore_and_d19b_recall(ctx_client):
    c, store, owner, _bridge, _fake = ctx_client
    # Build qualified usage entry for #padel.
    c.post(
        "/api/community/events",
        json={"post_id": "p1", "topic_key": "#padel", "event_type": "bookmark", "area_coarse": "Dubai Marina", "time_bucket": "evening", "session_id": "s1"},
    )
    c.post(
        "/api/community/events",
        json={"post_id": "p2", "topic_key": "padel", "event_type": "upvote", "area_coarse": "Dubai Marina", "time_bucket": "evening", "session_id": "s2"},
    )

    # Check age decay math: > 30 days decays down to floor 0.05 (not 0.01).
    row = store.db.execute("SELECT * FROM cm_usage_profile WHERE owner=? AND topic_key='padel'", (owner,)).fetchone()
    now_dt = datetime.now(timezone.utc)
    w_fresh = compute_usage_weight(row, now=now_dt)
    w_aged = compute_usage_weight(row, now=now_dt + timedelta(days=300))
    assert w_fresh >= 0.40
    assert w_aged == pytest.approx(AGE_DECAY_FLOOR, abs=1e-6)

    # D19 Lower -> drops weight to 0.01, still inspectable on profile, excluded from feed.
    low_resp = c.post("/api/community/profile/usage/lower", json={"topic_key": "padel"})
    assert low_resp.status_code == 200, low_resp.text
    assert low_resp.json()["weight"] == WEIGHT_MIN
    assert low_resp.json()["entries"][0]["weight"] == WEIGHT_MIN
    assert low_resp.json()["entries"][0]["active_in_feed"] is False

    # Profile inspection includes lowered by default (?include_lowered=true).
    prof_all = c.get("/api/community/profile/usage").json()["entries"]
    assert any(e["topic_key"] == "padel" and e["weight"] == WEIGHT_MIN for e in prof_all)
    prof_active = c.get("/api/community/profile/usage?include_lowered=false").json()["entries"]
    assert all(e["topic_key"] != "padel" for e in prof_active)

    # D19b Explicit Recall on lowered entry (0.01) -> 100% callable & boosts >= 0.35!
    recall_resp = c.post("/api/community/profile/usage/recall", json={"topic_key": "padel"})
    assert recall_resp.status_code == 200, recall_resp.text
    rj = recall_resp.json()
    assert rj["count"] >= 1
    assert "padel" in rj["boosted_topics"]
    recalled_entry = rj["recalled"][0]
    assert recalled_entry["lowered"] is False
    assert recalled_entry["weight"] >= RECALL_MIN_WEIGHT
    assert recalled_entry["active_in_feed"] is True

    # Lower again, then test explicit Restore endpoint.
    assert c.post("/api/community/profile/usage/lower", json={"topic_key": "padel"}).status_code == 200
    rest_resp = c.post("/api/community/profile/usage/restore", json={"topic_key": "padel"})
    assert rest_resp.status_code == 200
    assert rest_resp.json()["entries"][0]["lowered"] is False
    assert rest_resp.json()["entries"][0]["weight"] >= SURFACE_THRESHOLD

    # Settings toggle off disables context_aware_enabled and clears ephemeral context.
    c.post("/api/community/context/heartbeat", json={"area_coarse": "DIFC", "user_state": "walking"})
    assert c.get("/api/community/context/current").json()["active"] is True
    off = c.put("/api/community/profile/usage/settings", json={"context_aware_enabled": False})
    assert off.status_code == 200 and off.json()["context_aware_enabled"] is False
    cur_after = c.get("/api/community/context/current").json()
    assert cur_after["context_aware_enabled"] is False
    assert cur_after["active"] is False
