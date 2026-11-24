"""Tests for JWT verification, claims validation, JWKS caching/rotation, and config (ID-02, ID-03)."""
from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient
import httpx
import pytest

from app.identity import IdentityConfig, IdentityService, IdentityStore, JWTVerificationError, JWTVerifier
from tests.fixtures.contest_shared.db_fixtures import cs_postgres_isolation  # noqa: F401
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_AUDIENCE,
    TEST_HS256_SECRET,
    TEST_ISSUER,
    b64url_encode,
    build_test_app,
    default_claims,
    generate_synthetic_keyset,
    sign_alg_none_jwt,
    sign_eddsa_jwt,
    sign_es256_jwt,
    sign_hs256_jwt,
    sign_rs256_jwt,
)


def test_identity_config_from_env_happy_and_bounded(monkeypatch):
    monkeypatch.setenv("IDENTITY_JWT_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("IDENTITY_JWT_AUDIENCE", "custom-aud")
    monkeypatch.setenv("IDENTITY_JWT_JWKS_URL", "https://auth.example.test/jwks.json")
    monkeypatch.setenv("IDENTITY_JWT_HS256_SECRET", "env-secret")
    monkeypatch.setenv("IDENTITY_CLOCK_SKEW_SECONDS", "999")
    monkeypatch.setenv("IDENTITY_SESSION_TTL_SECONDS", "9999999")
    monkeypatch.setenv("IDENTITY_WS_TICKET_TTL_SECONDS", "45")
    monkeypatch.setenv("IDENTITY_TOKEN_KEY", "fernet-key-placeholder")

    cfg = IdentityConfig.from_env()
    assert cfg.jwt_issuer == TEST_ISSUER
    assert cfg.jwt_audience == "custom-aud"
    assert cfg.clock_skew_seconds == 120
    assert cfg.session_ttl_seconds == 604800
    assert cfg.ws_ticket_ttl_seconds == 45
    assert cfg.token_key == "fernet-key-placeholder"

    monkeypatch.setenv("IDENTITY_CLOCK_SKEW_SECONDS", "not-an-int")
    with pytest.raises(ValueError):
        IdentityConfig.from_env()


def test_identity_jwt_signature_and_claims(tmp_path):
    """ID-03: HS256, RS256, ES256 (P1363->DER), and EdDSA succeed; tampered, alg=none, confusion, wrong claims fail."""
    keys = generate_synthetic_keyset()
    verifier = JWTVerifier(
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
        hs256_secret=TEST_HS256_SECRET,
        static_jwks=keys.jwks,
        clock_skew_s=30,
    )

    claims_payload = default_claims(
        sub="550e8400-e29b-41d4-a716-446655440001",
        jti="jti-1",
        display_name="Layla",
        email_verified=True,
    )

    for token in (
        sign_hs256_jwt(claims_payload),
        sign_rs256_jwt(claims_payload, keys.rsa_private, kid=keys.rsa_kid),
        sign_es256_jwt(claims_payload, keys.ec_private, kid=keys.ec_kid),
        sign_eddsa_jwt(claims_payload, keys.ed_private, kid=keys.ed_kid),
    ):
        verified = verifier.verify(token)
        assert verified.issuer == TEST_ISSUER
        assert verified.subject == "550e8400-e29b-41d4-a716-446655440001"
        assert TEST_AUDIENCE in verified.audience
        assert verified.display_name == "Layla"
        assert verified.email_verified is True

    # Failure: tampered payload
    good_rs = sign_rs256_jwt(claims_payload, keys.rsa_private, kid=keys.rsa_kid)
    h, _p, s = good_rs.split(".")
    evil_payload = b64url_encode(json.dumps({**claims_payload, "sub": "attacker"}).encode("utf-8"))
    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(f"{h}.{evil_payload}.{s}")
    assert exc_info.value.code == "invalid_signature"

    # Failure: tampered signature
    with pytest.raises(JWTVerificationError):
        verifier.verify(f"{h}.{_p}.{s[:-2]}aa")

    # Failure: alg="none" (and "NONE")
    for alg_val in ("none", "NONE", "None"):
        with pytest.raises(JWTVerificationError) as exc_info:
            verifier.verify(sign_alg_none_jwt(claims_payload, alg_value=alg_val))
        assert exc_info.value.code == "invalid_alg"

    # Failure: HS256 / RSA public key confusion
    confused_verifier = JWTVerifier(
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
        hs256_secret=keys.rsa_pem_public,
    )
    confused_tok = sign_hs256_jwt(claims_payload, secret=keys.rsa_pem_public)
    with pytest.raises(JWTVerificationError) as exc_info:
        confused_verifier.verify(confused_tok)
    assert exc_info.value.code == "alg_confusion"

    # Failure: RSA token presented with HS256 secret verifier (no JWKS)
    hs_only_verifier = JWTVerifier(
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
        hs256_secret=TEST_HS256_SECRET,
        allowed_algs=("HS256",),
    )
    with pytest.raises(JWTVerificationError) as exc_info:
        hs_only_verifier.verify(good_rs)
    assert exc_info.value.code == "invalid_alg"

    # Failure: wrong iss, wrong aud, empty sub, unknown kid
    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(sign_hs256_jwt(default_claims(issuer="https://evil.example")))
    assert exc_info.value.code == "invalid_issuer"

    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(sign_hs256_jwt(default_claims(audience="wrong-aud")))
    assert exc_info.value.code == "invalid_audience"

    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(sign_hs256_jwt(default_claims(sub="   ")))
    assert exc_info.value.code == "missing_sub"

    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(sign_rs256_jwt(claims_payload, keys.rsa_private, kid="unknown-kid"))
    assert exc_info.value.code == "unknown_kid"

    # HTTP boundary returns 401 on invalid JWT and 200 on valid JWT
    store = IdentityStore(tmp_path / "id.sqlite3")
    svc = IdentityService(store, verifier)
    app = build_test_app(svc)
    client = TestClient(app)

    ok_resp = client.get("/api/identity/me", headers={"Authorization": f"Bearer {good_rs}"})
    assert ok_resp.status_code == 200
    assert ok_resp.json()["user_id"] == "550e8400-e29b-41d4-a716-446655440001"

    bad_resp = client.get("/api/identity/me", headers={"Authorization": f"Bearer {f'{h}.{evil_payload}.{s}'}"})
    assert bad_resp.status_code == 401


def test_identity_jwks_url_cache_and_rate_capped_refresh():
    """JWKS URL caches keys across calls, refreshes on unknown kid, and enforces cooldown rate cap."""
    keys1 = generate_synthetic_keyset()
    keys2 = generate_synthetic_keyset()
    rotated_rsa_jwk = {**keys2.rsa_jwk, "kid": "rsa-test-2"}

    fetch_count = 0
    serve_rotated = False

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal fetch_count
        fetch_count += 1
        if serve_rotated:
            return httpx.Response(200, json={"keys": [keys1.rsa_jwk, rotated_rsa_jwk]})
        return httpx.Response(200, json={"keys": [keys1.rsa_jwk]})

    verifier = JWTVerifier(
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
        jwks_url="https://jwks.synthetic.test/.well-known/jwks.json",
        jwks_ttl_s=300,
        jwks_refresh_cooldown_s=60,
        http_transport=httpx.MockTransport(_handler),
    )

    claims = default_claims(sub="user-jwks")
    tok1 = sign_rs256_jwt(claims, keys1.rsa_private, kid="rsa-test-1")
    assert verifier.verify(tok1).subject == "user-jwks"
    assert verifier.verify(tok1).subject == "user-jwks"
    assert fetch_count == 1  # cached

    # Unknown kid triggers forced refresh once
    serve_rotated = True
    tok_missing = sign_rs256_jwt(claims, keys2.rsa_private, kid="never-existed")
    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(tok_missing)
    assert exc_info.value.code == "unknown_kid"
    assert fetch_count == 2

    # Subsequent unknown kid within cooldown is rate-capped (does not hammer JWKS endpoint)
    with pytest.raises(JWTVerificationError):
        verifier.verify(tok_missing)
    assert fetch_count == 2

    # Rotated key loaded during refresh works immediately
    tok2 = sign_rs256_jwt(claims, keys2.rsa_private, kid="rsa-test-2")
    assert verifier.verify(tok2).subject == "user-jwks"


def test_identity_expiry(tmp_path):
    """ID-02 (JWT part): valid within skew succeeds; expired past skew, future nbf, missing exp fail 401."""
    verifier = JWTVerifier(
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
        hs256_secret=TEST_HS256_SECRET,
        clock_skew_s=30,
    )
    now = int(time.time())

    # Happy: expires in 10s (unexpired) and nbf 20s in future (within 30s skew)
    valid_tok = sign_hs256_jwt(default_claims(exp_offset_s=10, nbf_offset_s=20))
    assert verifier.verify(valid_tok, now_ts=now).subject == "550e8400-e29b-41d4-a716-446655440000"

    # Failure: expired 45s ago (beyond 30s skew)
    expired_tok = sign_hs256_jwt(default_claims(exp_offset_s=-45))
    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(expired_tok, now_ts=now)
    assert exc_info.value.code == "token_expired"

    # Failure: nbf 60s in future (beyond 30s skew)
    future_nbf_tok = sign_hs256_jwt(default_claims(exp_offset_s=300, nbf_offset_s=60))
    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(future_nbf_tok, now_ts=now)
    assert exc_info.value.code == "token_not_yet_valid"

    # Failure: missing exp and non-numeric exp
    no_exp_payload = default_claims()
    del no_exp_payload["exp"]
    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(sign_hs256_jwt(no_exp_payload), now_ts=now)
    assert exc_info.value.code == "missing_exp"

    bool_exp_payload = default_claims()
    bool_exp_payload["exp"] = True
    with pytest.raises(JWTVerificationError) as exc_info:
        verifier.verify(sign_hs256_jwt(bool_exp_payload), now_ts=now)
    assert exc_info.value.code == "missing_exp"

    # HTTP 401 check
    store = IdentityStore(tmp_path / "id.sqlite3")
    svc = IdentityService(store, verifier)
    client = TestClient(build_test_app(svc))
    resp = client.get("/api/identity/me", headers={"Authorization": f"Bearer {expired_tok}"})
    assert resp.status_code == 401
