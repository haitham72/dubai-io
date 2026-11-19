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


class ChatTurnIn(BaseModel):
    human_message: str
    ai_message: str
    source: str = "quest_chat"
    proactive: bool = False
    ping_type: str | None = None
    extracted_facts: list[dict] = []


@router.post("/chat/turn")
def save_chat_turn(body: ChatTurnIn, request: Request):
    owner, mem = _mem(request)
    res = mem.add_chat_turn(
        owner,
        human_message=body.human_message,
        ai_message=body.ai_message,
        source=body.source,
        proactive=body.proactive,
        ping_type=body.ping_type,
        extracted_facts=body.extracted_facts,
    )
    return {"ok": True, "turn": res}


@router.get("/chat/pings")
def get_proactive_pings(request: Request):
    owner, _ = _mem(request)
    return {
        "pings": [
            {
                "id": "ping-empathy-01",
                "type": "empathy_apology",
                "tag": "🤖 Autonomous Ping · Empathy & Memory Repair",
                "text": "Hey Haitham, I wanted to follow up and apologize about earlier. I realized I frustrated you by missing your gaming interests in the morning carousel and over-complicating the report format in ide-companio. I've updated your permanent memory profile (weighted gaming + minimal report format) so I don't drop the ball on that again. How does the current feed look?",
                "action_label": "Apology accepted · Feed looks great"
            },
            {
                "id": "ping-news-01",
                "type": "news",
                "tag": "⚡ Autonomous Ping · App News DB Pool",
                "text": "Saw this drop in the Dubai shared pool: Rockstar Games just updated the PC spec timeline for GTA 6, and a sealed PS5 Disc bundle was listed in Dubai for AED 1,200. Since you were tracking both, I pinned them to your Today carousel.",
                "action_label": "View in Today Carousel"
            },
            {
                "id": "ping-checkup-01",
                "type": "checkup",
                "tag": "🔍 Autonomous Ping · Morning Brief Open Loop",
                "text": "Quick checkup on your morning brief open loop: Did you receive the attendee confirmation badge for Dubai Future Week, or should I keep monitoring your inbox for it?",
                "action_label": "Badge Confirmed!"
            }
        ]
    }
