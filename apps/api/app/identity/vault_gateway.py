"""Thin authenticated Memory Gateway router (/api/vault/*) deriving owner strictly from session."""
from __future__ import annotations

from typing import Any, Callable, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from ..memory_bridge.client import HttpTemporalMemoryClient
from ..memory_bridge.models import MemoryBridgeError, TemporalMemoryClient
from .deps import get_identity_service, require_app_principal
from .models import VerifiedPrincipal
from .service import IdentityService

_SENSITIVE_CATEGORIES: frozenset[str] = frozenset({
    "health",
    "religion",
    "ethnicity_nationality",
    "gender_sexuality",
    "politics",
    "third_party_private",
    "credential",
    "family_third_party",
})


def _is_sensitive_item(item: dict[str, Any]) -> bool:
    if item.get("quarantined") or item.get("sensitive"):
        return True
    cat = item.get("sensitive_cat")
    if isinstance(cat, str) and cat in _SENSITIVE_CATEGORIES:
        return True
    path = str(item.get("path") or "").split("/")[0].strip().lower()
    return path in _SENSITIVE_CATEGORIES


class TierUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tier: Optional[Literal["T1", "T2", "T3"]] = None


class ForgetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact_id: Optional[str] = Field(default=None, min_length=1, max_length=256)
    record_ids: Optional[list[str]] = Field(default=None, max_length=500)
    # Explicit spoof traps so any caller attempt to specify owner returns 403.
    owner: Optional[str] = None
    owner_id: Optional[str] = None
    user_id: Optional[str] = None


def _default_get_tm_client(request: Request) -> TemporalMemoryClient:
    client = getattr(request.app.state, "temporal_memory_client", None)
    if client is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "temporal_memory_unavailable", "message": "Temporal memory client is not mounted"},
        )
    return client


def _ensure_owner_provisioned(request: Request, client: TemporalMemoryClient, owner: str) -> None:
    token_handler = getattr(request.app.state, "memory_token_handler", None)
    if token_handler is not None and callable(getattr(token_handler, "ensure_bridge_token", None)):
        token_handler.ensure_bridge_token(owner)
    else:
        client.ensure_owner(owner, label=owner, kind="real")


def _http_from_tm_error(exc: MemoryBridgeError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)})


def create_vault_gateway_router(
    *,
    get_tm_client: Optional[Callable[[Request], TemporalMemoryClient]] = None,
    get_identity: Optional[Callable[[Request], IdentityService]] = None,
) -> APIRouter:
    """Create the authenticated /api/vault/* gateway router."""
    tm_dep = get_tm_client or _default_get_tm_client
    read_principal = require_app_principal("quest", frozenset({"memory:read:owner"}))
    write_principal = require_app_principal("quest", frozenset({"memory:write:owner"}))
    forget_principal = require_app_principal("quest", frozenset({"memory:forget:owner"}))
    router = APIRouter(prefix="/api/vault", tags=["vault"])

    if get_identity is not None:
        # Preserve override support when callers mount with custom identity resolver.
        _ = get_identity

    @router.get("/graph")
    def vault_graph(
        request: Request,
        view: Literal["subjects", "people"] = Query(default="subjects"),
        principal: VerifiedPrincipal = Depends(read_principal),
        client: TemporalMemoryClient = Depends(tm_dep),
    ) -> dict[str, Any]:
        owner = principal.user_id
        try:
            _ensure_owner_provisioned(request, client, owner)
            if isinstance(client, HttpTemporalMemoryClient):
                resp = client._request(
                    "GET",
                    f"/v1/owners/{quote(owner, safe='')}/vault/graph",
                    headers=client._owner_headers(owner),
                    params={"view": view},
                )
                assert resp is not None
                return dict(resp.json())

            if view == "subjects":
                subj_data = client.get_vault_subjects(owner)
                themes = [t for t in subj_data.get("themes", []) if not _is_sensitive_item(t)]
                nodes = [
                    {
                        "id": t["id"],
                        "kind": "cluster",
                        "label": t["label"],
                        "group": t.get("path") or t["id"],
                        "fact_count": t.get("fact_count", 0),
                        "provenance": t.get("provenance"),
                    }
                    for t in themes
                ]
                return {
                    "view": "subjects",
                    "demo_data": bool(subj_data.get("demo_data")),
                    "provenance": subj_data.get("provenance", "user_supplied"),
                    "nodes": nodes,
                    "counts": {"hidden_by_group": {}},
                }

            ppl_data = client.get_vault_people(owner)
            nodes: list[dict[str, Any]] = [{"id": owner, "kind": "owner", "label": owner}]
            for group_key in ("people", "places", "orgs", "projects"):
                for ent in ppl_data.get(group_key, []):
                    if _is_sensitive_item(ent) or ent.get("status") == "merged":
                        continue
                    nodes.append({
                        "id": ent["id"],
                        "kind": ent.get("kind", "person"),
                        "label": ent.get("name") or ent.get("label") or ent["id"],
                        "subtitle": ent.get("relation_to_user"),
                        "tier": ent.get("closeness_tier"),
                        "closeness_suggested": ent.get("closeness_suggested"),
                        "provenance": ent.get("provenance"),
                        "place_type": ent.get("place_type"),
                    })
            return {
                "view": "people",
                "demo_data": bool(ppl_data.get("demo_data")),
                "provenance": ppl_data.get("provenance", "user_supplied"),
                "nodes": nodes,
                "counts": {"hidden_by_group": {}},
            }
        except MemoryBridgeError as exc:
            raise _http_from_tm_error(exc) from exc

    @router.get("/subjects")
    def vault_subjects(
        request: Request,
        principal: VerifiedPrincipal = Depends(read_principal),
        client: TemporalMemoryClient = Depends(tm_dep),
    ) -> dict[str, Any]:
        owner = principal.user_id
        try:
            _ensure_owner_provisioned(request, client, owner)
            data = client.get_vault_subjects(owner)
            data["themes"] = [t for t in data.get("themes", []) if not _is_sensitive_item(t)]
            return data
        except MemoryBridgeError as exc:
            raise _http_from_tm_error(exc) from exc

    @router.get("/people")
    def vault_people(
        request: Request,
        principal: VerifiedPrincipal = Depends(read_principal),
        client: TemporalMemoryClient = Depends(tm_dep),
    ) -> dict[str, Any]:
        owner = principal.user_id
        try:
            _ensure_owner_provisioned(request, client, owner)
            data = client.get_vault_people(owner)
            for key in ("people", "places", "orgs", "projects"):
                if key in data and isinstance(data[key], list):
                    data[key] = [
                        e for e in data[key] if not _is_sensitive_item(e) and e.get("status") != "merged"
                    ]
            return data
        except MemoryBridgeError as exc:
            raise _http_from_tm_error(exc) from exc

    @router.get("/timeline")
    def vault_timeline(
        request: Request,
        date_from: Optional[str] = Query(default=None),
        date_to: Optional[str] = Query(default=None),
        limit: int = Query(default=200, ge=1, le=500),
        principal: VerifiedPrincipal = Depends(read_principal),
        client: TemporalMemoryClient = Depends(tm_dep),
    ) -> dict[str, Any]:
        owner = principal.user_id
        try:
            _ensure_owner_provisioned(request, client, owner)
            data = client.get_timeline(owner, date_from=date_from, date_to=date_to, limit=limit)
            data["items"] = [f for f in data.get("items", []) if not _is_sensitive_item(f)]
            return data
        except MemoryBridgeError as exc:
            raise _http_from_tm_error(exc) from exc

    @router.get("/why/{fact_id}")
    def vault_why(
        fact_id: str,
        request: Request,
        principal: VerifiedPrincipal = Depends(read_principal),
        client: TemporalMemoryClient = Depends(tm_dep),
    ) -> dict[str, Any]:
        owner = principal.user_id
        try:
            _ensure_owner_provisioned(request, client, owner)
            data = client.get_why_fact(owner, fact_id)
            if isinstance(data.get("evidence"), list):
                data["evidence"] = [e for e in data["evidence"] if not _is_sensitive_item(e)]
            return data
        except MemoryBridgeError as exc:
            raise _http_from_tm_error(exc) from exc

    @router.post("/people/{entity_id}/tier")
    def vault_person_tier(
        entity_id: str,
        body: TierUpdateIn,
        request: Request,
        principal: VerifiedPrincipal = Depends(write_principal),
        client: TemporalMemoryClient = Depends(tm_dep),
    ) -> dict[str, Any]:
        owner = principal.user_id
        try:
            _ensure_owner_provisioned(request, client, owner)
            if isinstance(client, HttpTemporalMemoryClient):
                resp = client._request(
                    "POST",
                    f"/v1/owners/{quote(owner, safe='')}/vault/people/{quote(entity_id, safe='')}/tier",
                    headers=client._owner_headers(owner),
                    json_body={"tier": body.tier},
                )
                assert resp is not None
                return dict(resp.json())

            entities = getattr(client, "entities", {}).get(owner, [])
            target = next(
                (e for e in entities if e.get("id") == entity_id and e.get("status") != "merged"),
                None,
            )
            if target is None:
                raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Person entity not found"})
            if target.get("kind") != "person":
                raise HTTPException(
                    status_code=422,
                    detail={"code": "invalid_entity_kind", "message": "closeness_tier applies only to person entities"},
                )
            target["closeness_tier"] = body.tier
            if body.tier is not None:
                target["provenance"] = "user_supplied"
            return {"ok": True, "entity_id": entity_id, "tier": body.tier}
        except MemoryBridgeError as exc:
            raise _http_from_tm_error(exc) from exc

    @router.post("/forget")
    def vault_forget(
        body: ForgetIn,
        request: Request,
        principal: VerifiedPrincipal = Depends(forget_principal),
        client: TemporalMemoryClient = Depends(tm_dep),
    ) -> dict[str, Any]:
        if body.owner is not None or body.owner_id is not None or body.user_id is not None:
            raise HTTPException(
                status_code=403,
                detail={"code": "owner_spoof_rejected", "message": "Caller cannot supply owner or user_id"},
            )
        owner = principal.user_id
        try:
            _ensure_owner_provisioned(request, client, owner)
            if body.fact_id:
                return client.forget_fact(owner, body.fact_id)
            if body.record_ids:
                return client.forget_source(owner, body.record_ids)
            raise HTTPException(
                status_code=422,
                detail={"code": "missing_target", "message": "Provide fact_id or record_ids"},
            )
        except MemoryBridgeError as exc:
            raise _http_from_tm_error(exc) from exc

    @router.get("/quests")
    def vault_quests(
        request: Request,
        principal: VerifiedPrincipal = Depends(read_principal),
        client: TemporalMemoryClient = Depends(tm_dep),
    ) -> dict[str, Any]:
        owner = principal.user_id
        try:
            _ensure_owner_provisioned(request, client, owner)
            if isinstance(client, HttpTemporalMemoryClient):
                resp = client._request(
                    "GET",
                    f"/v1/owners/{quote(owner, safe='')}/quests",
                    headers=client._owner_headers(owner),
                    allow_404=True,
                )
                if resp is not None:
                    return dict(resp.json())
            return {"owner": owner, "quests": [], "demo_data": False}
        except MemoryBridgeError as exc:
            raise _http_from_tm_error(exc) from exc

    return router
