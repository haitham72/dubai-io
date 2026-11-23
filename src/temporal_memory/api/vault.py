"""FastAPI Vault, Quests, Timeline, Why, and Hypotheses endpoints (WP-B)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
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
