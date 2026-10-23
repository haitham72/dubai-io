"""ML HTTP surface: hybrid comment search and backend status."""
import re

from fastapi import APIRouter, HTTPException, Query, Request

from .communities import scope, setup

router = APIRouter(tags=["ml"])


@router.get("/api/community/search")
def community_search(request: Request, q: str = Query(default=""), limit: int = Query(default=10, ge=1, le=50)):
    from . import ml_rag, ml_tasks
    if not q.strip():
        raise HTTPException(400, "Query text is required")
    store, owner = scope(request)
    with store.lock:
        setup(store)
        ml_tasks.setup(store)
        return ml_rag.search(store, owner, q.strip(), limit)


@router.get("/api/ml/status")
def ml_status():
    from . import ml_models
    from .config import settings
    broker = re.sub(r"://[^@]+@", "://***@", settings.rabbitmq_url)
    probe = ml_models.probe()
    return {"eager": settings.ml_eager, "broker": broker, "models": {
        "sentiment": settings.sentiment_model, "embeddings": settings.embedding_model,
        "deps_installed": probe["deps_installed"], "backend_loaded": probe["backend_loaded"]}}
