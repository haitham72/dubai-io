"""Transactional outbox publisher and lease/fallback reconciler (WP-A)."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Callable

from temporal_memory.db.db import Database

logger = logging.getLogger(__name__)


def queue_for_priority(priority: int) -> str:
    """Map job priority to Celery queue name."""
    if priority == 0:
        return "mem.p0"
    if priority == 1:
        return "mem.p1"
    return "mem.p3"


def enqueue_outbox_row(conn: Any, job_id: str, priority: int) -> None:
    """Insert an unpublished outbox row inside an active job-enqueue transaction."""
    conn.execute(
        """
        INSERT INTO outbox (job_id, priority)
        VALUES (%s, %s)
        ON CONFLICT (job_id) DO NOTHING
        """,
        (job_id, priority),
    )


def _default_send(job_id: str, priority: int) -> None:
    from temporal_memory.queue.celery_app import celery_app

    celery_app.send_task(
        "memory.run_job",
        args=[job_id],
        queue=queue_for_priority(priority),
    )


def publish_pending(
    db: Database,
    *,
    send_fn: Callable[[str, int], None] | None = None,
) -> int:
    """Publish all pending outbox rows and mark published_at on success."""
    sender = send_fn or _default_send
    published = 0
    with db.transaction() as conn:
        rows = conn.execute(
            """
            SELECT id, job_id, priority
            FROM outbox
            WHERE published_at IS NULL
            ORDER BY id ASC
            FOR UPDATE SKIP LOCKED
            """
        ).fetchall()
        for row in rows:
            try:
                sender(row["job_id"], int(row["priority"]))
            except Exception as exc:
                logger.warning("Failed to publish outbox row %s (job=%s): %s", row["id"], row["job_id"], exc)
                continue
            conn.execute(
                "UPDATE outbox SET published_at = now() WHERE id = %s",
                (row["id"],),
            )
            published += 1
    return published


def reconcile(
    db: Database,
    *,
    send_fn: Callable[[str, int], None] | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Republish pending outbox rows, trigger owner-device fallback, and requeue/dead-letter expired leases."""
    ts = now or datetime.now(timezone.utc)
    republished = publish_pending(db, send_fn=send_fn)

    with db.transaction() as conn:
        fallback_rows = conn.execute(
            """
            UPDATE jobs
            SET pool = 'internal',
                updated_at = now()
            WHERE state = 'queued'
              AND pool = 'owner-device'
              AND fallback_at IS NOT NULL
              AND fallback_at <= %s
            RETURNING id, priority
            """,
            (ts,),
        ).fetchall()

        lease_rows = conn.execute(
            """
            UPDATE jobs
            SET state = CASE WHEN attempt_no >= 3 THEN 'dead' ELSE 'queued' END,
                fence_token = CASE WHEN attempt_no >= 3 THEN fence_token ELSE NULL END,
                worker_id = CASE WHEN attempt_no >= 3 THEN worker_id ELSE NULL END,
                lease_expires_at = CASE WHEN attempt_no >= 3 THEN lease_expires_at ELSE NULL END,
                updated_at = now()
            WHERE state = 'leased'
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at <= %s
            RETURNING id, priority, state
            """,
            (ts,),
        ).fetchall()

        to_dispatch = list(fallback_rows) + [r for r in lease_rows if r["state"] == "queued"]
        for row in to_dispatch:
            conn.execute(
                """
                INSERT INTO outbox (job_id, priority, published_at)
                VALUES (%s, %s, NULL)
                ON CONFLICT (job_id) DO UPDATE
                SET priority = EXCLUDED.priority,
                    published_at = NULL
                """,
                (row["id"], int(row["priority"])),
            )

    requeued = sum(1 for r in lease_rows if r["state"] == "queued")
    dead = sum(1 for r in lease_rows if r["state"] == "dead")
    return {
        "republished": republished,
        "fallback_to_internal": len(fallback_rows),
        "requeued": requeued,
        "dead": dead,
    }
