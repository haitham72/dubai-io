"""Postgres-backed job queue implementing the Jobs protocol (WP-A)."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
from typing import Any
import uuid

from temporal_memory.config import get_settings
from temporal_memory.core.extract import OUTPUT_SCHEMA, PROMPT_VERSION, build_system_prompt
from temporal_memory.db.db import Database
from temporal_memory.models import (
    Attempt,
    Job,
    JobBundle,
    JobKind,
    Owner,
    Pool,
    Priority,
    Record,
    Verdict,
    Worker,
)
from temporal_memory.queue.outbox import enqueue_outbox_row


def _row_to_job(row: dict[str, Any]) -> Job:
    raw_ref = row["input_ref"]
    input_ref = list(raw_ref) if isinstance(raw_ref, list) else list(json.loads(raw_ref or "[]"))
    lease = row.get("lease_expires_at")
    lease_str = lease.isoformat() if isinstance(lease, datetime) else lease
    return Job(
        id=row["id"],
        owner=row["owner"],
        kind=row["kind"],
        priority=int(row["priority"]),  # type: ignore[arg-type]
        pool=row["pool"],
        input_ref=input_ref,
        input_version=int(row["input_version"]),
        context_hash=row["context_hash"] or "",
        prompt_version=row["prompt_version"],
        day=row.get("day"),
        state=row["state"],
        attempt_no=int(row["attempt_no"]),
        fence_token=row.get("fence_token"),
        worker_id=row.get("worker_id"),
        lease_expires_at=lease_str,
    )


def _row_to_owner(row: dict[str, Any] | None) -> Owner | None:
    if row is None:
        return None
    raw_aliases = row.get("self_aliases") or []
    aliases = list(raw_aliases) if isinstance(raw_aliases, list) else list(json.loads(raw_aliases))
    return Owner(
        id=row["id"],
        label=row["label"],
        kind=row["kind"],
        display_name=row.get("display_name") or "",
        self_aliases=[str(a) for a in aliases],
        timezone=row.get("timezone") or "Asia/Dubai",
    )


def _row_to_record(row: dict[str, Any]) -> Record:
    return Record(
        id=row["id"],
        owner=row["owner"],
        source=row["source"],
        at=row["at"],
        author=row.get("author") or "",
        text=row["text"],
        generation=int(row.get("generation") or 0),
    )


def _call_validate(
    validate_fn: Any,
    job: Job,
    bundle: JobBundle,
    attempt: Attempt,
    *,
    existing_hashes: set[str],
    existing_norm_subjects: set[tuple[str, str]],
    current_generation: int,
    owner_obj: Owner | None,
) -> Verdict:
    sig = inspect.signature(validate_fn)
    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    kwargs: dict[str, Any] = {}
    if has_varkw or "existing_hashes" in sig.parameters:
        kwargs["existing_hashes"] = existing_hashes
    if has_varkw or "existing_norm_subjects" in sig.parameters:
        kwargs["existing_norm_subjects"] = existing_norm_subjects
    if has_varkw or "current_generation" in sig.parameters:
        kwargs["current_generation"] = current_generation
    if has_varkw or "owner_obj" in sig.parameters:
        kwargs["owner_obj"] = owner_obj
    return validate_fn(job, bundle, attempt, **kwargs)


def _call_apply(
    apply_fn: Any,
    owner: str,
    job: Job,
    attempt: Attempt,
    *,
    db: Database,
    bundle: JobBundle,
) -> Verdict:
    sig = inspect.signature(apply_fn)
    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    kwargs: dict[str, Any] = {}
    if has_varkw or "db" in sig.parameters:
        kwargs["db"] = db
    if has_varkw or "bundle" in sig.parameters:
        kwargs["bundle"] = bundle
    return apply_fn(owner, job, attempt, **kwargs)


class PostgresJobs:
    """Transactional Postgres job queue with SKIP LOCKED claims and fenced submissions."""

    def __init__(self, db: Database, store: Any = None) -> None:
        self.db = db
        self._store = store

    def _get_store(self) -> Any:
        if self._store is None:
            from temporal_memory.core.graph_store import PostgresGraphStore  # type: ignore[import-not-found]

            self._store = PostgresGraphStore(self.db)
        return self._store

    def _fetch_bundle_inputs(
        self,
        conn: Any,
        job: Job,
    ) -> tuple[Owner | None, list[Record]]:
        owner_row = conn.execute(
            "SELECT id, label, kind, display_name, self_aliases, timezone FROM owners WHERE id = %s",
            (job.owner,),
        ).fetchone()
        if job.input_ref:
            rec_rows = conn.execute(
                """
                SELECT id, owner, source, at, author, text, generation
                FROM records
                WHERE owner = %s AND id = ANY(%s) AND erased_at IS NULL
                ORDER BY at ASC, id ASC
                """,
                (job.owner, job.input_ref),
            ).fetchall()
        else:
            rec_rows = []
        return _row_to_owner(owner_row), [_row_to_record(r) for r in rec_rows]

    def _build_bundle(
        self,
        job: Job,
        owner_obj: Owner | None,
        records: list[Record],
    ) -> JobBundle:
        context = self._get_store().scoped_context(job.owner, records)
        return JobBundle(
            job=job,
            records=records,
            context=context,
            system_prompt=build_system_prompt(owner_obj),
            output_schema=OUTPUT_SCHEMA,
        )

    def enqueue(
        self,
        owner: str,
        kind: JobKind,
        record_ids: list[str],
        priority: Priority,
        pool: Pool = "internal",
        day: str | None = None,
        *,
        sensitive_flag: bool = False,
    ) -> Job:
        sorted_ids = sorted(record_ids)
        prompt_version = PROMPT_VERSION
        cfg = get_settings()

        with self.db.transaction() as conn:
            if sorted_ids:
                row = conn.execute(
                    """
                    SELECT COALESCE(MAX(generation), 0) AS max_gen
                    FROM records
                    WHERE owner = %s AND id = ANY(%s)
                    """,
                    (owner, sorted_ids),
                ).fetchone()
                input_version = int(row["max_gen"]) if row else 0
            else:
                input_version = 0

            key_payload = json.dumps(
                [owner, kind, sorted_ids, input_version, prompt_version],
                separators=(",", ":"),
            )
            idempotency_key = hashlib.sha256(key_payload.encode("utf-8")).hexdigest()

            fallback_at: datetime | None = None
            if pool == "owner-device":
                delay = cfg.p0_fallback_seconds if priority == 0 else cfg.p1_fallback_seconds
                fallback_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

            job_id = f"job_{uuid.uuid4().hex[:16]}"
            inserted = conn.execute(
                """
                INSERT INTO jobs (
                    id, owner, kind, priority, pool, input_ref, input_version,
                    context_hash, prompt_version, day, sensitive_flag, fallback_at, idempotency_key
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING *
                """,
                (
                    job_id,
                    owner,
                    kind,
                    int(priority),
                    pool,
                    sorted_ids,
                    input_version,
                    "",
                    prompt_version,
                    day,
                    sensitive_flag,
                    fallback_at,
                    idempotency_key,
                ),
            ).fetchone()

            if inserted is not None:
                enqueue_outbox_row(conn, inserted["id"], int(priority))
                return _row_to_job(inserted)

            existing = conn.execute(
                "SELECT * FROM jobs WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
            assert existing is not None
            return _row_to_job(existing)

    def claim(
        self,
        worker: Worker,
        pools: list[Pool],
        owner: str | None = None,
        day_from: str | None = None,
        day_to: str | None = None,
        limit: int = 1,
    ) -> list[JobBundle]:
        if not pools or limit <= 0:
            return []
        if worker.owner is not None:
            if owner is not None and owner != worker.owner:
                return []
            effective_owner: str | None = worker.owner
        else:
            effective_owner = owner

        cfg = get_settings()
        clauses = [
            "state = 'queued'",
            "pool = ANY(%s)",
            "not_before <= now()",
            "(sensitive_flag = FALSE OR pool = 'internal')",
        ]
        params: list[Any] = [list(pools)]
        if effective_owner is not None:
            clauses.append("owner = %s")
            params.append(effective_owner)
        if day_from is not None:
            clauses.append("day >= %s")
            params.append(day_from)
        if day_to is not None:
            clauses.append("day <= %s")
            params.append(day_to)

        where_sql = " AND ".join(clauses)
        params.extend([int(limit), worker.id, str(cfg.lease_seconds)])

        sql = f"""
            WITH picked AS (
                SELECT id
                FROM jobs
                WHERE {where_sql}
                ORDER BY priority ASC, created_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            UPDATE jobs j
            SET state = 'leased',
                attempt_no = j.attempt_no + 1,
                fence_token = gen_random_uuid()::text,
                worker_id = %s,
                lease_expires_at = now() + (%s || ' seconds')::interval,
                updated_at = now()
            FROM picked
            WHERE j.id = picked.id
            RETURNING j.*
        """

        claimed_inputs: list[tuple[Job, Owner | None, list[Record]]] = []
        with self.db.transaction() as conn:
            rows = conn.execute(sql, params).fetchall()
            rows.sort(key=lambda r: (int(r["priority"]), r.get("day") or "", r["created_at"]))
            for row in rows:
                job = _row_to_job(row)
                owner_obj, records = self._fetch_bundle_inputs(conn, job)
                claimed_inputs.append((job, owner_obj, records))

        return [self._build_bundle(job, owner_obj, records) for job, owner_obj, records in claimed_inputs]

    def claim_by_id(self, job_id: str, worker: Worker) -> JobBundle | None:
        cfg = get_settings()
        with self.db.transaction() as conn:
            row = conn.execute(
                """
                UPDATE jobs
                SET state = 'leased',
                    attempt_no = attempt_no + 1,
                    fence_token = gen_random_uuid()::text,
                    worker_id = %s,
                    lease_expires_at = now() + (%s || ' seconds')::interval,
                    updated_at = now()
                WHERE id = %s
                  AND state = 'queued'
                  AND (sensitive_flag = FALSE OR pool = 'internal')
                  AND (%s::text IS NULL OR owner = %s)
                RETURNING *
                """,
                (worker.id, str(cfg.lease_seconds), job_id, worker.owner, worker.owner),
            ).fetchone()
            if row is None:
                return None
            job = _row_to_job(row)
            owner_obj, records = self._fetch_bundle_inputs(conn, job)

        return self._build_bundle(job, owner_obj, records)

    def heartbeat(self, job_id: str, fence_token: str) -> bool:
        cfg = get_settings()
        with self.db.transaction() as conn:
            row = conn.execute(
                """
                UPDATE jobs
                SET lease_expires_at = now() + (%s || ' seconds')::interval,
                    updated_at = now()
                WHERE id = %s
                  AND state = 'leased'
                  AND fence_token = %s
                RETURNING id
                """,
                (str(cfg.lease_seconds), job_id, fence_token),
            ).fetchone()
            return row is not None

    def submit(self, attempt: Attempt) -> Verdict:
        from temporal_memory.core import applier, validator  # type: ignore[import-not-found]

        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = %s", (attempt.job_id,)).fetchone()
            if row is None:
                return Verdict(ok=False, reasons=["job_not_found"])
            job = _row_to_job(row)
            owner_obj, records = self._fetch_bundle_inputs(conn, job)
            if job.input_ref:
                gen_row = conn.execute(
                    "SELECT COALESCE(MAX(generation), 0) AS max_gen FROM records WHERE owner = %s AND id = ANY(%s)",
                    (job.owner, job.input_ref),
                ).fetchone()
                current_gen = int(gen_row["max_gen"]) if gen_row else 0
            else:
                current_gen = 0
            hash_rows = conn.execute(
                """
                SELECT f.content_hash, s.path AS subject_path, f.text
                FROM facts f
                LEFT JOIN subjects s ON s.id = f.subject_id AND s.owner = f.owner
                WHERE f.owner = %s AND f.erased_at IS NULL AND f.status = 'active'
                """,
                (job.owner,),
            ).fetchall()
            existing_hashes = {str(r["content_hash"]) for r in hash_rows if r.get("content_hash")}
            existing_norm_subjects = {
                (str(r["subject_path"]), str(r["text"]))
                for r in hash_rows
                if r.get("subject_path") and r.get("text")
            }

        bundle = self._build_bundle(job, owner_obj, records)
        verdict = _call_validate(
            validator.validate,
            job,
            bundle,
            attempt,
            existing_hashes=existing_hashes,
            existing_norm_subjects=existing_norm_subjects,
            current_generation=current_gen,
            owner_obj=owner_obj,
        )
        if verdict.ok:
            verdict = _call_apply(applier.apply, job.owner, job, attempt, db=self.db, bundle=bundle)

        new_state = "applied" if verdict.ok else "rejected"
        verdict_str = "applied" if verdict.ok else f"rejected:{','.join(verdict.reasons)}"
        output_json = json.dumps(asdict(attempt.output)) if attempt.output is not None else None

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET state = %s,
                    updated_at = now()
                WHERE id = %s AND fence_token = %s
                """,
                (new_state, job.id, attempt.fence_token),
            )
            conn.execute(
                """
                INSERT INTO job_attempts (
                    id, job_id, owner, attempt_no, fence_token, worker_id, worker_kind,
                    model, prompt_version, started_at, finished_at,
                    tokens_in, tokens_out, cost_usd, output_json, verdict
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                    %s, %s, %s, %s::jsonb, %s
                )
                """,
                (
                    f"att_{uuid.uuid4().hex[:16]}",
                    job.id,
                    job.owner,
                    int(attempt.attempt_no),
                    attempt.fence_token,
                    attempt.worker_id,
                    attempt.worker_kind,
                    attempt.model,
                    attempt.prompt_version,
                    attempt.started_at,
                    attempt.finished_at,
                    int(attempt.tokens_in),
                    int(attempt.tokens_out),
                    float(attempt.cost_usd),
                    output_json,
                    verdict_str,
                ),
            )
        return verdict
