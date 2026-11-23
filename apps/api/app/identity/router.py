"""FastAPI JSON router for /api/identity/* endpoints."""
from __future__ import annotations

import hashlib
from typing import Any, Callable, Literal, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from .deps import (
    LEGACY_ANON_COOKIE,
    _extract_bearer_token,
    _http_from_identity_error,
    _reject_if_legacy_anon_cookie_copied,
    get_identity_service,
    reject_spoofed_identity_headers,
    reject_spoofed_query_identity,
    require_verified_jwt,
)
from .models import VALID_APP_IDS, AppId, IdentityError, VerifiedPrincipal
from .service import IdentityService, normalize_origin


class AgeBandIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age_band: Literal["under_13", "teen_13_17", "adult_18_plus"]


class AdoptSessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proof_cookie_token: Optional[str] = Field(default=None, min_length=1, max_length=512)


class CreateSessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_id: AppId
    requested_capabilities: Optional[list[str]] = Field(default=None, max_length=32)
    set_cookie: bool = False
    ttl_seconds: Optional[int] = Field(default=None, ge=1)


class RevokeAllIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_id: Optional[AppId] = None
    reason: str = Field(default="global_revoke", min_length=1, max_length=120)


class WsTicketIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: Optional[str] = Field(default=None, max_length=512)
    app_id: Optional[AppId] = None


class StartLinkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_issuer: str = Field(min_length=1, max_length=512)


class CompleteLinkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: str = Field(min_length=1, max_length=128)
    proof_jwt: str = Field(min_length=1, max_length=16384)
    nonce: Optional[str] = Field(default=None, max_length=512)


def _authenticate_session_for_identity_route(
    request: Request,
    service: IdentityService,
    *,
    x_app_session: Optional[str],
    x_app_id: Optional[str],
    explicit_app_id: Optional[AppId] = None,
) -> Optional[VerifiedPrincipal]:
    if x_app_session:
        token = x_app_session.strip()
        _reject_if_legacy_anon_cookie_copied(request, token)
        expected_app: Optional[str] = explicit_app_id or (x_app_id.strip() if x_app_id else None)
        if expected_app is None:
            # Look up the session's own app_id on shared /api/identity/* self-management routes.
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            sess = service.store.get_app_session_by_token_hash(token_hash)
            if sess is None:
                raise HTTPException(status_code=401, detail={"code": "invalid_session", "message": "Invalid app session"})
            expected_app = sess["app_id"]
        if expected_app not in VALID_APP_IDS:
            raise HTTPException(status_code=422, detail={"code": "invalid_app_id", "message": "Unsupported app_id"})
        try:
            return service.authenticate_session(token, expected_app=expected_app)  # type: ignore[arg-type]
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc

    apps_to_check: tuple[AppId, ...] = (explicit_app_id,) if explicit_app_id else ("quest", "community", "messenger")
    for app_name in apps_to_check:
        cookie_val = (request.cookies.get(f"cs_session_{app_name}") or "").strip()
        if cookie_val:
            _reject_if_legacy_anon_cookie_copied(request, cookie_val)
            try:
                return service.authenticate_session(cookie_val, expected_app=app_name)
            except IdentityError as exc:
                raise _http_from_identity_error(exc) from exc
    return None


def _principal_to_dict(principal: VerifiedPrincipal) -> dict[str, Any]:
    return {
        "user_id": principal.user_id,
        "app_id": principal.app_id,
        "capabilities": sorted(principal.capabilities),
        "auth_mode": principal.auth_mode,
        "age_band": principal.age_band,
        "is_minor_protected": principal.is_minor_protected,
        "is_verified": principal.is_verified,
        "session_id": principal.session_id,
        "session_version": principal.session_version,
        "expires_at": principal.expires_at,
    }


def create_identity_router(
    get_service: Optional[Callable[[Request], IdentityService]] = None,
    *,
    memory_token_handler: Any = None,
) -> APIRouter:
    """Create the shared /api/identity FastAPI router."""
    service_dep = get_service or get_identity_service
    router = APIRouter(prefix="/api/identity", tags=["identity"])

    def _require_verified_any(
        request: Request,
        authorization: str | None = Header(default=None),
        x_app_session: str | None = Header(default=None, alias="X-App-Session"),
        x_app_id: str | None = Header(default=None, alias="X-App-Id"),
        service: IdentityService = Depends(service_dep),
    ) -> VerifiedPrincipal:
        reject_spoofed_identity_headers(request)
        bearer = _extract_bearer_token(authorization)
        if bearer:
            try:
                principal = service.authenticate_jwt(bearer)
            except IdentityError as exc:
                raise _http_from_identity_error(exc) from exc
            reject_spoofed_query_identity(request, principal)
            return principal

        sess_principal = _authenticate_session_for_identity_route(
            request,
            service,
            x_app_session=x_app_session,
            x_app_id=x_app_id,
        )
        if sess_principal is not None:
            reject_spoofed_query_identity(request, sess_principal)
            return sess_principal

        raise HTTPException(
            status_code=401,
            detail={"code": "authentication_required", "message": "Verified JWT or app session is required"},
        )

    def _require_jwt_with_custom_dep(
        request: Request,
        authorization: str | None = Header(default=None),
        service: IdentityService = Depends(service_dep),
    ) -> VerifiedPrincipal:
        return require_verified_jwt(request, authorization=authorization, service=service)

    @router.get("/me")
    def get_me(
        principal: VerifiedPrincipal = Depends(_require_verified_any),
        service: IdentityService = Depends(service_dep),
    ) -> dict[str, Any]:
        try:
            refreshed = service.refresh_principal(principal)
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc
        return _principal_to_dict(refreshed)

    @router.post("/age-band")
    def declare_age_band(
        body: AgeBandIn,
        principal: VerifiedPrincipal = Depends(_require_verified_any),
        service: IdentityService = Depends(service_dep),
    ) -> dict[str, Any]:
        try:
            updated = service.set_age_band(principal, age_band=body.age_band)
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc
        return {
            "user_id": updated.user_id,
            "age_band": updated.age_band,
            "age_source": "self_declared",
            "is_minor_protected": updated.is_minor_protected,
        }

    @router.post("/adopt-session")
    def adopt_session(
        request: Request,
        body: Optional[AdoptSessionIn] = Body(default=None),
        principal: VerifiedPrincipal = Depends(_require_verified_any),
        service: IdentityService = Depends(service_dep),
    ) -> dict[str, Any]:
        proof_token = (body.proof_cookie_token if body and body.proof_cookie_token else None) or request.cookies.get(
            LEGACY_ANON_COOKIE, ""
        )
        try:
            return service.adopt_session_owner(principal, proof_cookie_token=proof_token)
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc

    @router.post("/sessions")
    def create_session(
        request: Request,
        response: Response,
        body: CreateSessionIn,
        principal: VerifiedPrincipal = Depends(_require_jwt_with_custom_dep),
        service: IdentityService = Depends(service_dep),
    ) -> dict[str, Any]:
        requested = set(body.requested_capabilities) if body.requested_capabilities is not None else None
        try:
            session_out = service.create_app_session(
                principal,
                app_id=body.app_id,
                requested_capabilities=requested,
                ttl_seconds=body.ttl_seconds,
            )
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc

        if body.set_cookie:
            max_age = body.ttl_seconds if body.ttl_seconds is not None else service.config.session_ttl_seconds
            response.set_cookie(
                key=f"cs_session_{body.app_id}",
                value=session_out.session_token,
                httponly=True,
                samesite="lax",
                secure=request.url.scheme == "https",
                max_age=max_age,
            )
        return {
            "session_id": session_out.session_id,
            "session_token": session_out.session_token,
            "user_id": session_out.user_id,
            "app_id": session_out.app_id,
            "capabilities": list(session_out.capabilities),
            "age_band": session_out.age_band,
            "expires_at": session_out.expires_at,
        }

    @router.delete("/sessions/{session_id}")
    def delete_session(
        session_id: str,
        principal: VerifiedPrincipal = Depends(_require_verified_any),
        service: IdentityService = Depends(service_dep),
    ) -> dict[str, Any]:
        try:
            revoked = service.revoke_session(principal.user_id, session_id)
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc
        if not revoked:
            raise HTTPException(status_code=404, detail={"code": "session_not_found", "message": "Session not found"})
        return {"revoked": True, "session_id": session_id}

    @router.post("/sessions/revoke-all")
    def revoke_all(
        body: Optional[RevokeAllIn] = Body(default=None),
        principal: VerifiedPrincipal = Depends(_require_verified_any),
        service: IdentityService = Depends(service_dep),
    ) -> dict[str, Any]:
        payload = body or RevokeAllIn()
        try:
            count = service.revoke_all_sessions(
                principal.user_id,
                app_id=payload.app_id,
                reason=payload.reason,
            )
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc
        return {"revoked_count": count, "app_id": payload.app_id}

    @router.post("/ws-ticket")
    def issue_ws_ticket(
        request: Request,
        body: Optional[WsTicketIn] = Body(default=None),
        x_app_session: str | None = Header(default=None, alias="X-App-Session"),
        x_app_id: str | None = Header(default=None, alias="X-App-Id"),
        service: IdentityService = Depends(service_dep),
    ) -> dict[str, Any]:
        reject_spoofed_identity_headers(request)
        explicit_app = body.app_id if body else None
        sess_principal = _authenticate_session_for_identity_route(
            request,
            service,
            x_app_session=x_app_session,
            x_app_id=x_app_id,
            explicit_app_id=explicit_app,
        )
        if sess_principal is None:
            raise HTTPException(
                status_code=401,
                detail={"code": "session_required", "message": "Active app session is required for WS ticket"},
            )
        reject_spoofed_query_identity(request, sess_principal)

        header_origin = (request.headers.get("origin") or "").strip()
        body_origin = (body.origin or "").strip() if body and body.origin else ""
        if header_origin and body_origin:
            try:
                if normalize_origin(header_origin) != normalize_origin(body_origin):
                    raise HTTPException(
                        status_code=403,
                        detail={"code": "origin_mismatch", "message": "Body origin does not match Origin header"},
                    )
            except IdentityError as exc:
                raise _http_from_identity_error(exc) from exc
        effective_origin = header_origin or body_origin
        try:
            ticket_out = service.create_ws_ticket(sess_principal, origin=effective_origin)
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc
        return {
            "ticket": ticket_out.ticket,
            "expires_at": ticket_out.expires_at,
            "session_id": ticket_out.session_id,
            "app_id": ticket_out.app_id,
        }

    @router.post("/links/start")
    def start_link(
        body: StartLinkIn,
        principal: VerifiedPrincipal = Depends(_require_verified_any),
        service: IdentityService = Depends(service_dep),
    ) -> dict[str, Any]:
        try:
            return service.start_identity_link(principal, target_issuer=body.target_issuer)
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc

    @router.post("/links/complete")
    def complete_link(
        body: CompleteLinkIn,
        principal: VerifiedPrincipal = Depends(_require_verified_any),
        service: IdentityService = Depends(service_dep),
    ) -> dict[str, Any]:
        try:
            return service.complete_identity_link(
                principal,
                challenge_id=body.challenge_id,
                proof_jwt=body.proof_jwt,
                nonce=body.nonce,
            )
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc

    # CS-B5 temporal_memory owner-device token routes.
    def _resolve_memory_token_handler(request: Request) -> Any:
        handler = (
            memory_token_handler
            or getattr(request.app.state, "memory_token_handler", None)
            or getattr(request.app.state, "memory_token_service", None)
        )
        if handler is None:
            raise HTTPException(
                status_code=501,
                detail={"code": "not_implemented", "message": "Memory device token service is not mounted"},
            )
        return handler

    def _require_memory_device_token_cap(principal: VerifiedPrincipal) -> None:
        if principal.app_id != "quest" or "memory:device_token" not in principal.capabilities:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "missing_capability",
                    "message": "Quest session with memory:device_token capability is required",
                },
            )

    @router.get("/memory-device-token")
    def list_memory_device_tokens(
        request: Request,
        principal: VerifiedPrincipal = Depends(_require_verified_any),
    ) -> Any:
        handler = _resolve_memory_token_handler(request)
        _require_memory_device_token_cap(principal)
        try:
            if callable(getattr(handler, "list_tokens", None)):
                return {"tokens": handler.list_tokens(principal)}
            return handler.list(principal)
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc

    @router.post("/memory-device-token")
    def mint_memory_device_token(
        request: Request,
        body: Optional[dict[str, Any]] = Body(default=None),
        principal: VerifiedPrincipal = Depends(_require_verified_any),
    ) -> Any:
        handler = _resolve_memory_token_handler(request)
        _require_memory_device_token_cap(principal)
        try:
            return handler.mint(principal, body or {})
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc

    @router.delete("/memory-device-token/{tm_token_id}")
    def revoke_memory_device_token(
        tm_token_id: str,
        request: Request,
        principal: VerifiedPrincipal = Depends(_require_verified_any),
    ) -> Any:
        handler = _resolve_memory_token_handler(request)
        _require_memory_device_token_cap(principal)
        try:
            return handler.revoke(principal, tm_token_id)
        except IdentityError as exc:
            raise _http_from_identity_error(exc) from exc

    return router
