"""Standalone Community API for :8060. Run: uvicorn app.community.server:app --port 8060"""
import importlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.identity.router import create_identity_router
from app.memory_bridge.router import create_memory_bridge_router
from app.shared_runtime import create_shared_status_router, init_shared_runtime, shared_runtime_enabled
from ..actions import router as session_router
from .routes import router

DEFAULT_WEB_ORIGINS = ("http://localhost:3060", "http://127.0.0.1:3060")


@asynccontextmanager
async def lifespan(target_app: FastAPI):
    # E5: shared identity store + memory bridge (only when DUBAI_SHARED_IDENTITY_DB is set).
    created = init_shared_runtime(target_app)
    try:
        yield
    finally:
        for store in created:
            try:
                store.close()
            except Exception:
                pass


app = FastAPI(title="Dubai-io Community API", version="0.1.0", lifespan=lifespan)
_origins = [o.strip() for o in os.environ.get("COMMUNITY_ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or list(DEFAULT_WEB_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(session_router)
app.include_router(create_identity_router())
app.include_router(router)
app.include_router(create_shared_status_router())
if shared_runtime_enabled():
    app.include_router(create_memory_bridge_router())


@app.get("/health")
def health():
    return {"ok": True, "service": "community"}


@app.get("/api/health")
def api_health():
    return {"ok": True, "service": "community"}


@app.get("/api/community/health")
def community_health():
    return {"ok": True, "service": "community"}


import logging as _logging

_log = _logging.getLogger("app.community.server")
for _name in ("media", "moderation", "agents", "memory_routes", "context_profile"):
    try:
        _mod = importlib.import_module(f".{_name}", __package__)
        _router = getattr(_mod, "router", None)
        if _router is not None:
            app.include_router(_router)
        else:
            _log.error("Community module %r imported but has no router — endpoints missing", _name)
    except ImportError:
        _log.exception("Failed to import Community router module %r — refusing to start silently", _name)
        raise
