"""CM-B9 agents: Discovery, Community Answer, Group Organizer, Moderation Copilot.

Design choice (documented): publishing mirrors ``actions.py`` approve semantics
(exact ``revision`` + ``snapshot_hash`` match at line ~313, else 409, one
dispatch per approval) in own ``cm_`` tables instead of reusing the actions
engine. The actions engine is bound to merchant/order adapters and its
``CAPABILITIES`` registry lives in the parked ``actions.py`` (import-only
here); a community post is not a merchant order. So this module keeps a
*local* registered-capability set and only ids in it may execute. The agent
fills in data only; it never writes executable payloads.

Hard rules:
- AI drafts publish ONLY after approval of the exact revision+destination
  via registered capability ``community.answer.publish`` + snapshot hash.
- One approval per side effect (D15): replaying an approve returns the
  first result and never creates a second post.
- Group Organizer proposes only, never contacts/invites (D14): a proposal
  creates zero notifications for other members.
- No raw private text in ranking. Discovery always uses the adult's own
  Community profile interests and follows. Consented InterestFeature values
  are added afterwards. A denied or failed bridge adds nothing.
- No messenger: no DM endpoints, no outbound contact of any kind.
"""
import hashlib
import json
import os
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from ..actions import fingerprint
from . import store as cm
from .routes import (
    _create_post,
    group_access,
    group_row,
    is_active_member,
    member_row,
    post_row,
    present_post,
    profile_by_owner,
    require_group,
    require_visible_post,
    scope,
)

router = APIRouter(tags=["community-agents"])

# Local registered-capability registry (mirrors actions.CAPABILITIES pattern).
# Only ids in this set may execute a side effect.
REGISTERED_CAPABILITIES = {"community.answer.publish"}
CAPABILITY_ANSWER_PUBLISH = "community.answer.publish"

DEFAULT_SOURCE_ALLOWLIST = "gov.ae,dubai.ae,rta.ae,dubai.gov.ae,visitdubai.com,example.com,example.org"

DDL = (
    """CREATE TABLE IF NOT EXISTS cm_recommendation_events (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, candidate_type TEXT, candidate_id TEXT,
        features TEXT NOT NULL DEFAULT '[]', why_this TEXT NOT NULL DEFAULT '',
        reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS cm_answer_drafts (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, question TEXT NOT NULL DEFAULT '',
        text TEXT NOT NULL, group_id TEXT, destination TEXT NOT NULL,
        sources TEXT NOT NULL DEFAULT '[]', capability_id TEXT NOT NULL,
        revision INTEGER NOT NULL DEFAULT 1, snapshot_hash TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft', post_id TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS cm_answer_approvals (
        draft_id TEXT PRIMARY KEY, owner TEXT NOT NULL, revision INTEGER NOT NULL,
        snapshot_hash TEXT NOT NULL, post_id TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS cm_organizer_proposals (
        id TEXT PRIMARY KEY, group_id TEXT NOT NULL, owner TEXT NOT NULL,
        title TEXT NOT NULL, checklist TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'proposed', created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS cm_copilot_flags (
        id TEXT PRIMARY KEY, post_id TEXT NOT NULL, owner TEXT NOT NULL,
        label TEXT NOT NULL, created_at TEXT NOT NULL)""",
)


def setup_agents(store):
    if getattr(store, "_agents_ready", False):
        return
    cm.setup(store)
    for stmt in DDL:
        store.db.execute(stmt)
    store.db.commit()
    store._agents_ready = True


def _allowlist():
    raw = os.environ.get("CM_SOURCE_ALLOWLIST", DEFAULT_SOURCE_ALLOWLIST)
    return [h.strip().lower() for h in raw.split(",") if h.strip()]


def _host_allowed(url):
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    return any(host == a or host.endswith("." + a) for a in _allowlist())


def _snapshot(text, destination, group_id, sources, question, capability_id):
    return fingerprint({"text": text, "destination": destination, "group_id": group_id,
                        "sources": sources, "question": question, "capability_id": capability_id})


def _present_draft(row):
    return {"id": row[0], "owner": row[1], "question": row[2], "text": row[3],
            "group_id": row[4], "destination": row[5], "sources": json.loads(row[6] or "[]"),
            "capability_id": row[7], "revision": row[8], "snapshot_hash": row[9],
            "status": row[10], "post_id": row[11], "created_at": row[12], "updated_at": row[13],
            "provenance": "user_supplied", "as_of": row[13]}


def _draft_row(store, draft_id):
    return store.db.execute(
        "SELECT id,owner,question,text,group_id,destination,sources,capability_id,revision,snapshot_hash,status,post_id,created_at,updated_at FROM cm_answer_drafts WHERE id=?",
        (draft_id,)).fetchone()


# ---------------------------------------------------------------- models
class SourceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="", max_length=300)
    url: str = Field(min_length=1, max_length=2000)
    publisher: str = Field(default="", max_length=200)
    as_of: str = Field(default="", max_length=100)


class DraftIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(default="", max_length=2000)
    text: str | None = Field(default=None, max_length=4000)
    answer: str | None = Field(default=None, max_length=4000)
    answer_text: str | None = Field(default=None, max_length=4000)
    body: str | None = Field(default=None, max_length=4000)
    content: str | None = Field(default=None, max_length=4000)
    group_id: str | None = Field(default=None, max_length=100)
    destination: str | None = Field(default=None, max_length=100)
    sources: list[SourceIn] = Field(default_factory=list, max_length=20)
    capability_id: str = Field(default=CAPABILITY_ANSWER_PUBLISH, max_length=80)


class DraftEditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str | None = Field(default=None, max_length=4000)
    answer: str | None = Field(default=None, max_length=4000)
    answer_text: str | None = Field(default=None, max_length=4000)
    body: str | None = Field(default=None, max_length=4000)
    content: str | None = Field(default=None, max_length=4000)
    question: str | None = Field(default=None, max_length=2000)
    group_id: str | None = Field(default=None, max_length=100)
    destination: str | None = Field(default=None, max_length=100)
    sources: list[SourceIn] | None = Field(default=None, max_length=20)


class ApproveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    snapshot_hash: str = Field(min_length=8, max_length=128)
    capability_id: str | None = Field(default=None, max_length=80)


class ProposeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    checklist: list[str] = Field(default_factory=list, max_length=50)


class FlagIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    post_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=100)


def _draft_text(body):
    for v in (body.text, body.answer, body.answer_text, body.body, body.content):
        if v and v.strip():
            return v.strip()
    return (body.question or "").strip()


def _destination(group_id, destination):
    if group_id:
        return f"group:{group_id}"
    if destination and destination.strip():
        return destination.strip()
    return "feed"


# ---------------------------------------------------------------- Discovery
_CROSS_WHY = "From interests you share from Dubai-io, with consent"
_COLD_WHY = "Popular public community. Cold start, not based on your interests."


def _why_chip(item):
    item["why_chip"] = "Why this?"
    return item


def _local_why(matched, follow_handle):
    parts = []
    if matched:
        parts.append(f"You picked {matched[0]} when you joined")
    if follow_handle:
        parts.append(f"You follow @{follow_handle}")
    return ". ".join(parts)


def _bridge_post_items(request, store, owner):
    """InterestFeature posts only. Consent denied, empty, or any bridge error adds nothing."""
    from .memory import bridge_of

    bridge = bridge_of(request)
    principal = getattr(request.state, "community_principal", None)
    if bridge is None or principal is None:
        return []
    try:
        features = list(bridge.read_community_interest_features(principal))
    except Exception:
        return []
    by_id = {}
    rows = store.db.execute("SELECT id,owner,group_id,text FROM cm_posts WHERE deleted=0").fetchall()
    for feature in features:
        needle = (feature.topic_slug or "").lower()
        label = (feature.topic_label or "").lower()
        if not needle and not label:
            continue
        for row in rows:
            if row[1] == owner:
                continue
            hay = (row[3] or "").lower()
            if not ((needle and needle in hay) or (label and label in hay)):
                continue
            if row[2]:
                group = store.db.execute("SELECT visibility FROM cm_groups WHERE id=?", (row[2],)).fetchone()
                if group and group[0] == "private":
                    continue
            item = by_id.get(row[0])
            if item is None:
                item = _why_chip({
                    "kind": "post", "type": "post", "id": row[0], "post_id": row[0],
                    "group_id": row[2], "text": row[3], "score": 1,
                    "features_used": [], "why_this": _CROSS_WHY,
                    "origin": "interest_feature", "demo_data": bool(feature.demo_data),
                })
                by_id[row[0]] = item
            if feature.feature_id not in item["features_used"]:
                item["features_used"].append(feature.feature_id)
            item["demo_data"] = item["demo_data"] or bool(feature.demo_data)
    return list(by_id.values())


def _cold_start_groups(store, limit):
    rows = store.db.execute(
        "SELECT id,name,handle,description,visibility,owner,provenance,created_at FROM cm_groups WHERE visibility='public'"
    ).fetchall()
    ranked = []
    for g in rows:
        if g[4] != "public":
            continue
        count = store.db.execute(
            "SELECT COUNT(*) FROM cm_group_members WHERE group_id=? AND status='active'", (g[0],)
        ).fetchone()[0]
        ranked.append((count, g))
    ranked.sort(key=lambda pair: (-pair[0], pair[1][7] or "", pair[1][0]))
    items = []
    for count, g in ranked[:limit]:
        items.append(_why_chip({
            "kind": "group", "type": "group", "id": g[0], "group_id": g[0],
            "name": g[1], "handle": g[2], "description": g[3], "score": count,
            "features_used": [], "why_this": _COLD_WHY, "why_chip": "Why this?",
            "provenance": g[6], "as_of": g[7], "members": count, "origin": "cold_start",
        }))
    return items


def _discovery_source(local_marked, bridge_marked):
    if local_marked and bridge_marked:
        return "local_cm_profile+interest_feature"
    if bridge_marked:
        return "interest_feature"
    return "local_cm_profile"


def _compat_discovery_source(items, features_used, reason):
    """Map two-tower origins onto the legacy discovery source labels tests/UI expect."""
    if reason and "Cold start" in reason:
        return "local_cm_profile"
    bridge_marked = any(
        it.get("origin") == "interest_feature" or it.get("also_interest_feature") for it in items
    )
    local_marked = any(
        it.get("origin") in ("local", "two_tower")
        or any(str(f).startswith(("interest:", "follow:")) for f in (it.get("features_used") or []))
        for it in items
    ) or any(str(f).startswith(("interest:", "follow:")) for f in (features_used or []))
    if local_marked or bridge_marked:
        return _discovery_source(local_marked, bridge_marked)
    return "local_cm_profile"


def _interest_matched_groups(store, owner: str, interests: list[str], follow_handles: dict, follow_owners: set, limit: int):
    """Legacy group discovery cards (interest/follow features) merged after post ranking."""
    items = []
    for g in store.db.execute(
        "SELECT id,name,handle,description,visibility,owner,provenance,created_at FROM cm_groups WHERE visibility='public' ORDER BY created_at"
    ).fetchall():
        hay = f"{g[1]} {g[2]} {g[3]}".lower()
        matched = [i for i in interests if i in hay]
        features = [f"interest:{i}" for i in matched]
        follow_handle = follow_handles.get(g[5]) if g[5] in follow_owners else None
        if follow_handle:
            features.append(f"follow:{follow_handle}")
        if not features:
            continue
        items.append(_why_chip({
            "kind": "group", "type": "group", "id": g[0], "group_id": g[0],
            "name": g[1], "handle": g[2], "description": g[3],
            "score": len(matched) * 2 + (1 if follow_handle else 0),
            "features_used": features, "why_this": _local_why(matched, follow_handle),
            "provenance": g[6], "as_of": g[7], "origin": "local",
        }))
        if len(items) >= limit:
            break
    return items


@router.get("/api/community/discovery")
def discovery(request: Request, limit: int = Query(default=20, ge=1, le=100)):
    store, owner = scope(request)
    with store.lock:
        setup_agents(store)
        from .recommender import rank_discovery

        prof = profile_by_owner(store, owner)
        interests = []
        if prof:
            try:
                interests = [str(i).strip().lower() for i in json.loads(prof[5] or "[]") if str(i).strip()]
            except Exception:
                interests = []
        follows = store.db.execute(
            "SELECT f.followee, p.handle FROM cm_follows f LEFT JOIN cm_profiles p ON p.owner=f.followee WHERE f.follower=?",
            (owner,),
        ).fetchall()
        follow_owners = {r[0] for r in follows}
        follow_handles = {r[0]: r[1] for r in follows if r[1]}

        ranked = rank_discovery(request, store, owner, limit=limit)
        items = list(ranked.get("items") or [])
        reason = ranked.get("reason")

        # Merge interest-matched public groups so Scene A / legacy discovery UX still
        # surfaces communities (rank_discovery is post-first).
        group_cards = _interest_matched_groups(
            store, owner, interests, follow_handles, follow_owners, limit=max(5, limit // 2),
        )
        if group_cards:
            seen = {it["id"] for it in items}
            merged = [g for g in group_cards if g["id"] not in seen] + items
            items = merged[:limit]
            if reason and "Cold start" in str(reason) and any(it.get("origin") == "local" for it in items):
                reason = None

        if not items:
            items = _cold_start_groups(store, limit)
            reason = (
                "Cold start: public communities, not personalised."
                if items
                else "Cold start: no public communities yet."
            )
            stamp = cm.now()
            for it in items:
                store.db.execute(
                    "INSERT INTO cm_recommendation_events (id,owner,candidate_type,candidate_id,features,why_this,reason,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (uuid4().hex, owner, it["kind"], it["id"], json.dumps([]), it.get("why_this") or "", reason or "", stamp),
                )
            if not items:
                store.db.execute(
                    "INSERT INTO cm_recommendation_events (id,owner,candidate_type,candidate_id,features,why_this,reason,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (uuid4().hex, owner, None, None, json.dumps([]), "", reason or "", stamp),
                )
            store.db.commit()

        source = _compat_discovery_source(items, [], reason)
        if reason and "Cold start" in str(reason):
            used: list[str] = []
        else:
            used = sorted({f for it in items for f in (it.get("features_used") or [])})
        for it in items:
            it.setdefault("why_chip", ranked.get("why_chip") or "Why this?")
        return {
            "items": items,
            "candidates": items,
            "reason": reason,
            "empty": len(items) == 0,
            "features_used": used,
            "source": source,
            "why_chip": ranked.get("why_chip") or "Why this?",
        }


# ---------------------------------------------------------------- Community Answer
@router.post("/api/community/answers/draft")
def create_draft(body: DraftIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup_agents(store)
        if body.capability_id not in REGISTERED_CAPABILITIES:
            raise HTTPException(400, "Unregistered capability")
        if not body.sources:
            raise HTTPException(400, "At least one source citation is required")
        sources = []
        for s in body.sources:
            if not _host_allowed(s.url):
                raise HTTPException(400, f"Source publisher host not allowlisted: {s.url}")
            sources.append({"title": s.title, "url": s.url, "publisher": s.publisher, "as_of": s.as_of})
        text = _draft_text(body)
        if not text:
            raise HTTPException(422, "Answer text is required")
        group_id = body.group_id
        if group_id:
            group = require_group(store, group_id)
            group_access(store, group, owner)
        destination = _destination(group_id, body.destination)
        did = uuid4().hex
        stamp = cm.now()
        snap = _snapshot(text, destination, group_id, sources, body.question, body.capability_id)
        store.db.execute(
            "INSERT INTO cm_answer_drafts (id,owner,question,text,group_id,destination,sources,capability_id,revision,snapshot_hash,status,post_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,1,?,'draft',NULL,?,?)",
            (did, owner, body.question, text, group_id, destination, json.dumps(sources), body.capability_id, snap, stamp, stamp))
        store.db.commit()
        return {"draft": _present_draft(_draft_row(store, did))}


@router.get("/api/community/answers/{draft_id}")
def get_draft(draft_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup_agents(store)
        row = _draft_row(store, draft_id)
        if not row or row[1] != owner:
            raise HTTPException(404, "Draft not found")
        return {"draft": _present_draft(row)}


def _edit_draft(draft_id, body: DraftEditIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup_agents(store)
        row = _draft_row(store, draft_id)
        if not row or row[1] != owner:
            raise HTTPException(404, "Draft not found")
        draft = _present_draft(row)
        if draft["status"] == "published":
            raise HTTPException(409, "A published answer cannot be edited; create a new draft")
        text = draft["text"]
        for v in (body.text, body.answer, body.answer_text, body.body, body.content):
            if v and v.strip():
                text = v.strip()
                break
        question = body.question if body.question is not None else draft["question"]
        group_id = body.group_id if body.group_id is not None else draft["group_id"]
        if group_id:
            group = require_group(store, group_id)
            group_access(store, group, owner)
        destination = _destination(group_id, body.destination if body.destination is not None else draft["destination"] if not group_id else None)
        if body.destination is not None and not group_id:
            destination = body.destination
        sources = draft["sources"]
        if body.sources is not None:
            if not body.sources:
                raise HTTPException(400, "At least one source citation is required")
            sources = []
            for s in body.sources:
                if not _host_allowed(s.url):
                    raise HTTPException(400, f"Source publisher host not allowlisted: {s.url}")
                sources.append({"title": s.title, "url": s.url, "publisher": s.publisher, "as_of": s.as_of})
        revision = draft["revision"] + 1
        snap = _snapshot(text, destination, group_id, sources, question, draft["capability_id"])
        store.db.execute(
            "UPDATE cm_answer_drafts SET text=?,question=?,group_id=?,destination=?,sources=?,revision=?,snapshot_hash=?,status='draft',updated_at=? WHERE id=?",
            (text, question, group_id, destination, json.dumps(sources), revision, snap, cm.now(), draft_id))
        store.db.commit()
        return {"draft": _present_draft(_draft_row(store, draft_id))}


@router.put("/api/community/answers/{draft_id}")
def edit_draft(draft_id: str, body: DraftEditIn, request: Request):
    return _edit_draft(draft_id, body, request)


@router.patch("/api/community/answers/{draft_id}")
def edit_draft_patch(draft_id: str, body: DraftEditIn, request: Request):
    return _edit_draft(draft_id, body, request)


@router.post("/api/community/answers/{draft_id}/approve")
def approve_draft(draft_id: str, body: ApproveIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup_agents(store)
        row = _draft_row(store, draft_id)
        if not row or row[1] != owner:
            raise HTTPException(404, "Draft not found")
        draft = _present_draft(row)
        capability_id = body.capability_id or draft["capability_id"]
        if capability_id not in REGISTERED_CAPABILITIES:
            raise HTTPException(400, "Unregistered capability")
        if capability_id != draft["capability_id"]:
            raise HTTPException(409, "Draft capability changed. Review the current draft.")
        # Idempotent replay: same exact approval already dispatched once.
        if draft["status"] == "published" and draft["post_id"]:
            if draft["revision"] == body.revision and draft["snapshot_hash"] == body.snapshot_hash:
                return {"draft": draft, "status": "published", "post_id": draft["post_id"],
                        "post": present_post(store, post_row(store, draft["post_id"]), owner),
                        "idempotent": True}
            raise HTTPException(409, "Draft changed. Review and approve the current details.")
        # Mirror actions.py:313 — exact revision + snapshot_hash only.
        if draft["snapshot_hash"] != body.snapshot_hash or draft["revision"] != body.revision:
            raise HTTPException(409, "Draft changed. Review and approve the current details.")
        # Publish via core post creation (registered capability executes).
        pid = _create_post(store, owner, draft["text"], draft["group_id"])
        store.db.execute(
            "UPDATE cm_answer_drafts SET status='published', post_id=?, updated_at=? WHERE id=?",
            (pid, cm.now(), draft_id))
        store.db.execute(
            "INSERT OR IGNORE INTO cm_answer_approvals (draft_id,owner,revision,snapshot_hash,post_id,created_at) VALUES (?,?,?,?,?,?)",
            (draft_id, owner, draft["revision"], draft["snapshot_hash"], pid, cm.now()))
        store.db.commit()
        updated = _present_draft(_draft_row(store, draft_id))
        return {"draft": updated, "status": "published", "post_id": pid,
                "post": present_post(store, post_row(store, pid), owner), "idempotent": False}


# ---------------------------------------------------------------- Group Organizer (D14)
@router.post("/api/community/groups/{group_id}/organizer/propose")
def propose(group_id: str, body: ProposeIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup_agents(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        if not is_active_member(store, group_id, owner):
            raise HTTPException(403, "Only group members can propose")
        # Proposals only: no notify(), no invites, no outbound contact (D14).
        pid = uuid4().hex
        store.db.execute(
            "INSERT INTO cm_organizer_proposals (id,group_id,owner,title,checklist,status,created_at) VALUES (?,?,?,?,?,'proposed',?)",
            (pid, group_id, owner, body.title.strip(), json.dumps(body.checklist), cm.now()))
        store.db.commit()
        row = store.db.execute(
            "SELECT id,group_id,owner,title,checklist,status,created_at FROM cm_organizer_proposals WHERE id=?", (pid,)).fetchone()
        return {"proposal": _present_proposal(row)}


def _present_proposal(row):
    return {"id": row[0], "group_id": row[1], "owner": row[2], "proposed_by": row[2],
            "title": row[3], "checklist": json.loads(row[4] or "[]"), "status": row[5],
            "created_at": row[6], "as_of": row[6], "provenance": "user_supplied"}


@router.get("/api/community/groups/{group_id}/organizer/proposals")
def list_proposals(group_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup_agents(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        if group[4] == "private" and not is_active_member(store, group_id, owner):
            raise HTTPException(404, "Group not found")
        rows = store.db.execute(
            "SELECT id,group_id,owner,title,checklist,status,created_at FROM cm_organizer_proposals WHERE group_id=? ORDER BY created_at, id",
            (group_id,)).fetchall()
        return {"proposals": [_present_proposal(r) for r in rows]}


# ---------------------------------------------------------------- Moderation Copilot hook
@router.post("/api/community/copilot/flag")
def copilot_flag(body: FlagIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup_agents(store)
        require_visible_post(store, owner, body.post_id)
        fid = uuid4().hex
        store.db.execute("INSERT INTO cm_copilot_flags (id,post_id,owner,label,created_at) VALUES (?,?,?,?,?)",
                         (fid, body.post_id, owner, body.label.strip(), cm.now()))
        store.db.commit()
        row = store.db.execute("SELECT id,post_id,owner,label,created_at FROM cm_copilot_flags WHERE id=?", (fid,)).fetchone()
        # Never hides: the post is untouched.
        return {"flag": {"id": row[0], "post_id": row[1], "owner": row[2], "label": row[3],
                         "created_at": row[4], "as_of": row[4]},
                "post_hidden": False, "hidden": False}


@router.get("/api/community/copilot/flags")
def list_flags(request: Request, post_id: str | None = Query(default=None)):
    store, owner = scope(request)
    with store.lock:
        setup_agents(store)
        if post_id:
            rows = store.db.execute("SELECT id,post_id,owner,label,created_at FROM cm_copilot_flags WHERE post_id=? ORDER BY created_at", (post_id,)).fetchall()
        else:
            rows = store.db.execute("SELECT id,post_id,owner,label,created_at FROM cm_copilot_flags ORDER BY created_at").fetchall()
        return {"flags": [{"id": r[0], "post_id": r[1], "owner": r[2], "label": r[3], "created_at": r[4]} for r in rows]}
