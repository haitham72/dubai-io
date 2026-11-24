"""Image-ideas skill."""
from __future__ import annotations

import re

from .base import CHAT_RULE, CONTEXT_MAX, Msg, fence
from .planner import PLACES, STOPWORDS
# ------------------------------------------------------------------ image ideas
IDEAS_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["subject", "ideas"], "properties": {
    "subject": {"type": "string"},
    "ideas": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["title", "prompt"],
              "properties": {"title": {"type": "string", "description": "2-4 words"}, "prompt": {"type": "string"}}}}}}
STYLES = [("Photo", "cinematic travel photograph, golden hour, natural colours"),
          ("Illustration", "flat vector illustration, warm palette, clean shapes"),
          ("Poster", "bold retro travel poster, big title lettering")]


def subject_from(context: list[Msg]) -> str:
    """The thing the chat is about: the most mentioned place or noun phrase in the recent messages (rules)."""
    text = " ".join(m.text for m in context[-CONTEXT_MAX:])
    for place in sorted(PLACES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(place)}\b", text, re.I):
            return PLACES[place]["subject"]
    words = [w for w in re.findall(r"[A-Za-z]{4,}", text) if w.lower() not in STOPWORDS]
    return " ".join(words[-4:]) or "a friendly chat"


async def image_ideas(llm: LLM | None, context: list[Msg], request: str) -> dict:
    explicit = re.sub(r"^(?:create|make|generate|draw)\s+(?:an?\s+)?(?:image|picture|photo|pic)s?\s*(?:about|of|for|showing)?\s*", "", request.strip(), flags=re.I)
    explicit = "" if re.fullmatch(r"(?:this|that|it|the chat)?", explicit, re.I) else explicit
    if llm:
        out = await llm.json(
            f"You turn a chat into three distinct image ideas (different subjects or angles, not just styles). {CHAT_RULE}",
            f"Request: <<{request}>>\n\n{fence(context)}\nReturn exactly 3 ideas with a short title and a vivid prompt.",
            IDEAS_SCHEMA, "image_ideas")
        return {**out, "ideas": out.get("ideas", [])[:3], "mode": "live"}
    subject = explicit or subject_from(context)
    return {"subject": subject, "mode": "rules",
            "ideas": [{"title": t, "prompt": f"{subject}, {style}"} for t, style in STYLES]}
