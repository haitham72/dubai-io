"""WhatsApp chat export parser (WP-D). Ported from the Dubai-io repo — read-only source:

    g:\\Haitham\\VsCode\\contest\\apps\\api\\app\\lab\\parse.py

Formats: iOS `[dd/mm/yyyy, hh:mm:ss] Name: text`, Android `dd/mm/yyyy, hh:mm - Name: text`,
copy-paste `[hh:mm AM, m/d/yyyy] Name: text`. Multi-line messages, system lines, media
placeholders, U+200E/U+200F/U+202F/narrow spaces, and Arabic/Arabizi text are handled.
Timestamps are kept as local ISO strings (no timezone is invented).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re

from temporal_memory.models import Record

MARKS = dict.fromkeys(map(ord, "\u200e\u200f\u202a\u202b\u202c\ufeff"), None)
# Newer iOS exports put U+202F (narrow no-break space) before AM/PM; treat all odd spaces as a plain space.
MARKS.update(dict.fromkeys(map(ord, "\u202f\xa0\u2009"), " "))

# (name, regex, groups order). Each regex captures date/time parts and sender/text.
IOS = re.compile(
    r"^\[(\d{1,2})/(\d{1,2})/(\d{2,4}),? (\d{1,2}):(\d{2})(?::(\d{2}))?(?: ?([AaPp][Mm]))?\] ([^:]+?): ?(.*)$"
)
IOS_SYS = re.compile(
    r"^\[(\d{1,2})/(\d{1,2})/(\d{2,4}),? (\d{1,2}):(\d{2})(?::(\d{2}))?(?: ?([AaPp][Mm]))?\] (.*)$"
)
ANDROID = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{2,4}),? (\d{1,2}):(\d{2})(?::(\d{2}))?(?: ?([AaPp][Mm]))? - ([^:]+?): ?(.*)$"
)
ANDROID_SYS = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{2,4}),? (\d{1,2}):(\d{2})(?::(\d{2}))?(?: ?([AaPp][Mm]))? - (.*)$"
)
PASTE = re.compile(
    r"^\[(\d{1,2}):(\d{2})(?::(\d{2}))? ?([AaPp][Mm]), (\d{1,2})/(\d{1,2})/(\d{2,4})\] ([^:]+?): ?(.*)$"
)

# iOS prints some system notices with the chat name as the "sender".
SYSTEM_TEXT = re.compile(
    r"^(Messages and calls are end-to-end encrypted|.* created (this )?group|You were added|Your security code with .* changed)",
    re.I,
)

MEDIA = re.compile(
    r"^(<media omitted>|<attached: .*>|\S* ?(image|video|audio|sticker|gif|document|voice call|video call) omitted"
    r"|(video|voice) call,? .*|missed (video|voice) call.*|(this message was deleted|you deleted this message))$",
    re.I,
)


@dataclass
class Message:
    idx: int
    ts: str  # local ISO, second precision
    sender: str
    text: str
    kind: str = "message"  # message | media
    meta: dict = field(default_factory=dict)  # source-specific (email: subject, thread, from_addr, attachments...)


@dataclass
class Parsed:
    chat: str
    messages: list[Message]
    system_lines: int
    unparsed_lines: int
    date_order: str  # dmy | mdy

    def stats(self) -> dict:
        real = [m for m in self.messages if m.kind == "message"]
        stamps = [m.ts for m in self.messages]
        return {
            "chat": self.chat,
            "messages": len(self.messages),
            "text_messages": len(real),
            "media": len(self.messages) - len(real),
            "senders": sorted({m.sender for m in self.messages}),
            "first": min(stamps) if stamps else None,
            "last": max(stamps) if stamps else None,
            "system_lines": self.system_lines,
            "unparsed_lines": self.unparsed_lines,
            "date_order": self.date_order,
        }


def _clean(line: str) -> str:
    return line.translate(MARKS).rstrip("\r\n")


def _match(line: str):
    """Return (kind, groups, has_sender) for the first matching header pattern, else None."""
    for name, rx in (("paste", PASTE), ("ios", IOS), ("android", ANDROID)):
        m = rx.match(line)
        if m:
            return name, m.groups(), True
    for name, rx in (("ios", IOS_SYS), ("android", ANDROID_SYS)):
        m = rx.match(line)
        if m:
            return name, m.groups(), False
    return None


def _detect_order(headers: list[tuple[str, tuple]]) -> str:
    """dd/mm unless the data proves m/d (a second field above 12 and no first field above 12)."""
    first_big = second_big = False
    for name, g in headers:
        a, b = (int(g[4]), int(g[5])) if name == "paste" else (int(g[0]), int(g[1]))
        first_big |= a > 12
        second_big |= b > 12
    if second_big and not first_big:
        return "mdy"
    if first_big:
        return "dmy"
    return "mdy" if headers and headers[0][0] == "paste" else "dmy"


def _to_iso(name: str, g: tuple, order: str) -> str:
    if name == "paste":
        hh, mm, ss, ap, d1, d2, yy = g[0], g[1], g[2], g[3], g[4], g[5], g[6]
    else:
        d1, d2, yy, hh, mm, ss, ap = g[0], g[1], g[2], g[3], g[4], g[5], g[6]
    day, month = (int(d2), int(d1)) if order == "mdy" else (int(d1), int(d2))
    year = int(yy) + (2000 if int(yy) < 100 else 0)
    hour = int(hh)
    if ap:
        hour = hour % 12 + (12 if ap.lower() == "pm" else 0)
    return datetime(year, month, day, hour, int(mm), int(ss or 0)).isoformat(timespec="seconds")


def parse_chat(content: str, chat: str) -> Parsed:
    """Parse raw WhatsApp export text into structured messages."""
    lines = [_clean(x) for x in content.splitlines()]
    raw: list[tuple[str, tuple, bool, list[str]]] = []
    unparsed = 0
    for line in lines:
        hit = _match(line)
        if hit:
            name, groups, has_sender = hit
            raw.append((name, groups, has_sender, []))
        elif raw:
            raw[-1][3].append(line)  # continuation of a multi-line message
        elif line.strip():
            unparsed += 1
    order = _detect_order([(n, g) for n, g, _, _ in raw])
    messages: list[Message] = []
    system = 0
    for name, g, has_sender, extra in raw:
        if not has_sender:
            system += 1
            continue
        body_first = g[-1]
        sender = g[-2].strip()
        body = "\n".join([body_first, *extra]).strip()
        if SYSTEM_TEXT.match(body):
            system += 1
            continue
        try:
            ts = _to_iso(name, g, order)
        except ValueError:
            unparsed += 1
            continue
        kind = "media" if MEDIA.match(body.strip()) else "message"
        messages.append(Message(idx=len(messages), ts=ts, sender=sender, text=body, kind=kind))
    return Parsed(chat=chat, messages=messages, system_lines=system, unparsed_lines=unparsed, date_order=order)


def parse_whatsapp_file(path: str | Path, owner: str, *, source_name: str | None = None) -> list[Record]:
    """Parse a WhatsApp export file into Record instances with deterministic `wa-<slug>-<idx:04d>` IDs."""
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8-sig")
    if source_name:
        chat_label = source_name[9:] if source_name.startswith("whatsapp:") else source_name
        source = source_name if source_name.startswith("whatsapp:") else f"whatsapp:{chat_label}"
    else:
        chat_label = file_path.stem
        source = f"whatsapp:{chat_label}"
    slug = re.sub(r"[^a-z0-9]+", "-", chat_label.lower()).strip("-") or "chat"
    parsed = parse_chat(content, chat_label)
    return [
        Record(
            id=f"wa-{slug}-{msg.idx:04d}",
            owner=owner,
            source=source,
            at=msg.ts,
            author=msg.sender,
            text=msg.text,
            generation=0,
        )
        for msg in parsed.messages
    ]
