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
