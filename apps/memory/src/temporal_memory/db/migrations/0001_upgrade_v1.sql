ALTER TABLE entities
    ADD COLUMN IF NOT EXISTS provenance TEXT NOT NULL DEFAULT 'inferred',
    ADD COLUMN IF NOT EXISTS user_confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS closeness_suggested TEXT,
    ADD COLUMN IF NOT EXISTS closeness_suggested_evidence JSONB,
    ADD COLUMN IF NOT EXISTS tier_confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS salience_updated_at TIMESTAMPTZ;

ALTER TABLE subjects
    ADD COLUMN IF NOT EXISTS provenance TEXT NOT NULL DEFAULT 'inferred',
    ADD COLUMN IF NOT EXISTS user_confirmed_at TIMESTAMPTZ;

ALTER TABLE owners
    ADD COLUMN IF NOT EXISTS privacy_revision BIGINT NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS link_evidence (
    owner TEXT NOT NULL,
    link_id TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    PRIMARY KEY (owner, link_id, fact_id),
    FOREIGN KEY (owner, link_id) REFERENCES links(owner, id) ON DELETE CASCADE,
    FOREIGN KEY (owner, fact_id) REFERENCES facts(owner, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_link_evidence_owner_fact ON link_evidence(owner, fact_id);

CREATE TABLE IF NOT EXISTS forget_requests (
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL,
    request JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_forget_rules_owner_kind_value
    ON forget_rules(owner, kind, value);
