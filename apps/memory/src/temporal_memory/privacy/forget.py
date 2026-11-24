"""Forget-by-source with a generation fence (WP-C). Implements plan A5 + §3.2.

`forget_source(owner, record_ids)`:
  1. bumps `records.generation` and stamps `erased_at` for those records
     (planaudit §7: Forget bumps the generation and sets `erased_at`);
  2. sets `erased_at` on facts whose evidence is ONLY those records (facts with
     other surviving evidence keep the fact and drop just those evidence rows);
  3. recomputes `entity_subjects` from the surviving `visible_facts`;
  4. re-queues affected non-terminal day jobs in place with surviving-only
     `input_ref` and a recomputed `input_version` (a stale version would be
     rejected by the generation fence forever); fully-forgotten jobs go to
     `dead` so they can never be claimed again;
  5. re-queues affected *applied* days as fresh jobs through
     `temporal_memory.queue.jobs.PostgresJobs.enqueue` (CR-3), passing only
     surviving record ids so forgotten records cannot resurrect;
  6. writes `forget_rules` rows so a re-import of the same records is blocked
     at capture (WP-D `ingest.triage`, contract request) and at apply.

Nothing resurrects: the validator/applier fence drops any attempt whose
`input_version` predates the bumped generation, records are `erased_at` so
job bundles never re-send forgotten text, and all reads go through
`visible_facts` (erased_at IS NULL, generation current, no forget-rule match).

DB access goes through `temporal_memory.db` (CR-1): `db.connect()` for the
forget transaction and `db.get_database()` for the queue's pool.
"""
from __future__ import annotations

from typing import Any

# Non-terminal job states that Forget may reset to queued. `submitted`
# (validated, awaiting apply) is included on purpose: a late submit for the
# old lease then fails the fence instead of applying stale facts. `leased`
# jobs are deliberately NOT touched: their in-flight attempt is fenced by
# the generation bump and rejected on submit.
REQUEUEABLE_STATES = ("queued", "expired", "submitted", "rejected")


def plan_forget(evidence: dict[str, list[str]], record_ids: list[str]) -> dict[str, list[str]]:
    """Pure split of affected facts. `evidence`: fact_id -> its record ids.

    Returns {"erase": [...], "trim": [...]}: erase facts whose evidence is
    entirely inside `record_ids`; trim keeps the fact and drops just those rows.
    Fully unit-testable without a database.
    """
    forgotten = set(record_ids)
    erase, trim = [], []
    for fid, rids in evidence.items():
        have = set(rids)
        if not have or not (have & forgotten):
            continue  # no overlap: untouched
        (erase if have <= forgotten else trim).append(fid)
    return {"erase": sorted(erase), "trim": sorted(trim)}


def forget_source(owner: str, record_ids: list[str]) -> dict[str, Any]:
    """Forget one source's records for an owner. Returns counts + new generation."""
    if not record_ids:
        return {"owner": owner, "records": 0, "facts_erased": 0, "facts_trimmed": 0,
                "entity_subjects_recomputed": 0, "jobs_requeued": 0, "jobs_enqueued": 0,
                "days_needing_requeue": [], "days_dead": [], "generation": None}
    rids = sorted(set(record_ids))
    forgotten = set(rids)
    out: dict[str, Any] = {"owner": owner, "records": 0, "facts_erased": 0,
                           "facts_trimmed": 0, "entity_subjects_recomputed": 0,
                           "jobs_requeued": 0, "jobs_enqueued": 0,
                           "days_needing_requeue": [], "days_dead": [],
                           "generation": None}
    from temporal_memory import db as _db  # CR-1: WP-A pool/connect, no local seam

    # Applied days to mint fresh survivor-only jobs for, after the forget
    # transaction commits: (day, surviving record ids).
    applied_requeue: list[tuple[str, list[str]]] = []

    conn = _db.connect()
    try:
        with conn:
            with conn.cursor() as cur:
                # 1) Generation bump + erasure. No aggregates in RETURNING:
                # collect per-row generations and take the max in Python.
                cur.execute(
                    "UPDATE records SET generation = generation + 1, "
                    "erased_at = coalesce(erased_at, now()) "
                    "WHERE owner = %(owner)s AND id = ANY(%(rids)s) "
                    "RETURNING generation",
                    {"owner": owner, "rids": rids},
                )
                generations = [r[0] for r in cur.fetchall()]
                if not generations:
                    return out
                gen = out["generation"] = max(generations)
                out["records"] = len(generations)

                # 2) Erase only-evidence facts, trim shared facts.
                cur.execute(
                    "SELECT fact_id, record_id FROM fact_evidence "
                    "WHERE owner = %(owner)s AND fact_id IN "
                    "(SELECT fact_id FROM fact_evidence WHERE owner = %(owner)s "
                    "AND record_id = ANY(%(rids)s))",
                    {"owner": owner, "rids": rids},
                )
                evidence: dict[str, list[str]] = {}
                for fid, rid in cur.fetchall():
                    evidence.setdefault(fid, []).append(rid)
                plan = plan_forget(evidence, rids)

                if plan["erase"]:
                    cur.execute(
                        "UPDATE facts SET erased_at = now(), "
                        "embedding = NULL, embedding_model = NULL, embedded_at = NULL "
                        "WHERE owner = %(owner)s AND erased_at IS NULL "
                        "AND id = ANY(%(fids)s)",
                        {"owner": owner, "fids": plan["erase"]},
                    )
                    out["facts_erased"] = cur.rowcount
                if plan["trim"]:
                    cur.execute(
                        "DELETE FROM fact_evidence WHERE owner = %(owner)s "
                        "AND fact_id = ANY(%(fids)s) AND record_id = ANY(%(rids)s)",
                        {"owner": owner, "fids": plan["trim"], "rids": rids},
                    )
                    out["facts_trimmed"] = len(plan["trim"])

                # 3) Recompute entity_subjects from surviving visible facts
                # (same derivation as the applier; owner-qualified join).
                cur.execute(
                    "DELETE FROM entity_subjects WHERE owner = %(owner)s",
                    {"owner": owner},
                )
                cur.execute(
                    "INSERT INTO entity_subjects (owner, entity_id, subject_id, "
                    "role, weight, fact_count, first_seen, last_seen) "
                    "SELECT vf.owner, fe.entity_id, vf.subject_id, "
                    "coalesce(fe.role, ''), "
                    "sum(CASE WHEN vf.status = 'active' THEN 1.0 ELSE 0.3 END), "
                    "count(*)::int, min(vf.valid_from), max(vf.valid_from) "
                    "FROM visible_facts vf "
                    "JOIN fact_entities fe ON fe.owner = vf.owner AND fe.fact_id = vf.id "
                    "WHERE vf.owner = %(owner)s "
                    "GROUP BY vf.owner, fe.entity_id, vf.subject_id, coalesce(fe.role, '')",
                    {"owner": owner},
                )
                out["entity_subjects_recomputed"] = cur.rowcount

                # 4/5) Affected day jobs, classified by state.
                cur.execute(
                    "SELECT id, day, state, input_ref FROM jobs "
                    "WHERE owner = %(owner)s AND kind IN ('extract.day', 'extract.live', 'extract.session') "
                    "AND input_ref && %(rids)s",
                    {"owner": owner, "rids": rids},
                )
                affected = cur.fetchall()
                days_needing: set[str] = set()
                days_dead: set[str] = set()
                for job_id, day, state, input_ref in affected:
                    survivors = [r for r in (input_ref or []) if r not in forgotten]
                    if state in REQUEUEABLE_STATES:
                        if survivors:
                            cur.execute(
                                "UPDATE jobs SET state = 'queued', fence_token = NULL, "
                                "lease_expires_at = NULL, worker_id = NULL, "
                                "input_ref = %(surv)s, "
                                "input_version = (SELECT coalesce(max(generation), 0) "
                                "FROM records WHERE owner = %(owner)s "
                                "AND id = ANY(%(surv)s)), updated_at = now() "
                                "WHERE id = %(jid)s",
                                {"owner": owner, "surv": survivors, "jid": job_id},
                            )
                            out["jobs_requeued"] += cur.rowcount
                        else:
                            # Nothing left to extract: never claimable again.
                            cur.execute(
                                "UPDATE jobs SET state = 'dead', fence_token = NULL, "
                                "lease_expires_at = NULL, worker_id = NULL, "
                                "updated_at = now() WHERE id = %(jid)s",
                                {"jid": job_id},
                            )
                    elif state == "applied":
                        if day is not None and survivors:
                            applied_requeue.append((day, survivors))
                            days_needing.add(day)
                    elif state == "dead":
                        if day is not None:
                            days_dead.add(day)
                    # leased: left alone; the generation fence rejects its
                    # late submit and no fact can resurrect.
                out["days_needing_requeue"] = sorted(days_needing)
                out["days_dead"] = sorted(days_dead)

                for rid in rids:
                    cur.execute(
                        "INSERT INTO forget_rules (owner, kind, value, created_at) "
                        "VALUES (%(owner)s, 'item', %(rid)s, now()) ON CONFLICT DO NOTHING",
                        {"owner": owner, "rid": rid},
                    )
                cur.execute(
                    "SELECT content_hash FROM records WHERE owner = %(owner)s AND id = ANY(%(rids)s)",
                    {"owner": owner, "rids": rids},
                )
                for (digest,) in cur.fetchall():
                    if not digest:
                        continue
                    cur.execute(
                        "INSERT INTO forget_rules (owner, kind, value, created_at) "
                        "VALUES (%(owner)s, 'item', %(digest)s, now()) ON CONFLICT DO NOTHING",
                        {"owner": owner, "digest": digest},
                    )
                _finish_owner(cur, owner)
    finally:
        conn.close()
    _invalidate(owner)

    # CR-3: mint fresh jobs for applied days through the real queue, with
    # surviving records only, after the forget has committed.
    if applied_requeue:
        from temporal_memory.queue.jobs import PostgresJobs

        jobs = PostgresJobs(_db.get_database())
        seen: set[tuple[str, tuple[str, ...]]] = set()
        for day, survivors in applied_requeue:
            key = (day, tuple(survivors))
            if key in seen:
                continue
            seen.add(key)
            jobs.enqueue(owner, "extract.day", survivors, priority=1, day=day)
            out["jobs_enqueued"] += 1
    return out


def _finish_owner(cur: Any, owner: str) -> None:
    """Drop evidence-less entities, aliases and links, then bump both cache versions."""
    cur.execute(
        """
        UPDATE links SET erased_at = now()
        WHERE owner = %(owner)s AND erased_at IS NULL
          AND evidence_fact_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM facts f
              WHERE f.owner = links.owner AND f.id = links.evidence_fact_id
                AND f.erased_at IS NULL
          )
        """,
        {"owner": owner},
    )
    cur.execute(
        """
        UPDATE entities e SET erased_at = now()
        WHERE e.owner = %(owner)s AND e.erased_at IS NULL
          AND EXISTS (
              SELECT 1 FROM fact_entities fe
              WHERE fe.owner = e.owner AND fe.entity_id = e.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM fact_entities fe
              JOIN facts f ON f.owner = fe.owner AND f.id = fe.fact_id AND f.erased_at IS NULL
              WHERE fe.owner = e.owner AND fe.entity_id = e.id
          )
        """,
        {"owner": owner},
    )
    cur.execute(
        """
        DELETE FROM entity_aliases a
        USING entities e
        WHERE a.owner = e.owner AND a.entity_id = e.id
          AND e.owner = %(owner)s AND e.erased_at IS NOT NULL
        """,
        {"owner": owner},
    )
    cur.execute(
        """
        UPDATE subjects s SET fact_count = (
            SELECT count(*)::int FROM facts f
            WHERE f.owner = s.owner AND f.subject_id = s.id
              AND f.erased_at IS NULL AND f.status <> 'history'
        )
        WHERE s.owner = %(owner)s
        """,
        {"owner": owner},
    )
    cur.execute(
        """
        UPDATE owners
        SET facts_version = facts_version + 1,
            privacy_revision = privacy_revision + 1
        WHERE id = %(owner)s
        """,
        {"owner": owner},
    )


def _invalidate(owner: str) -> None:
    from temporal_memory.live.context import invalidate_alias_cache

    invalidate_alias_cache(owner)


def _public(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "generation": int(raw.get("generation") or 0),
        "records": int(raw.get("records") or 0),
        "facts_erased": int(raw.get("facts_erased") or 0),
        "facts_trimmed": int(raw.get("facts_trimmed") or 0),
        "entity_subjects_recomputed": int(raw.get("entity_subjects_recomputed") or 0),
        "jobs_requeued": int(raw.get("jobs_requeued") or 0),
        "jobs_enqueued": int(raw.get("jobs_enqueued") or 0),
    }


def forget_fact(owner: str, fact_id: str) -> dict[str, Any]:
    """Erase one fact, its evidence, and anything left with no surviving evidence."""
    from temporal_memory import db as _db

    out: dict[str, Any] = {
        "owner": owner, "records": 0, "facts_erased": 0, "facts_trimmed": 0,
        "entity_subjects_recomputed": 0, "jobs_requeued": 0, "jobs_enqueued": 0,
        "generation": 0,
    }
    conn = _db.connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE facts SET erased_at = now(), "
                    "embedding = NULL, embedding_model = NULL, embedded_at = NULL "
                    "WHERE owner = %(owner)s AND id = %(fid)s AND erased_at IS NULL "
                    "RETURNING id",
                    {"owner": owner, "fid": fact_id},
                )
                if cur.fetchone() is None:
                    return out
                out["facts_erased"] = 1
                cur.execute(
                    "DELETE FROM fact_evidence WHERE owner = %(owner)s AND fact_id = %(fid)s",
                    {"owner": owner, "fid": fact_id},
                )
                cur.execute(
                    "INSERT INTO forget_rules (owner, kind, value, created_at) "
                    "VALUES (%(owner)s, 'item', %(fid)s, now()) ON CONFLICT DO NOTHING",
                    {"owner": owner, "fid": fact_id},
                )
                cur.execute("DELETE FROM entity_subjects WHERE owner = %(owner)s", {"owner": owner})
                cur.execute(
                    "INSERT INTO entity_subjects (owner, entity_id, subject_id, "
                    "role, weight, fact_count, first_seen, last_seen) "
                    "SELECT vf.owner, fe.entity_id, vf.subject_id, "
                    "coalesce(fe.role, ''), "
                    "sum(CASE WHEN vf.status = 'active' THEN 1.0 ELSE 0.3 END), "
                    "count(*)::int, min(vf.valid_from), max(vf.valid_from) "
                    "FROM visible_facts vf "
                    "JOIN fact_entities fe ON fe.owner = vf.owner AND fe.fact_id = vf.id "
                    "WHERE vf.owner = %(owner)s "
                    "GROUP BY vf.owner, fe.entity_id, vf.subject_id, coalesce(fe.role, '')",
                    {"owner": owner},
                )
                out["entity_subjects_recomputed"] = cur.rowcount
                _finish_owner(cur, owner)
                cur.execute(
                    "SELECT coalesce(max(generation), 0) FROM records WHERE owner = %(owner)s",
                    {"owner": owner},
                )
                out["generation"] = int(cur.fetchone()[0])
    finally:
        conn.close()
    _invalidate(owner)
    return out


def recorded_forget(
    owner: str,
    record_ids: list[str],
    fact_id: str | None,
    idempotency_key: str | None,
) -> dict[str, Any]:
    """One forget effect per (owner, idempotency_key), durable across processes."""
    import json

    from temporal_memory import db as _db

    key = (idempotency_key or "").strip()
    if not key:
        raw = forget_source(owner, list(record_ids)) if record_ids else _public({})
        public = _public(raw)
        if fact_id:
            fact_raw = forget_fact(owner, fact_id)
            public["facts_erased"] = int(public["facts_erased"]) + int(fact_raw["facts_erased"])
            public["generation"] = int(fact_raw.get("generation") or public["generation"])
            public["entity_subjects_recomputed"] = int(fact_raw["entity_subjects_recomputed"])
        return public

    conn = _db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                (owner, key),
            )
            cur.execute(
                "SELECT result FROM forget_requests WHERE owner = %s AND idempotency_key = %s",
                (owner, key),
            )
            row = cur.fetchone()
            if row is not None:
                payload = row[0]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                conn.commit()
                return dict(payload)
        raw = forget_source(owner, list(record_ids)) if record_ids else _public({})
        public = _public(raw)
        if fact_id:
            fact_raw = forget_fact(owner, fact_id)
            public["facts_erased"] = int(public["facts_erased"]) + int(fact_raw["facts_erased"])
            public["generation"] = int(fact_raw.get("generation") or public["generation"])
            public["entity_subjects_recomputed"] = int(fact_raw["entity_subjects_recomputed"])
        request = {"record_ids": list(record_ids), "fact_id": fact_id}
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO forget_requests (owner, idempotency_key, request, result) "
                "VALUES (%s, %s, %s::jsonb, %s::jsonb) "
                "ON CONFLICT (owner, idempotency_key) DO NOTHING",
                (owner, key, json.dumps(request), json.dumps(public)),
            )
        conn.commit()
        return public
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
