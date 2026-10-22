-- Additive upgrade: no seeded/user content is deleted.
SET search_path TO dubaiio, extensions, public;
ALTER TABLE personas ADD COLUMN IF NOT EXISTS avatar TEXT;
ALTER TABLE personas ADD COLUMN IF NOT EXISTS profile TEXT;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS parent_id TEXT;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS model TEXT;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS trigger_id TEXT;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS persona_id TEXT;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS model TEXT;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS trigger_id TEXT;
CREATE TABLE IF NOT EXISTS social_generations (owner TEXT NOT NULL, request_id TEXT NOT NULL, fingerprint TEXT NOT NULL, trigger_id TEXT NOT NULL, status TEXT NOT NULL, model TEXT NOT NULL, reply_count INTEGER NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner,request_id));
CREATE UNIQUE INDEX IF NOT EXISTS social_comment_trigger ON comments(owner,trigger_id,persona_id);
CREATE UNIQUE INDEX IF NOT EXISTS social_chat_trigger ON chat_messages(owner,trigger_id,persona_id);
ALTER TABLE social_generations ENABLE ROW LEVEL SECURITY;
