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
    purge_owner_community_data,
    record_interaction_event,
    router as context_router,
    set_context_aware_enabled,
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
    # Exact centroid tests across Dubai districts (helper only — lat/lng never cross API).
    for district, (lat, lng) in DUBAI_AREAS.items():
        assert snap_coordinates_to_area(lat, lng) == district
    assert snap_coordinates_to_area(25.212345, 55.280987) == "DIFC"

    # S3: raw lat/lng rejected at the boundary (extra=forbid).
    assert c.post(
        "/api/community/context/heartbeat",
        json={
            "lat": 25.212345,
            "lng": 55.280987,
            "device_class": "mobile_ios",
            "user_state": "walking",
            "confidence": 0.88,
            "source": "expo_sensors",
        },
    ).status_code == 422
    assert c.post(
        "/api/community/events",
        json={
            "post_id": "p1",
            "topic_key": "padel",
            "event_type": "upvote",
            "lat": 25.0809,
            "lng": 55.1401,
            "session_id": "s1",
            "dedupe_key": "d1",
        },
    ).status_code == 422

    # Coarse area only.
    set_context_aware_enabled(store, owner, True)
    resp = c.post(
        "/api/community/context/heartbeat",
        json={
            "area_coarse": "DIFC",
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

    ev_resp = c.post(
        "/api/community/events",
        json={
            "post_id": "p1",
            "topic_key": "padel",
            "event_type": "upvote",
            "area_coarse": "Dubai Marina",
            "device_class": "mobile_ios",
            "user_state": "running",
            "session_id": "s1",
            "dedupe_key": "d1",
        },
    )
    assert ev_resp.status_code == 200, ev_resp.text
    # Echo may show request area; SQL columns stay unknown when context fields are ephemeral.
    assert ev_resp.json()["event"]["area_coarse"] in ("Dubai Marina", "unknown")

    cur = c.get("/api/community/context/current").json()
    cur_ctx = cur.get("context") or {}
    assert "lat" not in cur_ctx and "lng" not in cur_ctx
    dumped_ctx = json.dumps(cur)
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
    # D22 / Rule 8+9: SQL never permanently stores real user_state or area_coarse values.
    ev_dump = json.dumps(
        store.db.execute(
            "SELECT area_coarse, user_state FROM cm_interaction_events WHERE owner=?",
            (owner,),
        ).fetchall()
    )
    assert "walking" not in ev_dump and "running" not in ev_dump and "driving" not in ev_dump and "sitting" not in ev_dump
    assert "Dubai Marina" not in ev_dump
    assert '"unknown"' in ev_dump or "unknown" in ev_dump

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

    # Snapshot evidence counters before D19b recall (Rule 9: must not be fabricated).
    before = store.db.execute(
        "SELECT distinct_sessions, evidence_count FROM cm_usage_profile WHERE owner=? AND topic_key='padel'",
        (owner,),
    ).fetchone()
    assert before is not None
    sessions_before, evidence_before = int(before[0]), int(before[1])

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
    assert int(recalled_entry["distinct_sessions"]) == sessions_before
    assert int(recalled_entry["evidence_count"]) == evidence_before
    after = store.db.execute(
        "SELECT distinct_sessions, evidence_count, lowered_at FROM cm_usage_profile WHERE owner=? AND topic_key='padel'",
        (owner,),
    ).fetchone()
    assert int(after[0]) == sessions_before
    assert int(after[1]) == evidence_before
    assert after[2] is None

    # Lower again, then test explicit Restore endpoint.
    assert c.post("/api/community/profile/usage/lower", json={"topic_key": "padel"}).status_code == 200
    rest_resp = c.post("/api/community/profile/usage/restore", json={"topic_key": "padel"})
    assert rest_resp.status_code == 200
    assert rest_resp.json()["entries"][0]["lowered"] is False
    assert rest_resp.json()["entries"][0]["weight"] >= SURFACE_THRESHOLD

    # D22: context-aware is opt-in (default 0). Opt in, then toggle off clears ephemeral context.
    on = c.put("/api/community/profile/usage/settings", json={"context_aware_enabled": True})
    assert on.status_code == 200 and on.json()["context_aware_enabled"] is True
    c.post("/api/community/context/heartbeat", json={"area_coarse": "DIFC", "user_state": "walking"})
    assert c.get("/api/community/context/current").json()["active"] is True
    off = c.put("/api/community/profile/usage/settings", json={"context_aware_enabled": False})
    assert off.status_code == 200 and off.json()["context_aware_enabled"] is False
    cur_after = c.get("/api/community/context/current").json()
    assert cur_after["context_aware_enabled"] is False
    assert cur_after["active"] is False


def test_d19b_recall_exact_topic_match_only(ctx_client):
    """B4: recalling 'art' must not boost substring neighbours like 'party'."""
    c, store, owner, _bridge, _fake = ctx_client
    for topic, sess in (("art", "s_art"), ("party", "s_party"), ("smart-home", "s_home")):
        assert c.post(
            "/api/community/events",
            json={
                "post_id": f"p_{topic}",
                "topic_key": topic,
                "event_type": "upvote",
                "area_coarse": "DIFC",
                "session_id": sess,
                "dedupe_key": f"d_{topic}_1",
            },
        ).status_code == 200
        assert c.post(
            "/api/community/events",
            json={
                "post_id": f"p_{topic}_2",
                "topic_key": topic,
                "event_type": "bookmark",
                "area_coarse": "DIFC",
                "session_id": f"{sess}_b",
                "dedupe_key": f"d_{topic}_2",
            },
        ).status_code == 200
        assert c.post("/api/community/profile/usage/lower", json={"topic_key": topic}).status_code == 200

    party_before = store.db.execute(
        "SELECT positive_score, lowered_at, distinct_sessions, evidence_count FROM cm_usage_profile WHERE owner=? AND topic_key='party'",
        (owner,),
    ).fetchone()
    assert party_before is not None and party_before[1] is not None

    recall = c.post("/api/community/profile/usage/recall", json={"topic_key": "art"})
    assert recall.status_code == 200, recall.text
    body = recall.json()
    assert body["count"] >= 1
    assert all(e["topic_key"] == "art" for e in body["recalled"])
    assert "party" not in body.get("boosted_topics", [])
    assert "smart-home" not in body.get("boosted_topics", [])

    party_after = store.db.execute(
        "SELECT positive_score, lowered_at, distinct_sessions, evidence_count FROM cm_usage_profile WHERE owner=? AND topic_key='party'",
        (owner,),
    ).fetchone()
    assert party_after[0] == party_before[0]
    assert party_after[1] is not None  # still lowered
    assert int(party_after[2]) == int(party_before[2])
    assert int(party_after[3]) == int(party_before[3])

    art_after = store.db.execute(
        "SELECT lowered_at, distinct_sessions, evidence_count FROM cm_usage_profile WHERE owner=? AND topic_key='art'",
        (owner,),
    ).fetchone()
    assert art_after[0] is None
    # Evidence counters untouched by recall.
    assert int(art_after[1]) >= 1
    assert int(art_after[2]) >= 1


def test_purge_owner_community_data_clears_sql_and_ephemeral(ctx_client, monkeypatch):
    c, store, owner, _bridge, _fake = ctx_client
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:63999/0")
    set_context_aware_enabled(store, owner, True)
    set_ephemeral_context(owner, {"area_coarse": "JLT", "user_state": "walking"}, ttl_seconds=600)
    assert get_ephemeral_context(owner) is not None
    assert c.post(
        "/api/community/events",
        json={"post_id": "p_purge", "topic_key": "padel", "event_type": "upvote", "session_id": "s_purge"},
    ).status_code == 200
    assert store.db.execute("SELECT COUNT(*) FROM cm_interaction_events WHERE owner=?", (owner,)).fetchone()[0] >= 1
    assert store.db.execute("SELECT COUNT(*) FROM cm_usage_profile WHERE owner=?", (owner,)).fetchone()[0] >= 1
    assert store.db.execute("SELECT COUNT(*) FROM cm_usage_settings WHERE owner=?", (owner,)).fetchone()[0] >= 1

    out = purge_owner_community_data(owner, store=store)
    assert out["purged"] is True
    assert get_ephemeral_context(owner) is None
    assert store.db.execute("SELECT COUNT(*) FROM cm_interaction_events WHERE owner=?", (owner,)).fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM cm_usage_profile WHERE owner=?", (owner,)).fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM cm_usage_settings WHERE owner=?", (owner,)).fetchone()[0] == 0


def test_context_aware_default_opt_in_is_off(ctx_client):
    c, store, owner, _bridge, _fake = ctx_client
    from app.community.context_profile import setup_context_profile

    setup_context_profile(store)
    # Fresh owner with no settings row → D22 default off.
    assert store.db.execute("SELECT COUNT(*) FROM cm_usage_settings WHERE owner=?", (owner,)).fetchone()[0] == 0
    hb = c.post("/api/community/context/heartbeat", json={"area_coarse": "DIFC", "user_state": "walking"})
    assert hb.status_code == 200, hb.text
    body = hb.json()
    assert body["context_aware_enabled"] is False
    assert body["stored"] is False
    assert c.get("/api/community/context/current").json()["active"] is False
