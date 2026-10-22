"""Owner, command/revision, recovery and honest manual-status contracts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions, tasks
from app.actions import ActionEngine, ActionStore
from app.luna.schema import TaskFocusContext


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
    assert result["counts"] == {"needs_you":0, "running":0, "on_list":4, "paused":1}
    assert result["paused"]["tasks"][0]["outcome"] == "On hold"
    assert result["needs_you"]["tasks"] == [] and result["running"]["tasks"] == []
    other = TestClient(c.app)
    other.get("/api/session")
    assert other.get("/api/today").json()["paused"]["count"] == 0
    assert other.get("/api/today").json()["counts"] == {"needs_you":0, "running":0, "on_list":0, "paused":0}


def test_title_only_capture_has_no_invented_next_step(client):
    c, *_ = client
    task = create(c)
    assert task["next_step"] == ""
    assert command(c, task, "edit", changes={"next_step":" "}).json()["task"]["next_step"] == ""


def report_fields():
    return {key:{"value":value} for key,value in {"description":"Blue backpack", "when":"22 Oct 2026 10:00 Dubai time",
            "from":"Airport Terminal 3", "to":"Deira", "payment":"Cash"}.items()}


def test_tracking_report_is_idempotent_and_never_files_or_sends(client):
    c, store, *_ = client
    body = {"fields":report_fields()}
    first = c.post("/api/tasks/from-report",json=body)
    assert first.status_code == 200, first.text
    task = first.json()["task"]
    assert task["source"]["kind"] == "action" and task["mode"] == "manual"
    second = c.post("/api/tasks/from-report",json=body).json()
    assert second["replayed"] and second["task"]["id"] == task["id"]
    detail = c.get(f'/api/tasks/{task["id"]}').json()
    source = detail["linked_item"]
    assert source["status"] == "BLOCKED" and source["evidence"] is None
    assert source["capability_id"] == "recovery.rta" and len(source["events"]) == 1
    assert store.db.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 1
    assert store.db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0
    assert len(detail["events"]) == 1


def test_tracking_order_does_not_approve_and_reopens_terminal_tracking(client):
    c, store, *_ = client
    action = c.post("/api/actions/prepare",json={"capability_id":"order.request", "fields":{"area":{"value":"JLT"}},
        "order":{"provider_id":"marinaexpress","items":[{"name":"Shirt wash + press","qty":1}]}}).json()
    assert action["status"] == "AWAITING_APPROVAL"
    body = {"action_id":action["id"]}
    task = c.post("/api/tasks/from-action",json=body).json()["task"]
    cancelled = command(c, task, "cancel").json()["task"]
    assert c.post("/api/tasks/from-action",json=body).json()["task"] == cancelled
    assert c.get(f'/api/actions/{action["id"]}').json()["status"] == "AWAITING_APPROVAL"
    assert store.db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0
    assert len(c.get("/api/tasks").json()["tasks"]) == 1


def test_home_current_work_is_source_backed_owned_and_never_dispatches(client):
    c, store, owner, _ = client
    create(c, outcome="A manual note is not running")
    action = c.post("/api/actions/prepare",json={"capability_id":"order.request", "fields":{"area":{"value":"JLT"}},
        "order":{"provider_id":"marinaexpress","items":[{"name":"Shirt wash + press","qty":1}]}}).json()
    task = c.post("/api/tasks/from-action",json={"action_id":action["id"]}).json()["task"]
    today = c.get("/api/today").json()
    assert [item["task"]["id"] for item in today["current_work"]] == [task["id"]]
    assert today["current_work"][0]["source"]["status"] == "AWAITING_APPROVAL"
    assert today["running"]["tasks"] == [] and not today["monitoring_active"]
    assert store.db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0
    other = TestClient(c.app); other.get("/api/session")
    assert other.get("/api/today").json()["current_work"] == []
    command(c,task,"pause")
    assert c.get("/api/today").json()["current_work"] == []


def test_home_running_uses_authoritative_source_state_and_keeps_manual_state_separate(client):
    c, store, owner, _ = client
    action = c.post("/api/actions/prepare",json={"capability_id":"order.request", "fields":{"area":{"value":"JLT"}},
        "order":{"provider_id":"marinaexpress","items":[{"name":"Shirt wash + press","qty":1}]}}).json()
    task = c.post("/api/tasks/from-action",json={"action_id":action["id"]}).json()["task"]
    # Simulate a canonical provider event, rather than a model's claim.
    action["status"] = "ACCEPTED"
    store.put(owner,action)
    today = c.get("/api/today").json()
    assert today["running"]["tasks"][0]["source_status"] == "ACCEPTED"
    assert today["running"]["tasks"][0]["status"] == "WAITING_USER"
    action["status"] = "COMPLETED"; store.put(owner,action)
    assert c.get("/api/today").json()["current_work"] == []
    assert c.get(f'/api/tasks/{task["id"]}').json()["task"]["status"] == "WAITING_USER"


def test_source_link_and_context_are_owner_bound_and_cannot_be_forged(client):
    c, store, owner, _ = client
    task = c.post("/api/tasks/from-report",json={"fields":report_fields()}).json()["task"]
    other = TestClient(c.app)
    other_owner = other.get("/api/session").json()["user_id"]
    assert other.post("/api/tasks/from-action",json={"action_id":task["source"]["id"]}).status_code == 404
    assert other.get("/api/tasks").json()["tasks"] == []
    assert c.post("/api/tasks",json={"outcome":"Fake", "creation_key":"fake-source-key", "source":task["source"]}).status_code == 422
    assert c.post("/api/tasks",json={"outcome":"Fake", "creation_key":"source:action:anything"}).status_code == 422
    assert c.post("/api/tasks/from-report",json={"fields":{"owner":{"value":"other"}}}).status_code == 422
    reference = TaskFocusContext(task_id=task["id"], revision=1, selected_at=datetime.now(timezone.utc))
    with pytest.raises(tasks.HTTPException) as error:
        tasks.resolve_context(store,other_owner,reference)
    assert error.value.status_code == 404
    resolved = tasks.resolve_context(store,owner,reference)
    assert resolved["outcome"] == task["outcome"] and resolved["linked_item"]["status"] == "BLOCKED"
    command(c,task,"edit",changes={"outcome":"New tracking title"})
    with pytest.raises(tasks.HTTPException) as error:
        tasks.resolve_context(store,owner,reference)
    assert error.value.status_code == 409
    expired = reference.model_copy(update={"selected_at":datetime.now(timezone.utc)-timedelta(hours=1)})
    assert tasks.resolve_context(store,owner,expired) is None


def test_missing_source_does_not_hide_task_or_its_history(client):
    c, store, *_ = client
    task = c.post("/api/tasks/from-report",json={"fields":report_fields()}).json()["task"]
    store.db.execute("DELETE FROM actions WHERE id=?",(task["source"]["id"],))
    store.db.commit()
    detail = c.get(f'/api/tasks/{task["id"]}').json()
    assert detail["task"]["id"] == task["id"] and detail["linked_item"] is None and detail["events"]


def test_reviewed_task_change_is_read_only_until_revision_bound_apply(client):
    c, *_ = client
    task = c.post("/api/tasks/from-report",json={"fields":report_fields()}).json()["task"]
    changes = {"due_at":"2026-10-24T09:00:00+04:00", "next_step":"Check the official reporting options"}
    proposal = c.post(f'/api/tasks/{task["id"]}/prepare-change',json={"expected_revision":1,"changes":changes}).json()
    assert proposal["before"] == {"due_at":None,"next_step":""}
    assert proposal["after"]["due_at"] == "2026-10-24T05:00:00+00:00" and proposal["proposal_hash"]
    detail = c.get(f'/api/tasks/{task["id"]}').json()
    assert detail["task"]["revision"] == 1 and len(detail["events"]) == 1
    assert detail["linked_item"]["status"] == "BLOCKED"
    applied = command(c,task,"edit",changes=proposal["changes"],command_key="apply-reviewed-change").json()["task"]
    assert applied["revision"] == 2 and applied["due_at"] == proposal["after"]["due_at"]
    assert command(c,task,"edit",changes=proposal["changes"],command_key="apply-reviewed-change").json()["task"] == applied
    assert c.post(f'/api/tasks/{task["id"]}/prepare-change',json={"expected_revision":1,"changes":changes}).status_code == 409
    assert command(c,task,"edit",changes=changes).status_code == 409
    latest = c.get(f'/api/tasks/{task["id"]}').json()
    assert latest["linked_item"] == detail["linked_item"] and len(latest["events"]) == 2


def test_change_review_rejects_cross_owner_terminal_and_execution_fields(client):
    c, *_ = client
    task = create(c)
    other = TestClient(c.app)
    other.get("/api/session")
    path = f'/api/tasks/{task["id"]}/prepare-change'
    body = {"expected_revision":1,"changes":{"due_at":"2026-10-24T09:00:00+04:00"}}
    assert other.post(path,json=body).status_code == 404
    for changes in ({"status":"COMPLETED"},{"source":{"id":"other"}},{"due_at":"2026-10-24T09:00:00"},{"outcome":""}):
        assert c.post(path,json={"expected_revision":1,"changes":changes}).status_code == 422
    cancelled = command(c,task,"cancel").json()["task"]
    assert c.post(path,json={"expected_revision":cancelled["revision"],"changes":{"details":"Stale proposal"}}).status_code == 409


def tracked_order(c, **fields):
    action = c.post("/api/actions/prepare",json={"capability_id":"order.request",
        "fields":{"area":{"value":"JLT"}, **{k:{"value":v} for k,v in fields.items()}},
        "order":{"provider_id":"marinaexpress","items":[{"name":"Shirt wash + press","qty":1}]}}).json()
    task = c.post("/api/tasks/from-action",json={"action_id":action["id"]}).json()["task"]
    return action, task


def test_needs_you_lists_only_real_decisions_on_tracked_sources(client):
    c, store, owner, _ = client
    create(c, outcome="A manual note is never a decision")
    c.post("/api/actions/prepare",json={"capability_id":"order.request", "fields":{"area":{"value":"JLT"}},
        "order":{"provider_id":"marinaexpress","items":[{"name":"Shirt wash + press","qty":1}]}})  # opened, never kept
    action, task = tracked_order(c)
    today = c.get("/api/today").json()
    assert today["counts"]["needs_you"] == 1
    [row] = today["needs_you"]["tasks"]
    decision = row["decision"]
    assert row["id"] == task["id"] and decision["kind"] == "approve"
    assert decision["action_id"] == action["id"] and decision["revision"] == action["revision"]
    assert decision["snapshot_hash"] == action["snapshot_hash"] and decision["amount_aed"] == action["fixed_total_aed"]
    assert today["counts"]["on_list"] == 1 and task["id"] not in [t["id"] for t in today["on_list"]["tasks"]]
    assert store.db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0
    other = TestClient(c.app); other.get("/api/session")
    assert other.get("/api/today").json()["needs_you"]["tasks"] == []
    command(c, task, "pause")
    assert c.get("/api/today").json()["counts"]["needs_you"] == 0


def test_decision_follows_authoritative_source_state(client):
    c, store, owner, _ = client
    action, task = tracked_order(c, deadline="Tomorrow 09:00")
    action = store.get(owner, action["id"])
    action["status"], action["ready_at"] = "ACCEPTED", "Tomorrow 10:00"; store.put(owner, action)
    [row] = c.get("/api/today").json()["needs_you"]["tasks"]
    assert row["decision"]["kind"] == "deadline" and row["decision"]["earlier_target"] == "Tomorrow 08:30"
    assert c.get("/api/today").json()["running"]["tasks"] == []  # shown once, as the decision
    assert c.post(f'/api/actions/{action["id"]}/request-earlier', json={"target":"Tomorrow 08:30"}).status_code == 200
    today = c.get("/api/today").json()
    assert today["needs_you"]["tasks"] == [] and today["running"]["tasks"][0]["id"] == task["id"]
    assert today["counts"]["running"] == 1 and today["counts"]["needs_you"] == 0
    action = store.get(owner, action["id"]); action["status"] = "UNKNOWN_STATUS"; store.put(owner, action)
    assert c.get("/api/today").json()["needs_you"]["tasks"][0]["decision"]["kind"] == "check"
    action["status"] = "COMPLETED"; store.put(owner, action)
    assert c.get("/api/today").json()["counts"]["needs_you"] == 0
    assert c.get(f'/api/tasks/{task["id"]}').json()["task"]["status"] == "WAITING_USER"


def test_unsendable_report_stays_quietly_on_the_list(client):
    c, store, *_ = client
    task = c.post("/api/tasks/from-report",json={"fields":report_fields()}).json()["task"]
    today = c.get("/api/today").json()
    assert today["needs_you"]["tasks"] == [] and today["counts"]["needs_you"] == 0
    assert [t["id"] for t in today["on_list"]["tasks"]] == [task["id"]] and today["counts"]["on_list"] == 1
    assert store.db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0


def test_stale_decision_binding_cannot_approve_a_changed_draft(client):
    c, store, *_ = client
    action, task = tracked_order(c)
    old = c.get("/api/today").json()["needs_you"]["tasks"][0]["decision"]
    changed = c.post("/api/actions/prepare",json={"capability_id":"order.request","draft_id":action["id"],
        "fields":{"area":{"value":"Deira"}},"order":{"provider_id":"marinaexpress","items":[{"name":"Shirt wash + press","qty":2}]}}).json()
    fresh = c.get("/api/today").json()["needs_you"]["tasks"][0]["decision"]
    assert fresh["revision"] == changed["revision"] != old["revision"]
    stale = c.post(f'/api/actions/{action["id"]}/approve', headers={"Idempotency-Key":uuid4().hex},
                   json={"snapshot_hash":old["snapshot_hash"],"revision":old["revision"]})
    assert stale.status_code == 409
    assert store.db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0


def test_staged_recovery_replies_are_scripted_ordered_and_never_recover(client):
    c, store, *_ = client
    task = c.post("/api/tasks/from-report",json={"fields":report_fields()}).json()["task"]
    early = command(c, task, "collect")
    assert early.status_code == 409  # no choice before the staged reply
    for n in range(2):
        response = command(c, task, "staged_next"); assert response.status_code == 200, response.text
        task = response.json()["task"]
    assert command(c, task, "staged_next").status_code == 409
    events = c.get(f'/api/tasks/{task["id"]}').json()["events"]
    staged = [e for e in events if e["kind"] == "staged_reply"]
    assert len(staged) == 2 and all(e["actor"] == "staged" and e["provenance"] == "demo_fixture" for e in staged)
    assert "Blue backpack" in staged[1]["text"] and "Staged" in staged[1]["text"]
    task = command(c, task, "collect").json()["task"]
    assert task["status"] == "WAITING_USER" and task["result"] is None and "Collect it in person" in task["next_step"]
    assert command(c, task, "collect").status_code == 409
    linked = c.get(f'/api/tasks/{task["id"]}').json()["linked_item"]
    assert linked["status"] == "BLOCKED" and linked["evidence"] is None
    assert store.db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0


def test_staged_replies_reject_orders_manual_tasks_and_other_owners(client):
    c, *_ = client
    manual = create(c)
    assert command(c, manual, "staged_next").status_code == 409
    _, order_task = tracked_order(c)
    assert command(c, order_task, "staged_next").status_code == 409
    task = c.post("/api/tasks/from-report",json={"fields":report_fields()}).json()["task"]
    other = TestClient(c.app); other.get("/api/session")
    assert command(other, task, "staged_next").status_code == 404
    assert command(c, task, "staged_next", changes={"outcome":"x"}).status_code == 422


def test_check_back_is_consented_deduped_and_withdrawn_when_obsolete(client, monkeypatch):
    from app import proactive
    c, store, owner, _ = client
    c.app.include_router(proactive.router)
    task = create(c, outcome="Call the landlord about the deposit")
    at = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)  # 10:00 Dubai
    body = {"kind":"check_back", "expected_revision":task["revision"], "command_key":uuid4().hex, "at":at.isoformat()}
    task = c.post(f'/api/tasks/{task["id"]}/commands', json=body).json()["task"]
    assert c.post(f'/api/tasks/{task["id"]}/commands', json=body).json()["replayed"]
    pending = lambda: store.db.execute("SELECT dedupe_key FROM outbox WHERE owner=? AND delivered_at IS NULL", (owner,)).fetchall()
    assert len(pending()) == 1
    assert [t["id"] for t in c.get("/api/today").json()["scheduled"]["tasks"]] == [task["id"]]
    assert c.get("/api/messages").json()["messages"] == []  # not due yet
    later = at + timedelta(days=1)
    task = command(c, task, "check_back", at=later.isoformat()).json()["task"]
    assert [k for (k,) in pending()] == [f'checkback:{task["id"]}:{later.isoformat()}']  # rescheduled, old one withdrawn
    monkeypatch.setattr(proactive, "clock", lambda: later.astimezone(proactive.DUBAI) + timedelta(minutes=1))
    [message] = c.get("/api/messages").json()["messages"]
    assert message["task_id"] == task["id"] and message["kind"] == "task_checkback" and "Call the landlord" in message["text"]
    other = TestClient(c.app); other.get("/api/session")
    assert other.get("/api/messages").json()["messages"] == []
    assert command(other, task, "check_back", at=later.isoformat()).status_code == 404


def test_pause_cancel_and_quiet_hours_govern_check_backs(client):
    from app import proactive
    c, store, owner, _ = client
    task = create(c)
    night = (datetime.now(timezone.utc) + timedelta(days=2)).replace(hour=20, minute=30, second=0, microsecond=0)  # 00:30 Dubai
    task = command(c, task, "check_back", at=night.isoformat()).json()["task"]
    [(available,)] = store.db.execute("SELECT available_at FROM outbox WHERE owner=?", (owner,)).fetchall()
    assert datetime.fromisoformat(available).astimezone(proactive.DUBAI).hour == 7
    task = command(c, task, "pause").json()["task"]
    assert task["check_back_at"] is None
    assert store.db.execute("SELECT COUNT(*) FROM outbox WHERE delivered_at IS NULL").fetchone()[0] == 0
    assert command(c, task, "check_back", at=night.isoformat()).status_code == 409  # paused
    task = command(c, task, "resume").json()["task"]
    assert command(c, task, "check_back", at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()).status_code == 422
    task = command(c, task, "check_back", at=night.isoformat()).json()["task"]
    command(c, task, "cancel")
    assert store.db.execute("SELECT COUNT(*) FROM outbox WHERE delivered_at IS NULL").fetchone()[0] == 0
    assert c.post(f'/api/tasks/{task["id"]}/commands', json={"kind":"pause","expected_revision":1,"command_key":uuid4().hex,"at":None}).status_code == 422
