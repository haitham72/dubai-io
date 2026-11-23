-- Messenger chat tables. Not applied. Local Docker Supabase comes first (D12).
-- The API membership check is the fence until this script is run on that database.

CREATE TABLE IF NOT EXISTS mg_conversations (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mg_memberships (
    conversation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    ai_mode TEXT NOT NULL DEFAULT 'off',
    PRIMARY KEY (conversation_id, user_id)
);
CREATE TABLE IF NOT EXISTS mg_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    client_msg_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    edited_at TEXT,
    deleted_at TEXT,
    UNIQUE (conversation_id, sender_id, client_msg_id)
);
CREATE TABLE IF NOT EXISTS mg_receipts (
    message_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    at TEXT NOT NULL,
    PRIMARY KEY (message_id, user_id, kind)
);
