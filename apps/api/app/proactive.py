"""Deterministic proactive messages (CLAUDE.md rule 8, ARCHITECTURE.md §7).

Sources: a reminder the user asked for, or an operator Demo trigger. Every message
has a dedupe_key (one message per key per user), needs the user's consent, waits out
quiet hours, and is stored as a normal chat message. Wording comes from templates,
never from an LLM, and no LLM decides when anything fires.
"""
import json
from datetime import datetime, time, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .actions import COOKIE, DAYS, change_feed, engine, when_key
from .merchant import provider_for

router = APIRouter(tags=["proactive"])
DUBAI = timezone(timedelta(hours=4))  # no daylight saving
QUIET = (time(23, 0), time(7, 0))
clock = lambda: datetime.now(DUBAI)  # replaced in tests


def setup(store):
    store.db.execute("CREATE TABLE IF NOT EXISTS consent (owner TEXT PRIMARY KEY, at TEXT)")
    store.db.execute("""CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, owner TEXT, dedupe_key TEXT, kind TEXT, text TEXT,
        trigger_source TEXT, available_at TEXT, delivered_at TEXT, UNIQUE(owner, dedupe_key))""")
    store.db.commit()


def in_quiet_hours(at):
    start, end = QUIET
    return at.time() >= start or at.time() < end


def after_quiet(at):
    """The first non-quiet moment at or after `at`."""
    if not in_quiet_hours(at):
        return at
    day = at.date() if at.time() < QUIET[1] else at.date() + timedelta(days=1)
    return datetime.combine(day, QUIET[1], DUBAI)


def enqueue(store, owner, dedupe_key, kind, text, source, available_at):
    """Insert once per (owner, dedupe_key); a repeat returns False and adds nothing."""
    if not store.db.execute("SELECT 1 FROM consent WHERE owner=?", (owner,)).fetchone():
        return False
    cur = store.db.execute("INSERT OR IGNORE INTO outbox VALUES (?,?,?,?,?,?,?,NULL)",
                           (uuid4().hex, owner, dedupe_key, kind, text, source, available_at.isoformat()))
    store.db.commit()
    return cur.rowcount == 1


def deliver_due(store, owner):
    """Dispatcher step: release due messages outside quiet hours, then return the delivered thread."""
    now = clock()
    if not in_quiet_hours(now):
        store.db.execute("UPDATE outbox SET delivered_at=? WHERE owner=? AND delivered_at IS NULL AND available_at<=?",
                         (now.isoformat(), owner, now.isoformat()))
        store.db.commit()
    rows = store.db.execute("SELECT id, kind, text, trigger_source, delivered_at FROM outbox WHERE owner=? AND delivered_at IS NOT NULL ORDER BY delivered_at", (owner,)).fetchall()
    return [{"id": r[0], "kind": r[1], "text": r[2], "trigger_source": r[3], "delivered_at": r[4]} for r in rows]


def ready_datetime(action):
    """'Tomorrow 08:30' relative to the day the order was prepared (Dubai time)."""
    day, hm = when_key(action["ready_at"])
    prepared = datetime.fromisoformat(action["events"][0]["at"]).astimezone(DUBAI).date()
    hh, mm = map(int, hm.split(":"))
    return datetime.combine(prepared + timedelta(days=day), time(hh, mm), DUBAI)


class ReminderIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_id: str = Field(max_length=64)


class TriggerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(max_length=40)


@router.post("/api/reminders")
def remind_when_ready(body: ReminderIn, request: Request):
    """User tap: 'Remind me when it's ready'. That tap is the consent; the reminder fires 15 minutes before."""
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))
    with store.lock:
        setup(store)
        action = engine().get(owner, body.action_id)
        if action["status"] not in ("ACCEPTED", "READY") or not when_key(action.get("ready_at")):
            raise HTTPException(409, "A reminder needs an accepted order with a ready time")
        store.db.execute("INSERT OR IGNORE INTO consent VALUES (?,?)", (owner, clock().isoformat()))
        due = after_quiet(max(ready_datetime(action) - timedelta(minutes=15), clock()))
        provider = action["order"]["provider"]
        created = enqueue(store, owner, f"ready:{action['id']}:{action['ready_at']}", "order_ready",
                          f"Reminder you asked for: your order at {provider} is due ready at {action['ready_at']}. The shop confirms ready, not me.",
                          "user_reminder", due)
        return {"scheduled_for": due.isoformat(), "created": created}


@router.get("/api/messages")
def messages(request: Request):
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))
    with store.lock:
        setup(store)
        return {"messages": deliver_due(store, owner)}


@router.get("/api/messages/stream")
def message_stream(request: Request):
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))

    def read():
        with store.lock:
            setup(store)
            return deliver_due(store, owner)
    return StreamingResponse(change_feed(read), media_type="text/event-stream", headers={"Cache-Control": "no-store"})


# Operator-only stage triggers. They stand in for time passing or a flight feed and are always labelled.
TRIGGERS = {
    "fast_forward_reminders": "Make every pending reminder due now (stands in for the clock reaching the reminder time)",
    "flight_landed": "Your flight has landed. Welcome to Dubai. Want me to guide you to arrivals, one confirmed step at a time?",
}


@router.get("/api/demo/triggers")
def list_triggers(request: Request):
    provider_for(request)  # sandbox operator session required
    return {"triggers": [{"kind": k, "description": v} for k, v in TRIGGERS.items()]}


@router.post("/api/demo/triggers")
def fire_trigger(body: TriggerIn, request: Request):
    provider_for(request)  # sandbox operator session required
    if body.kind not in TRIGGERS:
        raise HTTPException(404, "Unknown trigger")
    store = engine().store
    with store.lock:
        setup(store)
        now = clock()
        if body.kind == "fast_forward_reminders":
            cur = store.db.execute("UPDATE outbox SET available_at=?, trigger_source='demo' WHERE delivered_at IS NULL AND available_at>?", (now.isoformat(), now.isoformat()))
            store.db.commit()
            return {"kind": body.kind, "affected": cur.rowcount}
        owners = [row[0] for row in store.db.execute("SELECT owner FROM consent").fetchall()]
        created = sum(enqueue(store, owner, f"landed:{now.date()}", "flight_landed", TRIGGERS["flight_landed"], "demo", now) for owner in owners)
        return {"kind": body.kind, "affected": created}


class ConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    on: bool


@router.post("/api/proactive/consent")
def set_consent(body: ConsentIn, request: Request):
    """Turning messages off also withdraws anything not yet delivered."""
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))
    with store.lock:
        setup(store)
        if body.on:
            store.db.execute("INSERT OR IGNORE INTO consent VALUES (?,?)", (owner, clock().isoformat()))
        else:
            store.db.execute("DELETE FROM consent WHERE owner=?", (owner,))
            store.db.execute("DELETE FROM outbox WHERE owner=? AND delivered_at IS NULL", (owner,))
        store.db.commit()
        return {"on": body.on, "quiet_hours": "23:00-07:00 Dubai"}
