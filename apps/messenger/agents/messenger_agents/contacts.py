"""Recipient guard: a person or group is accepted only on an exact name match. Anything close asks one short question.

The speech-to-text model takes no vocabulary hint, so "Sarah" can arrive for "Sara". The guard never guesses between
near-namesakes; with `strict_namesakes` even a correct first name asks when a near-namesake exists in the contact list.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

from .text import norm, send_parts

STOP = {"me", "my", "the", "a", "an", "him", "her", "them", "it", "everyone", "i", "you", "that", "this", "know", "say",
        "saying", "message", "text", "mail", "chat", "chats", "messages", "email", "everybody", "all", "us",
        "i'm", "i'll", "i've", "i'd", "im", "ill", "ive", "please", "thanks", "okay", "ok", "yes", "no", "hey", "hi"}


@dataclass(frozen=True)
class Contact:
    id: str
    name: str

    @property
    def keys(self) -> list[str]:
        full = norm(self.name)
        first = full.split()[0]
        return [full] if first == full else [full, first]


def _skeleton(w: str) -> str:
    """Consonant skeleton (Amr ≈ Omar, Mazin ≈ Mazen): drop vowels, h, y, w and doubled letters."""
    s = re.sub(r"[aeiouyhw]", "", w.lower())
    return re.sub(r"(.)\1+", r"\1", s)


def similar(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    if a == b:
        return False
    return SequenceMatcher(None, a, b).ratio() >= 0.75 or (len(a) > 2 and _skeleton(a) == _skeleton(b) and _skeleton(a) != "")


@dataclass
class Match:
    status: Literal["exact", "ask"]
    contact: Contact | None = None
    question: str = ""
    candidates: tuple[Contact, ...] = ()
    phrase: str = ""  # the words that named the contact (used to cut them out of the message text)


def mentions(text: str, contacts: list[Contact]) -> list[tuple[int, Contact, str]]:
    """Exact mentions as (word position, contact, phrase). A full name wins over the same first name."""
    ws = norm(text).split()
    found: list[tuple[int, Contact, str]] = []
    taken: set[int] = set()
    for c in sorted(contacts, key=lambda c: -len(c.keys[0].split())):
        for key in c.keys:
            kw = key.split()
            for i in range(len(ws) - len(kw) + 1):
                if ws[i:i + len(kw)] == kw and not taken.intersection(range(i, i + len(kw))):
                    found.append((i, c, " ".join(text.split()[i:i + len(kw)]) if len(text.split()) == len(ws) else key))
                    taken.update(range(i, i + len(kw)))
    return sorted(found, key=lambda x: x[0])


def name_candidates(text: str) -> list[str]:
    """Words that look like a person's name in a command: capitalised, or right after to/with/tell/text/message/ask."""
    raw = re.findall(r"[A-Za-z'’]+", text)
    out: list[str] = []
    for i, w in enumerate(raw):
        prev = raw[i - 1].lower() if i else ""
        if w.lower() in STOP or len(w) < 3:
            continue
        if (w[0].isupper() and i > 0) or prev in ("to", "with", "tell", "text", "message", "ask", "let", "call", "whatsapp"):
            out.append(w)
    return out


def resolve(text: str, contacts: list[Contact], model_pick: str | None = None, model_p: float = 1.0,
            threshold: float = 0.6, strict_namesakes: bool = True) -> Match:
    parts = send_parts(text, [k for c in contacts for k in c.keys])
    scope = parts.recipient if parts else text
    exact = mentions(scope, contacts)
    if exact:
        # The first mention after the command verb is the recipient ("tell Sara that Omar is here" → Sara).
        pos, contact, phrase = exact[0]
        # "Arif Kahn": the first name matches but the next word is a near-miss of the surname — ask, don't guess.
        rest = norm(contact.name).split()[1:]
        after = norm(parts.body).split()[:1] if parts else norm(text).split()[pos + len(norm(phrase).split()):][:1]
        if rest and after and similar(after[0], rest[0]):
            return Match("ask", question=f"Did you mean {contact.name}?", candidates=(contact,), phrase=phrase)
        if model_pick is not None and model_pick != contact.id and model_p >= threshold:
            return Match("ask", question=f"Send to {contact.name}?", candidates=(contact,), phrase=phrase)
        # Only a spoken multi-word full name ("Sara Ali") is unambiguous when a near-namesake exists: "Omar" alone may
        # be the transcriber's spelling of "Omer".
        said_full = norm(phrase) == norm(contact.name) and len(contact.keys[0].split()) > 1
        namesakes = tuple(c for c in contacts if c.id != contact.id and any(similar(k, contact.keys[-1]) for k in c.keys))
        if strict_namesakes and namesakes and not said_full:
            both = (contact,) + namesakes
            return Match("ask", question=f"{' or '.join(c.name for c in both)}?", candidates=both, phrase=phrase)
        return Match("exact", contact=contact, phrase=phrase)

    names = name_candidates(f"to {scope}" if parts and scope else scope)
    near: list[Contact] = []
    for n in names:
        for c in contacts:
            if c not in near and any(similar(n, k) for k in c.keys):
                near.append(c)
    if near:
        q = f"Did you mean {near[0].name}?" if len(near) == 1 else f"{' or '.join(c.name for c in near[:3])}?"
        return Match("ask", question=q, candidates=tuple(near[:3]), phrase=names[0] if names else "")
    if names:
        return Match("ask", question=f"{names[-1]} isn't in your contacts. Who should get it?", phrase=names[-1])
    return Match("ask", question="Who should I send it to?")
