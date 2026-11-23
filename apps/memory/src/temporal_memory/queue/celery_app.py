"""Celery application configuration for temporal-memory background workers (WP-A)."""
from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

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
    task_queues=tuple(Queue(name, Exchange(name), routing_key=name) for name in ("mem.p0", "mem.p1", "mem.p3")),
    task_routes={
        "memory.run_job": {"queue": "mem.p1"},
        # Publishing P0 and recovering P1 must work with every import slot busy or offline.
        "memory.reconcile": {"queue": "mem.p0"},
    },
    beat_schedule={
        "memory-reconcile-60s": {
            "task": "memory.reconcile",
            "schedule": 60.0,
        },
    },
)

app = celery_app
