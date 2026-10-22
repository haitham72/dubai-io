-- Gate A: backend-owned manual responsibilities. No browser/Data API policies.
SET search_path TO dubaiio, extensions, public;
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY, owner TEXT NOT NULL, creation_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
    revision INTEGER NOT NULL, status TEXT NOT NULL, cancelled_at TEXT, updated_at TEXT NOT NULL,
    data TEXT NOT NULL, UNIQUE(owner,creation_key), UNIQUE(id,owner));
CREATE INDEX IF NOT EXISTS tasks_owner_updated ON tasks(owner,status,updated_at,id);
CREATE TABLE IF NOT EXISTS task_events (
    task_id TEXT NOT NULL, owner TEXT NOT NULL, seq INTEGER NOT NULL, command_key TEXT NOT NULL,
    payload_hash TEXT NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL, data TEXT NOT NULL,
    PRIMARY KEY(task_id,seq), UNIQUE(owner,task_id,command_key),
    FOREIGN KEY(task_id,owner) REFERENCES tasks(id,owner));
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON tasks,task_events FROM PUBLIC,anon,authenticated,service_role;
