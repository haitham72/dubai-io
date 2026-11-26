"""FastAPI Vault, Quests, Timeline, Why, and Hypotheses endpoints (WP-B + U1c SQL reads)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from typing import Any, Callable, Iterable, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Path as FPath, Query

from temporal_memory.models import (
    CLUSTER_LABELS,
    CLUSTERS,
    HELD_BACK_ROOTS,
    Attempt,
    Entity,
    EntitySubject,
    Fact,
    GraphStore,
    Link,
    Milestone,
    Subject,
)

Role = Literal["admin", "worker", "owner-device"]

_HELD_BACK_ROOTS = frozenset(HELD_BACK_ROOTS)


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
    if auth.role != "admin" and not (auth.role == "owner-device" and auth.owner == owner):
        raise HTTPException(status_code=403, detail="owner access required")
    from temporal_memory.privacy.controls import account_deleted
    if account_deleted(get_store(), owner):
        raise HTTPException(status_code=403, detail="Account data has been deleted")
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


def _review_state(provenance: str, is_demo: bool) -> str:
    if is_demo or provenance == "demo_fixture":
        return "demo"
    if provenance in ("user_supplied", "provider_confirmed"):
        return "confirmed"
    return "pending_review"


def _envelope_provenance(values: Iterable[str], *, is_demo: bool, default: str = "inferred") -> str:
    if is_demo:
        return "demo_fixture"
    uniq = {v for v in values if v}
    if not uniq:
        return default
    if uniq <= {"user_supplied", "provider_confirmed"}:
        return "user_supplied"
    return "inferred"


def _is_sensitive_subject(subj: Subject | None) -> bool:
    if subj is None:
        return False
    root = (subj.path or "").split("/")[0].strip().lower()
    return subj.sensitive_cat is not None or root in _HELD_BACK_ROOTS


def _iter_all_visible(store: Any, owner: str, *, date_from: str | None = None, date_to: str | None = None) -> list[Fact]:
    iter_fn = getattr(store, "iter_visible_facts", None)
    if callable(iter_fn):
        return [f for f in iter_fn(owner, date_from=date_from, date_to=date_to, page_size=500) if f.status != "history"]
    return [
        f
        for f in store.visible_facts(owner, limit=200)
        if f.status != "history"
        and (not date_from or (f.valid_from or "")[:10] >= date_from[:10])
        and (not date_to or (f.valid_from or "")[:10] <= date_to[:10])
    ]


def _visible_id_set(store: Any, owner: str, fact_ids: list[str]) -> set[str]:
    clean = list(dict.fromkeys(fid for fid in fact_ids if fid))
    if not clean:
        return set()
    sub_fn = getattr(store, "visible_fact_ids_subset", None)
    if callable(sub_fn):
        return set(sub_fn(owner, clean))
    get_fn = getattr(store, "get_facts", None)
    if callable(get_fn):
        return {f.id for f in get_fn(owner, clean)}
    return {f.id for f in _iter_all_visible(store, owner) if f.id in set(clean)}


router = APIRouter(prefix="/v1/owners/{owner}", tags=["vault"])


@router.get("/vault/subjects")
def vault_subjects(
    owner: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    subjects: list[Subject] = call_opt(store, "list_subjects", owner, default=[])
    counts_fn = getattr(store, "fact_counts_by_subject", None)
    if callable(counts_fn):
        direct_counts: dict[str, int] = defaultdict(int, counts_fn(owner))
    else:
        direct_counts = defaultdict(int)
        for f in _iter_all_visible(store, owner):
            direct_counts[f.subject_id] += 1

    conf_fn = getattr(store, "confirmed_fact_counts_by_subject", None)
    confirmed_counts: dict[str, int] | None = (
        dict(conf_fn(owner)) if callable(conf_fn) else None
    )
    if confirmed_counts is None:
        confirmed_counts = defaultdict(int)
        for f in _iter_all_visible(store, owner):
            if f.provenance in ("user_supplied", "provider_confirmed"):
                confirmed_counts[f.subject_id] += 1

    sal_map: dict[str, float] = call_opt(store, "subject_salience_map", owner, default={}) or {}

    children_map: dict[str | None, list[Subject]] = defaultdict(list)
    by_id: dict[str, Subject] = {s.id: s for s in subjects}
    for s in subjects:
        children_map[s.parent_id].append(s)

    from temporal_memory.privacy.controls import subject_states
    weights = subject_states(store, owner)
    collected_provs: list[str] = []

    def _build(node: Subject, *, parent_sensitive: bool = False) -> dict[str, Any] | None:
        is_sens = parent_sensitive or _is_sensitive_subject(node)
        kids: list[dict[str, Any]] = []
        for c in sorted(children_map.get(node.id, []), key=lambda x: x.label):
            built = _build(c, parent_sensitive=is_sens)
            if built is not None:
                kids.append(built)

        if is_sens:
            own_cnt = confirmed_counts.get(node.id, 0)
            if own_cnt == 0 and not kids:
                return None
        else:
            own_cnt = direct_counts[node.id]

        total = own_cnt + sum(k["fact_count"] for k in kids)
        prov = getattr(node, "provenance", "inferred") or "inferred"
        collected_provs.append(prov)
        return {
            "id": node.id,
            "path": node.path,
            "label": node.label,
            "kind": node.kind,
            "status": node.status,
            "salience": sal_map.get(node.id, node.salience),
            **weights.get(node.id, {}),
            "fact_count": total,
            "direct_fact_count": own_cnt,
            "sensitive_cat": node.sensitive_cat,
            "provenance": prov,
            "review_state": _review_state(prov, is_demo),
            "as_of": now_iso,
            "demo_data": is_demo,
            "children": kids,
        }

    roots = [
        item
        for s in sorted(children_map.get(None, []), key=lambda x: x.label)
        if (item := _build(s)) is not None
    ]
    orphan_roots = [
        item
        for s in sorted(subjects, key=lambda x: x.path)
        if s.parent_id is not None and s.parent_id not in by_id
        if (item := _build(s)) is not None
    ]
    themes = roots + orphan_roots
    total_facts = sum(t["fact_count"] for t in themes)
    return {
        "owner": owner,
        "themes": themes,
        "total_facts": total_facts,
        "provenance": _envelope_provenance(collected_provs, is_demo=is_demo),
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
    vis_eids: set[str] | None = call_opt(store, "visible_entity_ids", owner, default=None)
    sal_map: dict[str, float] = call_opt(store, "entity_salience_map", owner, default={}) or {}

    link_ev_map: dict[str, list[str]] = call_opt(store, "list_link_evidence_map", owner, default={}) or {}
    all_link_fids: list[str] = []
    for ln in links:
        if ln.evidence_fact_id:
            all_link_fids.append(ln.evidence_fact_id)
        all_link_fids.extend(link_ev_map.get(ln.id, []))
    vis_link_fids = _visible_id_set(store, owner, all_link_fids)
    ev_facts_by_id: dict[str, Fact] = {
        f.id: f for f in (call_opt(store, "get_facts", owner, list(vis_link_fids), default=[]) or [])
    }

    es_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for es in ent_subjs:
        subj = subjects.get(es.subject_id)
        if _is_sensitive_subject(subj):
            continue
        es_map[es.entity_id].append({
            "subject_id": es.subject_id,
            "subject": subj.label if subj else es.subject_id,
            "role": es.role,
            "fact_count": es.fact_count,
            "weight": es.weight,
        })

    def _keep_entity(e: Entity) -> bool:
        if e.status == "merged":
            return False
        prov = getattr(e, "provenance", "inferred") or "inferred"
        if e.relation_to_user == "self" or prov in ("user_supplied", "provider_confirmed"):
            return True
        if vis_eids is not None:
            return e.id in vis_eids
        return e.id in es_map or e.status == "active"

    def _ser(e: Entity) -> dict[str, Any]:
        prov = getattr(e, "provenance", "inferred") or "inferred"
        return {
            "id": e.id,
            "kind": e.kind,
            "name": e.name,
            "status": e.status,
            "relation_to_user": e.relation_to_user,
            "closeness_tier": e.closeness_tier,
            "closeness_suggested": getattr(e, "closeness_suggested", None),
            "closeness_suggested_evidence": getattr(e, "closeness_suggested_evidence", None),
            "aliases": e.aliases,
            "salience": sal_map.get(e.id, e.salience),
            "first_seen": e.first_seen,
            "last_seen": e.last_seen,
            "subjects": es_map.get(e.id, []),
            "provenance": prov,
            "review_state": _review_state(prov, is_demo),
            "as_of": e.last_seen or now_iso,
            "demo_data": is_demo,
        }

    kept = [e for e in entities if _keep_entity(e)]
    kept_by_id = {e.id: e for e in kept}

    people = [_ser(e) for e in kept if e.kind == "person"]
    places = [_ser(e) for e in kept if e.kind == "place"]
    orgs = [_ser(e) for e in kept if e.kind == "org"]
    projects = [_ser(e) for e in kept if e.kind == "project"]
    events = [_ser(e) for e in kept if e.kind == "event"]

    vis_links: list[dict[str, Any]] = []
    for ln in links:
        if ln.src not in kept_by_id or ln.dst not in kept_by_id:
            continue
        ev_ids = [
            fid
            for fid in dict.fromkeys(([ln.evidence_fact_id] if ln.evidence_fact_id else []) + link_ev_map.get(ln.id, []))
            if fid in vis_link_fids
        ]
        if not ev_ids:
            continue
        is_family_link = (
            ln.rel == "FAMILY_OF"
            or kept_by_id[ln.src].relation_to_user == "family"
            or kept_by_id[ln.dst].relation_to_user == "family"
        )
        ev_provs = [ev_facts_by_id[fid].provenance for fid in ev_ids if fid in ev_facts_by_id]
        if is_family_link and not any(p in ("user_supplied", "provider_confirmed") for p in ev_provs):
            continue
        ln_prov = _envelope_provenance(ev_provs, is_demo=is_demo)
        vis_links.append({
            "id": ln.id,
            "src": ln.src,
            "rel": ln.rel,
            "dst": ln.dst,
            "valid_from": ln.valid_from,
            "valid_to": ln.valid_to,
            "evidence_fact_ids": ev_ids,
            "provenance": ln_prov,
            "review_state": _review_state(ln_prov, is_demo),
            "as_of": ln.valid_from or now_iso,
            "demo_data": is_demo,
        })

    all_provs = [*(p["provenance"] for p in people + places + orgs), *(ln["provenance"] for ln in vis_links)]
    return {
        "owner": owner,
        "people": people,
        "places": places,
        "orgs": orgs,
        "projects": projects,
        "events": events,
        "links": vis_links,
        "provenance": _envelope_provenance(all_provs, is_demo=is_demo),
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
    all_ev_ids = [fid for m in milestones for fid in (m.evidence_fact_ids or [])]
    visible_ids = _visible_id_set(store, owner, all_ev_ids)

    ms_by_subj: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in milestones:
        kept_ev = [fid for fid in m.evidence_fact_ids if fid in visible_ids]
        if m.evidence_fact_ids and not kept_ev:
            continue
        ms_by_subj[m.subject_id].append({
            "id": m.id,
            "title": m.title,
            "state": m.state,
            "evidence_fact_ids": kept_ev,
            "provenance": "inferred",
            "review_state": _review_state("inferred", is_demo),
            "hypothesis_label": "I noticed…",
            "actions": ["Confirm", "Edit", "Not true", "Forget"],
            "as_of": now_iso,
            "demo_data": is_demo,
        })

    goal_cards: list[dict[str, Any]] = []
    for s in subjects:
        if s.kind != "goal" or _is_sensitive_subject(s):
            continue
        ms_list = ms_by_subj.get(s.id, [])
        prov = getattr(s, "provenance", "inferred") or "inferred"
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
            "provenance": prov,
            "review_state": _review_state(prov, is_demo),
            "as_of": now_iso,
            "demo_data": is_demo,
        })
    return {
        "owner": owner,
        "quests": goal_cards,
        "provenance": _envelope_provenance((c["provenance"] for c in goal_cards), is_demo=is_demo),
        "as_of": now_iso,
        "demo_data": is_demo,
    }


@router.get("/hypotheses")
def hypotheses(
    owner: str,
    limit: int = Query(default=200, ge=1, le=500),
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    list_fn = getattr(store, "list_hypotheses", None)
    if callable(list_fn):
        hyps: list[Fact] = list_fn(owner, limit=limit)
    else:
        subjects = {s.id: s for s in call_opt(store, "list_subjects", owner, default=[])}
        hyps = [
            f
            for f in _iter_all_visible(store, owner)
            if f.status == "hypothesis" and not _is_sensitive_subject(subjects.get(f.subject_id))
        ][:limit]

    from temporal_memory.privacy.controls import fact_states
    weights = fact_states(store, owner, [f.id for f in hyps])
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
                "review_state": _review_state(f.provenance, is_demo),
                "as_of": f.valid_from or now_iso,
                "actions": ["Confirm", "Edit", "Not true", "Restore" if weights.get(f.id, {}).get("lowered") else "Lower"],
                **weights.get(f.id, {}),
                "demo_data": is_demo or f.provenance == "demo_fixture",
            }
            for f in hyps
        ],
        "provenance": "demo_fixture" if is_demo else "inferred",
        "as_of": now_iso,
        "demo_data": is_demo,
    }


@router.get("/timeline")
def timeline(
    owner: str,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    lowered: bool = Query(default=False),
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    subjects = {s.id: s for s in call_opt(store, "list_subjects", owner, default=[])}
    iter_fn = getattr(store, "iter_visible_facts", None)
    items_facts: list[Fact] = []
    if callable(iter_fn):
        from temporal_memory.privacy.controls import fact_states
        filters = {"lowered_only": True} if lowered and hasattr(store, "db") else {}
        for f in iter_fn(owner, date_from=date_from, date_to=date_to, page_size=min(limit, 500), **filters):
            if lowered and not filters and not fact_states(store, owner, [f.id]).get(f.id, {}).get("lowered"):
                continue
            if f.status == "history":
                continue
            if _is_sensitive_subject(subjects.get(f.subject_id)) and f.provenance not in (
                "user_supplied",
                "provider_confirmed",
            ):
                continue
            items_facts.append(f)
            if len(items_facts) >= limit:
                break
    else:
        items_facts = [
            f
            for f in _iter_all_visible(store, owner, date_from=date_from, date_to=date_to)
            if not (
                _is_sensitive_subject(subjects.get(f.subject_id))
                and f.provenance not in ("user_supplied", "provider_confirmed")
            )
        ]
        items_facts.sort(key=lambda x: (x.valid_from or "", x.id), reverse=True)
        items_facts = items_facts[:limit]

    from temporal_memory.privacy.controls import fact_states
    weights = fact_states(store, owner, [f.id for f in items_facts])
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
                **weights.get(f.id, {}),
                "superseded_by": f.superseded_by,
                "provenance": f.provenance,
                "review_state": _review_state(f.provenance, is_demo),
                "as_of": f.valid_from or now_iso,
                "demo_data": is_demo or f.provenance == "demo_fixture",
            }
            for f in items_facts
        ],
        "provenance": _envelope_provenance((f.provenance for f in items_facts), is_demo=is_demo),
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
LIFE_SPINES = [CLUSTER_LABELS[c] for c in CLUSTERS]
_SPINE_BY_ROOT = {
    "career": CLUSTER_LABELS["career"],
    "work": CLUSTER_LABELS["career"],
    "learning": CLUSTER_LABELS["learning"],
    "education": CLUSTER_LABELS["learning"],
    "projects": CLUSTER_LABELS["projects"],
    "project": CLUSTER_LABELS["projects"],
    "family": CLUSTER_LABELS["people-family"],
    "people": CLUSTER_LABELS["people-family"],
    "people-family": CLUSTER_LABELS["people-family"],
    "relationships": CLUSTER_LABELS["people-family"],
    "lifestyle": CLUSTER_LABELS["events"],
    "events": CLUSTER_LABELS["events"],
    "social": CLUSTER_LABELS["events"],
    "life": CLUSTER_LABELS["events"],
    "money": CLUSTER_LABELS["home-money"],
    "finance": CLUSTER_LABELS["home-money"],
    "home": CLUSTER_LABELS["home-money"],
    "home-money": CLUSTER_LABELS["home-money"],
    "travel": CLUSTER_LABELS["travel"],
    "places": CLUSTER_LABELS["travel"],
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
    if isinstance(records_attr, dict):
        return list(records_attr.get(owner, {}).values())
    db = getattr(store, "db", None)
    if db is not None:
        try:
            with db.connection() as conn:
                rows = conn.execute(
                    "SELECT id, source FROM records WHERE owner = %s AND erased_at IS NULL",
                    (owner,),
                ).fetchall()
            return [{"id": r["id"], "source": r["source"]} for r in rows]
        except Exception:
            pass
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
    subjects = call_opt(store, "list_subjects", owner, default=[])
    subj_by_id = {s.id: s for s in subjects}

    facts = [
        f
        for f in _iter_all_visible(store, owner)
        if f.status == "active"
        and not (
            _is_sensitive_subject(subj_by_id.get(f.subject_id))
            and f.provenance not in ("user_supplied", "provider_confirmed")
        )
    ]

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

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for f in facts:
        grouped[spine_for(f.subject_id)].append({
            "id": f.id, "text": f.text, "subject_id": f.subject_id,
            "valid_from": f.valid_from, "evidence": list(f.evidence or []),
            "provenance": f.provenance, "as_of": f.valid_from or now_iso,
        })
    known_so_far = {
        theme: sorted(items, key=lambda x: (x["valid_from"] or "", x["id"]), reverse=True)[:5]
        for theme, items in sorted(grouped.items()) if items
    }

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

    quarantine: dict[str, int] = call_opt(store, "get_quarantine_counts", owner, default={}) or {}

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
        "provenance": _envelope_provenance((f.provenance for f in facts), is_demo=is_demo),
        "as_of": as_of or now_iso,
        "demo_data": is_demo,
    }


def _extract_record_span(
    record_text: str,
    fact_text: str,
    fact_text_orig: str | None,
    *,
    span_start: int | None = None,
    span_end: int | None = None,
    max_chars: int = 220,
) -> tuple[str, int, int]:
    """Return a bounded excerpt (span, start, end) from record_text instead of the whole raw record."""
    raw = record_text or ""
    if not raw:
        return "", 0, 0
    if (
        span_start is not None
        and span_end is not None
        and 0 <= span_start < span_end <= len(raw)
    ):
        excerpt = raw[span_start:span_end]
        if len(excerpt) <= max_chars:
            return excerpt, span_start, span_end
        return excerpt[:max_chars].rstrip() + "...", span_start, span_start + max_chars

    if len(raw) <= max_chars:
        return raw, 0, len(raw)

    # Locate the strongest token overlap window between the fact and long record.
    terms = [
        tok
        for tok in f"{fact_text} {fact_text_orig or ''}".lower().replace(".", " ").split()
        if len(tok) >= 4
    ]
    low = raw.lower()
    anchor = 0
    for term in terms:
        pos = low.find(term)
        if pos >= 0:
            anchor = pos
            break
    half = max_chars // 2
    start = max(0, anchor - half // 2)
    if start > 0:
        ws = raw.find(" ", start)
        if 0 < ws < anchor:
            start = ws + 1
    end = min(len(raw), start + max_chars)
    if end < len(raw):
        ws_end = raw.rfind(" ", start, end)
        if ws_end > start + half:
            end = ws_end
    snippet = raw[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(raw):
        snippet = snippet + "..."
    return snippet, start, end


@router.get("/why/{fact_id}")
def why_fact(
    owner: str,
    fact_id: str,
    reinforce: bool = Query(default=True),
    auth: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    get_fn = getattr(store, "get_facts", None)
    if callable(get_fn):
        found = get_fn(owner, [fact_id])
        fact = found[0] if found else None
    else:
        fact = next((f for f in store.visible_facts(owner, limit=200) if f.id == fact_id), None)
    if fact is None:
        raise HTTPException(status_code=404, detail="Fact not found or forgotten")

    subjects = {s.id: s for s in call_opt(store, "list_subjects", owner, default=[])}
    if _is_sensitive_subject(subjects.get(fact.subject_id)) and fact.provenance not in (
        "user_supplied",
        "provider_confirmed",
    ):
        raise HTTPException(status_code=404, detail="Fact not found or forgotten")

    span_record_id = getattr(fact, "span_record_id", None)
    span_start = getattr(fact, "span_start", None)
    span_end = getattr(fact, "span_end", None)
    reason_text = getattr(fact, "reason_text", None)
    reason_record_id = getattr(fact, "reason_record_id", None)
    reason_start = getattr(fact, "reason_start", None)
    reason_end = getattr(fact, "reason_end", None)

    db_obj = getattr(store, "db", None)
    if db_obj is not None and reason_text is None and span_record_id is None and reason_record_id is None:
        try:
            with db_obj.connection() as conn:
                extra = conn.execute(
                    """
                    SELECT span_record_id, span_start, span_end,
                           reason_text, reason_record_id, reason_start, reason_end
                    FROM facts
                    WHERE owner = %s AND id = %s AND (erased_at IS NULL)::int = 1
                    """,
                    (owner, fact.id),
                ).fetchone()
            if extra:
                span_record_id = extra["span_record_id"]
                span_start = extra["span_start"]
                span_end = extra["span_end"]
                reason_text = extra["reason_text"]
                reason_record_id = extra["reason_record_id"]
                reason_start = extra["reason_start"]
                reason_end = extra["reason_end"]
        except Exception:
            pass

    rec_ids = list(dict.fromkeys([*fact.evidence, *([reason_record_id] if reason_record_id else [])]))
    records = call_opt(store, "get_records", owner, rec_ids, default=[])
    rec_by_id = {r.id: r for r in records}
    attempt: Attempt | None = call_opt(store, "get_attempt", fact.attempt_id, default=None) if fact.attempt_id else None
    is_owner_hook = bool(attempt and attempt.worker_kind == "owner-hook")
    model_label = "your Claude" if is_owner_hook else (fact.model or (attempt.model if attempt else None) or "unknown")
    ev_prov = "demo_fixture" if is_demo else fact.provenance

    evidence_spans: list[dict[str, Any]] = []
    for rid in fact.evidence:
        r = rec_by_id.get(rid)
        if r is None:
            continue
        use_exact = span_record_id == r.id
        span_txt, s_lo, s_hi = _extract_record_span(
            r.text,
            fact.text,
            fact.text_orig,
            span_start=span_start if use_exact else None,
            span_end=span_end if use_exact else None,
        )
        evidence_spans.append({
            "id": r.id,
            "source": r.source,
            "at": r.at,
            "author": r.author,
            "span": span_txt,
            "text": span_txt,
            "span_start": s_lo,
            "span_end": s_hi,
            "provenance": ev_prov,
            "as_of": r.at,
        })

    # Stored cited reason ONLY, kept strictly separate from provenance; never generated.
    clean_reason = (reason_text or "").strip()
    reason_span: dict[str, Any] | None = None
    if not clean_reason and reason_record_id and reason_start is not None and reason_end is not None:
        r_src = rec_by_id.get(reason_record_id)
        if r_src is not None and 0 <= reason_start < reason_end <= len(r_src.text):
            clean_reason = r_src.text[reason_start:reason_end].strip()
    if clean_reason:
        reason_value = clean_reason
        if reason_record_id is not None or reason_start is not None:
            reason_span = {
                "record_id": reason_record_id,
                "start": reason_start,
                "end": reason_end,
                "text": clean_reason,
            }
    else:
        reason_value = "reason unknown"

    if reinforce is True and auth.role == "owner-device":
        from temporal_memory.privacy.controls import reinforce_recall

        reinforce_recall(store, owner, [fact.id])

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
        "evidence": evidence_spans,
        "provenance": fact.provenance,
        "reason": reason_value,
        "reason_span": reason_span,
        "review_state": _review_state(fact.provenance, is_demo),
        "as_of": fact.valid_from or now_iso,
        "demo_data": is_demo or fact.provenance == "demo_fixture",
    }


@router.get("/vocab/learned")
def vault_learned_vocab(
    owner: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    """Return owner-scoped learned vocabulary terms with source record provenance."""
    now_iso, is_demo = _meta(store, owner)
    db_obj = getattr(store, "db", None)
    items: list[dict[str, Any]] = []
    if db_obj is not None:
        from temporal_memory.vocab.proposals import list_owner_learned_terms

        with db_obj.connection() as conn:
            from temporal_memory.privacy.controls import learned_weights
            items = list_owner_learned_terms(conn, owner)
            weights = learned_weights(conn, owner)
            for item in items:
                item["weight"] = weights.get(item["term_folded"], 0.01)
            items.sort(key=lambda item: (-item["weight"], item["term_folded"]))
    return {
        "owner": owner,
        "items": items,
        "count": len(items),
        "provenance": "demo_fixture" if is_demo else "inferred",
        "as_of": now_iso,
    }
