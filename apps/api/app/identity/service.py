"""Canonical identity business logic: JWT auth, age gate, session adoption, app sessions, WS tickets, and linking."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
import threading
from typing import Callable, Optional
from urllib.parse import quote, urlsplit
import uuid

from fastapi import HTTPException

from .config import IdentityConfig
from .jwt import JWTVerificationError, JWTVerifier
from .models import (
    APP_CAPABILITIES,
    DECLARED_AGE_BANDS,
    VALID_APP_IDS,
    AgeBand,
    AppId,
    AppSessionOut,
    IdentityError,
    VerifiedPrincipal,
    WsTicketOut,
)
from .store import IdentityStore, iso_utc, parse_iso, utcnow


_PAIR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PAIR_MAX_FAILURES = 5
PAIR_WINDOW_SECONDS = 300


def _public_api_base_url() -> Optional[str]:
    """PUBLIC_API_BASE_URL (http/https only) or None; the QR carries it so a phone learns the API address."""
    raw = (os.environ.get("PUBLIC_API_BASE_URL") or "").strip().rstrip("/")
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.fragment:
        return None
    return raw


def _normalize_device_label(label: Optional[str]) -> Optional[str]:
    if label is None:
        return None
    clean = " ".join(label.strip().split())
    return clean[:80] if clean else None


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_origin(origin: str) -> str:
    if not isinstance(origin, str) or not origin.strip():
        raise IdentityError("invalid_origin", "Origin is required", 403)
    raw = origin.strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise IdentityError("invalid_origin", "Malformed Origin header", 403) from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise IdentityError("invalid_origin", "Malformed Origin header", 403)
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    default_port = 443 if scheme == "https" else 80
    if port is not None and port != default_port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def _default_legacy_session_resolver(cookie_token: str) -> str:
    """Read-only lookup of ActionStore.owner for one-time legacy session adoption."""
    from ..actions import engine

    try:
        return engine().store.owner(cookie_token)
    except HTTPException as exc:
        raise IdentityError("invalid_legacy_session", "Invalid or missing legacy session cookie", 401) from exc


class IdentityService:
    """Orchestrates verified principals, age-band declaration, sessions, WS tickets, and identity links."""

    def __init__(
        self,
        store: IdentityStore,
        jwt_verifier: JWTVerifier,
        *,
        config: Optional[IdentityConfig] = None,
        legacy_session_resolver: Optional[Callable[[str], str]] = None,
        extra_verifiers: Optional[dict[str, JWTVerifier]] = None,
    ) -> None:
        self.store = store
        self._pair_lock = threading.Lock()
        self._pair_ip_failures: dict[str, list[datetime]] = {}
        self._pair_code_failures: dict[str, int] = {}
        self.jwt_verifier = jwt_verifier
        self.config = config or IdentityConfig()
        self._legacy_session_resolver = legacy_session_resolver or _default_legacy_session_resolver
        self._extra_verifiers: dict[str, JWTVerifier] = dict(extra_verifiers or {})

    def authenticate_jwt(self, raw_jwt: str, *, now_ts: Optional[int] = None) -> VerifiedPrincipal:
        try:
            claims = self.jwt_verifier.verify(raw_jwt, now_ts=now_ts)
        except JWTVerificationError as exc:
            raise IdentityError(exc.code, exc.message, 401) from exc

        if claims.jti and self.store.is_jti_revoked(claims.jti):
            raise IdentityError("jti_revoked", "JWT has been revoked", 401)

        user, created = self.store.get_or_create_user_for_identity(
            issuer=claims.issuer,
            subject=claims.subject,
            display_name=claims.display_name,
            email_verified=claims.email_verified,
        )
        if user["status"] != "active":
            raise IdentityError("user_inactive", "User account is not active", 403)
        if created:
            self.store.record_audit(
                user_id=user["user_id"],
                app_id=None,
                session_id=None,
                event_kind="user_provisioned",
                detail={"issuer": claims.issuer},
            )
        expires_at = iso_utc(datetime.fromtimestamp(claims.exp, tz=timezone.utc))
        return VerifiedPrincipal(
            user_id=user["user_id"],
            app_id=None,
            capabilities=frozenset(),
            auth_mode="verified_jwt",
            age_band=user["age_band"],
            is_verified=True,
            session_id=None,
            issuer=claims.issuer,
            subject=claims.subject,
            session_version=user["session_version"],
            expires_at=expires_at,
        )

    def refresh_principal(self, principal: VerifiedPrincipal) -> VerifiedPrincipal:
        user = self.store.get_user(principal.user_id)
        if user is None or user["status"] != "active":
            raise IdentityError("user_inactive", "User account is not active", 401)
        return VerifiedPrincipal(
            user_id=principal.user_id,
            app_id=principal.app_id,
            capabilities=principal.capabilities,
            auth_mode=principal.auth_mode,
            age_band=user["age_band"],
            is_verified=True,
            session_id=principal.session_id,
            issuer=principal.issuer,
            subject=principal.subject,
            session_version=user["session_version"],
            expires_at=principal.expires_at,
        )

    def set_age_band(self, principal: VerifiedPrincipal, *, age_band: AgeBand) -> VerifiedPrincipal:
        if not principal.is_verified:
            raise IdentityError("unverified_principal", "Verified principal is required", 401)
        if age_band not in DECLARED_AGE_BANDS:
            raise IdentityError("invalid_age_band", "age_band must be under_13, teen_13_17, or adult_18_plus", 422)
        now_str = iso_utc()
        user = self.store.update_age_band(principal.user_id, age_band=age_band, declared_at=now_str)
        if user is None:
            raise IdentityError("user_not_found", "User not found", 404)
        self.store.record_audit(
            user_id=principal.user_id,
            app_id=principal.app_id,
            session_id=principal.session_id,
            event_kind="age_band_declared",
            detail={"age_band": age_band, "age_source": "self_declared"},
            at=now_str,
        )
        return VerifiedPrincipal(
            user_id=principal.user_id,
            app_id=principal.app_id,
            capabilities=principal.capabilities,
            auth_mode=principal.auth_mode,
            age_band=user["age_band"],
            is_verified=True,
            session_id=principal.session_id,
            issuer=principal.issuer,
            subject=principal.subject,
            session_version=user["session_version"],
            expires_at=principal.expires_at,
        )

    def adopt_session_owner(self, principal: VerifiedPrincipal, *, proof_cookie_token: str) -> dict:
        if not principal.is_verified:
            raise IdentityError("unverified_principal", "Verified principal is required", 401)
        if not isinstance(proof_cookie_token, str) or not proof_cookie_token.strip():
            raise IdentityError("missing_proof", "Valid legacy session cookie proof is required", 401)

        try:
            session_owner = self._legacy_session_resolver(proof_cookie_token.strip())
        except IdentityError:
            raise
        except HTTPException as exc:
            raise IdentityError("invalid_legacy_session", str(exc.detail), exc.status_code) from exc

        if not isinstance(session_owner, str) or not session_owner.strip():
            raise IdentityError("invalid_legacy_session", "Invalid legacy session proof", 401)

        now_str = iso_utc()
        created = self.store.create_session_adoption(
            session_owner=session_owner,
            user_id=principal.user_id,
            adopted_at=now_str,
        )
        if not created:
            raise IdentityError("already_adopted", "Legacy session owner has already been adopted", 409)

        self.store.record_audit(
            user_id=principal.user_id,
            app_id=principal.app_id,
            session_id=principal.session_id,
            event_kind="session_owner_adopted",
            detail={"session_owner": session_owner},
            at=now_str,
        )
        return {
            "adopted": True,
            "session_owner": session_owner,
            "user_id": principal.user_id,
            "adopted_at": now_str,
        }

    def create_app_session(
        self,
        principal: VerifiedPrincipal,
        *,
        app_id: AppId,
        requested_capabilities: Optional[set[str]] = None,
        ttl_seconds: Optional[int] = None,
        source_jti: Optional[str] = None,
        device_label: Optional[str] = None,
    ) -> AppSessionOut:
        if not principal.is_verified:
            raise IdentityError("unverified_principal", "Verified principal is required", 401)
        return self.issue_user_session(
            principal.user_id,
            app_id=app_id,
            requested_capabilities=requested_capabilities,
            ttl_seconds=ttl_seconds,
            source_jti=source_jti,
            device_label=device_label,
        )

    def issue_user_session(
        self,
        user_id: str,
        *,
        app_id: AppId,
        requested_capabilities: Optional[set[str]] = None,
        ttl_seconds: Optional[int] = None,
        source_jti: Optional[str] = None,
        device_label: Optional[str] = None,
    ) -> AppSessionOut:
        if app_id not in VALID_APP_IDS:
            raise IdentityError("invalid_app_id", f"Unsupported app_id: {app_id}", 422)

        user = self.store.get_user(user_id)
        if user is None or user["status"] != "active":
            raise IdentityError("user_inactive", "User account is not active", 403)

        allowed = APP_CAPABILITIES[app_id]
        if requested_capabilities is None:
            granted = allowed
        else:
            req_set = set(requested_capabilities)
            disallowed = req_set - allowed
            if disallowed:
                raise IdentityError(
                    "invalid_capabilities",
                    f"Capabilities not permitted for {app_id}: {', '.join(sorted(disallowed))}",
                    403,
                )
            granted = frozenset(req_set)

        ttl = self.config.session_ttl_seconds if ttl_seconds is None else int(ttl_seconds)
        if ttl < 1 or ttl > self.config.max_session_ttl_seconds:
            raise IdentityError("invalid_ttl", "Session TTL is outside allowed bounds", 422)

        clean_label = _normalize_device_label(device_label)
        now_dt = utcnow()
        now_str = iso_utc(now_dt)
        expires_str = iso_utc(now_dt + timedelta(seconds=ttl))
        session_id = f"sess_{uuid.uuid4().hex}"
        raw_token = f"cs_{app_id}_{secrets.token_urlsafe(32)}"
        token_hash = _sha256_hex(raw_token)

        self.store.create_app_session(
            session_id=session_id,
            token_hash=token_hash,
            user_id=user["user_id"],
            app_id=app_id,
            capabilities=sorted(granted),
            session_version=user["session_version"],
            source_jti=source_jti,
            device_label=clean_label,
            created_at=now_str,
            expires_at=expires_str,
        )
        self.store.record_audit(
            user_id=user["user_id"],
            app_id=app_id,
            session_id=session_id,
            event_kind="app_session_created",
            detail={"capabilities": sorted(granted), "expires_at": expires_str, "device_label": clean_label},
            at=now_str,
        )
        return AppSessionOut(
            session_id=session_id,
            session_token=raw_token,
            user_id=user["user_id"],
            app_id=app_id,
            capabilities=tuple(sorted(granted)),
            age_band=user["age_band"],
            expires_at=expires_str,
            display_name=user.get("display_name") or "",
            email=user.get("email"),
            device_label=clean_label,
        )

    def list_active_sessions(
        self,
        user_id: str,
        *,
        current_session_id: Optional[str] = None,
    ) -> list[dict]:
        rows = self.store.list_active_user_sessions(user_id)
        return [
            {
                "session_id": row["session_id"],
                "app_id": row["app_id"],
                "device_label": row.get("device_label"),
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
                "is_current": bool(current_session_id and row["session_id"] == current_session_id),
            }
            for row in rows
        ]

    def _validate_session_record(
        self,
        session: Optional[dict],
        *,
        expected_app: AppId,
        required_capabilities: frozenset[str] = frozenset(),
        auth_mode: str = "verified_app_session",
    ) -> VerifiedPrincipal:
        if expected_app not in VALID_APP_IDS:
            raise IdentityError("invalid_app_id", f"Unsupported app_id: {expected_app}", 422)
        if session is None:
            raise IdentityError("invalid_session", "Invalid or unknown app session", 401)
        if session["revoked_at"] is not None:
            raise IdentityError("session_revoked", "App session has been revoked", 401)
        if parse_iso(session["expires_at"]) <= utcnow():
            raise IdentityError("session_expired", "App session has expired", 401)

        user = self.store.get_user(session["user_id"])
        if user is None or user["status"] != "active":
            raise IdentityError("user_inactive", "User account is not active", 401)
        if session["session_version"] != user["session_version"]:
            raise IdentityError("session_revoked", "Session invalidated by global revocation", 401)
        if session["app_id"] != expected_app:
            raise IdentityError("wrong_app", f"Session for '{session['app_id']}' cannot access '{expected_app}'", 403)

        granted = frozenset(session["capabilities"]) & APP_CAPABILITIES[expected_app]
        if not required_capabilities.issubset(granted):
            raise IdentityError("missing_capability", "Session lacks required capability", 403)

        return VerifiedPrincipal(
            user_id=user["user_id"],
            app_id=expected_app,
            capabilities=granted,
            auth_mode=auth_mode,  # type: ignore[arg-type]
            age_band=user["age_band"],
            is_verified=True,
            session_id=session["session_id"],
            session_version=user["session_version"],
            expires_at=session["expires_at"],
        )

    def authenticate_session(
        self,
        raw_session_token: str,
        *,
        expected_app: AppId,
        required_capabilities: frozenset[str] = frozenset(),
    ) -> VerifiedPrincipal:
        if not isinstance(raw_session_token, str) or not raw_session_token.strip():
            raise IdentityError("invalid_session", "Missing app session token", 401)
        token_hash = _sha256_hex(raw_session_token.strip())
        session = self.store.get_app_session_by_token_hash(token_hash)
        return self._validate_session_record(
            session,
            expected_app=expected_app,
            required_capabilities=required_capabilities,
        )

    def assert_session_active(
        self,
        session_id: str,
        *,
        expected_app: AppId,
        required_capabilities: frozenset[str] = frozenset(),
    ) -> VerifiedPrincipal:
        if not isinstance(session_id, str) or not session_id.strip():
            raise IdentityError("invalid_session", "Missing session_id", 401)
        session = self.store.get_app_session_by_id(session_id)
        return self._validate_session_record(
            session,
            expected_app=expected_app,
            required_capabilities=required_capabilities,
        )

    def revoke_session(self, user_id: str, session_id: str, *, reason: str = "user_logout") -> bool:
        session = self.store.get_app_session_by_id(session_id)
        if session is None:
            return False
        if session["user_id"] != user_id:
            raise IdentityError("forbidden", "Cannot revoke another user's session", 403)
        now_str = iso_utc()
        revoked = self.store.revoke_app_session(session_id, revoked_at=now_str, reason=reason)
        if revoked:
            self.store.record_audit(
                user_id=user_id,
                app_id=session["app_id"],
                session_id=session_id,
                event_kind="app_session_revoked",
                detail={"reason": reason},
                at=now_str,
            )
        return revoked

    def revoke_all_sessions(
        self,
        user_id: str,
        *,
        app_id: Optional[AppId] = None,
        reason: str = "global_revoke",
    ) -> int:
        if app_id is not None and app_id not in VALID_APP_IDS:
            raise IdentityError("invalid_app_id", f"Unsupported app_id: {app_id}", 422)
        now_str = iso_utc()
        count = self.store.revoke_all_user_sessions(
            user_id,
            app_id=app_id,
            revoked_at=now_str,
            reason=reason,
            bump_session_version=(app_id is None),
        )
        self.store.record_audit(
            user_id=user_id,
            app_id=app_id,
            session_id=None,
            event_kind="all_sessions_revoked",
            detail={"app_id": app_id, "revoked_count": count, "reason": reason, "version_bumped": app_id is None},
            at=now_str,
        )
        return count

    def revoke_jti(self, user_id: str, jti: str, expires_at: str) -> None:
        if not jti or not isinstance(jti, str):
            raise IdentityError("invalid_jti", "jti is required", 422)
        now_str = iso_utc()
        self.store.revoke_jti(jti=jti, user_id=user_id, revoked_at=now_str, expires_at=expires_at)
        self.store.record_audit(
            user_id=user_id,
            app_id=None,
            session_id=None,
            event_kind="jti_revoked",
            detail={"jti": jti},
            at=now_str,
        )

    def create_ws_ticket(self, principal: VerifiedPrincipal, *, origin: str) -> WsTicketOut:
        if not principal.is_verified or not principal.session_id or not principal.app_id:
            raise IdentityError("session_required", "Active app session is required for WebSocket tickets", 403)
        normalized_origin = normalize_origin(origin)
        active = self.assert_session_active(principal.session_id, expected_app=principal.app_id)
        if active.user_id != principal.user_id:
            raise IdentityError("forbidden", "Session ownership mismatch", 403)
        if active.app_id == "messenger" and "messenger:ws" not in active.capabilities:
            raise IdentityError("missing_capability", "Session lacks messenger:ws capability", 403)

        now_dt = utcnow()
        expires_str = iso_utc(now_dt + timedelta(seconds=self.config.ws_ticket_ttl_seconds))
        raw_ticket = f"wst_{secrets.token_urlsafe(32)}"
        self.store.create_ws_ticket(
            ticket_hash=_sha256_hex(raw_ticket),
            session_id=active.session_id or principal.session_id,
            user_id=active.user_id,
            app_id=active.app_id or principal.app_id,
            origin=normalized_origin,
            expires_at=expires_str,
        )
        self.store.record_audit(
            user_id=active.user_id,
            app_id=active.app_id,
            session_id=active.session_id,
            event_kind="ws_ticket_created",
            detail={"origin": normalized_origin, "expires_at": expires_str},
            at=iso_utc(now_dt),
        )
        return WsTicketOut(
            ticket=raw_ticket,
            expires_at=expires_str,
            session_id=active.session_id or principal.session_id,
            app_id=active.app_id or principal.app_id,
        )

    def consume_ws_ticket(
        self,
        raw_ticket: str,
        *,
        expected_app: AppId,
        origin: str,
        required_capabilities: frozenset[str] = frozenset(),
    ) -> VerifiedPrincipal:
        if not isinstance(raw_ticket, str) or not raw_ticket.strip():
            raise IdentityError("invalid_ws_ticket", "Missing WebSocket ticket", 401)
        normalized_origin = normalize_origin(origin)
        ticket_hash = _sha256_hex(raw_ticket.strip())
        ticket = self.store.get_ws_ticket(ticket_hash)
        if ticket is None:
            raise IdentityError("invalid_ws_ticket", "Unknown WebSocket ticket", 401)
        if ticket["consumed_at"] is not None:
            raise IdentityError("ws_ticket_reused", "WebSocket ticket has already been used", 401)
        if parse_iso(ticket["expires_at"]) <= utcnow():
            raise IdentityError("ws_ticket_expired", "WebSocket ticket has expired", 401)
        if ticket["app_id"] != expected_app:
            raise IdentityError("wrong_app", "WebSocket ticket app mismatch", 403)
        if ticket["origin"] != normalized_origin:
            raise IdentityError("origin_mismatch", "WebSocket Origin does not match ticket binding", 403)

        now_str = iso_utc()
        if not self.store.consume_ws_ticket_atomic(ticket_hash, consumed_at=now_str):
            raise IdentityError("ws_ticket_reused", "WebSocket ticket has already been used", 401)

        principal = self.assert_session_active(
            ticket["session_id"],
            expected_app=expected_app,
            required_capabilities=required_capabilities,
        )
        self.store.record_audit(
            user_id=principal.user_id,
            app_id=expected_app,
            session_id=principal.session_id,
            event_kind="ws_ticket_consumed",
            detail={"origin": normalized_origin},
            at=now_str,
        )
        return VerifiedPrincipal(
            user_id=principal.user_id,
            app_id=expected_app,
            capabilities=principal.capabilities,
            auth_mode="verified_ws_ticket",
            age_band=principal.age_band,
            is_verified=True,
            session_id=principal.session_id,
            session_version=principal.session_version,
            expires_at=principal.expires_at,
        )

    def start_identity_link(self, principal: VerifiedPrincipal, *, target_issuer: str) -> dict:
        if not principal.is_verified:
            raise IdentityError("unverified_principal", "Verified principal is required", 401)
        if not isinstance(target_issuer, str) or not target_issuer.strip():
            raise IdentityError("invalid_issuer", "target_issuer is required", 422)
        target = target_issuer.strip()
        now_dt = utcnow()
        expires_str = iso_utc(now_dt + timedelta(seconds=300))
        challenge_id = f"lnk_{uuid.uuid4().hex}"
        nonce = secrets.token_urlsafe(24)
        self.store.create_link_challenge(
            challenge_id=challenge_id,
            user_id=principal.user_id,
            nonce_hash=_sha256_hex(nonce),
            target_issuer=target,
            expires_at=expires_str,
        )
        self.store.record_audit(
            user_id=principal.user_id,
            app_id=principal.app_id,
            session_id=principal.session_id,
            event_kind="identity_link_started",
            detail={"challenge_id": challenge_id, "target_issuer": target},
            at=iso_utc(now_dt),
        )
        return {
            "challenge_id": challenge_id,
            "nonce": nonce,
            "target_issuer": target,
            "expires_at": expires_str,
        }

    def complete_identity_link(
        self,
        principal: VerifiedPrincipal,
        *,
        challenge_id: str,
        proof_jwt: str,
        nonce: Optional[str] = None,
        proof_verifier: Optional[JWTVerifier] = None,
    ) -> dict:
        if not principal.is_verified:
            raise IdentityError("unverified_principal", "Verified principal is required", 401)
        challenge = self.store.get_link_challenge(challenge_id)
        if challenge is None:
            raise IdentityError("challenge_not_found", "Unknown link challenge", 400)
        if challenge["user_id"] != principal.user_id:
            raise IdentityError("forbidden", "Link challenge belongs to another user", 403)
        if challenge["consumed_at"] is not None:
            raise IdentityError("challenge_reused", "Link challenge has already been consumed", 400)
        if parse_iso(challenge["expires_at"]) <= utcnow():
            raise IdentityError("challenge_expired", "Link challenge has expired", 400)

        verifier = proof_verifier or self._extra_verifiers.get(challenge["target_issuer"])
        if verifier is None and self.jwt_verifier.issuer == challenge["target_issuer"]:
            verifier = self.jwt_verifier
        if verifier is None:
            raise IdentityError("unsupported_issuer", "No verifier configured for target_issuer", 400)

        try:
            claims = verifier.verify(proof_jwt)
        except JWTVerificationError as exc:
            raise IdentityError(exc.code, exc.message, 401) from exc

        if claims.issuer != challenge["target_issuer"]:
            raise IdentityError("issuer_mismatch", "proof_jwt issuer does not match challenge target_issuer", 400)

        supplied_nonce = claims.nonce if claims.nonce is not None else nonce
        if not isinstance(supplied_nonce, str) or not supplied_nonce or _sha256_hex(supplied_nonce) != challenge["nonce_hash"]:
            raise IdentityError("invalid_challenge_nonce", "Challenge nonce proof does not match", 403)

        existing = self.store.get_identity_link(claims.issuer, claims.subject)
        if existing is not None and existing["user_id"] != principal.user_id:
            raise IdentityError("identity_already_linked", "Identity is already linked to another user", 409)

        now_str = iso_utc()
        if not self.store.consume_link_challenge(challenge_id, consumed_at=now_str):
            raise IdentityError("challenge_reused", "Link challenge has already been consumed", 400)

        if existing is None:
            self.store.add_identity_link(
                issuer=claims.issuer,
                subject=claims.subject,
                user_id=principal.user_id,
                email_verified=claims.email_verified,
                linked_at=now_str,
                link_proof=f"verified_challenge:{challenge_id}",
            )

        self.store.record_audit(
            user_id=principal.user_id,
            app_id=principal.app_id,
            session_id=principal.session_id,
            event_kind="identity_link_completed",
            detail={"challenge_id": challenge_id, "issuer": claims.issuer},
            at=now_str,
        )
        return {
            "linked": True,
            "user_id": principal.user_id,
            "issuer": claims.issuer,
            "subject": claims.subject,
            "challenge_id": challenge_id,
        }

    def start_pairing(
        self,
        principal: VerifiedPrincipal,
        *,
        ttl_seconds: int = 300,
    ) -> dict:
        if not principal.is_verified:
            raise IdentityError("unverified_principal", "Verified principal is required", 401)
        if principal.session_id and self.store.is_pairing_session(principal.session_id):
            raise IdentityError(
                "pairing_from_paired_device",
                "A paired phone cannot create pairing codes; use the web or desktop app",
                403,
            )
        user = self.store.get_user(principal.user_id)
        if user is None or user["status"] != "active":
            raise IdentityError("user_inactive", "User account is not active", 403)
        ttl = max(30, min(int(ttl_seconds), 300))
        code = "".join(secrets.choice(_PAIR_ALPHABET) for _ in range(8))
        now_dt = utcnow()
        now_str = iso_utc(now_dt)
        expires_str = iso_utc(now_dt + timedelta(seconds=ttl))
        self.store.create_pairing_code(
            code_hash=_sha256_hex(code),
            user_id=principal.user_id,
            created_by_session_id=principal.session_id,
            created_at=now_str,
            expires_at=expires_str,
        )
        self.store.record_audit(
            user_id=principal.user_id,
            app_id=principal.app_id,
            session_id=principal.session_id,
            event_kind="device_pairing_started",
            detail={"expires_at": expires_str, "ttl_seconds": ttl},
            at=now_str,
        )
        api_base = _public_api_base_url()
        payload = f"dubaiio://pair?code={code}"
        out = {"code": code, "expires_at": expires_str, "ttl_seconds": ttl}
        if api_base:
            payload += f"&api={quote(api_base, safe='')}"
            out["api_base_url"] = api_base
        out["qr_payload"] = payload
        return out

    def _pair_throttle_check(self, client_ip: str) -> None:
        now = utcnow()
        cutoff = now - timedelta(seconds=PAIR_WINDOW_SECONDS)
        with self._pair_lock:
            recent = [t for t in self._pair_ip_failures.get(client_ip, []) if t > cutoff]
            self._pair_ip_failures[client_ip] = recent
            if len(recent) >= PAIR_MAX_FAILURES:
                raise IdentityError(
                    "too_many_attempts",
                    "Too many failed pairing attempts. Wait 5 minutes and generate a fresh code.",
                    429,
                )

    def _pair_record_failure(self, client_ip: str, code_hash: str) -> bool:
        """Record a failed attempt; True when this code has now failed too many times."""
        with self._pair_lock:
            self._pair_ip_failures.setdefault(client_ip, []).append(utcnow())
            n = self._pair_code_failures.get(code_hash, 0) + 1
            self._pair_code_failures[code_hash] = n
            return n >= PAIR_MAX_FAILURES

    def complete_pairing(
        self,
        code: str,
        *,
        device_label: Optional[str] = None,
        client_ip: str = "unknown",
        app_id: AppId = "quest",
    ) -> AppSessionOut:
        self._pair_throttle_check(client_ip)
        try:
            return self._complete_pairing(code, device_label=device_label, client_ip=client_ip, app_id=app_id)
        except IdentityError as exc:
            if exc.status_code in (400, 409, 410):
                code_hash = _sha256_hex((code or "").strip().upper()[:128])
                if self._pair_record_failure(client_ip, code_hash):
                    self.store.invalidate_pairing_code(code_hash, at=iso_utc())
                    raise IdentityError(
                        "code_invalidated",
                        "Too many wrong attempts on this code; it is no longer valid. Generate a new one.",
                        429,
                    ) from exc
            raise

    def _complete_pairing(
        self,
        code: str,
        *,
        device_label: Optional[str] = None,
        client_ip: str = "unknown",
        app_id: AppId = "quest",
    ) -> AppSessionOut:
        if app_id not in VALID_APP_IDS:
            raise IdentityError("invalid_app_id", f"Unsupported app_id: {app_id}", 422)
        normalized = (code or "").strip().upper()
        if not normalized or len(normalized) > 128:
            raise IdentityError("invalid_code", "Invalid pairing code", 400)

        code_hash = _sha256_hex(normalized)
        record = self.store.get_pairing_code(code_hash)
        if record is None:
            raise IdentityError("invalid_code", "Invalid pairing code", 400)
        if record["consumed_at"] is not None:
            raise IdentityError("code_already_used", "Pairing code has already been used", 409)
        if parse_iso(record["expires_at"]) <= utcnow():
            raise IdentityError("expired_code", "Pairing code has expired", 410)

        session_out = self.issue_user_session(
            record["user_id"],
            app_id=app_id,
            device_label=device_label or "iPhone",
        )
        now_str = iso_utc()
        if not self.store.consume_pairing_code_atomic(
            code_hash,
            consumed_at=now_str,
            consumed_by_session_id=session_out.session_id,
        ):
            # Another concurrent request consumed the code first — revoke the just-minted session.
            self.store.revoke_app_session(session_out.session_id, revoked_at=now_str, reason="pairing_race")
            raise IdentityError("code_already_used", "Pairing code has already been used", 409)

        self.store.record_audit(
            user_id=record["user_id"],
            app_id="quest",
            session_id=session_out.session_id,
            event_kind="device_pairing_completed",
            detail={"device_label": session_out.device_label},
            at=now_str,
        )
        return session_out
