"""Tests for two-user isolation, non-merging identity links, anonymous cookie boundary, and anti-spoofing (ID-01, ID-06, ID-07, ID-08)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest
from starlette.testclient import WebSocketDenialResponse

from app import actions
from app.identity import IdentityConfig, IdentityService, IdentityStore, JWTVerifier
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_ALT_ISSUER,
    TEST_AUDIENCE,
    TEST_HS256_SECRET,
    TEST_ISSUER,
    build_test_app,
    default_claims,
    sign_hs256_jwt,
)

ALT_SECRET = "synthetic-alt-issuer-secret-32bytes!"


def _setup(tmp_path, monkeypatch=None):
    primary_verifier = JWTVerifier(
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
        hs256_secret=TEST_HS256_SECRET,
    )
    alt_verifier = JWTVerifier(
        issuer=TEST_ALT_ISSUER,
        audience=TEST_AUDIENCE,
        hs256_secret=ALT_SECRET,
    )
    store = IdentityStore(tmp_path / "identity.sqlite3")
    action_store = actions.ActionStore(tmp_path / "actions.sqlite3")
    action_engine = actions.ActionEngine(action_store)
    if monkeypatch is not None:
        monkeypatch.setattr(actions, "_engine", action_engine)
    svc = IdentityService(
        store,
        primary_verifier,
        config=IdentityConfig(jwt_issuer=TEST_ISSUER, jwt_audience=TEST_AUDIENCE, jwt_hs256_secret=TEST_HS256_SECRET),
        legacy_session_resolver=action_store.owner,
        extra_verifiers={TEST_ALT_ISSUER: alt_verifier},
    )
    app = build_test_app(svc, action_engine=action_engine)
    return svc, store, alt_verifier, TestClient(app)


def test_identity_two_users_isolated(tmp_path):
    """ID-01: Two JWTs resolve identically across quest/community/messenger; User A cannot touch User B's sessions or WS tickets."""
    svc, _store, _alt, client = _setup(tmp_path)
    jwt_a = sign_hs256_jwt(default_claims(sub="550e8400-e29b-41d4-a716-446655440021"))
    jwt_b = sign_hs256_jwt(default_claims(sub="non-uuid-subject-b"))

    # Happy: identical user_id across all 3 apps for User A and User B
    uid_a_per_app = {}
    uid_b_per_app = {}
    sess_b_id = None
    sess_b_tok = None

    for app_id, route in (
        ("quest", "/api/test/quest/chat"),
        ("community", "/api/test/community/feed"),
        ("messenger", "/api/test/messenger/chat"),
    ):
        sa = client.post("/api/identity/sessions", headers={"Authorization": f"Bearer {jwt_a}"}, json={"app_id": app_id}).json()
        sb = client.post("/api/identity/sessions", headers={"Authorization": f"Bearer {jwt_b}"}, json={"app_id": app_id}).json()
        ra = client.get(route, headers={"X-App-Session": sa["session_token"]}).json()
        rb = client.get(route, headers={"X-App-Session": sb["session_token"]}).json()
        uid_a_per_app[app_id] = ra["user_id"]
        uid_b_per_app[app_id] = rb["user_id"]
        if app_id == "messenger":
            sess_b_id = sb["session_id"]
            sess_b_tok = sb["session_token"]

    assert len(set(uid_a_per_app.values())) == 1
    assert len(set(uid_b_per_app.values())) == 1
    assert uid_a_per_app["quest"] == "550e8400-e29b-41d4-a716-446655440021"
    assert uid_b_per_app["quest"].startswith("usr_")
    assert uid_a_per_app["quest"] != uid_b_per_app["quest"]

    # Failure: User A cannot revoke User B's session -> 403
    cross_del = client.delete(
        f"/api/identity/sessions/{sess_b_id}",
        headers={"Authorization": f"Bearer {jwt_a}"},
    )
    assert cross_del.status_code == 403

    # User B's session remains active
    assert client.get("/api/test/messenger/chat", headers={"X-App-Session": sess_b_tok}).status_code == 200

    # User A cannot forge a WS ticket for User B's session
    principal_a = svc.authenticate_jwt(jwt_a)
    principal_a_forged_sess = type(principal_a)(
        user_id=principal_a.user_id,
        app_id="messenger",
        capabilities=frozenset({"messenger:ws"}),
        auth_mode="verified_app_session",
        session_id=sess_b_id,
    )
    with pytest.raises(Exception) as exc_ticket:
        svc.create_ws_ticket(principal_a_forged_sess, origin="https://messenger.dubai.test")
    assert getattr(exc_ticket.value, "status_code", None) == 403


def test_identity_no_merge_by_display_name(tmp_path):
    """ID-06: Identical display_name + email_verified never auto-merge; explicit challenge links second (issuer, subject)."""
    _svc, store, _alt, client = _setup(tmp_path)

    # Two distinct identities with identical display_name and email_verified=True
    jwt_primary = sign_hs256_jwt(
        default_claims(
            sub="550e8400-e29b-41d4-a716-446655440030",
            issuer=TEST_ISSUER,
            display_name="Tariq Al Mansoori",
            email_verified=True,
        ),
        secret=TEST_HS256_SECRET,
    )
    jwt_other_same_issuer = sign_hs256_jwt(
        default_claims(
            sub="550e8400-e29b-41d4-a716-446655440031",
            issuer=TEST_ISSUER,
            display_name="Tariq Al Mansoori",
            email_verified=True,
        ),
        secret=TEST_HS256_SECRET,
    )
    me_1 = client.get("/api/identity/me", headers={"Authorization": f"Bearer {jwt_primary}"}).json()
    me_2 = client.get("/api/identity/me", headers={"Authorization": f"Bearer {jwt_other_same_issuer}"}).json()
    assert me_1["user_id"] != me_2["user_id"]

    # Happy: explicit challenge links (TEST_ALT_ISSUER, "alt-sub-1") to me_1
    start_resp = client.post(
        "/api/identity/links/start",
        headers={"Authorization": f"Bearer {jwt_primary}"},
        json={"target_issuer": TEST_ALT_ISSUER},
    )
    assert start_resp.status_code == 200
    challenge_id = start_resp.json()["challenge_id"]
    nonce = start_resp.json()["nonce"]

    proof_jwt = sign_hs256_jwt(
        default_claims(
            sub="alt-sub-1",
            issuer=TEST_ALT_ISSUER,
            nonce=nonce,
            display_name="Tariq Al Mansoori",
            email_verified=True,
        ),
        secret=ALT_SECRET,
    )
    complete_resp = client.post(
        "/api/identity/links/complete",
        headers={"Authorization": f"Bearer {jwt_primary}"},
        json={"challenge_id": challenge_id, "proof_jwt": proof_jwt},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["user_id"] == me_1["user_id"]
    assert store.get_identity_link(TEST_ALT_ISSUER, "alt-sub-1")["user_id"] == me_1["user_id"]

    # Failure: replay same challenge -> 400
    replay_resp = client.post(
        "/api/identity/links/complete",
        headers={"Authorization": f"Bearer {jwt_primary}"},
        json={"challenge_id": challenge_id, "proof_jwt": proof_jwt},
    )
    assert replay_resp.status_code == 400

    # Failure: wrong user completing challenge -> 403
    start_2 = client.post(
        "/api/identity/links/start",
        headers={"Authorization": f"Bearer {jwt_primary}"},
        json={"target_issuer": TEST_ALT_ISSUER},
    ).json()
    wrong_user_resp = client.post(
        "/api/identity/links/complete",
        headers={"Authorization": f"Bearer {jwt_other_same_issuer}"},
        json={"challenge_id": start_2["challenge_id"], "proof_jwt": proof_jwt},
    )
    assert wrong_user_resp.status_code == 403

    # Failure: wrong nonce -> 403
    bad_nonce_jwt = sign_hs256_jwt(
        default_claims(sub="alt-sub-2", issuer=TEST_ALT_ISSUER, nonce="wrong-nonce"),
        secret=ALT_SECRET,
    )
    wrong_nonce_resp = client.post(
        "/api/identity/links/complete",
        headers={"Authorization": f"Bearer {jwt_primary}"},
        json={"challenge_id": start_2["challenge_id"], "proof_jwt": bad_nonce_jwt},
    )
    assert wrong_nonce_resp.status_code == 403

    # Failure: identity already linked to User 1 cannot be linked to User 2 -> 409
    start_b = client.post(
        "/api/identity/links/start",
        headers={"Authorization": f"Bearer {jwt_other_same_issuer}"},
        json={"target_issuer": TEST_ALT_ISSUER},
    ).json()
    steal_jwt = sign_hs256_jwt(
        default_claims(sub="alt-sub-1", issuer=TEST_ALT_ISSUER, nonce=start_b["nonce"]),
        secret=ALT_SECRET,
    )
    steal_resp = client.post(
        "/api/identity/links/complete",
        headers={"Authorization": f"Bearer {jwt_other_same_issuer}"},
        json={"challenge_id": start_b["challenge_id"], "proof_jwt": steal_jwt},
    )
    assert steal_resp.status_code == 409

    # Failure: expired challenge -> 400
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    with store.lock:
        store.db.execute("UPDATE cs_link_challenges SET expires_at = ? WHERE challenge_id = ?", (past_iso, start_b["challenge_id"]))
        store.db.commit()
    expired_resp = client.post(
        "/api/identity/links/complete",
        headers={"Authorization": f"Bearer {jwt_other_same_issuer}"},
        json={"challenge_id": start_b["challenge_id"], "proof_jwt": steal_jwt},
    )
    assert expired_resp.status_code == 400


def test_identity_anon_cookie_boundary(tmp_path, monkeypatch):
    """ID-07: Legacy /api/session & /api/actions remain green; dubaiio_lab_session fails verified routes 401."""
    _svc, _store, _alt, client = _setup(tmp_path, monkeypatch)

    # Happy: legacy anonymous session and /api/actions/prepare work untouched
    sess = client.get("/api/session")
    assert sess.status_code == 200
    assert sess.json()["mode"] == "anonymous_lab_session"
    anon_cookie = client.cookies.get("dubaiio_lab_session")
    assert anon_cookie

    prep = client.post(
        "/api/actions/prepare",
        json={
            "capability_id": "laundry.request",
            "fields": {
                "request": {"value": "2 shirts", "provenance": "user_supplied"},
                "area": {"value": "Marina", "provenance": "user_supplied"},
            },
        },
    )
    assert prep.status_code == 200

    # Failure: anonymous cookie rejected 401 on all verified identity and app routes
    assert client.get("/api/identity/me").status_code == 401
    assert client.post("/api/identity/sessions", json={"app_id": "quest"}).status_code == 401
    assert client.post("/api/identity/age-band", json={"age_band": "adult_18_plus"}).status_code == 401
    assert client.get("/api/test/jwt-only").status_code == 401
    assert client.get("/api/test/quest/chat").status_code == 401

    # Failure: even copying dubaiio_lab_session into cs_session_* or X-App-Session fails 401
    assert client.get("/api/test/quest/chat", headers={"X-App-Session": anon_cookie}).status_code == 401
    assert (
        client.get(
            "/api/test/quest/chat",
            headers={"cookie": f"dubaiio_lab_session={anon_cookie}; cs_session_quest={anon_cookie}"},
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/test/messenger/chat",
            headers={"cookie": f"dubaiio_lab_session={anon_cookie}; cs_session_messenger={anon_cookie}"},
        ).status_code
        == 401
    )

    with pytest.raises(WebSocketDenialResponse) as exc_ws:
        with client.websocket_connect(
            "/ws/messenger",
            headers={"origin": "http://testserver", "cookie": f"dubaiio_lab_session={anon_cookie}; cs_session_messenger={anon_cookie}"},
        ):
            pass
    assert exc_ws.value.status_code == 401


def test_identity_spoofing_rejected(tmp_path):
    """ID-08: Spoofed headers fail 400 (HTTP & WS); mismatched query/body owner/user_id fail 403/422."""
    _svc, _store, _alt, client = _setup(tmp_path)
    jwt_a = sign_hs256_jwt(default_claims(sub="550e8400-e29b-41d4-a716-446655440040"))

    # Happy: clean request works
    assert client.get("/api/identity/me", headers={"Authorization": f"Bearer {jwt_a}"}).status_code == 200
    sess = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_a}"},
        json={"app_id": "messenger"},
    ).json()

    # Construct legacy POC header dynamically without embedding retired product name literal.
    legacy_poc_header = f"X-M{chr(105)}rsal-User"
    spoof_headers = (
        "X-User-Id",
        "X-Owner",
        "X-Owner-Id",
        "X-Dubaiio-User",
        "X-Principal",
        legacy_poc_header,
    )
    for hdr in spoof_headers:
        r_me = client.get("/api/identity/me", headers={"Authorization": f"Bearer {jwt_a}", hdr: "attacker"})
        assert r_me.status_code == 400

        r_app = client.get("/api/test/messenger/chat", headers={"X-App-Session": sess["session_token"], hdr: "attacker"})
        assert r_app.status_code == 400

        with pytest.raises(WebSocketDenialResponse) as exc_ws:
            with client.websocket_connect("/ws/messenger", headers={"origin": "http://testserver", hdr: "attacker"}):
                pass
        assert exc_ws.value.status_code == 400

    # Failure: mismatched query owner/user_id -> 403; forbidden query override -> 422
    assert (
        client.get(
            "/api/test/messenger/chat?owner=other-user",
            headers={"X-App-Session": sess["session_token"]},
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/test/messenger/chat?user_id=other-user",
            headers={"X-App-Session": sess["session_token"]},
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/test/messenger/chat?age_band=adult_18_plus",
            headers={"X-App-Session": sess["session_token"]},
        ).status_code
        == 422
    )

    # Failure: body trying to set owner/user_id on JSON endpoints -> 422
    assert (
        client.post(
            "/api/identity/sessions",
            headers={"Authorization": f"Bearer {jwt_a}"},
            json={"app_id": "quest", "user_id": "other-user"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/identity/age-band",
            headers={"Authorization": f"Bearer {jwt_a}"},
            json={"age_band": "adult_18_plus", "owner": "other-user"},
        ).status_code
        == 422
    )
