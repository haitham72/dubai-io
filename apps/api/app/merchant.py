"""Sandbox merchant role: one provider's inbox of fixed-price orders.

A merchant session is separate from user sessions and sees only its provider's
dispatched orders, and only the fields the user approved for sharing. Every
status change comes from a merchant tap here; nothing is simulated.
"""
import hmac
from contextlib import contextmanager
import json
import logging
import secrets

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from . import catalog
from .actions import MERCHANT_MOVES, annotate, change_feed, engine, fingerprint, now, when_key
from .config import settings

router = APIRouter(tags=["merchant"])
COOKIE = "dubaiio_merchant_session"
VISIBLE = ("SUBMITTED", "ACCEPTED", "READY", "COMPLETED", "DECLINED", "UNKNOWN_STATUS")
log = logging.getLogger("dubaiio.merchant")
_pin = None


def merchant_pin():
    """Configured PIN, or one generated once into data/merchant.pin for the local sandbox."""
    global _pin
    if _pin is None:
        path = settings.data_dir / "merchant.pin"
        if settings.merchant_pin:
            _pin = settings.merchant_pin
        elif path.exists():
            _pin = path.read_text().strip()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            _pin = f"{secrets.randbelow(10**6):06d}"
            path.write_text(_pin)
            log.warning("Sandbox merchant PIN written to %s", path)
    return _pin


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_id: str = Field(max_length=40)
    pin: str = Field(max_length=20)


class CommandIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ready_at: str | None = Field(default=None, max_length=20)
    reason: str | None = Field(default=None, max_length=200)


def provider_for(request: Request):
    token = request.cookies.get(COOKIE)
    store = engine().store
    with store.lock:
        row = store.db.execute("SELECT provider_id FROM merchant_sessions WHERE token_hash=?", (fingerprint(token),)).fetchone() if token else None
    if not row:
        raise HTTPException(401, "Sign in as the sandbox merchant first")
    return row[0]


def shared_view(action):
    """What the merchant may see: the approved order and fields, never the user's identity."""
    return {key: action.get(key) for key in ("id", "status", "order", "fixed_total_aed", "ready_at", "earlier_request", "deadline_check", "evidence")} | {
        "fields": {key: field["value"] for key, field in action["fields"].items()},
        "events": [event for event in action["events"] if event["kind"] in ("adapter_result", "status", "earlier_requested", "ready_time")]}


def orders(provider):
    store = engine().store
    with store.lock:
        rows = store.db.execute("SELECT owner, data FROM actions WHERE provider=?", (provider,)).fetchall()
    found = [annotate(json.loads(data)) for _, data in rows]
    return sorted((shared_view(a) for a in found if a["status"] in VISIBLE), key=lambda a: a["events"][-1]["at"] if a["events"] else "", reverse=True)


@router.get("/api/merchant/providers")
def providers():
    return {"providers": [{"id": key, "name": name, "service": service} for key, (name, service, _, _) in catalog.PROVIDERS.items()]}


@router.post("/api/merchant/login")
def login(body: LoginIn, request: Request, response: Response):
    if body.provider_id not in catalog.PROVIDERS or not hmac.compare_digest(body.pin, merchant_pin()):
        raise HTTPException(403, "Wrong provider or PIN")
    token = secrets.token_urlsafe(32)
    store = engine().store
    with store.lock:
        store.db.execute("INSERT INTO merchant_sessions VALUES (?,?)", (fingerprint(token), body.provider_id))
        store.db.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=86400)
    return {"provider_id": body.provider_id, "name": catalog.PROVIDERS[body.provider_id][0], "role": "merchant"}


@router.get("/api/merchant/orders")
def list_orders(request: Request):
    return {"orders": orders(provider_for(request))}


@router.get("/api/merchant/stream")
def stream(request: Request):
    provider = provider_for(request)
    return StreamingResponse(change_feed(lambda: orders(provider)), media_type="text/event-stream", headers={"Cache-Control": "no-store"})


@router.post("/api/merchant/orders/{action_id}/{command}")
def command(action_id: str, command: str, body: CommandIn, request: Request, idempotency_key: str = Header(min_length=8, max_length=100)):
    provider = provider_for(request)
    eng, store = engine(), engine().store
    with order_write(store, provider, action_id) as owner:
        replay = store.db.execute("SELECT result FROM merchant_commands WHERE action_id=? AND key=?", (action_id, idempotency_key)).fetchone()
        if replay:
            return json.loads(replay[0])
        action = eng.get(owner, action_id)
        if command == "confirm-time":
            if action["status"] not in ("ACCEPTED", "READY") or not when_key(body.ready_at):
                raise HTTPException(409, "Confirm a time like 'Tomorrow 08:30' on an accepted order")
            action["events"].append({"kind": "ready_time", "from": action.get("ready_at"), "to": body.ready_at, "actor": "merchant", "at": now(), "price_unchanged": action["fixed_total_aed"]})
            action["ready_at"], action["earlier_request"] = body.ready_at, None
            store.put(owner, action)
            annotate(action)
        elif command in MERCHANT_MOVES:
            allowed, to = MERCHANT_MOVES[command]
            if action["status"] not in allowed:
                raise HTTPException(409, f"Cannot {command} an order that is {action['status']}")
            meta = {}
            if command == "accept":
                if not when_key(body.ready_at):
                    raise HTTPException(422, "Accept with a ready time like 'Tomorrow 10:00'")
                action["ready_at"] = meta["ready_at"] = body.ready_at
            if command == "decline":
                meta["reason"] = (body.reason or "Declined by the merchant").strip()
            eng.transition(owner, action, to, "merchant", **meta)
        else:
            raise HTTPException(404, "Unknown command")
        if command in ("accept", "confirm-time"):
            from .proactive import auto_follow_up_order  # proactive imports this module
            auto_follow_up_order(store, owner, action)
        result = shared_view(action)
        store.db.execute("INSERT INTO merchant_commands VALUES (?,?,?)", (action_id, idempotency_key, json.dumps(result)))
        return result


@contextmanager
def order_write(store, provider, action_id):
    """Authenticate the provider, then serialize with user/task source writes."""
    with store.lock:
        row = store.db.execute("SELECT owner FROM actions WHERE id=? AND provider=?", (action_id, provider)).fetchone()
        if not row:
            raise HTTPException(404, "Order not found")
    with store.transaction(row[0]):
        yield row[0]
