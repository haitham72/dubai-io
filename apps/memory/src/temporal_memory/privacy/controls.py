"""D19 account deletion and reversible, non-destructive memory controls."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import logging
import re
import uuid

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from temporal_memory.config import get_settings
from temporal_memory.models import HELD_BACK_ROOTS

WEIGHT_FLOOR = 0.01
SURFACE_WEIGHT_THRESHOLD = 0.10
log = logging.getLogger(__name__)


def owner_deleted(conn, owner: str) -> bool:
    row = conn.execute("SELECT deleted_from_external FROM owners WHERE id = %s", (owner,)).fetchone()
    return bool(row and row["deleted_from_external"])


def account_deleted(store, owner: str) -> bool:
    db = getattr(store, "db", None)
    if db is None:
        return False
    with db.connection() as conn:
        return owner_deleted(conn, owner)


def lock_active_owner(conn, owner: str) -> None:
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (owner,))
    if owner_deleted(conn, owner):
        raise HTTPException(403, "Account data has been deleted")


def invalidate_owner(owner: str, *, deleted: bool = False) -> None:
    from temporal_memory.core.retrieval import invalidate_learned_cache
    from temporal_memory.live.context import invalidate_alias_cache

    invalidate_alias_cache(owner)
    invalidate_learned_cache(owner)
    if deleted:
        from temporal_memory.core.embed import invalidate_owner_embeddings
        invalidate_owner_embeddings(owner)


def set_lowered(store, owner: str, body, *, lower: bool) -> dict:
    if sum(map(bool, (body.fact_id, body.subject_id, body.record_ids, body.source))) != 1:
        raise HTTPException(422, "Choose one fact, subject, source or set of records")
    at = datetime.now(timezone.utc).isoformat() if lower else None
    records = 0
    if not hasattr(store, "db"):
        return store.set_memory_lowered(owner, body, lower=lower)
    with store.db.transaction() as conn:
        lock_active_owner(conn, owner)
        if body.fact_id:
            changed = conn.execute(
                "UPDATE facts SET lowered_at = %s WHERE owner = %s AND id = %s AND erased_at IS NULL",
                (at, owner, body.fact_id),
            ).rowcount
        elif body.subject_id:
            changed = conn.execute(
                "UPDATE subjects SET lowered_at = %s WHERE owner = %s AND id = %s AND provenance = 'inferred'",
                (at, owner, body.subject_id),
            ).rowcount
        elif body.record_ids:
            ids = list(dict.fromkeys(body.record_ids))
            records = changed = conn.execute(
                "UPDATE records SET lowered_at = %s WHERE owner = %s AND id = ANY(%s) AND erased_at IS NULL",
                (at, owner, ids),
            ).rowcount
            if changed != len(ids):
                raise HTTPException(404, "Memory records not found")
        else:
            source = body.source.strip().lower()
            if not source:
                raise HTTPException(422, "Source is required")
            if lower:
                conn.execute(
                    "INSERT INTO lowered_sources(owner, source) VALUES (%s,%s) ON CONFLICT (owner, source) DO UPDATE SET lowered_at = now()",
                    (owner, source),
                )
            else:
                conn.execute("DELETE FROM lowered_sources WHERE owner = %s AND source = %s", (owner, source))
            records = conn.execute(
                "SELECT count(*) AS n FROM records WHERE owner = %s AND erased_at IS NULL "
                "AND memory_source_matches(source, id, %s)",
                (owner, source),
            ).fetchone()["n"]
            changed = 1
        if not changed:
            raise HTTPException(404, "Memory target not found")
        version = conn.execute(
            "UPDATE owners SET facts_version = facts_version + 1, privacy_revision = privacy_revision + 1 "
            "WHERE id = %s RETURNING facts_version", (owner,)
        ).fetchone()
        if version is None:
            raise HTTPException(404, "Memory owner not found")
        conn.execute("DELETE FROM story_cache WHERE owner = %s", (owner,))
    invalidate_owner(owner)
    return {"ok": True, "lowered": lower, "weight": WEIGHT_FLOOR if lower else None,
            "records": records, "affected": changed, "facts_erased": 0,
            "facts_version": version["facts_version"]}


def reinforce_recall(store, owner: str, ids: list[str]) -> dict[str, float]:
    """Refresh only owner-visible facts selected by an explicit recall."""
    if not ids or not hasattr(store, "db"):
        return {}
    with store.db.transaction() as conn:
        lock_active_owner(conn, owner)
        rows = conn.execute(
            """
            UPDATE facts f SET lowered_at = NULL, last_refreshed_at = clock_timestamp(),
                weight_steps = 0, refreshed_weight = LEAST(1.0, GREATEST(0.35, w.weight + 0.25))
            FROM visible_facts vf JOIN memory_fact_weights w USING (owner, id)
            WHERE (f.owner, f.id) = (vf.owner, vf.id) AND f.owner = %s AND f.id = ANY(%s)
              AND (f.provenance IN ('user_supplied', 'provider_confirmed') OR NOT EXISTS (
                  SELECT 1 FROM subjects s WHERE (s.owner, s.id) = (f.owner, f.subject_id)
                    AND (s.sensitive_cat IS NOT NULL OR lower(split_part(s.path, '/', 1)) = ANY(%s))
              ))
            RETURNING f.id, f.refreshed_weight
            """,
            (owner, ids, sorted(HELD_BACK_ROOTS)),
        ).fetchall()
        if rows:
            conn.execute("UPDATE owners SET facts_version = facts_version + 1 WHERE id = %s", (owner,))
            conn.execute("DELETE FROM story_cache WHERE owner = %s", (owner,))
    if rows:
        invalidate_owner(owner)
    return {row["id"]: row["refreshed_weight"] for row in rows}


def fact_states(store, owner: str, ids: list[str]) -> dict:
    db = getattr(store, "db", None)
    if db is None:
        is_lowered = getattr(store, "fact_lowered", None)
        return ({fid: {"lowered": is_lowered(owner, fid), "weight": 0.01 if is_lowered(owner, fid) else 1.0}
                 for fid in ids} if is_lowered else {})
    if not ids:
        return {}
    with db.connection() as conn:
        return {r["id"]: {"weight": r["weight"], "lowered": r["lowered"]}
                for r in conn.execute(
                    "SELECT id, weight, lowered FROM memory_fact_weights WHERE owner = %s AND id = ANY(%s)",
                    (owner, ids),
                )}


def learned_weights(conn, owner: str) -> dict[str, float]:
    rows = conn.execute(
        """
        SELECT lt.term_folded, COALESCE(MAX(CASE
            WHEN r.id IS NULL OR r.erased_at IS NOT NULL OR lr.id IS NOT NULL THEN 0.01
            WHEN w.weight IS NOT NULL THEN w.weight
            WHEN lts.had_fact THEN 0.01
            ELSE memory_weight(1.0, 1.0, memory_age_days(r.at, r.created_at::date), 0, 'inferred', false)
        END), 0.01) AS weight
        FROM learned_terms lt
        LEFT JOIN learned_term_sources lts USING (owner, term_folded)
        LEFT JOIN records r ON (r.owner, r.id) = (lts.owner, lts.record_id)
        LEFT JOIN memory_lowered_records lr ON (lr.owner, lr.id) = (r.owner, r.id)
        LEFT JOIN fact_evidence fe ON (fe.owner, fe.record_id) = (r.owner, r.id)
        LEFT JOIN visible_facts vf ON (vf.owner, vf.id) = (fe.owner, fe.fact_id)
        LEFT JOIN memory_fact_weights w ON (w.owner, w.id) = (vf.owner, vf.id)
        WHERE lt.owner = %s GROUP BY lt.term_folded
        """, (owner,)
    )
    return {row["term_folded"]: float(row["weight"]) for row in rows}


def weight_learned_index(conn, owner: str, index):
    from temporal_memory.vocab.loader import OwnerLearnedIndex
    if not index.nodes:
        return index
    weights = learned_weights(conn, owner)
    return OwnerLearnedIndex([
        replace(node, weight=weights[node.term_folded])
        for node in index.by_term.values()
        if weights.get(node.term_folded, 0.0) >= SURFACE_WEIGHT_THRESHOLD
    ])


def purge_redis(owner: str) -> bool:
    url = get_settings().redis_url
    if not url:
        raise HTTPException(503, "Redis purge unavailable; TM_REDIS_URL is unconfigured")
    import redis

    pattern = "*" + "".join("\\" + c if c in r"\*?[]" else c for c in owner) + "*"
    try:
        with redis.Redis.from_url(url, socket_timeout=5, socket_connect_timeout=5) as client:
            for key in client.scan_iter(match=pattern, count=250):
                if re.search(r"(?<![A-Za-z0-9-])" + re.escape(owner) + r"(?![A-Za-z0-9-])",
                             key.decode("utf-8", errors="replace") if isinstance(key, bytes) else key):
                    client.delete(key)
    except (redis.RedisError, OSError, ValueError) as exc:
        log.warning("Account deletion could not purge Redis (%s)", type(exc).__name__)
        raise HTTPException(503, "Redis purge unavailable; retry account deletion") from exc
    return True


def delete_account(store, owner: str) -> dict:
    with store.db.transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (owner,))
        row = conn.execute("SELECT deleted_at FROM owners WHERE id = %s FOR UPDATE", (owner,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO owners (id, label) VALUES (%s, '')", (owner,))
            row = {"deleted_at": None}
        purge_redis(owner)
        if row["deleted_at"] is None:
            # Store only coarse, allowlisted training signals. Unknown or mixed provenance is
            # excluded, as are all free text, entities, record IDs and precise timestamps.
            signals = conn.execute(
                """
                SELECT split_part(s.path, '/', 1) AS cluster, count(*) AS count
                FROM visible_facts f JOIN subjects s ON (s.owner, s.id) = (f.owner, f.subject_id)
                WHERE f.owner = %s AND s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) IN
                    ('career','learning','projects','events','home-money','travel')
                  AND EXISTS (SELECT 1 FROM fact_evidence e WHERE (e.owner,e.fact_id) = (f.owner,f.id))
                  AND NOT EXISTS (
                    SELECT 1 FROM fact_evidence e JOIN records r ON (r.owner,r.id) = (e.owner,e.record_id)
                    WHERE (e.owner,e.fact_id) = (f.owner,f.id)
                      AND (split_part(lower(r.source), ':', 1) NOT IN ('notes','whatsapp','manual')
                           OR lower(r.source) ~ 'gmail|calendar|youtube|takeout|google'
                           OR lower(r.id) ~ 'gmail|calendar|youtube|takeout|google'
                           OR lower(r.meta::text) ~ 'gmail|calendar|youtube|takeout|google')
                  )
                GROUP BY 1 ORDER BY 1
                """, (owner,)
            ).fetchall()
            conn.execute("INSERT INTO training_backups VALUES (%s, %s)", (uuid.uuid4(), Jsonb(signals)))
            row = conn.execute(
                """
                UPDATE owners SET deleted_from_external = true, deleted_at = now(),
                    facts_version = facts_version + 1, alias_version = alias_version + 1,
                    privacy_revision = privacy_revision + 1,
                    deletion_generation = 1 + (SELECT COALESCE(MAX(generation),0) FROM records WHERE owner = %s)
                WHERE id = %s RETURNING deleted_at
                """, (owner, owner)
            ).fetchone()
            conn.execute("UPDATE tokens SET revoked_at = now() WHERE owner = %s AND revoked_at IS NULL", (owner,))
            conn.execute(
                "UPDATE jobs SET state = 'cancelled', fence_token = NULL "
                "WHERE owner = %s AND state IN ('queued','leased')", (owner,)
            )
            conn.execute("DELETE FROM story_cache WHERE owner = %s", (owner,))
            # E13b (integrator-approved 2-line exception): purge anonymised query signals.
            from temporal_memory.vocab.similarity import purge_owner_query_signals
            purge_owner_query_signals(conn, owner)
    invalidate_owner(owner, deleted=True)
    redis_purged = purge_redis(owner)
    return {"ok": True, "deleted_from_external": True,
            "deleted_at": row["deleted_at"].isoformat(), "redis_purged": redis_purged}


def subject_states(store, owner: str) -> dict:
    db = getattr(store, "db", None)
    if db is None:
        return {}
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.lowered_at IS NOT NULL AS lowered,
                COALESCE(MAX(w.weight), 0.01) AS weight
            FROM subjects s
            LEFT JOIN visible_facts f ON (f.owner,f.subject_id) = (s.owner,s.id)
            LEFT JOIN memory_fact_weights w ON (w.owner,w.id) = (f.owner,f.id)
            WHERE s.owner = %s
            GROUP BY s.id, s.lowered_at
            """, (owner,)
        )
        return {r["id"]: {"weight": r["weight"], "lowered": r["lowered"]} for r in rows}
