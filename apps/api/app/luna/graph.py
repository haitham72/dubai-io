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
import operator
import re
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Annotated, Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from ..config import settings
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
- greeting, smalltalk: hello, thanks, chit-chat.
- unclear: you cannot tell. Then ask one short clarifying question in `clarify`.

Rules:
- If the user wants something done at home or wants prices, prefer service_offers; if they want to go somewhere nearby, prefer places_near.
- stated_facts: only facts the user explicitly stated about themselves in their own words. Never guess or infer.
- reply: one or two warm, plain sentences in the user's language. Never include prices, phone numbers, URLs, or claim anything was booked, sent, filed, confirmed or found.
- confidence: your honest probability that the intent is right.
"""

ALLOWED_SUBS = {
    "pets": {"Vet", "24h", "Pet shop", "Boarding", "Grooming", "Photo"},
    "food": {"Restaurants", "Delivery"},
    "home-help": {"Maid", "Cleaning", "Visa services"},
    "fix-it": {"AC", "Plumbing", "Electrical"},
}
URL = re.compile(r"https?://\S+|www\.\S+", re.I)
DIGITS = re.compile(r"\+?\d[\d\s-]{6,}\d")


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
class FactStore:
    """Tiny JSON store until Postgres arrives with the profiler (step P)."""

    def __init__(self, path):
        self.path = path
        self.lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = json.loads(self.path.read_text("utf-8")) if self.path.exists() else {}

    def add(self, user_id: str, key: str, value: str, source: str) -> dict:
        fact = {"key": key, "value": value, "provenance": "user_supplied", "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": source[:140]}
        with self.lock:
            facts = self.data.setdefault(user_id, [])
            for old in facts:  # a newer statement supersedes the old one; keep history
                if old["key"] == key and old.get("valid_to") is None and old["value"] != value:
                    old["valid_to"] = fact["as_of"]
            if not any(f["key"] == key and f["value"] == value and f.get("valid_to") is None for f in facts):
                facts.append(fact)
            self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), "utf-8")
        return fact

    def current(self, user_id: str) -> list[dict]:
        return [f for f in self.data.get(user_id, []) if f.get("valid_to") is None]

    def forget(self, user_id: str, key: str) -> int:
        with self.lock:
            before = len(self.data.get(user_id, []))
            self.data[user_id] = [f for f in self.data.get(user_id, []) if f["key"] != key]
            self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), "utf-8")
            return before - len(self.data[user_id])


facts = FactStore(settings.data_dir / "memory.json")
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
    u["reply"] = DIGITS.sub("", URL.sub("", u.get("reply") or "")).strip()
    return {"understanding": u}


def remember(state: LunaState) -> dict:
    saved = [facts.add(state["user_id"], f["key"], f["value"], state["text"]) for f in state["understanding"].get("stated_facts", [])]
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
    return g.compile(checkpointer=InMemorySaver())


graph = build()


def turn(thread_id: str, user_id: str, text: str) -> dict:
    out = graph.invoke({"user_id": user_id, "text": text}, config={"configurable": {"thread_id": thread_id}})
    return {
        **out["understanding"],
        "via": "langgraph",
        "model": out.get("model"),
        "ms": out.get("ms"),
        "remembered": out.get("remembered", []),
        "told": facts.current(user_id),
        "turns": len(out.get("history", [])) // 2,
    }
