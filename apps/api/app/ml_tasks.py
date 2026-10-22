"""Background ML jobs: Celery on RabbitMQ/Redis, eager inline by default.

CELERY_EAGER=1 (default): analysis runs inside the request, no broker needed.
Production (docker): CELERY_EAGER=0, RabbitMQ broker, results in Redis.
dispatch_* never raises: worst case the comment stays unlabelled.
"""
import logging

from .config import settings

log = logging.getLogger(__name__)

try:
    from celery import Celery

    celery = Celery("dubaiio", broker=settings.rabbitmq_url, backend=settings.redis_url)
    celery.conf.update(task_always_eager=settings.ml_eager, task_acks_late=True,
                       worker_prefetch_multiplier=1)

    @celery.task(name="ml.analyze_comment")
    def analyze_comment_task(owner, comment_id, post_id, text, analyzed_at):
        store = _worker_store()
        from . import ml_models
        return ml_models.store_label(store, owner, comment_id, post_id, text, analyzed_at)
except ImportError:
    celery = None


def setup(store):
    from . import ml_models
    ml_models.setup(store)


def _worker_store():
    from .actions import ActionStore
    return ActionStore(settings.database_url or settings.data_dir / "actions.sqlite3")


def dispatch_comment(store, owner, comment_id, post_id, text, analyzed_at):
    """Queue (broker) or run inline (eager/dev). Returns a short status."""
    try:
        if celery is not None and not settings.ml_eager:
            try:
                celery.send_task("ml.analyze_comment",
                                 args=[owner, comment_id, post_id, text, analyzed_at])
                return "queued"
            except Exception as exc:
                log.warning("broker unreachable, running inline: %s", exc)
        from . import ml_models
        return ml_models.store_label(store, owner, comment_id, post_id, text, analyzed_at)["status"]
    except Exception as exc:
        log.warning("ml dispatch failed: %s", exc)
        return "failed"
