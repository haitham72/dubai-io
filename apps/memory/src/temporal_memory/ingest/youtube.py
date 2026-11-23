"""YouTube watch-history importer producing Rule-9-compliant daily interest summaries."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import unicodedata

from temporal_memory.models import Record
from temporal_memory.privacy.sensitive import categories_hit, pre_write

_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")
_CONTROL_AND_DELIM = re.compile(r"[\r\n\t\x00-\x1f\x7f|=,]+")
_INJECTION_RE = re.compile(
    r"(ignore\s+(?:all\s+)?previous|system\s*:|assistant\s*:|developer\s*:|"
    r"you\s+are\s+now|exfiltrate|reveal\s+all|https?://|```|<\/?untrusted)",
    re.I,
)
_EXTRA_SENSITIVE: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("credential", re.compile(r"\b(passwords|passcodes|credentials|secret\s+keys?)\b", re.I)),
    ("health", re.compile(r"\b(diabet\w*|insulin|hypertension|asthma)\b", re.I)),
)

_TOPIC_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ai/coding",
        re.compile(
            r"\b(?:ai|llm|llms|gpt|claude|coding|code|python|rust|typescript|javascript|"
            r"react|next\.?js|postgres(?:ql)?|sql|docker|kubernetes|git|programming|"
            r"developer|software|api|mcp|agent|agents|machine learning|neural|fastapi)\b",
            re.I,
        ),
    ),
    (
        "design/3d",
        re.compile(
            r"\b(?:blender|3d|figma|ui|ux|design|animation|shader|three\.?js|motion|"
            r"typography|render|rendering|cad|modeling)\b",
            re.I,
        ),
    ),
    (
        "gaming",
        re.compile(
            r"\b(?:game|games|gaming|gameplay|playthrough|steam|xbox|playstation|"
            r"nintendo|esports|fps|rpg|minecraft|elden ring|speedrun)\b",
            re.I,
        ),
    ),
    (
        "tech/hardware",
        re.compile(
            r"\b(?:hardware|gpu|cpu|rtx|nvidia|amd|intel|laptop|macbook|keyboard|"
            r"monitor|ssd|benchmark|iphone|android|gadget|camera|pc build|pc)\b",
            re.I,
        ),
    ),
    (
        "learning",
        re.compile(
            r"\b(?:tutorial|course|lecture|explained|how to|math|physics|history|"
            r"science|documentary|study|lesson|crash course)\b",
            re.I,
        ),
    ),
)


def _classify_topic(title: str, channel: str) -> str:
    combined = f"{title} {channel}"
    for topic, pattern in _TOPIC_RULES:
        if pattern.search(combined):
            return topic
    return "general"


def _sensitive_category(title: str, channel: str) -> str | None:
    """Screen title, channel, and combined text independently so cross-field tokens cannot mask hits."""
    for probe in (title.strip(), channel.strip(), f"{title} {channel}".strip()):
        if not probe:
            continue
        cat = pre_write(probe)
        if cat is not None:
            return cat
        hits = categories_hit(probe)
        if hits:
            return hits[0]
        norm_probe = unicodedata.normalize("NFKC", probe)
        for extra_cat, rx in _EXTRA_SENSITIVE:
            if rx.search(norm_probe):
                return extra_cat
    return None


def _sanitize_channel(channel: str) -> str:
    """Strip control/delimiter chars and drop untrusted prompt-injection strings from channel labels."""
    clean = unicodedata.normalize("NFKC", channel or "").strip()
    if not clean or _INJECTION_RE.search(clean):
        return "unknown"
    clean = _CONTROL_AND_DELIM.sub(" ", clean)
    clean = re.sub(r"\s{2,}", " ", clean).strip()[:80]
    return clean or "unknown"


def _format_counts(counts: Counter[str]) -> str:
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ", ".join(f"{name}={cnt}" for name, cnt in ordered)


def parse_youtube_history(path: str | Path, owner: str) -> tuple[list[Record], dict[str, int]]:
    """Parse YouTube history JSON into at most one aggregated interest Record per day.

    Every item's ``title`` + ``channel`` is checked with both ``pre_write`` and
    ``categories_hit``. Sensitive items are held back and counted in ``held_back``;
    individual video titles, watch URLs, and per-video facts are never emitted.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(raw, list):
        raise ValueError("YouTube history JSON must be a list of watch items")

    held_back: dict[str, int] = {}
    by_day: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        channel = str(item.get("channel") or "").strip()
        watched_at = str(item.get("watched_at") or "").strip()

        cat = _sensitive_category(title, channel)
        if cat is not None:
            held_back[cat] = held_back.get(cat, 0) + 1
            continue

        if not _DATE_PREFIX.match(watched_at):
            continue
        day = watched_at[:10]
        topic = _classify_topic(title, channel)
        by_day[day].append((_sanitize_channel(channel), topic))

    records: list[Record] = []
    for day in sorted(by_day):
        items = by_day[day]
        channel_counts = Counter(ch for ch, _ in items)
        topic_counts = Counter(tp for _, tp in items)
        text = (
            f"YouTube daily interests ({day}): {len(items)} videos watched | "
            f"topics: {_format_counts(topic_counts)} | "
            f"channels: {_format_counts(channel_counts)}"
        )
        records.append(
            Record(
                id=f"yt-day-{day}",
                owner=owner,
                source="youtube:interests",
                at=f"{day}T00:00:00",
                author="owner",
                text=text,
                generation=0,
            )
        )

    return records, held_back
