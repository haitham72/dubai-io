"""Knowledge Graph Vault endpoint (`GET /vault/graph`) & T1 tier confirmation (`POST /vault/people/{id}/tier`) (U1c)."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path as FPath, Query
from pydantic import BaseModel

from temporal_memory.api.vault import (
    AuthContext,
    _envelope_provenance,
    _is_sensitive_subject,
    _meta,
    _review_state,
    call_opt,
    get_auth,
    get_store,
    require_owner_access,
)
from temporal_memory.core.retrieval import compute_entity_salience_sql, compute_subject_salience_sql
from temporal_memory.live.context import invalidate_alias_cache
from temporal_memory.models import CLUSTER_LABELS, CLUSTERS as ENGINE_CLUSTERS, Entity, GraphStore, HELD_BACK_ROOTS, Link, Subject

router = APIRouter(prefix="/v1/owners/{owner}", tags=["vault"])

_CLUSTER_BY_ROOT: dict[str, str] = {
    "career": "career",
    "work": "career",
    "learning": "learning",
    "education": "learning",
    "projects": "projects",
    "project": "projects",
    "people-family": "people-family",
    "family": "people-family",
    "people": "people-family",
    "relationships": "people-family",
    "events": "events",
    "lifestyle": "events",
    "social": "events",
    "life": "events",
    "home-money": "home-money",
    "money": "home-money",
    "finance": "home-money",
    "home": "home-money",
    "travel": "travel",
    "places": "travel",
}
_SENSITIVE_ROOTS = frozenset(HELD_BACK_ROOTS)


def _cluster_for_subject(subj: Subject | None) -> str | None:
    if subj is None or subj.sensitive_cat is not None:
        return None
    root = (subj.path or "").split("/")[0].strip().lower()
    if root in _SENSITIVE_ROOTS:
        return None
    return _CLUSTER_BY_ROOT.get(root, "events")


def _require_strict_owner_only(
    owner: str = FPath(...),
    auth: AuthContext = Depends(get_auth),
) -> AuthContext:
    """Confirming T1 closeness is strictly owner-device auth matching `{owner}` (admin/worker/cross-owner -> 403)."""
    if auth.role == "owner-device" and auth.owner == owner:
        return auth
    raise HTTPException(status_code=403, detail="owner-device authentication matching owner required")


class TierConfirmIn(BaseModel):
    tier: Literal["T1", "T2", "T3"] | None = None


@router.post("/vault/people/{entity_id}/tier")
def confirm_person_tier(
    owner: str,
    entity_id: str,
    body: TierConfirmIn,
    _: AuthContext = Depends(_require_strict_owner_only),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    """Explicit owner confirmation of closeness_tier (D-c). Never auto-inferred; owner token only."""
    now_iso = datetime.now(timezone.utc).isoformat()
    db = getattr(store, "db", None)
    if db is not None:
        with db.transaction() as conn:
            row = conn.execute(
                "SELECT id, kind, status, erased_at FROM entities WHERE owner = %s AND id = %s",
                (owner, entity_id),
            ).fetchone()
            if row is None or row["erased_at"] is not None or row["status"] == "merged":
                raise HTTPException(status_code=404, detail="Person entity not found")
            if row["kind"] != "person":
                raise HTTPException(status_code=422, detail="closeness_tier applies only to person entities")
            confirmed_at = now_iso if body.tier is not None else None
            if body.tier is not None:
                conn.execute(
                    """
                    UPDATE entities
                    SET closeness_tier = %s,
                        tier_confirmed_at = %s,
                        provenance = 'user_supplied',
                        user_confirmed_at = COALESCE(user_confirmed_at, %s)
                    WHERE owner = %s AND id = %s
                    """,
                    (body.tier, confirmed_at, confirmed_at, owner, entity_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE entities
                    SET closeness_tier = NULL,
                        tier_confirmed_at = NULL
                    WHERE owner = %s AND id = %s
                    """,
                    (owner, entity_id),
                )
            conn.execute(
                "UPDATE owners SET alias_version = alias_version + 1, privacy_revision = privacy_revision + 1 WHERE id = %s",
                (owner,),
            )
        invalidate_alias_cache(owner)
        return {
            "ok": True,
            "owner": owner,
            "entity_id": entity_id,
            "closeness_tier": body.tier,
            "tier_confirmed_at": confirmed_at,
        }

    # FakeGraphStore fallback
    entities = call_opt(store, "list_entities", owner, default=[])
    target = next((e for e in entities if e.id == entity_id and e.status != "merged"), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Person entity not found")
    if target.kind != "person":
        raise HTTPException(status_code=422, detail="closeness_tier applies only to person entities")
    target.closeness_tier = body.tier
    target.tier_confirmed_at = now_iso if body.tier is not None else None
    if body.tier is not None:
        target.provenance = "user_supplied"
        if target.user_confirmed_at is None:
            target.user_confirmed_at = now_iso
    if hasattr(store, "bump_privacy_revision"):
        store.bump_privacy_revision(owner)
    invalidate_alias_cache(owner)
    return {
        "ok": True,
        "owner": owner,
        "entity_id": entity_id,
        "closeness_tier": body.tier,
        "tier_confirmed_at": target.tier_confirmed_at,
    }


def _hidden_fact_ids_for_owner(conn: Any, owner: str) -> list[str]:
    """Return IDs hidden from `visible_facts` via erased/stale evidence or `forget_rules`."""
    hidden: set[str] = set()
    stale_rec = conn.execute(
        "SELECT id FROM records WHERE owner = %s AND (erased_at IS NOT NULL OR generation > 0)",
        (owner,),
    ).fetchall()
    if stale_rec:
        ev_rows = conn.execute(
            """
            SELECT DISTINCT fe.fact_id
            FROM fact_evidence fe
            JOIN records r ON r.id = fe.record_id AND r.owner = fe.owner
            WHERE fe.owner = %s AND (r.erased_at IS NOT NULL OR r.generation > fe.record_generation)
            """,
            (owner,),
        ).fetchall()
        hidden.update(r["fact_id"] for r in ev_rows)

    fr_rows = conn.execute("SELECT kind, value FROM forget_rules WHERE owner = %s", (owner,)).fetchall()
    if fr_rows:
        item_ids = [r["value"] for r in fr_rows if r["kind"] == "item"]
        text_vals = [r["value"].lower() for r in fr_rows if r["kind"] == "text" and r["value"]]
        hidden.update(item_ids)
        if text_vals:
            matched = conn.execute(
                """
                SELECT f.id
                FROM facts f
                WHERE f.owner = %s AND f.erased_at IS NULL AND f.status <> 'history'
                  AND EXISTS (
                      SELECT 1 FROM forget_rules fr
                      WHERE fr.owner = f.owner AND fr.kind = 'text'
                        AND position(lower(fr.value) IN lower(f.text)) > 0
                  )
                """,
                (owner,),
            ).fetchall()
            hidden.update(r["id"] for r in matched)
    return sorted(hidden)


def _fetch_entity_evidence_map(
    conn: Any,
    owner: str,
    entity_ids: list[str],
    hidden_fids: list[str],
) -> dict[str, list[str]]:
    """Fetch up to 3 most-recent visible evidence fact IDs per shown entity (SQL)."""
    if not entity_ids:
        return {}
    hid_clause = "AND NOT (f.id = ANY(%s))" if hidden_fids else ""
    params: tuple[Any, ...] = (
        (owner, entity_ids, hidden_fids) if hidden_fids else (owner, entity_ids)
    )
    rows = conn.execute(
        f"""
        WITH ranked AS (
            SELECT fe.entity_id, f.id,
                   ROW_NUMBER() OVER (PARTITION BY fe.entity_id ORDER BY f.valid_from DESC, f.id DESC) AS rn
            FROM fact_entities fe
            JOIN facts f ON f.owner = fe.owner AND f.id = fe.fact_id
            LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
            WHERE fe.owner = %s
              AND fe.entity_id = ANY(%s)
              AND (f.erased_at IS NULL)::int = 1 AND f.status <> 'history' {hid_clause}
              AND (
                  s.id IS NULL
                  OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith'))
                  OR f.provenance IN ('user_supplied', 'provider_confirmed')
              )
        )
        SELECT entity_id, id FROM ranked WHERE rn <= 3
        """,
        params,
    ).fetchall()
    out: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        out[r["entity_id"]].append(r["id"])
    return out


def _collect_sql_projection(
    store: Any,
    owner: str,
    *,
    view: str = "subjects",
) -> dict[str, Any]:
    """Single fast SQL snapshot for `/vault/graph` (O(nodes), < 100ms at 20k facts)."""
    db = store.db
    with db.connection() as conn:
        owner_row = conn.execute(
            "SELECT id, label, kind, display_name, facts_version, privacy_revision FROM owners WHERE id = %s",
            (owner,),
        ).fetchone()
        subjects = store.list_subjects(owner)
        entities = store.list_entities(owner)
        links = store.list_links(owner)

        hidden_fids = _hidden_fact_ids_for_owner(conn, owner)
        hid_clause = "AND NOT (f.id = ANY(%s))" if hidden_fids else ""
        base_params: tuple[Any, ...] = (owner, hidden_fids) if hidden_fids else (owner,)

        subj_agg_rows = conn.execute(
            f"""
            WITH counts AS (
                SELECT s.id AS subject_id,
                       s.provenance,
                       s.user_confirmed_at,
                       COUNT(f.id)::int AS total_cnt,
                       COUNT(f.id) FILTER (WHERE f.provenance IN ('user_supplied', 'provider_confirmed'))::int AS conf_cnt,
                       COUNT(f.id) FILTER (WHERE f.valid_from >= to_char(CURRENT_DATE - 30, 'YYYY-MM-DD'))::int AS mentions_30d,
                       MAX(f.valid_from) AS max_valid_from,
                       MAX(NULLIF(substr(f.valid_from, 1, 10), '')) AS max_valid_day
                FROM subjects s
                LEFT JOIN facts f ON f.owner = s.owner AND f.subject_id = s.id
                  AND f.erased_at IS NULL AND f.status <> 'history' {hid_clause}
                WHERE s.owner = %s
                GROUP BY s.id, s.provenance, s.user_confirmed_at
            )
            SELECT subject_id, total_cnt, conf_cnt, max_valid_from,
                   GREATEST(
                       0.05,
                       0.5 * LN(1.0 + mentions_30d)
                       + 0.3 * EXP(
                           -GREATEST(
                               0,
                               (CURRENT_DATE - COALESCE(
                                   CASE WHEN COALESCE(max_valid_day, '') ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
                                        THEN max_valid_day::date
                                        ELSE CURRENT_DATE - 90
                                   END,
                                   CURRENT_DATE - 90
                               ))
                           )::double precision / 30.0
                       )
                       + 0.2 * CASE WHEN provenance = 'user_supplied' OR user_confirmed_at IS NOT NULL THEN 1.0 ELSE 0.0 END
                   ) AS sal
            FROM counts
            """,
            (hidden_fids, owner) if hidden_fids else (owner,),
        ).fetchall()

        subj_ev_rows: list[dict[str, Any]] = []
        if view == "subjects":
            subj_ev_rows = conn.execute(
                f"""
                SELECT s.id AS subject_id, ev.id, ev.provenance
                FROM subjects s
                CROSS JOIN LATERAL (
                    SELECT f.id, f.provenance
                    FROM facts f
                    WHERE f.owner = s.owner AND f.subject_id = s.id
                      AND f.erased_at IS NULL AND f.status <> 'history' {hid_clause}
                    ORDER BY f.valid_from DESC, f.id DESC
                    LIMIT 3
                ) ev
                WHERE s.owner = %s
                """,
                (hidden_fids, owner) if hidden_fids else (owner,),
            ).fetchall()

        ent_agg_rows = conn.execute(
            f"""
            WITH agg AS MATERIALIZED (
                SELECT fe.entity_id,
                       COUNT(*)::int AS total_cnt,
                       COUNT(*) FILTER (WHERE f.provenance IN ('user_supplied', 'provider_confirmed'))::int AS conf_cnt,
                       COUNT(*) FILTER (WHERE f.valid_from >= to_char(CURRENT_DATE - 30, 'YYYY-MM-DD'))::int AS mentions_30d,
                       MAX(f.valid_from) AS max_valid_from,
                       MAX(NULLIF(substr(f.valid_from, 1, 10), '')) AS max_valid_day
                FROM fact_entities fe
                JOIN facts f ON f.owner = fe.owner AND f.id = fe.fact_id
                LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                WHERE fe.owner = %s AND (f.erased_at IS NULL)::int = 1 AND f.status <> 'history' {hid_clause}
                  AND (
                      s.id IS NULL
                      OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith'))
                      OR f.provenance IN ('user_supplied', 'provider_confirmed')
                  )
                GROUP BY fe.entity_id
            )
            SELECT e.id AS entity_id,
                   COALESCE(a.total_cnt, 0) AS total_cnt,
                   COALESCE(a.conf_cnt, 0) AS conf_cnt,
                   a.max_valid_from,
                   GREATEST(
                       0.05,
                       0.5 * LN(1.0 + COALESCE(a.mentions_30d, 0))
                       + 0.3 * EXP(
                           -GREATEST(
                               0,
                               (CURRENT_DATE - COALESCE(
                                   CASE WHEN COALESCE(a.max_valid_day, substr(e.last_seen, 1, 10), '') ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
                                        THEN COALESCE(a.max_valid_day, substr(e.last_seen, 1, 10))::date
                                        ELSE CURRENT_DATE - 90
                                   END,
                                   CURRENT_DATE - 90
                               ))
                           )::double precision / 30.0
                       )
                       + 0.2 * CASE WHEN e.provenance = 'user_supplied' OR e.user_confirmed_at IS NOT NULL THEN 1.0 ELSE 0.0 END
                   ) AS sal
            FROM entities e
            LEFT JOIN agg a ON a.entity_id = e.id
            WHERE e.owner = %s AND e.erased_at IS NULL AND e.status <> 'merged'
            """,
            (owner, hidden_fids, owner) if hidden_fids else (owner, owner),
        ).fetchall()

        link_ev_rows = conn.execute(
            f"""
            SELECT ln.id AS link_id, ev.fact_id, f.provenance
            FROM links ln
            JOIN (
                SELECT owner, id AS link_id, evidence_fact_id AS fact_id FROM links WHERE owner = %s AND evidence_fact_id IS NOT NULL
                UNION
                SELECT owner, link_id, fact_id FROM link_evidence WHERE owner = %s
            ) ev ON ev.owner = ln.owner AND ev.link_id = ln.id
            JOIN facts f ON f.owner = ev.owner AND f.id = ev.fact_id
            WHERE ln.owner = %s AND ln.erased_at IS NULL
              AND f.erased_at IS NULL AND f.status <> 'history' {hid_clause}
            ORDER BY ln.id ASC, ev.fact_id ASC
            """,
            (owner, owner, owner, hidden_fids) if hidden_fids else (owner, owner, owner),
        ).fetchall()

    return {
        "owner_row": owner_row,
        "subjects": subjects,
        "entities": entities,
        "links": links,
        "hidden_fids": hidden_fids,
        "ent_sal": {r["entity_id"]: round(float(r["sal"]), 4) for r in ent_agg_rows},
        "subj_sal": {r["subject_id"]: round(float(r["sal"]), 4) for r in subj_agg_rows},
        "subj_agg": {r["subject_id"]: r for r in subj_agg_rows},
        "subj_ev": subj_ev_rows,
        "ent_agg": {r["entity_id"]: r for r in ent_agg_rows},
        "ent_ev": [],
        "link_ev": link_ev_rows,
    }


def _collect_memory_projection(store: Any, owner: str) -> dict[str, Any]:
    """Fallback projection builder for FakeGraphStore parity."""
    owner_obj = call_opt(store, "get_owner", owner, default=None)
    subjects: list[Subject] = call_opt(store, "list_subjects", owner, default=[])
    entities: list[Entity] = call_opt(store, "list_entities", owner, default=[])
    links: list[Link] = call_opt(store, "list_links", owner, default=[])
    subj_by_id = {s.id: s for s in subjects}

    all_facts = list(store.iter_visible_facts(owner, page_size=500)) if hasattr(store, "iter_visible_facts") else store.visible_facts(owner, limit=500)
    subj_agg: dict[str, dict[str, Any]] = {}
    subj_ev: list[dict[str, Any]] = []
    ent_agg: dict[str, dict[str, Any]] = {}
    ent_ev: list[dict[str, Any]] = []
    vis_fmap = {f.id: f for f in all_facts}

    for f in sorted(all_facts, key=lambda x: (x.valid_from or "", x.id), reverse=True):
        if f.status == "history":
            continue
        is_conf = f.provenance in ("user_supplied", "provider_confirmed")
        sa = subj_agg.setdefault(f.subject_id, {"subject_id": f.subject_id, "total_cnt": 0, "conf_cnt": 0, "max_valid_from": f.valid_from})
        sa["total_cnt"] += 1
        if is_conf:
            sa["conf_cnt"] += 1
        sa["max_valid_from"] = max(sa["max_valid_from"] or "", f.valid_from or "")
        if sum(1 for r in subj_ev if r["subject_id"] == f.subject_id) < 3:
            subj_ev.append({"subject_id": f.subject_id, "id": f.id, "provenance": f.provenance})

        subj = subj_by_id.get(f.subject_id)
        if _is_sensitive_subject(subj) and not is_conf:
            continue
        for fe in f.entities:
            ea = ent_agg.setdefault(fe.entity_id, {"entity_id": fe.entity_id, "total_cnt": 0, "conf_cnt": 0, "max_valid_from": f.valid_from})
            ea["total_cnt"] += 1
            if is_conf:
                ea["conf_cnt"] += 1
            ea["max_valid_from"] = max(ea["max_valid_from"] or "", f.valid_from or "")
            if sum(1 for r in ent_ev if r["entity_id"] == fe.entity_id) < 3:
                ent_ev.append({"entity_id": fe.entity_id, "id": f.id, "provenance": f.provenance})

    link_ev: list[dict[str, Any]] = []
    for ln in links:
        if ln.evidence_fact_id and ln.evidence_fact_id in vis_fmap:
            link_ev.append({"link_id": ln.id, "fact_id": ln.evidence_fact_id, "provenance": vis_fmap[ln.evidence_fact_id].provenance})

    return {
        "owner_row": {
            "id": owner,
            "display_name": owner_obj.display_name if owner_obj else owner,
            "kind": owner_obj.kind if owner_obj else "real",
            "facts_version": call_opt(store, "facts_version", owner, default=0),
            "privacy_revision": call_opt(store, "privacy_revision", owner, default=0),
        },
        "subjects": subjects,
        "entities": entities,
        "links": links,
        "ent_sal": {e.id: e.salience for e in entities},
        "subj_sal": {s.id: s.salience for s in subjects},
        "subj_agg": subj_agg,
        "subj_ev": subj_ev,
        "ent_agg": ent_agg,
        "ent_ev": ent_ev,
        "link_ev": link_ev,
    }


@router.get("/vault/graph")
def vault_graph(
    owner: str,
    view: Literal["subjects", "people"] = Query(default="subjects"),
    max_per_group: int = Query(default=12, ge=1, le=200),
    cluster: str | None = Query(default=None),
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    """Return Rule-9-gated Subjects or People & Places constellation graph DTO (plan §5.1)."""
    now_iso, is_demo = _meta(store, owner)
    proj = (
        _collect_sql_projection(store, owner, view=view)
        if hasattr(store, "db")
        else _collect_memory_projection(store, owner)
    )
    ow = proj["owner_row"] or {"id": owner, "display_name": owner, "kind": "real", "facts_version": 0, "privacy_revision": 0}
    subjects: list[Subject] = proj["subjects"]
    entities: list[Entity] = proj["entities"]
    links: list[Link] = proj["links"]

    subj_ev_all: dict[str, list[str]] = defaultdict(list)
    subj_ev_conf: dict[str, list[str]] = defaultdict(list)
    for r in proj["subj_ev"]:
        subj_ev_all[r["subject_id"]].append(r["id"])
        if r["provenance"] in ("user_supplied", "provider_confirmed"):
            subj_ev_conf[r["subject_id"]].append(r["id"])

    ent_ev_all: dict[str, list[str]] = defaultdict(list)
    for r in proj["ent_ev"]:
        ent_ev_all[r["entity_id"]].append(r["id"])

    link_ev_map: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for r in proj["link_ev"]:
        link_ev_map[r["link_id"]].append((r["fact_id"], r["provenance"]))

    # 1. Authorized Entities (single Rule-9 projection used across BOTH views + counts)
    self_ent = next((e for e in entities if e.status != "merged" and e.relation_to_user == "self"), None)
    center_id = self_ent.id if self_ent else owner
    center_label = (ow.get("display_name") or (self_ent.name if self_ent else "") or owner)

    auth_entities: list[dict[str, Any]] = []
    for e in entities:
        if e.status == "merged" or e.relation_to_user == "self":
            continue
        agg = proj["ent_agg"].get(e.id)
        total_cnt = int(agg["total_cnt"]) if agg else 0
        conf_cnt = int(agg["conf_cnt"]) if agg else 0
        prov = getattr(e, "provenance", "inferred") or "inferred"
        is_family = e.relation_to_user == "family"
        if is_family:
            # Rule 9 / D-a: People & family items must be confirmed/user_supplied only.
            if prov not in ("user_supplied", "provider_confirmed") and conf_cnt == 0:
                continue
            eff_count = conf_cnt
            if eff_count == 0 and prov not in ("user_supplied", "provider_confirmed"):
                continue
        else:
            if total_cnt == 0 and prov not in ("user_supplied", "provider_confirmed"):
                continue
            eff_count = total_cnt

        group_name = {
            "person": "people",
            "place": "places",
            "org": "orgs",
            "project": "projects",
            "event": "events",
        }.get(e.kind, "other")
        auth_entities.append({
            "id": e.id,
            "kind": e.kind,
            "label": e.name,
            "subtitle": e.relation_to_user or e.kind,
            "group": group_name,
            "tier": e.closeness_tier,
            "closeness_suggested": None if is_family else getattr(e, "closeness_suggested", None),
            "closeness_suggested_evidence": None if is_family else getattr(e, "closeness_suggested_evidence", None),
            "fact_count": eff_count,
            "salience": proj["ent_sal"].get(e.id, e.salience),
            "provenance": prov,
            "review_state": _review_state(prov, is_demo),
            "as_of": e.last_seen or (agg["max_valid_from"] if agg and agg["max_valid_from"] else now_iso),
            "evidence_fact_ids": ent_ev_all.get(e.id, []),
        })
    auth_ent_by_id = {n["id"]: n for n in auth_entities}

    # 2. Authorized observed edges (zero orphan or Rule-9-violating edges)
    auth_edges: list[dict[str, Any]] = []
    for ln in links:
        src_ok = ln.src == center_id or ln.src in auth_ent_by_id
        dst_ok = ln.dst == center_id or ln.dst in auth_ent_by_id
        if not (src_ok and dst_ok):
            continue
        ev_pairs = link_ev_map.get(ln.id, [])
        if not ev_pairs:
            continue
        is_family_edge = (
            ln.rel == "FAMILY_OF"
            or auth_ent_by_id.get(ln.src, {}).get("subtitle") == "family"
            or auth_ent_by_id.get(ln.dst, {}).get("subtitle") == "family"
        )
        if is_family_edge:
            ev_pairs = [(fid, p) for fid, p in ev_pairs if p in ("user_supplied", "provider_confirmed")]
            if not ev_pairs:
                continue
        ln_prov = _envelope_provenance((p for _, p in ev_pairs), is_demo=is_demo)
        auth_edges.append({
            "id": ln.id,
            "src": ln.src,
            "dst": ln.dst,
            "rel": ln.rel,
            "kind": "observed",
            "provenance": ln_prov,
            "review_state": _review_state(ln_prov, is_demo),
            "valid_from": ln.valid_from,
            "valid_to": ln.valid_to,
            "evidence_fact_ids": [fid for fid, _ in ev_pairs[:5]],
        })

    # 3. Authorized Subjects grouped into the 7 engine clusters (never health or faith)
    topic_nodes_by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cluster_fact_totals: dict[str, int] = defaultdict(int)
    for s in subjects:
        cl = _cluster_for_subject(s)
        if cl is None:
            continue
        if cluster and cl != cluster:
            continue
        agg = proj["subj_agg"].get(s.id)
        total_cnt = int(agg["total_cnt"]) if agg else 0
        conf_cnt = int(agg["conf_cnt"]) if agg else 0
        prov = getattr(s, "provenance", "inferred") or "inferred"
        if cl == "people-family":
            if conf_cnt == 0 and prov not in ("user_supplied", "provider_confirmed"):
                continue
            eff_cnt = conf_cnt
            ev_ids = subj_ev_conf.get(s.id, [])
        else:
            if total_cnt == 0 and s.kind == "theme":
                continue
            if total_cnt == 0 and prov not in ("user_supplied", "provider_confirmed"):
                continue
            eff_cnt = total_cnt
            ev_ids = subj_ev_all.get(s.id, [])
        cluster_fact_totals[cl] += eff_cnt
        if s.kind == "theme" and s.path.split("/")[0].lower() == cl:
            continue
        topic_nodes_by_cluster[cl].append({
            "id": s.id,
            "kind": "subject",
            "label": s.label,
            "subtitle": s.path,
            "group": cl,
            "tier": None,
            "closeness_suggested": None,
            "closeness_suggested_evidence": None,
            "fact_count": eff_cnt,
            "salience": proj["subj_sal"].get(s.id, s.salience),
            "provenance": prov,
            "review_state": _review_state(prov, is_demo),
            "as_of": (agg["max_valid_from"] if agg and agg["max_valid_from"] else now_iso),
            "evidence_fact_ids": ev_ids,
        })

    # Base counts before capping (identical Rule-9-gated projection)
    people_all = [n for n in auth_entities if n["group"] == "people"]
    places_all = [n for n in auth_entities if n["group"] == "places"]
    projects_all = [n for n in auth_entities if n["group"] == "projects"]
    orgs_all = [n for n in auth_entities if n["group"] == "orgs"]
    events_all = [n for n in auth_entities if n["group"] == "events"]

    hidden_by_group: dict[str, int] = {}
    nodes: list[dict[str, Any]] = [
        {
            "id": center_id,
            "kind": "owner",
            "label": center_label,
            "subtitle": "You",
            "group": "center",
            "tier": None,
            "closeness_suggested": None,
            "closeness_suggested_evidence": None,
            "fact_count": sum(cluster_fact_totals.values()),
            "salience": 1.0,
            "provenance": "demo_fixture" if is_demo else "user_supplied",
            "review_state": "demo" if is_demo else "confirmed",
            "as_of": now_iso,
            "evidence_fact_ids": [],
        }
    ]
    edges: list[dict[str, Any]] = []
    key_items: list[dict[str, Any]] = []

    if view == "subjects":
        active_clusters = [cl for cl in ENGINE_CLUSTERS if cluster_fact_totals.get(cl, 0) > 0 or topic_nodes_by_cluster.get(cl)]
        total_subject_nodes = len(active_clusters) + sum(len(topic_nodes_by_cluster[cl]) for cl in active_clusters)
        for cl in active_clusters:
            items = sorted(topic_nodes_by_cluster[cl], key=lambda x: (-float(x["salience"]), -int(x["fact_count"]), x["id"]))
            shown = items[:max_per_group]
            hidden = max(0, len(items) - len(shown))
            if hidden > 0:
                hidden_by_group[cl] = hidden
            cl_id = f"cluster:{cl}"
            cl_prov = _envelope_provenance((n["provenance"] for n in items), is_demo=is_demo)
            nodes.append({
                "id": cl_id,
                "kind": "cluster",
                "label": CLUSTER_LABELS[cl],
                "subtitle": f"{cluster_fact_totals[cl]} facts",
                "group": cl,
                "tier": None,
                "closeness_suggested": None,
                "closeness_suggested_evidence": None,
                "fact_count": cluster_fact_totals[cl],
                "salience": max((float(n["salience"]) for n in items), default=0.5),
                "provenance": cl_prov,
                "review_state": _review_state(cl_prov, is_demo),
                "as_of": now_iso,
                "evidence_fact_ids": [fid for n in items[:3] for fid in n["evidence_fact_ids"]][:3],
            })
            edges.append({
                "id": f"mem:{center_id}->{cl_id}",
                "src": center_id,
                "dst": cl_id,
                "rel": "CLUSTER_OF",
                "kind": "membership",
                "provenance": cl_prov,
                "review_state": _review_state(cl_prov, is_demo),
                "valid_from": None,
                "valid_to": None,
                "evidence_fact_ids": [],
            })
            for tn in shown:
                nodes.append(tn)
                edges.append({
                    "id": f"mem:{cl_id}->{tn['id']}",
                    "src": cl_id,
                    "dst": tn["id"],
                    "rel": "TOPIC_OF",
                    "kind": "membership",
                    "provenance": tn["provenance"],
                    "review_state": tn["review_state"],
                    "valid_from": None,
                    "valid_to": None,
                    "evidence_fact_ids": tn["evidence_fact_ids"][:3],
                })
            key_items.append({
                "id": cl_id,
                "cluster": cl,
                "label": CLUSTER_LABELS[cl],
                "summary": " · ".join(n["label"] for n in shown[:3]) or CLUSTER_LABELS[cl],
                "fact_count": cluster_fact_totals[cl],
                "provenance": cl_prov,
                "review_state": _review_state(cl_prov, is_demo),
            })
        total_nodes_count = total_subject_nodes
        shown_nodes_count = len(nodes) - 1
    else:
        tier_rank = {"T1": 0, "T2": 1, "T3": 2, None: 3}
        grouped_lists = [
            ("people", people_all),
            ("places", places_all),
            ("orgs", orgs_all),
            ("projects", projects_all),
            ("events", events_all),
        ]
        for grp_name, grp_items in grouped_lists:
            ordered = sorted(
                grp_items,
                key=lambda n: (tier_rank.get(n["tier"], 3), -float(n["salience"]), -int(n["fact_count"]), n["id"]),
            )
            shown = ordered[:max_per_group]
            hidden = max(0, len(ordered) - len(shown))
            if hidden > 0:
                hidden_by_group[grp_name] = hidden
            nodes.extend(shown)

        if hasattr(store, "db") and len(nodes) > 1:
            shown_eids = [n["id"] for n in nodes[1:]]
            with store.db.connection() as conn:
                ev_map = _fetch_entity_evidence_map(conn, owner, shown_eids, proj.get("hidden_fids") or [])
            for n in nodes[1:]:
                n["evidence_fact_ids"] = ev_map.get(n["id"], [])

        visible_node_ids = {n["id"] for n in nodes}
        # Only emit edges where BOTH endpoints are visible (zero orphan edges)
        edges = [e for e in auth_edges if e["src"] in visible_node_ids and e["dst"] in visible_node_ids]
        connected_ids = {e["dst"] for e in edges if e["src"] == center_id} | {e["src"] for e in edges if e["dst"] == center_id}
        for n in nodes[1:]:
            if n["id"] not in connected_ids:
                edges.append({
                    "id": f"mem:{center_id}->{n['id']}",
                    "src": center_id,
                    "dst": n["id"],
                    "rel": (n["subtitle"] or "KNOWS").upper(),
                    "kind": "membership",
                    "provenance": n["provenance"],
                    "review_state": n["review_state"],
                    "valid_from": None,
                    "valid_to": None,
                    "evidence_fact_ids": n["evidence_fact_ids"][:3],
                })
        key_items = [
            {
                "id": n["id"],
                "kind": n["kind"],
                "label": n["label"],
                "subtitle": n["subtitle"],
                "tier": n["tier"],
                "fact_count": n["fact_count"],
                "provenance": n["provenance"],
                "review_state": n["review_state"],
            }
            for n in nodes[1:8]
        ]
        total_nodes_count = len(auth_entities)
        shown_nodes_count = len(nodes) - 1

    env_prov = _envelope_provenance((n["provenance"] for n in nodes[1:]), is_demo=is_demo)
    return {
        "version": "1",
        "owner": owner,
        "view": view,
        "center_id": center_id,
        "as_of": now_iso,
        "provenance": env_prov,
        "demo_data": is_demo,
        "privacy_revision": int(ow.get("privacy_revision", 0) or 0),
        "facts_version": int(ow.get("facts_version", 0) or 0),
        "counts": {
            "total_nodes": total_nodes_count,
            "shown_nodes": shown_nodes_count,
            "people": len(people_all),
            "places": len(places_all),
            "projects": len(projects_all),
            "relations": len(auth_edges),
            "hidden_by_group": hidden_by_group,
        },
        "nodes": nodes,
        "edges": edges,
        "key_items": key_items,
    }
