"""Standalone Community API for :8060. Run: uvicorn app.community.server:app --port 8060"""
import importlib

from fastapi import FastAPI

from ..actions import router as session_router
from .routes import router

app = FastAPI(title="Dubai-io Community API", version="0.1.0")
app.include_router(session_router)
app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True, "service": "community"}


@app.get("/api/health")
def api_health():
    return {"ok": True, "service": "community"}


@app.get("/api/community/health")
def community_health():
    return {"ok": True, "service": "community"}


for _name in ("media", "moderation", "agents"):
    try:
        _mod = importlib.import_module(f".{_name}", __package__)
        _router = getattr(_mod, "router", None)
        if _router is not None:
            app.include_router(_router)
    except ImportError:
        pass
