"""user_circle + user_profile: what the founder told us, used as context for every extraction call.

`circle.json` lives in the data dir (outside the repo) and is *user_supplied*: relation and nicknames
come from the founder, never from the model (the model once called a mother "partner or close friend").
It also fixes names: a name the model wrote that is one letter away from a known nickname
("مامتب" vs "مامتي") is corrected to the nickname's spelling, and the misspelling is queued as an alias
suggestion (hypothesis -> Confirm / Not true), never silently trusted.

    {"owner": {"name": "Haitham"},
     "profile_summary": "short, editable, cold-start summary of the owner",
     "people": {"<chat id>": {"name": "mamty", "relation": "mother",
                              "nicknames": ["مامتي", "قطتي"], "summary": "..."}}}
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_DIACRITICS = re.compile("[ً-ٰٟـ]")  # harakat, dagger alef, tatweel
_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})
FUZZY = 0.8
MIN_FUZZY_LEN = 4


def fold(text: str) -> str:
    """Spelling-insensitive form for comparing Arabic / Latin names."""
    text = _DIACRITICS.sub("", (text or "").lower()).translate(_LETTERS)
    return re.sub(r"[\W_]+", "", text)


@dataclass
class Circle:
    owner: str = ""
    profile_summary: str = ""
    people: dict[str, dict] = field(default_factory=dict)
    owner_emails: tuple[str, ...] = ()

    def person(self, chat: str) -> dict | None:
        return self.people.get(chat)

    def prompt_block(self, chat: str) -> str:
        p = self.person(chat)
        if not p:
            return "THE OTHER PERSON: unknown (no circle entry; do not guess their relation)."
        nick = ", ".join(p.get("nicknames", [])) or "none"
        return (f"THE OTHER PERSON: {p['name']} - relation to the owner: {p.get('relation', 'unknown')}. "
                f"Nicknames used for them: {nick}. About them: {p.get('summary', '')}")


def load(data_dir: str | Path) -> Circle:
    path = Path(data_dir) / "circle.json"
    if not path.exists():
        return Circle()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Circle(owner=raw.get("owner", {}).get("name", ""), profile_summary=raw.get("profile_summary", ""),
                  people=raw.get("people", {}),
                  owner_emails=tuple(raw.get("owner", {}).get("emails", [])))


def normalize_names(names: list[str], chat: str, circle: Circle) -> tuple[list[str], list[tuple[str, str]], list[str]]:
    """-> (names with circle spelling, [(misspelling, correct spelling)], display names of circle members seen).

    Exact folded matches are corrected silently; fuzzy matches are corrected AND returned as suggestions."""
    person = circle.person(chat)
    known: dict[str, tuple[str, str]] = {}  # folded alias -> (spelling to store, who it is)
    if circle.owner:
        known[fold(circle.owner)] = (circle.owner, circle.owner)
    if person:
        for alias in [person["name"], *person.get("nicknames", [])]:
            known[fold(alias)] = (alias, person["name"])
    out, suggestions, members = [], [], []
    for raw in names:
        raw = raw.strip()
        if not raw:
            continue
        key = fold(raw)
        hit = known.get(key)
        if hit is None and len(key) >= MIN_FUZZY_LEN:
            best, score = None, FUZZY
            for alias_key in known:
                if len(alias_key) < MIN_FUZZY_LEN:
                    continue
                ratio = difflib.SequenceMatcher(None, key, alias_key).ratio()
                if ratio >= score:
                    best, score = alias_key, ratio
            if best:
                hit = known[best]
                suggestions.append((raw, hit[0]))
        if hit:
            out.append(hit[0])
            members.append(hit[1])
        else:
            out.append(raw)
    return list(dict.fromkeys(out)), suggestions, list(dict.fromkeys(members))


def scan_aliases(texts: list[str], chat: str, circle: Circle) -> list[tuple[str, str]]:
    """Deterministic: words in the raw messages that are one slip away from a circle nickname
    (e.g. مامتب for مامتي). Returned as (word as written, nickname spelling) - hypotheses only.
    Independent of the model, which tends to correct such typos silently and leave no trace."""
    person = circle.person(chat)
    if not person:
        return []
    known = {fold(a): a for a in [person["name"], *person.get("nicknames", [])] if len(fold(a)) >= MIN_FUZZY_LEN}
    found: dict[str, str] = {}
    for text in texts:
        for word in re.findall(r"\w+", text):
            key = fold(word)
            if len(key) < MIN_FUZZY_LEN or key in known or word in found:
                continue
            best, score = None, FUZZY
            for alias_key, alias in known.items():
                if abs(len(key) - len(alias_key)) <= 1 and key[:2] == alias_key[:2]:  # a slip, not a different word
                    ratio = difflib.SequenceMatcher(None, key, alias_key).ratio()
                    if ratio >= score:
                        best, score = alias, ratio
            if best:
                found[word] = best
    return list(found.items())
