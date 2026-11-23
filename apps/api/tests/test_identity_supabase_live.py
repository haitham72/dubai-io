"""Live integration tests against local Supabase Auth (GoTrue) + Postgres 17 (D12).

Skipped automatically when SUPABASE_LOCAL_URL / SUPABASE_SERVICE_ROLE_KEY are unset.
Requires synthetic test users provisioned and deleted cleanly in finally:.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
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
from app.memory_bridge import FakeTemporalMemoryClient, MemoryBridge, create_memory_bridge_router
from tests.fixtures.contest_shared.db_fixtures import cs_postgres_isolation  # noqa: F401

SUPABASE_URL = os.getenv("SUPABASE_LOCAL_URL", "").strip().rstrip("/")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "").strip()

pytestmark = pytest.mark.skipif(
    not (SUPABASE_URL and SERVICE_ROLE_KEY and ANON_KEY),
    reason="Local Supabase Auth env vars (SUPABASE_LOCAL_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY) not set",
)


def _jwt_header(token: str) -> dict:
    seg = token.split(".")[0]
    padded = seg + "=" * (-len(seg) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))


def test_live_local_supabase_auth_jwt_and_postgres_roundtrip(tmp_path: Path):
    """Real GoTrue JWTs (ES256 JWKS or HS256) verify and drive Identity + MemoryBridge on Postgres 17."""
    run_id = uuid4().hex[:10]
    email_a = f"synth_alpha_{run_id}@dubai.test"
    email_b = f"synth_beta_{run_id}@dubai.test"
    password = f"SynthPass!{run_id}"
    created_ids: list[str] = []

    admin_headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    anon_headers = {
        "apikey": ANON_KEY,
        "Content-Type": "application/json",
    }

    with httpx.Client(base_url=SUPABASE_URL, timeout=15.0) as supa:
        try:
            for email, name in ((email_a, "Alpha Synth"), (email_b, "Beta Synth")):
                r = supa.post(
                    "/auth/v1/admin/users",
                    headers=admin_headers,
                    json={
                        "email": email,
                        "password": password,
                        "email_confirm": True,
                        "user_metadata": {"display_name": name},
                    },
                )
                assert r.status_code in (200, 201), r.text
                created_ids.append(r.json()["id"])

            tok_a = supa.post(
                "/auth/v1/token?grant_type=password",
                headers=anon_headers,
                json={"email": email_a, "password": password},
            )
            assert tok_a.status_code == 200, tok_a.text
            jwt_a = tok_a.json()["access_token"]
            sub_a = tok_a.json()["user"]["id"]

            tok_b = supa.post(
                "/auth/v1/token?grant_type=password",
                headers=anon_headers,
                json={"email": email_b, "password": password},
            )
            assert tok_b.status_code == 200, tok_b.text
            jwt_b = tok_b.json()["access_token"]
            sub_b = tok_b.json()["user"]["id"]

            hdr_a = _jwt_header(jwt_a)
            assert hdr_a.get("alg") in {"ES256", "RS256", "EdDSA", "HS256"}

            issuer = f"{SUPABASE_URL}/auth/v1"
            jwks_url = f"{issuer}/.well-known/jwks.json"
            verifier = JWTVerifier(
                issuer=issuer,
                audience="authenticated",
                hs256_secret=JWT_SECRET,
                jwks_url=jwks_url,
            )
            shared_db = db_mod.connect(tmp_path / "live_supabase.sqlite3")
            id_store = IdentityStore(shared_db)
            id_svc = IdentityService(
                id_store,
                verifier,
                config=IdentityConfig(
                    jwt_issuer=issuer,
                    jwt_audience="authenticated",
                    jwt_jwks_url=jwks_url,
                    jwt_hs256_secret=JWT_SECRET,
                ),
            )
            fake_tm = FakeTemporalMemoryClient()
            token_svc = MemoryTokenService(
                id_store,
                fake_tm,
                token_key=Fernet.generate_key(),
                key_path=tmp_path / "live.key",
            )
            bridge = MemoryBridge(shared_db, fake_tm)

            app = FastAPI()
            app.state.identity_service = id_svc
            app.state.memory_token_handler = token_svc
            app.state.memory_bridge = bridge
            app.include_router(create_identity_router())
            app.include_router(create_memory_bridge_router())

            client = TestClient(app)

            # 1. Verify both real GoTrue tokens resolve to distinct canonical user_ids
            me_a = client.get("/api/identity/me", headers={"Authorization": f"Bearer {jwt_a}"})
            assert me_a.status_code == 200, me_a.text
            assert me_a.json()["user_id"] == sub_a
            assert me_a.json()["is_minor_protected"] is True

            me_b = client.get("/api/identity/me", headers={"Authorization": f"Bearer {jwt_b}"})
            assert me_b.status_code == 200, me_b.text
            assert me_b.json()["user_id"] == sub_b
            assert sub_a != sub_b

            # 2. Tampered real Supabase JWT fails closed (401)
            tampered = jwt_a[:-4] + ("AAAA" if jwt_a[-4:] != "AAAA" else "BBBB")
            assert client.get("/api/identity/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401

            # 3. Declare adult_18_plus for User A, mint per-app sessions, write & cross-app read on Postgres 17
            age_r = client.post(
                "/api/identity/age-band",
                headers={"Authorization": f"Bearer {jwt_a}"},
                json={"age_band": "adult_18_plus"},
            )
            assert age_r.status_code == 200, age_r.text
            assert age_r.json()["is_minor_protected"] is False

            sess_q = client.post(
                "/api/identity/sessions",
                headers={"Authorization": f"Bearer {jwt_a}"},
                json={"app_id": "quest"},
            ).json()["session_token"]
            sess_c = client.post(
                "/api/identity/sessions",
                headers={"Authorization": f"Bearer {jwt_a}"},
                json={"app_id": "community"},
            ).json()["session_token"]
            sess_m = client.post(
                "/api/identity/sessions",
                headers={"Authorization": f"Bearer {jwt_a}"},
                json={"app_id": "messenger"},
            ).json()["session_token"]

            # Wrong-app session isolation (community token rejected on quest route)
            assert client.get(
                "/api/v1/memory-bridge/quest/timeline",
                headers={"X-App-Session": sess_c},
            ).status_code == 403

            # WS ticket minted from real Supabase-backed messenger session
            ws_r = client.post(
                "/api/identity/ws-ticket",
                headers={"X-App-Session": sess_m, "Origin": "http://testserver"},
                json={},
            )
            assert ws_r.status_code == 200, ws_r.text
            assert ws_r.json()["ticket"]

            # Enable consents & write a Quest fact + read Community InterestFeature on Postgres 17
            assert client.put(
                "/api/v1/memory-bridge/consent/source",
                headers={"X-App-Session": sess_q},
                json={"source_kind": "quest", "enabled": True, "allow_interest_export": True},
            ).status_code == 200
            assert client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess_q},
                json={"app_id": "quest", "read_enabled": True, "write_enabled": True},
            ).status_code == 200
            assert client.put(
                "/api/v1/memory-bridge/consent/app",
                headers={"X-App-Session": sess_c},
                json={
                    "app_id": "community",
                    "read_enabled": True,
                    "write_enabled": True,
                    "allow_interest_export_to_community": True,
                },
            ).status_code == 200

            w = client.post(
                "/api/v1/memory-bridge/writes",
                headers={"X-App-Session": sess_q},
                json={
                    "record_id": "qmsg:live-supa-1",
                    "source_kind": "quest",
                    "source_id": "quest:live-1",
                    "host_app": "quest",
                    "author_id": sub_a,
                    "text": "I enjoy urban cycling on Al Qudra track.",
                    "valid_time": "2026-11-23T12:00:00Z",
                    "subject_path": "hobbies/cycling",
                    "explicit_user_confirm": True,
                },
            )
            assert w.status_code == 200, w.text
            assert w.json()["status"] == "applied"

            feats = client.get("/api/v1/memory-bridge/community/interests", headers={"X-App-Session": sess_c})
            assert feats.status_code == 200, feats.text
            assert len(feats.json()["features"]) == 1
            assert feats.json()["features"][0]["topic_slug"] == "cycling"

            # User B cannot see User A's audit or memories
            sess_b_q = client.post(
                "/api/identity/sessions",
                headers={"Authorization": f"Bearer {jwt_b}"},
                json={"app_id": "quest"},
            ).json()["session_token"]
            assert client.get("/api/v1/memory-bridge/audit", headers={"X-App-Session": sess_b_q}).json()["events"] == []
        finally:
            for uid in created_ids:
                try:
                    supa.delete(f"/auth/v1/admin/users/{uid}", headers=admin_headers)
                except Exception:
                    pass
