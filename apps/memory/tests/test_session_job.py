"""Session ingest, transactional persistence and catch-up on compose Postgres."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from temporal_memory.api import bridge, graph, vault
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema
from temporal_memory.models import Attempt, ExtractionOutput, OutFact, Owner
from temporal_memory.queue import session, worker
from temporal_memory.queue.outbox import reconcile


OWNER = "u2-owner"
BASE = f"/v1/owners/{OWNER}"
NOW = datetime(2026, 11, 24, 10, tzinfo=timezone.utc)


@pytest.fixture
def api(monkeypatch):
    db, schema = create_test_schema()
    try:
        store = PostgresGraphStore(db)
        store.create_owner(Owner(OWNER, "Synthetic", display_name="Synthetic user"))
        with db.transaction() as conn:
            conn.execute(
                """INSERT INTO subjects (owner,id,path,label) VALUES
                   (%s,'agents','learning/ai-agents','AI agents'),
                   (%s,'family','people-family/cousins','Cousins')""",
                (OWNER, OWNER),
            )
        vault.configure(store=store, auth_verifier=lambda _: vault.AuthContext(role="owner-device", owner=OWNER))
        app = FastAPI()
        app.include_router(bridge.router)
        app.include_router(vault.router)
        app.include_router(graph.router)
        with TestClient(app) as client:
            yield db, client
    finally:
        drop_test_schema(db, schema)


def record(rid, text, key=None, author=OWNER):
    meta = {} if key is None else {"session_id": key}
    return {"id": rid, "source": "live", "at": NOW.isoformat(), "author": author, "text": text, "meta": meta}


def post(client, records=(), **payload):
    res = client.post(f"{BASE}/records", json={"records": list(records), **payload})
    assert res.status_code == 200, res.text
    return res.json()


def query(db, sql, params=()):
    with db.connection() as conn:
        return conn.execute(sql, params).fetchall()


def test_hot_path_stores_triples_edits_are_rejected_and_quarantine_is_text_free(api):
    db, client = api
    records = [
        record("p", "I bought an iPhone yesterday", "s"),
        record("v", "I had dinner at Zuma in DIFC", "s"),
        record("t", "I bought a laptop", "s", author="Sara"),
        record("q", "My father's health", "s"),
        record("c", "My wifi password is FakeSecret!", "s"),
    ]
    result = post(client, records)
    assert result["job_id"] is None
    assert result["quarantined"] == 2
    assert len(result["fact_ids"]) == 2
    assert post(client, records)["quarantined"] == 0
    assert query(db, "SELECT id FROM records WHERE id IN ('q','c')") == []
    rows = query(db, "SELECT predicate,object_text,event_at,provenance,span_record_id,span_start,span_end "
                     "FROM facts ORDER BY span_record_id")
    assert [row["object_text"] for row in rows] == ["iPhone", "Zuma"]
    assert rows[0]["event_at"] == "2026-11-23"
    assert rows[0]["provenance"] == "user_supplied"
    assert records[0]["text"][rows[0]["span_start"]:rows[0]["span_end"]] == "I bought an iPhone"
    places = query(db, "SELECT name,place_type FROM entities WHERE kind='place'")
    assert places == [{"name": "Zuma", "place_type": "restaurant"}]
    changed = client.post(f"{BASE}/records", json={"records": [record("p", "I bought a PS5", "s")]})
    assert changed.status_code == 409
    assert query(db, "SELECT text FROM records WHERE id='p'") == [{"text": records[0]["text"]}]
    job = post(client, session_id="s", close_session=True)["job_id"]
    assert query(db, "SELECT input_ref FROM jobs WHERE id=%s", (job,)) == [{"input_ref": ["p", "v"]}]


def test_topic_evidence_uses_two_distinct_sessions_and_excludes_family(api):
    db, client = api
    for rid, key, text in [
        ("r1", "s1", "How do AI agents work?"), ("r2", "s1", "Tell me about AI agents"),
        ("r3", "s2", "Where are the cousins?"), ("r4", "s2", "I have another AI agents question"),
        ("r5", "s3", "Explain AI agents"), ("r6", "s3", "More AI agents"),
    ]:
        reply = post(client, [record(rid, text, key)])
        assert bool(reply["fact_ids"]) == (rid == "r4")
    assert query(db, "SELECT subject_id,count(*) AS n FROM topic_mentions GROUP BY subject_id") == [
        {"subject_id": "agents", "n": 3}
    ]
    assert query(db, "SELECT status,provenance FROM facts") == [{"status": "hypothesis", "provenance": "inferred"}]
    assert query(db, "SELECT record_id FROM fact_evidence ORDER BY record_id") == [{"record_id": "r1"}, {"record_id": "r4"}]


def test_idle_and_explicit_close_share_exactly_one_durable_job(api, monkeypatch):
    db, client = api
    monkeypatch.setenv("TM_SESSION_IDLE_MINUTES", "30")
    monkeypatch.setattr(session, "_now", lambda: NOW)
    assert post(client, [record("r1", "First turn")])["job_id"] is None
    monkeypatch.setattr(session, "_now", lambda: NOW + timedelta(minutes=10))
    assert post(client, [record("r2", "Second turn")])["job_id"] is None
    assert session.flush_idle_sessions(db, now=NOW + timedelta(minutes=39)) == 0
    assert session.flush_idle_sessions(db, now=NOW + timedelta(minutes=40)) == 1
    assert session.flush_idle_sessions(db, now=NOW + timedelta(hours=1)) == 0
    assert post(client, [record("r3", "Next turn", "explicit")])["job_id"] is None
    job = post(client, close_session=True, session_id="explicit")["job_id"]
    assert post(client, close_session=True, session_id="explicit")["job_id"] == job
    assert post(client, [record("r3", "Next turn", "explicit")])["job_id"] is None
    late = client.post(f"{BASE}/records", json={"records": [record("r4", "Late turn", "explicit")]})
    assert late.status_code == 409
    assert query(db, "SELECT id FROM records WHERE id='r4'") == []
    jobs = query(db, "SELECT kind,pool,input_ref FROM jobs ORDER BY input_ref")
    assert jobs == [
        {"kind": "extract.session", "pool": "owner-device", "input_ref": ["r1", "r2"]},
        {"kind": "extract.session", "pool": "owner-device", "input_ref": ["r3"]},
    ]


def _attempt(bundle, model, fact=None):
    output = ExtractionOutput([], [fact] if fact else [], [])
    return Attempt(bundle.job.id, bundle.job.attempt_no, bundle.job.fence_token or "",
                   bundle.job.worker_id or "", "internal-local", model, bundle.job.prompt_version,
                   output, model_observed=model)


def test_qwen_unavailability_uses_same_job_after_fallback(api, monkeypatch):
    db, client = api
    monkeypatch.setenv("TM_P1_FALLBACK_SECONDS", "30")
    job = post(client, [record("r", "Let's discuss camera lenses", "s")], close_session=True)["job_id"]
    users = []

    def model(bundle, runner, name):
        users.append((runner, name))
        if runner == "lmstudio":
            raise httpx.ConnectError("Synthetic unavailable local model")
        return _attempt(bundle, name)

    monkeypatch.setattr(worker.extract, "run", model)
    assert worker.run_job(job, db=db)["status"] == "deferred"
    assert worker.run_job(job, db=db)["status"] == "deferred"
    assert [runner for runner, _ in users] == ["lmstudio"]
    fallback_at = query(db, "SELECT fallback_at FROM jobs WHERE id=%s", (job,))[0]["fallback_at"]
    assert reconcile(db, send_fn=lambda *_: None, now=fallback_at - timedelta(seconds=1))["fallback_to_internal"] == 0
    assert reconcile(db, send_fn=lambda *_: None, now=fallback_at)["fallback_to_internal"] == 1
    assert worker.run_job(job, db=db)["status"] == "applied"
    assert [runner for runner, _ in users] == ["lmstudio", "anthropic"]
    attempt = query(db, "SELECT worker_kind,model,model_observed FROM job_attempts WHERE job_id=%s", (job,))[0]
    assert attempt == {"worker_kind": "internal-cloud", "model": users[-1][1], "model_observed": users[-1][1]}


def test_session_worker_dedupes_a_new_assertion_with_same_evidence(api, monkeypatch):
    db, client = api
    hot = post(client, [record("r", "I bought an iPhone yesterday", "s")], close_session=True)
    job = hot["job_id"]
    fact = OutFact("Karim purchased an iPhone yesterday", None, "events", [], "new", None,
                   "2026-11-24", ["r"], None)
    model = Mock(side_effect=lambda bundle, runner, name: _attempt(bundle, name, fact))
    monkeypatch.setattr(worker.extract, "run", model)
    assert worker.run_job(job, db=db)["status"] == "applied"
    assert query(db, "SELECT id FROM facts") == [{"id": hot["fact_ids"][0]}]
    assert model.call_args.args[1] == "lmstudio"


def test_forget_excludes_an_open_session_turn(api):
    db, client = api
    post(client, [record("r1", "Hello first", "s"), record("r2", "Hello second", "s")])
    res = client.post(f"{BASE}/forget", json={"record_ids": ["r1"]})
    assert res.status_code == 200
    job = post(client, close_session=True, session_id="s")["job_id"]
    assert query(db, "SELECT input_ref FROM jobs WHERE id=%s", (job,)) == [{"input_ref": ["r2"]}]


def test_http_hot_path_p95_under_50_ms(api):
    from time import perf_counter_ns

    db, client = api
    latencies = []
    for i in range(110):
        start = perf_counter_ns()
        result = post(client, [record(f"turn-{i}", f"I bought iPhone {i}", "bench")])
        latencies.append((perf_counter_ns() - start) / 1_000_000)
        assert result["fact_ids"] and result["job_id"] is None
    p95 = sorted(latencies)[104]
    print(f"110 authenticated Postgres HTTP turns: p95 {p95:.3f} ms")
    assert p95 < 50


def test_empty_implicit_close_works_even_after_idle(api, monkeypatch):
    db, client = api
    monkeypatch.setenv("TM_SESSION_IDLE_MINUTES", "30")
    monkeypatch.setattr(session, "_now", lambda: NOW)
    post(client, [record("r1", "A short question")])
    monkeypatch.setattr(session, "_now", lambda: NOW + timedelta(minutes=31))
    first = post(client, close_session=True)["job_id"]
    assert first and post(client, close_session=True)["job_id"] == first
    assert query(db, "SELECT input_ref FROM jobs WHERE id=%s", (first,)) == [{"input_ref": ["r1"]}]


def test_forgotten_first_visit_cannot_qualify_a_topic(api):
    _, client = api
    post(client, [record("r1", "How do AI agents work?", "s1")])
    assert client.post(f"{BASE}/forget", json={"record_ids": ["r1"]}).status_code == 200
    assert not post(client, [record("r2", "What are AI agents?", "s2")])["fact_ids"]
    assert post(client, [record("r3", "Explain AI agents", "s3")])["fact_ids"]



@pytest.mark.parametrize("replacement,erase", [(False, True), (True, False)])
def test_topic_forget_rechecks_distinct_cited_sessions(api, replacement, erase, monkeypatch):
    monkeypatch.setenv('TM_SEMANTIC', '0')
    db, client = api
    post(client, [record("visit1", "How do AI agents work?", "first")])
    if replacement:
        post(client, [record("backup", "More about AI agents", "first")])
    fact_id, = post(client, [record("visit2", "Explain AI agents", "second")])["fact_ids"]
    post(client, [record("unrelated", "An unrelated remark", "third")])

    def surfaces():
        return {
            "hypotheses": client.get(f"{BASE}/hypotheses"),
            "graph": client.get(f"{BASE}/vault/graph?view=subjects"),
            "context": client.post(f"{BASE}/context", json={"text": "Tell me about AI agents"}),
        }

    def forget(rid):
        req = client.post(f"{BASE}/forget", json={"record_ids": [rid]})
        assert req.status_code == 200, req.text
        return req.json()

    assert fact_id in surfaces()["hypotheses"].text
    assert forget("unrelated")["facts_erased"] == 0
    assert fact_id in surfaces()["hypotheses"].text
    revision = query(db, "SELECT privacy_revision FROM owners")[0]["privacy_revision"]
    result = forget("visit1")
    assert result["facts_erased"] == int(erase)
    assert query(db, "SELECT privacy_revision FROM owners")[0]["privacy_revision"] == revision + 1
    current = surfaces()
    assert all(response.status_code == 200 for response in current.values())
    assert (fact_id in current["hypotheses"].text) is not erase
    assert query(db, "SELECT session_id FROM topic_mentions ORDER BY session_id") == [
        {"session_id": key} for key in (["client:second"] if erase else ["client:first", "client:second"])
    ]
    if erase:
        assert all(fact_id not in response.text for response in current.values())
    else:
        assert query(db, "SELECT record_id FROM fact_evidence ORDER BY record_id") == [
            {"record_id": "backup"}, {"record_id": "visit2"},
        ]
