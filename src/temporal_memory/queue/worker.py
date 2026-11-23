"""Celery worker tasks for running extraction jobs and reconciling outbox/leases (WP-A)."""
from __future__ import annotations

import os
import socket
from typing import Any

from temporal_memory.config import get_settings
from temporal_memory.core import extract
from temporal_memory.db.db import Database, get_database
from temporal_memory.models import Worker, WorkerKind
from temporal_memory.queue.celery_app import celery_app
from temporal_memory.queue.jobs import PostgresJobs
from temporal_memory.queue.outbox import reconcile as reconcile_outbox


def _default_runner_and_model() -> tuple[str, str, WorkerKind]:
    cfg = get_settings()
    has_key = bool(cfg.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"))
    runner = os.environ.get("TM_WORKER_RUNNER") or ("anthropic" if has_key else "lmstudio")
    if runner == "anthropic":
        return runner, cfg.cloud_model, "internal-cloud"
    if runner == "lmstudio":
        return runner, cfg.lmstudio_model, "internal-local"
    return runner, os.environ.get("TM_WORKER_MODEL", "default"), "agent-cli"


@celery_app.task(name="memory.run_job")
def run_job(
    job_id: str,
    *,
    runner: str | None = None,
    model: str | None = None,
    db: Database | None = None,
    jobs: PostgresJobs | None = None,
) -> dict[str, Any]:
    """Claim a queued job by id, run extraction if acquired, and submit the attempt."""
    default_runner, default_model, default_kind = _default_runner_and_model()
    used_runner = runner or default_runner
    used_model = model or default_model
    worker_kind: WorkerKind = (
        "internal-cloud"
        if used_runner == "anthropic"
        else ("internal-local" if used_runner == "lmstudio" else default_kind)
    )
    worker = Worker(
        id=f"celery-{socket.gethostname()}-{os.getpid()}",
        kind=worker_kind,
        model=used_model,
        runner=used_runner,
    )
    jobs_svc = jobs or PostgresJobs(db or get_database())
    bundle = jobs_svc.claim_by_id(job_id, worker)
    if bundle is None:
        return {"status": "skipped", "job_id": job_id}

    attempt = extract.run(bundle, used_runner, used_model)
    attempt.worker_id = worker.id
    attempt.worker_kind = worker.kind
    verdict = jobs_svc.submit(attempt)
    return {
        "status": "applied" if verdict.ok else "rejected",
        "job_id": job_id,
        "reasons": list(verdict.reasons),
    }


@celery_app.task(name="memory.reconcile")
def reconcile(db: Database | None = None) -> dict[str, int]:
    """Republish pending outbox rows, trigger fallback, and requeue/dead-letter expired leases."""
    return reconcile_outbox(db or get_database())
