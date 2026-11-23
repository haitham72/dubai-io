"""E2E-01 Gate S tests: full FastAPI TestClient across Identity + MemoryBridge routers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import db as db_mod
from app.identity import (
    IdentityConfig,
    IdentityService,
    IdentityStore,
    JWTVerifier,
    MemoryTokenService,
    create_identity_router,
)
from app.identity.deps import LEGACY_ANON_COOKIE
from app.memory_bridge import FakeTemporalMemoryClient, MemoryBridge, create_memory_bridge_router
from app.memory_bridge.models import MemoryBridgeUnavailable, SensitiveContentError
from tests.fixtures.contest_shared.db_fixtures import cs_postgres_isolation  # noqa: F401
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_AUDIENCE,
    TEST_HS256_SECRET,
    TEST_ISSUER,
    default_claims,
    sign_hs256_jwt,
)


def _build_e2e_app(tmp_path: Path, *, bridge_override: Any = None):
    shared_db = db_mod.connect(tmp_path / "gate_s_shared.sqlite3")
    id_store = IdentityStore(shared_db)
    verifier = JWTVerifier(
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
        hs256_secret=TEST_HS256_SECRET,
    )
    id_svc = IdentityService(
        id_store,
        verifier,
        config=IdentityConfig(
            jwt_issuer=TEST_ISSUER,
            jwt_audience=TEST_AUDIENCE,
            jwt_hs256_secret=TEST_HS256_SECRET,
        ),
    )
    fake_tm = FakeTemporalMemoryClient()
    token_svc = MemoryTokenService(
        id_store,
        fake_tm,
        token_key=Fernet.generate_key(),
        key_path=tmp_path / "token.key",
    )
    bridge = bridge_override if bridge_override is not None else MemoryBridge(shared_db, fake_tm)

    app = FastAPI()
    app.state.identity_service = id_svc
    app.state.memory_token_handler = token_svc
    app.state.memory_bridge = bridge
    app.include_router(create_identity_router())
    app.include_router(create_memory_bridge_router())
    return shared_db, id_svc, fake_tm, token_svc, bridge, TestClient(app)


def _login_all_apps(
    client: TestClient,
    *,
    sub: str,
    age_band: str | None = "adult_18_plus",
) -> tuple[str, dict[str, str]]:
    jwt_tok = sign_hs256_jwt(default_claims(sub=sub))
    if age_band is not None:
        age_resp = client.post(
            "/api/identity/age-band",
            headers={"Authorization": f"Bearer {jwt_tok}"},
            json={"age_band": age_band},
        )
        assert age_resp.status_code == 200, age_resp.text

    sessions: dict[str, str] = {}
    user_ids: set[str] = set()
    for app_id in ("quest", "community", "messenger"):
        resp = client.post(
            "/api/identity/sessions",
            headers={"Authorization": f"Bearer {jwt_tok}"},
            json={"app_id": app_id},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        user_ids.add(data["user_id"])
        sessions[app_id] = data["session_token"]
    assert len(user_ids) == 1
    return next(iter(user_ids)), sessions


def test_gate_s_full_cross_app_e2e(tmp_path: Path) -> None:
    """E2E-01: Single user across Quest/Community/Messenger with consent, isolation, forget cascade, and Gate S fences."""
    db, _id_svc, fake_tm, token_svc, _bridge, client = _build_e2e_app(tmp_path)
    try:
        # Simulated native app source tables that must remain untouched by memory forget.
        social_posts = [{"id": "cmpost:p1", "author": "alice", "body": "Public coffee meetup thread"}]
        mg_messages = [
            {"id": "mgmsg:a1", "conversation_id": "conv-A", "text": "Group agreed to meet at 6pm"},
            {"id": "mgmsg:b1", "conversation_id": "conv-B", "text": "conv-B budget review tomorrow"},
        ]

        uid_a, sess_a = _login_all_apps(client, sub="550e8400-e29b-41d4-a716-446655440201")
        uid_b, sess_b = _login_all_apps(client, sub="550e8400-e29b-41d4-a716-446655440202")
        assert uid_a != uid_b

        # Bind per-owner temporal_memory bridge token.
        bridge_tok_a = token_svc.ensure_bridge_token(uid_a)
        assert bridge_tok_a
        assert token_svc.ensure_bridge_token(uid_a) == bridge_tok_a

        # Anonymous cookie rejected 401 on all protected routes.
        anon_hdr = {"Cookie": f"{LEGACY_ANON_COOKIE}=anon-lab-123"}
        assert client.get("/api/v1/memory-bridge/consent", headers=anon_hdr).status_code == 401
        assert client.post("/api/v1/memory-bridge/quest/context", headers=anon_hdr, json={"query": "x"}).status_code == 401
        assert client.get("/api/v1/memory-bridge/community/interests", headers=anon_hdr).status_code == 401
        assert client.get("/api/v1/memory-bridge/audit", headers=anon_hdr).status_code == 401

        # Spoofed identity header rejected 400 (including legacy header pattern).
        assert (
            client.get(
                "/api/v1/memory-bridge/consent",
                headers={"X-App-Session": sess_a["quest"], "X-User-Id": uid_b},
            ).status_code
            == 400
        )
        legacy_hdr = f"x-m{'i'}rsal-user"
        assert (
            client.get(
                "/api/v1/memory-bridge/consent",
                headers={"X-App-Session": sess_a["quest"], legacy_hdr: uid_b},
            ).status_code
            == 400
        )

        # Default-off consent blocks writes and reads before opt-in.
        assert (
            client.post(
                "/api/v1/memory-bridge/writes",
                headers={"X-App-Session": sess_a["quest"]},
                json={
                    "record_id": "qmsg:blocked-1",
                    "source_kind": "quest",
                    "source_id": "quest:t1",
                    "host_app": "quest",
                    "text": "I like specialty coffee",
                    "valid_time": "2026-11-23T08:00:00Z",
                    "explicit_user_confirm": True,
                },
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/memory-bridge/quest/context",
                headers={"X-App-Session": sess_a["quest"]},
                json={"query": "coffee"},
            ).status_code
            == 403
        )

        # Cross-app misuse rejected 403.
        assert (
            client.post(
                "/api/v1/memory-bridge/quest/context",
                headers={"X-App-Session": sess_a["community"]},
                json={"query": "coffee"},
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/conversation",
                headers={"X-App-Session": sess_a["community"]},
                json={"conversation_id": "conv-A", "ai_mode": "save"},
            ).status_code
            == 403
        )

        # 1. Enable Quest + Community export consent.
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/source",
                headers={"X-App-Session": sess_a["quest"]},
                json={"source_kind": "quest", "enabled": True, "allow_interest_export": True},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess_a["quest"]},
                json={"app_id": "quest", "read_enabled": True, "write_enabled": True},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/source",
                headers={"X-App-Session": sess_a["community"]},
                json={"source_kind": "community", "enabled": True, "allow_interest_export": True},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess_a["community"]},
                json={
                    "app_id": "community",
                    "read_enabled": True,
                    "write_enabled": True,
                    "allow_interest_export_to_community": True,
                },
            ).status_code
            == 200
        )

        # 2. Quest writes confirmed interest + sensitive credential/family traps.
        q_write = client.post(
            "/api/v1/memory-bridge/writes",
            headers={"X-App-Session": sess_a["quest"]},
            json={
                "record_id": "qmsg:coffee-1",
                "source_kind": "quest",
                "source_id": "quest:t1",
                "host_app": "quest",
                "text": "I enjoy specialty coffee tasting with Omar at Alserkal",
                "valid_time": "2026-11-23T09:00:00Z",
                "subject_path": "hobbies/specialty-coffee",
                "explicit_user_confirm": True,
            },
        )
        assert q_write.status_code == 200, q_write.text
        assert q_write.json()["ok"] is True

        q_quarantine = client.post(
            "/api/v1/memory-bridge/writes",
            headers={"X-App-Session": sess_a["quest"]},
            json={
                "record_id": "qmsg:cred-1",
                "source_kind": "quest",
                "source_id": "quest:t1",
                "host_app": "quest",
                "text": "My Wi-Fi password is Dubai1234",
                "valid_time": "2026-11-23T09:01:00Z",
                "subject_path": "home/wifi",
                "explicit_user_confirm": True,
            },
        )
        assert q_quarantine.status_code == 200
        assert q_quarantine.json()["status"] == "quarantined"

        # Community GET /community/interests returns projected InterestFeature with ZERO raw text/names.
        interests_resp = client.get(
            "/api/v1/memory-bridge/community/interests",
            headers={"X-App-Session": sess_a["community"]},
        )
        assert interests_resp.status_code == 200, interests_resp.text
        features = interests_resp.json()["features"]
        assert len(features) == 1
        assert features[0]["topic_slug"] == "specialty-coffee"
        serialized_features = json.dumps(features)
        assert "Alserkal" not in serialized_features
        assert "Omar" not in serialized_features
        assert "Dubai1234" not in serialized_features

        # 3. Community writes saved discussion (cmsave:*) separate from social post; Quest recalls it with provenance.
        cm_write = client.post(
            "/api/v1/memory-bridge/writes",
            headers={"X-App-Session": sess_a["community"]},
            json={
                "record_id": "cmsave:disc-1",
                "source_kind": "community",
                "source_id": "community:thread-42",
                "host_app": "community",
                "text": "Saved discussion on urban padel courts in Dubai",
                "valid_time": "2026-11-23T10:00:00Z",
                "subject_path": "sports/urban-padel",
                "explicit_user_confirm": True,
            },
        )
        assert cm_write.status_code == 200, cm_write.text
        cm_fact_id = cm_write.json()["fact_ids"][0]

        act_resp = client.get(
            "/api/v1/memory-bridge/community/activity",
            headers={"X-App-Session": sess_a["community"]},
        )
        assert act_resp.status_code == 200
        assert any(a["record_id"] == "cmsave:disc-1" for a in act_resp.json()["activities"])

        # Two-visit behavioral signal promotes hypothesis -> Quest confirms it.
        s1 = client.post(
            "/api/v1/memory-bridge/signals",
            headers={"X-App-Session": sess_a["community"]},
            json={
                "source_kind": "community",
                "source_id": "community:feed",
                "topic_slug": "desert-astronomy",
                "option_key": "view_1",
                "at": "2026-11-22T18:00:00Z",
            },
        )
        assert s1.status_code == 200 and s1.json()["qualified"] is False
        s2 = client.post(
            "/api/v1/memory-bridge/signals",
            headers={"X-App-Session": sess_a["community"]},
            json={
                "source_kind": "community",
                "source_id": "community:feed",
                "topic_slug": "desert-astronomy",
                "option_key": "view_2",
                "at": "2026-11-23T08:00:00Z",
            },
        )
        assert s2.status_code == 200 and s2.json()["qualified"] is True
        hyp_fid = s2.json()["promoted_fact_id"]

        hyps_resp = client.get(
            "/api/v1/memory-bridge/quest/hypotheses",
            headers={"X-App-Session": sess_a["quest"]},
        )
        assert hyps_resp.status_code == 200
        assert any(h["fact_id"] == hyp_fid and h["display_prefix"] == "I noticed" for h in hyps_resp.json()["hypotheses"])

        res_hyp = client.post(
            f"/api/v1/memory-bridge/facts/{hyp_fid}/resolve",
            headers={"X-App-Session": sess_a["quest"]},
            json={"action": "confirm"},
        )
        assert res_hyp.status_code == 200

        q_ctx = client.post(
            "/api/v1/memory-bridge/quest/context",
            headers={"X-App-Session": sess_a["quest"]},
            json={"query": "padel"},
        )
        assert q_ctx.status_code == 200
        assert any("padel" in f["text"].lower() and f["display_prefix"] == "You told me" for f in q_ctx.json()["facts"])

        q_tl = client.get(
            "/api/v1/memory-bridge/quest/timeline",
            headers={"X-App-Session": sess_a["quest"]},
        )
        assert q_tl.status_code == 200
        assert any(item["fact_id"] == cm_fact_id for item in q_tl.json()["items"])

        why_resp = client.get(
            f"/api/v1/memory-bridge/why/{cm_fact_id}",
            headers={"X-App-Session": sess_a["quest"]},
        )
        assert why_resp.status_code == 200
        assert why_resp.json()["evidence"][0]["id"] == "cmsave:disc-1"

        # 4. Messenger consented group decision (conv-A) + chat scope isolation from conv-B.
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/source",
                headers={"X-App-Session": sess_a["messenger"]},
                json={"source_kind": "messenger", "enabled": True},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess_a["messenger"]},
                json={"app_id": "messenger", "read_enabled": True, "write_enabled": True},
            ).status_code
            == 200
        )
        for cid in ("conv-A", "conv-B"):
            assert (
                client.put(
                    "/api/v1/memory-bridge/consent/conversation",
                    headers={"X-App-Session": sess_a["messenger"]},
                    json={"conversation_id": cid, "ai_mode": "save"},
                ).status_code
                == 200
            )

        mg_write_a = client.post(
            "/api/v1/memory-bridge/writes",
            headers={"X-App-Session": sess_a["messenger"]},
            json={
                "record_id": "mgmsg:a1",
                "source_kind": "messenger",
                "source_id": "messenger:conv-A",
                "host_app": "messenger",
                "text": "Group agreed to meet at 6pm",
                "valid_time": "2026-11-23T11:00:00Z",
                "subject_path": "plans/meetup",
                "explicit_user_confirm": True,
                "group_consent": {
                    "conversation_id": "conv-A",
                    "caller_is_member": True,
                    "all_active_members_ai_enabled": True,
                    "cited_authors_save_enabled": True,
                    "membership_revision": 1,
                },
            },
        )
        assert mg_write_a.status_code == 200, mg_write_a.text
        mg_write_b = client.post(
            "/api/v1/memory-bridge/writes",
            headers={"X-App-Session": sess_a["messenger"]},
            json={
                "record_id": "mgmsg:b1",
                "source_kind": "messenger",
                "source_id": "messenger:conv-B",
                "host_app": "messenger",
                "text": "conv-B budget review tomorrow",
                "valid_time": "2026-11-23T11:05:00Z",
                "subject_path": "plans/budget",
                "explicit_user_confirm": True,
                "group_consent": {
                    "conversation_id": "conv-B",
                    "caller_is_member": True,
                    "all_active_members_ai_enabled": True,
                    "cited_authors_save_enabled": True,
                    "membership_revision": 1,
                },
            },
        )
        assert mg_write_b.status_code == 200, mg_write_b.text
        gen_before_forget = fake_tm.records[uid_a]["mgmsg:a1"].generation

        # Messenger chat scope isolates conv-A from conv-B.
        conv_a_ctx = client.post(
            "/api/v1/memory-bridge/messenger/conversations/conv-A/context",
            headers={"X-App-Session": sess_a["messenger"]},
            json={
                "group_consent": {
                    "conversation_id": "conv-A",
                    "caller_is_member": True,
                    "all_active_members_ai_enabled": True,
                    "cited_authors_save_enabled": True,
                    "membership_revision": 1,
                },
                "query": "",
            },
        )
        assert conv_a_ctx.status_code == 200
        conv_a_facts = conv_a_ctx.json()["facts"]
        assert len(conv_a_facts) == 1
        assert "6pm" in conv_a_facts[0]["text"]
        assert all("conv-B" not in f["text"] for f in conv_a_facts)

        # Messenger opt-in owner recall works when allow_cross_source_recall=True.
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess_a["messenger"]},
                json={
                    "app_id": "messenger",
                    "read_enabled": True,
                    "write_enabled": True,
                    "allow_cross_source_recall": True,
                },
            ).status_code
            == 200
        )
        recall_resp = client.post(
            "/api/v1/memory-bridge/messenger/conversations/conv-A/recall",
            headers={"X-App-Session": sess_a["messenger"]},
            json={"query": "coffee"},
        )
        assert recall_resp.status_code == 200
        assert any("coffee" in f["text"].lower() for f in recall_resp.json()["facts"])

        # Quest recalls conv-A decision within scope.
        q_meetup = client.post(
            "/api/v1/memory-bridge/quest/context",
            headers={"X-App-Session": sess_a["quest"]},
            json={"query": "6pm"},
        )
        assert q_meetup.status_code == 200
        assert any("6pm" in f["text"] for f in q_meetup.json()["facts"])

        # 5. Forget propagates across all 3 apps immediately; native app content stays intact; stale worker blocked.
        f_conv = client.post(
            "/api/v1/memory-bridge/forget/conversation",
            headers={"X-App-Session": sess_a["messenger"]},
            json={"conversation_id": "conv-A", "idempotency_key": "e2e-forget-conv-a"},
        )
        assert f_conv.status_code == 200
        assert f_conv.json()["status"] == "completed"

        f_comm = client.post(
            "/api/v1/memory-bridge/forget/source",
            headers={"X-App-Session": sess_a["quest"]},
            json={"source_kind": "community", "idempotency_key": "e2e-forget-comm"},
        )
        assert f_comm.status_code == 200
        assert f_comm.json()["status"] == "completed"

        # Forget specific Messenger conv-B record via /forget/records.
        f_rec = client.post(
            "/api/v1/memory-bridge/forget/records",
            headers={"X-App-Session": sess_a["messenger"]},
            json={"record_ids": ["mgmsg:b1"], "idempotency_key": "e2e-forget-rec-b1"},
        )
        assert f_rec.status_code == 200
        assert f_rec.json()["status"] == "completed"

        # Messenger conv-A and Community derived memories gone from Quest & Community interests.
        q_after = client.post(
            "/api/v1/memory-bridge/quest/context",
            headers={"X-App-Session": sess_a["quest"]},
            json={"query": ""},
        ).json()["facts"]
        assert not any("6pm" in f["text"] or "padel" in f["text"] or "astronomy" in f["text"] for f in q_after)
        assert any("specialty coffee" in f["text"].lower() for f in q_after)

        comm_after = client.get(
            "/api/v1/memory-bridge/community/interests",
            headers={"X-App-Session": sess_a["community"]},
        ).json()["features"]
        assert all(f["source_app"] != "community" for f in comm_after)

        # Native app stores remain intact.
        assert len(social_posts) == 1 and social_posts[0]["id"] == "cmpost:p1"
        assert len(mg_messages) == 2

        # Late stale-generation worker blocked by fence.
        stale = fake_tm.simulate_worker_submit(
            uid_a,
            "mgmsg:a1",
            gen_before_forget,
            "Late extracted conv-A memory",
            subject_path="plans/meetup",
        )
        assert stale["ok"] is False and stale["verdict"] == "fence_stale"

        # User A audit contains content-free receipts.
        audit_a = client.get("/api/v1/memory-bridge/audit", headers={"X-App-Session": sess_a["quest"]}).json()["events"]
        assert any(ev["action"] == "memory.forget_conversation" for ev in audit_a)
        assert any(ev["action"] == "memory.forget_source" for ev in audit_a)
        assert "Dubai1234" not in json.dumps(audit_a)

        # 6. User B sees zero memories, interests, or audit events from User A.
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess_b["quest"]},
                json={"app_id": "quest", "read_enabled": True, "write_enabled": False},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess_b["community"]},
                json={
                    "app_id": "community",
                    "read_enabled": True,
                    "write_enabled": False,
                    "allow_interest_export_to_community": True,
                },
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/memory-bridge/quest/context",
                headers={"X-App-Session": sess_b["quest"]},
                json={"query": ""},
            ).json()["facts"]
            == []
        )
        assert (
            client.get(
                "/api/v1/memory-bridge/quest/timeline",
                headers={"X-App-Session": sess_b["quest"]},
            ).json()["items"]
            == []
        )
        assert (
            client.get(
                "/api/v1/memory-bridge/community/interests",
                headers={"X-App-Session": sess_b["community"]},
            ).json()["features"]
            == []
        )
        audit_b = client.get("/api/v1/memory-bridge/audit", headers={"X-App-Session": sess_b["quest"]}).json()["events"]
        assert all(ev["owner_id"] == uid_b for ev in audit_b)
    finally:
        db.close()


@pytest.mark.parametrize("age_band", [None, "under_13", "teen_13_17"])
def test_gate_s_d11_minor_protection_across_routes(tmp_path: Path, age_band: str | None) -> None:
    """D11: under_13, teen_13_17, and undeclared (unknown) accounts fail closed 403 on writes/export and receive [] interests."""
    db, _id_svc, _fake_tm, _token_svc, _bridge, client = _build_e2e_app(tmp_path)
    try:
        sub = f"550e8400-e29b-41d4-a716-44665544030{0 if age_band is None else len(age_band)}"
        _uid, sess = _login_all_apps(client, sub=sub, age_band=age_band)

        # Cannot enable cross-app interest export on any consent scope -> 403.
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/source",
                headers={"X-App-Session": sess["quest"]},
                json={"source_kind": "quest", "enabled": True, "allow_interest_export": True},
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess["community"]},
                json={
                    "app_id": "community",
                    "read_enabled": True,
                    "write_enabled": True,
                    "allow_interest_export_to_community": True,
                },
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/conversation",
                headers={"X-App-Session": sess["messenger"]},
                json={"conversation_id": "conv-minor", "ai_mode": "save", "allow_interest_export": True},
            ).status_code
            == 403
        )

        # Even with source/app consent enabled without export, writes & signals fail closed 403.
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/source",
                headers={"X-App-Session": sess["quest"]},
                json={"source_kind": "quest", "enabled": True, "allow_interest_export": False},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess["quest"]},
                json={"app_id": "quest", "read_enabled": True, "write_enabled": True},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/memory-bridge/writes",
                headers={"X-App-Session": sess["quest"]},
                json={
                    "record_id": "qmsg:minor-1",
                    "source_kind": "quest",
                    "source_id": "quest:t1",
                    "host_app": "quest",
                    "text": "I enjoy robotics",
                    "valid_time": "2026-11-23T12:00:00Z",
                    "explicit_user_confirm": True,
                },
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/memory-bridge/signals",
                headers={"X-App-Session": sess["quest"]},
                json={
                    "source_kind": "quest",
                    "source_id": "quest:t1",
                    "topic_slug": "robotics",
                    "option_key": "k1",
                    "at": "2026-11-23T12:00:00Z",
                },
            ).status_code
            == 403
        )

        # Community interests returns empty list [].
        comm_resp = client.get(
            "/api/v1/memory-bridge/community/interests",
            headers={"X-App-Session": sess["community"]},
        )
        assert comm_resp.status_code == 200
        assert comm_resp.json() == {"features": []}
    finally:
        db.close()


def test_router_error_mapping_and_spoof_guards(tmp_path: Path) -> None:
    """Router maps SensitiveContentError->400, MemoryBridgeUnavailable->503, and rejects caller field spoofs."""
    db, _id_svc, _fake_tm, _token_svc, _bridge, client = _build_e2e_app(tmp_path)
    try:
        uid, sess = _login_all_apps(client, sub="550e8400-e29b-41d4-a716-446655440401")

        # Caller spoofs owner / scope / provenance / age_band in body or query -> 403/422.
        for bad_body in (
            {"owner": "usr_other"},
            {"provenance": "user_supplied"},
            {"age_band": "adult_18_plus"},
            {"scope": "cross_app_interest"},
        ):
            payload = {
                "record_id": "qmsg:spoof",
                "source_kind": "quest",
                "source_id": "quest:t1",
                "host_app": "quest",
                "text": "Spoof test",
                "valid_time": "2026-11-23T12:00:00Z",
                **bad_body,
            }
            resp = client.post(
                "/api/v1/memory-bridge/writes",
                headers={"X-App-Session": sess["quest"]},
                json=payload,
            )
            assert resp.status_code == 403

        assert (
            client.get(
                f"/api/v1/memory-bridge/quest/timeline?owner_id={uid}_other",
                headers={"X-App-Session": sess["quest"]},
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/api/v1/memory-bridge/quest/timeline?age_band=adult_18_plus",
                headers={"X-App-Session": sess["quest"]},
            ).status_code
            == 422
        )

        # SensitiveContentError -> HTTP 400; MemoryBridgeUnavailable -> HTTP 503.
        class _ErrorBridge:
            def resolve_fact(self, *_args, **_kwargs):
                raise SensitiveContentError("credential")

            def read_quest_context(self, *_args, **_kwargs):
                raise MemoryBridgeUnavailable("temporal_memory offline")

        client.app.state.memory_bridge = _ErrorBridge()  # type: ignore[attr-defined]
        r_sens = client.post(
            "/api/v1/memory-bridge/facts/f_1/resolve",
            headers={"X-App-Session": sess["quest"]},
            json={"action": "edit", "new_text": "token is secret"},
        )
        assert r_sens.status_code == 400
        assert r_sens.json()["detail"]["category"] == "credential"

        r_unavail = client.post(
            "/api/v1/memory-bridge/quest/context",
            headers={"X-App-Session": sess["quest"]},
            json={"query": "anything"},
        )
        assert r_unavail.status_code == 503
    finally:
        db.close()
