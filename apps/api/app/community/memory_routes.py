"""Consent and Forget for Community. Default is off. There is no messenger here."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.memory_bridge.models import ConsentDeniedError, MinorProtectionError

from .memory import bridge_of
from .routes import scope

router = APIRouter(tags=["community-memory"])


class ConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    read_enabled: bool = False
    write_enabled: bool = False
    allow_interest_export: bool = False


@router.post("/api/community/memory/consent")
def set_consent(body: ConsentIn, request: Request):
    store, owner = scope(request)
    del store, owner
    bridge = bridge_of(request)
    principal = getattr(request.state, "community_principal", None)
    if bridge is None or principal is None:
        raise HTTPException(503, "Memory bridge is not configured")
    if principal.is_minor_protected:
        raise HTTPException(403, detail={"code": "adults_only", "message": "Community is adults only (18+)."})
    try:
        source = bridge.set_source_consent(principal, "community", enabled=body.write_enabled or body.read_enabled, allow_interest_export=body.allow_interest_export)
        app = bridge.set_app_consent(
            principal,
            "community",
            read_enabled=body.read_enabled,
            write_enabled=body.write_enabled,
            allow_interest_export_to_community=body.allow_interest_export,
        )
    except (ConsentDeniedError, MinorProtectionError) as exc:
        raise HTTPException(403, str(exc)) from exc
    return {
        "read_enabled": app.read_enabled,
        "write_enabled": app.write_enabled,
        "allow_interest_export": source[0].allow_interest_export,
        "default_off": not (app.read_enabled or app.write_enabled),
    }


@router.post("/api/community/memory/forget")
def forget(request: Request):
    store, owner = scope(request)
    del store, owner
    bridge = bridge_of(request)
    principal = getattr(request.state, "community_principal", None)
    if bridge is None or principal is None:
        raise HTTPException(503, "Memory bridge is not configured")
    receipt = bridge.forget_source(principal, "community", host_app="community", idempotency_key=f"forget-community-{principal.user_id}")
    return {"forgotten": True, "records_forgotten": receipt.records_forgotten, "facts_erased": receipt.facts_erased}
