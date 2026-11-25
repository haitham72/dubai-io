-- E10: Owner-scoped learned vocabulary terms traced to source records.

CREATE TABLE IF NOT EXISTS learned_terms (
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    term_folded TEXT NOT NULL,
    term TEXT NOT NULL,
    parent_path TEXT NOT NULL,
    path TEXT NOT NULL,
    provenance TEXT NOT NULL DEFAULT 'inferred',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner, term_folded),
    UNIQUE (owner, path)
);

CREATE INDEX IF NOT EXISTS idx_learned_terms_owner_parent
    ON learned_terms(owner, parent_path);

CREATE TABLE IF NOT EXISTS learned_term_sources (
    owner TEXT NOT NULL,
    term_folded TEXT NOT NULL,
    record_id TEXT NOT NULL,
    had_fact BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner, term_folded, record_id),
    FOREIGN KEY (owner, term_folded) REFERENCES learned_terms(owner, term_folded) ON DELETE CASCADE,
    FOREIGN KEY (owner, record_id) REFERENCES records(owner, id)
);

CREATE INDEX IF NOT EXISTS idx_learned_term_sources_owner_record
    ON learned_term_sources(owner, record_id);
