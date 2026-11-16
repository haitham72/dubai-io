"""File import for sources that have no authorized personal API.

Amounts copied from the file stay user_supplied. A file cannot declare itself official.
"""
from __future__ import annotations

import csv
import io
import json

from ..base import BaseConnector
from ..types import PermanentFailure, RawItem
from . import register

EXPORT_IDS = (
    "linkedin",
    "instagram",
    "amazon",
    "noon",
    "ebay",
    "purchase_receipts",
    "finance_statements",
    "browser_history",
    "browser_bookmarks",
    "browser_saved_pages",
    "saved_media",
)

KINDS = {
    "linkedin": "export_item",
    "instagram": "export_item",
    "amazon": "receipt",
    "noon": "receipt",
    "ebay": "receipt",
    "purchase_receipts": "receipt",
    "finance_statements": "statement_line",
    "browser_history": "history_visit",
    "browser_bookmarks": "bookmark",
    "browser_saved_pages": "saved_page",
    "saved_media": "saved_media",
}


def parse_import(content: str, *, kind: str) -> list[RawItem]:
    text = (content or "").strip()
    if not text:
        raise PermanentFailure("The file is empty")
    if text[0] in "[{":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PermanentFailure("The JSON file could not be read") from exc
        if isinstance(data, dict):
            data = data.get("items") or data.get("records") or data.get("orders") or data.get("messages")
        if not isinstance(data, list):
            raise PermanentFailure("The JSON file must be a list of records")
        rows = data
    else:
        try:
            rows = list(csv.DictReader(io.StringIO(text)))
        except csv.Error as exc:
            raise PermanentFailure("The CSV file could not be read") from exc
        if not rows:
            raise PermanentFailure("The CSV file has no rows")
    if len(rows) > 500:
        raise PermanentFailure("Import at most 500 rows at a time")
    return [_row(row, index, kind) for index, row in enumerate(rows)]


def _row(row, index: int, kind: str) -> RawItem:
    if not isinstance(row, dict):
        raise PermanentFailure("Each record must be an object")
    source_id = str(row.get("id") or row.get("source_id") or row.get("order_id") or "").strip()
    if not source_id:
        raise PermanentFailure(f"Row {index + 1} needs an id")
    title = str(row.get("title") or row.get("name") or "")
    body = row.get("text") or row.get("body") or row.get("description") or title
    timestamp = row.get("timestamp") if row.get("timestamp") is not None else row.get("date") or row.get("source_timestamp") or ""
    meta: dict = {}
    if row.get("url"):
        meta["url"] = str(row["url"])[:2000]
    amount = row.get("amount")
    if amount not in (None, ""):
        money = {"value": str(amount), "provenance": "user_supplied"}
        if row.get("currency"):
            money["currency"] = str(row["currency"])[:8]
        if timestamp:
            money["as_of"] = str(timestamp)
        meta["amount"] = money
    return RawItem(
        source_id=source_id,
        source_timestamp="" if timestamp is None else str(timestamp),
        title=title,
        text=str(body or ""),
        kind=kind,
        metadata=meta,
    )


class FileImportConnector(BaseConnector):
    transport = "local"

    def parse(self, content: str) -> list[RawItem]:
        return parse_import(content, kind=KINDS[self.spec.id])


@register(*EXPORT_IDS)
def build(spec):
    return FileImportConnector(spec)
