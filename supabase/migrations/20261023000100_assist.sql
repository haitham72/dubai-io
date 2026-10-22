-- Backend-only follow-up mode per owner (ask | auto | learn). No mode can send, share or pay.
SET search_path TO dubaiio, extensions, public;
CREATE TABLE IF NOT EXISTS assist (owner TEXT PRIMARY KEY, mode TEXT NOT NULL,
        manual_reminders INTEGER NOT NULL, offer_dismissed INTEGER NOT NULL, updated_at TEXT NOT NULL);
ALTER TABLE assist ENABLE ROW LEVEL SECURITY;
