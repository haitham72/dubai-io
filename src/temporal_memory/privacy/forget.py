"""Forget-by-source with a generation fence (WP-C). Implements plan A5 + §3.2.

`forget_source(owner, record_ids)`:
  1. bumps `records.generation` for those records;
  2. sets `erased_at` on facts whose evidence is ONLY those records (facts with
     other surviving evidence keep the fact and drop just those evidence rows);
  3. recomputes `entity_subjects` from the surviving facts;
  4. re-queues affected non-terminal day jobs (queued/expired/submitted/rejected
     -> queued; their attempts are invalidated by the fence);
  5. writes `forget_rules` rows so a re-import of the same records is blocked.

Nothing resurrects: the validator/applier fence (WP-A) drops any attempt whose
`input_version` predates the bumped generation, and all reads go through
`visible_facts` (erased_at IS NULL, no forget-rule match). Days whose jobs had
already applied are returned as `days_needing_requeue` — minting fresh job rows
is WP-A's `Jobs.enqueue` (contract request CR-3); this module never invents jobs.

Table names follow planaudit.md v2.1 §3.2 as applied to the standalone repo
(v2.1 box §11: no `mem_` prefix; `connector_records` is `records`). The DDL
itself is WP-A's (`db/schema.sql`); until it lands, the DB path raises a clear
error and the DB tests are xfail.
"""
from __future__ import annotations

import os
from typing import Any

# Non-terminal job states that Forget may reset to queued. `submitted` (validated,
# awaiting apply) is included on purpose: a late submit for the old lease then
# fails the fence instead of applying stale facts.
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


def _connect():
    """DB seam. WP-A's `temporal_memory.db` helper wins when it lands (CR-1);
    until then, fall back to TM_DATABASE_URL via psycopg. Raises RuntimeError
    with an actionable message when neither exists.
    """
    try:
        from temporal_memory import db as _db  # WP-A, not landed yet

        connect = getattr(_db, "connect", None) or getattr(_db, "get_connection", None)
        if connect is not None:
            return connect()
    except ImportError:
        pass
    dsn = os.environ.get("TM_DATABASE_URL", "")
    if not dsn:
        raise RuntimeError(
            "forget_source needs a database: WP-A temporal_memory.db is not landed "
            "and TM_DATABASE_URL is not set (CR-1)."
        )
    import psycopg

    return psycopg.connect(dsn)


def forget_source(owner: str, record_ids: list[str]) -> dict[str, Any]:
    """Forget one source's records for an owner. Returns counts + new generation."""
    if not record_ids:
        return {"owner": owner, "records": 0, "facts_erased": 0, "facts_trimmed": 0,
                "entity_subjects_recomputed": 0, "jobs_requeued": 0,
                "days_needing_requeue": [], "generation": None}
    rids = sorted(set(record_ids))
    out: dict[str, Any] = {"owner": owner, "records": 0, "facts_erased": 0,
                           "facts_trimmed": 0, "entity_subjects_recomputed": 0,
                           "jobs_requeued": 0, "days_needing_requeue": [],
                           "generation": None}
    conn = _connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE records SET generation = generation + 1 "
                    "WHERE owner = %(owner)s AND id = ANY(%(rids)s) "
                    "RETURNING max(generation)",
                    {"owner": owner, "rids": rids},
                )
                row = cur.fetchone()
                if row is None or row[0] is None:
                    return out
                gen = out["generation"] = row[0]
                cur.execute("SELECT count(*) FROM records WHERE owner = %(owner)s "
                            "AND id = ANY(%(rids)s)",
                            {"owner": owner, "rids": rids})
                out["records"] = cur.fetchone()[0]

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
                        "UPDATE facts SET erased_at = now() "
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

                # Recompute entity_subjects from surviving facts: drop pairs with
                # no visible facts left, recount the rest (role = most common
                # surviving role; weight is WP-A applier's formula — untouched).
                cur.execute(
                    "DELETE FROM entity_subjects es WHERE es.owner = %(owner)s AND NOT EXISTS "
                    "(SELECT 1 FROM fact_entities fe JOIN facts f ON f.id = fe.fact_id "
                    "WHERE fe.owner = %(owner)s AND fe.entity_id = es.entity_id "
                    "AND f.subject_id = es.subject_id AND f.erased_at IS NULL)",
                    {"owner": owner},
                )
                dropped = cur.rowcount
                cur.execute(
                    "WITH agg AS (SELECT fe.entity_id, f.subject_id AS subject_id, "
                    "count(*) AS c, min(f.valid_from) AS first_seen, "
                    "max(coalesce(f.valid_to, f.valid_from)) AS last_seen "
                    "FROM fact_entities fe JOIN facts f ON f.id = fe.fact_id "
                    "WHERE fe.owner = %(owner)s AND f.erased_at IS NULL "
                    "GROUP BY 1, 2) "
                    "UPDATE entity_subjects es SET fact_count = agg.c, "
                    "first_seen = agg.first_seen, last_seen = agg.last_seen "
                    "FROM agg WHERE es.owner = %(owner)s "
                    "AND es.entity_id = agg.entity_id AND es.subject_id = agg.subject_id",
                    {"owner": owner},
                )
                out["entity_subjects_recomputed"] = dropped + cur.rowcount

                # Re-queue affected live jobs; collect applied days for WP-A.
                cur.execute(
                    "UPDATE jobs SET state = 'queued', fence_token = NULL, "
                    "lease_expires_at = NULL, worker_id = NULL "
                    "WHERE owner = %(owner)s AND kind = 'extract.day' "
                    "AND state = ANY(%(states)s) AND input_ref && %(rids)s "
                    "RETURNING id",
                    {"owner": owner, "states": list(REQUEUEABLE_STATES), "rids": rids},
                )
                out["jobs_requeued"] = len(cur.fetchall())
                cur.execute(
                    "SELECT DISTINCT day FROM jobs WHERE owner = %(owner)s "
                    "AND kind = 'extract.day' AND day IS NOT NULL "
                    "AND input_ref && %(rids)s AND state NOT IN ('queued', 'leased')",
                    {"owner": owner, "rids": rids},
                )
                out["days_needing_requeue"] = sorted(r[0] for r in cur.fetchall()
                                                    if r[0] is not None)

                for rid in rids:
                    cur.execute(
                        "INSERT INTO forget_rules (owner, kind, value, created_at) "
                        "VALUES (%(owner)s, 'item', %(rid)s, now()) ON CONFLICT DO NOTHING",
                        {"owner": owner, "rid": rid},
                    )
    finally:
        conn.close()
    return out
