"""Memory rows - thin entry points over the generic engine (engine.py) and the per-source skills (skills/).

`process` runs a source through the skill its connector id maps to (whatsapp/telegram/messenger/... -> chat,
gmail/imap/outlook/email -> email). The chat helpers below are re-exported for callers and tests that
predate the skills split.
"""
from __future__ import annotations

from . import circle as circle_mod
from . import engine, llm
from .skills import Context, format_row, skill_for
from .skills import chat as _chat
from .skills.chat import ROW_MAX, avg_time, row_hash, segment  # noqa: F401  (re-exports)
from .store import Lab

PACK_ROWS = _chat.CHAT.pack_items


def pack(rows: list[list], budget: int) -> list[list[list]]:
    """Pack chat rows (lists of messages) into calls: by token budget and by row count."""
    return engine.pack(rows, budget, lambda r: sum(llm.est_tokens(_chat.line(m)) + 1 for m in r) + 6, PACK_ROWS)


def process(lab: Lab, chat: str, me: str, cir: circle_mod.Circle, *, sample: int = 0, connector_id: str = "whatsapp") -> dict:
    return engine.process(lab, connector_id, chat, Context(owner=me, circle=cir, source=chat), sample=sample)


def render(lab: Lab, followups_by_row: dict[str, list[str]], limit: int | None = None) -> str:
    """rows.md: one line per row, in the format of its own skill."""
    lines = ["# Memory rows", "",
             "chat:  `time_date: topics | names | user | memory | multimodal | topic:salience/recurring | emotions, sentiment`",
             "email: `date time | [category] subject | topics | names | user | memory | entities | action | attachments | emotions, sentiment`",
             "Sentiment and emotions come from the two local classifiers (sentiment: cardiffnlp xlm-roberta; emotion: "
             "multilingual go_emotions >= 0.45) and are `_` when they could not run. salience = the extraction model's estimate; "
             "recurring = computed from all rows (`_` until the follow-up step runs). Everything is `inferred`, evidence = the "
             "row's own messages. `followup:` lines are open questions, not facts.", ""]
    for r in lab.rows()[:limit]:
        fu = followups_by_row.get(r["id"], [])
        lines.append(f"[{r['kind']}] " + format_row(r) + (" | followup: " + " ; ".join(fu) if fu else ""))
        lines.append("")
    return "\n".join(lines)
