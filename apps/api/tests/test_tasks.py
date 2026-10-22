"""Owner, command/revision, recovery and honest manual-status contracts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions, tasks
from app.actions import ActionEngine, ActionStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "tasks.sqlite3"
    store = ActionStore(path)
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(tasks.router)
    c = TestClient(app)
    owner = c.get("/api/session").json()["user_id"]
    yield c, store, owner, path
    store.db.close()


def create(c, **kw):
    response = c.post("/api/tasks", json={"outcome": "Follow up on my lost bag", "creation_key": uuid4().hex, **kw})
    assert response.status_code == 200, response.text
    return response.json()["task"]


def command(c, task, kind, **kw):
    return c.post(f'/api/tasks/{task["id"]}/commands', json={"kind": kind,
        "expected_revision": task["revision"], "command_key": uuid4().hex, **kw})


def test_manual_task_survives_restart_with_history_and_no_execution(client, monkeypatch):
    c, store, owner, path = client
    task = create(c, due_at="2026-10-28T09:00:00+04:00", details="Cash; no receipt")
    assert task["status"] == "WAITING_USER" and task["mode"] == "manual"
    assert task["due_at"] == "2026-10-28T05:00:00+00:00"
    assert task["provenance"] == "user_supplied"
    second = ActionStore(path)
    try:
        monkeypatch.setattr(actions, "_engine", ActionEngine(second))
        result = c.get(f'/api/tasks/{task["id"]}')
        assert result.headers["cache-control"] == "private, no-store"
        assert result.json()["task"] == task
        assert [e["kind"] for e in result.json()["events"]] == ["created"]
        today = c.get("/api/today").json()
        assert not today["monitoring_active"] and not today["running"]["tasks"]
        assert second.db.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 0
    finally:
        second.db.close()


def test_owner_isolation_covers_list_detail_commands_and_history(client):
    c, store, owner, path = client
    task = create(c)
    other = TestClient(c.app)
    assert other.get("/api/tasks").status_code == 401
    assert other.post("/api/tasks", json={"outcome":"Private", "creation_key":"private-create"}).status_code == 401
    other.get("/api/session")
    assert other.get("/api/tasks").json()["tasks"] == []
    assert other.get("/api/today").json()["needs_you"]["tasks"] == []
    for path in (f'/api/tasks/{task["id"]}', f'/api/tasks/{task["id"]}/activity?before_seq=5'):
        assert other.get(path).status_code == 404
    assert command(other, task, "cancel").status_code == 404


def test_creation_replay_and_key_conflict_do_not_duplicate_tasks(client):
    c, *_ = client
    task = create(c, creation_key="same-save-key")
    assert create(c, creation_key="same-save-key")["id"] == task["id"]
    conflict = c.post("/api/tasks", json={"outcome":"Different", "creation_key":"same-save-key"})
    assert conflict.status_code == 409
    assert len(c.get("/api/tasks").json()["tasks"]) == 1
    assert len(c.get(f'/api/tasks/{task["id"]}').json()["events"]) == 1


def test_stale_edit_cannot_overwrite_cancel_and_replayed_command_returns_current_state(client):
    c, *_ = client
    task = create(c, creation_key="initial-task-key")
    edit = {"changes":{"outcome":"A new deadline"}, "command_key":"same-edit-key"}
    edited = command(c, task, "edit", **edit).json()["task"]
    cancelled = command(c, edited, "cancel").json()["task"]
    assert cancelled["cancelled_at"] and cancelled["status"] == "CANCELLED"
    assert command(c, task, "edit", changes={"details":"stale"}).status_code == 409
    replay = command(c, task, "edit", **edit).json()
    assert replay["replayed"] and replay["task"] == cancelled
    assert create(c, creation_key="initial-task-key") == cancelled
    assert command(c, task, "edit", changes={"details":"different"}, command_key="same-edit-key").status_code == 409
    assert len(c.get(f'/api/tasks/{task["id"]}').json()["events"]) == 3


def test_pause_resume_completion_are_explicit_user_reports(client):
    c, *_ = client
    task = create(c)
    assert command(c, task, "resume").status_code == 409
    task = command(c, task, "pause").json()["task"]
    assert task["status"] == "PAUSED"
    assert not c.get("/api/today").json()["needs_you"]["tasks"]
    assert command(c, task, "pause").status_code == 409
    task = command(c, task, "resume").json()["task"]
    done = command(c, task, "complete", result="I collected the bag myself").json()["task"]
    assert done["status"] == "COMPLETED" and done["result"]["provenance"] == "user_supplied"
    assert done["result"]["as_of"]
    assert c.get("/api/today").json()["completed"]["tasks"][0]["id"] == done["id"]
    assert command(c, done, "cancel").status_code == 409
    assert command(c, done, "edit", changes={"outcome":"Reopen"}).status_code == 409


def test_two_connections_compete_for_one_revision_without_lost_updates(client):
    c, store, owner, path = client
    task = create(c)
    second = ActionStore(path)
    repositories = [tasks.Tasks(store), tasks.Tasks(second)]
    def edit(index):
        body = tasks.TaskCommand(kind="edit", expected_revision=1, command_key=uuid4().hex,
                                 changes=tasks.TaskChanges(outcome=f"Change {index}"))
        try:
            return repositories[index].command(owner, task["id"], body)["task"]["revision"]
        except tasks.HTTPException as err:
            return err.status_code
    try:
        with ThreadPoolExecutor(2) as pool:
            assert sorted(pool.map(edit, (0,1))) == [2,409]
        detail = c.get(f'/api/tasks/{task["id"]}').json()
        assert detail["task"]["revision"] == 2 and len(detail["events"]) == 2
    finally:
        second.db.close()


def test_failed_event_append_rolls_back_the_state_change(client, monkeypatch):
    c, store, owner, path = client
    task = create(c)
    execute = store.db.execute
    def failing(sql, params=()):
        if sql.startswith("INSERT INTO task_events"):
            raise RuntimeError("Simulated event storage failure")
        return execute(sql, params)
    monkeypatch.setattr(store.db, "execute", failing)
    with pytest.raises(RuntimeError, match="Simulated"):
        command(c, task, "cancel")
    detail = c.get(f'/api/tasks/{task["id"]}').json()
    assert detail["task"] == task and len(detail["events"]) == 1


def test_today_previews_and_pagination_do_not_hide_tasks(client):
    c, *_ = client
    for i in range(5):
        create(c, outcome=f"Task {i}")
    today = c.get("/api/today").json()
    assert len(today["on_list"]["tasks"]) == 3 and today["on_list"]["has_more"]
    assert today["needs_you"]["tasks"] == []
    first = c.get("/api/tasks?limit=3").json()
    second = c.get(f'/api/tasks?limit=3&offset={first["next_offset"]}').json()
    assert len(first["tasks"]) == 3 and len(second["tasks"]) == 2 and second["next_offset"] is None
    assert len({t["id"] for t in first["tasks"]+second["tasks"]}) == 5


def test_bounded_activity_has_an_owner_scoped_older_page(client):
    c, *_ = client
    task = create(c)
    for i in range(51):
        task = command(c, task, "edit", changes={"details":str(i)}).json()["task"]
    detail = c.get(f'/api/tasks/{task["id"]}').json()
    assert len(detail["events"]) == 50 and detail["before_seq"] == 3
    older = c.get(f'/api/tasks/{task["id"]}/activity?before_seq=3').json()
    assert [e["seq"] for e in older["events"]] == [1,2] and older["before_seq"] is None


@pytest.mark.parametrize("extra", [{"status":"COMPLETED"}, {"owner":"tester"}, {"provenance":"provider_confirmed"},
                                   {"outcome":"   "}, {"due_at":"2026-10-28T09:00:00"}])
def test_caller_cannot_set_status_owner_evidence_or_ambiguous_time(client, extra):
    c, *_ = client
    assert c.post("/api/tasks",json={"outcome":"Task", "creation_key":"task-create", **extra}).status_code == 422
    assert c.get("/api/tasks").json()["tasks"] == []


def test_edit_can_clear_due_date_and_details_but_cannot_inject_commands(client):
    c, *_ = client
    task = create(c, due_at="2026-10-28T09:00:00+04:00", details="Some context")
    changed = command(c, task, "edit", changes={"due_at":None, "details":""}).json()["task"]
    assert changed["due_at"] is None and changed["details"] == ""
    for changes in ({"status":"COMPLETED"},{"outcome":None},{"next_step":None},{}):
        assert command(c, changed, "edit", changes=changes).status_code == 422
    assert command(c, changed, "complete", result=" ").status_code == 422


def test_due_priority_and_paused_visibility_do_not_manufacture_decisions(client, monkeypatch):
    c, *_ = client
    monkeypatch.setattr(tasks, "clock", lambda: datetime(2026,10,22,12,tzinfo=timezone.utc))
    create(c, outcome="Tomorrow", due_at="2026-10-23T09:00:00+04:00")
    create(c, outcome="Overdue", due_at="2026-10-20T09:00:00+04:00")
    create(c, outcome="November", due_at="2026-11-01T09:00:00+04:00")
    create(c, outcome="Undated")
    paused = create(c, outcome="On hold")
    command(c, paused, "pause")
    result = c.get("/api/today").json()
    assert [t["outcome"] for t in result["on_list"]["tasks"]] == ["Overdue","Tomorrow","November"]
    assert [t["due_state"] for t in result["on_list"]["tasks"]] == ["overdue","due_soon",None]
    assert result["on_list"]["has_more"] and result["paused"]["count"] == 1
    assert result["counts"] == {"needs_you":0, "on_list":4, "paused":1}
    assert result["paused"]["tasks"][0]["outcome"] == "On hold"
    assert result["needs_you"]["tasks"] == [] and result["running"]["tasks"] == []
    other = TestClient(c.app)
    other.get("/api/session")
    assert other.get("/api/today").json()["paused"]["count"] == 0
    assert other.get("/api/today").json()["counts"] == {"needs_you":0, "on_list":0, "paused":0}


def test_title_only_capture_has_no_invented_next_step(client):
    c, *_ = client
    task = create(c)
    assert task["next_step"] == ""
    assert command(c, task, "edit", changes={"next_step":" "}).json()["task"]["next_step"] == ""
