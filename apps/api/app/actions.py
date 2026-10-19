"""Durable local action engine; production providers are deliberately unconnected.

Preparation is local. Only a registered adapter can execute, after an approval
of the exact server snapshot. SQLite is a lab store, not the planned Postgres gate.
"""
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets
import sqlite3
from threading import RLock
from typing import Callable, Literal
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from .config import settings


class InputValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(max_length=600)
    provenance: Literal["user_supplied"] = "user_supplied"


class PrepareIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capability_id: str = Field(max_length=80)
    fields: dict[str, InputValue] = Field(max_length=20)
    draft_id: str | None = Field(default=None, max_length=64)
    preparation_key: str = Field(default_factory=lambda: uuid4().hex, min_length=8, max_length=100)


class ApprovalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    revision: int = Field(ge=1)


@dataclass(frozen=True)
class Capability:
    id: str
    label: str
    fields: tuple[str, ...]
    required: tuple[str, ...]
    recipient: str
    blocked_reason: str
    adapter: Callable | None = None
    effect: str = "Send these details only; no payment or booking"
    fixed_total_aed: str | None = None

    def __post_init__(self):
        if self.fixed_total_aed is not None and (not Decimal(self.fixed_total_aed).is_finite() or Decimal(self.fixed_total_aed) < 0):
            raise ValueError("Published total must be a finite nonnegative amount")


SERVICES = {"laundry": "Laundry", "cleaning": "Home cleaning", "ac": "AC service",
            "grooming": "Pet grooming", "carwash": "Car wash", "pharmacy": "Pharmacy", "maid": "Maid hire"}
CAPABILITIES = {key + ".request": Capability(key + ".request", label,
    ("request", "area", "provider"), ("request", "area"), "Provider not connected",
    "No live provider adapter is connected. Your draft is saved; nothing has been sent.")
    for key, label in SERVICES.items()}
CAPABILITIES["recovery.rta"] = Capability("recovery.rta", "Taxi lost item report",
    ("description", "when", "from", "to", "plate", "roof", "fare", "payment", "booking"),
    ("description", "when", "from", "to"), "RTA lost & found",
    "RTA reporting integration is unavailable. Your report is saved; nothing has been filed.")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class ActionStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, owner TEXT, data TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, owner TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS preparations (owner TEXT, key TEXT, payload_hash TEXT, result TEXT, PRIMARY KEY(owner,key))")
        self.db.execute("CREATE TABLE IF NOT EXISTS approvals (action_id TEXT, key TEXT, result TEXT, PRIMARY KEY(action_id,key))")
        self.db.commit()
        self.lock = RLock()

    def session(self, token):
        with self.lock:
            row = self.db.execute("SELECT owner FROM sessions WHERE token_hash=?", (fingerprint(token),)).fetchone() if token else None
            if row:
                return row[0], None
            token, owner = secrets.token_urlsafe(32), uuid4().hex
            self.db.execute("INSERT INTO sessions VALUES (?,?)", (fingerprint(token), owner))
            self.db.commit()
            return owner, token

    def owner(self, token):
        with self.lock:
            row = self.db.execute("SELECT owner FROM sessions WHERE token_hash=?", (fingerprint(token),)).fetchone() if token else None
            if not row:
                raise HTTPException(401, "Open an app session first")
            return row[0]

    def get(self, owner, action_id):
        row = self.db.execute("SELECT data FROM actions WHERE id=? AND owner=?", (action_id, owner)).fetchone()
        if not row:
            raise HTTPException(404, "Request not found")
        return json.loads(row[0])

    def put(self, owner, action):
        self.db.execute("INSERT INTO actions VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (action["id"], owner, json.dumps(action)))
        self.db.commit()


class ActionEngine:
    def __init__(self, store, registry=None):
        self.store, self.registry = store, CAPABILITIES if registry is None else registry
        self.in_flight = set()

    def catalog(self):
        return [{"id": c.id, "label": c.label, "fields": c.fields, "required": c.required,
                 "recipient": c.recipient, "effect": c.effect, "fixed_total_aed": c.fixed_total_aed, "execution_available": c.adapter is not None,
                 "blocked_reason": None if c.adapter else c.blocked_reason} for c in self.registry.values()]

    def prepare(self, owner, body: PrepareIn):
        capability = self.registry.get(body.capability_id)
        if capability is None:
            raise HTTPException(400, "Unregistered capability")
        if set(body.fields) - set(capability.fields):
            raise HTTPException(422, "Unsupported fields")
        with self.store.lock:
            payload_hash = fingerprint({"capability_id": body.capability_id, "fields": {key: value.model_dump() for key, value in body.fields.items()}, "draft_id": body.draft_id})
            replay = self.store.db.execute("SELECT payload_hash,result FROM preparations WHERE owner=? AND key=?", (owner, body.preparation_key)).fetchone()
            if replay:
                if replay[0] != payload_hash:
                    raise HTTPException(409, "Preparation key already used for different details")
                return json.loads(replay[1])
            previous = self.store.get(owner, body.draft_id) if body.draft_id else None
            if previous and previous["status"] not in {"DRAFT", "BLOCKED", "AWAITING_APPROVAL"}:
                raise HTTPException(409, "This action cannot be edited after dispatch")
            if previous and previous["capability_id"] != capability.id:
                raise HTTPException(409, "A draft cannot change capabilities")
            fields = {key: {"value": field.value.strip(), "provenance": "user_supplied"} for key, field in body.fields.items() if field.value.strip()}
            missing = [key for key in capability.required if key not in fields]
            snapshot = {"capability_id": capability.id, "recipient": capability.recipient, "effect": capability.effect, "fixed_total_aed": capability.fixed_total_aed, "fields": fields}
            action = {"id": previous["id"] if previous else uuid4().hex,
                      **snapshot, "revision": previous["revision"] + 1 if previous else 1,
                      "snapshot_hash": fingerprint(snapshot), "missing": missing,
                      "status": "DRAFT" if missing else "AWAITING_APPROVAL" if capability.adapter else "BLOCKED",
                      "execution_available": capability.adapter is not None,
                      "blocked_reason": None if capability.adapter else capability.blocked_reason,
                      "evidence": None, "events": (previous or {}).get("events", []) + [{"kind": "prepared", "at": now(), "revision": previous["revision"] + 1 if previous else 1}]}
            self.store.db.execute("INSERT INTO preparations VALUES (?,?,?,?)", (owner, body.preparation_key, payload_hash, json.dumps(action)))
            self.store.put(owner, action)
            return action

    def get(self, owner, action_id):
        with self.store.lock:
            action = self.store.get(owner, action_id)
            if action["status"] == "DISPATCHING" and action_id not in self.in_flight:
                action["status"] = "UNKNOWN_STATUS"
                action["blocked_reason"] = "Dispatch was interrupted. Check the provider before retrying."
                self.store.put(owner, action)
            return action

    def cancel(self, owner, action_id):
        with self.store.lock:
            action = self.get(owner, action_id)
            if action["status"] == "CANCELLED":
                return action
            if action["status"] not in {"DRAFT", "BLOCKED", "AWAITING_APPROVAL"}:
                raise HTTPException(409, "A dispatched request needs a provider cancellation capability")
            action["status"] = "CANCELLED"
            action["blocked_reason"] = "You discarded this draft. Nothing was sent."
            action["events"].append({"kind": "cancelled", "at": now()})
            self.store.put(owner, action)
            return action

    def approve(self, owner, action_id, body: ApprovalIn, key):
        with self.store.lock:
            action = self.get(owner, action_id)
            if action["snapshot_hash"] != body.snapshot_hash or action["revision"] != body.revision:
                raise HTTPException(409, "Draft changed. Review and approve the current details.")
            replay = self.store.db.execute("SELECT result FROM approvals WHERE action_id=? AND key=?", (action_id, key)).fetchone()
            if replay:
                return json.loads(replay[0])
            if action["status"] in {"SUBMITTED", "DISPATCHING", "UNKNOWN_STATUS", "FAILED"}:
                return action  # no second dispatch, including after an ambiguous failure
            capability = self.registry[action["capability_id"]]
            if (action["recipient"], action["effect"], action["fixed_total_aed"]) != (capability.recipient, capability.effect, capability.fixed_total_aed):
                raise HTTPException(409, "Provider terms changed. Prepare and review the current request.")
            if action["status"] != "AWAITING_APPROVAL" or capability.adapter is None:
                raise HTTPException(409, action["blocked_reason"] or "Complete the missing fields first")
            action["status"] = "DISPATCHING"
            action["events"].append({"kind": "approved", "at": now(), "revision": action["revision"]})
            self.in_flight.add(action_id)
            self.store.put(owner, action)
        try:
            evidence = capability.adapter(action, key)
            # A trusted adapter must return a provider reference, not LLM status text.
            if not isinstance(evidence, dict) or evidence.get("provenance") != "provider_confirmed" or not isinstance(evidence.get("reference"), str) or not evidence["reference"].strip():
                raise ValueError("Unverified provider response")
            action["status"], action["evidence"] = "SUBMITTED", {"reference": evidence["reference"], "provenance": "provider_confirmed"}
            action["blocked_reason"] = None
        except Exception:
            action["status"] = "UNKNOWN_STATUS"
            action["blocked_reason"] = "The provider outcome is unknown. Reconcile it before any retry."
        finally:
            with self.store.lock:
                action["events"].append({"kind": "adapter_result", "at": now(), "status": action["status"]})
                self.store.put(owner, action)
                self.store.db.execute("INSERT INTO approvals VALUES (?,?,?)", (action_id, key, json.dumps(action)))
                self.store.db.commit()
                self.in_flight.discard(action_id)
        return action


_engine = None
_engine_lock = RLock()

def engine():
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = ActionEngine(ActionStore(settings.data_dir / "actions.sqlite3"))
        return _engine


router = APIRouter(tags=["actions"])
COOKIE = "dubaiio_lab_session"

@router.get("/api/session")
def session(request: Request, response: Response):
    owner, token = engine().store.session(request.cookies.get(COOKIE))
    if token:
        response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=30*86400)
    return {"user_id": owner, "mode": "anonymous_lab_session"}

@router.get("/api/actions/capabilities")
def capabilities():
    return {"capabilities": engine().catalog()}

@router.post("/api/actions/prepare")
def prepare(body: PrepareIn, request: Request):
    return engine().prepare(engine().store.owner(request.cookies.get(COOKIE)), body)

@router.get("/api/actions")
def list_actions(request: Request):
    owner = engine().store.owner(request.cookies.get(COOKIE))
    with engine().store.lock:
        ids = [row[0] for row in engine().store.db.execute("SELECT id FROM actions WHERE owner=?", (owner,)).fetchall()]
        return {"actions": [engine().get(owner, action_id) for action_id in ids]}

@router.get("/api/actions/{action_id}")
def get_action(action_id: str, request: Request):
    return engine().get(engine().store.owner(request.cookies.get(COOKIE)), action_id)

@router.post("/api/actions/{action_id}/approve")
def approve(action_id: str, body: ApprovalIn, request: Request, idempotency_key: str = Header(min_length=8, max_length=100)):
    return engine().approve(engine().store.owner(request.cookies.get(COOKIE)), action_id, body, idempotency_key)


@router.post("/api/actions/{action_id}/cancel")
def cancel_action(action_id: str, request: Request):
    return engine().cancel(engine().store.owner(request.cookies.get(COOKIE)), action_id)
