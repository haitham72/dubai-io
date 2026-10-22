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
    # How follow-ups happen: ask (default), auto (routine reminders/check-backs without
    # asking each time) or learn (ask, then offer auto once the user keeps choosing it).
    # No mode can send, share or pay; those always wait for an approval tap.
    store.db.execute("""CREATE TABLE IF NOT EXISTS assist (owner TEXT PRIMARY KEY, mode TEXT NOT NULL,
        manual_reminders INTEGER NOT NULL, offer_dismissed INTEGER NOT NULL, updated_at TEXT NOT NULL)""")
    store.commit()


MODES = ("ask", "auto", "learn")
LEARN_AFTER = 3


def assist(store, owner):
    row = store.db.execute("SELECT mode, manual_reminders, offer_dismissed FROM assist WHERE owner=?", (owner,)).fetchone()
    mode, count, dismissed = row or ("ask", 0, 0)
    return {"mode": mode, "manual_reminders": count, "offer_auto": mode == "learn" and count >= LEARN_AFTER and not dismissed}


def save_assist(store, owner, **changes):
    current = assist(store, owner)
    row = store.db.execute("SELECT offer_dismissed FROM assist WHERE owner=?", (owner,)).fetchone()
    values = {"mode": current["mode"], "manual_reminders": current["manual_reminders"], "offer_dismissed": row[0] if row else 0, **changes}
    store.db.execute("DELETE FROM assist WHERE owner=?", (owner,))
    store.db.execute("INSERT INTO assist VALUES (?,?,?,?,?)", (owner, values["mode"], values["manual_reminders"],
                                                                values["offer_dismissed"], clock().isoformat()))


def schedule_ready_reminder(store, owner, action, source="user_reminder"):
    """Fires 15 minutes before the shop's ready time; the caller has established consent."""
    store.db.execute("INSERT OR IGNORE INTO consent VALUES (?,?)", (owner, clock().isoformat()))
    due = after_quiet(max(ready_datetime(action) - timedelta(minutes=15), clock()))
    provider = action["order"]["provider"]
    lead = "Reminder you asked for" if source == "user_reminder" else "Automatic reminder (Auto follow-ups)"
    created = enqueue(store, owner, f"ready:{action['id']}:{action['ready_at']}", "order_ready",
                      f"{lead}: your order at {provider} is due ready at {action['ready_at']}. The shop confirms ready, not me.",
                      source, due)
    return due, created


def auto_follow_up_order(store, owner, action):
    """Merchant set a ready time: in Auto mode, schedule the reminder without asking."""
    setup(store)
    if assist(store, owner)["mode"] == "auto" and action["status"] in ("ACCEPTED", "READY") and when_key(action.get("ready_at")):
        schedule_ready_reminder(store, owner, action, source="auto_follow_up")


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
    store.commit()
    return cur.rowcount == 1


def deliver_due(store, owner):
    """Dispatcher step: release due messages outside quiet hours, then return the delivered thread."""
    now = clock()
    if not in_quiet_hours(now):
        store.db.execute("UPDATE outbox SET delivered_at=? WHERE owner=? AND delivered_at IS NULL AND available_at<=?",
                         (now.isoformat(), owner, now.isoformat()))
        store.commit()
    rows = store.db.execute("SELECT id, kind, text, trigger_source, delivered_at, dedupe_key FROM outbox WHERE owner=? AND delivered_at IS NOT NULL ORDER BY delivered_at", (owner,)).fetchall()
    # A check-back names its task so the message can open it; the task is re-read with ownership checks.
    return [{"id": r[0], "kind": r[1], "text": r[2], "trigger_source": r[3], "delivered_at": r[4],
             **({"task_id": r[5].split(":")[1]} if r[1] == "task_checkback" else {})} for r in rows]


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
        due, created = schedule_ready_reminder(store, owner, action)
        if created:  # Learn counts what the user keeps choosing by hand
            save_assist(store, owner, manual_reminders=assist(store, owner)["manual_reminders"] + 1)
        store.commit()
        return {"scheduled_for": due.isoformat(), "created": created, "offer_auto": assist(store, owner)["offer_auto"]}


class AssistIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str = Field(pattern="^(ask|auto|learn)$")
    dismiss_offer: bool = False


@router.get("/api/assist")
def get_assist(request: Request):
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))
    with store.lock:
        setup(store)
        return assist(store, owner)


@router.put("/api/assist")
def set_assist(body: AssistIn, request: Request):
    """Choosing Auto is the standing consent for routine reminders and check-backs."""
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))
    with store.lock:
        setup(store)
        save_assist(store, owner, mode=body.mode, **({"offer_dismissed": 1} if body.dismiss_offer else {}))
        if body.mode == "auto":
            store.db.execute("INSERT OR IGNORE INTO consent VALUES (?,?)", (owner, clock().isoformat()))
        store.db.commit()
        return assist(store, owner)


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
