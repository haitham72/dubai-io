-- Backend-only project workspaces. Chat references do not contain transcripts.
SET search_path TO dubaiio, extensions, public;
CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL, context TEXT NOT NULL,
        revision INTEGER NOT NULL, status TEXT NOT NULL, creation_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(owner,creation_key), UNIQUE(id,owner));
CREATE INDEX IF NOT EXISTS projects_owner_updated ON projects(owner,status,updated_at,id);
CREATE TABLE IF NOT EXISTS project_tasks (
        project_id TEXT NOT NULL, owner TEXT NOT NULL, task_id TEXT NOT NULL,
        PRIMARY KEY(project_id,owner,task_id), FOREIGN KEY(project_id,owner) REFERENCES projects(id,owner),
        FOREIGN KEY(task_id,owner) REFERENCES tasks(id,owner));
CREATE TABLE IF NOT EXISTS project_chats (
        owner TEXT NOT NULL, thread_id TEXT NOT NULL, project_id TEXT NOT NULL, title TEXT NOT NULL,
        PRIMARY KEY(owner,thread_id), FOREIGN KEY(project_id,owner) REFERENCES projects(id,owner));
CREATE TABLE IF NOT EXISTS project_commands (
        owner TEXT NOT NULL, project_id TEXT NOT NULL, command_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
        revision INTEGER NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL,
        PRIMARY KEY(owner,project_id,command_key), UNIQUE(project_id,revision),
        FOREIGN KEY(project_id,owner) REFERENCES projects(id,owner));
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_commands ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON projects,project_tasks,project_chats,project_commands FROM PUBLIC,anon,authenticated,service_role;
