-- ML comment analysis + embeddings (additive; nothing deleted).
SET search_path TO dubaiio, extensions, public;
CREATE TABLE IF NOT EXISTS comment_labels (comment_id TEXT PRIMARY KEY, post_id TEXT NOT NULL, sentiment TEXT NOT NULL, neg REAL NOT NULL, neu REAL NOT NULL, pos REAL NOT NULL, topics TEXT NOT NULL, harsh INTEGER NOT NULL, harsh_basis TEXT NOT NULL, model TEXT NOT NULL, analyzed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS comment_embeddings (comment_id TEXT PRIMARY KEY, post_id TEXT NOT NULL, model TEXT NOT NULL, dim INTEGER NOT NULL, vec TEXT NOT NULL);
ALTER TABLE comment_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE comment_embeddings ENABLE ROW LEVEL SECURITY;
