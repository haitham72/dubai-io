"""Messenger HTTP entrypoint. Run: uvicorn app.messenger.server:app --port 8070.

There is no image-generation route.
Stickers are finished pack files or a cut-out of a photo the user already has.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace
import os
from pathlib import Path
import tempfile
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.identity.config import IdentityConfig
from app.identity.jwt import JWTVerifier
from app.identity.router import create_identity_router
from app.identity.service import IdentityService
from app.identity.store import IdentityStore
import app.messenger.capabilities  # noqa: F401  registers workspace.task.create
from app.memory_bridge.router import create_memory_bridge_router
from app.shared_runtime import create_shared_status_router, init_shared_runtime, shared_runtime_enabled
from app.messenger.hub import DEFAULT_DEV_ORIGINS, ChatHub, get_allowed_origins
from app.messenger.routes_chat import router as chat_router
from app.messenger.stickers import PackError, load_manifest, packs_root, resolve_sticker
from app.messenger.store import ChatStore


def _build_identity_config() -> IdentityConfig:
    cfg = IdentityConfig.from_env()
    supa_url = os.getenv("SUPABASE_LOCAL_URL", "").strip().rstrip("/")
    if not cfg.jwt_issuer and supa_url:
        issuer = f"{supa_url}/auth/v1"
        jwks_url = cfg.jwt_jwks_url or f"{issuer}/.well-known/jwks.json"
        hs256_secret = cfg.jwt_hs256_secret or os.getenv("SUPABASE_JWT_SECRET", "")
        audience = os.getenv("IDENTITY_JWT_AUDIENCE", "authenticated").strip() or "authenticated"
        cfg = replace(
            cfg,
            jwt_issuer=issuer,
            jwt_jwks_url=jwks_url,
            jwt_hs256_secret=hs256_secret,
            jwt_audience=audience,
        )
    return cfg


def ensure_runtime_state(target_app: FastAPI) -> list[tuple[str, Any]]:
    """Initialize app.state chat_hub, chat_store, and identity_service only when missing."""
    created: list[tuple[str, Any]] = []

    if getattr(target_app.state, "chat_hub", None) is None:
        target_app.state.chat_hub = ChatHub()

    if getattr(target_app.state, "chat_store", None) is None:
        chat_db = os.getenv("MESSENGER_CHAT_DB", "").strip() or str(
            Path(tempfile.gettempdir()) / "messenger_chat.sqlite3"
        )
        chat_store = ChatStore(chat_db)
        target_app.state.chat_store = chat_store
        created.append(("chat_store", chat_store))

    if getattr(target_app.state, "identity_service", None) is None:
        cfg = _build_identity_config()
        ident_db = os.getenv("MESSENGER_IDENTITY_DB", "").strip() or str(
            Path(tempfile.gettempdir()) / "messenger_identity.sqlite3"
        )
        ident_store = IdentityStore(ident_db)
        verifier = JWTVerifier(
            issuer=cfg.jwt_issuer,
            audience=cfg.jwt_audience,
            hs256_secret=cfg.jwt_hs256_secret,
            jwks_url=cfg.jwt_jwks_url,
            clock_skew_s=cfg.clock_skew_seconds,
            jwks_ttl_s=cfg.jwks_ttl_seconds,
            jwks_refresh_cooldown_s=cfg.jwks_refresh_cooldown_seconds,
        )
        target_app.state.identity_service = IdentityService(ident_store, verifier, config=cfg)
        created.append(("identity_service", ident_store))

    return created


@asynccontextmanager
async def lifespan(target_app: FastAPI):
    shared = init_shared_runtime(target_app)  # E5: shared identity + memory bridge (env-gated)
    created = ensure_runtime_state(target_app) + [("shared_store", st) for st in shared]
    try:
        yield
    finally:
        for attr_name, store in created:
            try:
                store.close()
            except Exception:
                pass
            if attr_name == "chat_store" and getattr(target_app.state, "chat_store", None) is store:
                target_app.state.chat_store = None
            elif attr_name == "identity_service":
                svc = getattr(target_app.state, "identity_service", None)
                if svc is not None and getattr(svc, "store", None) is store:
                    target_app.state.identity_service = None


app = FastAPI(title="Messenger", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins() or list(DEFAULT_DEV_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(create_identity_router())
app.include_router(chat_router)
app.include_router(create_shared_status_router())
if shared_runtime_enabled():
    app.include_router(create_memory_bridge_router())


@app.get("/api/messenger/health")
def health() -> dict:
    return {"ok": True, "app": "messenger"}


@app.get("/api/messenger/packs")
def packs() -> dict:
    root = packs_root()
    manifest = load_manifest(root)
    return {
        "packs": [
            {"id": p["id"], "label": p.get("label"), "provenance": p.get("provenance"), "stickers": [s["id"] for s in p.get("stickers") or []]}
            for p in manifest.get("packs") or []
        ]
    }


@app.post("/api/messenger/packs/{pack_id}/stickers/{sticker_id}")
def send_pack_sticker(pack_id: str, sticker_id: str) -> dict:
    try:
        sent = resolve_sticker(packs_root(), pack_id, sticker_id)
    except PackError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"kind": sent["kind"], "packId": sent["packId"], "stickerId": sent["stickerId"], "label": sent["label"], "provenance": sent["provenance"]}
