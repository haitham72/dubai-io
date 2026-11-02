"""HTTP surface for product memory — timeline, search, hypotheses, forget."""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..actions import COOKIE, engine
from .store import MemoryStore

router = APIRouter(prefix="/api/memory", tags=["memory"])


def _mem(request: Request) -> tuple[str, MemoryStore]:
    owner = engine().store.owner(request.cookies.get(COOKIE))
    return owner, MemoryStore(engine().store.db)


@router.get("/timeline")
def timeline(request: Request, limit: int = Query(default=40, ge=1, le=100)):
    owner, mem = _mem(request)
    return {"items": mem.timeline(owner, limit), "provenance_note": "You told me / provider-backed events only"}


@router.get("/search")
def search(request: Request, q: str = Query(default="", max_length=120), k: int = Query(default=10, ge=1, le=30)):
    owner, mem = _mem(request)
    return {"hits": mem.search(owner, q, k)}


@router.get("/hypotheses")
def hypotheses(request: Request):
    owner, mem = _mem(request)
    return {"items": mem.hypotheses(owner)}


class HypothesisIn(BaseModel):
    status: str = Field(pattern="^(confirmed|rejected|hypothesis)$")


@router.put("/hypotheses/{item_id}")
def set_hypothesis(item_id: str, body: HypothesisIn, request: Request):
    owner, mem = _mem(request)
    if not mem.set_hypothesis(owner, item_id, body.status):
        raise HTTPException(404, "Hypothesis not found")
    return {"ok": True, "id": item_id, "status": body.status}


@router.delete("/items/{item_id}")
def forget(item_id: str, request: Request):
    owner, mem = _mem(request)
    mem.forget(owner, item_id)
    return {"ok": True, "forgotten": item_id}


@router.get("/context")
def context(request: Request, q: str = Query(default="", max_length=120)):
    owner, mem = _mem(request)
    return {"pack": mem.context_pack(owner, q), "as_of": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds")}
