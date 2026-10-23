-- Community votes (additive).
SET search_path TO dubaiio, extensions, public;
CREATE TABLE IF NOT EXISTS votes (target_type TEXT NOT NULL, target_id TEXT NOT NULL, owner TEXT NOT NULL, value INTEGER NOT NULL, PRIMARY KEY(target_type, target_id, owner));
ALTER TABLE votes ENABLE ROW LEVEL SECURITY;
