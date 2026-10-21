-- FastAPI owns access checks. These tables must never be exposed through PostgREST.
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE SCHEMA IF NOT EXISTS dubaiio;
REVOKE ALL ON SCHEMA dubaiio FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA dubaiio REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA dubaiio REVOKE ALL ON FUNCTIONS FROM PUBLIC, anon, authenticated, service_role;
SET search_path TO dubaiio, extensions, public;

CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, owner TEXT, data TEXT, provider TEXT);
CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, owner TEXT);
CREATE TABLE IF NOT EXISTS preparations (owner TEXT, key TEXT, payload_hash TEXT, result TEXT, PRIMARY KEY(owner,key));
CREATE TABLE IF NOT EXISTS approvals (action_id TEXT, key TEXT, result TEXT, PRIMARY KEY(action_id,key));
CREATE TABLE IF NOT EXISTS merchant_sessions (token_hash TEXT PRIMARY KEY, provider_id TEXT);
CREATE TABLE IF NOT EXISTS merchant_commands (action_id TEXT, key TEXT, result TEXT, PRIMARY KEY(action_id,key));
CREATE TABLE IF NOT EXISTS consent (owner TEXT PRIMARY KEY, at TEXT);
CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, owner TEXT, dedupe_key TEXT, kind TEXT, text TEXT,
    trigger_source TEXT, available_at TEXT, delivered_at TEXT, UNIQUE(owner,dedupe_key));
CREATE TABLE IF NOT EXISTS episodes (id TEXT PRIMARY KEY, owner TEXT, at TEXT, kind TEXT, text TEXT, ev JSONB,
    dedupe_key TEXT, UNIQUE(owner,dedupe_key));
CREATE TABLE IF NOT EXISTS profile_overrides (owner TEXT, hypothesis TEXT, status TEXT, at TEXT, PRIMARY KEY(owner,hypothesis));
CREATE TABLE IF NOT EXISTS user_profile (owner TEXT PRIMARY KEY, display_name TEXT, home_area TEXT, language TEXT,
    mode TEXT, attributes JSONB NOT NULL DEFAULT '{}', version INTEGER NOT NULL DEFAULT 0, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS profile_facts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, facet TEXT NOT NULL, key TEXT NOT NULL,
    value JSONB NOT NULL, provenance TEXT NOT NULL, status TEXT NOT NULL, confidence REAL, source TEXT, evidence JSONB,
    valid_from TEXT NOT NULL, valid_to TEXT, recorded_at TEXT NOT NULL, superseded_by TEXT, embedding extensions.vector(1536));
CREATE INDEX IF NOT EXISTS profile_facts_current ON profile_facts(owner,key,valid_to);
CREATE INDEX IF NOT EXISTS profile_facts_attributes ON user_profile USING gin(attributes);
CREATE TABLE IF NOT EXISTS oauth_attempts (state_hash TEXT PRIMARY KEY, owner TEXT, expires DOUBLE PRECISION, data BYTEA);
CREATE TABLE IF NOT EXISTS oauth_grants (owner TEXT, provider TEXT, data BYTEA, PRIMARY KEY(owner,provider));

DO $$ DECLARE t RECORD; BEGIN
    FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'dubaiio' LOOP
        EXECUTE format('ALTER TABLE dubaiio.%I ENABLE ROW LEVEL SECURITY',t.tablename);
        EXECUTE format('REVOKE ALL ON TABLE dubaiio.%I FROM PUBLIC, anon, authenticated, service_role',t.tablename);
    END LOOP;
END $$;
