"""Owner-scoped temporal memory tables (temporal_note engine shape, product data only)."""
from __future__ import annotations

DDL = [
    """CREATE TABLE IF NOT EXISTS mem_events (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        at TEXT NOT NULL,
        kind TEXT NOT NULL,
        text TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT '',
        provenance TEXT NOT NULL DEFAULT 'user_supplied',
        confidence REAL,
        content_hash TEXT,
        ontology_path TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS mem_entities (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        kind TEXT NOT NULL,
        name TEXT NOT NULL,
        ontology_path TEXT,
        provenance TEXT NOT NULL DEFAULT 'user_supplied'
    )""",
    """CREATE TABLE IF NOT EXISTS mem_entity_aliases (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        alias TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS mem_relationships (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        a TEXT NOT NULL,
        b TEXT NOT NULL,
        kind TEXT NOT NULL,
        valid_from TEXT,
        valid_to TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS mem_event_entities (
        owner TEXT NOT NULL,
        event_id TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        PRIMARY KEY (owner, event_id, entity_id)
    )""",
    """CREATE TABLE IF NOT EXISTS mem_patterns (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        statement TEXT NOT NULL,
        confidence REAL,
        evidence_json JSON,
        status TEXT NOT NULL DEFAULT 'hypothesis',
        valid_from TEXT,
        valid_to TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS mem_advice (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        text TEXT NOT NULL,
        due_at TEXT,
        stale_after TEXT,
        status TEXT NOT NULL DEFAULT 'open'
    )""",
    """CREATE TABLE IF NOT EXISTS mem_ontology_paths (
        path TEXT PRIMARY KEY,
        ui_bot TEXT NOT NULL,
        label TEXT NOT NULL
    )""",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_mem_events_owner_at ON mem_events(owner, at)",
    "CREATE INDEX IF NOT EXISTS idx_mem_entities_owner ON mem_entities(owner, name)",
    "CREATE INDEX IF NOT EXISTS idx_mem_patterns_owner ON mem_patterns(owner, status)",
]


def ensure_memory_schema(db) -> None:
    for stmt in DDL:
        db.execute(stmt)
    for stmt in INDEXES:
        db.execute(stmt)
    # Seed a minimal ontology slice used by demos / profiler (idempotent).
    seeds = [
        ("lifestyle/sports/gym", "lifestyle", "Gym"),
        ("lifestyle/shopping/clothing", "lifestyle", "Clothing"),
        ("career/applications/inbox", "career", "Job applications"),
        ("household/home/area", "household", "Area"),
        ("travel/taxi_recovery", "travel", "Taxi recovery"),
        ("money/insurance/network", "money", "Insurance"),
    ]
    for path, bot, label in seeds:
        db.execute(
            "INSERT OR IGNORE INTO mem_ontology_paths (path, ui_bot, label) VALUES (?,?,?)",
            (path, bot, label),
        )
    db.commit()
