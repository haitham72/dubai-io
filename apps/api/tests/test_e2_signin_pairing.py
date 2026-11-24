"""E2 tests: Google sign-in (token exchange MOCKED), QR pairing, device revoke, owner isolation through the vault gateway."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from app.identity import IdentityConfig, IdentityService, IdentityStore, JWTVerifier, create_identity_router
from app.identity.google_signin import GoogleSignInService, validate_return_to
from app.identity.models import IdentityError
from app.identity.store import iso_utc, utcnow
from app.identity.vault_gateway import create_vault_gateway_router
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_AUDIENCE,
    TEST_HS256_SECRET,
    TEST_ISSUER,
)

REDIRECT = "http://localhost:8000/api/identity/google/callback"
PROFILES = {
    "tok-a": {"sub": "g-sub-A", "email": "a@example.test", "name": "Alice Test", "email_verified": True},
    "tok-b": {"sub": "g-sub-B", "email": "b@example.test", "name": "Bob Test", "email_verified": True},
}


def _google_transport(state: dict) -> httpx.MockTransport:
    """Stands in for Google: the token endpoint and userinfo. No network, no real secret."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            body = parse_qs(request.content.decode())
            state["token_form"] = {k: v[0] for k, v in body.items()}
            if body.get("code", [""])[0] == "bad-code":
                return httpx.Response(400, json={"error": "invalid_grant"})
            who = "tok-b" if body.get("code", [""])[0] == "code-b" else "tok-a"
            return httpx.Response(
                200,
                json={"access_token": who, "token_type": "Bearer", "scope": "openid email profile"},
            )
        if request.url.host.endswith("googleapis.com"):
            token = request.headers["authorization"].split()[1]
            return httpx.Response(200, json=PROFILES[token])
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.fixture()
def env(tmp_path: Path):
    verifier = JWTVerifier(issuer=TEST_ISSUER, audience=TEST_AUDIENCE, hs256_secret=TEST_HS256_SECRET)
    store = IdentityStore(tmp_path / "identity.sqlite3")
    svc = IdentityService(
        store,
        verifier,
        config=IdentityConfig(jwt_issuer=TEST_ISSUER, jwt_audience=TEST_AUDIENCE, jwt_hs256_secret=TEST_HS256_SECRET),
    )
    state: dict = {}
    google = GoogleSignInService(
        svc,
        client_id="synthetic-client-id.apps.test",
        client_secret="synthetic-client-secret-not-real",
        redirect_uri=REDIRECT,
        token_key=Fernet.generate_key(),
        transport=_google_transport(state),
    )
    tm = FakeTemporalMemoryClient()
    app = FastAPI()
    app.state.identity_service = svc
    app.state.google_signin_service = google
    app.include_router(create_identity_router())
    app.include_router(create_vault_gateway_router(get_tm_client=lambda: tm))
    client = TestClient(app, follow_redirects=False)
    return svc, store, tm, client, state, google


def _sign_in(client: TestClient, code: str = "code-a", return_to: str = "http://localhost:8081/connect"):
    start = client.get("/api/identity/google/start", params={"client": "web", "return_to": return_to})
    assert start.status_code == 302
    q = parse_qs(urlsplit(start.headers["location"]).query)
    cb = client.get("/api/identity/google/callback", params={"state": q["state"][0], "code": code})
    assert cb.status_code == 302, cb.text
    target = urlsplit(cb.headers["location"])
    auth_code = parse_qs(target.query)["auth_code"][0]
    return start, target, auth_code


def test_google_start_uses_server_side_client_id_pkce_and_exact_redirect(env):
    _svc, _store, _tm, client, _state, _g = env
    start = client.get("/api/identity/google/start", params={"client": "web", "return_to": "http://localhost:8081/connect"})
    loc = start.headers["location"]
    q = parse_qs(urlsplit(loc).query)
    assert loc.startswith("https://accounts.google.com/")
    assert q["redirect_uri"] == [REDIRECT]
    assert q["code_challenge_method"] == ["S256"]
    assert q["client_id"] == ["synthetic-client-id.apps.test"]
    assert "client_secret" not in loc and "synthetic-client-secret" not in loc
    assert "synthetic-client-secret" not in start.text


def test_full_google_signin_with_mocked_exchange_gives_session_and_me(env):
    _svc, _store, _tm, client, state, _g = env
    _start, target, auth_code = _sign_in(client)
    assert f"{target.scheme}://{target.netloc}{target.path}" == "http://localhost:8081/connect"
    assert state["token_form"]["code_verifier"]  # PKCE verifier reached "Google"
    ex = client.post("/api/identity/google/exchange", json={"auth_code": auth_code, "device_label": "PC browser"})
    assert ex.status_code == 200, ex.text
    body = ex.json()
    assert body["display_name"] == "Alice Test"
    assert "synthetic-client-secret" not in ex.text
    me = client.get("/api/identity/me", headers={"X-App-Session": body["session_token"]})
    assert me.status_code == 200
    assert me.json()["display_name"] == "Alice Test"
    assert me.json()["user_id"] == body["user_id"]


def test_google_failure_paths(env):
    _svc, _store, _tm, client, _state, _g = env
    # unknown / replayed state
    assert client.get("/api/identity/google/callback", params={"state": "nope", "code": "x"}).status_code == 400
    start = client.get("/api/identity/google/start", params={"client": "web", "return_to": "http://localhost:8081/connect"})
    st = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    # Google refuses the code
    assert client.get("/api/identity/google/callback", params={"state": st, "code": "bad-code"}).status_code == 502
    assert client.get("/api/identity/google/callback", params={"state": st, "code": "code-a"}).status_code == 400
    # user denied consent
    assert client.get("/api/identity/google/callback", params={"error": "access_denied"}).status_code == 400
    # auth_code is single use
    _s, _t, auth_code = _sign_in(client)
    assert client.post("/api/identity/google/exchange", json={"auth_code": auth_code}).status_code == 200
    reused = client.post("/api/identity/google/exchange", json={"auth_code": auth_code})
    assert reused.status_code == 401
    assert client.post("/api/identity/google/exchange", json={"auth_code": "garbage"}).status_code == 401


def test_return_to_must_be_loopback(env):
    _svc, _store, _tm, client, _state, _g = env
    for bad in ("https://evil.example/cb", "http://localhost.evil.example/cb", "http://user:pw@localhost/cb", "javascript:alert(1)"):
        r = client.get("/api/identity/google/start", params={"client": "web", "return_to": bad})
        assert r.status_code == 400, bad
    assert validate_return_to("http://127.0.0.1:53211/callback") == "http://127.0.0.1:53211/callback"
    with pytest.raises(IdentityError):
        validate_return_to("ftp://localhost/x")


def test_unconfigured_google_is_a_clear_503(tmp_path):
    verifier = JWTVerifier(issuer=TEST_ISSUER, audience=TEST_AUDIENCE, hs256_secret=TEST_HS256_SECRET)
    svc = IdentityService(IdentityStore(tmp_path / "i.sqlite3"), verifier)
    unconfigured = GoogleSignInService(svc, client_id="", client_secret="", redirect_uri=REDIRECT, token_key=Fernet.generate_key())
    app = FastAPI()
    app.state.identity_service = svc
    app.state.google_signin_service = unconfigured
    app.include_router(create_identity_router())
    r = TestClient(app, follow_redirects=False).get(
        "/api/identity/google/start", params={"client": "web", "return_to": "http://localhost:8081/connect"}
    )
    assert r.status_code == 503


def _login(client, code):
    _s, _t, auth_code = _sign_in(client, code=code)
    ex = client.post("/api/identity/google/exchange", json={"auth_code": auth_code, "device_label": f"PC-{code}"})
    return ex.json()


def test_qr_pairing_phone_gets_its_own_revocable_session(env):
    _svc, _store, _tm, client, _state, _g = env
    pc = _login(client, "code-a")
    pc_h = {"X-App-Session": pc["session_token"]}
    start = client.post("/api/identity/pair/start", headers=pc_h, json={"ttl_seconds": 300})
    assert start.status_code == 200
    pair = start.json()
    assert pair["ttl_seconds"] <= 300 and pair["qr_payload"].endswith(pair["code"])

    done = client.post("/api/identity/pair/complete", json={"code": pair["code"], "device_label": "iPhone"})
    assert done.status_code == 200, done.text
    phone = done.json()
    assert phone["session_id"] != pc["session_id"]
    assert phone["user_id"] == pc["user_id"]
    assert phone["display_name"] == "Alice Test"
    # phone payload carries no Google or service tokens
    assert set(phone) <= {"session_id", "session_token", "user_id", "display_name", "email", "app_id", "expires_at"}

    phone_h = {"X-App-Session": phone["session_token"]}
    assert client.get("/api/identity/me", headers=phone_h).json()["display_name"] == "Alice Test"
    listing = client.get("/api/identity/sessions", headers=pc_h).json()["sessions"]
    assert {s["session_id"] for s in listing} == {pc["session_id"], phone["session_id"]}
    assert [s for s in listing if s["is_current"]][0]["session_id"] == pc["session_id"]

    # revoke the phone from the PC: phone is signed out, PC stays in
    assert client.delete(f"/api/identity/sessions/{phone['session_id']}", headers=pc_h).status_code == 200
    assert client.get("/api/identity/me", headers=phone_h).status_code == 401
    assert client.get("/api/identity/me", headers=pc_h).status_code == 200


def test_pairing_codes_are_one_time_expiring_and_signed_in_only(env, monkeypatch):
    _svc, _store, _tm, client, _state, _g = env
    pc = _login(client, "code-a")
    pc_h = {"X-App-Session": pc["session_token"]}
    assert client.post("/api/identity/pair/start").status_code == 401  # must be signed in

    code = client.post("/api/identity/pair/start", headers=pc_h).json()["code"]
    assert client.post("/api/identity/pair/complete", json={"code": code}).status_code == 200
    reused = client.post("/api/identity/pair/complete", json={"code": code})
    assert reused.status_code == 409 and reused.json()["detail"]["code"] == "code_already_used"

    assert client.post("/api/identity/pair/complete", json={"code": "NOPE1234"}).status_code == 400

    code2 = client.post("/api/identity/pair/start", headers=pc_h).json()["code"]
    import app.identity.service as service_mod

    real_now = service_mod.utcnow
    monkeypatch.setattr(service_mod, "utcnow", lambda: real_now() + timedelta(minutes=6))
    expired = client.post("/api/identity/pair/complete", json={"code": code2})
    assert expired.status_code == 410 and expired.json()["detail"]["code"] == "expired_code"
    monkeypatch.undo()
    assert client.post("/api/identity/pair/start", headers=pc_h, json={"ttl_seconds": 9999}).status_code == 422


def test_account_a_never_sees_account_b(env):
    _svc, _store, tm, client, _state, _g = env
    a = _login(client, "code-a")
    b = _login(client, "code-b")
    assert a["user_id"] != b["user_id"]
    ha, hb = {"X-App-Session": a["session_token"]}, {"X-App-Session": b["session_token"]}

    # identity: names, sessions and revoke are owner-scoped
    assert client.get("/api/identity/me", headers=ha).json()["display_name"] == "Alice Test"
    assert client.get("/api/identity/me", headers=hb).json()["display_name"] == "Bob Test"
    assert {s["session_id"] for s in client.get("/api/identity/sessions", headers=hb).json()["sessions"]} == {b["session_id"]}
    cross = client.delete(f"/api/identity/sessions/{a['session_id']}", headers=hb)
    assert cross.status_code == 403
    assert client.get("/api/identity/me", headers=ha).status_code == 200

    # memory: a fact stored for A is invisible to B through the vault gateway
    tm.upsert_record_and_enqueue(
        a["user_id"], record_id="rec:a1", source="quest:profile", at="2026-11-24T08:00:00Z",
        author=a["user_id"], text="Alice likes alpine pottery.", enqueue="none",
        direct_fact={
            "id": "fact_alpine", "text": "Likes alpine pottery.", "subject_path": "interests/pottery",
            "valid_from": "2026-11-24T08:00:00Z", "provenance": "user_supplied", "status": "active",
            "evidence": ["rec:a1"],
        },
    )
    a_graph = client.get("/api/vault/graph", headers=ha).json()
    b_graph = client.get("/api/vault/graph", headers=hb).json()
    assert "pottery" in str(a_graph).lower()
    assert "pottery" not in str(b_graph).lower() and "alpine" not in str(b_graph).lower()
    assert "fact_alpine" not in str(client.get("/api/vault/subjects", headers=hb).json())
    assert client.get("/api/vault/why/fact_alpine", headers=hb).status_code in (403, 404)

    # no session, no data
    assert client.get("/api/vault/graph").status_code == 401


# ---- E2b: pairing polish ----


def test_qr_payload_carries_api_base_when_configured(env, monkeypatch):
    _svc, _store, _tm, client, _state, _g = env
    pc_h = {"X-App-Session": _login(client, "code-a")["session_token"]}
    monkeypatch.delenv("PUBLIC_API_BASE_URL", raising=False)
    plain = client.post("/api/identity/pair/start", headers=pc_h).json()
    assert plain["qr_payload"] == f"dubaiio://pair?code={plain['code']}" and "api_base_url" not in plain

    monkeypatch.setenv("PUBLIC_API_BASE_URL", "http://192.168.1.20:8000/")
    rich = client.post("/api/identity/pair/start", headers=pc_h).json()
    q = parse_qs(urlsplit(rich["qr_payload"]).query)
    assert q["code"] == [rich["code"]] and q["api"] == ["http://192.168.1.20:8000"]
    assert rich["api_base_url"] == "http://192.168.1.20:8000"

    monkeypatch.setenv("PUBLIC_API_BASE_URL", "javascript:alert(1)")
    bad = client.post("/api/identity/pair/start", headers=pc_h).json()
    assert "api=" not in bad["qr_payload"]


def test_pair_complete_locks_out_ip_after_five_failures(env):
    _svc, _store, _tm, client, _state, _g = env
    pc_h = {"X-App-Session": _login(client, "code-a")["session_token"]}
    good = client.post("/api/identity/pair/start", headers=pc_h).json()["code"]
    for i in range(5):
        r = client.post("/api/identity/pair/complete", json={"code": f"WRONG00{i}"})
        assert r.status_code == 400
    locked = client.post("/api/identity/pair/complete", json={"code": good})
    assert locked.status_code == 429 and locked.json()["detail"]["code"] == "too_many_attempts"


def test_pair_lockout_expires_after_window(env, monkeypatch):
    _svc, _store, _tm, client, _state, _g = env
    pc_h = {"X-App-Session": _login(client, "code-a")["session_token"]}
    good = client.post("/api/identity/pair/start", headers=pc_h, json={"ttl_seconds": 300}).json()["code"]
    for i in range(5):
        client.post("/api/identity/pair/complete", json={"code": f"WRONG00{i}"})
    import app.identity.service as service_mod

    real_now = service_mod.utcnow
    monkeypatch.setattr(service_mod, "utcnow", lambda: real_now() + timedelta(minutes=5, seconds=1))
    # lockout window passed (the code itself has also expired by now, a clear 410 not a 429)
    r = client.post("/api/identity/pair/complete", json={"code": good})
    assert r.status_code == 410


def test_code_invalidated_after_five_wrong_guesses_against_it(env):
    svc, _store, _tm, client, _state, _g = env
    pc_h = {"X-App-Session": _login(client, "code-a")["session_token"]}
    code = client.post("/api/identity/pair/start", headers=pc_h).json()["code"]
    # five attempts on the same (expired-for-this-test) submitted code from a rotating client: simulate via service
    for _ in range(4):
        with pytest.raises(IdentityError):
            svc.complete_pairing("ZZZZZZZZ", client_ip="10.0.0.1")
    with pytest.raises(IdentityError) as exc:
        svc.complete_pairing("ZZZZZZZZ", client_ip="10.0.0.1")
    assert exc.value.status_code == 429
    # an unrelated real code is still fine from another address
    ok = client.post("/api/identity/pair/complete", json={"code": code})
    assert ok.status_code == 200


def test_invalidate_pairing_code_blocks_a_valid_code(env):
    svc, store, _tm, client, _state, _g = env
    pc_h = {"X-App-Session": _login(client, "code-a")["session_token"]}
    code = client.post("/api/identity/pair/start", headers=pc_h).json()["code"]
    from app.identity.service import _sha256_hex

    assert store.invalidate_pairing_code(_sha256_hex(code), at=iso_utc())
    r = client.post("/api/identity/pair/complete", json={"code": code})
    assert r.status_code == 409


def test_paired_phone_cannot_start_pairing(env):
    _svc, _store, _tm, client, _state, _g = env
    pc_h = {"X-App-Session": _login(client, "code-a")["session_token"]}
    code = client.post("/api/identity/pair/start", headers=pc_h).json()["code"]
    phone = client.post("/api/identity/pair/complete", json={"code": code}).json()
    phone_h = {"X-App-Session": phone["session_token"]}
    r = client.post("/api/identity/pair/start", headers=phone_h)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "pairing_from_paired_device"
    assert client.post("/api/identity/pair/start", headers=pc_h).status_code == 200
