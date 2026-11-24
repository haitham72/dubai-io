"""E5: one per-user layer for the three products.

The Community (:8060) and Messenger (:8070) servers share ONLY two things with apps/api (:8000): the identity store (one
verified user_id, app-scoped sessions) and the temporal_note memory through the memory bridge. This module wires both
into an entry server's lifespan when `DUBAI_SHARED_IDENTITY_DB` names the same identity database apps/api uses (a path
or a database URL). Without that variable nothing changes (tests and standalone runs keep their own stores).

Memory goes through `MEMORY_BRIDGE_BACKEND` / `TM_BASE_URL` / `TM_SERVICE_TOKEN`, read server-side only.
"""
from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import APIRouter, FastAPI, Request

from .identity import IdentityConfig, IdentityService, IdentityStore, JWTVerifier
from .identity.google_signin import GoogleSignInService
from .identity.memory_tokens import MemoryTokenService
from .memory_bridge.bridge import MemoryBridge
from .memory_bridge.config import build_temporal_memory_client
from .memory_bridge.fake_client import FakeTemporalMemoryClient
from .memory_bridge.models import MemoryBridgeUnavailable

SHARED_DB_ENV = "DUBAI_SHARED_IDENTITY_DB"


def shared_runtime_enabled() -> bool:
    return bool(os.environ.get(SHARED_DB_ENV, "").strip())


def init_shared_runtime(app: FastAPI) -> list[Any]:
    """Attach identity + memory bridge to `app.state` once. Returns the stores to close on shutdown."""
    created: list[Any] = []
    target = os.environ.get(SHARED_DB_ENV, "").strip()
    if not target or getattr(app.state, "memory_bridge", None) is not None:
        return created

    cfg = IdentityConfig.from_env()
    if cfg.jwt_issuer and (cfg.jwt_hs256_secret or cfg.jwt_jwks_url):
        verifier = JWTVerifier(
            issuer=cfg.jwt_issuer, audience=cfg.jwt_audience, hs256_secret=cfg.jwt_hs256_secret,
            jwks_url=cfg.jwt_jwks_url, clock_skew_s=cfg.clock_skew_seconds,
            jwks_ttl_s=cfg.jwks_ttl_seconds, jwks_refresh_cooldown_s=cfg.jwks_refresh_cooldown_seconds,
        )
    else:  # sessions minted by apps/api need no JWT verification here
        verifier = JWTVerifier(issuer="local-unconfigured", audience=cfg.jwt_audience or "authenticated",
                               hs256_secret=secrets.token_urlsafe(32))

    store = IdentityStore(target)
    created.append(store)
    if getattr(app.state, "identity_service", None) is None:
        app.state.identity_service = IdentityService(store, verifier, config=cfg)
    service = app.state.identity_service

    backend = (os.environ.get("MEMORY_BRIDGE_BACKEND") or "").strip().lower()
    try:
        tm_client = build_temporal_memory_client()
    except MemoryBridgeUnavailable:
        if backend == "http":
            raise  # fail closed: an http backend that cannot be configured must not silently become the fake
        tm_client = FakeTemporalMemoryClient()
    token_svc = MemoryTokenService(service.store, tm_client, token_key=cfg.token_key or None)
    if hasattr(tm_client, "_owner_token_resolver") and getattr(tm_client, "_owner_token_resolver", None) is None:
        tm_client._owner_token_resolver = token_svc.owner_token_resolver

    app.state.identity_store = service.store
    app.state.temporal_memory_client = tm_client
    app.state.memory_token_handler = token_svc
    app.state.google_signin_service = GoogleSignInService(service)
    app.state.memory_bridge = MemoryBridge(service.store.db, tm_client)
    return created


def create_shared_status_router():
    """GET /api/shared/status: which shared layer this entry server runs (kinds only, never a secret)."""

    router = APIRouter()

    @router.get("/api/shared/status")
    def shared_status(request: Request) -> dict[str, Any]:
        client = getattr(request.app.state, "temporal_memory_client", None)
        kind = "none" if client is None else ("http" if client.__class__.__name__.startswith("Http") else "fake")
        return {
            "ok": True,
            "identity_shared": shared_runtime_enabled() and getattr(request.app.state, "identity_service", None) is not None,
            "memory_backend": kind,
            "memory_bridge": getattr(request.app.state, "memory_bridge", None) is not None,
        }

    return router
