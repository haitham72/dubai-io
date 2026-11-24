"""Portable DDL schema initializer for cs_* memory_bridge tables."""
from __future__ import annotations

import threading
from typing import Any

_SCHEMA_LOCK = threading.RLock()

_DDL_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS cs_consent_grants (
        owner_id TEXT NOT NULL,
        scope_kind TEXT NOT NULL,
        scope_id TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 0,
        read_enabled INTEGER NOT NULL DEFAULT 0,
        write_enabled INTEGER NOT NULL DEFAULT 0,
        ai_mode TEXT NOT NULL DEFAULT 'off',
        allow_interest_export INTEGER NOT NULL DEFAULT 0,
        allow_cross_source_recall INTEGER NOT NULL DEFAULT 0,
        generation INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL,
        updated_by TEXT NOT NULL,
        PRIMARY KEY (owner_id, scope_kind, scope_id)
    )
    """.strip(),
    """
    CREATE TABLE IF NOT EXISTS cs_memory_record_refs (
        owner_id TEXT NOT NULL,
        record_id TEXT NOT NULL,
        source_kind TEXT NOT NULL,
        source_id TEXT NOT NULL,
        host_app TEXT NOT NULL,
        author_is_owner INTEGER NOT NULL,
        consent_generation INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        erased_at TEXT,
        PRIMARY KEY (owner_id, record_id)
    )
    """.strip(),
    """
    CREATE TABLE IF NOT EXISTS cs_two_visit_signals (
        id TEXT PRIMARY KEY,
        owner_id TEXT NOT NULL,
        source_kind TEXT NOT NULL,
        source_id TEXT NOT NULL,
        topic_slug TEXT NOT NULL,
        option_key TEXT NOT NULL,
        visit_at TEXT NOT NULL,
        weight REAL NOT NULL,
        promoted_fact_id TEXT,
        erased_at TEXT
    )
    """.strip(),
    """
    CREATE TABLE IF NOT EXISTS cs_interest_projection_cache (
        owner_id TEXT PRIMARY KEY,
        consent_generation_sig TEXT NOT NULL,
        facts_version INTEGER NOT NULL,
        features_json JSON NOT NULL,
        computed_at TEXT NOT NULL
    )
    """.strip(),
    """
    CREATE TABLE IF NOT EXISTS cs_memory_audit (
        id TEXT PRIMARY KEY,
        owner_id TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        host_app TEXT NOT NULL,
        action TEXT NOT NULL,
        scope_kind TEXT,
        scope_id TEXT,
        target_ids_json JSON NOT NULL,
        consent_generation INTEGER NOT NULL,
        outcome TEXT NOT NULL,
        reason_code TEXT,
        receipt_json JSON NOT NULL,
        idempotency_key TEXT UNIQUE,
        created_at TEXT NOT NULL
    )
    """.strip(),
    "CREATE INDEX IF NOT EXISTS cs_memory_audit_owner_at ON cs_memory_audit(owner_id, created_at)",
)


def ensure_memory_bridge_schema(db: Any, *, lock: threading.RLock | None = None) -> None:
    """Create cs_* memory bridge tables and indexes idempotently using portable SQL."""
    guard = lock if lock is not None else _SCHEMA_LOCK
    with guard:
        for stmt in _DDL_STATEMENTS:
            db.execute(stmt)
        db.commit()
