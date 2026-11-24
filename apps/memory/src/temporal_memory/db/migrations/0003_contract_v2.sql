ALTER TABLE facts
    ADD COLUMN IF NOT EXISTS actor_entity_id TEXT,
    ADD COLUMN IF NOT EXISTS predicate TEXT,
    ADD COLUMN IF NOT EXISTS object_text TEXT,
    ADD COLUMN IF NOT EXISTS object_entity_id TEXT,
    ADD COLUMN IF NOT EXISTS polarity TEXT,
    ADD COLUMN IF NOT EXISTS modality TEXT,
    ADD COLUMN IF NOT EXISTS event_at TEXT,
    ADD COLUMN IF NOT EXISTS span_record_id TEXT,
    ADD COLUMN IF NOT EXISTS span_start INTEGER,
    ADD COLUMN IF NOT EXISTS span_end INTEGER,
    ADD COLUMN IF NOT EXISTS reason_text TEXT,
    ADD COLUMN IF NOT EXISTS reason_record_id TEXT,
    ADD COLUMN IF NOT EXISTS reason_start INTEGER,
    ADD COLUMN IF NOT EXISTS reason_end INTEGER;

ALTER TABLE entities
    ADD COLUMN IF NOT EXISTS place_type TEXT;

CREATE TABLE IF NOT EXISTS topic_mentions (
    owner TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    first_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner, subject_id, session_id),
    FOREIGN KEY (owner, subject_id) REFERENCES subjects(owner, id) ON DELETE CASCADE
);
