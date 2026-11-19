"""Skill: IDE Sessions & Developer Transcripts (Claude Code, Codex, Antigravity, Git Commits).

Borrows the fast local scanner architecture from ide-companio (Claude Report):
- Reads local session JSONLs and Git commit history.
- Scans and redacts secrets before model extraction.
- Output row: minimal temporal memory summary designed for developer timeline logging.
- Presentation format: extremely minimal for user facing feed / 'developer' filter.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from typing import Any

from ..parse import Message
from . import Context, Skill, Unit, register

CATEGORIES = ["feature", "bugfix", "refactor", "research", "architecture", "test", "docs"]

SYSTEM = """You read a summary of an IDE developer session (prompts, tool calls, or git commit messages) and write ONE temporal memory row.
OWNER: {owner}. {profile}
For each ROW n return:
- project: short name of the repo or workspace (e.g. contest, mirsal-builder, ide-companio).
- topics: 1-4 lowercase labels of 1-3 words (e.g. two-tower, postgres, memory).
- memory: ONE concise, factual narrative sentence: what the owner designed, implemented, tested, or debugged. Keep it extremely minimal, high-signal, and clean. Never retell logs or prompt noise.
- category: one of feature, bugfix, refactor, research, architecture, test, docs.
- sensitive: true if the session exposes secrets, credentials, internal IP, or confidential keys; then leave memory empty.
Return JSON only."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["row", "project", "topics", "memory", "category", "sensitive"],
                "properties": {
                    "row": {"type": "integer"},
                    "project": {"type": "string"},
                    "topics": {"type": "array", "items": {"type": "string"}},
                    "memory": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "sensitive": {"type": "boolean"},
                },
            },
        }
    },
}


def system(ctx: Context) -> str:
    c = ctx.circle
    return SYSTEM.format(owner=getattr(c, "owner", "") or ctx.owner, profile=getattr(c, "profile_summary", "") or "")


def units(records: list[Any], ctx: Context) -> list[Unit]:
    """Group records into single-session units."""
    out = []
    for idx, rec in enumerate(records):
        # Support either Message objects or raw dicts
        text = getattr(rec, "text", "") or str(rec.get("text", "") if isinstance(rec, dict) else "")
        t = getattr(rec, "timestamp", "") or str(rec.get("timestamp", "") if isinstance(rec, dict) else "")
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        
        # Fake a single-record message if raw dict
        msg_obj = rec if hasattr(rec, "idx") else Message(
            idx=idx,
            author=ctx.owner,
            text=text,
            timestamp=t or datetime.utcnow().isoformat(),
            tokens=len(text.split()),
        )
        
        out.append(
            Unit(
                key=f"dev_sess_{idx}",
                records=[msg_obj],
                evidence=[idx],
                t_start=msg_obj.timestamp,
                t_end=msg_obj.timestamp,
                t_avg=msg_obj.timestamp,
                text_hash=text_hash,
            )
        )
    return out


def render(unit: Unit, ctx: Context) -> str:
    rec = unit.records[0]
    return f"[SESSION {unit.key}] {rec.text[:1200]}"


def to_row(unit: Unit, item: dict, ctx: Context) -> dict:
    return {
        "kind": "ide_session",
        "key": unit.key,
        "t_start": unit.t_start,
        "t_end": unit.t_end,
        "t_avg": unit.t_avg,
        "project": item.get("project", "workspace"),
        "topics": item.get("topics", ["dev"]),
        "memory": item.get("memory", "").strip(),
        "category": item.get("category", "feature"),
        "evidence": unit.evidence,
        "sensitive": bool(item.get("sensitive", False)),
    }


def score_texts(unit: Unit, row: dict, ctx: Context) -> dict[str, list[str]]:
    # Developer sessions skip sentiment/emotion scoring
    return {"texts": []}


def extra_followups(unit: Unit, row: dict, ctx: Context) -> list[str]:
    return []


def format_row(row: dict) -> str:
    """Extremely minimal one-line human-readable summary for timeline logging."""
    proj = row.get("project", "dev")
    mem = row.get("memory", "").strip() or "Developer session activity recorded."
    return f"[IDE · {proj}] {mem}"


def cost(unit: Unit, est) -> int:
    rec = unit.records[0]
    return est(rec.text[:1200]) + 150


SKILL = Skill(
    name="ide_session",
    source_types=("ide_session", "claude_code", "codex", "developer_session", "git_commit"),
    schema=SCHEMA,
    system=system,
    units=units,
    render=render,
    to_row=to_row,
    score_texts=score_texts,
    extra_followups=extra_followups,
    format_row=format_row,
    cost=cost,
    pack_tokens=2500,
    pack_items=6,
    max_output=1500,
)

register(SKILL)
