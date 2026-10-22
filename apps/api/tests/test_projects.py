from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from app import actions, projects, tasks
from app.actions import ActionEngine, ActionStore
from app.luna.schema import ProjectFocusContext


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "projects.sqlite3"
    store = ActionStore(path)
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    for router in (actions.router, tasks.router, projects.router):
        app.include_router(router)
    c = TestClient(app); owner = c.get("/api/session").json()["user_id"]
    yield c, store, owner, path
    store.db.close()


def create(c, **kw):
    r = c.post("/api/projects", json={"name":"Moving home", "context":"Move before December", "creation_key":uuid4().hex, **kw})
    assert r.status_code == 200, r.text
    return r.json()["project"]


def command(c, p, kind, **kw):
    return c.post(f'/api/projects/{p["id"]}/commands', json={"kind":kind,"expected_revision":p["revision"],"command_key":uuid4().hex,**kw})


def test_create_retry_conflict_and_restart(client):
    c, store, owner, path = client
    p = create(c, creation_key="create-workspace")
    assert create(c, creation_key="create-workspace") == p
    assert c.post("/api/projects",json={"name":"Other", "creation_key":"create-workspace"}).status_code == 409
    second = ActionStore(path)
    try:
        workspace = projects.Projects(second)
        assert workspace.get(owner,p["id"]) == p
    finally:
        second.db.close()
    assert store.db.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 0


def test_owner_isolation_on_all_routes_membership_and_context(client):
    c, store, owner, _ = client
    p = create(c)
    task = c.post("/api/tasks",json={"outcome":"Arrange movers","creation_key":"owned-task"}).json()["task"]
    other = TestClient(c.app)
    assert other.get("/api/projects").status_code == 401
    other.get("/api/session")
    assert other.get("/api/projects").json()["projects"] == []
    assert other.get(f'/api/projects/{p["id"]}').status_code == 404
    assert command(other,p,"add_task",task_id=task["id"]).status_code == 404
    foreign = create(other)
    assert command(other,foreign,"add_task",task_id=task["id"]).status_code == 404
    command(c,p,"add_chat",thread_id="shared-thread-id",title="Moving")
    assert other.get("/api/projects/for-chat/shared-thread-id").json()["project"] is None


def test_membership_commands_are_revision_bound_idempotent_and_do_not_change_sources(client):
    c, store, *_ = client
    p = create(c)
    task = c.post("/api/tasks",json={"outcome":"Arrange movers","creation_key":"arrange-movers"}).json()["task"]
    result = command(c,p,"add_task",task_id=task["id"],command_key="link-task-once")
    assert result.status_code == 200 and len(result.json()["tasks"]) == 1
    latest = result.json()["project"]
    assert command(c,p,"add_task",task_id=task["id"],command_key="link-task-once").json()["replayed"]
    assert command(c,p,"archive",command_key="link-task-once").status_code == 409
    assert command(c,p,"edit",changes={"name":"Stale"}).status_code == 409
    linked = command(c,latest,"add_chat",thread_id="my-thread",title="Moving plan").json()
    assert linked["chats"] == [{"id":"my-thread","title":"Moving plan"}]
    unlinked = command(c,linked["project"],"remove_task",task_id=task["id"]).json()
    assert unlinked["tasks"] == [] and c.get(f'/api/tasks/{task["id"]}').json()["task"] == task
    assert store.db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0


def test_scoped_context_requires_current_owner_membership_revision_and_fresh_reference(client):
    c, store, owner, _ = client
    p = create(c)
    p = command(c,p,"add_chat",thread_id="workspace-thread",title="Plan").json()["project"]
    ref = ProjectFocusContext(project_id=p["id"],revision=p["revision"],selected_at=datetime.now(timezone.utc))
    resolved = projects.resolve_context(store,owner,"workspace-thread",ref)
    assert resolved["context"] == "Move before December" and resolved["tasks"] == []
    with pytest.raises(HTTPException): projects.resolve_context(store,owner,"unrelated-thread",ref)
    command(c,p,"edit",changes={"context":"New date"})
    with pytest.raises(HTTPException): projects.resolve_context(store,owner,"workspace-thread",ref)
    assert projects.resolve_context(store,owner,"workspace-thread",ref.model_copy(update={"selected_at":datetime.now(timezone.utc)-timedelta(hours=1)})) is None


def test_archive_restore_keeps_references_and_stops_shared_context(client):
    c, store, owner, _ = client
    p = create(c)
    p = command(c,p,"add_chat",thread_id="archive-thread",title="My plan").json()["project"]
    archived = command(c,p,"archive").json()
    assert archived["chats"] and archived["project"]["status"] == "ARCHIVED"
    assert c.get("/api/projects/for-chat/archive-thread").json()["project"] is None
    assert command(c,archived["project"],"edit",changes={"name":"Blocked"}).status_code == 409
    restored = command(c,archived["project"],"restore").json()
    assert restored["project"]["status"] == "ACTIVE" and restored["chats"]


def test_concurrent_edits_have_one_winner_across_store_handles(client):
    c, store, owner, path = client
    p = create(c)
    other = ActionStore(path)
    try:
        engines = (projects.Projects(store),projects.Projects(other))
        def edit(pair):
            index, workspace = pair
            try:
                return workspace.command(owner,p["id"],projects.ProjectCommand(kind="edit",expected_revision=1,command_key=f"concurrent-{index}",changes={"name":f"Name {index}"}))["project"]["revision"]
            except HTTPException as e:
                return e.status_code
        with ThreadPoolExecutor(2) as pool:
            assert sorted(pool.map(edit,enumerate(engines))) == [2,409]
    finally:
        other.db.close()


def test_receipt_failure_rolls_back_membership_and_revision(client, monkeypatch):
    c, store, *_ = client
    p = create(c)
    task = c.post("/api/tasks",json={"outcome":"Keep this","creation_key":"rollback-member"}).json()["task"]
    execute = store.db.execute
    def fail(sql, params=()):
        if sql.startswith("INSERT INTO project_commands"):
            raise RuntimeError("receipt failure")
        return execute(sql,params)
    monkeypatch.setattr(store.db,"execute",fail)
    with pytest.raises(RuntimeError): command(c,p,"add_task",task_id=task["id"])
    assert c.get(f'/api/projects/{p["id"]}').json()["tasks"] == []
    assert c.get(f'/api/projects/{p["id"]}').json()["project"]["revision"] == 1


def test_partial_edit_keeps_context_until_explicit_clear_and_does_not_retain_old_notes_in_receipts(client):
    c, store, *_ = client
    p = create(c)
    p = command(c,p,"edit",changes={"name":"New name"}).json()["project"]
    assert p["context"] == "Move before December"
    p = command(c,p,"edit",changes={"context":""}).json()["project"]
    assert p["context"] == ""
    assert "Move before December" not in str(store.db.execute("SELECT * FROM project_commands").fetchall())
    assert command(c,p,"edit",changes={}).status_code == 422
    assert command(c,p,"edit",changes={"name":None}).status_code == 422
    assert command(c,p,"add_chat",thread_id="x",title="  ").status_code == 422
