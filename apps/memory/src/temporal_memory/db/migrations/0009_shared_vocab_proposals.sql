-- E13b (D21): privacy-safe anonymised query signals + shared vocabulary proposals.
-- vocab_query_signals stores ONLY a keyed HMAC-SHA256 hash of the owner id (never a
-- plain hash, never raw owner ids; key = TM_SIGNAL_HMAC_KEY env / server secret) plus
-- folded terms; raw PII sentences are never written (screened pre-write by
-- privacy/sensitive.py). Only user-typed queries are logged — automatic /context calls
-- are never written (record_query_signal enforces source="user_typed"). Account
-- deletion purges an owner's signals via purge_owner_query_signals (no FK: the key is
-- one-way). shared_vocab_proposals stages human-approved shared vocab; it never
-- auto-edits vocab/tree.json.

CREATE TABLE IF NOT EXISTS vocab_query_signals (
    id BIGSERIAL PRIMARY KEY,
    owner_hash TEXT NOT NULL,
    term_folded TEXT NOT NULL,
    query_folded TEXT NOT NULL DEFAULT '',
    embedding public.vector(1024),
    embedding_model TEXT,
    hit_count INTEGER NOT NULL DEFAULT 1,
    resolved_branch TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_hash, term_folded, query_folded)
);

CREATE INDEX IF NOT EXISTS idx_vocab_query_signals_term
    ON vocab_query_signals(term_folded);
CREATE INDEX IF NOT EXISTS idx_vocab_query_signals_branch
    ON vocab_query_signals(resolved_branch);
-- Purge-by-owner (account deletion) and per-owner aggregate lookups.
CREATE INDEX IF NOT EXISTS idx_vocab_query_signals_owner
    ON vocab_query_signals(owner_hash);

CREATE TABLE IF NOT EXISTS shared_vocab_proposals (
    id BIGSERIAL PRIMARY KEY,
    canonical_term TEXT NOT NULL,
    aliases_en_ar TEXT[] NOT NULL DEFAULT '{}',
    parent_path TEXT NOT NULL,
    rationale TEXT NOT NULL DEFAULT '',
    distinct_owners INTEGER NOT NULL DEFAULT 0,
    cluster_metadata JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    decided_at TIMESTAMPTZ,
    decided_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One live (pending/approved) proposal per canonical term + branch; a rejected
-- proposal may be superseded by a fresh pending one.
CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_vocab_proposals_live_unique
    ON shared_vocab_proposals(canonical_term, parent_path)
    WHERE status <> 'rejected';

CREATE INDEX IF NOT EXISTS idx_shared_vocab_proposals_status
    ON shared_vocab_proposals(status);
