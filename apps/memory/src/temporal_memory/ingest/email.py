"""Email and notes ingest parsers (WP-D). Ported from the Dubai-io repo — read-only source:

    g:\\Haitham\\VsCode\\contest\\apps\\api\\app\\lab\\parse_email.py

Supports `.mbox` files, directories of `.eml` files (or a single `.eml` file),
synthetic gold `gmail.jsonl` lines, and `[nNNN] YYYY-MM-DD | text` / plain dated notes.
"""
from __future__ import annotations

from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
import html
import json
import mailbox
from pathlib import Path
import re
from typing import Any

from temporal_memory.models import Record
from .whatsapp import Message

BULK_SENDER = re.compile(
    r"(no-?reply|do-?not-?reply|newsletter|notifications?|mailer-daemon|updates?@|news@|info@)",
    re.I,
)
QUOTE_HEAD = re.compile(
    r"^(on .{5,120} wrote:|-{2,}\s*(original message|forwarded message)\s*-{2,}|from:\s.+\ssent:\s)",
    re.I,
)
SIGNATURES = ("sent from my iphone", "sent from my ipad", "sent from outlook", "get outlook for")
FOOTERS = re.compile(r"(unsubscribe|view (this email )?in (your )?browser|you are receiving this)", re.I)

_NOTE_TAGGED = re.compile(r"^\[([a-zA-Z0-9_-]+)\]\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+)$")
_NOTE_DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})\s*(?:\||:|-)\s*(.+)$")
_NOTE_HEADER = re.compile(r"^(?:#{1,6}\s*)?(\d{4}-\d{2}-\d{2})\s*$")


def clean_body(text: str) -> str:
    """Strip quoted replies, signatures, and email footers."""
    out = []
    for line in text.replace("\r", "").split("\n"):
        stripped = line.strip()
        low = stripped.lower()
        if QUOTE_HEAD.match(stripped) or low.startswith(SIGNATURES) or line.startswith("-- ") or stripped == "--":
            break  # everything after a quote header or signature is the previous message / boilerplate
        if stripped.startswith(">") or FOOTERS.search(stripped):
            continue
        out.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def _body(msg: EmailMessage) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    text = part.get_content()
    if part.get_content_type() == "text/html":
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
        text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", text)))
    return clean_body(re.sub(r"[ \t]+", " ", text))


def _thread(msg: EmailMessage) -> str:
    refs = (msg.get("References") or "").split()
    return (refs[0] if refs else (msg.get("In-Reply-To") or msg.get("Message-ID") or "")).strip("<> ") or re.sub(
        r"^((re|fwd?):\s*)+", "", (msg.get("Subject") or "").lower()
    ).strip()


def to_record(msg: EmailMessage) -> Message | None:
    """Convert an EmailMessage into a Message with cleaned body and email metadata."""
    try:
        when = parsedate_to_datetime(msg["Date"]).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None
    name, addr = parseaddr(msg.get("From", ""))
    body = _body(msg)
    attachments = [f"{p.get_filename()} ({p.get_content_type()})" for p in msg.iter_attachments() if p.get_filename()]
    precedence = (msg.get("Precedence") or "").lower()
    bulk = bool(msg.get("List-Unsubscribe")) or precedence in {"bulk", "list", "junk"} or bool(BULK_SENDER.search(addr))
    return Message(
        idx=0,
        ts=when.isoformat(timespec="seconds"),
        sender=name or addr,
        text=body or (msg.get("Subject") or ""),
        kind="message",
        meta={
            "subject": (msg.get("Subject") or "").strip(),
            "thread": _thread(msg),
            "from_addr": addr.lower(),
            "to": [a for _, a in getaddresses(msg.get_all("To", []))],
            "attachments": attachments,
            "bulk": bulk,
            "list_unsubscribe": bool(msg.get("List-Unsubscribe")),
            "precedence": precedence,
        },
    )


def parse_mailbox(path: str | Path) -> list[Message]:
    """Parse an .mbox file, an .eml file, or a folder of .eml files into chronological Message records."""
    path = Path(path)
    msgs: list[EmailMessage] = []
    if path.is_dir():
        for f in sorted(path.glob("*.eml")):
            msgs.append(BytesParser(policy=policy.default).parsebytes(f.read_bytes()))
    elif path.suffix.lower() == ".eml":
        msgs.append(BytesParser(policy=policy.default).parsebytes(path.read_bytes()))
    else:
        box = mailbox.mbox(str(path), factory=lambda f: BytesParser(policy=policy.default).parse(f))
        try:
            msgs = list(box)
        finally:
            box.close()
    records = [r for r in (to_record(m) for m in msgs) if r]
    records.sort(key=lambda r: r.ts)
    for i, r in enumerate(records):
        r.idx = i
    return records


def parse_gold_gmail(path: str | Path) -> list[tuple[Message, dict[str, Any]]]:
    """Parse `{id, thread_id, ts, from, subject, body}` JSONL lines, preserving gold IDs."""
    items: list[tuple[Message, dict[str, Any]]] = []
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    for line in lines:
        raw_line = line.strip()
        if not raw_line:
            continue
        row: dict[str, Any] = json.loads(raw_line)
        idx = len(items)
        name, addr = parseaddr(str(row.get("from", "")))
        subject = str(row.get("subject") or "").strip()
        body = clean_body(str(row.get("body") or ""))
        thread_id = str(row.get("thread_id") or "").strip()
        rec_id = str(row.get("id") or f"gm-{idx:04d}")
        ts = str(row.get("ts") or "")
        msg = Message(
            idx=idx,
            ts=ts,
            sender=name or addr,
            text=body or subject,
            kind="message",
            meta={
                "id": rec_id,
                "subject": subject,
                "thread": thread_id,
                "thread_id": thread_id,
                "from": str(row.get("from", "")),
                "from_addr": addr.lower(),
                "bulk": bool(BULK_SENDER.search(addr)),
            },
        )
        items.append((msg, row))
    return items


def parse_notes(path: str | Path) -> list[Message]:
    """Parse `[nNNN] YYYY-MM-DD | text` and plain dated notes files into Message records."""
    messages: list[Message] = []
    current_date: str | None = None
    for raw_line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m_tagged = _NOTE_TAGGED.match(line)
        if m_tagged:
            note_id, date_str, body = m_tagged.groups()
            messages.append(
                Message(
                    idx=len(messages),
                    ts=f"{date_str}T00:00:00",
                    sender="owner",
                    text=body.strip(),
                    kind="message",
                    meta={"id": note_id},
                )
            )
            continue
        m_header = _NOTE_HEADER.match(line)
        if m_header:
            current_date = m_header.group(1)
            continue
        m_dated = _NOTE_DATED.match(line)
        if m_dated:
            date_str, body = m_dated.groups()
            messages.append(
                Message(
                    idx=len(messages),
                    ts=f"{date_str}T00:00:00",
                    sender="owner",
                    text=body.strip(),
                    kind="message",
                    meta={},
                )
            )
            continue
        if current_date is not None:
            cleaned = re.sub(r"^[-*+]\s+", "", line).strip()
            if cleaned:
                messages.append(
                    Message(
                        idx=len(messages),
                        ts=f"{current_date}T00:00:00",
                        sender="owner",
                        text=cleaned,
                        kind="message",
                        meta={},
                    )
                )
    return messages


def _format_email_text(msg: Message) -> str:
    subject = str(msg.meta.get("subject") or "").strip()
    body = (msg.text or "").strip()
    if subject and body and body != subject:
        return f"{subject}\n{body}"
    return body or subject


def email_to_records(
    messages: list[Message],
    owner: str,
    *,
    source: str = "email",
    prefix: str = "em",
    slug: str = "mail",
) -> list[Record]:
    """Convert parsed email Messages into Record instances with deterministic IDs."""
    clean_slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-") or "mail"
    return [
        Record(
            id=str(msg.meta.get("id") or f"{prefix}-{clean_slug}-{msg.idx:04d}"),
            owner=owner,
            source=source,
            at=msg.ts,
            author=msg.sender,
            text=_format_email_text(msg),
            generation=0,
        )
        for msg in messages
    ]


def gmail_to_records(items: list[tuple[Message, dict[str, Any]]], owner: str) -> list[Record]:
    """Convert `parse_gold_gmail` output into Record instances preserving gold IDs."""
    out: list[Record] = []
    for msg, row in items:
        rec_id = str(row.get("id") or msg.meta.get("id") or f"gm-{msg.idx:04d}")
        out.append(
            Record(
                id=rec_id,
                owner=owner,
                source="gmail",
                at=msg.ts,
                author=msg.sender,
                text=_format_email_text(msg),
                generation=0,
            )
        )
    return out


def notes_to_records(messages: list[Message], owner: str, *, slug: str = "notes") -> list[Record]:
    """Convert parsed notes Messages into Record instances."""
    clean_slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-") or "notes"
    return [
        Record(
            id=str(msg.meta.get("id") or f"note-{clean_slug}-{msg.idx:04d}"),
            owner=owner,
            source="notes",
            at=msg.ts,
            author=msg.sender,
            text=msg.text,
            generation=0,
        )
        for msg in messages
    ]
