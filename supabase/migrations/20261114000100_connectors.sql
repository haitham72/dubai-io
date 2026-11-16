-- Universal connector storage. Source-specific fields stay in metadata JSONB.
-- Browser roles have no access. Owner checks remain in FastAPI.
SET search_path TO dubaiio, extensions, public;

CREATE TABLE IF NOT EXISTS connector_credentials (
    owner TEXT NOT NULL,
    connector_id TEXT NOT NULL,
    ciphertext BYTEA NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (owner, connector_id)
);

CREATE TABLE IF NOT EXISTS connector_connections (
    owner TEXT NOT NULL,
    connector_id TEXT NOT NULL,
    status TEXT NOT NULL,
    health TEXT NOT NULL,
    account_label TEXT,
    cursor JSONB,
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
);

CREATE UNIQUE INDEX IF NOT EXISTS connector_connections_hook ON connector_connections(hook_id);

CREATE TABLE IF NOT EXISTS connector_records (
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
    metadata JSONB,
    UNIQUE (owner, dedupe_key)
);

CREATE INDEX IF NOT EXISTS connector_records_owner ON connector_records(owner, connector_id, ingested_at);

CREATE TABLE IF NOT EXISTS connector_sync_log (
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
);

CREATE INDEX IF NOT EXISTS connector_sync_owner ON connector_sync_log(owner, connector_id, started_at);

CREATE TABLE IF NOT EXISTS connector_outbound_grants (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    connector_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload JSONB NOT NULL,
    shares JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    decided_at TEXT
);

CREATE INDEX IF NOT EXISTS connector_grants_owner ON connector_outbound_grants(owner, status);

ALTER TABLE connector_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_sync_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_outbound_grants ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON connector_credentials, connector_connections, connector_records, connector_sync_log, connector_outbound_grants
    FROM PUBLIC, anon, authenticated, service_role;
