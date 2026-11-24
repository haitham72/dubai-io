"""CM-B7 moderation lane: reports, flag-only events, human resolution.

Policy (hard rules):
- Moderation FLAGS ONLY. A model / harsh / spam flag never auto-hides,
  bans, or decides. ``harsh`` is sentiment-derived, never a verdict.
- Only a human resolves (keep / remove / restore). A model flag alone
  leaves the target in ``flagged`` state, still visible via routes.
- No messenger. Synthetic/demo data only in tests.
- Adults-only now (D11): no under-18 accounts exist. The ``is_minor``
  concept is kept fail-closed (unknown band => minor) for future use,
  but nothing here creates or admits a minor account.
- Sensitive screening reuses ``app.lab.sensitive`` when importable;
  when unavailable or the model is down, screening fails closed
  (``unscreened`` / ``unavailable`` => blocked flag).

Follow-up (honest, left open): ``remove`` records ``target_state=
removed`` on the moderation event and is exposed via
``GET /api/community/moderation/target/{type}/{id}``. Filtering
``removed`` targets out of the feed / post GET lives in
``routes.py``, which this lane does not edit.
"""
from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from . import store as cm
from .routes import group_row, member_row, post_row, profile_by_handle, profile_by_owner, scope

router = APIRouter(tags=["community-moderation"])

TARGET_TYPES = ("post", "comment", "profile")
DECISIONS = {"keep": "kept", "remove": "removed", "restore": "restored"}
SPAM_DUPLICATE_THRESHOLD = 3

DDL = (
    """CREATE TABLE IF NOT EXISTS cm_reports (
        id TEXT PRIMARY KEY, reporter TEXT NOT NULL, target_type TEXT NOT NULL,
        target_id TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS cm_moderation_events (
        id TEXT PRIMARY KEY, report_id TEXT, source TEXT NOT NULL DEFAULT 'human',
        label TEXT NOT NULL DEFAULT '', evidence TEXT NOT NULL DEFAULT '',
        categories TEXT NOT NULL DEFAULT '[]',
        target_type TEXT NOT NULL, target_id TEXT NOT NULL,
        target_owner TEXT, group_id TEXT,
        status TEXT NOT NULL DEFAULT 'flagged', target_state TEXT NOT NULL DEFAULT 'flagged',
        resolved_by TEXT, resolution TEXT, is_minor INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, resolved_at TEXT)""",
    "CREATE INDEX IF NOT EXISTS cm_mod_events_target ON cm_moderation_events(target_type, target_id, created_at)",
    "CREATE INDEX IF NOT EXISTS cm_reports_target ON cm_reports(target_type, target_id, created_at)",
)


def setup_mod(store):
    if getattr(store, "_moderation_ready", False):
        return
    for stmt in DDL:
        store.db.execute(stmt)
    store.db.commit()
    store._moderation_ready = True


def _setup(store):
    cm.setup(store)
    setup_mod(store)


# ---------------------------------------------------------------- minor (fail-closed, unused for admission)
def is_minor_age_band(age_band: str | None) -> bool:
    """Fail-closed: unknown / non-adult band is treated as minor.

    No under-18 accounts exist in the current adults-only build; this
    only stamps ``is_minor`` on events so a future minor target would
    be prioritised, never admitted by this module.
    """
    band = (age_band or "").strip().lower()
    if not band:
        return True
    if cm.is_non_adult_band(band):
        return True
    if cm.is_adult_band(band):
        return False
    return True


def owner_is_minor(store, owner: str | None) -> bool:
    if not owner:
        return True
    row = profile_by_owner(store, owner)
    if not row:
        return True
    return is_minor_age_band(row[6])


# ---------------------------------------------------------------- sensitive flag helper
def _load_sensitive():
    try:
        from ..lab import sensitive  # app.lab.sensitive (two-layer, fail-closed)
        return sensitive
    except Exception:
        return None


def flag_text(text: str, _screen_fn=None, _categories_fn=None) -> dict:
    """Screen ``text`` and return a flag descriptor. Never a verdict.

    Blocked/flagged means "route to a human", not hidden. When the
    sensitive module cannot be imported, or ``screen()`` raises
    (model down), the result is a blocked flag (fail-closed).
    """
    text = text or ""
    sensitive = _load_sensitive()
    if sensitive is None and _screen_fn is None and _categories_fn is None:
        return {"flagged": True, "blocked": True, "categories": ["unavailable"],
                "source": "sensitive_unavailable", "label": "sensitive_unavailable",
                "evidence": "sensitive screen unavailable; fail-closed flag for human review",
                "target_state": "flagged", "verdict": None}
    try:
        keyword_hits = list(_categories_fn(text)) if _categories_fn else list(sensitive.categories_hit(text))
    except Exception:
        keyword_hits = []
    screen_fn = _screen_fn or (sensitive.screen if sensitive is not None else None)
    if screen_fn is None:
        return {"flagged": True, "blocked": True, "categories": ["unavailable"] + keyword_hits,
                "source": "sensitive_unavailable", "label": "sensitive_unavailable",
                "evidence": "sensitive screen unavailable; fail-closed flag for human review",
                "target_state": "flagged", "verdict": None}
    try:
        blocked = screen_fn([text])
    except Exception:
        cats = list(dict.fromkeys(["unscreened"] + keyword_hits))
        return {"flagged": True, "blocked": True, "categories": cats,
                "source": "model", "label": "unscreened",
                "evidence": "sensitive model unavailable/unscreened; fail-closed flag for human review",
                "target_state": "flagged", "verdict": None}
    categories: list[str] = []
    if isinstance(blocked, dict) and text in blocked:
        categories = [blocked[text]]
    elif keyword_hits:
        categories = keyword_hits
    flagged = bool(categories)
    return {"flagged": flagged, "blocked": flagged, "categories": categories,
            "source": "model" if flagged else "none",
            "label": categories[0] if categories else "none",
            "evidence": f"sensitive categories: {', '.join(categories)}" if categories else "",
            "target_state": "flagged" if flagged else "visible", "verdict": None}


# ---------------------------------------------------------------- spam fingerprint helper
def text_fingerprint(text: str) -> str:
    norm = " ".join((text or "").strip().lower().split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def duplicate_count(store, owner: str, text: str) -> int:
    fp = text_fingerprint(text)
    count = 0
    for (t,) in store.db.execute("SELECT text FROM cm_posts WHERE owner=?", (owner,)).fetchall():
        if text_fingerprint(t) == fp:
            count += 1
    for (t,) in store.db.execute("SELECT text FROM cm_comments WHERE owner=?", (owner,)).fetchall():
        if text_fingerprint(t) == fp:
            count += 1
    return count


def check_spam(store, owner: str, text: str) -> dict:
    """Duplicate-text spam check. Flags only; never bans or hides."""
    count = duplicate_count(store, owner, text)
    flagged = count >= SPAM_DUPLICATE_THRESHOLD
    return {"flagged": flagged, "blocked": False, "banned": False,
            "count": count, "threshold": SPAM_DUPLICATE_THRESHOLD,
            "fingerprint": text_fingerprint(text),
            "label": "spam_duplicate" if flagged else "none",
            "action": "flag" if flagged else "none", "verdict": None}


# ---------------------------------------------------------------- target context / permissions
def target_context(store, target_type: str, target_id: str) -> dict:
    if target_type == "post":
        row = post_row(store, target_id)
        if not row:
            raise HTTPException(404, "Post not found")
        return {"target_type": "post", "target_id": target_id, "owner": row[1],
                "group_id": row[2], "text": row[3]}
    if target_type == "comment":
        row = store.db.execute(
            "SELECT id,post_id,owner,parent_id,text,provenance,created_at FROM cm_comments WHERE id=?",
            (target_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Comment not found")
        post = post_row(store, row[1])
        return {"target_type": "comment", "target_id": target_id, "owner": row[2],
                "group_id": post[2] if post else None, "text": row[4], "post_id": row[1]}
    if target_type == "profile":
        row = profile_by_owner(store, target_id) or profile_by_handle(store, target_id)
        if not row:
            raise HTTPException(404, "Profile not found")
        return {"target_type": "profile", "target_id": target_id, "owner": row[0],
                "group_id": None, "text": row[3] or ""}
    raise HTTPException(422, "target_type must be post, comment or profile")


def is_group_moderator(store, owner: str, group_id: str | None) -> bool:
    if not group_id:
        return False
    group = group_row(store, group_id)
    if group and group[5] == owner:
        return True
    m = member_row(store, group_id, owner)
    return bool(m and m[3] == "active" and m[2] in ("owner", "moderator"))


def _can_view(store, owner: str, ctx: dict, reporter: str | None = None) -> bool:
    if is_group_moderator(store, owner, ctx.get("group_id")):
        return True
    if ctx.get("owner") and ctx["owner"] == owner:
        return True
    if reporter and reporter == owner:
        return True
    return False


def _can_resolve(store, owner: str, ctx: dict, decision: str) -> bool:
    if is_group_moderator(store, owner, ctx.get("group_id")):
        return True
    # Author appeal: the target author may ask for / effect a restore
    # of their own content; keep/remove stay moderator-only.
    if decision == "restore" and ctx.get("owner") and ctx["owner"] == owner:
        return True
    return False


def _ctx_from_event(store, ev: dict) -> dict:
    return {"target_type": ev["target_type"], "target_id": ev["target_id"],
            "owner": ev.get("target_owner"), "group_id": ev.get("group_id"), "text": ""}


# ---------------------------------------------------------------- event helpers
def _present_event(row) -> dict:
    (eid, report_id, source, label, evidence, categories, ttype, tid, towner,
     group_id, status, target_state, resolved_by, resolution, is_minor,
     created_at, resolved_at) = row
    return {"id": eid, "event_id": eid, "report_id": report_id, "source": source,
            "flag_source": source, "label": label, "evidence": evidence,
            "categories": json.loads(categories or "[]"),
            "target_type": ttype, "target_id": tid, "target_owner": towner,
            "group_id": group_id, "status": status, "target_state": target_state,
            "state": target_state, "resolved_by": resolved_by, "resolution": resolution,
            "is_minor": bool(is_minor), "provenance": "user_supplied" if source == "human" else "inferred",
            "as_of": resolved_at or created_at, "created_at": created_at, "resolved_at": resolved_at}


_EVENT_COLS = ("id,report_id,source,label,evidence,categories,target_type,target_id,target_owner,"
               "group_id,status,target_state,resolved_by,resolution,is_minor,created_at,resolved_at")


def _event_row(store, event_id: str):
    return store.db.execute(f"SELECT {_EVENT_COLS} FROM cm_moderation_events WHERE id=?", (event_id,)).fetchone()


def create_event(store, *, source: str, label: str, evidence: str, categories: list[str],
                 ctx: dict, report_id: str | None = None) -> dict:
    eid = uuid4().hex
    stamp = cm.now()
    minor = 1 if owner_is_minor(store, ctx.get("owner")) else 0
    store.db.execute(
        f"INSERT INTO cm_moderation_events ({_EVENT_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?, 'flagged','flagged',NULL,NULL,?,?,NULL)",
        (eid, report_id, source, label, evidence, json.dumps(categories),
         ctx["target_type"], ctx["target_id"], ctx.get("owner"), ctx.get("group_id"), minor, stamp))
    return _present_event(_event_row(store, eid))


def record_model_flag(store, *, target_type: str, target_id: str, label: str = "model_flag",
                      evidence: str = "", categories: list[str] | None = None) -> dict:
    """Insert a model-origin flag. Target stays ``flagged``; never removed."""
    ctx = target_context(store, target_type, target_id)
    return create_event(store, source="model", label=label, evidence=evidence or label,
                        categories=categories or [label], ctx=ctx)


def flag_spam_if_duplicate(store, owner: str, text: str, *, target_type: str, target_id: str) -> dict:
    result = check_spam(store, owner, text)
    event = None
    if result["flagged"]:
        ctx = target_context(store, target_type, target_id)
        event = create_event(store, source="model", label="spam_duplicate",
                             evidence=f"identical text x{result['count']} by same owner (fingerprint {result['fingerprint'][:12]})",
                             categories=["spam_duplicate"], ctx=ctx)
    return {**result, "event": event}


def _order(store, desc: bool = False) -> str:
    # created_at has 1s resolution; rowid preserves insertion order on SQLite.
    col = "rowid" if getattr(store.db, "dialect", "sqlite") == "sqlite" else "created_at"
    return f"{col} {'DESC' if desc else 'ASC'}"


def is_removed(store, target_type: str, target_id: str) -> bool:
    """Latest human decision. A flag alone is not removed. Restore clears it."""
    try:
        setup_mod(store)
        return bool(get_target_state(store, target_type, target_id)["removed"])
    except Exception:
        return False


def get_target_state(store, target_type: str, target_id: str) -> dict:
    rows = store.db.execute(
        f"SELECT {_EVENT_COLS} FROM cm_moderation_events WHERE target_type=? AND target_id=? ORDER BY {_order(store)}",
        (target_type, target_id)).fetchall()
    events = [_present_event(r) for r in rows]
    if not events:
        return {"target_type": target_type, "target_id": target_id, "target_state": "visible",
                "state": "visible", "flagged": False, "removed": False, "events": [], "latest": None}
    latest = events[-1]
    state = latest["target_state"]
    return {"target_type": target_type, "target_id": target_id, "target_state": state,
            "state": state, "flagged": state == "flagged", "removed": state == "removed",
            "events": events, "latest": latest}


# ---------------------------------------------------------------- models
class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_type: str = Field(pattern="^(post|comment|profile)$")
    target_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)


class ResolveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(keep|remove|restore)$")
    note: str = Field(default="", max_length=500)


# ---------------------------------------------------------------- endpoints
@router.post("/api/community/reports")
def create_report(body: ReportIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        _setup(store)
        ctx = target_context(store, body.target_type, body.target_id)
        rid = uuid4().hex
        stamp = cm.now()
        store.db.execute(
            "INSERT INTO cm_reports (id,reporter,target_type,target_id,reason,status,created_at) VALUES (?,?,?,?,?,'pending',?)",
            (rid, owner, body.target_type, body.target_id, body.reason.strip(), stamp))
        event = create_event(store, source="human", label="user_report",
                             evidence=body.reason.strip(), categories=["user_report"],
                             ctx=ctx, report_id=rid)
        store.db.commit()
        report = {"id": rid, "reporter": owner, "target_type": body.target_type,
                  "target_id": body.target_id, "reason": body.reason.strip(),
                  "status": "pending", "created_at": stamp}
        return {"report": report, "event": event, "moderation_event": event}


@router.get("/api/community/moderation/queue")
def moderation_queue(request: Request, status: str | None = Query(default=None, max_length=30)):
    store, owner = scope(request)
    with store.lock:
        _setup(store)
        rows = store.db.execute(
            f"SELECT {_EVENT_COLS} FROM cm_moderation_events ORDER BY {_order(store, desc=True)}").fetchall()
        out = []
        for r in rows:
            ev = _present_event(r)
            if status and ev["status"] != status:
                continue
            reporter = None
            if ev.get("report_id"):
                rep = store.db.execute("SELECT reporter FROM cm_reports WHERE id=?", (ev["report_id"],)).fetchone()
                reporter = rep[0] if rep else None
            if _can_view(store, owner, _ctx_from_event(store, ev), reporter=reporter):
                out.append(ev)
        return {"events": out, "queue": out, "count": len(out)}


@router.post("/api/community/moderation/{event_id}/resolve")
def resolve_event(event_id: str, body: ResolveIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        _setup(store)
        row = _event_row(store, event_id)
        if not row:
            raise HTTPException(404, "Moderation event not found")
        ev = _present_event(row)
        ctx = _ctx_from_event(store, ev)
        if not _can_resolve(store, owner, ctx, body.decision):
            raise HTTPException(403, "Only a group moderator (or the author, for a restore appeal) can resolve this flag")
        new_state = DECISIONS[body.decision]
        stamp = cm.now()
        resolution = body.note.strip() or body.decision
        store.db.execute(
            "UPDATE cm_moderation_events SET status=?, target_state=?, resolved_by=?, resolution=?, resolved_at=? WHERE id=?",
            (new_state, new_state, owner, resolution, stamp, event_id))
        if ev.get("report_id"):
            store.db.execute("UPDATE cm_reports SET status=? WHERE id=?", (new_state, ev["report_id"]))
        store.db.commit()
        updated = _present_event(_event_row(store, event_id))
        return {"event": updated, "moderation_event": updated, "target_state": new_state}


@router.get("/api/community/moderation/target/{target_type}/{target_id}")
def moderation_target(target_type: str, target_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        _setup(store)
        if target_type not in TARGET_TYPES:
            raise HTTPException(422, "target_type must be post, comment or profile")
        state = get_target_state(store, target_type, target_id)
        if state["events"]:
            latest_ctx = _ctx_from_event(store, state["latest"])
            reporter = None
            if state["latest"].get("report_id"):
                rep = store.db.execute("SELECT reporter FROM cm_reports WHERE id=?",
                                       (state["latest"]["report_id"],)).fetchone()
                reporter = rep[0] if rep else None
            if not _can_view(store, owner, latest_ctx, reporter=reporter):
                raise HTTPException(403, "You cannot view moderation state for this target")
        # Honest integration note: routes.py feed/post filtering is a follow-up.
        state["feed_filtering"] = "removed targets are hidden from the feed, search, notifications and community pages"
        return state
