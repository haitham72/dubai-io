-- temporal-memory Postgres 17 schema (planaudit.md v2.1 §3.2, §6; no mem_ prefix)
-- Unqualified table names allow per-session test isolation via SET search_path.
-- Baseline for fresh installs and pre-migration databases. New DDL belongs in migrations/.

CREATE TABLE IF NOT EXISTS owners (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'real',
    display_name TEXT NOT NULL DEFAULT '',
    self_aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
    timezone TEXT NOT NULL DEFAULT 'Asia/Dubai',
    user_md TEXT NOT NULL DEFAULT '',
    evidence_limits TEXT NOT NULL DEFAULT 'voice notes not read; history before import start not seen',
    alias_version BIGINT NOT NULL DEFAULT 0,
    facts_version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS records (
    id TEXT NOT NULL,
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    at TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    generation INTEGER NOT NULL DEFAULT 0,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    erased_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner, id)
);
CREATE INDEX IF NOT EXISTS idx_records_owner_at ON records(owner, at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_records_owner_hash ON records(owner, content_hash) WHERE erased_at IS NULL;

CREATE TABLE IF NOT EXISTS entities (
    id TEXT NOT NULL,
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'candidate',
    relation_to_user TEXT,
    closeness_tier TEXT,
    merged_into TEXT,
    salience DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    distinct_days INTEGER NOT NULL DEFAULT 1,
    first_seen TEXT,
    last_seen TEXT,
    erased_at TIMESTAMPTZ,
    PRIMARY KEY (owner, id)
);
CREATE INDEX IF NOT EXISTS idx_entities_owner_kind ON entities(owner, kind, status) WHERE erased_at IS NULL;

CREATE TABLE IF NOT EXISTS entity_aliases (
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_folded TEXT NOT NULL,
    lang TEXT,
    source TEXT NOT NULL DEFAULT 'extractor',
    PRIMARY KEY (owner, alias_folded, entity_id),
    FOREIGN KEY (owner, entity_id) REFERENCES entities(owner, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_aliases_owner_folded ON entity_aliases(owner, alias_folded);

CREATE TABLE IF NOT EXISTS subjects (
    id TEXT NOT NULL,
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    parent_id TEXT,
    path TEXT NOT NULL,
    label TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'topic',
    status TEXT NOT NULL DEFAULT 'candidate',
    salience DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    fact_count INTEGER NOT NULL DEFAULT 0,
    distinct_days INTEGER NOT NULL DEFAULT 1,
    sensitive_cat TEXT,
    PRIMARY KEY (owner, id),
    UNIQUE (owner, path)
);
CREATE INDEX IF NOT EXISTS idx_subjects_owner_kind ON subjects(owner, kind, status);

CREATE TABLE IF NOT EXISTS facts (
    id TEXT NOT NULL,
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    text_orig TEXT,
    text_folded TEXT NOT NULL DEFAULT '',
    lang TEXT,
    subject_id TEXT NOT NULL,
    valid_from TEXT NOT NULL DEFAULT '',
    valid_to TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    superseded_by TEXT,
    provenance TEXT NOT NULL DEFAULT 'inferred',
    confidence DOUBLE PRECISION,
    job_id TEXT,
    attempt_id TEXT,
    worker_id TEXT,
    model TEXT,
    prompt_version TEXT,
    content_hash TEXT NOT NULL,
    tsv TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(text_folded, '') || ' ' || coalesce(text, '') || ' ' || coalesce(text_orig, ''))
    ) STORED,
    erased_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner, id)
);
CREATE INDEX IF NOT EXISTS idx_facts_owner_status ON facts(owner, status, valid_from) WHERE erased_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_facts_owner_subj ON facts(owner, subject_id) WHERE erased_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_facts_owner_hash ON facts(owner, content_hash) WHERE erased_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_facts_tsv ON facts USING GIN (tsv);

CREATE TABLE IF NOT EXISTS fact_entities (
    owner TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    role TEXT,
    PRIMARY KEY (owner, fact_id, entity_id),
    FOREIGN KEY (owner, fact_id) REFERENCES facts(owner, id) ON DELETE CASCADE,
    FOREIGN KEY (owner, entity_id) REFERENCES entities(owner, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_fact_entities_owner_ent ON fact_entities(owner, entity_id);

CREATE TABLE IF NOT EXISTS fact_evidence (
    owner TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    record_id TEXT NOT NULL,
    record_generation INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (owner, fact_id, record_id),
    FOREIGN KEY (owner, fact_id) REFERENCES facts(owner, id) ON DELETE CASCADE,
    FOREIGN KEY (owner, record_id) REFERENCES records(owner, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_fact_evidence_owner_rec ON fact_evidence(owner, record_id);

CREATE TABLE IF NOT EXISTS links (
    id TEXT NOT NULL,
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    src TEXT NOT NULL,
    rel TEXT NOT NULL,
    dst TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    evidence_fact_id TEXT,
    erased_at TIMESTAMPTZ,
    PRIMARY KEY (owner, id)
);
CREATE INDEX IF NOT EXISTS idx_links_owner_src_dst ON links(owner, src, dst) WHERE erased_at IS NULL;

CREATE TABLE IF NOT EXISTS entity_subjects (
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    weight DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    fact_count INTEGER NOT NULL DEFAULT 0,
    first_seen TEXT NOT NULL DEFAULT '',
    last_seen TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (owner, entity_id, subject_id, role)
);
CREATE INDEX IF NOT EXISTS idx_entity_subjects_owner_ent ON entity_subjects(owner, entity_id);

CREATE TABLE IF NOT EXISTS milestones (
    id TEXT NOT NULL,
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    subject_id TEXT NOT NULL,
    title TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'in_progress',
    evidence_fact_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    state_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (owner, id)
);
CREATE INDEX IF NOT EXISTS idx_milestones_owner_subj ON milestones(owner, subject_id);

CREATE TABLE IF NOT EXISTS quarantine (
    id BIGSERIAL PRIMARY KEY,
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    record_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'held',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_quarantine_owner ON quarantine(owner, category, status);

CREATE TABLE IF NOT EXISTS forget_rules (
    id BIGSERIAL PRIMARY KEY,
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner, kind, value)
);
CREATE INDEX IF NOT EXISTS idx_forget_rules_owner ON forget_rules(owner, kind);

CREATE TABLE IF NOT EXISTS workers (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    model TEXT NOT NULL,
    model_version TEXT NOT NULL DEFAULT '',
    runner TEXT NOT NULL,
    owner TEXT,
    prompt_versions JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'online',
    released BOOLEAN NOT NULL DEFAULT FALSE,
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_workers_kind_status ON workers(kind, status);

CREATE TABLE IF NOT EXISTS tokens (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    owner TEXT,
    label TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_tokens_owner_active ON tokens(owner, role) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 1,
    pool TEXT NOT NULL DEFAULT 'internal',
    input_ref TEXT[] NOT NULL DEFAULT '{}',
    input_version INTEGER NOT NULL DEFAULT 0,
    context_hash TEXT NOT NULL DEFAULT '',
    prompt_version TEXT NOT NULL DEFAULT 'extract@3',
    day TEXT,
    sensitive_flag BOOLEAN NOT NULL DEFAULT FALSE,
    state TEXT NOT NULL DEFAULT 'queued',
    attempt_no INTEGER NOT NULL DEFAULT 0,
    fence_token TEXT,
    worker_id TEXT,
    lease_expires_at TIMESTAMPTZ,
    fallback_at TIMESTAMPTZ,
    not_before TIMESTAMPTZ NOT NULL DEFAULT now(),
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_jobs_claim ON jobs(state, priority, created_at) WHERE state = 'queued';
CREATE INDEX IF NOT EXISTS idx_jobs_owner_day ON jobs(owner, day, kind);
CREATE INDEX IF NOT EXISTS idx_jobs_leased ON jobs(state, lease_expires_at) WHERE state = 'leased';

CREATE TABLE IF NOT EXISTS job_attempts (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    owner TEXT NOT NULL,
    attempt_no INTEGER NOT NULL,
    fence_token TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    worker_kind TEXT NOT NULL,
    model TEXT NOT NULL,
    model_observed TEXT,
    prompt_version TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    output_json JSONB,
    verdict TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_job ON job_attempts(job_id, attempt_no);
CREATE INDEX IF NOT EXISTS idx_attempts_owner ON job_attempts(owner, finished_at);

CREATE TABLE IF NOT EXISTS outbox (
    id BIGSERIAL PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    priority INTEGER NOT NULL DEFAULT 1,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_outbox_unpub ON outbox(id) WHERE published_at IS NULL;

CREATE OR REPLACE VIEW visible_facts AS
SELECT f.*
FROM facts f
WHERE f.erased_at IS NULL
  AND f.status <> 'history'
  AND NOT EXISTS (
      SELECT 1
      FROM fact_evidence fe
      JOIN records r ON r.id = fe.record_id AND r.owner = fe.owner
      WHERE fe.fact_id = f.id
        AND fe.owner = f.owner
        AND (r.erased_at IS NOT NULL OR r.generation > fe.record_generation)
  )
  AND NOT EXISTS (
      SELECT 1
      FROM forget_rules fr
      WHERE fr.owner = f.owner
        AND (
            (fr.kind = 'item' AND fr.value = f.id)
            OR (fr.kind = 'text' AND position(lower(fr.value) IN lower(f.text)) > 0)
        )
  );

CREATE OR REPLACE VIEW hypotheses AS
SELECT *
FROM visible_facts
WHERE status = 'hypothesis';
