"""Extraction skills: one per KIND of source. The engine (../engine.py) is generic; a skill owns everything
that depends on what the source looks like.

    chat   whatsapp, telegram, messenger, instagram, imessage, sms, signal   -> rows of 5-10 messages
    email  gmail, imap, outlook, email                                       -> rows per thread

A skill is plain data + functions:
    system(ctx)            the system prompt (function, so it can embed the circle / profile / owner)
    schema                 JSON schema of what the model may write (nothing code can compute)
    units(records, ctx)    how the source is cut into rows
    render(unit, ctx)      the text the model sees for one unit
    to_row(unit, item, ctx)  model item -> row fields; every checkable field is decided by code here
    score_texts(...)       which texts the two local scoring models (sentiment, emotion) read
    extra_followups(...)   questions that need no model (e.g. an image or attachment we cannot see)
    format_row(row)        the human-readable one-line row for that kind
    cost(unit, est)        prompt tokens one unit costs, so units can be packed into a call
Add a source kind = add a file here and call `register`. Nothing else changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class UnknownSource(KeyError):
    pass


@dataclass
class Context:
    owner: str  # the owner's name as it appears in the source
    circle: Any  # app.lab.circle.Circle
    source: str  # chat id / mailbox name
    owner_emails: tuple[str, ...] = ()


@dataclass
class Unit:
    key: str
    records: list  # list[app.lab.parse.Message]
    evidence: list[int]  # message ids a row may cite = its own text records
    t_start: str
    t_end: str
    t_avg: str
    text_hash: str

    @property
    def first_idx(self) -> int:
        return self.records[0].idx

    @property
    def last_idx(self) -> int:
        return self.records[-1].idx


@dataclass(frozen=True)
class Skill:
    name: str
    source_types: tuple[str, ...]
    schema: dict
    system: Callable[[Context], str]
    units: Callable[[list, Context], list[Unit]]
    render: Callable[[Unit, Context], str]
    to_row: Callable[[Unit, dict, Context], dict]
    score_texts: Callable[[Unit, dict, Context], dict[str, list[str]]]
    extra_followups: Callable[[Unit, dict, Context], list[str]]
    format_row: Callable[[dict], str]
    cost: Callable[[Unit, Callable[[str], int]], int]  # prompt tokens a unit costs (for packing)
    pack_tokens: int = 3000
    pack_items: int = 8
    max_output: int = 3500


REGISTRY: dict[str, Skill] = {}


def register(skill: Skill) -> Skill:
    for source_type in skill.source_types:
        REGISTRY[source_type] = skill
    return skill


def skill_for(connector_id: str) -> Skill:
    try:
        return REGISTRY[connector_id.lower()]
    except KeyError:
        raise UnknownSource(
            f"no extraction skill for source '{connector_id}' (known: {', '.join(sorted(REGISTRY))})") from None


def format_row(row: dict) -> str:
    """Render a stored row with the skill of its kind."""
    for skill in REGISTRY.values():
        if skill.name == row.get("kind", "chat"):
            return skill.format_row(row)
    raise UnknownSource(row.get("kind"))


from . import chat, email, ide_session  # noqa: E402,F401  (registers the built-in skills)
