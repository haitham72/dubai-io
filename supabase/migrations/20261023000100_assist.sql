-- Backend-only follow-up mode per owner (ask | auto | learn). No mode can send, share or pay.
SET search_path TO dubaiio, extensions, public;
CREATE TABLE IF NOT EXISTS assist (owner TEXT PRIMARY KEY, mode TEXT NOT NULL,
        manual_reminders INTEGER NOT NULL, offer_dismissed INTEGER NOT NULL, updated_at TEXT NOT NULL);
ALTER TABLE assist ENABLE ROW LEVEL SECURITY;
-- Reviewed routines (Gate F): explicit activation, daily time, 30-day expiry.
CREATE TABLE IF NOT EXISTS routines (owner TEXT NOT NULL, kind TEXT NOT NULL, at_time TEXT NOT NULL,
        active INTEGER NOT NULL, expires_at TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(owner, kind));
ALTER TABLE routines ENABLE ROW LEVEL SECURITY;
