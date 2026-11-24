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


def _state(grant, source_enabled: bool) -> dict:
    return {
        "read_enabled": grant.read_enabled,
        "write_enabled": grant.write_enabled,
        "allow_interest_export": grant.allow_interest_export,
        "default_off": not (grant.read_enabled or grant.write_enabled or grant.allow_interest_export),
        "source_enabled": source_enabled,
        "generation": grant.generation,
        "as_of": grant.updated_at,
        "provenance": "user_supplied",
    }


@router.get("/api/community/memory/consent")
def get_consent(request: Request):
    """Current server-side consent. Nothing is assumed: the UI shows only what this returns."""
    scope(request)
    bridge = bridge_of(request)
    principal = getattr(request.state, "community_principal", None)
    if bridge is None or principal is None:
        raise HTTPException(503, "Memory bridge is not configured")
    if principal.is_minor_protected:
        raise HTTPException(403, detail={"code": "adults_only", "message": "Community is adults only (18+)."})
    app = bridge.get_consent(principal, "app", "community")
    source = bridge.get_consent(principal, "source", "community")
    return _state(app, source.enabled)


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
        # Switching a toggle off must never erase anything: Forget is its own explicit action.
        source = bridge.set_source_consent(
            principal, "community",
            enabled=body.write_enabled or body.read_enabled or body.allow_interest_export,
            allow_interest_export=body.allow_interest_export,
            forget_on_revoke=False,
        )
        app = bridge.set_app_consent(
            principal,
            "community",
            read_enabled=body.read_enabled,
            write_enabled=body.write_enabled,
            allow_interest_export_to_community=body.allow_interest_export,
        )
    except (ConsentDeniedError, MinorProtectionError) as exc:
        raise HTTPException(403, str(exc)) from exc
    return _state(app, source[0].enabled) | {"allow_interest_export": source[0].allow_interest_export}


@router.post("/api/community/memory/forget")
def forget(request: Request):
    store, owner = scope(request)
    del store, owner
    bridge = bridge_of(request)
    principal = getattr(request.state, "community_principal", None)
    if bridge is None or principal is None:
        raise HTTPException(503, "Memory bridge is not configured")
    receipt = bridge.forget_source(principal, "community", host_app="community", idempotency_key=f"forget-community-{principal.user_id}")
    from datetime import datetime, timezone
    return {
        "forgotten": True,
        "records_forgotten": receipt.records_forgotten,
        "facts_erased": receipt.facts_erased,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "provenance": "provider_confirmed",
    }
