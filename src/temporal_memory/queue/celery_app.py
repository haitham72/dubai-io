"""Celery application configuration for temporal-memory background workers (WP-A)."""
from __future__ import annotations

from celery import Celery
from kombu import Queue

from temporal_memory.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "temporal_memory",
    broker=_settings.broker_url,
    include=["temporal_memory.queue.worker"],
)

celery_app.conf.update(
    task_ignore_result=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="mem.p1",
    task_queues=(
        Queue("mem.p0"),
        Queue("mem.p1"),
        Queue("mem.p3"),
    ),
    task_routes={
        "memory.run_job": {"queue": "mem.p1"},
        "memory.reconcile": {"queue": "mem.p3"},
    },
    beat_schedule={
        "memory-reconcile-60s": {
            "task": "memory.reconcile",
            "schedule": 60.0,
        },
    },
)

app = celery_app
