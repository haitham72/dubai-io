"""Postgres implementations of the CR-TM bridge writes.

Kept out of graph_store.py so the retrieval workstream can edit that file.
`/search` calls `store.search_candidates` when that contract method exists
(U1c). Until it does, the SQL below applies `source_prefix` before LIMIT.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import uuid
from typing import Any

from fastapi import HTTPException

from temporal_memory.core.daytime import local_day
from temporal_memory.core.graph_store import _record_hash
from temporal_memory.models import Record
from temporal_memory.privacy.sensitive import pre_write

_PROVENANCE = {"user_supplied", "inferred", "provider_confirmed", "demo_fixture"}
_STATUSES = {"active", "hypothesis"}


def _postgres(store: Any) -> bool:
    return store is not None and hasattr(store, "db") and not hasattr(store, "records")


def _like_prefix(prefix: str) -> str:
    escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return escaped + "%"


def _fact_hash(text: str, subject_id: str) -> str:
    return hashlib.sha256(f"{subject_id}\0{text}".encode()).hexdigest()


def _subject(conn: Any, owner: str, subject_id: str) -> None:
    conn.execute(
        """
        INSERT INTO subjects (id, owner, path, label, kind)
        VALUES (%s, %s, %s, %s, 'topic')
        ON CONFLICT (owner, id) DO NOTHING
        """,
        (subject_id, owner, subject_id, subject_id),
    )


def ingest_records(store: Any, owner: str, body: Any) -> dict[str, Any]:
    """Batch upsert, hash dedupe, optional direct fact, and a real queue job."""
    records = list(body.records)
    for record in records:
        if pre_write(record.text) == "credential":
            raise HTTPException(status_code=400, detail="credential")
    fact = body.direct_fact
    if fact is not None:
        if not fact.evidence:
            raise HTTPException(status_code=422, detail="direct_fact.evidence must be non-empty")
        if pre_write(fact.text) == "credential":
            raise HTTPException(status_code=400, detail="credential")
        provenance = fact.provenance or "user_supplied"
        if provenance not in _PROVENANCE:
            raise HTTPException(status_code=422, detail="provenance is not allowlisted")
        status = getattr(fact, "status", None) or "active"
        if status not in _STATUSES:
            raise HTTPException(status_code=422, detail="status is not allowlisted")

    record_ids: list[str] = []
    fact_ids: list[str] = []
    quarantined = 0
    with store.db.transaction() as conn:
        owner_row = conn.execute("SELECT id FROM owners WHERE id = %s", (owner,)).fetchone()
        if owner_row is None:
            raise HTTPException(status_code=404, detail="owner not found")
        incoming_ids = [r.id for r in records]
        incoming_hashes = [
            _record_hash(Record(id=r.id, owner=owner, source=r.source, at=r.at, author=r.author, text=r.text))
            for r in records
        ]
        if incoming_ids or incoming_hashes:
            blocked = conn.execute(
                """
                SELECT 1 FROM forget_rules
                WHERE owner = %s AND kind = 'item'
                  AND (value = ANY(%s) OR value = ANY(%s))
                LIMIT 1
                """,
                (owner, incoming_ids, incoming_hashes),
            ).fetchone()
            if blocked is not None:
                raise HTTPException(status_code=409, detail="forget_rule")

        seen_hashes: dict[str, str] = {}
        for record, digest in zip(records, incoming_hashes):
            if digest in seen_hashes:
                record_ids.append(seen_hashes[digest])
                continue
            existing = conn.execute(
                """
                SELECT id FROM records
                WHERE owner = %s AND content_hash = %s AND erased_at IS NULL
                """,
                (owner, digest),
            ).fetchone()
            if existing is not None:
                seen_hashes[digest] = existing["id"]
                record_ids.append(existing["id"])
                continue
            conn.execute(
                """
                INSERT INTO records (id, owner, source, at, author, text, content_hash, generation)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
                ON CONFLICT (owner, id) DO UPDATE SET
                    source = EXCLUDED.source,
                    at = EXCLUDED.at,
                    author = EXCLUDED.author,
                    text = EXCLUDED.text,
                    content_hash = EXCLUDED.content_hash
                """,
                (record.id, owner, record.source, record.at, record.author, record.text, digest),
            )
            seen_hashes[digest] = record.id
            record_ids.append(record.id)

        if fact is not None:
            known = set(record_ids)
            if any(rid not in known for rid in fact.evidence):
                found = conn.execute(
                    """
                    SELECT id FROM records
                    WHERE owner = %s AND id = ANY(%s) AND erased_at IS NULL
                    """,
                    (owner, list(fact.evidence)),
                ).fetchall()
                known |= {row["id"] for row in found}
            if any(rid not in known for rid in fact.evidence):
                raise HTTPException(status_code=422, detail="direct_fact.evidence references an unknown record")
            gate = pre_write(fact.text)
            if gate:
                conn.execute(
                    "INSERT INTO quarantine (owner, category, record_ids) VALUES (%s, %s, %s::jsonb)",
                    (owner, gate, json.dumps(list(fact.evidence))),
                )
                quarantined = 1
            else:
                subject_id = fact.subject_id or getattr(fact, "subject_path", "") or "general/interests"
                _subject(conn, owner, subject_id)
                fid = f"df-{uuid.uuid4().hex[:8]}"
                status = getattr(fact, "status", None) or "active"
                provenance = fact.provenance or "user_supplied"
                conn.execute(
                    """
                    INSERT INTO facts (
                        id, owner, text, text_orig, subject_id, valid_from, status,
                        provenance, content_hash
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        fid, owner, fact.text, getattr(fact, "text_orig", None), subject_id,
                        fact.valid_from or "", status, provenance, _fact_hash(fact.text, subject_id),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation)
                    SELECT %s, %s, r.id, r.generation
                    FROM records r
                    WHERE r.owner = %s AND r.id = ANY(%s) AND r.erased_at IS NULL
                    """,
                    (owner, fid, owner, list(fact.evidence)),
                )
                conn.execute(
                    "UPDATE owners SET facts_version = facts_version + 1 WHERE id = %s",
                    (owner,),
                )
                fact_ids.append(fid)

    job_id = None
    if body.enqueue != "none" and record_ids:
        from temporal_memory.queue.jobs import PostgresJobs

        priority = 0 if body.enqueue == "extract.live" else 1
        owner_tz = "Asia/Dubai"
        with store.db.connection() as conn:
            tz_row = conn.execute("SELECT timezone FROM owners WHERE id = %s", (owner,)).fetchone()
            if tz_row and tz_row["timezone"]:
                owner_tz = tz_row["timezone"]
        day = local_day(records[0].at, owner_tz) if records and records[0].at else None
        job = PostgresJobs(store.db, store=store).enqueue(
            owner, body.enqueue, record_ids, priority=priority, day=day,
        )
        job_id = job.id
    if fact_ids:
        from temporal_memory.live.context import invalidate_alias_cache

        invalidate_alias_cache(owner)
    return {
        "ok": True,
        "record_ids": record_ids,
        "job_id": job_id,
        "fact_ids": fact_ids,
        "quarantined": quarantined,
    }


def forget(store: Any, owner: str, record_ids: list[str], fact_id: str | None, idempotency_key: str | None) -> dict[str, Any]:
    """Durable forget. The row in forget_requests is the idempotency record."""
    from temporal_memory.db import db as db_module
    from temporal_memory.privacy.forget import recorded_forget

    previous = db_module._DEFAULT_DB
    db_module._DEFAULT_DB = store.db
    try:
        return recorded_forget(owner, list(record_ids), fact_id, idempotency_key)
    finally:
        db_module._DEFAULT_DB = previous


def resolve_fact(store: Any, owner: str, fact_id: str, body: Any) -> dict[str, Any]:
    """Confirm, edit/supersede, or reject one fact. Bumps facts_version."""
    new_id: str | None = None
    with store.db.transaction() as conn:
        fact = conn.execute(
            """
            SELECT id, text, subject_id, valid_from, status
            FROM facts
            WHERE owner = %s AND id = %s AND erased_at IS NULL
            """,
            (owner, fact_id),
        ).fetchone()
        if fact is None:
            raise HTTPException(status_code=404, detail="Fact not found or forgotten")
        status = fact["status"]
        if body.action == "confirm":
            conn.execute(
                """
                UPDATE facts SET status = 'active', provenance = 'user_supplied'
                WHERE owner = %s AND id = %s
                """,
                (owner, fact_id),
            )
            status = "active"
        elif body.action in ("edit", "supersede"):
            text = (body.new_text or "").strip()
            if not text:
                raise HTTPException(status_code=422, detail="new_text is required")
            gate = pre_write(text)
            if gate == "credential":
                raise HTTPException(status_code=400, detail="credential")
            if gate:
                raise HTTPException(status_code=400, detail="sensitive")
            evidence = [
                row["record_id"]
                for row in conn.execute(
                    "SELECT record_id FROM fact_evidence WHERE owner = %s AND fact_id = %s ORDER BY record_id",
                    (owner, fact_id),
                ).fetchall()
            ]
            if body.evidence_record_id:
                known = conn.execute(
                    "SELECT id FROM records WHERE owner = %s AND id = %s AND erased_at IS NULL",
                    (owner, body.evidence_record_id),
                ).fetchone()
                if known is None:
                    raise HTTPException(status_code=422, detail="evidence_record_id is unknown")
                if body.evidence_record_id not in evidence:
                    evidence.append(body.evidence_record_id)
            new_id = f"rf-{uuid.uuid4().hex[:8]}"
            valid_to = body.valid_from or fact["valid_from"]
            conn.execute(
                """
                UPDATE facts
                SET status = 'superseded', valid_to = %s, superseded_by = %s
                WHERE owner = %s AND id = %s
                """,
                (valid_to, new_id, owner, fact_id),
            )
            _subject(conn, owner, fact["subject_id"])
            conn.execute(
                """
                INSERT INTO facts (
                    id, owner, text, subject_id, valid_from, status, provenance, content_hash
                )
                VALUES (%s, %s, %s, %s, %s, 'active', 'user_supplied', %s)
                """,
                (
                    new_id, owner, text, fact["subject_id"],
                    body.valid_from or fact["valid_from"], _fact_hash(text, fact["subject_id"]),
                ),
            )
            if evidence:
                conn.execute(
                    """
                    INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation)
                    SELECT %s, %s, r.id, r.generation
                    FROM records r
                    WHERE r.owner = %s AND r.id = ANY(%s) AND r.erased_at IS NULL
                    """,
                    (owner, new_id, owner, evidence),
                )
            status = "active"
        elif body.action == "reject":
            conn.execute(
                "UPDATE facts SET erased_at = now(), embedding = NULL, embedding_model = NULL, embedded_at = NULL WHERE owner = %s AND id = %s",
                (owner, fact_id),
            )
            conn.execute(
                "DELETE FROM fact_evidence WHERE owner = %s AND fact_id = %s",
                (owner, fact_id),
            )
            status = "rejected"
        version_row = conn.execute(
            """
            UPDATE owners SET facts_version = facts_version + 1
            WHERE id = %s RETURNING facts_version
            """,
            (owner,),
        ).fetchone()
    from temporal_memory.live.context import invalidate_alias_cache

    invalidate_alias_cache(owner)
    old_status = "superseded" if new_id else status
    return {
        "ok": True,
        "fact_id": fact_id,
        "new_fact_id": new_id,
        "status": status,  # legacy: status of the NEW fact for edit/supersede (kept for old clients)
        "old_fact": {"id": fact_id, "status": old_status},
        "new_fact": {"id": new_id, "status": "active"} if new_id else None,
        "facts_version": int(version_row["facts_version"]) if version_row else 0,
    }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return list(json.loads(value))
    return list(value)


def _sql_search(store: Any, owner: str, query: str, limit: int, source_prefix: str | None) -> list[dict[str, Any]]:
    clauses = ["vf.owner = %s", "(vf.text ILIKE %s OR coalesce(vf.text_orig, '') ILIKE %s)"]
    needle = f"%{query}%"
    params: list[Any] = [owner, needle, needle]
    if source_prefix:
        like = _like_prefix(source_prefix)
        clauses.append(
            """
            EXISTS (
                SELECT 1 FROM fact_evidence fe
                JOIN records r ON r.owner = fe.owner AND r.id = fe.record_id
                WHERE fe.owner = vf.owner AND fe.fact_id = vf.id
                  AND r.erased_at IS NULL AND r.source LIKE %s ESCAPE '\\'
            )
            """
        )
        clauses.append(
            """
            NOT EXISTS (
                SELECT 1 FROM fact_evidence fe
                JOIN records r ON r.owner = fe.owner AND r.id = fe.record_id
                WHERE fe.owner = vf.owner AND fe.fact_id = vf.id
                  AND r.erased_at IS NULL
                  AND r.source NOT LIKE %s ESCAPE '\\'
            )
            """
        )
        params.extend([like, like])
    params.append(limit)
    sql = f"""
        SELECT vf.id, vf.text, vf.subject_id, vf.status, vf.provenance, vf.valid_from,
               COALESCE((
                   SELECT json_agg(fe.record_id ORDER BY fe.record_id)
                   FROM fact_evidence fe
                   WHERE fe.owner = vf.owner AND fe.fact_id = vf.id
               ), '[]'::json) AS evidence,
               COALESCE((
                   SELECT json_agg(r.source ORDER BY r.id)
                   FROM fact_evidence fe
                   JOIN records r ON r.owner = fe.owner AND r.id = fe.record_id
                   WHERE fe.owner = vf.owner AND fe.fact_id = vf.id AND r.erased_at IS NULL
               ), '[]'::json) AS sources
        FROM visible_facts vf
        WHERE {' AND '.join(clauses)}
        ORDER BY vf.valid_from DESC, vf.id ASC
        LIMIT %s
    """
    with store.db.connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {
            "id": row["id"],
            "text": row["text"],
            "subject_id": row["subject_id"],
            "status": row["status"],
            "provenance": row["provenance"],
            "as_of": row["valid_from"],
            "evidence": _as_list(row["evidence"]),
            "sources": _as_list(row["sources"]),
        }
        for row in rows
    ]


def _hydrate_ranked_facts(store: Any, owner: str, ranked_ids: list[str], limit: int) -> list[dict[str, Any]]:
    if not ranked_ids or limit <= 0:
        return []
    target_ids = list(dict.fromkeys(ranked_ids))[:limit]
    with store.db.connection() as conn:
        rows = conn.execute(
            """
            SELECT f.id, f.text, f.subject_id, f.status, f.provenance, f.valid_from,
                   COALESCE((
                       SELECT json_agg(fe.record_id ORDER BY fe.record_id)
                       FROM fact_evidence fe
                       WHERE fe.owner = f.owner AND fe.fact_id = f.id
                   ), '[]'::json) AS evidence,
                   COALESCE((
                       SELECT json_agg(r.source ORDER BY r.id)
                       FROM fact_evidence fe
                       JOIN records r ON r.owner = fe.owner AND r.id = fe.record_id
                       WHERE fe.owner = f.owner AND fe.fact_id = f.id AND r.erased_at IS NULL
                   ), '[]'::json) AS sources
            FROM facts f
            WHERE f.owner = %s AND f.id = ANY(%s) AND (f.erased_at IS NULL)::int = 1
            """,
            (owner, target_ids),
        ).fetchall()
    by_id = {
        row["id"]: {
            "id": row["id"],
            "text": row["text"],
            "subject_id": row["subject_id"],
            "status": row["status"],
            "provenance": row["provenance"],
            "as_of": row["valid_from"],
            "evidence": _as_list(row["evidence"]),
            "sources": _as_list(row["sources"]),
        }
        for row in rows
    }
    return [by_id[fid] for fid in target_ids if fid in by_id]


def search_facts(store: Any, owner: str, query: str, limit: int, source_prefix: str | None) -> dict[str, Any]:
    """Prefer the contract method and hydrate exact ranked IDs by PK; fall back to substring SQL when empty."""
    fn = getattr(store, "search_candidates", None)
    if callable(fn):
        params = inspect.signature(fn).parameters
        kwargs: dict[str, Any] = {}
        if "limit" in params:
            kwargs["limit"] = limit
        if "source_prefix" in params:
            kwargs["source_prefix"] = source_prefix
        if source_prefix is None or "source_prefix" in params:
            candidates = fn(owner, query, **kwargs)
            ids = []
            for cand in candidates:
                if isinstance(cand, dict):
                    ids.append(str(cand.get("fact_id") or cand.get("id")))
                elif isinstance(cand, (tuple, list)):
                    ids.append(str(cand[0]))
                else:
                    ids.append(str(getattr(cand, "fact_id", cand)))
            if ids:
                return {"ok": True, "facts": _hydrate_ranked_facts(store, owner, ids, limit)}
    return {"ok": True, "facts": _sql_search(store, owner, query, limit, source_prefix)}
