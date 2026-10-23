"""Founder ops endpoints: access control, health honesty, ML aggregate. No live broker."""
import json

import pytest
from fastapi.testclient import TestClient

from app import actions, ml_models, ops
from app.actions import ActionEngine, ActionStore
from app.config import settings

TOKEN = "t0ken-for-tests"
H = {"X-Ops-Token": TOKEN}


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.main import app
    store = ActionStore(tmp_path / "ops.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    monkeypatch.setattr(settings, "ops_token", TOKEN)
    monkeypatch.setattr(settings, "ml_eager", True)
    monkeypatch.setattr(settings, "widget_port", 0)
    yield TestClient(app)
    store.db.close()


def _probes_ok(monkeypatch, redis=True):
    monkeypatch.setattr(ops, "probe_redis", (lambda: True) if redis else (lambda: (_ for _ in ()).throw(ConnectionError("down"))))
    monkeypatch.setattr(ops, "probe_rabbitmq", lambda: True)
    monkeypatch.setattr(ops, "probe_worker", lambda: ["celery@w1"])


def rows(body):
    return {r["name"]: r for r in body["dependencies"]}


def test_access_control(client, monkeypatch):
    assert client.get("/api/ops/health").status_code == 403
    assert client.get("/api/ops/health", headers={"X-Ops-Token": "wrong"}).status_code == 403
    assert client.get("/api/ops/ml").status_code == 403
    monkeypatch.setattr(settings, "ops_token", "")
    assert client.get("/api/ops/health", headers=H).status_code == 404
    assert client.get("/api/ops/ml", headers=H).status_code == 404
    monkeypatch.setattr(settings, "ops_token", TOKEN)
    assert client.get("/api/ops/health", headers=H).status_code == 200


def test_health_happy_path(client, monkeypatch):
    monkeypatch.setattr(settings, "ml_eager", False)
    monkeypatch.setattr(ops, "probe_migration", lambda: "20261023000500")
    _probes_ok(monkeypatch)
    body = client.get("/api/ops/health", headers=H).json()
    assert body["state"] == "ok" and body["api"]["version"]
    r = rows(body)
    assert {k: v["state"] for k, v in r.items()} == {k: "ok" for k in ("database", "redis", "rabbitmq", "celery_worker", "migration")}
    assert all(v["probed"] and v["as_of"] for v in r.values())


def test_redis_down_is_not_ok(client, monkeypatch):
    monkeypatch.setattr(settings, "ml_eager", False)
    _probes_ok(monkeypatch, redis=False)
    body = client.get("/api/ops/health", headers=H).json()
    assert rows(body)["redis"]["state"] == "degraded"
    assert body["state"] == "degraded"


def test_worker_silent_is_unknown(client, monkeypatch):
    monkeypatch.setattr(settings, "ml_eager", False)
    _probes_ok(monkeypatch)
    monkeypatch.setattr(ops, "probe_worker", lambda: None)
    body = client.get("/api/ops/health", headers=H).json()
    assert rows(body)["celery_worker"]["state"] == "unknown"
    assert body["state"] != "ok"


def test_eager_mode_never_reports_worker_ok(client):
    body = client.get("/api/ops/health", headers=H).json()
    assert rows(body)["celery_worker"]["state"] == "unknown" and body["state"] != "ok"


def test_probe_timeout_does_not_hang(client, monkeypatch):
    import time
    monkeypatch.setattr(ops, "PROBE_TIMEOUT_S", 0.2)
    monkeypatch.setattr(ops, "probe_redis", lambda: time.sleep(2))
    monkeypatch.setattr(ops, "probe_rabbitmq", lambda: True)
    start = time.monotonic()
    body = client.get("/api/ops/health", headers=H).json()
    assert time.monotonic() - start < 1.5
    assert rows(body)["redis"]["state"] != "ok"


def test_ml_empty_db_has_no_invented_numbers(client):
    body = client.get("/api/ops/ml", headers=H).json()
    assert body["sentiment"]["state"] == "empty" and body["sentiment"]["total_labelled"] == 0
    assert "run a classification" in body["sentiment"]["hint"]
    for k in ("queue", "active_jobs", "failed_jobs"):
        assert body[k]["state"] == "unavailable" and body[k]["value"] is None
    assert body["rag"]["state"] == "unavailable" and body["rag"]["hybrid_ratio"] is None


def test_ml_sentiment_counts_from_stored_labels(client):
    from datetime import datetime, timedelta, timezone
    store = actions.engine().store
    ml_models.setup(store)
    now = datetime.now(timezone.utc)
    for i, (label, age) in enumerate([("negative", 1), ("positive", 30), ("positive", 24 * 10)]):
        store.db.execute("INSERT INTO comment_labels VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (f"c{i}", "p", label, .1, .1, .1, "[]", 0, "sentiment_negative", "m",
                          (now - timedelta(hours=age)).isoformat()))
    store.db.commit()
    s = client.get("/api/ops/ml", headers=H).json()["sentiment"]
    assert s["windows"]["24h"] == {"negative": 1, "neutral": 0, "positive": 0}
    assert s["windows"]["7d"] == {"negative": 1, "neutral": 0, "positive": 1}
    assert s["total_labelled"] == 3


def test_failed_job_exposes_only_id_and_category(client, monkeypatch):
    monkeypatch.setattr(settings, "ml_eager", False)
    secret = "user said something private"
    meta = {"status": "FAILURE", "task_id": "job-123", "args": [secret],
            "result": {"exc_type": "ValueError", "exc_message": [secret], "exc_module": "builtins"}}

    class FakeRedis:
        def scan_iter(self, **_):
            return iter([b"celery-task-meta-job-123", b"celery-task-meta-ok"])

        def get(self, key):
            return json.dumps(meta if key.endswith(b"123") else {"status": "SUCCESS"})

    import redis
    monkeypatch.setattr(redis.Redis, "from_url", staticmethod(lambda *a, **k: FakeRedis()))
    monkeypatch.setattr(ops, "_queue_depth", lambda: {"queue": "celery", "messages": 2})
    monkeypatch.setattr(ops, "_active_jobs", lambda: 1)
    raw = client.get("/api/ops/ml", headers=H)
    body = raw.json()
    assert body["failed_jobs"]["value"] == {"count": 1, "jobs": [{"job_id": "job-123", "category": "ValueError"}]}
    assert body["queue"]["value"]["messages"] == 2 and body["active_jobs"]["value"] == 1
    assert secret not in raw.text


def test_broker_down_marks_unavailable(client, monkeypatch):
    monkeypatch.setattr(settings, "ml_eager", False)

    def boom():
        raise ConnectionError("no broker")

    for name in ("_queue_depth", "_active_jobs", "_failed_jobs"):
        monkeypatch.setattr(ops, name, boom)
    body = client.get("/api/ops/ml", headers=H).json()
    assert all(body[k]["state"] == "unavailable" and body[k]["value"] is None for k in ("queue", "active_jobs", "failed_jobs"))


def test_dash_served_and_pwa_root_intact(client):
    r = client.get("/dash/")
    assert r.status_code == 200 and "Founder tool" in r.text
    assert client.get("/dash/dash.js").status_code == 200
    root = client.get("/", follow_redirects=False)
    assert root.status_code in (302, 307) and root.headers["location"] == "/index.html"
    pwa = client.get("/index.html")
    assert pwa.status_code == 200 and "Founder tool" not in pwa.text
