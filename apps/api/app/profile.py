"""Temporal profile store (CLAUDE.md rule 9, ARCHITECTURE.md §12; contest scope: SQLite + the JS math).

Episodes are what the user actually did on this device; the browser computes beliefs
with the shared deterministic math (apps/web/profile.js). Evidence may only point at
allowlisted hypotheses, so sensitive traits (health, religion, ethnicity, nationality,
gender, sexuality, politics) cannot be inferred or stored. Overrides persist:
Confirm / Not true / Forget; Forget also unlinks this device's evidence.
"""
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .actions import COOKIE, engine


def profile_store():
    from .luna.graph import facts  # the shared ProfileStore (user_profile + profile_facts)
    return facts

router = APIRouter(tags=["profile"])
# Mirrors HYPOTHESES in apps/web/data.js. Adding one is a reviewed code change, never model output.
HYPOTHESES = {"order_in_weeknight": ("routine", "Late on weeknights you order in"), "eat_out_friday": ("routine", "On Friday lunch you eat out"),
              "price_unless_deadline": ("preference", "You pick the cheapest, unless a deadline is at risk"),
              "specialty_coffee": ("like", "You like specialty coffee around Al Quoz"), "haircut_4w": ("routine", "You get a haircut about every 4 weeks"),
              "prefers_closest": ("preference", "You pick the closest provider")}
WEIGHTS = {0.5, 1, 2}  # view/dwell 0.5 · dismissal 1 · choice 2 (told facts live in memory, not here)
KINDS = {"view", "choice", "dismissal"}
STATUSES = {"confirmed", "rejected", "forgotten"}


def setup(store):
    store.db.execute("""CREATE TABLE IF NOT EXISTS episodes (id TEXT PRIMARY KEY, owner TEXT, at TEXT, kind TEXT, text TEXT, ev JSON,
        dedupe_key TEXT, UNIQUE(owner, dedupe_key))""")
    store.db.execute("CREATE TABLE IF NOT EXISTS profile_overrides (owner TEXT, hypothesis TEXT, status TEXT, at TEXT, PRIMARY KEY(owner, hypothesis))")
    store.db.commit()


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    h: str = Field(max_length=40)
    w: float


class EpisodeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(max_length=20)
    text: str = Field(min_length=1, max_length=160)
    ev: list[Evidence] = Field(min_length=1, max_length=4)
    dedupe_key: str = Field(min_length=4, max_length=120)


class OverrideIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(max_length=20)


def owner_of(request):
    store = engine().store
    owner = store.owner(request.cookies.get(COOKIE))
    setup(store)
    return store, owner


@router.get("/api/profile")
def read_profile(request: Request):
    store, owner = owner_of(request)
    with store.lock:
        eps = store.db.execute("SELECT at, kind, text, ev FROM episodes WHERE owner=? ORDER BY at", (owner,)).fetchall()
        ovr = store.db.execute("SELECT hypothesis, status FROM profile_overrides WHERE owner=?", (owner,)).fetchall()
    return {"episodes": [{"at": at, "kind": kind, "text": text, "ev": json.loads(ev), "source": "this_device"} for at, kind, text, ev in eps if json.loads(ev)],
            "overrides": dict(ovr)}


@router.post("/api/profile/episodes")
def add_episode(body: EpisodeIn, request: Request):
    if body.kind not in KINDS:
        raise HTTPException(422, "Unknown episode kind")
    if any(e.h not in HYPOTHESES or e.w not in WEIGHTS for e in body.ev):
        raise HTTPException(422, "Evidence must point at an allowlisted hypothesis with a standard weight")
    store, owner = owner_of(request)
    with store.lock:
        cur = store.db.execute("INSERT OR IGNORE INTO episodes VALUES (?,?,?,?,?,?,?)",
                               (uuid4().hex, owner, datetime.now(timezone.utc).isoformat(timespec="seconds"), body.kind, body.text,
                                json.dumps([e.model_dump() for e in body.ev]), body.dedupe_key))
        store.db.commit()
    return {"recorded": cur.rowcount == 1}


@router.put("/api/profile/overrides/{hypothesis}")
def set_override(hypothesis: str, body: OverrideIn, request: Request):
    if hypothesis not in HYPOTHESES or body.status not in STATUSES:
        raise HTTPException(422, "Unknown hypothesis or status")
    store, owner = owner_of(request)
    with store.lock:
        store.db.execute("INSERT INTO profile_overrides VALUES (?,?,?,?) ON CONFLICT(owner, hypothesis) DO UPDATE SET status=excluded.status, at=excluded.at",
                         (owner, hypothesis, body.status, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        if body.status == "forgotten":  # unlink this device's evidence for it
            for eid, ev in store.db.execute("SELECT id, ev FROM episodes WHERE owner=?", (owner,)).fetchall():
                kept = [e for e in json.loads(ev) if e["h"] != hypothesis]
                store.db.execute("UPDATE episodes SET ev=? WHERE id=?", (json.dumps(kept), eid))
        store.db.commit()
    # Only a confirmed hypothesis becomes a profile fact (user_supplied); Not true / Forget remove it.
    facet, label = HYPOTHESES[hypothesis]
    if body.status == "confirmed":
        profile_store().add(owner, hypothesis, label, "You confirmed: " + label, facet=facet, status="confirmed")
    else:
        profile_store().forget(owner, hypothesis)
    return {"hypothesis": hypothesis, "status": body.status}


@router.delete("/api/profile/overrides/{hypothesis}")
def clear_override(hypothesis: str, request: Request):
    store, owner = owner_of(request)
    with store.lock:
        store.db.execute("DELETE FROM profile_overrides WHERE owner=? AND hypothesis=?", (owner, hypothesis))
        store.db.commit()
    profile_store().forget(owner, hypothesis)
    return {"hypothesis": hypothesis, "status": None}


@router.get("/api/profile/me")
def profile_document(request: Request):
    """The growing profile document plus its current facts (all user_supplied: told or confirmed)."""
    store, owner = owner_of(request)
    facts = profile_store()
    return {**facts.document(owner), "facts": facts.current(owner)}
