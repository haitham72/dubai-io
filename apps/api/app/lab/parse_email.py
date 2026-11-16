"""Email import (stdlib only): an .mbox file or a folder of .eml files -> Message records for the email skill.

Until the Gmail connector is authorised, an mbox / .eml export (Google Takeout, Apple Mail, Thunderbird) is the
manual-export path, like WhatsApp's "Export chat". Per message we keep: subject, thread, from / to,
attachment names (never their content), a bulk flag (newsletters and automatic notices), and a cleaned body -
quoted replies, signatures and footers removed so a long thread does not repeat itself in every row.
"""
from __future__ import annotations

import html
import mailbox
import re
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from pathlib import Path

from .parse import Message

BULK_SENDER = re.compile(r"(no-?reply|do-?not-?reply|newsletter|notifications?|mailer-daemon|updates?@|news@|info@)", re.I)
QUOTE_HEAD = re.compile(r"^(on .{5,120} wrote:|-{2,}\s*(original message|forwarded message)\s*-{2,}|from:\s.+\ssent:\s)", re.I)
SIGNATURES = ("sent from my iphone", "sent from my ipad", "sent from outlook", "get outlook for")
FOOTERS = re.compile(r"(unsubscribe|view (this email )?in (your )?browser|you are receiving this)", re.I)


def clean_body(text: str) -> str:
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
    return (refs[0] if refs else (msg.get("In-Reply-To") or msg.get("Message-ID") or "")).strip("<> ") or \
        re.sub(r"^((re|fwd?):\s*)+", "", (msg.get("Subject") or "").lower()).strip()


def to_record(msg: EmailMessage) -> Message | None:
    try:
        when = parsedate_to_datetime(msg["Date"]).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None
    name, addr = parseaddr(msg.get("From", ""))
    body = _body(msg)
    attachments = [f"{p.get_filename()} ({p.get_content_type()})" for p in msg.iter_attachments() if p.get_filename()]
    bulk = bool(msg.get("List-Unsubscribe")) or (msg.get("Precedence", "").lower() in {"bulk", "list", "junk"}) \
        or bool(BULK_SENDER.search(addr))
    return Message(
        idx=0, ts=when.isoformat(timespec="seconds"), sender=name or addr, text=body or (msg.get("Subject") or ""),
        kind="message",
        meta={"subject": (msg.get("Subject") or "").strip(), "thread": _thread(msg), "from_addr": addr.lower(),
              "to": [a for _, a in getaddresses(msg.get_all("To", []))], "attachments": attachments, "bulk": bulk},
    )


def parse_mailbox(path: str | Path) -> list[Message]:
    path = Path(path)
    msgs: list[EmailMessage] = []
    if path.is_dir():
        for f in sorted(path.glob("*.eml")):
            msgs.append(BytesParser(policy=policy.default).parsebytes(f.read_bytes()))
    else:
        box = mailbox.mbox(str(path), factory=lambda f: BytesParser(policy=policy.default).parse(f))
        msgs = list(box)
    records = [r for r in (to_record(m) for m in msgs) if r]
    records.sort(key=lambda r: r.ts)
    for i, r in enumerate(records):
        r.idx = i
    return records
