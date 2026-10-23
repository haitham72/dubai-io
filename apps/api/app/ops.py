"""Founder-ops surface: GET /api/ops/*. Read-only, server-measured, never fixtures.

Access: header X-Ops-Token must equal OPS_TOKEN. Unset token -> 404 (feature off),
wrong/missing header -> 403. The token is never logged or echoed.
Every dependency probe is bounded (<= PROBE_TIMEOUT_S) so the endpoint cannot hang.
An unreachable dependency is `degraded`/`unknown`, never `ok`.
"""
import hmac
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException

from .config import settings

PROBE_TIMEOUT_S = 1.0
STARTED = time.monotonic()
VERSION = "0.1.0"
_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ops-probe")
_RANK = {"ok": 0, "unknown": 1, "degraded": 2}


def require_ops_token(x_ops_token: str | None = Header(default=None)):
    if not settings.ops_token:
        raise HTTPException(404, "Not found")
    if not x_ops_token or not hmac.compare_digest(x_ops_token.encode(), settings.ops_token.encode()):
        raise HTTPException(403, "Ops token missing or invalid")


router = APIRouter(prefix="/api/ops", tags=["ops"], dependencies=[Depends(require_ops_token)])


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row(name, state, probed, detail=None):
    row = {"name": name, "state": state, "probed": probed, "as_of": now_iso(), "provenance": "official"}
    if detail:
        row["detail"] = detail
    return row


def _bounded(fn):
    """Run a probe with a hard time limit; returns (value, error_text)."""
    future = _pool.submit(fn)
    try:
        return future.result(timeout=PROBE_TIMEOUT_S), None
    except FutureTimeout:
        return None, "timed out"
    except Exception as exc:
        return None, type(exc).__name__


def _store():
    from .actions import engine
    return engine().store


# ---- probes (module-level so tests can monkeypatch them) ----

def probe_db():
    store = _store()
    with store.lock:
        store.db.execute("CREATE TABLE IF NOT EXISTS ops_probe (id TEXT PRIMARY KEY, at TEXT)")
        store.db.execute("DELETE FROM ops_probe WHERE id=?", ("health",))
        store.db.execute("INSERT INTO ops_probe VALUES (?,?)", ("health", now_iso()))
        store.db.commit()
    return str(getattr(store.db, "dialect", "sqlite"))


def probe_redis():
    import redis
    client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=PROBE_TIMEOUT_S,
                                  socket_timeout=PROBE_TIMEOUT_S)
    return bool(client.ping())


def probe_rabbitmq():
    import socket
    url = urlparse(settings.rabbitmq_url)
    with socket.create_connection((url.hostname or "localhost", url.port or 5672), timeout=PROBE_TIMEOUT_S):
        return True


def probe_worker():
    """Celery worker heartbeat: names that replied to a control ping, or None if silent."""
    from . import ml_tasks
    if ml_tasks.celery is None:
        raise RuntimeError("celery not installed")
    replies = ml_tasks.celery.control.inspect(timeout=PROBE_TIMEOUT_S).ping()
    return sorted(replies) if replies else None


def probe_migration():
    store = _store()
    if getattr(store.db, "dialect", "sqlite") == "sqlite":
        return None
    row = store.db.execute("SELECT max(version) FROM supabase_migrations.schema_migrations").fetchone()
    return row[0] if row and row[0] else None


def _dependency_rows():
    eager = settings.ml_eager
    rows = []
    dialect, err = _bounded(probe_db)
    probed = "INSERT + commit into ops_probe table (write probe)"
    rows.append(_row("database", "ok", probed, f"{dialect} write succeeded") if err is None
                else _row("database", "degraded", probed, f"write probe failed: {err}"))
    unreachable = "unknown" if eager else "degraded"
    note = " (CELERY_EAGER=1: not required in this mode)" if eager else ""
    ok, err = _bounded(probe_redis)
    probed = "Redis PING"
    rows.append(_row("redis", "ok", probed) if err is None and ok
                else _row("redis", unreachable, probed, f"unreachable: {err or 'no pong'}{note}"))
    ok, err = _bounded(probe_rabbitmq)
    probed = "TCP connect to RabbitMQ broker port"
    rows.append(_row("rabbitmq", "ok", probed) if err is None and ok
                else _row("rabbitmq", unreachable, probed, f"unreachable: {err or 'no connection'}{note}"))
    probed = "Celery control ping (worker heartbeat)"
    if eager:
        rows.append(_row("celery_worker", "unknown", probed, "CELERY_EAGER=1: jobs run inline, no worker to ping"))
    else:
        workers, err = _bounded(probe_worker)
        if err is None and workers:
            rows.append(_row("celery_worker", "ok", probed, f"{len(workers)} worker(s) replied"))
        else:
            rows.append(_row("celery_worker", "unknown", probed, f"no worker reply ({err or 'silent'})"))
    version, err = _bounded(probe_migration)
    probed = "max(version) in supabase_migrations.schema_migrations (Postgres only)"
    if err is None and version:
        rows.append(_row("migration", "ok", probed, f"last applied: {version}"))
    else:
        rows.append(_row("migration", "unknown", probed,
                         "not knowable on this database" if err is None else f"query failed: {err}"))
    return rows


@router.get("/health")
def health():
    try:
        rows = _dependency_rows()
    except Exception as exc:  # the aggregator itself failed: name the failure, never empty-200
        raise HTTPException(503, f"health aggregation failed ({type(exc).__name__})") from exc
    state = max((r["state"] for r in rows), key=_RANK.get)
    return {"state": state, "as_of": now_iso(), "provenance": "official",
            "api": {"version": VERSION, "uptime_s": round(time.monotonic() - STARTED, 1), "as_of": now_iso(),
                    "provenance": "official"},
            "dependencies": rows}


# ---- /ml ----

def _unavailable(reason):
    return {"state": "unavailable", "reason": reason, "value": None, "as_of": now_iso(), "provenance": "official"}


def _queue_depth():
    from kombu import Connection
    from . import ml_tasks
    name = ml_tasks.celery.conf.task_default_queue or "celery"
    with Connection(settings.rabbitmq_url, connect_timeout=PROBE_TIMEOUT_S) as conn:
        return {"queue": name, "messages": conn.default_channel.queue_declare(queue=name, passive=True).message_count}


def _active_jobs():
    from . import ml_tasks
    active = ml_tasks.celery.control.inspect(timeout=PROBE_TIMEOUT_S).active()
    if active is None:
        raise RuntimeError("no worker reply")
    return sum(len(v) for v in active.values())


def _failed_jobs(limit=20):
    """Job id + exception class only, read from Celery's Redis result keys. Never args, results or messages."""
    import redis
    client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=PROBE_TIMEOUT_S,
                                  socket_timeout=PROBE_TIMEOUT_S)
    failed, total = [], 0
    for key in client.scan_iter(match="celery-task-meta-*", count=200):
        raw = client.get(key)
        if not raw:
            continue
        meta = json.loads(raw)
        if meta.get("status") != "FAILURE":
            continue
        total += 1
        if len(failed) < limit:
            exc = meta.get("result")
            category = exc.get("exc_type") if isinstance(exc, dict) else None
            if not (isinstance(category, str) and re.fullmatch(r"\w{1,80}", category)):
                category = "UnknownError"
            job_id = meta.get("task_id") or key.decode().split("celery-task-meta-", 1)[-1]
            failed.append({"job_id": str(job_id)[:64], "category": category})
    return {"count": total, "jobs": failed}


def _sentiment_counts():
    store = _store()
    with store.lock:
        from . import ml_models
        ml_models.setup(store)
        rows = store.db.execute("SELECT sentiment, analyzed_at FROM comment_labels").fetchall()
    now = datetime.now(timezone.utc)
    windows = {"24h": timedelta(hours=24), "7d": timedelta(days=7)}
    out = {k: {"negative": 0, "neutral": 0, "positive": 0} for k in windows}
    total = 0
    for sentiment, at in rows:
        try:
            when = datetime.fromisoformat(at)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        total += 1
        for label, span in windows.items():
            if now - when <= span and sentiment in out[label]:
                out[label][sentiment] += 1
    return {"state": "ok" if total else "empty", "windows": out, "total_labelled": total,
            "hint": None if total else "No jobs yet — run a classification to populate",
            "as_of": now_iso(), "provenance": "official"}


def _broker_block(fn, label):
    if settings.ml_eager:
        return _unavailable("CELERY_EAGER=1: jobs run inline, there is no queue or worker to inspect")
    value, err = _bounded(fn)
    if err is not None:
        return _unavailable(f"{label} unreachable ({err})")
    return {"state": "ok", "value": value, "as_of": now_iso(), "provenance": "official"}


@router.get("/ml")
def ml():
    try:
        sentiment = _sentiment_counts()
    except Exception as exc:
        raise HTTPException(503, f"database unreadable ({type(exc).__name__})") from exc
    return {
        "as_of": now_iso(), "eager": settings.ml_eager,
        "queue": _broker_block(_queue_depth, "RabbitMQ"),
        "active_jobs": _broker_block(_active_jobs, "Celery worker"),
        "failed_jobs": _broker_block(_failed_jobs, "Redis result backend"),
        "sentiment": sentiment,
        "rag": {"state": "unavailable", "hybrid_ratio": None, "keyword_fallback_ratio": None,
                "reason": "search method is not persisted per query, so no honest ratio exists yet",
                "as_of": now_iso(), "provenance": "official"},
    }
