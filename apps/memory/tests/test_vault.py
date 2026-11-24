"""Tests for FastAPI Vault, Quests, Timeline, Why, and Ops endpoints (WP-B)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from temporal_memory.api import export_md, ops, vault
from temporal_memory.api.vault import AuthContext
from tests.fixtures.fake_store import FakeGraphStore


def _make_client(store: FakeGraphStore) -> TestClient:
    tokens = {
        "admin-tok": AuthContext(role="admin", owner=None, token_id="t-admin"),
        "karim-tok": AuthContext(role="owner-device", owner="karim", token_id="t-karim"),
        "other-tok": AuthContext(role="owner-device", owner="layla", token_id="t-layla"),
        "worker-tok": AuthContext(role="worker", owner=None, token_id="t-worker"),
    }
    vault.configure(store=store, auth_verifier=lambda tok: tokens.get(tok or ""))
    app = FastAPI()
    app.include_router(vault.router)
    app.include_router(export_md.router)
    app.include_router(ops.router)
    return TestClient(app)


def test_vault_quests_timeline_why_happy_paths():
    st = FakeGraphStore.from_karim_slice()
    client = _make_client(st)
    hdr = {"Authorization": "Bearer karim-tok"}

    subj_res = client.get("/v1/owners/karim/vault/subjects", headers=hdr)
    assert subj_res.status_code == 200
    body = subj_res.json()
    assert body["provenance"] and body["as_of"] and body["demo_data"] is False
    assert body["total_facts"] >= 9

    ppl = client.get("/v1/owners/karim/vault/people", headers=hdr).json()
    farouk = next(p for p in ppl["people"] if p["name"] == "Omar Farouk")
    assert farouk["relation_to_user"] == "friend"
    assert farouk["closeness_tier"] == "T1"
    assert any(s["role"] == "groom" for s in farouk["subjects"])

    quests = client.get("/v1/owners/karim/quests", headers=hdr).json()
    assert quests["quests"][0]["milestones"][0]["title"] == "Ship Raseef beta to testers"
    assert quests["quests"][0]["counts"]["done"] == 1

    why_hook = client.get("/v1/owners/karim/why/f004", headers=hdr).json()
    assert why_hook["model"] == "your Claude"
    assert why_hook["cost_badge"] == "processed on your Claude · $0 app cost"
    assert why_hook["evidence"][0]["id"] == "g081"

    why_cloud = client.get("/v1/owners/karim/why/f001", headers=hdr).json()
    assert why_cloud["model"] == "claude-haiku-5-5"


def test_demo_owner_flag_and_auth_403_and_forgotten_404():
    st_demo = FakeGraphStore.from_karim_slice(owner_override="demo", owner_kind="demo")
    client = _make_client(st_demo)

    # Cross-owner read with owner-device token is 403
    r403 = client.get("/v1/owners/demo/vault/subjects", headers={"Authorization": "Bearer karim-tok"})
    assert r403.status_code == 403

    # Missing token is 401
    r401 = client.get("/v1/owners/demo/vault/subjects")
    assert r401.status_code == 401

    # Demo flag propagates across endpoints
    tl = client.get("/v1/owners/demo/timeline", headers={"Authorization": "Bearer admin-tok"}).json()
    assert tl["demo_data"] is True
    assert tl["items"][0]["demo_data"] is True

    # Forgotten fact disappears from timeline, subjects, and why returns 404
    st_demo.forget_source("demo", ["g081"])
    tl_after = client.get("/v1/owners/demo/timeline", headers={"Authorization": "Bearer admin-tok"}).json()
    assert not any(it["id"] == "f004" for it in tl_after["items"])
    why_404 = client.get("/v1/owners/demo/why/f004", headers={"Authorization": "Bearer admin-tok"})
    assert why_404.status_code == 404


def _onboarding_store(records, facts=(), subjects=()):
    from temporal_memory.models import Fact, Owner, Record, Subject

    st = FakeGraphStore()
    st.owners["karim"] = Owner(id="karim", label="Karim", kind="simulated",
                                display_name="Karim Haddad")
    for rid, source in records:
        st.records["karim"][rid] = Record(id=rid, owner="karim", source=source,
                                           at="2026-11-20T10:00:00Z", author="x", text="synthetic")
    for item in subjects:
        st.subjects["karim"].append(Subject(**item))
    for item in facts:
        st.facts["karim"].append(Fact(**item))
    return st


_HDR = {"Authorization": "Bearer karim-tok"}


def test_onboarding_mobile_only_exactly_36():
    st = _onboarding_store([("g1", "gmail"), ("c1", "calendar"), ("y1", "youtube:api")])
    body = _make_client(st).get("/v1/owners/karim/onboarding-status", headers=_HDR).json()
    assert body["completeness_pct"] == 36
    assert body["breakdown"] == {"gmail": 14, "calendar": 10, "youtube_api": 12,
                                  "whatsapp": 0, "youtube_history": 0, "browser": 0,
                                  "agent_sessions": 0}
    assert body["sources_present"] == ["gmail", "calendar", "youtube_api"]
    assert body["next_recommended_action"] == "install_desktop_and_sync"


def test_onboarding_desktop_73_one_desktop_and_full_100():
    base = [("g1", "gmail"), ("c1", "calendar"), ("y1", "youtube:api")]
    st = _onboarding_store(base + [("b1", "browser"), ("a1", "agent:claude-code")])
    body = _make_client(st).get("/v1/owners/karim/onboarding-status", headers=_HDR).json()
    assert body["completeness_pct"] == 73
    assert body["next_recommended_action"] == "add_whatsapp_or_youtube_history"

    st_one = _onboarding_store(base + [("b1", "browser")])
    one = _make_client(st_one).get("/v1/owners/karim/onboarding-status", headers=_HDR).json()
    assert one["completeness_pct"] == 54
    assert one["next_recommended_action"] == "enable_browser_or_sessions"

    st_full = _onboarding_store(base + [("b1", "browser"), ("a1", "agent:codex"),
                                        ("w1", "whatsapp:work"), ("h1", "youtube:interests")])
    full = _make_client(st_full).get("/v1/owners/karim/onboarding-status", headers=_HDR).json()
    assert full["completeness_pct"] == 100
    assert full["next_recommended_action"] == "complete"
    assert full["analytics"]["by_source"]["whatsapp"]["records"] == 1
    assert full["analytics"]["by_source"]["agent:codex"]["records"] == 1


def test_onboarding_known_so_far_by_theme_and_rising_21d():
    subjects = [
        {"id": "th-career", "owner": "karim", "path": "career", "label": "Career", "kind": "theme"},
        {"id": "s-jobs", "owner": "karim", "path": "career/jobs", "label": "Jobs", "kind": "topic", "parent_id": "th-career"},
    ]
    facts = [
        {"id": "f-new", "owner": "karim", "text": "Interview at QamarTech", "subject_id": "s-jobs",
         "valid_from": "2026-11-20", "evidence": ["g1"], "provenance": "user_supplied"},
        {"id": "f-mid", "owner": "karim", "text": "Portfolio updated", "subject_id": "s-jobs",
         "valid_from": "2026-11-10", "evidence": ["g1"]},
        {"id": "f-old", "owner": "karim", "text": "Old application", "subject_id": "s-jobs",
         "valid_from": "2026-10-20", "evidence": ["g1"]},
        {"id": "f-hyp", "owner": "karim", "text": "SENTINEL_HYPOTHESIS", "subject_id": "s-jobs",
         "valid_from": "2026-11-21", "evidence": ["g1"], "status": "hypothesis"},
    ]
    st = _onboarding_store([("g1", "gmail")], facts=facts, subjects=subjects)
    body = _make_client(st).get(
        "/v1/owners/karim/onboarding-status?as_of=2026-11-24", headers=_HDR).json()
    career = body["analytics"]["by_theme"]["Career"]
    assert set(body["analytics"]["by_theme"]) >= {
        "Career", "Learning", "Projects", "People & family", "Events", "Home & money", "Travel"}
    assert career["recent_21d"] == 2 and career["baseline_21d"] == 1
    assert career["rising_21d"] is True and "Career" in body["analytics"]["rising_21d"]
    known = body["known_so_far"]["Career"]
    assert known[0]["id"] == "f-new" and known[0]["evidence"] == ["g1"]
    assert "SENTINEL_HYPOTHESIS" not in str(body["known_so_far"])
    assert body["analytics"]["by_source"]["gmail"] == {"records": 1, "facts": 3}


def test_onboarding_privacy_shield_counts_only_and_compute_saved():
    import json as _json

    st = FakeGraphStore.from_karim_slice()
    st.quarantine["karim"] = {"health": 2, "credential": 1}
    body = _make_client(st).get("/v1/owners/karim/onboarding-status", headers=_HDR).json()
    shield = body["analytics"]["privacy_shield"]
    assert shield == {"held_back_total": 3, "by_category": {"credential": 1, "health": 2}}
    assert "text" not in _json.dumps(shield) and "evidence" not in _json.dumps(shield)
    saved = body["analytics"]["compute_saved"]
    assert saved["tokens_in"] == 1_000_000 and saved["tokens_out"] == 200_000
    assert saved["demo_cost_saved_usd"] == 2.0
    assert saved["owner_hook_facts"] >= 1

    # Cross-owner token cannot read the status.
    res = _make_client(st).get("/v1/owners/karim/onboarding-status",
                               headers={"Authorization": "Bearer other-tok"})
    assert res.status_code == 403


def test_ops_memory_admin_only_and_cost_saved():
    st = FakeGraphStore.from_karim_slice()
    client = _make_client(st)

    # Non-admin (owner-device or worker) rejected with 403
    assert client.get("/v1/ops/memory", headers={"Authorization": "Bearer karim-tok"}).status_code == 403
    assert client.get("/v1/ops/memory", headers={"Authorization": "Bearer worker-tok"}).status_code == 403

    res = client.get("/v1/ops/memory", headers={"Authorization": "Bearer admin-tok"})
    assert res.status_code == 200
    data = res.json()
    assert data["queue_depth_by_priority"]["P0"] == 1
    assert data["queue_depth_by_priority"]["P1"] == 1
    assert "claude-haiku-5-5" in data["workers_online_by_model"]
    assert data["attempts_by_verdict_per_model"]["claude-code-hook"]["applied"] == 1
    # att-hook-1: 1M in * $1/1M + 200k out * $5/1M = $2.00 saved
    assert data["demo_cost_saved_usd"] == 2.0
    assert data["cost_per_owner_per_week"]["karim"]["2026-W43"] == 0.01
