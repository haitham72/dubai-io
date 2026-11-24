"""Tests for app sessions, cross-app capability isolation, WS tickets, revocation, age gate, and adoption."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest
from starlette.testclient import WebSocketDenialResponse

from app import actions
from app.identity import IdentityConfig, IdentityError, IdentityService, IdentityStore, JWTVerifier
from tests.fixtures.contest_shared.db_fixtures import cs_postgres_isolation  # noqa: F401
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_AUDIENCE,
    TEST_HS256_SECRET,
    TEST_ISSUER,
    build_test_app,
    default_claims,
    sign_hs256_jwt,
)


def _setup(tmp_path, monkeypatch=None):
    verifier = JWTVerifier(
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
        hs256_secret=TEST_HS256_SECRET,
    )
    store = IdentityStore(tmp_path / "identity.sqlite3")
    action_store = actions.ActionStore(tmp_path / "actions.sqlite3")
    action_engine = actions.ActionEngine(action_store)
    if monkeypatch is not None:
        monkeypatch.setattr(actions, "_engine", action_engine)
    svc = IdentityService(
        store,
        verifier,
        config=IdentityConfig(jwt_issuer=TEST_ISSUER, jwt_audience=TEST_AUDIENCE, jwt_hs256_secret=TEST_HS256_SECRET),
        legacy_session_resolver=action_store.owner,
    )
    app = build_test_app(svc, action_engine=action_engine)
    return svc, store, action_store, TestClient(app)


def test_identity_session_and_ws_ticket_expiry(tmp_path):
    """ID-02 (Session & WS ticket part): unexpired succeeds; expired cs_app_sessions and cs_ws_tickets fail 401."""
    svc, store, _actions, client = _setup(tmp_path)
    jwt_a = sign_hs256_jwt(default_claims(sub="550e8400-e29b-41d4-a716-446655440010"))

    # Mint active session
    sess_resp = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"app_id": "messenger"},
    )
    assert sess_resp.status_code == 200
    sess_data = sess_resp.json()
    assert client.get("/api/test/messenger/chat", headers={"X-App-Session": sess_data["session_token"]}).status_code == 200

    # Mint active WS ticket and connect
    origin = "https://messenger.dubai.test"
    t_resp = client.post(
        "/api/identity/ws-ticket",
        headers={"X-App-Session": sess_data["session_token"], "Origin": origin},
        json={"app_id": "messenger"},
    )
    assert t_resp.status_code == 200
    ticket = t_resp.json()["ticket"]
    with client.websocket_connect(f"/ws/messenger?ticket={ticket}", headers={"origin": origin}) as ws:
        msg = ws.receive_json()
        assert msg["user_id"] == sess_data["user_id"]
        assert msg["auth_mode"] == "verified_ws_ticket"

    # Force-expire a WS ticket in DB -> 401
    t_resp2 = client.post(
        "/api/identity/ws-ticket",
        headers={"X-App-Session": sess_data["session_token"], "Origin": origin},
        json={"app_id": "messenger"},
    )
    expired_ticket = t_resp2.json()["ticket"]
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    with store.lock:
        store.db.execute("UPDATE cs_ws_tickets SET expires_at = ?", (past_iso,))
        store.db.commit()
    with pytest.raises(WebSocketDenialResponse) as exc_ws:
        with client.websocket_connect(f"/ws/messenger?ticket={expired_ticket}", headers={"origin": origin}):
            pass
    assert exc_ws.value.status_code == 401

    # Force-expire session in DB -> 401
    with store.lock:
        store.db.execute("UPDATE cs_app_sessions SET expires_at = ? WHERE session_id = ?", (past_iso, sess_data["session_id"]))
        store.db.commit()
    assert client.get("/api/test/messenger/chat", headers={"X-App-Session": sess_data["session_token"]}).status_code == 401


def test_identity_revocation_immediate(tmp_path):
    """ID-04: revoke_session, revoke_all_sessions (session_version bump), revoke_jti, WS ticket replay, wrong Origin fail."""
    svc, store, _actions, client = _setup(tmp_path)
    jwt_a = sign_hs256_jwt(default_claims(sub="550e8400-e29b-41d4-a716-446655440011", jti="jti-revoke-me"))

    # Happy: mint messenger cookie session and connect WS same-origin
    sess_resp = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"app_id": "messenger", "set_cookie": True},
    )
    assert sess_resp.status_code == 200
    sess1 = sess_resp.json()
    with client.websocket_connect("/ws/messenger", headers={"origin": "http://testserver"}) as ws:
        hello = ws.receive_json()
        assert hello["user_id"] == sess1["user_id"]
        ws.send_text("ping")
        assert ws.receive_json() == {"echo": "ping", "user_id": sess1["user_id"]}

    # Failure: cross-origin cookie WS handshake -> 403
    with pytest.raises(WebSocketDenialResponse) as exc_cross:
        with client.websocket_connect("/ws/messenger", headers={"origin": "https://evil.example"}):
            pass
    assert exc_cross.value.status_code == 403

    # Failure: missing Origin header on WS -> 403
    with pytest.raises(WebSocketDenialResponse) as exc_no_origin:
        with client.websocket_connect("/ws/messenger"):
            pass
    assert exc_no_origin.value.status_code == 403

    # Happy: single-use WS ticket succeeds once, fails on replay (401) and wrong Origin (403)
    origin = "https://messenger.dubai.test"
    ticket = client.post(
        "/api/identity/ws-ticket",
        headers={"X-App-Session": sess1["session_token"], "Origin": origin},
        json={"app_id": "messenger"},
    ).json()["ticket"]

    # Wrong origin before consumption -> 403
    with pytest.raises(WebSocketDenialResponse) as exc_bad_origin:
        with client.websocket_connect(f"/ws/messenger?ticket={ticket}", headers={"origin": "https://evil.example"}):
            pass
    assert exc_bad_origin.value.status_code == 403

    # Correct origin succeeds once
    with client.websocket_connect(f"/ws/messenger?ticket={ticket}", headers={"origin": origin}) as ws:
        assert ws.receive_json()["user_id"] == sess1["user_id"]

    # Replay fails 401
    with pytest.raises(WebSocketDenialResponse) as exc_replay:
        with client.websocket_connect(f"/ws/messenger?ticket={ticket}", headers={"origin": origin}):
            pass
    assert exc_replay.value.status_code == 401

    # Revoke single session immediately -> 401
    del_resp = client.delete(
        f"/api/identity/sessions/{sess1['session_id']}",
        headers={"X-App-Session": sess1["session_token"]},
    )
    assert del_resp.status_code == 200
    assert client.get("/api/test/messenger/chat", headers={"X-App-Session": sess1["session_token"]}).status_code == 401

    # Mint 2 sessions across quest + messenger, then revoke-all -> bumps session_version and blocks both
    s_quest = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"app_id": "quest"},
    ).json()
    s_msg = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"app_id": "messenger"},
    ).json()
    assert client.get("/api/test/quest/chat", headers={"X-App-Session": s_quest["session_token"]}).status_code == 200
    assert client.get("/api/test/messenger/chat", headers={"X-App-Session": s_msg["session_token"]}).status_code == 200

    # Mint ticket on s_msg, then revoke-all BEFORE consuming ticket -> ticket consumption must fail 401!
    t_before_revoke = client.post(
        "/api/identity/ws-ticket",
        headers={"X-App-Session": s_msg["session_token"], "Origin": origin},
        json={"app_id": "messenger"},
    ).json()["ticket"]

    rev_all = client.post(
        "/api/identity/sessions/revoke-all",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={},
    )
    assert rev_all.status_code == 200
    assert rev_all.json()["revoked_count"] == 2
    assert store.get_user(s_quest["user_id"])["session_version"] == 2

    assert client.get("/api/test/quest/chat", headers={"X-App-Session": s_quest["session_token"]}).status_code == 401
    assert client.get("/api/test/messenger/chat", headers={"X-App-Session": s_msg["session_token"]}).status_code == 401
    with pytest.raises(WebSocketDenialResponse) as exc_revoked_parent:
        with client.websocket_connect(f"/ws/messenger?ticket={t_before_revoke}", headers={"origin": origin}):
            pass
    assert exc_revoked_parent.value.status_code == 401

    # Revoke JTI blocks JWT immediately
    svc.revoke_jti(s_quest["user_id"], "jti-revoke-me", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
    assert client.get("/api/identity/me", headers={"Authorization": f"Bearer {jwt_a}"}).status_code == 401


def test_identity_cross_app_capability_isolation(tmp_path):
    """ID-05: Per-app session works for own app + granted caps; cross-app and ungranted/out-of-allowlist caps fail 403/422."""
    _svc, _store, _actions, client = _setup(tmp_path)
    jwt_a = sign_hs256_jwt(default_claims(sub="550e8400-e29b-41d4-a716-446655440012"))

    # Happy: community session with subset capability community:read
    comm_sess = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"app_id": "community", "requested_capabilities": ["community:read"]},
    )
    assert comm_sess.status_code == 200
    comm_tok = comm_sess.json()["session_token"]
    assert client.get("/api/test/community/feed", headers={"X-App-Session": comm_tok}).status_code == 200

    # Failure: missing capability community:moderate -> 403
    assert client.get("/api/test/community/moderate", headers={"X-App-Session": comm_tok}).status_code == 403

    # Failure: community session rejected on messenger and quest -> 403
    assert client.get("/api/test/messenger/chat", headers={"X-App-Session": comm_tok}).status_code == 403
    assert client.get("/api/test/quest/chat", headers={"X-App-Session": comm_tok}).status_code == 403

    # Failure: messenger session rejected on community -> 403
    msg_tok = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"app_id": "messenger"},
    ).json()["session_token"]
    assert client.get("/api/test/messenger/chat", headers={"X-App-Session": msg_tok}).status_code == 200
    assert client.get("/api/test/community/feed", headers={"X-App-Session": msg_tok}).status_code == 403

    # Failure: out-of-allowlist capability request rejected -> 403
    bad_cap_resp = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"app_id": "community", "requested_capabilities": ["messenger:ws"]},
    )
    assert bad_cap_resp.status_code == 403

    # Failure: invalid app_id rejected -> 422
    bad_app_resp = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"app_id": "admin"},
    )
    assert bad_app_resp.status_code == 422

    # Happy vs Failure on allow_jwt_fallback
    assert client.get("/api/test/quest/chat", headers={"Authorization": f"Bearer {jwt_a}"}).status_code == 401
    assert client.get("/api/test/quest/fallback", headers={"Authorization": f"Bearer {jwt_a}"}).status_code == 200


def test_identity_age_band_self_declared(tmp_path):
    """ID-10: Self-declared age_band sets is_minor_protected=False ONLY for adult_18_plus; invalid/inferred rejected."""
    svc, store, _actions, client = _setup(tmp_path)
    jwt_a = sign_hs256_jwt(default_claims(sub="550e8400-e29b-41d4-a716-446655440013"))

    # Default state is unknown -> is_minor_protected=True (fail-closed D11)
    me_default = client.get("/api/identity/me", headers={"Authorization": f"Bearer {jwt_a}"}).json()
    assert me_default["age_band"] == "unknown"
    assert me_default["is_minor_protected"] is True

    # Self-declare under_13 and teen_13_17 -> is_minor_protected=True
    for minor_band in ("under_13", "teen_13_17"):
        r = client.post(
            "/api/identity/age-band",
            headers={"Authorization": f"Bearer {jwt_a}"},
            json={"age_band": minor_band},
        )
        assert r.status_code == 200
        assert r.json()["age_band"] == minor_band
        assert r.json()["age_source"] == "self_declared"
        assert r.json()["is_minor_protected"] is True

    # Self-declare adult_18_plus -> is_minor_protected=False
    r_adult = client.post(
        "/api/identity/age-band",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"age_band": "adult_18_plus"},
    )
    assert r_adult.status_code == 200
    assert r_adult.json()["age_band"] == "adult_18_plus"
    assert r_adult.json()["age_source"] == "self_declared"
    assert r_adult.json()["is_minor_protected"] is False
    assert store.get_user(me_default["user_id"])["age_source"] == "self_declared"

    # Failure: invalid age_band or inferred age_source override rejected 422
    assert client.post(
        "/api/identity/age-band",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"age_band": "18+"},
    ).status_code == 422
    assert client.post(
        "/api/identity/age-band",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"age_band": "unknown"},
    ).status_code == 422
    assert client.post(
        "/api/identity/age-band",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"age_band": "adult_18_plus", "age_source": "inferred"},
    ).status_code == 422

    principal = svc.authenticate_jwt(jwt_a)
    with pytest.raises(IdentityError) as exc_age:
        svc.set_age_band(principal, age_band="unknown")  # type: ignore[arg-type]
    assert exc_age.value.status_code == 422


def test_identity_session_owner_adoption(tmp_path, monkeypatch):
    """ID-11: Valid dubaiio_lab_session cookie adopts session_owner once; missing/wrong/replayed adoption fails."""
    _svc, store, _action_store, client = _setup(tmp_path, monkeypatch)

    # Create legacy anonymous session via /api/session
    sess_resp = client.get("/api/session")
    assert sess_resp.status_code == 200
    legacy_owner = sess_resp.json()["user_id"]
    legacy_cookie = client.cookies.get("dubaiio_lab_session")
    assert legacy_cookie

    jwt_a = sign_hs256_jwt(default_claims(sub="550e8400-e29b-41d4-a716-446655440014", display_name="SameName"))
    jwt_b = sign_hs256_jwt(default_claims(sub="550e8400-e29b-41d4-a716-446655440015", display_name="SameName"))

    # Failure: invalid proof_cookie_token -> 401
    bad_proof = client.post(
        "/api/identity/adopt-session",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"proof_cookie_token": "forged-cookie-token"},
    )
    assert bad_proof.status_code == 401

    # Happy: adopt once using proof_cookie_token (or cookie)
    ok_adopt = client.post(
        "/api/identity/adopt-session",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"proof_cookie_token": legacy_cookie},
    )
    assert ok_adopt.status_code == 200
    assert ok_adopt.json()["adopted"] is True
    assert ok_adopt.json()["session_owner"] == legacy_owner
    adoption_row = store.get_session_adoption(legacy_owner)
    assert adoption_row is not None
    assert adoption_row["user_id"] == "550e8400-e29b-41d4-a716-446655440014"

    # Failure: second adoption attempt by same or different user -> 409
    replay_same = client.post(
        "/api/identity/adopt-session",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"proof_cookie_token": legacy_cookie},
    )
    assert replay_same.status_code == 409

    replay_other = client.post(
        "/api/identity/adopt-session",
        headers={"Authorization": f"Bearer {jwt_b}"},
        json={"proof_cookie_token": legacy_cookie},
    )
    assert replay_other.status_code == 409

    # Failure: without cookie or proof_cookie_token (display_name alone) -> 401
    client.cookies.clear()
    no_proof = client.post(
        "/api/identity/adopt-session",
        headers={"Authorization": f"Bearer {jwt_b}"},
        json={},
    )
    assert no_proof.status_code == 401


def test_identity_memory_token_store_and_router_hook(tmp_path):
    """Store cs_memory_tokens helpers and /api/identity/memory-device-token hook work cleanly."""
    _svc, store, _actions, client = _setup(tmp_path)
    jwt_a = sign_hs256_jwt(default_claims(sub="550e8400-e29b-41d4-a716-446655440019"))
    me = client.get("/api/identity/me", headers={"Authorization": f"Bearer {jwt_a}"}).json()
    uid = me["user_id"]

    # Default placeholder returns 501 until CS-B5 mounts handler
    assert (
        client.post(
            "/api/identity/memory-device-token",
            headers={"Authorization": f"Bearer {jwt_a}"},
            json={},
        ).status_code
        == 501
    )
    assert (
        client.delete(
            "/api/identity/memory-device-token/tmtok-1",
            headers={"Authorization": f"Bearer {jwt_a}"},
        ).status_code
        == 501
    )

    # Store helpers happy + failure paths
    store.create_memory_token(
        record_id="mt_1",
        user_id=uid,
        tm_owner_id=uid,
        tm_token_id="tmtok-1",
        kind="bridge_service",
        label="cs-bridge",
        encrypted_token=b"encrypted-bytes",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    active = store.get_active_memory_token(uid, kind="bridge_service")
    assert active is not None
    assert active["encrypted_token"] == b"encrypted-bytes"
    assert store.get_memory_token_by_tm_id("tmtok-1") is not None

    assert store.revoke_memory_token("tmtok-1", revoked_at=datetime.now(timezone.utc).isoformat()) is True
    assert store.revoke_memory_token("tmtok-1", revoked_at=datetime.now(timezone.utc).isoformat()) is False
    assert store.get_active_memory_token(uid, kind="bridge_service") is None

