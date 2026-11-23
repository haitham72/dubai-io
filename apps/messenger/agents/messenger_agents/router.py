"""A traceable plan of the complete utterance, using the SAME boundaries as streaming ticks.

Segmentation lives in text.split_clauses. Keeping one parser prevents a final-only router from silently
merging or reordering commands that already ran during speech. Rule scores below describe the plan;
the engine's configured decider and policy still decide what may execute.
"""
from __future__ import annotations

from .contacts import Contact
from .deciders import Decision, RuleDecider
from .text import split_clauses


async def route_utterance(text: str, contacts: list[Contact]) -> dict:
    rules = RuleDecider()
    clauses = []
    for segment in split_clauses(text):
        decision = await rules.decide(segment, text, contacts)
        action, p, margin = Decision.top(decision.action)
        clauses.append({"text": segment, "command": action, "p": round(p, 4), "margin": round(margin, 4)})
    return {"raw": text, "source": "rules", "clauses": clauses}


def plan_texts(plan: dict) -> list[str]:
    return [clause["text"] for clause in plan["clauses"]]
