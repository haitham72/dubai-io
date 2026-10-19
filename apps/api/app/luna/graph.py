"""Luna: user understanding as a LangGraph graph.

normalize -> understand (LLM, structured output) -> validate (allowlist, clamps,
confidence gate) -> remember (stated facts only)

Memory
- short-term: the conversation's recent messages, kept per thread by the
  LangGraph checkpointer and passed back to the model on the next turn.
- long-term: facts the user explicitly stated ("I'm at Terminal 3", "my hotel
  is in JLT"), stored as user_supplied with a timestamp and shown back as
  "You told me". Inferred hypotheses belong to the profiler (ARCHITECTURE §12),
  not here.
Luna returns understanding only. It never acts, writes HTML or URLs, or sets a
status (CLAUDE.md rules 1 and 7).
"""
import json
from hashlib import sha256
import operator
import re
import time
from typing import Annotated, Optional, TypedDict

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from ..actions import engine as action_engine
from ..config import settings
from ..user_profile import ProfileStore
from .schema import Understanding

INSTRUCTIONS = """You are Luna, the understanding step of Dubai-io, a companion app for people living in or visiting Dubai.
Classify the user's latest message using the conversation so far, and fill the typed slots.

Intents:
- lost_item: they lost or left something (wallet, phone, bag, passport...). Set item and, if they said, where_lost.
- airport_guide: they need help getting through Dubai airport (arrivals, passport control, baggage, terminal). Set terminal if said.
- service_offers: they want a service done for them, comparing providers and prices. service is one of:
  laundry (washing, ironing, dry cleaning), cleaning (home cleaning), ac (air-conditioning repair or service),
  grooming (pet grooming at home), carwash (car wash at home), pharmacy (medicine delivery), maid (hiring a maid or nanny with a visa).
- places_near: they want a place nearby to go to. category is one of:
  pets, food, coffee, barber, home-help, laundry, clothing, fix-it. subcategory if obvious (e.g. Grooming, Vet, 24h, Restaurants).
- order_status: they ask about an order or request they already sent (is it ready, accepted, when). Never state its status yourself; the app reads it from the order record.
- greeting, smalltalk: hello, thanks, chit-chat.
- unclear: you cannot tell. Then ask one short clarifying question in `clarify`.

Rules:
- If the user wants something done at home or wants prices, prefer service_offers; if they want to go somewhere nearby, prefer places_near.
- stated_facts: only durable facts the user explicitly stated about themselves (where they stay, hotel, terminal, taxi plate/roof, a deadline they gave, pet, language). Never record the request or event itself (for example "lost a bag" or "needs laundry") as a fact. Never guess or infer.
- reply: one or two warm, plain sentences in the user's language. Never include prices, phone numbers, URLs, or claim anything was booked, sent, filed, confirmed or found.
- confidence: your honest probability that the intent is right.
"""

ALLOWED_SUBS = {
    "pets": {"Vet", "24h", "Pet shop", "Boarding", "Grooming", "Photo"},
    "food": {"Restaurants", "Delivery"},
    "home-help": {"Maid", "Cleaning", "Visa services"},
    "fix-it": {"AC", "Plumbing", "Electrical"},
}
# An "other" fact that just restates the request or an incident is not a fact about the user.
EVENT = re.compile(r"\b(lost|left|forgot|missing|need|needs|want|wants|looking for|book|order)\b", re.I)
URL = re.compile(r"https?://\S+|www\.\S+", re.I)
DIGITS = re.compile(r"\+?\d[\d\s-]{6,}\d")
CLAIMS = re.compile(r"\b(booked|confirmed|filed|paid|delivered|verified|submitted|sent|found)\b|تم(?:\s+)?(?:الحجز|التأكيد|الإرسال|الدفع|التسليم)|درهم|\b(?:AED|USD|GBP)\b|[$£€]", re.I)


class Turn(TypedDict):
    role: str
    text: str


class LunaState(TypedDict, total=False):
    user_id: str
    text: str
    history: Annotated[list[Turn], operator.add]
    understanding: dict
    remembered: list[dict]
    ms: int
    model: str


# ---------------------------------------------------------------- long-term memory (stated facts)
facts = ProfileStore(lambda: action_engine().store, legacy_json=settings.data_dir / "memory.json")
_client: Optional[OpenAI] = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key, timeout=settings.luna_timeout_s, max_retries=1)
    return _client


# ---------------------------------------------------------------- nodes
def normalize(state: LunaState) -> dict:
    text = " ".join(state["text"].split())[:600]
    return {"text": text}


def understand(state: LunaState) -> dict:
    recent = state.get("history", [])[-12:]
    known = facts.current(state["user_id"])
    context = ""
    if known:
        context = "Facts the user told us earlier (user_supplied): " + "; ".join(f"{f['key']}={f['value']}" for f in known) + "\n\n"
    transcript = "\n".join(f"{t['role']}: {t['text']}" for t in recent)
    prompt = f"{context}Conversation so far:\n{transcript or '(none)'}\n\nLatest user message:\n{state['text']}"
    t0 = time.perf_counter()
    res = client().responses.parse(
        model=settings.luna_model,
        reasoning={"effort": settings.luna_effort},
        instructions=INSTRUCTIONS,
        input=prompt,
        text_format=Understanding,
        max_output_tokens=4000,
    )
    u = res.output_parsed
    if u is None:
        raise RuntimeError("Luna returned no parsed output")
    return {"understanding": u.model_dump(), "ms": int((time.perf_counter() - t0) * 1000), "model": f"{settings.luna_model} ({settings.luna_effort})"}


def validate(state: LunaState) -> dict:
    u = dict(state["understanding"])
    # keep slots only where they belong to the intent
    keep = {"lost_item": {"item", "where_lost"}, "airport_guide": {"terminal"}, "service_offers": {"service"}, "places_near": {"category", "subcategory"}}.get(u["intent"], set())
    for slot in ("item", "where_lost", "service", "category", "subcategory", "terminal"):
        if slot not in keep:
            u[slot] = None
    if u.get("subcategory") and u.get("subcategory") not in ALLOWED_SUBS.get(u.get("category") or "", set()):
        u["subcategory"] = None
    if u["intent"] == "service_offers" and not u.get("service"):
        u["confidence"] = min(u["confidence"], 0.5)
    if u["confidence"] < 0.6 and u["intent"] not in ("greeting", "smalltalk"):
        u["intent"] = "unclear"
        u["clarify"] = u.get("clarify") or "Do you want a place near you, a service done for you, help at the airport, or help with something you lost?"
    # the reply is display text only: strip anything that looks like a link or a phone number
    for field in ("reply", "clarify"):
        text = DIGITS.sub("", URL.sub("", u.get(field) or "")).strip()
        u[field] = "How can I help with your next step?" if CLAIMS.search(text) else text
    return {"understanding": u}


def remember(state: LunaState) -> dict:
    saved = [facts.add(state["user_id"], f["key"], f["value"], state["text"]) for f in state["understanding"].get("stated_facts", [])
             if not (f["key"] == "other" and EVENT.search(f["value"]))]
    return {"remembered": saved, "history": [{"role": "user", "text": state["text"]}, {"role": "luna", "text": state["understanding"].get("reply", "")}]}


def build():
    g = StateGraph(LunaState)
    g.add_node("normalize", normalize)
    g.add_node("understand", understand)
    g.add_node("validate", validate)
    g.add_node("remember", remember)
    g.add_edge(START, "normalize")
    g.add_edge("normalize", "understand")
    g.add_edge("understand", "validate")
    g.add_edge("validate", "remember")
    g.add_edge("remember", END)
    # Conversation state survives restarts (thread-scoped short-term memory; the profile is long-term memory).
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.data_dir / "luna_checkpoints.sqlite3", check_same_thread=False)
    return g.compile(checkpointer=SqliteSaver(conn))


graph = build()


def turn(thread_id: str, user_id: str, text: str) -> dict:
    out = graph.invoke({"user_id": user_id, "text": text}, config={"configurable": {"thread_id": sha256(json.dumps([user_id, thread_id]).encode()).hexdigest()}})
    return {
        **out["understanding"],
        "via": "langgraph",
        "model": out.get("model"),
        "ms": out.get("ms"),
        "remembered": out.get("remembered", []),
        "told": facts.current(user_id),
        "turns": len(out.get("history", [])) // 2,
    }
