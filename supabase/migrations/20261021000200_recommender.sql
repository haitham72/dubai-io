SET search_path TO dubaiio, extensions, public;

CREATE TABLE IF NOT EXISTS recommendation_events (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, event_key TEXT NOT NULL, session_id TEXT NOT NULL, thread_id TEXT,
        kind TEXT NOT NULL, topic TEXT NOT NULL, entity_id TEXT NOT NULL, weight REAL NOT NULL,
        received_at DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL, usage_class TEXT NOT NULL,
        UNIQUE(owner,event_key));

CREATE INDEX IF NOT EXISTS recommendation_events_owner ON recommendation_events(owner,session_id,topic,entity_id);

CREATE TABLE IF NOT EXISTS profile_interests (
        owner TEXT NOT NULL, topic TEXT NOT NULL, scope TEXT NOT NULL, context_key TEXT NOT NULL,
        usage_class TEXT NOT NULL, positive REAL NOT NULL, negative REAL NOT NULL, evidence_count INTEGER NOT NULL,
        last_decay DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL, evidence JSONB NOT NULL,
        status TEXT NOT NULL DEFAULT 'active', PRIMARY KEY(owner,topic,scope,context_key,usage_class));

CREATE TABLE IF NOT EXISTS recommendation_runs (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, session_id TEXT NOT NULL, surface TEXT NOT NULL,
        intent TEXT, profile_version TEXT NOT NULL, ranker_version TEXT NOT NULL, results JSONB NOT NULL,
        created_at DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL);

ALTER TABLE recommendation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE profile_interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendation_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON recommendation_events,profile_interests,recommendation_runs FROM PUBLIC,anon,authenticated,service_role;
