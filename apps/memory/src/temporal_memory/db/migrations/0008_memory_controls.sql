ALTER TABLE owners
    ADD COLUMN deleted_from_external boolean NOT NULL DEFAULT false,
    ADD COLUMN deleted_at timestamptz,
    ADD COLUMN deletion_generation integer NOT NULL DEFAULT 0;
ALTER TABLE facts
    ADD COLUMN lowered_at timestamptz,
    ADD COLUMN weight_steps integer NOT NULL DEFAULT 0 CHECK (weight_steps >= 0),
    ADD COLUMN base_weight double precision NOT NULL DEFAULT 1.0,
    ADD COLUMN last_refreshed_at timestamptz,
    ADD COLUMN refreshed_weight double precision;
ALTER TABLE subjects ADD COLUMN lowered_at timestamptz;
ALTER TABLE records ADD COLUMN lowered_at timestamptz;

CREATE INDEX idx_lowered_subjects_owner_path ON subjects(owner, path) WHERE lowered_at IS NOT NULL;
-- Bounded Vault evidence lookups should not sort all facts in each subject.
CREATE INDEX idx_facts_vault_latest
    ON facts(owner, subject_id, valid_from DESC, id DESC) INCLUDE (provenance)
    WHERE erased_at IS NULL AND status <> 'history';
CREATE TABLE lowered_sources (
    owner text NOT NULL REFERENCES owners(id),
    source text NOT NULL,
    lowered_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (owner, source)
);
CREATE TABLE training_backups (surrogate_id uuid PRIMARY KEY, signal_rows jsonb NOT NULL);
REVOKE ALL ON training_backups FROM PUBLIC;

CREATE FUNCTION memory_weight(
    base double precision, confidence double precision, age_days integer,
    steps integer, provenance text, lowered boolean
) RETURNS double precision LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN lowered THEN 0.01 ELSE GREATEST(0.01,
        LEAST(base * confidence, GREATEST(0.05,
            base * confidence * CASE WHEN provenance IN ('user_supplied', 'provider_confirmed')
                THEN 1.0 ELSE power(2.0, -GREATEST(0, age_days - 30) / 30.0) END
        )) * power(0.5, steps)
    ) END
$$;
CREATE FUNCTION memory_age_days(at_text text, fallback date)
RETURNS integer LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CURRENT_DATE - CASE WHEN left(at_text, 10) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        AND pg_input_is_valid(left(at_text, 10), 'date') THEN left(at_text, 10)::date ELSE fallback END
$$;

CREATE OR REPLACE VIEW visible_facts AS
SELECT f.id, f.owner, f.text, f.text_orig, f.text_folded, f.lang, f.subject_id, f.valid_from,
       f.valid_to, f.status, f.superseded_by, f.provenance, f.confidence, f.job_id, f.attempt_id,
       f.worker_id, f.model, f.prompt_version, f.content_hash, f.tsv, f.erased_at, f.created_at
FROM facts f
JOIN owners o ON o.id = f.owner AND NOT o.deleted_from_external
WHERE f.erased_at IS NULL AND f.status <> 'history'
  AND NOT EXISTS (
    SELECT 1 FROM fact_evidence fe JOIN records r ON (r.owner, r.id) = (fe.owner, fe.record_id)
    WHERE (fe.owner, fe.fact_id) = (f.owner, f.id)
      AND (r.erased_at IS NOT NULL OR r.generation > fe.record_generation)
  )
  AND NOT EXISTS (
    SELECT 1 FROM forget_rules fr WHERE fr.owner = f.owner AND (
      (fr.kind = 'item' AND fr.value = f.id)
      OR (fr.kind = 'text' AND position(lower(fr.value) IN lower(f.text)) > 0)
    )
  );

CREATE FUNCTION memory_source_matches(record_source text, record_id text, target text)
RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT lower(record_source) = target OR starts_with(lower(record_source), target || ':')
        OR starts_with(record_id, 'e3:' || target || ':')
        OR (target = 'agent_sessions' AND starts_with(lower(record_source), 'agent:'))
$$;

CREATE VIEW memory_lowered_records AS
SELECT r.owner, r.id FROM records r
WHERE r.lowered_at IS NOT NULL OR EXISTS (
    SELECT 1 FROM lowered_sources ls WHERE ls.owner = r.owner AND (
        memory_source_matches(r.source, r.id, ls.source)
    )
);
CREATE VIEW memory_fact_weights AS
SELECT f.owner, f.id, f.subject_id, f.text, f.status, f.erased_at,
       memory_weight(COALESCE(f.refreshed_weight, f.base_weight),
           CASE WHEN f.refreshed_weight IS NULL THEN COALESCE(f.confidence, 1.0) ELSE 1.0 END,
           CASE WHEN f.last_refreshed_at IS NULL THEN memory_age_days(f.valid_from, f.created_at::date)
                ELSE CURRENT_DATE - f.last_refreshed_at::date END,
           f.weight_steps, f.provenance, x.lowered) AS weight,
       x.lowered
FROM facts f CROSS JOIN LATERAL (
    SELECT f.lowered_at IS NOT NULL OR EXISTS (
        SELECT 1 FROM subjects target JOIN subjects parent ON parent.owner = target.owner
        WHERE (target.owner, target.id) = (f.owner, f.subject_id) AND parent.lowered_at > COALESCE(f.last_refreshed_at, '-infinity'::timestamptz)
          AND (target.path = parent.path OR starts_with(target.path, parent.path || '/'))
    ) OR EXISTS (
        SELECT 1 FROM fact_evidence fe
        JOIN records r ON (r.owner, r.id) = (fe.owner, fe.record_id)
        WHERE (fe.owner, fe.fact_id) = (f.owner, f.id)
          AND (r.lowered_at > COALESCE(f.last_refreshed_at, '-infinity'::timestamptz)
               OR EXISTS (
                   SELECT 1 FROM lowered_sources ls WHERE ls.owner = r.owner
                     AND ls.lowered_at > COALESCE(f.last_refreshed_at, '-infinity'::timestamptz)
                     AND memory_source_matches(r.source, r.id, ls.source)
               ))
    ) AS lowered
) x;
CREATE VIEW memory_surface_facts AS
SELECT vf.* FROM visible_facts vf
JOIN memory_fact_weights w ON (w.owner, w.id) = (vf.owner, vf.id)
WHERE w.weight >= 0.10;
