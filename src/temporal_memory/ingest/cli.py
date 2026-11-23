"""`tm` command-line entrypoint for owner management and source ingestion (WP-D)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from typing import Any
import uuid

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import Database, get_database
from temporal_memory.models import Owner, Record
from .email import (
    email_to_records,
    gmail_to_records,
    notes_to_records,
    parse_gold_gmail,
    parse_mailbox,
    parse_notes,
)
from .triage import ingest_records, is_noise_email, is_noise_whatsapp
from .whatsapp import parse_whatsapp_file


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _resolve_db(db: Database | None, dsn: str | None) -> Database:
    if db is not None:
        return db
    env_dsn = dsn or os.environ.get("TM_DATABASE_URL") or None
    return get_database(env_dsn)


def _cmd_owner_create(args: argparse.Namespace, db: Database) -> dict[str, Any]:
    owner_id = args.id or _slugify(args.label) or f"owner-{uuid.uuid4().hex[:8]}"
    owner = Owner(
        id=owner_id,
        label=args.label,
        kind=args.kind,
        display_name=args.display_name,
        self_aliases=list(args.alias or []),
        timezone=args.timezone,
    )
    created = PostgresGraphStore(db).create_owner(owner)
    return {
        "id": created.id,
        "label": created.label,
        "kind": created.kind,
        "display_name": created.display_name,
        "self_aliases": created.self_aliases,
        "timezone": created.timezone,
    }


def _load_and_triage(kind: str, path: Path, owner: str, source_name: str | None) -> tuple[list[Record], int]:
    if not path.exists():
        raise FileNotFoundError(f"Import path does not exist: {path}")

    if kind == "whatsapp":
        raw_recs = parse_whatsapp_file(path, owner, source_name=source_name)
        kept = [r for r in raw_recs if not is_noise_whatsapp(r)]
        return kept, len(raw_recs) - len(kept)

    if kind in {"mbox", "eml"}:
        msgs = parse_mailbox(path)
        kept_msgs = [m for m in msgs if not is_noise_email(m)]
        return email_to_records(kept_msgs, owner, slug=path.stem), len(msgs) - len(kept_msgs)

    if kind == "gmail":
        items = parse_gold_gmail(path)
        kept_items = [(m, row) for m, row in items if not is_noise_email(m)]
        return gmail_to_records(kept_items, owner), len(items) - len(kept_items)

    if kind == "notes":
        msgs = parse_notes(path)
        return notes_to_records(msgs, owner, slug=path.stem), 0

    raise ValueError(f"Unsupported import kind: {kind}")


def _cmd_import(args: argparse.Namespace, db: Database) -> dict[str, Any]:
    store = PostgresGraphStore(db)
    if store.get_owner(args.owner) is None:
        raise ValueError(f"Owner not found: {args.owner}")

    records, pre_dropped = _load_and_triage(args.kind, Path(args.path), args.owner, args.source_name)
    summary = ingest_records(
        db,
        args.owner,
        records,
        split=not args.no_split,
        apply_triage=False,
    )
    summary["dropped_triage"] = pre_dropped + int(summary.get("dropped_triage", 0))
    summary["kind"] = args.kind
    return summary


def build_parser() -> argparse.ArgumentParser:
    """Build the `tm` CLI argument parser."""
    parser = argparse.ArgumentParser(prog="tm", description="temporal-memory CLI")
    parser.add_argument("--dsn", default=None, help="Postgres DSN (overrides TM_DATABASE_URL)")
    sub = parser.add_subparsers(dest="command", required=True)

    owner_p = sub.add_parser("owner", help="Owner management")
    owner_sub = owner_p.add_subparsers(dest="owner_command", required=True)
    create_p = owner_sub.add_parser("create", help="Create or update an owner")
    create_p.add_argument("--label", required=True, help="Owner label")
    create_p.add_argument("--id", default=None, help="Explicit owner ID")
    create_p.add_argument("--kind", choices=["real", "simulated", "demo"], default="real")
    create_p.add_argument("--display-name", default="", help="Owner display name")
    create_p.add_argument("--alias", action="append", default=[], help="Self alias (repeatable)")
    create_p.add_argument("--timezone", default="Asia/Dubai")

    imp_p = sub.add_parser("import", help="Import records from a source file or directory")
    imp_p.add_argument("kind", choices=["whatsapp", "mbox", "eml", "notes", "gmail"])
    imp_p.add_argument("path", help="External path to chat, mailbox, notes, or gmail.jsonl")
    imp_p.add_argument("--owner", required=True, help="Target owner ID")
    imp_p.add_argument("--source-name", default=None, help="Optional chat/source label for WhatsApp")
    imp_p.add_argument("--no-split", action="store_true", help="Insert records without enqueueing day jobs")
    return parser


def main(argv: list[str] | None = None, *, db: Database | None = None) -> int:
    """CLI entrypoint for `tm` and `python -m temporal_memory.ingest.cli`."""
    parser = build_parser()
    args = parser.parse_args(argv)
    database = _resolve_db(db, args.dsn)
    try:
        if args.command == "owner" and args.owner_command == "create":
            out = _cmd_owner_create(args, database)
        elif args.command == "import":
            out = _cmd_import(args, database)
        else:
            parser.error("Unknown command")
            return 2
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(status=2, message=f"error: {exc}\n")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
