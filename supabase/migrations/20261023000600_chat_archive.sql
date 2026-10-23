-- Owner-scoped chat archive (additive).
SET search_path TO dubaiio, extensions, public;
CREATE TABLE IF NOT EXISTS chat_archived (owner TEXT NOT NULL, thread_id TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY(owner, thread_id));
ALTER TABLE chat_archived ENABLE ROW LEVEL SECURITY;
