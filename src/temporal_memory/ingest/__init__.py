"""Ingest parsers, deterministic triage, and `tm` CLI (WP-D)."""
from __future__ import annotations

from .email import (
    clean_body,
    email_to_records,
    gmail_to_records,
    notes_to_records,
    parse_gold_gmail,
    parse_mailbox,
    parse_notes,
    to_record,
)
from .triage import (
    ingest_records,
    is_forgotten,
    is_noise_email,
    is_noise_whatsapp,
    owner_has_active_device,
)
from .whatsapp import Message, Parsed, parse_chat, parse_whatsapp_file

__all__ = [
    "Message",
    "Parsed",
    "clean_body",
    "email_to_records",
    "gmail_to_records",
    "ingest_records",
    "is_forgotten",
    "is_noise_email",
    "is_noise_whatsapp",
    "notes_to_records",
    "owner_has_active_device",
    "parse_chat",
    "parse_gold_gmail",
    "parse_mailbox",
    "parse_notes",
    "parse_whatsapp_file",
    "to_record",
]
