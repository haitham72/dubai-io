"""Zero-new-dependency RFC 7519 JWT verifier (HS256, RS256, ES256, EdDSA)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from threading import RLock
import time
from typing import Any, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
import httpx

from .models import VerifiedClaims

SUPPORTED_ALGS = frozenset({"HS256", "RS256", "ES256", "EdDSA"})
ASYMMETRIC_ALGS = frozenset({"RS256", "ES256", "EdDSA"})
MAX_JWT_CHARS = 16384


class JWTVerificationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _b64url_decode(segment: str, *, field_name: str) -> bytes:
    if not segment or not isinstance(segment, str):
        raise JWTVerificationError("malformed_jwt", f"Empty JWT {field_name}")
    pad_len = (-len(segment)) % 4
    padded = segment + ("=" * pad_len)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:
        raise JWTVerificationError("malformed_jwt", f"Invalid base64url in JWT {field_name}") from exc


def _b64url_uint(value: Any, *, field_name: str) -> int:
    if not isinstance(value, str) or not value:
        raise JWTVerificationError("invalid_jwk", f"Missing JWK parameter {field_name}")
    raw = _b64url_decode(value, field_name=f"jwk.{field_name}")
    return int.from_bytes(raw, "big")


def _parse_json_dict(raw: bytes, *, field_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise JWTVerificationError("malformed_jwt", f"Invalid JSON in JWT {field_name}") from exc
    if not isinstance(parsed, dict):
        raise JWTVerificationError("malformed_jwt", f"JWT {field_name} must be a JSON object")
    return parsed


def _is_numeric_claim(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _jwk_to_public_key(jwk: dict[str, Any], alg: str) -> Any:
    kty = jwk.get("kty")
    jwk_use = jwk.get("use")
    if jwk_use is not None and jwk_use != "sig":
        raise JWTVerificationError("invalid_jwk", "JWK use must be sig")
    jwk_alg = jwk.get("alg")
    if jwk_alg is not None and jwk_alg != alg:
        raise JWTVerificationError("alg_mismatch", "JWK alg does not match token header alg")

    if alg == "RS256":
        if kty != "RSA":
            raise JWTVerificationError("alg_mismatch", "RS256 requires an RSA JWK")
        n = _b64url_uint(jwk.get("n"), field_name="n")
        e = _b64url_uint(jwk.get("e"), field_name="e")
        if n <= 0 or e <= 1:
            raise JWTVerificationError("invalid_jwk", "Invalid RSA JWK numbers")
        return rsa.RSAPublicNumbers(e=e, n=n).public_key()

    if alg == "ES256":
        if kty != "EC" or jwk.get("crv") != "P-256":
            raise JWTVerificationError("alg_mismatch", "ES256 requires an EC P-256 JWK")
        x = _b64url_uint(jwk.get("x"), field_name="x")
        y = _b64url_uint(jwk.get("y"), field_name="y")
        return ec.EllipticCurvePublicNumbers(x=x, y=y, curve=ec.SECP256R1()).public_key()

    if alg == "EdDSA":
        if kty != "OKP" or jwk.get("crv") != "Ed25519":
            raise JWTVerificationError("alg_mismatch", "EdDSA requires an OKP Ed25519 JWK")
        x_bytes = _b64url_decode(jwk.get("x", ""), field_name="jwk.x")
        try:
            return ed25519.Ed25519PublicKey.from_public_bytes(x_bytes)
        except Exception as exc:
            raise JWTVerificationError("invalid_jwk", "Invalid Ed25519 public key") from exc

    raise JWTVerificationError("invalid_alg", f"Unsupported asymmetric algorithm: {alg}")


class JWTVerifier:
    """RFC 7519 JWT verifier supporting HS256, RS256, ES256, and EdDSA."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        hs256_secret: str = "",
        jwks_url: str = "",
        static_jwks: Optional[dict] = None,
        allowed_algs: tuple[str, ...] = ("RS256", "ES256", "EdDSA", "HS256"),
        clock_skew_s: int = 30,
        jwks_ttl_s: int = 300,
        jwks_refresh_cooldown_s: int = 10,
        http_transport: Any = None,
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.hs256_secret = hs256_secret
        self.jwks_url = jwks_url
        self.static_jwks = static_jwks
        self.allowed_algs = tuple(alg for alg in allowed_algs if alg in SUPPORTED_ALGS)
        self.clock_skew_s = max(0, min(int(clock_skew_s), 120))
        self.jwks_ttl_s = max(1, int(jwks_ttl_s))
        self.jwks_refresh_cooldown_s = max(1, int(jwks_refresh_cooldown_s))
        self._http_transport = http_transport
        self._lock = RLock()
        self._cached_keys: list[dict[str, Any]] = []
        self._cache_expires_mono: float = 0.0
        self._last_forced_refresh_mono: float = -1e9

    def _load_jwks_from_url(self) -> list[dict[str, Any]]:
        if not self.jwks_url:
            return []
        try:
            with httpx.Client(timeout=5.0, transport=self._http_transport, follow_redirects=False) as client:
                resp = client.get(self.jwks_url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            raise JWTVerificationError("jwks_unavailable", "Unable to fetch JWKS") from exc
        keys = data.get("keys") if isinstance(data, dict) else None
        if not isinstance(keys, list):
            raise JWTVerificationError("invalid_jwks", "JWKS payload missing keys list")
        return [k for k in keys if isinstance(k, dict)]

    def _get_jwks_keys(self, *, force_refresh: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            now_mono = time.monotonic()
            if self.static_jwks is not None and not self.jwks_url:
                keys = self.static_jwks.get("keys", [])
                return [k for k in keys if isinstance(k, dict)]

            if not force_refresh and self._cached_keys and now_mono < self._cache_expires_mono:
                return list(self._cached_keys)

            if force_refresh:
                if now_mono - self._last_forced_refresh_mono < self.jwks_refresh_cooldown_s:
                    return list(self._cached_keys)
                self._last_forced_refresh_mono = now_mono

            keys: list[dict[str, Any]] = []
            if self.static_jwks is not None:
                keys.extend(k for k in self.static_jwks.get("keys", []) if isinstance(k, dict))
            if self.jwks_url:
                keys.extend(self._load_jwks_from_url())
            self._cached_keys = keys
            self._cache_expires_mono = now_mono + self.jwks_ttl_s
            return list(keys)

    def _find_jwk(self, kid: Optional[str], alg: str) -> dict[str, Any]:
        keys = self._get_jwks_keys(force_refresh=False)
        match = self._select_jwk(keys, kid=kid, alg=alg)
        if match is None and kid and self.jwks_url:
            keys = self._get_jwks_keys(force_refresh=True)
            match = self._select_jwk(keys, kid=kid, alg=alg)
        if match is None:
            raise JWTVerificationError("unknown_kid", "No matching signing key found in JWKS")
        return match

    @staticmethod
    def _select_jwk(keys: list[dict[str, Any]], *, kid: Optional[str], alg: str) -> Optional[dict[str, Any]]:
        if kid is not None:
            for jwk in keys:
                if jwk.get("kid") == kid:
                    return jwk
            return None
        expected_kty = {"RS256": "RSA", "ES256": "EC", "EdDSA": "OKP"}.get(alg)
        candidates = [jwk for jwk in keys if jwk.get("kty") == expected_kty]
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _verify_signature(self, header: dict[str, Any], signing_input: bytes, sig_bytes: bytes) -> None:
        alg = header.get("alg")
        if not isinstance(alg, str) or not alg or alg.lower() == "none":
            raise JWTVerificationError("invalid_alg", "JWT algorithm is missing or none")
        if alg not in self.allowed_algs:
            raise JWTVerificationError("invalid_alg", f"JWT algorithm '{alg}' is not permitted")

        if alg == "HS256":
            if not self.hs256_secret:
                raise JWTVerificationError("invalid_key", "HS256 secret is not configured")
            if self.hs256_secret.lstrip().startswith("-----BEGIN"):
                raise JWTVerificationError("alg_confusion", "Asymmetric PEM key cannot be used for HS256")
            expected = hmac.new(self.hs256_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, sig_bytes):
                raise JWTVerificationError("invalid_signature", "JWT HS256 signature verification failed")
            return

        if alg not in ASYMMETRIC_ALGS:
            raise JWTVerificationError("invalid_alg", f"Unsupported JWT algorithm '{alg}'")

        kid = header.get("kid")
        if kid is not None and not isinstance(kid, str):
            raise JWTVerificationError("malformed_jwt", "JWT kid header must be a string")
        jwk = self._find_jwk(kid, alg)
        public_key = _jwk_to_public_key(jwk, alg)

        try:
            if alg == "RS256":
                public_key.verify(sig_bytes, signing_input, padding.PKCS1v15(), hashes.SHA256())
            elif alg == "ES256":
                # Convert raw IEEE P1363 (r || s, 64 bytes) JWT signature into ASN.1 DER for cryptography.
                if len(sig_bytes) != 64:
                    raise JWTVerificationError("invalid_signature", "ES256 signature must be 64 bytes")
                r = int.from_bytes(sig_bytes[:32], "big")
                s = int.from_bytes(sig_bytes[32:], "big")
                if r <= 0 or s <= 0:
                    raise JWTVerificationError("invalid_signature", "Invalid ES256 signature components")
                der_sig = encode_dss_signature(r, s)
                public_key.verify(der_sig, signing_input, ec.ECDSA(hashes.SHA256()))
            elif alg == "EdDSA":
                public_key.verify(sig_bytes, signing_input)
        except JWTVerificationError:
            raise
        except InvalidSignature as exc:
            raise JWTVerificationError("invalid_signature", "JWT signature verification failed") from exc
        except Exception as exc:
            raise JWTVerificationError("invalid_signature", "JWT signature verification error") from exc

    def verify(self, raw_jwt: str, *, now_ts: Optional[int] = None) -> VerifiedClaims:
        if not isinstance(raw_jwt, str) or not raw_jwt or len(raw_jwt) > MAX_JWT_CHARS:
            raise JWTVerificationError("malformed_jwt", "JWT must be a non-empty bounded string")
        parts = raw_jwt.split(".")
        if len(parts) != 3 or any(not p for p in parts):
            raise JWTVerificationError("malformed_jwt", "JWT must have three non-empty segments")
        header_b64, payload_b64, sig_b64 = parts

        header = _parse_json_dict(_b64url_decode(header_b64, field_name="header"), field_name="header")
        payload = _parse_json_dict(_b64url_decode(payload_b64, field_name="payload"), field_name="payload")
        sig_bytes = _b64url_decode(sig_b64, field_name="signature")

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        self._verify_signature(header, signing_input, sig_bytes)

        now = int(time.time()) if now_ts is None else int(now_ts)

        exp = payload.get("exp")
        if not _is_numeric_claim(exp):
            raise JWTVerificationError("missing_exp", "JWT must include a numeric exp claim")
        if now >= int(exp) + self.clock_skew_s:
            raise JWTVerificationError("token_expired", "JWT has expired")

        nbf = payload.get("nbf")
        if nbf is not None:
            if not _is_numeric_claim(nbf):
                raise JWTVerificationError("invalid_nbf", "JWT nbf claim must be numeric")
            if now + self.clock_skew_s < int(nbf):
                raise JWTVerificationError("token_not_yet_valid", "JWT is not valid yet (nbf)")

        iat = payload.get("iat")
        if iat is not None and not _is_numeric_claim(iat):
            raise JWTVerificationError("invalid_iat", "JWT iat claim must be numeric")

        iss = payload.get("iss")
        if not self.issuer or not isinstance(iss, str) or iss != self.issuer:
            raise JWTVerificationError("invalid_issuer", "JWT issuer mismatch")

        raw_aud = payload.get("aud")
        if isinstance(raw_aud, str):
            aud_tuple = (raw_aud,)
        elif isinstance(raw_aud, list) and raw_aud and all(isinstance(a, str) for a in raw_aud):
            aud_tuple = tuple(raw_aud)
        else:
            raise JWTVerificationError("invalid_audience", "JWT audience is missing or malformed")
        if not self.audience or self.audience not in aud_tuple:
            raise JWTVerificationError("invalid_audience", "JWT audience mismatch")

        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub.strip():
            raise JWTVerificationError("missing_sub", "JWT subject (sub) must be a non-empty string")

        jti = payload.get("jti")
        if jti is not None and not isinstance(jti, str):
            raise JWTVerificationError("invalid_jti", "JWT jti must be a string")

        nonce = payload.get("nonce")
        if nonce is not None and not isinstance(nonce, str):
            raise JWTVerificationError("invalid_nonce", "JWT nonce must be a string")

        display_name = ""
        if isinstance(payload.get("display_name"), str):
            display_name = payload["display_name"]
        elif isinstance(payload.get("name"), str):
            display_name = payload["name"]
        elif isinstance(payload.get("user_metadata"), dict) and isinstance(payload["user_metadata"].get("full_name"), str):
            display_name = payload["user_metadata"]["full_name"]

        email_verified = payload.get("email_verified") is True

        return VerifiedClaims(
            issuer=iss,
            subject=sub,
            audience=aud_tuple,
            exp=int(exp),
            iat=int(iat) if iat is not None else None,
            jti=jti,
            display_name=display_name,
            email_verified=email_verified,
            nonce=nonce,
        )
