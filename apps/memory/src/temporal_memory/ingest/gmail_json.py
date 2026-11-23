"""Gmail JSON export importer with deterministic noise triage and thread preservation."""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
import html
import json
from pathlib import Path
import re
from typing import Any

from temporal_memory.ingest.triage import is_noise_email
from temporal_memory.models import Record

_BULK_SENDER = re.compile(
    r"(no-?reply|do-?not-?reply|newsletter|notifications?|mailer-daemon|updates?@|news@|info@)",
    re.I,
)


def _parse_timestamp(date_val: Any, internal_date_val: Any) -> str:
    raw_date = str(date_val or "").strip()
    if raw_date:
        try:
            dt = parsedate_to_datetime(raw_date)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.isoformat(timespec="seconds")
        except (TypeError, ValueError):
            try:
                iso_dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                if iso_dt.tzinfo is not None:
                    iso_dt = iso_dt.astimezone(timezone.utc).replace(tzinfo=None)
                return iso_dt.isoformat(timespec="seconds")
            except ValueError:
                pass

    raw_internal = str(internal_date_val or "").strip()
    if raw_internal:
        try:
            ms = int(raw_internal)
            dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).replace(tzinfo=None)
            return dt.isoformat(timespec="seconds")
        except (TypeError, ValueError, OSError):
            pass

    return ""


def _format_text(subject: str, snippet: str, thread_id: str) -> str:
    header_parts: list[str] = []
    if thread_id:
        header_parts.append(f"[thread:{thread_id}]")
    if subject:
        header_parts.append(subject)
    header = " ".join(header_parts).strip()

    if header and snippet and snippet != subject:
        return f"{header}\n{snippet}"
    return header or snippet


def parse_gmail_json(path: str | Path, owner: str) -> tuple[list[Record], int]:
    """Parse Gmail JSON messages, dropping noise emails and preserving ids and thread_ids."""
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(raw, list):
        raise ValueError("Gmail JSON must be a list of message objects")

    records: list[Record] = []
    dropped = 0

    for idx, row in enumerate(raw):
        if not isinstance(row, dict):
            continue
        raw_from = str(row.get("from") or "").strip()
        name, addr = parseaddr(raw_from)
        subject = str(row.get("subject") or "").strip()
        snippet = html.unescape(str(row.get("snippet") or "")).strip()
        thread_id = str(row.get("thread_id") or "").strip()
        rec_id = str(row.get("id") or f"gm-{idx:04d}").strip()

        triage_payload = {
            "text": snippet,
            "subject": subject,
            "from": raw_from,
            "from_addr": addr.lower(),
            "bulk": bool(row.get("bulk")) or bool(_BULK_SENDER.search(addr)),
            "list_unsubscribe": bool(row.get("list_unsubscribe")),
            "precedence": str(row.get("precedence") or ""),
        }
        if is_noise_email(triage_payload):
            dropped += 1
            continue

        at = _parse_timestamp(row.get("date"), row.get("internal_date"))
        records.append(
            Record(
                id=rec_id,
                owner=owner,
                source="gmail",
                at=at,
                author=name or addr,
                text=_format_text(subject, snippet, thread_id),
                generation=0,
            )
        )

    return records, dropped
