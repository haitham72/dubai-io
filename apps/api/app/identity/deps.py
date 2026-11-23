"""FastAPI HTTP and WebSocket dependencies and anti-spoofing guards for CS-B1."""
from __future__ import annotations

import re
from threading import RLock
from typing import Callable, Optional
from urllib.parse import urlsplit

from fastapi import Depends, Header, HTTPException, Request, WebSocket
from starlette.requests import HTTPConnection

from ..config import settings
from .config import IdentityConfig
from .jwt import JWTVerifier
from .models import APP_CAPABILITIES, VALID_APP_IDS, AppId, IdentityError, VerifiedPrincipal
from .service import IdentityService, normalize_origin
from .store import IdentityStore

LEGACY_ANON_COOKIE = "dubaiio_lab_session"

SPOOFED_IDENTITY_HEADERS: frozenset[str] = frozenset({
    "x-user-id",
    "x-owner",
    "x-owner-id",
    "x-dubaiio-user",
    "x-principal",
})
LEGACY_POC_HEADER_RE = re.compile(r"^x-m[i]rsal-user$", re.IGNORECASE)

_default_service_lock = RLock()
_default_service: Optional[IdentityService] = None


def _http_from_identity_error(exc: IdentityError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


def reject_spoofed_identity_headers(request: HTTPConnection) -> None:
    """Reject any caller-supplied identity override header with HTTP 400."""
    for header_name in request.headers.keys():
        lowered = header_name.strip().lower()
        if lowered in SPOOFED_IDENTITY_HEADERS or LEGACY_POC_HEADER_RE.match(lowered):
            raise HTTPException(
                status_code=400,
                detail={"code": "spoofed_identity_header", "message": f"Header '{header_name}' is not allowed"},
            )


def reject_spoofed_query_identity(request: HTTPConnection, principal: VerifiedPrincipal) -> None:
    """Reject mismatched owner/user_id or server-derived field overrides in query parameters."""
    params = request.query_params
    for key in ("owner", "owner_id", "user_id"):
        if key in params:
            val = params.get(key)
            if val != principal.user_id:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "owner_mismatch", "message": f"Query '{key}' does not match verified principal"},
                )
    for forbidden_key in ("age_band", "age_source", "provenance", "scope"):
        if forbidden_key in params:
            raise HTTPException(
                status_code=422,
                detail={"code": "forbidden_override", "message": f"Query '{forbidden_key}' cannot be set by caller"},
            )


def get_identity_service(request: HTTPConnection) -> IdentityService:
    """Resolve IdentityService from app.state or lazy environment configuration."""
    svc = getattr(request.app.state, "identity_service", None)
    if svc is not None:
        return svc

    global _default_service
    with _default_service_lock:
        if _default_service is None:
            cfg = IdentityConfig.from_env()
            if not cfg.jwt_issuer or (not cfg.jwt_hs256_secret and not cfg.jwt_jwks_url):
                raise HTTPException(
                    status_code=503,
                    detail={"code": "identity_unconfigured", "message": "Identity service is not configured"},
                )
            verifier = JWTVerifier(
                issuer=cfg.jwt_issuer,
                audience=cfg.jwt_audience,
                hs256_secret=cfg.jwt_hs256_secret,
                jwks_url=cfg.jwt_jwks_url,
                clock_skew_s=cfg.clock_skew_seconds,
                jwks_ttl_s=cfg.jwks_ttl_seconds,
                jwks_refresh_cooldown_s=cfg.jwks_refresh_cooldown_seconds,
            )
            store = IdentityStore(settings.database_url or (settings.data_dir / "identity.sqlite3"))
            _default_service = IdentityService(store, verifier, config=cfg)
        return _default_service


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    return parts[1].strip()


def require_verified_jwt(
    request: Request,
    authorization: str | None = Header(default=None),
    service: IdentityService = Depends(get_identity_service),
) -> VerifiedPrincipal:
    """FastAPI dependency requiring a valid cryptographic Bearer JWT."""
    reject_spoofed_identity_headers(request)
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(
            status_code=401,
            detail={"code": "missing_bearer_jwt", "message": "Verified Bearer JWT is required"},
        )
    try:
        principal = service.authenticate_jwt(token)
    except IdentityError as exc:
        raise _http_from_identity_error(exc) from exc
    reject_spoofed_query_identity(request, principal)
    return principal


def _reject_if_legacy_anon_cookie_copied(request: HTTPConnection, token: str) -> None:
    anon_cookie = request.cookies.get(LEGACY_ANON_COOKIE)
    if anon_cookie and token == anon_cookie:
        raise HTTPException(
            status_code=401,
            detail={"code": "anonymous_cookie_rejected", "message": "Anonymous lab session cookie is not accepted"},
        )


def require_app_principal(
    app_id: AppId,
    required_capabilities: frozenset[str] = frozenset(),
    *,
    allow_jwt_fallback: bool = False,
) -> Callable[..., VerifiedPrincipal]:
    """Return a FastAPI dependency enforcing per-app session (and optional JWT fallback) + capabilities."""
    if app_id not in VALID_APP_IDS:
        raise ValueError(f"Unsupported app_id: {app_id}")

    def _dependency(
        request: Request,
        x_app_session: str | None = Header(default=None, alias="X-App-Session"),
        authorization: str | None = Header(default=None),
        service: IdentityService = Depends(get_identity_service),
    ) -> VerifiedPrincipal:
        reject_spoofed_identity_headers(request)
        cookie_name = f"cs_session_{app_id}"
        raw_token = (x_app_session or "").strip() or (request.cookies.get(cookie_name) or "").strip()

        if raw_token:
            _reject_if_legacy_anon_cookie_copied(request, raw_token)
            try:
                principal = service.authenticate_session(
                    raw_token,
                    expected_app=app_id,
                    required_capabilities=required_capabilities,
                )
            except IdentityError as exc:
                raise _http_from_identity_error(exc) from exc
            reject_spoofed_query_identity(request, principal)
            return principal

        if allow_jwt_fallback:
            bearer = _extract_bearer_token(authorization)
            if bearer:
                try:
                    jwt_principal = service.authenticate_jwt(bearer)
                except IdentityError as exc:
                    raise _http_from_identity_error(exc) from exc
                allowed = APP_CAPABILITIES[app_id]
                if not required_capabilities.issubset(allowed):
                    raise HTTPException(
                        status_code=403,
                        detail={"code": "missing_capability", "message": "Requested capability not valid for app"},
                    )
                principal = VerifiedPrincipal(
                    user_id=jwt_principal.user_id,
                    app_id=app_id,
                    capabilities=allowed,
                    auth_mode="verified_jwt",
                    age_band=jwt_principal.age_band,
                    is_verified=True,
                    session_id=None,
                    issuer=jwt_principal.issuer,
                    subject=jwt_principal.subject,
                    session_version=jwt_principal.session_version,
                    expires_at=jwt_principal.expires_at,
                )
                reject_spoofed_query_identity(request, principal)
                return principal

        raise HTTPException(
            status_code=401,
            detail={"code": "missing_app_session", "message": f"Verified '{app_id}' session is required"},
        )

    return _dependency


def _same_ws_origin(origin_header: str, websocket: WebSocket) -> bool:
    try:
        norm_origin = normalize_origin(origin_header)
    except IdentityError:
        return False
    parsed_origin = urlsplit(norm_origin)
    ws_scheme = "https" if websocket.url.scheme in {"wss", "https"} else "http"
    ws_host = (websocket.url.hostname or "").lower()
    if not ws_host and "host" in websocket.headers:
        host_hdr = websocket.headers["host"].split(":")[0].lower()
        ws_host = host_hdr
    ws_port = websocket.url.port
    default_ws_port = 443 if ws_scheme == "https" else 80
    effective_ws_port = ws_port if (ws_port is not None and ws_port != default_ws_port) else None

    origin_port = parsed_origin.port
    default_origin_port = 443 if parsed_origin.scheme == "https" else 80
    effective_origin_port = origin_port if (origin_port is not None and origin_port != default_origin_port) else None

    return (parsed_origin.scheme, (parsed_origin.hostname or "").lower(), effective_origin_port) == (
        ws_scheme,
        ws_host,
        effective_ws_port,
    )


def require_ws_principal(
    websocket: WebSocket,
    *,
    app_id: AppId,
    required_capabilities: frozenset[str] = frozenset(),
    service: Optional[IdentityService] = None,
) -> VerifiedPrincipal:
    """Validate WebSocket Origin plus single-use ticket or same-origin cs_session_<app_id> cookie."""
    reject_spoofed_identity_headers(websocket)
    svc = service or get_identity_service(websocket)
    origin = websocket.headers.get("origin", "")
    if not origin.strip():
        raise HTTPException(
            status_code=403,
            detail={"code": "missing_origin", "message": "Origin header is required for WebSocket handshake"},
        )

    ticket = (websocket.query_params.get("ticket") or "").strip()
    if ticket:
        try:
            principal = svc.consume_ws_ticket(
                ticket,
                expected_app=app_id,
                origin=origin,
                required_capabilities=required_capabilities,
            )
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc
        reject_spoofed_query_identity(websocket, principal)
        return principal

    cookie_token = (websocket.cookies.get(f"cs_session_{app_id}") or "").strip()
    if cookie_token:
        _reject_if_legacy_anon_cookie_copied(websocket, cookie_token)
        if not _same_ws_origin(origin, websocket):
            raise HTTPException(
                status_code=403,
                detail={"code": "origin_mismatch", "message": "Cross-origin WebSocket cookie auth rejected"},
            )
        try:
            principal = svc.authenticate_session(
                cookie_token,
                expected_app=app_id,
                required_capabilities=required_capabilities,
            )
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc
        reject_spoofed_query_identity(websocket, principal)
        return principal

    raise HTTPException(
        status_code=401,
        detail={"code": "missing_ws_credentials", "message": "Valid WebSocket ticket or app session cookie required"},
    )
