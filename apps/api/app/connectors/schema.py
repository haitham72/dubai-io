"""Runtime tables for SQLite tests and for Postgres when migrations are not applied yet.

The versioned Supabase migration is supabase/migrations/20261114000100_connectors.sql.
New connectors do not add columns. Source-specific fields stay in metadata JSON.
"""
from __future__ import annotations

DDL = [
    """CREATE TABLE IF NOT EXISTS connector_credentials (
        owner TEXT NOT NULL,
        connector_id TEXT NOT NULL,
        ciphertext BLOB NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (owner, connector_id)
    )""",
    """CREATE TABLE IF NOT EXISTS connector_connections (
        owner TEXT NOT NULL,
        connector_id TEXT NOT NULL,
        status TEXT NOT NULL,
        health TEXT NOT NULL,
        account_label TEXT,
        cursor JSON,
        hook_id TEXT,
        secret_hash TEXT,
        last_sync_at TEXT,
        last_error TEXT,
        next_retry_at TEXT,
        attempt INTEGER NOT NULL DEFAULT 0,
        notice TEXT,
        connected_at TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (owner, connector_id)
    )""",
    """CREATE TABLE IF NOT EXISTS connector_records (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        connector_id TEXT NOT NULL,
        source_id TEXT NOT NULL,
        source_timestamp TEXT NOT NULL,
        ingested_at TEXT NOT NULL,
        dedupe_key TEXT NOT NULL,
        kind TEXT NOT NULL,
        title TEXT NOT NULL,
        text TEXT NOT NULL,
        provenance TEXT NOT NULL,
        as_of TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        metadata JSON,
        UNIQUE (owner, dedupe_key)
    )""",
    """CREATE TABLE IF NOT EXISTS connector_sync_log (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        connector_id TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        attempt INTEGER NOT NULL,
        imported INTEGER NOT NULL DEFAULT 0,
        duplicate INTEGER NOT NULL DEFAULT 0,
        error TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS connector_outbound_grants (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        connector_id TEXT NOT NULL,
        action TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        payload JSON NOT NULL,
        shares JSON NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        decided_at TEXT
    )""",
]

INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS connector_connections_hook ON connector_connections(hook_id)",
    "CREATE INDEX IF NOT EXISTS connector_records_owner ON connector_records(owner, connector_id, ingested_at)",
    "CREATE INDEX IF NOT EXISTS connector_sync_owner ON connector_sync_log(owner, connector_id, started_at)",
    "CREATE INDEX IF NOT EXISTS connector_grants_owner ON connector_outbound_grants(owner, status)",
]


def ensure_connector_schema(db) -> None:
    for stmt in DDL:
        db.execute(stmt)
    for stmt in INDEXES:
        db.execute(stmt)
    db.commit()
