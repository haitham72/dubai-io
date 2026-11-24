"""FastAPI Vault, Quests, Timeline, Why, and Hypotheses endpoints (WP-B)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from typing import Any, Callable, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Path as FPath, Query

from temporal_memory.models import Attempt, Entity, EntitySubject, Fact, GraphStore, Link, Milestone, Subject

Role = Literal["admin", "worker", "owner-device"]


@dataclass
class AuthContext:
    role: Role
    owner: str | None = None
    token_id: str = ""


_STORE: GraphStore | None = None
_AUTH_VERIFIER: Callable[[str | None], AuthContext | None] | None = None


def configure(
    *,
    store: GraphStore | None = None,
    auth_verifier: Callable[[str | None], AuthContext | None] | None = None,
) -> None:
    """Wire the process-level GraphStore and token verifier (called by api/app.py or tests)."""
    global _STORE, _AUTH_VERIFIER
    if store is not None:
        _STORE = store
    if auth_verifier is not None:
        _AUTH_VERIFIER = auth_verifier


def get_store() -> GraphStore:
    if _STORE is None:
        raise HTTPException(status_code=503, detail="GraphStore not configured")
    return _STORE


def get_auth(authorization: str | None = Header(default=None)) -> AuthContext:
    if _AUTH_VERIFIER is None:
        raise HTTPException(status_code=401, detail="Auth verifier not configured")
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    ctx = _AUTH_VERIFIER(token)
    if ctx is None:
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")
    return ctx


def require_owner_access(owner: str = FPath(...), auth: AuthContext = Depends(get_auth)) -> AuthContext:
    if auth.role == "owner-device" and auth.owner != owner:
        raise HTTPException(status_code=403, detail="owner-device token scoped to a different owner")
    return auth


def require_admin(auth: AuthContext = Depends(get_auth)) -> AuthContext:
    if auth.role != "admin":
        raise HTTPException(status_code=403, detail="Admin token required")
    return auth


def call_opt(store: Any, name: str, *args: Any, default: Any = None, **kwargs: Any) -> Any:
    fn = getattr(store, name, None)
    return fn(*args, **kwargs) if callable(fn) else default


def _meta(store: Any, owner: str) -> tuple[str, bool]:
    now_iso = datetime.now(timezone.utc).isoformat()
    owner_obj = call_opt(store, "get_owner", owner, default=None)
    return now_iso, bool(owner_obj and owner_obj.kind == "demo")


router = APIRouter(prefix="/v1/owners/{owner}", tags=["vault"])


@router.get("/vault/subjects")
def vault_subjects(
    owner: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    facts: list[Fact] = store.visible_facts(owner, limit=10_000)
    subjects: list[Subject] = call_opt(store, "list_subjects", owner, default=[])

    direct_counts: dict[str, int] = defaultdict(int)
    for f in facts:
        if f.status != "history":
            direct_counts[f.subject_id] += 1

    children_map: dict[str | None, list[Subject]] = defaultdict(list)
    by_id: dict[str, Subject] = {s.id: s for s in subjects}
    for s in subjects:
        children_map[s.parent_id].append(s)

    def _build(node: Subject) -> dict[str, Any]:
        kids = [_build(c) for c in sorted(children_map.get(node.id, []), key=lambda x: x.label)]
        total = direct_counts[node.id] + sum(k["fact_count"] for k in kids)
        return {
            "id": node.id,
            "path": node.path,
            "label": node.label,
            "kind": node.kind,
            "status": node.status,
            "salience": node.salience,
            "fact_count": total,
            "direct_fact_count": direct_counts[node.id],
            "provenance": "user_supplied" if node.status == "active" else "inferred",
            "as_of": now_iso,
            "demo_data": is_demo,
            "children": kids,
        }

    roots = [_build(s) for s in sorted(children_map.get(None, []), key=lambda x: x.label)]
    # Fallback for nodes whose parent_id isn't in by_id
    orphan_roots = [
        _build(s)
        for s in sorted(subjects, key=lambda x: x.path)
        if s.parent_id is not None and s.parent_id not in by_id
    ]
    themes = roots + orphan_roots
    return {
        "owner": owner,
        "themes": themes,
        "total_facts": sum(direct_counts.values()),
        "provenance": "user_supplied",
        "as_of": now_iso,
        "demo_data": is_demo,
    }


@router.get("/vault/people")
def vault_people(
    owner: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    entities: list[Entity] = call_opt(store, "list_entities", owner, default=[])
    links: list[Link] = call_opt(store, "list_links", owner, default=[])
    ent_subjs: list[EntitySubject] = call_opt(store, "list_entity_subjects", owner, default=[])
    subjects = {s.id: s for s in call_opt(store, "list_subjects", owner, default=[])}
    visible_fids = {f.id for f in store.visible_facts(owner, limit=10_000)}

    es_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for es in ent_subjs:
        es_map[es.entity_id].append({
            "subject_id": es.subject_id,
            "subject": subjects[es.subject_id].label if es.subject_id in subjects else es.subject_id,
            "role": es.role,
            "fact_count": es.fact_count,
            "weight": es.weight,
        })

    def _ser(e: Entity) -> dict[str, Any]:
        return {
            "id": e.id,
            "kind": e.kind,
            "name": e.name,
            "status": e.status,
            "relation_to_user": e.relation_to_user,
            "closeness_tier": e.closeness_tier,
            "aliases": e.aliases,
            "salience": e.salience,
            "first_seen": e.first_seen,
            "last_seen": e.last_seen,
            "subjects": es_map.get(e.id, []),
            "provenance": "user_supplied" if e.status == "active" else "inferred",
            "as_of": e.last_seen or now_iso,
            "demo_data": is_demo,
        }

    people = [_ser(e) for e in entities if e.kind == "person" and e.status != "merged"]
    places = [_ser(e) for e in entities if e.kind == "place" and e.status != "merged"]
    orgs = [_ser(e) for e in entities if e.kind == "org" and e.status != "merged"]
    vis_links = [
        {
            "id": ln.id, "src": ln.src, "rel": ln.rel, "dst": ln.dst,
            "valid_from": ln.valid_from, "valid_to": ln.valid_to,
            "provenance": "inferred", "as_of": ln.valid_from or now_iso, "demo_data": is_demo,
        }
        for ln in links
        if ln.evidence_fact_id is None or ln.evidence_fact_id in visible_fids
    ]
    return {
        "owner": owner,
        "people": people,
        "places": places,
        "orgs": orgs,
        "links": vis_links,
        "provenance": "user_supplied",
        "as_of": now_iso,
        "demo_data": is_demo,
    }


@router.get("/quests")
def quests(
    owner: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    subjects: list[Subject] = call_opt(store, "list_subjects", owner, default=[])
    milestones: list[Milestone] = call_opt(store, "list_milestones", owner, default=[])
    visible_ids = {f.id for f in store.visible_facts(owner, limit=10_000)}

    ms_by_subj: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in milestones:
        kept_ev = [fid for fid in m.evidence_fact_ids if fid in visible_ids]
        if m.evidence_fact_ids and not kept_ev:
            continue  # all supporting evidence forgotten
        ms_by_subj[m.subject_id].append({
            "id": m.id,
            "title": m.title,
            "state": m.state,
            "evidence_fact_ids": kept_ev,
            "provenance": "inferred",
            "hypothesis_label": "I noticed…",
            "actions": ["Confirm", "Edit", "Not true", "Forget"],
            "as_of": now_iso,
            "demo_data": is_demo,
        })

    goal_cards: list[dict[str, Any]] = []
    for s in subjects:
        if s.kind != "goal":
            continue
        ms_list = ms_by_subj.get(s.id, [])
        goal_cards.append({
            "id": s.id,
            "path": s.path,
            "label": s.label,
            "status": s.status,
            "hypothesis_label": "I noticed…" if s.status == "candidate" else None,
            "milestones": ms_list,
            "counts": {
                st: sum(1 for m in ms_list if m["state"] == st)
                for st in ("done", "in_progress", "planned")
            },
            "provenance": "user_supplied" if s.status == "active" else "inferred",
            "as_of": now_iso,
            "demo_data": is_demo,
        })
    return {"owner": owner, "quests": goal_cards, "provenance": "inferred", "as_of": now_iso, "demo_data": is_demo}


@router.get("/hypotheses")
def hypotheses(
    owner: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    hyps = [f for f in store.visible_facts(owner, limit=10_000) if f.status == "hypothesis"]
    return {
        "owner": owner,
        "hypotheses": [
            {
                "id": f.id,
                "text": f.text if f.text.startswith("I noticed") else f"I noticed {f.text}",
                "subject_id": f.subject_id,
                "evidence": f.evidence,
                "valid_from": f.valid_from,
                "provenance": f.provenance,
                "as_of": f.valid_from or now_iso,
                "actions": ["Confirm", "Edit", "Not true", "Forget"],
                "demo_data": is_demo or f.provenance == "demo_fixture",
            }
            for f in hyps
        ],
        "provenance": "inferred",
        "as_of": now_iso,
        "demo_data": is_demo,
    }


@router.get("/timeline")
def timeline(
    owner: str,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    facts = [
        f
        for f in store.visible_facts(owner, limit=10_000)
        if f.status != "history"
        and (not date_from or (f.valid_from or "") >= date_from)
        and (not date_to or (f.valid_from or "") <= date_to)
    ]
    facts.sort(key=lambda x: (x.valid_from or "", x.id), reverse=True)
    return {
        "owner": owner,
        "items": [
            {
                "id": f.id,
                "text": f.text,
                "text_orig": f.text_orig,
                "subject_id": f.subject_id,
                "valid_from": f.valid_from,
                "valid_to": f.valid_to,
                "status": f.status,
                "superseded_by": f.superseded_by,
                "provenance": f.provenance,
                "as_of": f.valid_from or now_iso,
                "demo_data": is_demo or f.provenance == "demo_fixture",
            }
            for f in facts[:limit]
        ],
        "provenance": "user_supplied",
        "as_of": now_iso,
        "demo_data": is_demo,
    }


# ---------------------------------------------------------------------------
# Onboarding status & user analytics (D-C)
# Canonical completeness weights (gamified-onboarding-and-analytics.md §3):
# gmail 14 + calendar 10 + youtube_api 12 = 36% mobile base.
SOURCE_WEIGHTS: dict[str, int] = {
    "gmail": 14, "calendar": 10, "youtube_api": 12,
    "whatsapp": 15, "youtube_history": 12, "browser": 18, "agent_sessions": 19,
}
LIFE_SPINES = ["Career", "Learning", "Projects", "People & family",
               "Events", "Home & money", "Travel"]
_SPINE_BY_ROOT = {
    "career": "Career", "work": "Career", "learning": "Learning",
    "education": "Learning", "projects": "Projects", "project": "Projects",
    "family": "People & family", "people": "People & family",
    "relationships": "People & family", "lifestyle": "Events",
    "events": "Events", "social": "Events", "life": "Events",
    "money": "Home & money", "finance": "Home & money", "home": "Home & money",
    "travel": "Travel", "places": "Travel",
}


def _canonical_source(source: str) -> str | None:
    s = (source or "").strip().lower()
    if s == "gmail" or s.startswith("gmail:"):
        return "gmail"
    if s.startswith(("calendar", "gcal", "google:calendar")):
        return "calendar"
    if s.startswith(("youtube:api", "youtube_api", "youtube-api")):
        return "youtube_api"
    if s.startswith("whatsapp"):
        return "whatsapp"
    if s in ("youtube:interests", "takeout:youtube"):
        return "youtube_history"
    if s in ("browser", "takeout:chrome"):
        return "browser"
    if s.startswith(("agent:", "ai:chatgpt")) or s in ("dev_sessions", "takeout:gemini-apps"):
        return "agent_sessions"
    return None


def _source_bucket(source: str) -> str:
    s = (source or "").strip()
    if s.lower().startswith("whatsapp"):
        return "whatsapp"
    return s


def _list_opt(store: Any, name: str) -> list:
    fn = getattr(store, name, None)
    if not callable(fn):
        return []
    try:
        return list(fn())
    except TypeError:
        return []


def _owner_records(store: Any, owner: str, facts: list) -> list:
    """Raw records for by_source counts: portable across Fake and Postgres stores."""
    fn = getattr(store, "list_records", None)
    if callable(fn):
        try:
            return list(fn(owner))
        except TypeError:
            pass
    records_attr = getattr(store, "records", None)
    if isinstance(records_attr, dict):  # FakeGraphStore
        return list(records_attr.get(owner, {}).values())
    db = getattr(store, "db", None)
    if db is not None:  # PostgresGraphStore
        try:
            with db.connection() as conn:
                rows = conn.execute(
                    "SELECT id, source FROM records WHERE owner = %s AND erased_at IS NULL",
                    (owner,),
                ).fetchall()
            return [{"id": r["id"], "source": r["source"]} for r in rows]
        except Exception:
            pass
    # Fallback: records referenced by visible facts (extracted evidence only).
    ids = sorted({rid for f in facts for rid in (f.evidence or [])})
    return call_opt(store, "get_records", owner, ids, default=[]) if ids else []


def _record_source(record: Any) -> str:
    return record["source"] if isinstance(record, dict) else getattr(record, "source", "")


def _record_id(record: Any) -> str:
    return record["id"] if isinstance(record, dict) else getattr(record, "id", "")


@router.get("/onboarding-status")
def onboarding_status(
    owner: str,
    as_of: str | None = Query(default=None),
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    # Verified facts only: history and unconfirmed hypotheses never count here.
    facts = [f for f in store.visible_facts(owner, limit=10_000) if f.status == "active"]
    subjects = call_opt(store, "list_subjects", owner, default=[])
    subj_by_id = {s.id: s for s in subjects}

    def spine_for(subject_id: str) -> str:
        node = subj_by_id.get(subject_id)
        seen: set[str] = set()
        while node is not None and node.parent_id and node.parent_id not in seen:
            seen.add(node.id)
            node = subj_by_id.get(node.parent_id)
        if node is None:
            return "Other"
        root_key = (node.path or node.label or "").split("/")[0].strip().lower()
        return _SPINE_BY_ROOT.get(root_key, "Other")

    records = _owner_records(store, owner, facts)
    rec_by_id = {_record_id(r): r for r in records}

    # --- completeness (deterministic, presence-based, counted once per source)
    present = sorted(
        {c for c in (_canonical_source(_record_source(r)) for r in records) if c},
        key=lambda c: list(SOURCE_WEIGHTS).index(c),
    )
    completeness = min(100, sum(SOURCE_WEIGHTS[c] for c in present))
    breakdown = {k: (w if k in present else 0) for k, w in SOURCE_WEIGHTS.items()}
    desktop_present = [c for c in ("browser", "agent_sessions") if c in present]
    if completeness >= 100:
        next_action: str | None = "complete"
    elif len(desktop_present) == 1:
        next_action = "enable_browser_or_sessions"
    elif not desktop_present:
        next_action = "install_desktop_and_sync"
    else:
        next_action = "add_whatsapp_or_youtube_history"

    # --- by_source: record counts (raw) + fact counts (via evidence)
    by_source: dict[str, dict[str, int]] = defaultdict(lambda: {"records": 0, "facts": 0})
    for r in records:
        by_source[_source_bucket(_record_source(r))]["records"] += 1
    fact_sources: dict[str, set[str]] = defaultdict(set)
    for f in facts:
        for rid in f.evidence or []:
            rec = rec_by_id.get(rid)
            if rec is not None:
                fact_sources[_source_bucket(_record_source(rec))].add(f.id)
    for bucket, fids in fact_sources.items():
        by_source[bucket]["facts"] = len(fids)

    # --- known_so_far: top verified (active) facts grouped by life spine
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for f in facts:
        if f.status != "active":
            continue
        grouped[spine_for(f.subject_id)].append({
            "id": f.id, "text": f.text, "subject_id": f.subject_id,
            "valid_from": f.valid_from, "evidence": list(f.evidence or []),
            "provenance": f.provenance, "as_of": f.valid_from or now_iso,
        })
    known_so_far = {
        theme: sorted(items, key=lambda x: (x["valid_from"] or "", x["id"]), reverse=True)[:5]
        for theme, items in sorted(grouped.items()) if items
    }

    # --- by_theme + rising_21d (anchored at latest fact date or ?as_of=)
    def _parse_day(value: str | None):
        try:
            return datetime.fromisoformat(str(value)[:10]).date()
        except (ValueError, TypeError):
            return None

    anchor = _parse_day(as_of) or max(
        (d for d in (_parse_day(f.valid_from) for f in facts) if d), default=None)
    by_theme: dict[str, dict[str, Any]] = {
        spine: {"facts": 0, "recent_21d": 0, "baseline_21d": 0, "delta": 0, "rising_21d": False}
        for spine in LIFE_SPINES
    }
    for f in facts:
        spine = spine_for(f.subject_id)
        if spine not in by_theme:
            continue
        by_theme[spine]["facts"] += 1
        day = _parse_day(f.valid_from)
        if anchor is not None and day is not None:
            age = (anchor - day).days
            if 0 <= age < 21:
                by_theme[spine]["recent_21d"] += 1
            elif 21 <= age < 42:
                by_theme[spine]["baseline_21d"] += 1
    rising = []
    for spine, stats in by_theme.items():
        stats["delta"] = stats["recent_21d"] - stats["baseline_21d"]
        stats["rising_21d"] = stats["recent_21d"] > stats["baseline_21d"]
        if stats["rising_21d"]:
            rising.append(spine)

    # --- privacy shield: quarantine counts only, never raw text
    quarantine: dict[str, int] = call_opt(store, "get_quarantine_counts", owner, default={}) or {}

    # --- compute saved (owner-hook / agent-cli, scoped to this owner's jobs)
    jobs = _list_opt(store, "list_jobs")
    attempts = _list_opt(store, "list_attempts")
    owner_job_ids = {j.id for j in jobs if getattr(j, "owner", owner) == owner}
    rate_in = float(os.environ.get("TM_CLOUD_RATE_IN_PER_1M", "1.00"))
    rate_out = float(os.environ.get("TM_CLOUD_RATE_OUT_PER_1M", "5.00"))
    tokens_in = tokens_out = 0
    saved_usd = 0.0
    for a in attempts:
        if owner_job_ids and a.job_id not in owner_job_ids:
            continue
        if a.worker_kind in ("owner-hook", "agent-cli"):
            tokens_in += a.tokens_in or 0
            tokens_out += a.tokens_out or 0
            saved_usd += (a.tokens_in / 1_000_000.0) * rate_in + (a.tokens_out / 1_000_000.0) * rate_out
    owner_hook_facts = 0
    for f in facts:
        if not f.attempt_id:
            continue
        attempt = call_opt(store, "get_attempt", f.attempt_id, default=None)
        if attempt is not None and attempt.worker_kind == "owner-hook":
            owner_hook_facts += 1

    return {
        "owner": owner,
        "completeness_pct": completeness,
        "breakdown": breakdown,
        "sources_present": present,
        "next_recommended_action": next_action,
        "known_so_far": known_so_far,
        "analytics": {
            "by_source": {k: dict(v) for k, v in sorted(by_source.items())},
            "by_theme": by_theme,
            "rising_21d": rising,
            "privacy_shield": {
                "held_back_total": sum(int(v) for v in quarantine.values()),
                "by_category": {k: int(v) for k, v in sorted(quarantine.items())},
            },
            "compute_saved": {
                "owner_hook_facts": owner_hook_facts,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "demo_cost_saved_usd": round(saved_usd, 6),
            },
        },
        "provenance": "user_supplied",
        "as_of": as_of or now_iso,
        "demo_data": is_demo,
    }


@router.get("/why/{fact_id}")
def why_fact(
    owner: str,
    fact_id: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    facts = {f.id: f for f in store.visible_facts(owner, limit=10_000)}
    fact = facts.get(fact_id)
    if fact is None:
        raise HTTPException(status_code=404, detail="Fact not found or forgotten")

    records = call_opt(store, "get_records", owner, fact.evidence, default=[])
    attempt: Attempt | None = call_opt(store, "get_attempt", fact.attempt_id, default=None) if fact.attempt_id else None
    is_owner_hook = bool(attempt and attempt.worker_kind == "owner-hook")
    model_label = "your Claude" if is_owner_hook else (fact.model or (attempt.model if attempt else None) or "unknown")

    return {
        "owner": owner,
        "fact_id": fact.id,
        "text": fact.text,
        "text_orig": fact.text_orig,
        "status": fact.status,
        "valid_from": fact.valid_from,
        "job_id": fact.job_id,
        "attempt_id": fact.attempt_id,
        "model": model_label,
        "cost_badge": "processed on your Claude · $0 app cost" if is_owner_hook else None,
        "evidence": [
            {
                "id": r.id,
                "source": r.source,
                "at": r.at,
                "author": r.author,
                "text": r.text,
                "provenance": "user_supplied",
                "as_of": r.at,
            }
            for r in records
        ],
        "provenance": fact.provenance,
        "as_of": fact.valid_from or now_iso,
        "demo_data": is_demo or fact.provenance == "demo_fixture",
    }

