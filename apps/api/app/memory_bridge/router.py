"""FastAPI JSON router for /api/v1/memory-bridge endpoints."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
from typing import Any, Callable, Mapping, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.identity.deps import (
    _http_from_identity_error,
    _reject_if_legacy_anon_cookie_copied,
    get_identity_service as default_get_identity_service,
    reject_spoofed_identity_headers,
    reject_spoofed_query_identity,
)
from app.identity.models import VALID_APP_IDS, AppId, IdentityError, VerifiedPrincipal
from app.identity.service import IdentityService

from .bridge import MemoryBridge
from .models import (
    MEMORY_SCOPES,
    AppId as BridgeAppId,
    ConsentDeniedError,
    ConsentScopeKind,
    ConversationAIMode,
    FactResolutionAction,
    GroupConsentSnapshot,
    HostApp,
    MemoryBridgeError,
    MemoryBridgeUnavailable,
    MemoryRecordInput,
    MemoryScope,
    MinorProtectionError,
    SensitiveContentError,
    SourceKind,
)


class SourceConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_kind: SourceKind
    enabled: bool
    allow_interest_export: bool = False
    forget_on_revoke: bool = True
    idempotency_key: Optional[str] = Field(default=None, max_length=256)


class AppConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_id: BridgeAppId
    read_enabled: bool
    write_enabled: bool
    allow_interest_export_to_community: bool = False
    allow_cross_source_recall: bool = False


class ConversationConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str = Field(min_length=1, max_length=256)
    ai_mode: ConversationAIMode
    allow_interest_export: bool = False
    forget_on_withdraw: bool = False
    idempotency_key: Optional[str] = Field(default=None, max_length=256)


class GroupConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str = Field(min_length=1, max_length=256)
    caller_is_member: bool
    all_active_members_ai_enabled: bool
    cited_authors_save_enabled: bool
    membership_revision: int = Field(default=1, ge=1)


class WriteRecordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_id: str = Field(min_length=1, max_length=256)
    source_kind: SourceKind
    source_id: str = Field(min_length=1, max_length=256)
    host_app: HostApp
    author_id: Optional[str] = Field(default=None, max_length=256)
    text: str = Field(min_length=1, max_length=32000)
    valid_time: str = Field(min_length=1, max_length=128)
    scope: Optional[str] = Field(default=None, max_length=64)
    text_orig: Optional[str] = Field(default=None, max_length=32000)
    subject_path: Optional[str] = Field(default=None, max_length=256)
    explicit_user_confirm: bool = False
    allow_sensitive_confirmed: bool = False
    demo_data: bool = False
    group_consent: Optional[GroupConsentIn] = None
    expected_consent_generation: Optional[int] = Field(default=None, ge=1)
    # Explicit spoof-trap fields so caller overrides return deterministic 403 errors.
    owner: Optional[str] = None
    owner_id: Optional[str] = None
    user_id: Optional[str] = None
    provenance: Optional[str] = None
    age_band: Optional[str] = None


class SignalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_kind: SourceKind
    source_id: str = Field(min_length=1, max_length=256)
    topic_slug: str = Field(min_length=1, max_length=128)
    option_key: str = Field(min_length=1, max_length=128)
    at: str = Field(min_length=1, max_length=128)
    weight: float = Field(default=1.0, gt=0.0, le=1.0)
    owner: Optional[str] = None
    owner_id: Optional[str] = None
    user_id: Optional[str] = None
    age_band: Optional[str] = None


class ResolveFactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: FactResolutionAction
    new_text: Optional[str] = Field(default=None, max_length=32000)
    valid_from: Optional[str] = Field(default=None, max_length=128)
    host_app: Optional[BridgeAppId] = None


class QuestContextIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(default="", max_length=4000)
    max_tokens: int = Field(default=1500, ge=100, le=8000)


class MessengerContextIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_consent: GroupConsentIn
    query: str = Field(default="", max_length=4000)
    limit: int = Field(default=20, ge=1, le=100)


class MessengerRecallIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(default="", max_length=4000)
    limit: int = Field(default=10, ge=1, le=100)


class ForgetRecordsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_ids: list[str] = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=1, max_length=256)
    host_app: Optional[BridgeAppId] = None


class ForgetConversationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)


class ForgetSourceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_kind: SourceKind
    idempotency_key: str = Field(min_length=1, max_length=256)
    host_app: Optional[BridgeAppId] = None


def _default_get_bridge(request: Request) -> MemoryBridge:
    bridge = getattr(request.app.state, "memory_bridge", None)
    if bridge is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "memory_bridge_unavailable", "message": "MemoryBridge is not mounted"},
        )
    return bridge


def _http_from_bridge_error(exc: MemoryBridgeError) -> HTTPException:
    if isinstance(exc, MinorProtectionError):
        return HTTPException(
            status_code=403,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, ConsentDeniedError):
        status = exc.status_code if exc.status_code in (401, 403, 409) else 403
        return HTTPException(
            status_code=status,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, SensitiveContentError):
        status = exc.status_code if exc.status_code in (400, 422) else 400
        return HTTPException(
            status_code=status,
            detail={"code": exc.code, "category": exc.category, "message": str(exc)},
        )
    if isinstance(exc, MemoryBridgeUnavailable):
        return HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": str(exc)},
        )
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


def _reject_caller_spoof_fields(
    *,
    owner: Optional[str] = None,
    owner_id: Optional[str] = None,
    user_id: Optional[str] = None,
    provenance: Optional[str] = None,
    age_band: Optional[str] = None,
) -> None:
    if owner is not None or owner_id is not None or user_id is not None:
        raise HTTPException(
            status_code=403,
            detail={"code": "owner_spoof_rejected", "message": "Caller cannot supply owner or user_id"},
        )
    if provenance is not None:
        raise HTTPException(
            status_code=403,
            detail={"code": "provenance_spoof_rejected", "message": "Caller cannot supply provenance"},
        )
    if age_band is not None:
        raise HTTPException(
            status_code=403,
            detail={"code": "age_band_spoof_rejected", "message": "Caller cannot supply age_band"},
        )


def _check_required_capability(principal: VerifiedPrincipal, required_cap: str) -> None:
    if required_cap not in principal.capabilities:
        raise HTTPException(
            status_code=403,
            detail={"code": "missing_capability", "message": f"Missing required capability: {required_cap}"},
        )


def create_memory_bridge_router(
    get_bridge: Optional[Callable[[Request], MemoryBridge]] = None,
    *,
    get_identity_service: Optional[Callable[[Request], IdentityService]] = None,
) -> APIRouter:
    """Create the shared /api/v1/memory-bridge FastAPI router."""
    bridge_dep = get_bridge or _default_get_bridge
    identity_dep = get_identity_service or default_get_identity_service
    router = APIRouter(prefix="/api/v1/memory-bridge", tags=["memory-bridge"])

    def _require_bridge_principal(
        allowed_apps: tuple[AppId, ...],
        cap_by_app: Mapping[AppId, frozenset[str]],
    ) -> Callable[..., VerifiedPrincipal]:
        def _dependency(
            request: Request,
            service: IdentityService = Depends(identity_dep),
        ) -> VerifiedPrincipal:
            reject_spoofed_identity_headers(request)
            x_app_session = (request.headers.get("x-app-session") or "").strip()
            x_app_id = (request.headers.get("x-app-id") or "").strip()

            if x_app_session:
                _reject_if_legacy_anon_cookie_copied(request, x_app_session)
                token_hash = hashlib.sha256(x_app_session.encode("utf-8")).hexdigest()
                sess = service.store.get_app_session_by_token_hash(token_hash)
                if sess is None:
                    raise HTTPException(
                        status_code=401,
                        detail={"code": "invalid_session", "message": "Invalid app session"},
                    )
                sess_app = str(sess["app_id"])
                if sess_app not in VALID_APP_IDS:
                    raise HTTPException(
                        status_code=422,
                        detail={"code": "invalid_app_id", "message": "Unsupported app_id"},
                    )
                if x_app_id and x_app_id != sess_app:
                    raise HTTPException(
                        status_code=403,
                        detail={"code": "wrong_app", "message": f"Session app '{sess_app}' does not match X-App-Id"},
                    )
                try:
                    principal = service.authenticate_session(
                        x_app_session,
                        expected_app=sess_app,  # type: ignore[arg-type]
                    )
                except IdentityError as exc:
                    raise _http_from_identity_error(exc) from exc
                if principal.app_id not in allowed_apps:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "code": "wrong_app",
                            "message": f"Session for '{principal.app_id}' is not permitted on this route",
                        },
                    )
                needed = cap_by_app.get(principal.app_id, frozenset())
                if not needed.issubset(principal.capabilities):
                    raise HTTPException(
                        status_code=403,
                        detail={"code": "missing_capability", "message": "Session lacks required capability"},
                    )
                reject_spoofed_query_identity(request, principal)
                return principal

            # Cookie fallback (`cs_session_<app_id>`)
            check_order: list[AppId] = list(allowed_apps)
            if x_app_id and x_app_id in allowed_apps:
                check_order = [x_app_id] + [a for a in allowed_apps if a != x_app_id]  # type: ignore[list-item]

            for app_name in check_order:
                cookie_val = (request.cookies.get(f"cs_session_{app_name}") or "").strip()
                if cookie_val:
                    _reject_if_legacy_anon_cookie_copied(request, cookie_val)
                    try:
                        principal = service.authenticate_session(
                            cookie_val,
                            expected_app=app_name,
                            required_capabilities=cap_by_app.get(app_name, frozenset()),
                        )
                    except IdentityError as exc:
                        raise _http_from_identity_error(exc) from exc
                    reject_spoofed_query_identity(request, principal)
                    return principal

            # If only a disallowed app cookie is present, return 403 wrong_app (after checking validity).
            for other_app in ("quest", "community", "messenger"):
                if other_app in allowed_apps:
                    continue
                cookie_val = (request.cookies.get(f"cs_session_{other_app}") or "").strip()
                if cookie_val:
                    _reject_if_legacy_anon_cookie_copied(request, cookie_val)
                    try:
                        service.authenticate_session(cookie_val, expected_app=other_app)  # type: ignore[arg-type]
                    except IdentityError as exc:
                        raise _http_from_identity_error(exc) from exc
                    raise HTTPException(
                        status_code=403,
                        detail={"code": "wrong_app", "message": f"Session for '{other_app}' is not permitted on this route"},
                    )

            raise HTTPException(
                status_code=401,
                detail={"code": "missing_app_session", "message": "Verified app session is required"},
            )

        return _dependency

    _ALL_READ_CAPS: dict[AppId, frozenset[str]] = {
        "quest": frozenset({"memory:read:owner"}),
        "community": frozenset({"memory:read:interests"}),
        "messenger": frozenset({"memory:read:chat"}),
    }
    _ALL_WRITE_CAPS: dict[AppId, frozenset[str]] = {
        "quest": frozenset({"memory:write:owner"}),
        "community": frozenset({"memory:write:community"}),
        "messenger": frozenset({"memory:write:chat"}),
    }
    _ALL_FORGET_CAPS: dict[AppId, frozenset[str]] = {
        "quest": frozenset({"memory:forget:owner"}),
        "community": frozenset({"memory:forget:community"}),
        "messenger": frozenset({"memory:forget:chat"}),
    }

    # ----------------------------------------------------------------- Consent
    @router.get("/consent")
    def get_consent(
        scope_kind: Optional[ConsentScopeKind] = Query(default=None),
        scope_id: Optional[str] = Query(default=None),
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest", "community", "messenger"), _ALL_READ_CAPS)
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        if scope_id is not None and scope_kind is None:
            raise HTTPException(
                status_code=422,
                detail={"code": "missing_scope_kind", "message": "scope_kind is required when scope_id is supplied"},
            )
        try:
            if scope_kind is not None and scope_id is not None:
                return {"grant": asdict(bridge.get_consent(principal, scope_kind, scope_id))}
            grants = bridge.list_consents(principal, scope_kind=scope_kind)
            return {"grants": [asdict(g) for g in grants]}
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.put("/consent/source")
    def put_source_consent(
        body: SourceConsentIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest", "community", "messenger"), _ALL_WRITE_CAPS)
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        if principal.app_id == "community" and body.source_kind != "community":
            raise HTTPException(
                status_code=403,
                detail={"code": "app_scope_mismatch", "message": "community cannot manage non-community source consent"},
            )
        if principal.app_id == "messenger" and body.source_kind != "messenger":
            raise HTTPException(
                status_code=403,
                detail={"code": "app_scope_mismatch", "message": "messenger cannot manage non-messenger source consent"},
            )
        if not body.enabled and body.forget_on_revoke and principal.app_id is not None:
            needed = next(iter(_ALL_FORGET_CAPS[principal.app_id]))
            _check_required_capability(principal, needed)
        try:
            grant, receipt = bridge.set_source_consent(
                principal,
                body.source_kind,
                enabled=body.enabled,
                allow_interest_export=body.allow_interest_export,
                forget_on_revoke=body.forget_on_revoke,
                idempotency_key=body.idempotency_key,
            )
            return {
                "grant": asdict(grant),
                "forget_receipt": asdict(receipt) if receipt is not None else None,
            }
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.put("/consent/app")
    def put_app_consent(
        body: AppConsentIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest", "community", "messenger"), _ALL_WRITE_CAPS)
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        if principal.app_id != "quest" and body.app_id != principal.app_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "app_scope_mismatch", "message": "App session can only manage its own app consent"},
            )
        try:
            grant = bridge.set_app_consent(
                principal,
                body.app_id,
                read_enabled=body.read_enabled,
                write_enabled=body.write_enabled,
                allow_interest_export_to_community=body.allow_interest_export_to_community,
                allow_cross_source_recall=body.allow_cross_source_recall,
            )
            return {"grant": asdict(grant)}
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.put("/consent/conversation")
    def put_conversation_consent(
        body: ConversationConsentIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(
                ("messenger", "quest"),
                {
                    "messenger": frozenset({"memory:write:chat"}),
                    "quest": frozenset({"memory:write:owner"}),
                },
            )
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        if body.ai_mode == "off" and body.forget_on_withdraw and principal.app_id is not None:
            needed = next(iter(_ALL_FORGET_CAPS[principal.app_id]))
            _check_required_capability(principal, needed)
        try:
            grant, receipt = bridge.set_conversation_consent(
                principal,
                body.conversation_id,
                ai_mode=body.ai_mode,
                allow_interest_export=body.allow_interest_export,
                forget_on_withdraw=body.forget_on_withdraw,
                idempotency_key=body.idempotency_key,
            )
            return {
                "grant": asdict(grant),
                "forget_receipt": asdict(receipt) if receipt is not None else None,
            }
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    # ------------------------------------------------------- Writes & Signals
    @router.post("/writes")
    def post_write(
        body: WriteRecordIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest", "community", "messenger"), _ALL_WRITE_CAPS)
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        _reject_caller_spoof_fields(
            owner=body.owner,
            owner_id=body.owner_id,
            user_id=body.user_id,
            provenance=body.provenance,
            age_band=body.age_band,
        )
        expected_scope: MemoryScope = "chat_scoped" if body.source_kind == "messenger" else "owner_private"
        if body.scope is not None:
            if body.scope not in MEMORY_SCOPES:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "invalid_scope", "message": f"Invalid scope: {body.scope!r}"},
                )
            if body.scope == "cross_app_interest" or body.scope != expected_scope:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "scope_spoof_rejected", "message": "Caller cannot override memory scope"},
                )
        group_snap: GroupConsentSnapshot | None = None
        if body.group_consent is not None:
            group_snap = GroupConsentSnapshot(
                conversation_id=body.group_consent.conversation_id,
                caller_is_member=body.group_consent.caller_is_member,
                all_active_members_ai_enabled=body.group_consent.all_active_members_ai_enabled,
                cited_authors_save_enabled=body.group_consent.cited_authors_save_enabled,
                membership_revision=body.group_consent.membership_revision,
            )
        record = MemoryRecordInput(
            record_id=body.record_id,
            source_kind=body.source_kind,
            source_id=body.source_id,
            host_app=body.host_app,
            author_id=body.author_id if body.author_id is not None else principal.user_id,
            text=body.text,
            valid_time=body.valid_time,
            scope=expected_scope,
            text_orig=body.text_orig,
            subject_path=body.subject_path,
            explicit_user_confirm=body.explicit_user_confirm,
            allow_sensitive_confirmed=body.allow_sensitive_confirmed,
            demo_data=body.demo_data,
        )
        try:
            receipt = bridge.write_consented(
                principal,
                record,
                group_consent=group_snap,
                expected_consent_generation=body.expected_consent_generation,
            )
            return asdict(receipt)
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.post("/signals")
    def post_signal(
        body: SignalIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest", "community", "messenger"), _ALL_WRITE_CAPS)
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        _reject_caller_spoof_fields(
            owner=body.owner,
            owner_id=body.owner_id,
            user_id=body.user_id,
            age_band=body.age_band,
        )
        try:
            return bridge.record_behavioral_signal(
                principal,
                source_kind=body.source_kind,
                source_id=body.source_id,
                topic_slug=body.topic_slug,
                option_key=body.option_key,
                at=body.at,
                weight=body.weight,
            )
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.post("/facts/{fact_id}/resolve")
    def post_resolve_fact(
        fact_id: str,
        body: ResolveFactIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest", "community", "messenger"), _ALL_WRITE_CAPS)
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        assert principal.app_id is not None
        if body.host_app is not None and body.host_app != principal.app_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "app_scope_mismatch", "message": "host_app must match verified app session"},
            )
        try:
            return bridge.resolve_fact(
                principal,
                fact_id,
                action=body.action,
                host_app=principal.app_id,
                new_text=body.new_text,
                valid_from=body.valid_from,
            )
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    # ------------------------------------------------------------ Quest reads
    @router.post("/quest/context")
    def post_quest_context(
        body: Optional[QuestContextIn] = Body(default=None),
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest",), {"quest": frozenset({"memory:read:owner"})})
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        payload = body or QuestContextIn()
        try:
            return bridge.read_quest_context(principal, payload.query, max_tokens=payload.max_tokens)
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.get("/quest/timeline")
    def get_quest_timeline(
        limit: int = Query(default=100, ge=1, le=500),
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest",), {"quest": frozenset({"memory:read:owner"})})
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        try:
            views = bridge.read_quest_timeline(principal, limit=limit)
            return {"items": [asdict(v) for v in views]}
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.get("/quest/hypotheses")
    def get_quest_hypotheses(
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest",), {"quest": frozenset({"memory:read:owner"})})
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        try:
            views = bridge.read_quest_hypotheses(principal)
            return {"hypotheses": [asdict(v) for v in views]}
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.get("/why/{fact_id}")
    def get_why_fact(
        fact_id: str,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest",), {"quest": frozenset({"memory:read:owner"})})
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        try:
            return bridge.read_why_fact(principal, fact_id, host_app="quest")
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    # -------------------------------------------------------- Community reads
    @router.get("/community/interests")
    def get_community_interests(
        limit: int = Query(default=20, ge=1, le=100),
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("community",), {"community": frozenset({"memory:read:interests"})})
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        try:
            features = bridge.read_community_interest_features(principal, limit=limit)
            return {"features": [asdict(f) for f in features]}
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.get("/community/activity")
    def get_community_activity(
        limit: int = Query(default=50, ge=1, le=200),
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("community",), {"community": frozenset()})
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        try:
            activities = bridge.read_community_own_activity(principal, limit=limit)
            return {"activities": activities}
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    # -------------------------------------------------------- Messenger reads
    @router.post("/messenger/conversations/{conversation_id}/context")
    def post_messenger_context(
        conversation_id: str,
        body: MessengerContextIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("messenger",), {"messenger": frozenset({"memory:read:chat"})})
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        snap = GroupConsentSnapshot(
            conversation_id=body.group_consent.conversation_id,
            caller_is_member=body.group_consent.caller_is_member,
            all_active_members_ai_enabled=body.group_consent.all_active_members_ai_enabled,
            cited_authors_save_enabled=body.group_consent.cited_authors_save_enabled,
            membership_revision=body.group_consent.membership_revision,
        )
        try:
            views = bridge.read_messenger_chat_scope(
                principal,
                conversation_id,
                group_consent=snap,
                query=body.query,
                limit=body.limit,
            )
            return {"facts": [asdict(v) for v in views]}
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.post("/messenger/conversations/{conversation_id}/recall")
    def post_messenger_recall(
        conversation_id: str,
        body: Optional[MessengerRecallIn] = Body(default=None),
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("messenger",), {"messenger": frozenset({"memory:read:chat"})})
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        payload = body or MessengerRecallIn()
        try:
            views = bridge.read_messenger_owner_recall(
                principal,
                conversation_id,
                query=payload.query,
                limit=payload.limit,
            )
            return {"facts": [asdict(v) for v in views]}
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    # --------------------------------------------------------- Forget & Audit
    @router.post("/forget/records")
    def post_forget_records(
        body: ForgetRecordsIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest", "community", "messenger"), _ALL_FORGET_CAPS)
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        assert principal.app_id is not None
        if body.host_app is not None and body.host_app != principal.app_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "app_scope_mismatch", "message": "host_app must match verified app session"},
            )
        try:
            receipt = bridge.forget_records(
                principal,
                body.record_ids,
                host_app=principal.app_id,
                idempotency_key=body.idempotency_key,
            )
            return asdict(receipt)
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.post("/forget/conversation")
    def post_forget_conversation(
        body: ForgetConversationIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(
                ("messenger", "quest"),
                {
                    "messenger": frozenset({"memory:forget:chat"}),
                    "quest": frozenset({"memory:forget:owner"}),
                },
            )
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        try:
            receipt = bridge.forget_conversation(
                principal,
                body.conversation_id,
                idempotency_key=body.idempotency_key,
            )
            return asdict(receipt)
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.post("/forget/source")
    def post_forget_source(
        body: ForgetSourceIn,
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest", "community", "messenger"), _ALL_FORGET_CAPS)
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        assert principal.app_id is not None
        if body.host_app is not None and body.host_app != principal.app_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "app_scope_mismatch", "message": "host_app must match verified app session"},
            )
        if principal.app_id == "community" and body.source_kind != "community":
            raise HTTPException(
                status_code=403,
                detail={"code": "app_scope_mismatch", "message": "community cannot forget non-community sources"},
            )
        if principal.app_id == "messenger" and body.source_kind != "messenger":
            raise HTTPException(
                status_code=403,
                detail={"code": "app_scope_mismatch", "message": "messenger cannot forget non-messenger sources"},
            )
        try:
            receipt = bridge.forget_source(
                principal,
                body.source_kind,
                host_app=principal.app_id,
                idempotency_key=body.idempotency_key,
            )
            return asdict(receipt)
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    @router.get("/audit")
    def get_audit(
        limit: int = Query(default=100, ge=1, le=500),
        principal: VerifiedPrincipal = Depends(
            _require_bridge_principal(("quest", "community", "messenger"), _ALL_READ_CAPS)
        ),
        bridge: MemoryBridge = Depends(bridge_dep),
    ) -> dict[str, Any]:
        try:
            return {"events": bridge.list_audit_events(principal, limit=limit)}
        except MemoryBridgeError as exc:
            raise _http_from_bridge_error(exc) from exc

    return router
