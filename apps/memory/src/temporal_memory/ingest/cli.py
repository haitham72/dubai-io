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
from .desktop import BrowserProfileError, agent_session_records, browser_records, preview as browser_preview
from .dev_sessions import parse_dev_sessions
from .email import (
    email_to_records,
    gmail_to_records,
    notes_to_records,
    parse_gold_gmail,
    parse_mailbox,
    parse_notes,
)
from .ai_exports import chatgpt_records
from .export_cli import export_owner_tree
from .gmail_json import parse_gmail_json
from .takeout import TakeoutError, takeout_records
from .temporal_note import import_temporal_note
from .triage import ingest_records, is_noise_email, is_noise_whatsapp
from .whatsapp import parse_whatsapp_file
from .youtube import parse_youtube_history

_AGENT_TOOLS = ("claude-code", "codex")
_AGENT_DEFAULT_ROOTS = {
    "claude-code": Path.home() / ".claude" / "projects",
    "codex": Path.home() / ".codex" / "sessions",
}


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


def _load_and_triage(
    kind: str,
    path: Path,
    owner: str,
    source_name: str | None,
) -> tuple[list[Record], int, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Import path does not exist: {path}")

    if kind == "whatsapp":
        raw_recs = parse_whatsapp_file(path, owner, source_name=source_name)
        kept = [r for r in raw_recs if not is_noise_whatsapp(r)]
        return kept, len(raw_recs) - len(kept), {}

    if kind in {"mbox", "eml"}:
        msgs = parse_mailbox(path)
        kept_msgs = [m for m in msgs if not is_noise_email(m)]
        return email_to_records(kept_msgs, owner, slug=path.stem), len(msgs) - len(kept_msgs), {}

    if kind == "gmail":
        items = parse_gold_gmail(path)
        kept_items = [(m, row) for m, row in items if not is_noise_email(m)]
        return gmail_to_records(kept_items, owner), len(items) - len(kept_items), {}

    if kind == "gmail-json":
        recs, dropped = parse_gmail_json(path, owner)
        return recs, dropped, {}

    if kind == "notes":
        msgs = parse_notes(path)
        return notes_to_records(msgs, owner, slug=path.stem), 0, {}

    if kind == "youtube":
        recs, held_back = parse_youtube_history(path, owner)
        return recs, 0, {"held_back": held_back, "held_back_count": sum(held_back.values())}

    if kind == "dev-sessions":
        return parse_dev_sessions(path, owner), 0, {}

    raise ValueError(f"Unsupported import kind: {kind}")


def _agent_roots(path: str | None, tool: str | None) -> dict[str, Path] | None:
    """Resolve agent-session roots. None means use library defaults."""
    if path is None and tool is None:
        return None
    if path is None:
        assert tool is not None
        default = _AGENT_DEFAULT_ROOTS.get(tool)
        if default is None:
            raise ValueError(f"Unknown agent tool (no default root): {tool}")
        return {tool: default}
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"Import path does not exist: {root}")
    if tool is None:
        raise ValueError("Specify --tool when providing an agent-sessions ROOT")
    return {tool: root}


def _cmd_import_agent_sessions(args: argparse.Namespace, db: Database) -> dict[str, Any]:
    roots = _agent_roots(args.path, args.tool)
    records = agent_session_records(args.owner, roots=roots, since=args.since)
    summary = ingest_records(
        db,
        args.owner,
        records,
        split=not args.no_split,
        apply_triage=False,
    )
    summary["kind"] = "agent-sessions"
    summary["dropped_triage"] = int(summary.get("dropped_triage", 0))
    return summary


def _cmd_import_browser(args: argparse.Namespace, db: Database) -> dict[str, Any]:
    if not args.path:
        raise ValueError("browser import requires a PROFILE_DIR path")
    profile = Path(args.path)
    if not profile.exists():
        raise FileNotFoundError(f"Browser profile directory does not exist: {profile}")
    if not profile.is_dir():
        raise FileNotFoundError(f"Browser profile path is not a directory: {profile}")

    if args.preview:
        try:
            counts = browser_preview(profile)
        except BrowserProfileError as exc:
            raise ValueError(str(exc)) from exc
        return {
            "kind": "browser",
            "preview": True,
            "imported": 0,
            "deduped": 0,
            "blocked_forgotten": 0,
            "dropped_triage": 0,
            "jobs_enqueued": 0,
            "domain_counts": counts,
        }

    try:
        records = browser_records(args.owner, profile, since=args.since)
    except BrowserProfileError as exc:
        raise ValueError(str(exc)) from exc

    summary = ingest_records(
        db,
        args.owner,
        records,
        split=not args.no_split,
        apply_triage=False,
    )
    summary["kind"] = "browser"
    summary["dropped_triage"] = int(summary.get("dropped_triage", 0))
    return summary


def _cmd_import_takeout(args: argparse.Namespace, db: Database) -> dict[str, Any]:
    if not args.path:
        raise ValueError("takeout import requires a ZIP_OR_DIR path")
    target_path = Path(args.path)
    if not target_path.exists():
        raise FileNotFoundError(f"Import path does not exist: {target_path}")
    try:
        records = takeout_records(args.owner, target_path, since=args.since)
    except TakeoutError as exc:
        raise ValueError(str(exc)) from exc
    summary = ingest_records(
        db,
        args.owner,
        records,
        split=not args.no_split,
        apply_triage=False,
    )
    summary["kind"] = "takeout"
    summary["dropped_triage"] = int(summary.get("dropped_triage", 0))
    return summary


def _cmd_import_chatgpt(args: argparse.Namespace, db: Database) -> dict[str, Any]:
    if not args.path:
        raise ValueError("chatgpt import requires a ZIP_OR_JSON path")
    target_path = Path(args.path)
    if not target_path.exists():
        raise FileNotFoundError(f"Import path does not exist: {target_path}")
    try:
        records = chatgpt_records(args.owner, target_path, since=args.since)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    summary = ingest_records(
        db,
        args.owner,
        records,
        split=not args.no_split,
        apply_triage=False,
    )
    summary["kind"] = "chatgpt"
    summary["dropped_triage"] = int(summary.get("dropped_triage", 0))
    return summary


def _cmd_import(args: argparse.Namespace, db: Database) -> dict[str, Any]:
    store = PostgresGraphStore(db)
    if store.get_owner(args.owner) is None:
        raise ValueError(f"Owner not found: {args.owner}")

    if args.kind == "agent-sessions":
        return _cmd_import_agent_sessions(args, db)

    if args.kind == "browser":
        return _cmd_import_browser(args, db)

    if args.kind == "takeout":
        return _cmd_import_takeout(args, db)

    if args.kind == "chatgpt":
        return _cmd_import_chatgpt(args, db)

    if not args.path:
        raise ValueError(f"Import kind {args.kind!r} requires a path")

    target_path = Path(args.path)
    if not target_path.exists():
        raise FileNotFoundError(f"Import path does not exist: {target_path}")

    if args.kind == "temporal-note":
        summary = import_temporal_note(db, args.owner, target_path, split=not args.no_split)
        summary["kind"] = args.kind
        return summary

    records, pre_dropped, extra = _load_and_triage(args.kind, target_path, args.owner, args.source_name)
    summary = ingest_records(
        db,
        args.owner,
        records,
        split=not args.no_split,
        apply_triage=False,
    )
    summary["dropped_triage"] = pre_dropped + int(summary.get("dropped_triage", 0))
    summary["kind"] = args.kind
    summary.update(extra)
    return summary


def _cmd_export(args: argparse.Namespace, db: Database) -> dict[str, Any]:
    store = PostgresGraphStore(db)
    if store.get_owner(args.owner) is None:
        raise ValueError(f"Owner not found: {args.owner}")
    return export_owner_tree(db, args.owner, args.out)


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
    imp_p.add_argument(
        "kind",
        choices=[
            "whatsapp",
            "mbox",
            "eml",
            "notes",
            "gmail",
            "youtube",
            "gmail-json",
            "dev-sessions",
            "temporal-note",
            "agent-sessions",
            "browser",
            "takeout",
            "chatgpt",
        ],
    )
    imp_p.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Source path; optional for agent-sessions (defaults), required for other kinds",
    )
    imp_p.add_argument("--owner", required=True, help="Target owner ID")
    imp_p.add_argument("--source-name", default=None, help="Optional chat/source label for WhatsApp")
    imp_p.add_argument("--no-split", action="store_true", help="Insert records without enqueueing day jobs")
    imp_p.add_argument(
        "--since",
        default=None,
        help="Inclusive cutoff date/time (YYYY-MM-DD or ISO) for agent-sessions, browser, takeout and chatgpt",
    )
    imp_p.add_argument(
        "--tool",
        choices=list(_AGENT_TOOLS),
        default=None,
        help="Agent-sessions tool filter (claude-code, codex, …)",
    )
    imp_p.add_argument(
        "--preview",
        action="store_true",
        help="Browser only: print domain visit counts and create no records",
    )

    exp_p = sub.add_parser("export", help="Render owner Quest-style Markdown tree to an external folder")
    exp_p.add_argument("--owner", required=True, help="Target owner ID")
    exp_p.add_argument("--out", required=True, help="Output directory outside repository root")
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
        elif args.command == "export":
            out = _cmd_export(args, database)
        else:
            parser.error("Unknown command")
            return 2
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(status=2, message=f"error: {exc}\n")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
