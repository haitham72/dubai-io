"""Manual responsibilities, independent of chat checkpoints and external Actions.

This first slice has no worker, connector or external execution path. Saving a
task means waiting for a user update. Only an explicit user report completes it;
that report is never presented as provider evidence.
"""
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import json
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from . import proactive
from .actions import COOKIE, InputValue, PrepareIn, annotate, engine, fingerprint

router = APIRouter(tags=["tasks"])
clock = lambda: datetime.now(timezone.utc)
ACTIVE = {"WAITING_USER", "PAUSED"}
# TAXI-02 staged replies (founder chose staged first). Host-owned script, never
# client text; every reply is a demo fixture and nothing here means recovered.
STAGED_REPLIES = (
    ("RTA lost & found", "Your report details were received for checking. This is a staged reply, not a real RTA response."),
    ("Taxi company", "An item matching “{item}” was found in the back seat and is held at the company’s lost property desk. Staged reply."),
)
COLLECT_STEP = "Collect it in person from the lost property desk named in the reply. Confirm the place with RTA first (staged location), then mark this task done."
DDL = (
    """CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, creation_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
        revision INTEGER NOT NULL, status TEXT NOT NULL, cancelled_at TEXT, updated_at TEXT NOT NULL,
        data TEXT NOT NULL, UNIQUE(owner,creation_key), UNIQUE(id,owner))""",
    "CREATE INDEX IF NOT EXISTS tasks_owner_updated ON tasks(owner,status,updated_at,id)",
    """CREATE TABLE IF NOT EXISTS task_events (
        task_id TEXT NOT NULL, owner TEXT NOT NULL, seq INTEGER NOT NULL, command_key TEXT NOT NULL,
        payload_hash TEXT NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL, data TEXT NOT NULL,
        PRIMARY KEY(task_id,seq), UNIQUE(owner,task_id,command_key),
        FOREIGN KEY(task_id,owner) REFERENCES tasks(id,owner))""",
)


class TaskFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: str = Field(min_length=1, max_length=240)
    details: str = Field(default="", max_length=1600)
    next_step: str = Field(default="", max_length=300)
    due_at: AwareDatetime | None = None

    @field_validator("outcome", "next_step", "details")
    @classmethod
    def trim(cls, value, info):
        value = value.strip()
        if info.field_name == "outcome" and not value:
            raise ValueError("Enter a value")
        return value


class CreateTask(TaskFields):
    creation_key: str = Field(min_length=8, max_length=100)

    @field_validator("creation_key")
    @classmethod
    def reserved_source_keys(cls, value):
        if value.startswith("source:"):
            raise ValueError("This save key is reserved for linked items")
        return value


class TrackAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_id: str = Field(min_length=1, max_length=64)


class TrackReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fields: dict[str, InputValue] = Field(min_length=1, max_length=10)


class TaskChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: str | None = Field(default=None, min_length=1, max_length=240)
    details: str | None = Field(default=None, max_length=1600)
    next_step: str | None = Field(default=None, max_length=300)
    due_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("Choose a field to edit")
        for name in self.model_fields_set - {"due_at"}:
            value = getattr(self, name)
            if value is None or (name == "outcome" and not value.strip()):
                raise ValueError("Text fields cannot be empty")
            setattr(self, name, value.strip())
        return self


class TaskCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["edit", "pause", "resume", "cancel", "complete", "staged_next", "collect", "check_back"]
    expected_revision: int = Field(ge=1)
    command_key: str = Field(min_length=8, max_length=100)
    changes: TaskChanges | None = None
    result: str | None = Field(default=None, max_length=1000)
    at: AwareDatetime | None = None  # check_back only; null clears it

    @model_validator(mode="after")
    def validate_command(self):
        if (self.kind == "check_back") != ("at" in self.model_fields_set):
            raise ValueError("Only a check-back accepts a time")
        if (self.kind == "edit") != (self.changes is not None):
            raise ValueError("Only an edit accepts changes")
        if self.kind == "complete":
            if not self.result or not self.result.strip():
                raise ValueError("Describe the result you are reporting")
            self.result = self.result.strip()
        elif self.result is not None:
            raise ValueError("Only completion accepts a result")
        return self


class ChangeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    changes: TaskChanges


def values(body, **options):
    data = body.model_dump(mode="json", **options)
    # Persist one sortable, time-zone-aware representation; UI uses Dubai time.
    if data.get("due_at"):
        data["due_at"] = datetime.fromisoformat(data["due_at"].replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    return data


class Tasks:
    def __init__(self, store):
        self.store = store
        with store.lock:
            if not getattr(store, "_tasks_ready", False):
                try:
                    for statement in DDL:
                        store.db.execute(statement)
                    if store.db.dialect == "postgres":
                        for table in ("tasks", "task_events"):
                            store.db.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
                    store.db.commit()
                    proactive.setup(store)  # check-backs share the consented outbox
                    store._tasks_ready = True
                except Exception:
                    store.db.conn.rollback()
                    raise

    @contextmanager
    def transaction(self, owner, *, write=False):
        """One atomic command/event; no transactions span network/model calls.

        The process lock protects the shared handle. DB locks also serialize
        competing handles/workers: SQLite's writer lock or a PG owner lock.
        Revision predicates remain the final write guard.
        """
        if write:
            with self.store.transaction(owner):
                yield
            return
        with self.store.lock:
            try:
                yield
                self.store.commit()
            except Exception:
                if not self.store._write_depth:
                    self.store.db.conn.rollback()
                raise

    def get(self, owner, task_id):
        row = self.store.db.execute("SELECT data FROM tasks WHERE id=? AND owner=?", (task_id, owner)).fetchone()
        if not row:
            raise HTTPException(404, "Task not found")
        return json.loads(row[0])

    def event(self, owner, task, key, payload_hash, kind, data):
        self.store.db.execute("INSERT INTO task_events VALUES (?,?,?,?,?,?,?,?)",
                              (task["id"], owner, task["revision"], key, payload_hash, kind,
                               task["updated_at"], json.dumps(data)))

    def create(self, owner, body):
        data = values(body, exclude={"creation_key"})
        digest = fingerprint(data)
        with self.transaction(owner, write=True):
            row = self.store.db.execute("SELECT id,payload_hash FROM tasks WHERE owner=? AND creation_key=?",
                                        (owner, body.creation_key)).fetchone()
            if row:
                if row[1] != digest:
                    raise HTTPException(409, "This save key already belongs to different task details")
                return {"task": self.get(owner, row[0]), "replayed": True}
            return self.insert(owner, body.creation_key, digest, data)

    def insert(self, owner, creation_key, digest, data):
        """Called only within the owner write transaction; reference capture never executes."""
        at = clock().isoformat()
        task = {"id": uuid4().hex, **data, "revision": 1, "status": "WAITING_USER",
                "mode": "manual", "created_at": at, "updated_at": at, "cancelled_at": None,
                "result": None, "provenance": "user_supplied", "as_of": at}
        self.store.db.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)",
                              (task["id"], owner, creation_key, digest, 1, task["status"], None, at, json.dumps(task)))
        self.event(owner, task, "create:" + creation_key, digest, "created", {"actor": "user"})
        return {"task": task, "replayed": False}

    def track_action(self, owner, action_id):
        with self.transaction(owner, write=True):
            # Read, never reconcile or dispatch, the canonical owner-bound item.
            action = self.store.get(owner, action_id)
            creation_key = "source:action:" + action_id
            row = self.store.db.execute("SELECT id FROM tasks WHERE owner=? AND creation_key=?", (owner, creation_key)).fetchone()
            if row:
                return {"task": self.get(owner, row[0]), "replayed": True}
            recovery = action["capability_id"] == "recovery.rta"
            title = ("Lost item: " + action["fields"].get("description", {}).get("value", "my report")) if recovery else (
                "Follow up with " + ((action.get("order") or {}).get("provider") or action["recipient"]))
            data = values(TaskFields(outcome=title[:240]))
            data["source"] = {"kind": "action", "id": action_id}
            return self.insert(owner, creation_key, fingerprint(data), data)

    def linked_item(self, owner, task):
        source = task.get("source")
        if not source or source["kind"] != "action":
            return None
        try:
            return annotate(self.store.get(owner, source["id"]))
        except HTTPException as error:
            if error.status_code != 404:
                raise
            return None  # Tracking/history remain readable if its source disappears.

    def command(self, owner, task_id, body, actor="user"):
        payload = values(body, exclude={"command_key"})
        digest = fingerprint(payload)
        with self.transaction(owner, write=True):
            task = self.get(owner, task_id)
            replay = self.store.db.execute("SELECT payload_hash FROM task_events WHERE owner=? AND task_id=? AND command_key=?",
                                           (owner, task_id, body.command_key)).fetchone()
            if replay:
                if replay[0] != digest:
                    raise HTTPException(409, "This command key already belongs to a different change")
                # Return current state, not an old receipt that could revive a cancelled task.
                return {"task": task, "replayed": True}
            if task["revision"] != body.expected_revision:
                raise HTTPException(409, "This task changed. Reload it before applying your edit.")
            if task["status"] not in ACTIVE:
                raise HTTPException(409, "A completed or cancelled task cannot be changed")
            kind = body.kind
            event_data = {"actor": actor}
            if kind == "edit":
                changes = values(body.changes, exclude_unset=True)
                task.update(changes)
                event_data["fields"] = sorted(changes)
            elif kind == "pause":
                if task["status"] == "PAUSED":
                    raise HTTPException(409, "This task is already paused")
                task["status"] = "PAUSED"
            elif kind == "resume":
                if task["status"] != "PAUSED":
                    raise HTTPException(409, "Only a paused task can be resumed")
                task["status"] = "WAITING_USER"
            elif kind == "cancel":
                task["status"] = "CANCELLED"
                task["cancelled_at"] = clock().isoformat()
            elif kind in ("staged_next", "collect"):
                item = self.linked_item(owner, task)
                if not item or item["capability_id"] != "recovery.rta" or task["status"] != "WAITING_USER":
                    raise HTTPException(409, "Staged replies apply only to an active lost-item report")
                shown = self.store.db.execute("SELECT kind FROM task_events WHERE owner=? AND task_id=? AND kind IN ('staged_reply','collection_chosen')",
                                              (owner, task_id)).fetchall()
                replies, chosen = sum(r[0] == "staged_reply" for r in shown), any(r[0] == "collection_chosen" for r in shown)
                if kind == "staged_next":
                    if replies >= len(STAGED_REPLIES):
                        raise HTTPException(409, "There are no more staged replies")
                    sender, text = STAGED_REPLIES[replies]
                    event_data = {"actor": "staged", "provenance": "demo_fixture", "sender": sender,
                                  "text": text.format(item=(item["fields"].get("description") or {}).get("value", "your item")[:80])}
                    if replies + 1 == len(STAGED_REPLIES):
                        task["next_step"] = "Choose how to get it back."
                else:
                    if replies < len(STAGED_REPLIES) or chosen:
                        raise HTTPException(409, "Collection can be chosen once, after the staged reply")
                    task["next_step"] = COLLECT_STEP
                    event_data["choice"] = "collect"
            elif kind == "check_back":
                if task["status"] != "WAITING_USER":
                    raise HTTPException(409, "Resume the task before scheduling a check-back")
                if body.at is not None and not clock() + timedelta(minutes=1) <= body.at <= clock() + timedelta(days=60):
                    raise HTTPException(422, "Choose a check-back time between a minute and 60 days from now")
                task["check_back_at"] = body.at.astimezone(timezone.utc).isoformat() if body.at else None
                event_data["at"] = task["check_back_at"]
            elif kind == "complete":
                task["status"] = "COMPLETED"
                task["result"] = {"text": body.result, "provenance": "user_supplied", "as_of": clock().isoformat()}
            task["revision"] += 1
            task["updated_at"] = task["as_of"] = clock().isoformat()
            changed = self.store.db.execute("""UPDATE tasks SET revision=?,status=?,cancelled_at=?,updated_at=?,data=?
                WHERE id=? AND owner=? AND revision=? AND cancelled_at IS NULL AND status IN ('WAITING_USER','PAUSED')""",
                (task["revision"], task["status"], task["cancelled_at"], task["updated_at"], json.dumps(task),
                 task_id, owner, body.expected_revision))
            if changed.rowcount != 1:
                raise HTTPException(409, "This task changed. Reload it before applying your edit.")
            self.event(owner, task, body.command_key, digest, {"edit": "edited", "pause": "paused", "resume": "resumed",
                       "cancel": "cancelled", "complete": "completed", "staged_next": "staged_reply",
                       "collect": "collection_chosen", "check_back": "check_back_set" if body.at else "check_back_cleared"}[kind], event_data)
            if kind in ("check_back", "pause", "cancel", "complete"):
                sync_check_back(self.store, owner, task, kind)
            return {"task": task, "replayed": False}

    def activity(self, owner, task_id, before=None):
        sql = "SELECT seq,kind,at,data FROM task_events WHERE owner=? AND task_id=?"
        params = [owner, task_id]
        if before is not None:
            sql += " AND seq<?"
            params.append(before)
        rows = self.store.db.execute(sql + " ORDER BY seq DESC LIMIT 51", tuple(params)).fetchall()
        return {"events": [{"seq": r[0], "kind": r[1], "at": r[2], **json.loads(r[3])} for r in reversed(rows[:50])],
                "before_seq": rows[49][0] if len(rows) > 50 else None}


def owned(request, response):
    response.headers["Cache-Control"] = "private, no-store"
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))
    return Tasks(store), owner


def present(task, at=None):
    """Time-sensitive display flags are computed, never saved as user facts."""
    due_state = None
    if task.get("due_at") and task["status"] == "WAITING_USER":
        due = datetime.fromisoformat(task["due_at"])
        current = at or clock()
        due_state = "overdue" if due < current else "due_soon" if due <= current + timedelta(days=1) else None
    return {**task, "due_state": due_state}


def presented_result(result):
    return {**result, "task": present(result["task"])}


def sync_check_back(store, owner, task, kind):
    """Gate B: one outbox message per scheduled check-back, written in the task's
    transaction. Rescheduling, pausing, cancelling or completing withdraws any
    undelivered one, so an obsolete check-back never arrives."""
    store.db.execute("DELETE FROM outbox WHERE owner=? AND delivered_at IS NULL AND dedupe_key LIKE ?",
                     (owner, f"checkback:{task['id']}:%"))
    if kind != "check_back":
        task["check_back_at"] = None
        store.db.execute("UPDATE tasks SET data=? WHERE id=? AND owner=?", (json.dumps(task), task["id"], owner))
        return
    if task["check_back_at"]:
        at = datetime.fromisoformat(task["check_back_at"]).astimezone(proactive.DUBAI)
        store.db.execute("INSERT OR IGNORE INTO consent VALUES (?,?)", (owner, clock().isoformat()))  # the tap is the consent
        proactive.enqueue(store, owner, f"checkback:{task['id']}:{task['check_back_at']}", "task_checkback",
                          f"Check-back you asked for: {task['outcome'][:200]}. Open the task to add an update.",
                          "user_reminder", proactive.after_quiet(at))


def earlier_than(deadline):
    """'Tomorrow 09:00' -> 'Tomorrow 08:30': 30 minutes of slack, never across midnight."""
    day, hm = deadline.split()
    minutes = int(hm[:2]) * 60 + int(hm[3:]) - 30
    return f"{day} {minutes // 60:02d}:{minutes % 60:02d}" if minutes >= 0 else None


def decision_for(action):
    """The crucial choice a tracked source is stopped on, or None.

    Only points where going on could spend money, duplicate a send or miss the user's
    deadline. Prepared-but-unsendable items stay quietly on the list. Derived from
    canonical Action state on every read; approval binds the revision/snapshot shown."""
    status, order = action["status"], action.get("order") or {}
    who = order.get("provider") or action["recipient"]
    base = {"action_id": action["id"], "revision": action["revision"], "source_status": status}
    if status == "AWAITING_APPROVAL" and action.get("execution_available"):
        return {**base, "kind": "approve", "title": "Approve and send" + (f" · AED {Decimal(action['fixed_total_aed']):.2f}" if action.get("fixed_total_aed") is not None else ""),
                "detail": "Fixed published price. Nothing is sent until you approve.",
                "amount_aed": action.get("fixed_total_aed"), "snapshot_hash": action["snapshot_hash"]}
    if status == "UNKNOWN_STATUS":
        return {**base, "kind": "check", "title": f"Check with {who} before resending",
                "detail": "The send outcome is not known. Resending could duplicate the order."}
    check = action.get("deadline_check")
    if status == "ACCEPTED" and check and not check["meets"] and not action.get("earlier_request"):
        return {**base, "kind": "deadline", "title": f"Ready {check['ready_at']} misses your {check['deadline']} deadline",
                "detail": "Confirmed by the shop. You can ask for an earlier time at the same price.",
                "earlier_target": earlier_than(check["deadline"])}
    return None


def resolve_context(store, owner, reference):
    """Resolve IDs, ownership and revision before supplying transient model context."""
    if not 0 <= (clock() - reference.selected_at).total_seconds() <= 1800:
        return None
    tasks = Tasks(store)
    with tasks.transaction(owner):
        task = tasks.get(owner, reference.task_id)
        if task["revision"] != reference.revision:
            raise HTTPException(409, "This task changed. Reopen its latest details before discussing it.")
        item = tasks.linked_item(owner, task)
        return {"task_id": task["id"], "revision": task["revision"], "outcome": task["outcome"],
                "next_step": task["next_step"], "details": task["details"], "due_at": task["due_at"],
                "status": task["status"], "result": task["result"], "mode": task["mode"],
                "linked_item": {"id": item["id"], "status": item["status"], "missing": item["missing"],
                    "evidence": item.get("evidence"), "fields": {k: v["value"][:300] for k, v in item["fields"].items()}} if item else None}


@router.post("/api/tasks")
def create_task(body: CreateTask, request: Request, response: Response):
    tasks, owner = owned(request, response)
    return presented_result(tasks.create(owner, body))


@router.get("/api/tasks")
def list_tasks(request: Request, response: Response, offset: int = Query(default=0, ge=0), limit: int = Query(default=30, ge=1, le=50)):
    tasks, owner = owned(request, response)
    with tasks.transaction(owner):
        rows = tasks.store.db.execute("SELECT data FROM tasks WHERE owner=? ORDER BY updated_at DESC,id DESC LIMIT ? OFFSET ?",
                                       (owner, limit + 1, offset)).fetchall()
        return {"tasks": [present(json.loads(r[0])) for r in rows[:limit]], "next_offset": offset + limit if len(rows) > limit else None}


@router.post("/api/tasks/from-action")
def track_action(body: TrackAction, request: Request, response: Response):
    tasks, owner = owned(request, response)
    return presented_result(tasks.track_action(owner, body.action_id))


@router.post("/api/tasks/from-report")
def track_report(body: TrackReport, request: Request, response: Response):
    tasks, owner = owned(request, response)
    # Saving the prepared report has a stable payload key across retries/reloads.
    # The fixed capability has no adapter; this endpoint never calls approve.
    action = engine().prepare(owner, PrepareIn(capability_id="recovery.rta", fields=body.fields,
        preparation_key="report-task:" + fingerprint({k: v.model_dump() for k, v in body.fields.items()})))
    result = tasks.track_action(owner, action["id"])
    with tasks.transaction(owner):
        auto = proactive.assist(tasks.store, owner)["mode"] == "auto"
    if auto and not result["replayed"]:
        # Auto follow-ups: a kept report gets a check-back two days later at 10:00 Dubai.
        day = (clock().astimezone(proactive.DUBAI) + timedelta(days=2)).date()
        at = datetime.combine(day, datetime.min.time().replace(hour=10), proactive.DUBAI)
        result = tasks.command(owner, result["task"]["id"], TaskCommand(kind="check_back", expected_revision=result["task"]["revision"],
                               command_key="auto-check-back:" + result["task"]["id"], at=at), actor="auto")
    return presented_result(result)


@router.get("/api/today")
def today(request: Request, response: Response):
    tasks, owner = owned(request, response)
    with tasks.transaction(owner):
        at = clock()
        due = "json_extract(data, '$.due_at')" if tasks.store.db.dialect == "sqlite" else "(data::jsonb ->> 'due_at')"
        priority = f"CASE WHEN {due} IS NULL THEN 1 ELSE 0 END, {due}, updated_at DESC,id DESC"
        groups = {"needs_you": {"tasks": [], "has_more": False}, "running": {"tasks": [], "has_more": False}}
        for key, status in (("on_list", "WAITING_USER"), ("paused", "PAUSED"), ("completed", "COMPLETED")):
            order = priority if status == "WAITING_USER" else "updated_at DESC,id DESC"
            rows = tasks.store.db.execute(f"SELECT data FROM tasks WHERE owner=? AND status=? ORDER BY {order} LIMIT 4",
                                           (owner, status)).fetchall()
            groups[key] = {"tasks": [present(json.loads(r[0]), at) for r in rows[:3]], "has_more": len(rows) > 3}
        totals = dict(tasks.store.db.execute("SELECT status,COUNT(*) FROM tasks WHERE owner=? GROUP BY status", (owner,)).fetchall())
        groups["paused"]["count"] = totals.get("PAUSED", 0)
        extract = (lambda col, path: f"json_extract({col}, '$.{path}')") if tasks.store.db.dialect == "sqlite" else (lambda col, path: f"({col}::jsonb ->> '{path}')")
        # Source-backed work only. A saved manual note never becomes a running
        # agent. Reads do not reconcile, approve or dispatch an Action.
        source_id = "json_extract(t.data, '$.source.id')" if tasks.store.db.dialect == "sqlite" else "(t.data::jsonb -> 'source' ->> 'id')"
        source_status = extract("a.data", "status")
        current_rows = tasks.store.db.execute(f"""SELECT t.data,a.data FROM tasks t
            JOIN actions a ON a.id={source_id} AND a.owner=t.owner
            WHERE t.owner=? AND t.status='WAITING_USER'
              AND {source_status} IN ('AWAITING_APPROVAL','DISPATCHING','SUBMITTED','ACCEPTED','READY','UNKNOWN_STATUS')
            ORDER BY CASE WHEN {source_status} IN ('DISPATCHING','SUBMITTED','ACCEPTED','READY') THEN 0 ELSE 1 END,
              t.updated_at DESC,t.id DESC LIMIT 6""", (owner,)).fetchall()
        current = [{"task": present(json.loads(t), at), "source": annotate(json.loads(a))} for t, a in current_rows[:5]]
        # Decisions come only from tracked, active sources; a draft merely opened is not one.
        decisions = []
        for t, a in tasks.store.db.execute(f"""SELECT t.data,a.data FROM tasks t
                JOIN actions a ON a.id={source_id} AND a.owner=t.owner
                WHERE t.owner=? AND t.status='WAITING_USER'
                  AND {source_status} IN ('AWAITING_APPROVAL','UNKNOWN_STATUS','ACCEPTED')
                ORDER BY t.updated_at DESC,t.id DESC""", (owner,)).fetchall():
            decision = decision_for(annotate(json.loads(a)))
            if decision:
                decisions.append({**present(json.loads(t), at), "source_status": decision["source_status"], "decision": decision})
        deciding = {row["id"] for row in decisions}
        groups["needs_you"] = {"tasks": decisions[:3], "has_more": len(decisions) > 3}
        check = extract("data", "check_back_at")
        scheduled = [present(json.loads(r[0]), at) for r in tasks.store.db.execute(
            f"SELECT data FROM tasks WHERE owner=? AND status='WAITING_USER' AND {check} IS NOT NULL ORDER BY {check} LIMIT 4", (owner,)).fetchall()]
        groups["scheduled"] = {"tasks": scheduled[:3], "has_more": len(scheduled) > 3}
        if deciding:  # each task shows in one lane only
            rows = [r for r in tasks.store.db.execute(f"SELECT data FROM tasks WHERE owner=? AND status='WAITING_USER' ORDER BY {priority} LIMIT ?",
                                                      (owner, 4 + len(deciding))).fetchall() if json.loads(r[0])["id"] not in deciding]
            groups["on_list"] = {"tasks": [present(json.loads(r[0]), at) for r in rows[:3]], "has_more": len(rows) > 3}
        groups["running"] = {"tasks": [{**item["task"], "source_status": item["source"]["status"]} for item in current
            if item["source"]["status"] in {"DISPATCHING", "SUBMITTED", "ACCEPTED", "READY"} and item["task"]["id"] not in deciding],
            "has_more": len(current_rows) > 5}
        return {**groups, "counts": {"needs_you": len(decisions), "running": len(groups["running"]["tasks"]), "on_list": totals.get("WAITING_USER", 0) - len(decisions), "paused": totals.get("PAUSED", 0)},
                "current_work": current, "mode": "manual", "monitoring_active": False, "as_of": at.isoformat()}


@router.get("/api/tasks/{task_id}")
def task_detail(task_id: str, request: Request, response: Response):
    tasks, owner = owned(request, response)
    with tasks.transaction(owner):
        task = tasks.get(owner, task_id)
        return {"task": present(task), "linked_item": tasks.linked_item(owner, task), **tasks.activity(owner, task_id)}


@router.get("/api/tasks/{task_id}/activity")
def task_activity(task_id: str, request: Request, response: Response, before_seq: int = Query(ge=1)):
    tasks, owner = owned(request, response)
    with tasks.transaction(owner):
        tasks.get(owner, task_id)
        return tasks.activity(owner, task_id, before_seq)


@router.post("/api/tasks/{task_id}/commands")
def task_command(task_id: str, body: TaskCommand, request: Request, response: Response):
    tasks, owner = owned(request, response)
    return presented_result(tasks.command(owner, task_id, body))


@router.post("/api/tasks/{task_id}/prepare-change")
def prepare_change(task_id: str, body: ChangeProposal, request: Request, response: Response):
    tasks, owner = owned(request, response)
    with tasks.transaction(owner):
        task = tasks.get(owner, task_id)
        if task["revision"] != body.expected_revision or task["status"] not in ACTIVE:
            raise HTTPException(409, "This task changed. Reopen its latest details before reviewing this proposal.")
        changes = values(body.changes, exclude_unset=True)
        return {"task_id": task_id, "expected_revision": task["revision"], "changes": changes,
                "before": {field: task[field] for field in changes}, "after": changes,
                "proposal_hash": fingerprint({"task_id": task_id, "revision": task["revision"], "changes": changes})}
