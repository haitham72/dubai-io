"""Owner-scoped workspaces. Membership/context never authorizes an Action."""
from datetime import datetime, timezone
import json
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .actions import COOKIE, engine, fingerprint
from .tasks import Tasks, present

router = APIRouter(tags=["projects"])
DDL = (
    """CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL, context TEXT NOT NULL,
        revision INTEGER NOT NULL, status TEXT NOT NULL, creation_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(owner,creation_key), UNIQUE(id,owner))""",
    "CREATE INDEX IF NOT EXISTS projects_owner_updated ON projects(owner,status,updated_at,id)",
    """CREATE TABLE IF NOT EXISTS project_tasks (
        project_id TEXT NOT NULL, owner TEXT NOT NULL, task_id TEXT NOT NULL,
        PRIMARY KEY(project_id,owner,task_id), FOREIGN KEY(project_id,owner) REFERENCES projects(id,owner),
        FOREIGN KEY(task_id,owner) REFERENCES tasks(id,owner))""",
    """CREATE TABLE IF NOT EXISTS project_chats (
        owner TEXT NOT NULL, thread_id TEXT NOT NULL, project_id TEXT NOT NULL, title TEXT NOT NULL,
        PRIMARY KEY(owner,thread_id), FOREIGN KEY(project_id,owner) REFERENCES projects(id,owner))""",
    """CREATE TABLE IF NOT EXISTS project_commands (
        owner TEXT NOT NULL, project_id TEXT NOT NULL, command_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
        revision INTEGER NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL,
        PRIMARY KEY(owner,project_id,command_key), UNIQUE(project_id,revision),
        FOREIGN KEY(project_id,owner) REFERENCES projects(id,owner))""",
)


class ProjectFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    context: str = Field(default="", max_length=4000)

    @field_validator("name", "context")
    @classmethod
    def trim(cls, value, info):
        value = value.strip()
        if info.field_name == "name" and not value:
            raise ValueError("Enter a project name")
        return value


class CreateProject(ProjectFields):
    creation_key: str = Field(min_length=8, max_length=100)


class ProjectChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    context: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def provided(self):
        if not self.model_fields_set or any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Provide a name or shared context change")
        for name in self.model_fields_set:
            setattr(self, name, getattr(self, name).strip())
        if self.name == "":
            raise ValueError("Enter a project name")
        return self


class ProjectCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["edit", "add_task", "remove_task", "add_chat", "remove_chat", "archive", "restore"]
    expected_revision: int = Field(ge=1)
    command_key: str = Field(min_length=8, max_length=100)
    changes: ProjectChanges | None = None
    task_id: str | None = Field(default=None, min_length=1, max_length=64)
    thread_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    title: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Enter a chat title")
        return value.strip() if value else value

    @model_validator(mode="after")
    def required_fields(self):
        allowed = {"edit": {"changes"}, "add_task": {"task_id"}, "remove_task": {"task_id"},
                   "add_chat": {"thread_id", "title"}, "remove_chat": {"thread_id"}}.get(self.kind, set())
        for name in ("changes", "task_id", "thread_id", "title"):
            if (getattr(self, name) is not None) != (name in allowed):
                raise ValueError("Provide only the fields needed by this project change")
        return self


class Projects:
    def __init__(self, store):
        self.store = store
        self.tasks = Tasks(store)
        with store.lock:
            if not getattr(store, "_projects_ready", False):
                try:
                    for sql in DDL:
                        store.db.execute(sql)
                    if store.db.dialect == "postgres":
                        for table in ("projects", "project_tasks", "project_chats", "project_commands"):
                            store.db.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
                    store.commit()
                    store._projects_ready = True
                except Exception:
                    store.db.conn.rollback()
                    raise

    def get(self, owner, project_id):
        row = self.store.db.execute("SELECT id,name,context,revision,status,created_at,updated_at FROM projects WHERE owner=? AND id=?", (owner, project_id)).fetchone()
        if not row:
            raise HTTPException(404, "Project not found")
        return dict(zip(("id", "name", "context", "revision", "status", "created_at", "updated_at"), row))

    def detail(self, owner, project_id):
        project = self.get(owner, project_id)
        rows = self.store.db.execute("""SELECT t.data FROM project_tasks p JOIN tasks t ON t.id=p.task_id AND t.owner=p.owner
            WHERE p.owner=? AND p.project_id=? ORDER BY t.updated_at DESC,t.id DESC""", (owner, project_id)).fetchall()
        chats = self.store.db.execute("SELECT thread_id,title FROM project_chats WHERE owner=? AND project_id=? ORDER BY title,thread_id", (owner, project_id)).fetchall()
        return {"project": project, "tasks": [present(json.loads(row[0])) for row in rows],
                "chats": [{"id": row[0], "title": row[1]} for row in chats], "chat_storage": "device_local"}

    def create(self, owner, body):
        digest = fingerprint(body.model_dump(exclude={"creation_key"}))
        with self.store.transaction(owner):
            row = self.store.db.execute("SELECT id,payload_hash FROM projects WHERE owner=? AND creation_key=?", (owner, body.creation_key)).fetchone()
            if row:
                if row[1] != digest:
                    raise HTTPException(409, "This save key already belongs to another project")
                return {**self.detail(owner, row[0]), "replayed": True}
            project_id, at = uuid4().hex, datetime.now(timezone.utc).isoformat()
            self.store.db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?,?)",
                (project_id, owner, body.name, body.context, 1, "ACTIVE", body.creation_key, digest, at, at))
            return {**self.detail(owner, project_id), "replayed": False}

    def command(self, owner, project_id, body):
        digest = fingerprint(body.model_dump(exclude={"command_key"}))
        with self.store.transaction(owner):
            project = self.get(owner, project_id)
            row = self.store.db.execute("SELECT payload_hash FROM project_commands WHERE owner=? AND project_id=? AND command_key=?", (owner, project_id, body.command_key)).fetchone()
            if row:
                if row[0] != digest:
                    raise HTTPException(409, "This change key already belongs to another project change")
                return {**self.detail(owner, project_id), "replayed": True}
            if project["revision"] != body.expected_revision:
                raise HTTPException(409, "This project changed. Open its latest details before changing it.")
            if project["status"] == "ARCHIVED" and body.kind != "restore":
                raise HTTPException(409, "Restore the project before changing it")
            if body.kind == "edit":
                project.update(body.changes.model_dump(exclude_unset=True))
            elif body.kind == "add_task":
                self.tasks.get(owner, body.task_id)  # Validate ownership before membership.
                self.store.db.execute("INSERT OR IGNORE INTO project_tasks VALUES (?,?,?)", (project_id, owner, body.task_id))
            elif body.kind == "remove_task":
                self.store.db.execute("DELETE FROM project_tasks WHERE owner=? AND project_id=? AND task_id=?", (owner, project_id, body.task_id))
            elif body.kind == "add_chat":
                row = self.store.db.execute("SELECT project_id FROM project_chats WHERE owner=? AND thread_id=?", (owner, body.thread_id)).fetchone()
                if row and row[0] != project_id:
                    raise HTTPException(409, "This chat belongs to another project. Remove it there before adding it here.")
                # A chat reference is scoped to this owner, including model thread
                # hashing. It never grants access to another owner's transcript.
                self.store.db.execute("INSERT INTO project_chats VALUES (?,?,?,?) ON CONFLICT(owner,thread_id) DO UPDATE SET title=excluded.title", (owner, body.thread_id, project_id, body.title.strip()))
            elif body.kind == "remove_chat":
                self.store.db.execute("DELETE FROM project_chats WHERE owner=? AND project_id=? AND thread_id=?", (owner, project_id, body.thread_id))
            else:
                project["status"] = "ARCHIVED" if body.kind == "archive" else "ACTIVE"
            at = datetime.now(timezone.utc).isoformat()
            updated = self.store.db.execute("UPDATE projects SET name=?,context=?,status=?,revision=revision+1,updated_at=? WHERE owner=? AND id=? AND revision=?",
                (project["name"], project["context"], project["status"], at, owner, project_id, body.expected_revision))
            if updated.rowcount != 1:
                raise HTTPException(409, "This project changed. Open its latest details.")
            # Store only command hashes/metadata, never old shared context text.
            self.store.db.execute("INSERT INTO project_commands VALUES (?,?,?,?,?,?,?)", (owner, project_id, body.command_key, digest, body.expected_revision + 1, body.kind, at))
            return {**self.detail(owner, project_id), "replayed": False}

    def for_chat(self, owner, thread_id):
        row = self.store.db.execute("SELECT p.id FROM projects p JOIN project_chats c ON c.project_id=p.id AND c.owner=p.owner WHERE c.owner=? AND c.thread_id=? AND p.status='ACTIVE'", (owner, thread_id)).fetchone()
        return self.get(owner, row[0]) if row else None


def owned(request, response):
    response.headers["Cache-Control"] = "private, no-store"
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))
    return Projects(store), owner


def resolve_context(store, owner, thread_id, reference):
    if not 0 <= (datetime.now(timezone.utc) - reference.selected_at).total_seconds() <= 1800:
        return None
    projects = Projects(store)
    with projects.tasks.transaction(owner):
        project = projects.for_chat(owner, thread_id)
        if not project or project["id"] != reference.project_id:
            raise HTTPException(409, "This chat is no longer in the selected project. Reopen its latest workspace.")
        if project["revision"] != reference.revision:
            raise HTTPException(409, "The shared project context changed. Reopen its latest workspace before asking.")
        rows = store.db.execute("""SELECT t.data FROM project_tasks p JOIN tasks t ON t.id=p.task_id AND t.owner=p.owner
            WHERE p.owner=? AND p.project_id=? ORDER BY t.updated_at DESC,t.id DESC LIMIT 21""", (owner, project["id"])).fetchall()
        return {"project_id": project["id"], "revision": project["revision"], "name": project["name"],
                "context": project["context"], "tasks": [{k: t.get(k) for k in ("id", "outcome", "next_step", "due_at", "status")} for t in (json.loads(row[0]) for row in rows[:20])],
                "has_more_tasks": len(rows) > 20}


@router.post("/api/projects")
def create_project(body: CreateProject, request: Request, response: Response):
    projects, owner = owned(request, response)
    return projects.create(owner, body)


@router.get("/api/projects")
def list_projects(request: Request, response: Response, offset: int = Query(default=0, ge=0), limit: int = Query(default=30, ge=1, le=50)):
    projects, owner = owned(request, response)
    with projects.tasks.transaction(owner):
        rows = projects.store.db.execute("SELECT id FROM projects WHERE owner=? ORDER BY status,updated_at DESC,id DESC LIMIT ? OFFSET ?", (owner, limit + 1, offset)).fetchall()
        return {"projects": [projects.get(owner, row[0]) for row in rows[:limit]], "next_offset": offset + limit if len(rows) > limit else None}


@router.get("/api/projects/for-chat/{thread_id}")
def chat_project(thread_id: str, request: Request, response: Response):
    projects, owner = owned(request, response)
    with projects.tasks.transaction(owner):
        return {"project": projects.for_chat(owner, thread_id)}


@router.get("/api/projects/{project_id}")
def project_detail(project_id: str, request: Request, response: Response):
    projects, owner = owned(request, response)
    with projects.tasks.transaction(owner):
        return projects.detail(owner, project_id)


@router.post("/api/projects/{project_id}/commands")
def project_command(project_id: str, body: ProjectCommand, request: Request, response: Response):
    projects, owner = owned(request, response)
    return projects.command(owner, project_id, body)
