"""Google OAuth2 + PKCE sign-in flow for /api/identity/google/* (PC web & desktop)."""
from __future__ import annotations

import base64
from datetime import timedelta
from hashlib import sha256
import os
from pathlib import Path
import secrets
from typing import Any, Literal, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from cryptography.fernet import Fernet, InvalidToken
import httpx

from ..config import settings
from ..oauth import AUTH_URL, TOKEN_URL, USERINFO_URL, local_key
from .models import AppSessionOut, IdentityError
from .service import IdentityService
from .store import iso_utc, parse_iso, utcnow

GOOGLE_ISSUER = "https://accounts.google.com"
SIGNIN_SCOPES: tuple[str, ...] = ("openid", "email", "profile")
DEFAULT_GOOGLE_IDENTITY_REDIRECT = "http://localhost:8000/api/identity/google/callback"
AUTH_CODE_TTL_SECONDS = 60
ATTEMPT_TTL_SECONDS = 600


def _sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def validate_return_to(uri: str) -> str:
    """Validate that return_to is an http://localhost[:port]/... or http://127.0.0.1[:port]/... URL."""
    if not isinstance(uri, str) or not uri.strip():
        raise IdentityError("invalid_return_to", "return_to is required", 400)
    raw = uri.strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise IdentityError("invalid_return_to", "Malformed return_to URL", 400) from exc

    if (
        parsed.scheme.lower() != "http"
        or (parsed.hostname or "").lower() not in {"localhost", "127.0.0.1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise IdentityError(
            "invalid_return_to",
            "return_to must be an http://localhost or http://127.0.0.1 URL",
            400,
        )
    if port is not None and not (1 <= port <= 65535):
        raise IdentityError("invalid_return_to", "Invalid return_to port", 400)
    return raw


def append_auth_code(return_to: str, auth_code: str) -> str:
    """Append auth_code=... cleanly to a validated return_to URL."""
    parts = urlsplit(return_to)
    query_pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "auth_code"]
    query_pairs.append(("auth_code", auth_code))
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urlencode(query_pairs), ""))


class GoogleSignInService:
    """Handles PC Google OAuth start, callback, and single-use auth_code exchange."""

    def __init__(
        self,
        identity_service: IdentityService,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        token_key: Optional[str | bytes] = None,
        key_path: Optional[Path] = None,
        transport: Optional[httpx.AsyncBaseTransport | httpx.BaseTransport] = None,
    ) -> None:
        self.identity = identity_service
        self.store = identity_service.store
        self._client_id = client_id if client_id is not None else settings.google_oauth_client_id
        self._client_secret = client_secret if client_secret is not None else settings.google_oauth_client_secret
        self._redirect_uri = (
            redirect_uri
            if redirect_uri is not None
            else (os.getenv("IDENTITY_GOOGLE_REDIRECT_URI", "").strip() or DEFAULT_GOOGLE_IDENTITY_REDIRECT)
        )
        self._transport = transport

        if isinstance(token_key, bytes):
            raw_key = token_key
        else:
            configured = (
                token_key
                if token_key is not None
                else (os.environ.get("IDENTITY_TOKEN_KEY") or settings.oauth_token_key or "").strip()
            )
            resolved_path = Path(key_path) if key_path is not None else (settings.data_dir / "identity_token.key")
            raw_key = local_key(resolved_path, configured)
        self._fernet = Fernet(raw_key)

    @property
    def redirect_uri(self) -> str:
        return self._redirect_uri

    def is_configured(self) -> bool:
        return bool((self._client_id or "").strip() and (self._client_secret or "").strip() and self._redirect_uri)

    def _ensure_configured(self) -> None:
        if not self.is_configured():
            raise IdentityError(
                "google_oauth_unconfigured",
                "Google OAuth client credentials are not configured",
                503,
            )

    def _http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=15.0, transport=self._transport, follow_redirects=False)

    def start(self, *, client_kind: Literal["web", "desktop"], return_to: str) -> str:
        self._ensure_configured()
        if client_kind not in ("web", "desktop"):
            raise IdentityError("invalid_client", "client must be web or desktop", 422)
        validated_return = validate_return_to(return_to)

        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(sha256(verifier.encode("utf-8")).digest()).rstrip(b"=").decode("ascii")
        expires_str = iso_utc(utcnow() + timedelta(seconds=ATTEMPT_TTL_SECONDS))
        enc_verifier = self._fernet.encrypt(verifier.encode("utf-8"))

        self.store.create_oauth_attempt(
            state_hash=_sha256_hex(state),
            client_kind=client_kind,
            return_to=validated_return,
            code_verifier_enc=enc_verifier,
            expires_at=expires_str,
        )
        return AUTH_URL + "?" + urlencode({
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(SIGNIN_SCOPES),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        })

    async def callback(self, *, state: str, code: str) -> str:
        self._ensure_configured()
        if not state or not code or len(state) > 256 or len(code) > 4096:
            raise IdentityError("google_signin_failed", "Missing or invalid Google sign-in callback parameters", 400)

        state_hash = _sha256_hex(state)
        attempt = self.store.get_oauth_attempt(state_hash)
        if attempt is None:
            raise IdentityError("invalid_oauth_state", "Sign-in state is invalid or unknown", 400)
        if attempt["consumed_at"] is not None:
            raise IdentityError("oauth_state_reused", "Sign-in state has already been used", 400)
        if parse_iso(attempt["expires_at"]) <= utcnow():
            raise IdentityError("oauth_state_expired", "Sign-in attempt has expired", 400)

        now_str = iso_utc()
        if not self.store.consume_oauth_attempt_atomic(state_hash, consumed_at=now_str):
            raise IdentityError("oauth_state_reused", "Sign-in state has already been used", 400)

        try:
            code_verifier = self._fernet.decrypt(attempt["code_verifier_enc"]).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise IdentityError("invalid_oauth_state", "Sign-in verifier could not be decrypted", 400) from exc

        async with self._http_client() as client:
            try:
                tok_resp = await client.post(
                    TOKEN_URL,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "redirect_uri": self._redirect_uri,
                        "code_verifier": code_verifier,
                        "code": code,
                        "grant_type": "authorization_code",
                    },
                )
            except httpx.HTTPError as exc:
                raise IdentityError("google_exchange_failed", "Could not reach Google token endpoint", 502) from exc

            if not tok_resp.is_success:
                raise IdentityError("google_exchange_failed", "Google did not complete sign-in", 502)
            tok_data = tok_resp.json()
            access_token = tok_data.get("access_token")
            token_type = str(tok_data.get("token_type") or "").lower()
            if not isinstance(access_token, str) or not access_token or token_type != "bearer":
                raise IdentityError("google_invalid_token", "Google returned an invalid token grant", 502)

            granted_scopes = set(str(tok_data.get("scope") or " ".join(SIGNIN_SCOPES)).split())
            if not {"openid", "email", "profile"}.issubset(granted_scopes):
                raise IdentityError("google_missing_scopes", "Google did not grant required identity scopes", 502)

            try:
                prof_resp = await client.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
            except httpx.HTTPError as exc:
                raise IdentityError("google_userinfo_failed", "Could not verify Google profile", 502) from exc

            if not prof_resp.is_success:
                raise IdentityError("google_userinfo_failed", "Google account could not be verified", 502)
            profile = prof_resp.json()

        subject = profile.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise IdentityError("google_userinfo_failed", "Google profile missing sub", 502)

        raw_email = profile.get("email")
        email = raw_email.strip() if isinstance(raw_email, str) and raw_email.strip() else None
        raw_name = profile.get("name") or profile.get("given_name") or (email.split("@")[0] if email else "")
        display_name = str(raw_name).strip()[:120]
        email_verified = profile.get("email_verified") is True

        user, created = self.store.get_or_create_user_for_identity(
            issuer=GOOGLE_ISSUER,
            subject=subject.strip(),
            display_name=display_name,
            email=email,
            email_verified=email_verified,
        )
        if user["status"] != "active":
            raise IdentityError("user_inactive", "User account is not active", 403)
        if created:
            self.store.record_audit(
                user_id=user["user_id"],
                app_id=None,
                session_id=None,
                event_kind="user_provisioned",
                detail={"issuer": GOOGLE_ISSUER},
                at=now_str,
            )

        auth_code = secrets.token_urlsafe(32)
        auth_expires = iso_utc(utcnow() + timedelta(seconds=AUTH_CODE_TTL_SECONDS))
        self.store.create_oauth_auth_code(
            code_hash=_sha256_hex(auth_code),
            user_id=user["user_id"],
            client_kind=attempt["client_kind"],
            expires_at=auth_expires,
        )
        return append_auth_code(attempt["return_to"], auth_code)

    def exchange_auth_code(
        self,
        auth_code: str,
        *,
        device_label: Optional[str] = None,
    ) -> AppSessionOut:
        clean_code = (auth_code or "").strip()
        if not clean_code or len(clean_code) > 512:
            raise IdentityError("invalid_auth_code", "Invalid auth_code", 401)
        code_hash = _sha256_hex(clean_code)
        row = self.store.get_oauth_auth_code(code_hash)
        if row is None:
            raise IdentityError("invalid_auth_code", "Invalid or unknown auth_code", 401)
        if row["consumed_at"] is not None:
            raise IdentityError("auth_code_already_used", "auth_code has already been used", 401)
        if parse_iso(row["expires_at"]) <= utcnow():
            raise IdentityError("auth_code_expired", "auth_code has expired", 401)

        now_str = iso_utc()
        if not self.store.consume_oauth_auth_code_atomic(code_hash, consumed_at=now_str):
            raise IdentityError("auth_code_already_used", "auth_code has already been used", 401)

        default_label = "Desktop" if row["client_kind"] == "desktop" else "Web"
        session_out = self.identity.issue_user_session(
            row["user_id"],
            app_id="quest",
            device_label=device_label or default_label,
        )
        self.store.record_audit(
            user_id=row["user_id"],
            app_id="quest",
            session_id=session_out.session_id,
            event_kind="google_auth_code_exchanged",
            detail={"client_kind": row["client_kind"], "device_label": session_out.device_label},
            at=now_str,
        )
        return session_out
