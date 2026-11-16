"""Two small model calls on labels only: label -> group, then group -> life theme (with definitions).

One call that does both made the 9B model dump almost everything under a single theme; splitting the
job and defining each theme fixes that. A failed call or a skipped label falls back honestly to
('Other', label) - nothing is invented.
"""
from __future__ import annotations

from . import llm
from .sensitive import filter_statement

THEMES = ["Career", "Learning", "Projects", "People & family", "Events", "Home & money", "Travel", "Everyday life", "Other"]

THEME_DEFS = """Career: jobs, work schedule, employers, colleagues, job search
Learning: study, courses, skills being learned, school or university
Projects: things being built or made (apps, videos, creative or technical projects)
People & family: relatives, friends, calls, family chat, social plans
Events: holidays, occasions, appointments, celebrations
Home & money: housing, bills, banking, shopping, purchases, cars, home repairs
Travel: trips, flights, destinations
Everyday life: routines, weather, food, errands, small talk
Other: only if nothing above fits"""

GROUP_SYSTEM = """You group short chat-topic labels. For every label give a group: a 1-3 word parent label ("Job search", "Car", "Family chat").
Reuse the same group name for related labels so each group holds several labels. Do not add or change labels. JSON only."""
GROUP_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["items"], "properties": {"items": {
    "type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["label", "group"],
                               "properties": {"label": {"type": "string"}, "group": {"type": "string"}}}}}}

THEME_SYSTEM = f"""You file topic groups into life themes. Themes:
{THEME_DEFS}
Pick the single best theme for every group, using the definitions. Spread across themes where they fit; do not default to one. JSON only."""
THEME_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["items"], "properties": {"items": {
    "type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["group", "theme"],
                               "properties": {"group": {"type": "string"}, "theme": {"type": "string", "enum": THEMES}}}}}}


def _batches(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def assign(labels: list[str], batch: int = 40) -> dict[str, tuple[str, str]]:
    """label -> (theme, group)."""
    group_of: dict[str, str] = {}
    for chunk in _batches(labels, batch):
        try:
            res = llm.chat_json(GROUP_SYSTEM, "Labels:\n" + "\n".join(f"- {x}" for x in chunk), GROUP_SCHEMA,
                                name="topic_groups", max_tokens=2500)
        except llm.LabLLMError:
            continue
        for item in res.get("items", []):
            label, group = (item.get("label") or "").strip().lower(), (item.get("group") or "").strip()
            if label in chunk and group and not filter_statement(group):
                group_of[label] = group
    groups = sorted(set(group_of.values()))
    theme_of: dict[str, str] = {}
    for chunk in _batches(groups, batch):
        try:
            res = llm.chat_json(THEME_SYSTEM, "Groups:\n" + "\n".join(f"- {g}" for g in chunk), THEME_SCHEMA,
                                name="group_themes", max_tokens=2500)
        except llm.LabLLMError:
            continue
        for item in res.get("items", []):
            if item.get("group") in chunk:
                theme_of[item["group"]] = item.get("theme", "Other")
    return {x: (theme_of.get(group_of[x], "Other"), group_of[x]) if x in group_of else ("Other", x) for x in labels}
