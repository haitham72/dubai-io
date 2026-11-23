"""Synthetic cryptographic keys, JWT signers, and FastAPI test harness for CS-B1 identity tests."""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
import time
from typing import Any, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect

from app import actions
from app.identity import (
    IdentityConfig,
    IdentityService,
    IdentityStore,
    JWTVerifier,
    VerifiedPrincipal,
    create_identity_router,
    require_app_principal,
    require_verified_jwt,
    require_ws_principal,
)

TEST_ISSUER = "https://auth.synthetic.dubai.test/auth/v1"
TEST_ALT_ISSUER = "https://idp2.synthetic.dubai.test"
TEST_AUDIENCE = "authenticated"
TEST_HS256_SECRET = "synthetic-hs256-test-secret-key-32bytes"


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def int_to_b64url(value: int, length: Optional[int] = None) -> str:
    if length is None:
        length = max(1, (value.bit_length() + 7) // 8)
    return b64url_encode(value.to_bytes(length, "big"))


@dataclass(frozen=True)
class SyntheticKeySet:
    rsa_private: rsa.RSAPrivateKey
    rsa_kid: str
    rsa_jwk: dict[str, Any]
    rsa_pem_public: str
    ec_private: ec.EllipticCurvePrivateKey
    ec_kid: str
    ec_jwk: dict[str, Any]
    ed_private: ed25519.Ed25519PrivateKey
    ed_kid: str
    ed_jwk: dict[str, Any]
    jwks: dict[str, Any]


def generate_synthetic_keyset() -> SyntheticKeySet:
    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pub_nums = rsa_priv.public_key().public_numbers()
    rsa_kid = "rsa-test-1"
    rsa_jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": rsa_kid,
        "n": int_to_b64url(rsa_pub_nums.n),
        "e": int_to_b64url(rsa_pub_nums.e),
    }
    rsa_pem_public = rsa_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    ec_priv = ec.generate_private_key(ec.SECP256R1())
    ec_pub_nums = ec_priv.public_key().public_numbers()
    ec_kid = "ec-test-1"
    ec_jwk = {
        "kty": "EC",
        "use": "sig",
        "alg": "ES256",
        "crv": "P-256",
        "kid": ec_kid,
        "x": int_to_b64url(ec_pub_nums.x, 32),
        "y": int_to_b64url(ec_pub_nums.y, 32),
    }

    ed_priv = ed25519.Ed25519PrivateKey.generate()
    ed_pub_bytes = ed_priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    ed_kid = "ed-test-1"
    ed_jwk = {
        "kty": "OKP",
        "use": "sig",
        "alg": "EdDSA",
        "crv": "Ed25519",
        "kid": ed_kid,
        "x": b64url_encode(ed_pub_bytes),
    }

    return SyntheticKeySet(
        rsa_private=rsa_priv,
        rsa_kid=rsa_kid,
        rsa_jwk=rsa_jwk,
        rsa_pem_public=rsa_pem_public,
        ec_private=ec_priv,
        ec_kid=ec_kid,
        ec_jwk=ec_jwk,
        ed_private=ed_priv,
        ed_kid=ed_kid,
        ed_jwk=ed_jwk,
        jwks={"keys": [rsa_jwk, ec_jwk, ed_jwk]},
    )


def default_claims(
    sub: str = "550e8400-e29b-41d4-a716-446655440000",
    *,
    issuer: str = TEST_ISSUER,
    audience: str | list[str] = TEST_AUDIENCE,
    exp_offset_s: int = 3600,
    nbf_offset_s: Optional[int] = None,
    jti: Optional[str] = None,
    display_name: str = "Synthetic User",
    email_verified: bool = False,
    nonce: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": sub,
        "iat": now,
        "exp": now + exp_offset_s,
        "display_name": display_name,
        "email_verified": email_verified,
    }
    if nbf_offset_s is not None:
        payload["nbf"] = now + nbf_offset_s
    if jti is not None:
        payload["jti"] = jti
    if nonce is not None:
        payload["nonce"] = nonce
    if extra:
        payload.update(extra)
    return payload


def _encode_jwt(header: dict[str, Any], payload: dict[str, Any], signer_fn) -> str:
    h_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    sig_bytes = signer_fn(signing_input)
    return f"{h_b64}.{p_b64}.{b64url_encode(sig_bytes)}"


def sign_hs256_jwt(payload: dict[str, Any], secret: str = TEST_HS256_SECRET, *, kid: Optional[str] = None) -> str:
    header: dict[str, Any] = {"alg": "HS256", "typ": "JWT"}
    if kid is not None:
        header["kid"] = kid
    return _encode_jwt(header, payload, lambda msg: hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest())


def sign_rs256_jwt(payload: dict[str, Any], private_key: rsa.RSAPrivateKey, *, kid: Optional[str] = "rsa-test-1") -> str:
    header: dict[str, Any] = {"alg": "RS256", "typ": "JWT"}
    if kid is not None:
        header["kid"] = kid
    return _encode_jwt(
        header,
        payload,
        lambda msg: private_key.sign(msg, padding.PKCS1v15(), hashes.SHA256()),
    )


def sign_es256_jwt(
    payload: dict[str, Any],
    private_key: ec.EllipticCurvePrivateKey,
    *,
    kid: Optional[str] = "ec-test-1",
) -> str:
    header: dict[str, Any] = {"alg": "ES256", "typ": "JWT"}
    if kid is not None:
        header["kid"] = kid

    def _sign_p1363(msg: bytes) -> bytes:
        der = private_key.sign(msg, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")

    return _encode_jwt(header, payload, _sign_p1363)


def sign_eddsa_jwt(
    payload: dict[str, Any],
    private_key: ed25519.Ed25519PrivateKey,
    *,
    kid: Optional[str] = "ed-test-1",
) -> str:
    header: dict[str, Any] = {"alg": "EdDSA", "typ": "JWT"}
    if kid is not None:
        header["kid"] = kid
    return _encode_jwt(header, payload, lambda msg: private_key.sign(msg))


def sign_alg_none_jwt(payload: dict[str, Any], *, alg_value: str = "none") -> str:
    return _encode_jwt({"alg": alg_value, "typ": "JWT"}, payload, lambda _msg: b"unsigned")


def build_test_app(service: IdentityService, *, action_engine: Optional[actions.ActionEngine] = None) -> FastAPI:
    """Mount /api/identity, legacy /api/session + /api/actions, and sample Quest/Community/Messenger routes."""
    app = FastAPI()
    app.state.identity_service = service
    app.include_router(create_identity_router())

    if action_engine is not None:
        # Use isolated ActionStore in tests without mutating repo data/.
        app.include_router(actions.router)

    @app.get("/api/test/jwt-only")
    def jwt_only_route(principal: VerifiedPrincipal = Depends(require_verified_jwt)):
        return {"user_id": principal.user_id, "auth_mode": principal.auth_mode}

    @app.get("/api/test/quest/chat")
    def quest_chat(principal: VerifiedPrincipal = Depends(require_app_principal("quest", frozenset({"quest:chat"})))):
        return {"user_id": principal.user_id, "app_id": principal.app_id, "caps": sorted(principal.capabilities)}

    @app.get("/api/test/quest/fallback")
    def quest_fallback(
        principal: VerifiedPrincipal = Depends(
            require_app_principal("quest", frozenset({"quest:chat"}), allow_jwt_fallback=True)
        ),
    ):
        return {"user_id": principal.user_id, "app_id": principal.app_id, "auth_mode": principal.auth_mode}

    @app.get("/api/test/community/feed")
    def community_feed(
        principal: VerifiedPrincipal = Depends(require_app_principal("community", frozenset({"community:read"}))),
    ):
        return {"user_id": principal.user_id, "app_id": principal.app_id}

    @app.get("/api/test/community/moderate")
    def community_moderate(
        principal: VerifiedPrincipal = Depends(require_app_principal("community", frozenset({"community:moderate"}))),
    ):
        return {"user_id": principal.user_id, "app_id": principal.app_id}

    @app.get("/api/test/messenger/chat")
    def messenger_chat(
        principal: VerifiedPrincipal = Depends(require_app_principal("messenger", frozenset({"messenger:chat"}))),
    ):
        return {"user_id": principal.user_id, "app_id": principal.app_id}

    @app.websocket("/ws/messenger")
    async def messenger_ws(websocket: WebSocket):
        principal = require_ws_principal(
            websocket,
            app_id="messenger",
            required_capabilities=frozenset({"messenger:ws"}),
        )
        await websocket.accept()
        await websocket.send_json(
            {
                "user_id": principal.user_id,
                "app_id": principal.app_id,
                "auth_mode": principal.auth_mode,
                "session_id": principal.session_id,
            }
        )
        try:
            while True:
                msg = await websocket.receive_text()
                service.assert_session_active(principal.session_id or "", expected_app="messenger")
                await websocket.send_json({"echo": msg, "user_id": principal.user_id})
        except WebSocketDisconnect:
            return

    return app
