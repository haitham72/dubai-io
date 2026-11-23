"""Transactional graph applier with per-owner advisory lock and generation fence (WP-A)."""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from temporal_memory.core.validator import _gate_fact
from temporal_memory.db.db import Database, fold_text, get_database
from temporal_memory.models import (
    Attempt,
    Entity,
    Job,
    JobBundle,
    OutEntity,
    OutFact,
    Verdict,
)

try:
    from temporal_memory.privacy.policy import may_promote as _policy_may_promote
except ImportError:  # pragma: no cover - WP-C not yet merged
    _policy_may_promote = None  # type: ignore[assignment]


def _may_promote(entity: Entity, distinct_days: int, user_confirmed: bool) -> bool:
    if _policy_may_promote is not None:
        return _policy_may_promote(entity, distinct_days, user_confirmed)
    # TODO WP-C: keep third-party entities as candidate until privacy.policy.may_promote is wired.
    return entity.relation_to_user == "self"


def _strip_new(ref: str) -> str:
    s = ref.strip()
    return s[4:].strip() if s.startswith("new:") else s


def _matches_forget_rule(
    fact: OutFact,
    rules: list[dict[str, Any]],
    resolved_names_by_ref: dict[str, str],
) -> bool:
    text_l = fact.text.lower()
    orig_l = (fact.text_orig or "").lower()
    subj_l = fact.subject_path.lower()
    for r in rules:
        kind = r["kind"]
        val = str(r["value"])
        val_l = val.lower()
        if kind == "text" and (val_l in text_l or (orig_l and val_l in orig_l)):
            return True
        if kind == "item" and fact.target == val:
            return True
        if kind == "subject" and val_l in subj_l:
            return True
        if kind == "entity":
            for fe in fact.entities:
                if fe.entity_id == val or resolved_names_by_ref.get(fe.entity_id, "").lower() == val_l:
                    return True
    return False


def apply(
    owner: str,
    job: Job,
    attempt: Attempt,
    *,
    db: Database | None = None,
    bundle: JobBundle | None = None,
) -> Verdict:
    """Apply validated extraction output atomically under a per-owner advisory lock."""
    del bundle  # unused; kept to match optional caller kwargs cleanly
    if attempt.output is None:
        return Verdict(ok=False, reasons=["schema_invalid"])

    database = db or get_database()
    out = attempt.output
    applied_fact_ids: list[str] = []
    quarantined: dict[str, int] = {}

    with database.transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (owner,))

        # 1) Generation & erasure fence
        rec_gen: dict[str, int] = {}
        if job.input_ref:
            unique_refs = list(dict.fromkeys(job.input_ref))
            rec_rows = conn.execute(
                "SELECT id, generation, erased_at FROM records WHERE owner = %s AND id = ANY(%s)",
                (owner, unique_refs),
            ).fetchall()
            if len(rec_rows) != len(unique_refs):
                return Verdict(ok=False, reasons=["fence_stale"])
            for r in rec_rows:
                if r["erased_at"] is not None or int(r["generation"]) > job.input_version:
                    return Verdict(ok=False, reasons=["fence_stale"])
                rec_gen[r["id"]] = int(r["generation"])

        # 2) Active forget rules
        forget_rules = conn.execute(
            "SELECT kind, value FROM forget_rules WHERE owner = %s",
            (owner,),
        ).fetchall()

        # 3) Load existing entities & aliases for resolution
        ent_rows = conn.execute(
            """
            SELECT id, kind, name, status, relation_to_user, first_seen, last_seen, merged_into
            FROM entities
            WHERE owner = %s AND erased_at IS NULL
            """,
            (owner,),
        ).fetchall()
        entities_by_id: dict[str, dict[str, Any]] = {}
        merged_map: dict[str, str] = {}
        alias_to_eid: dict[str, str] = {}
        for er in ent_rows:
            if er["status"] == "merged" and er["merged_into"]:
                merged_map[er["id"]] = er["merged_into"]
                continue
            entities_by_id[er["id"]] = dict(er)
            nf = fold_text(er["name"])
            if nf:
                alias_to_eid.setdefault(nf, er["id"])

        alias_rows = conn.execute(
            "SELECT entity_id, alias_folded FROM entity_aliases WHERE owner = %s",
            (owner,),
        ).fetchall()
        for ar in alias_rows:
            if ar["alias_folded"] and ar["entity_id"] in entities_by_id:
                alias_to_eid.setdefault(ar["alias_folded"], ar["entity_id"])

        hints: dict[str, OutEntity] = {e.ref.strip(): e for e in out.entities if e.ref}
        ref_to_eid: dict[str, str] = {}

        def _follow_merged(eid: str) -> str:
            seen: set[str] = set()
            cur = eid
            while cur in merged_map and cur not in seen:
                seen.add(cur)
                cur = merged_map[cur]
            return cur

        def _add_alias(eid: str, alias: str) -> None:
            af = fold_text(alias)
            if not af:
                return
            alias_to_eid.setdefault(af, eid)
            conn.execute(
                """
                INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded, source)
                VALUES (%s, %s, %s, %s, 'extractor')
                ON CONFLICT (owner, alias_folded, entity_id) DO NOTHING
                """,
                (owner, eid, alias.strip(), af),
            )

        def _resolve(ref: str, hint: OutEntity | None = None) -> str | None:
            raw = (ref or "").strip()
            if not raw:
                return None
            if raw in ref_to_eid:
                return ref_to_eid[raw]
            canon = _follow_merged(raw)
            if canon in entities_by_id:
                ref_to_eid[raw] = canon
                return canon

            name = _strip_new(raw)
            folded = fold_text(name)
            if folded and folded in alias_to_eid:
                eid = alias_to_eid[folded]
                ref_to_eid[raw] = eid
                return eid

            eid = f"e_{uuid.uuid4().hex[:12]}"
            kind = hint.kind if hint else "person"
            rel = hint.relation_to_user if hint else None
            ent_obj = Entity(id=eid, owner=owner, kind=kind, name=name, relation_to_user=rel)
            status = "active" if _may_promote(ent_obj, distinct_days=1, user_confirmed=False) else "candidate"
            conn.execute(
                """
                INSERT INTO entities (id, owner, kind, name, status, relation_to_user)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (eid, owner, kind, name, status, rel),
            )
            entities_by_id[eid] = {
                "id": eid,
                "kind": kind,
                "name": name,
                "status": status,
                "relation_to_user": rel,
                "first_seen": None,
                "last_seen": None,
            }
            _add_alias(eid, name)
            if hint:
                for al in hint.aliases:
                    _add_alias(eid, al)
            ref_to_eid[raw] = eid
            return eid

        for ref, hint in hints.items():
            before_count = len(entities_by_id)
            eid = _resolve(ref, hint)
            if eid and len(entities_by_id) == before_count:
                for al in hint.aliases:
                    _add_alias(eid, al)
                if hint.relation_to_user and not entities_by_id[eid].get("relation_to_user"):
                    conn.execute(
                        "UPDATE entities SET relation_to_user = %s WHERE owner = %s AND id = %s",
                        (hint.relation_to_user, owner, eid),
                    )
                    entities_by_id[eid]["relation_to_user"] = hint.relation_to_user

        # 4) Load subjects map & helper to ensure hierarchy exists
        subj_rows = conn.execute(
            "SELECT id, path, status FROM subjects WHERE owner = %s",
            (owner,),
        ).fetchall()
        subj_by_path: dict[str, str] = {r["path"]: r["id"] for r in subj_rows}

        def _ensure_subject(subject_path: str) -> str:
            parts = [p.strip() for p in subject_path.strip("/").split("/") if p.strip()]
            if not parts:
                parts = ["general"]
            parent_id: str | None = None
            cur_id = ""
            for idx, part in enumerate(parts):
                seg_path = "/".join(parts[: idx + 1])
                if seg_path in subj_by_path:
                    cur_id = subj_by_path[seg_path]
                else:
                    cur_id = f"s_{uuid.uuid4().hex[:12]}"
                    kind = "theme" if idx == 0 else "topic"
                    conn.execute(
                        """
                        INSERT INTO subjects (id, owner, parent_id, path, label, kind, status)
                        VALUES (%s, %s, %s, %s, %s, %s, 'candidate')
                        ON CONFLICT (owner, path) DO NOTHING
                        """,
                        (cur_id, owner, parent_id, seg_path, part, kind),
                    )
                    row = conn.execute(
                        "SELECT id FROM subjects WHERE owner = %s AND path = %s",
                        (owner, seg_path),
                    ).fetchone()
                    cur_id = row["id"]
                    subj_by_path[seg_path] = cur_id
                parent_id = cur_id
            return cur_id

        # 5) Apply facts (privacy quarantine + forget rules + temporal update/end)
        resolved_names_by_ref = {
            k: entities_by_id[v]["name"] for k, v in ref_to_eid.items() if v in entities_by_id
        }

        for fact in out.facts:
            if _matches_forget_rule(fact, forget_rules, resolved_names_by_ref):
                continue

            sens_cat = fact.sensitive or _gate_fact(fact, attempt.worker_kind)
            if sens_cat:
                if sens_cat == "credential":
                    continue
                conn.execute(
                    """
                    INSERT INTO quarantine (owner, category, record_ids, status)
                    VALUES (%s, %s, %s::jsonb, 'held')
                    """,
                    (owner, sens_cat, json.dumps(list(fact.evidence))),
                )
                quarantined[sens_cat] = quarantined.get(sens_cat, 0) + 1
                continue

            subject_id = _ensure_subject(fact.subject_path)
            new_fact_id = f"f_{uuid.uuid4().hex[:12]}"
            text_folded = fold_text(fact.text)
            content_hash = hashlib.sha256(
                f"{subject_id}|{text_folded}".encode("utf-8")
            ).hexdigest()

            status = "active"
            valid_to: str | None = None
            superseded_by: str | None = None

            if fact.op in ("update", "end") and fact.target:
                tgt = conn.execute(
                    """
                    SELECT id, status, valid_from
                    FROM facts
                    WHERE owner = %s AND id = %s AND erased_at IS NULL
                    """,
                    (owner, fact.target),
                ).fetchone()
                if tgt and tgt["status"] == "active":
                    if fact.valid_from and tgt["valid_from"] and fact.valid_from < tgt["valid_from"]:
                        # Older evidence never overwrites newer
                        status = "history"
                        superseded_by = tgt["id"]
                        valid_to = tgt["valid_from"]
                    else:
                        new_tgt_status = "superseded" if fact.op == "update" else "ended"
                        conn.execute(
                            """
                            UPDATE facts
                            SET status = %s, superseded_by = %s, valid_to = %s
                            WHERE owner = %s AND id = %s
                            """,
                            (new_tgt_status, new_fact_id, fact.valid_from, owner, tgt["id"]),
                        )

            conn.execute(
                """
                INSERT INTO facts (
                    id, owner, text, text_orig, text_folded, subject_id,
                    valid_from, valid_to, status, superseded_by, provenance,
                    job_id, attempt_id, worker_id, model, prompt_version, content_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'inferred', %s, %s, %s, %s, %s, %s)
                """,
                (
                    new_fact_id,
                    owner,
                    fact.text,
                    fact.text_orig,
                    text_folded,
                    subject_id,
                    fact.valid_from,
                    valid_to,
                    status,
                    superseded_by,
                    job.id,
                    f"{job.id}:{attempt.attempt_no}",
                    attempt.worker_id,
                    attempt.model,
                    attempt.prompt_version,
                    content_hash,
                ),
            )
            applied_fact_ids.append(new_fact_id)

            for fe in fact.entities:
                eid = _resolve(fe.entity_id, hints.get(fe.entity_id))
                if not eid:
                    continue
                conn.execute(
                    """
                    INSERT INTO fact_entities (owner, fact_id, entity_id, role)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (owner, fact_id, entity_id)
                    DO UPDATE SET role = COALESCE(EXCLUDED.role, fact_entities.role)
                    """,
                    (owner, new_fact_id, eid, fe.role),
                )
                if fact.valid_from:
                    ent_row = entities_by_id[eid]
                    first_s = ent_row["first_seen"]
                    last_s = ent_row["last_seen"]
                    new_first = fact.valid_from if not first_s or fact.valid_from < first_s else first_s
                    new_last = fact.valid_from if not last_s or fact.valid_from > last_s else last_s
                    if new_first != first_s or new_last != last_s:
                        conn.execute(
                            "UPDATE entities SET first_seen = %s, last_seen = %s WHERE owner = %s AND id = %s",
                            (new_first, new_last, owner, eid),
                        )
                        ent_row["first_seen"] = new_first
                        ent_row["last_seen"] = new_last

            for rid in dict.fromkeys(fact.evidence):
                conn.execute(
                    """
                    INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (owner, fact_id, record_id) DO NOTHING
                    """,
                    (owner, new_fact_id, rid, rec_gen.get(rid, job.input_version)),
                )

        # 6) Links
        anchor_fact_id = applied_fact_ids[0] if applied_fact_ids else None
        for lnk in out.links:
            src_id = _resolve(lnk.src, hints.get(lnk.src))
            dst_id = _resolve(lnk.dst, hints.get(lnk.dst))
            if src_id and dst_id and src_id != dst_id:
                link_id = f"l_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO links (id, owner, src, rel, dst, valid_from, evidence_fact_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (link_id, owner, src_id, lnk.rel, dst_id, lnk.valid_from, anchor_fact_id),
                )

        # 7) Recompute derived entity_subjects & subject fact_count from visible_facts
        conn.execute("DELETE FROM entity_subjects WHERE owner = %s", (owner,))
        conn.execute(
            """
            INSERT INTO entity_subjects (
                owner, entity_id, subject_id, role, weight, fact_count, first_seen, last_seen
            )
            SELECT
                vf.owner,
                fe.entity_id,
                vf.subject_id,
                COALESCE(fe.role, '') AS role,
                SUM(CASE WHEN vf.status = 'active' THEN 1.0 ELSE 0.3 END) AS weight,
                COUNT(*)::int AS fact_count,
                MIN(vf.valid_from) AS first_seen,
                MAX(vf.valid_from) AS last_seen
            FROM visible_facts vf
            JOIN fact_entities fe ON fe.owner = vf.owner AND fe.fact_id = vf.id
            WHERE vf.owner = %s
            GROUP BY vf.owner, fe.entity_id, vf.subject_id, COALESCE(fe.role, '')
            """,
            (owner,),
        )
        conn.execute(
            """
            UPDATE subjects s
            SET fact_count = COALESCE((
                SELECT COUNT(*)::int
                FROM visible_facts vf
                WHERE vf.owner = s.owner AND vf.subject_id = s.id
            ), 0)
            WHERE s.owner = %s
            """,
            (owner,),
        )

        # 8) Bump facts_version
        conn.execute(
            "UPDATE owners SET facts_version = facts_version + 1 WHERE id = %s",
            (owner,),
        )

    return Verdict(
        ok=True,
        applied_fact_ids=applied_fact_ids,
        quarantined=quarantined,
    )
