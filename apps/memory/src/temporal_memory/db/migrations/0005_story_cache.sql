-- U5: Atomic cache for /story keyed by generation, facts_version, privacy_revision, query_hash, and version_key.
CREATE TABLE IF NOT EXISTS story_cache (
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    record_generation INTEGER NOT NULL,
    facts_version INTEGER NOT NULL,
    privacy_revision INTEGER NOT NULL,
    query_hash TEXT NOT NULL,
    version_key TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner, record_generation, facts_version, privacy_revision, query_hash, version_key)
);

CREATE INDEX IF NOT EXISTS idx_story_cache_owner_created
    ON story_cache(owner, created_at DESC);
