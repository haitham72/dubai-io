"""Tests for core.extract, queue.jobs, queue.outbox, queue.celery_app, and queue.worker."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from typing import Any

import pytest

from temporal_memory.core import extract
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema
from temporal_memory.models import (
    Attempt,
    ExtractionOutput,
    FactEntity,
    Job,
    JobBundle,
    OutEntity,
    OutFact,
    OutLink,
    Owner,
    Record,
    Worker,
)
from temporal_memory.queue.celery_app import celery_app
from temporal_memory.queue.jobs import PostgresJobs
from temporal_memory.queue.outbox import publish_pending, queue_for_priority, reconcile
from temporal_memory.queue.worker import run_job


@pytest.fixture()
def pg_db():
    db, schema = create_test_schema()
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


def _seed_owner_and_records(
    db,
    owner_id: str = "karim",
    days: list[str] | None = None,
) -> tuple[PostgresGraphStore, Owner, dict[str, list[str]]]:
    store = PostgresGraphStore(db)
    owner = store.create_owner(
        Owner(
            id=owner_id,
            label=f"{owner_id}-label",
            kind="simulated",
            display_name="Karim Haddad",
            self_aliases=["Kimo", "كريم"],
            timezone="Asia/Dubai",
        )
    )
    days = days or ["2025-05-01"]
    recs: list[Record] = []
    by_day: dict[str, list[str]] = {}
    for idx, day in enumerate(days, start=1):
        rid = f"{owner_id}-r{idx}"
        recs.append(
            Record(
                id=rid,
                owner=owner_id,
                source="whatsapp:friends",
                at=f"{day}T10:00:00Z",
                author="Omar",
                text=f"Omar and Karim met at QamarTech cafe on {day}.",
                generation=0,
            )
        )
        by_day[day] = [rid]
    store.upsert_records(owner_id, recs)
    return store, owner, by_day


def _make_worker(worker_id: str = "w-int-1", *, owner: str | None = None) -> Worker:
    return Worker(
        id=worker_id,
        kind="owner-hook" if owner else "internal-local",
        model="qwen/qwen3-4b-2507",
        runner="lmstudio",
        owner=owner,
        released=True,
    )


def _sample_bundle(record_id: str = "r1") -> JobBundle:
    owner = Owner(
        id="karim",
        label="Karim",
        kind="simulated",
        display_name="Karim Haddad",
        self_aliases=["Kimo", "كريم"],
    )
    rec = Record(
        id=record_id,
        owner="karim",
        source="whatsapp:omar",
        at="2025-05-01T10:00:00Z",
        author="Omar",
        text="Omar started working at QamarTech in Dubai. عمر بدأ شغل في قمر تك",
    )
    job = Job(
        id="job_test_1",
        owner="karim",
        kind="extract.day",
        priority=1,
        pool="internal",
        input_ref=[record_id],
        input_version=0,
        context_hash="",
        prompt_version=extract.PROMPT_VERSION,
        day="2025-05-01",
        state="leased",
        attempt_no=1,
        fence_token="fence-123",
        worker_id="w-1",
    )
    return JobBundle(
        job=job,
        records=[rec],
        context={"entities": [{"id": "e1", "name": "Karim Haddad", "kind": "person", "aliases": ["Kimo"], "relation_to_user": "self"}], "facts": [], "subjects": []},
        system_prompt=extract.build_system_prompt(owner),
        output_schema=extract.OUTPUT_SCHEMA,
    )


# ---------------------------------------------------------------------------
# Queue: enqueue idempotency + outbox
# ---------------------------------------------------------------------------
def test_enqueue_idempotency_and_outbox(pg_db) -> None:
    store, _, by_day = _seed_owner_and_records(pg_db, days=["2025-05-01", "2025-05-02"])
    jobs = PostgresJobs(pg_db, store=store)
    rids = [by_day["2025-05-01"][0], by_day["2025-05-02"][0]]

    j1 = jobs.enqueue("karim", "extract.day", rids, priority=0, day="2025-05-01")
    j2 = jobs.enqueue("karim", "extract.day", list(reversed(rids)), priority=0, day="2025-05-01")

    assert j1.id == j2.id
    assert j1.priority == 0
    assert j1.state == "queued"

    with pg_db.connection() as conn:
        job_count = conn.execute("SELECT COUNT(*)::int AS c FROM jobs").fetchone()["c"]
        outbox_rows = conn.execute("SELECT job_id, priority, published_at FROM outbox").fetchall()
    assert job_count == 1
    assert len(outbox_rows) == 1
    assert outbox_rows[0]["job_id"] == j1.id
    assert outbox_rows[0]["published_at"] is None

    sent: list[tuple[str, int]] = []
    assert publish_pending(pg_db, send_fn=lambda jid, prio: sent.append((jid, prio))) == 1
    assert sent == [(j1.id, 0)]
    assert publish_pending(pg_db, send_fn=lambda jid, prio: sent.append((jid, prio))) == 0

    assert queue_for_priority(0) == "mem.p0"
    assert queue_for_priority(1) == "mem.p1"
    assert queue_for_priority(3) == "mem.p3"


# ---------------------------------------------------------------------------
# Queue: week claim (day_from..day_to limit=7) + sensitive pool isolation
# ---------------------------------------------------------------------------
def test_claim_week_slice_and_sensitive_isolation(pg_db) -> None:
    days = [f"2025-05-{d:02d}" for d in range(1, 11)]
    store, _, karim_days = _seed_owner_and_records(pg_db, "karim", days=days)
    _, _, other_days = _seed_owner_and_records(pg_db, "other", days=days[:3])
    jobs = PostgresJobs(pg_db, store=store)

    for day in days:
        jobs.enqueue("karim", "extract.day", karim_days[day], priority=1, day=day)
    for day in days[:3]:
        jobs.enqueue("other", "extract.day", other_days[day], priority=0, day=day)

    worker = _make_worker("w-week")
    bundles = jobs.claim(
        worker,
        ["internal"],
        owner="karim",
        day_from="2025-05-02",
        day_to="2025-05-08",
        limit=7,
    )

    assert len(bundles) == 7
    claimed_days = sorted(b.job.day for b in bundles if b.job.day)
    assert claimed_days == [f"2025-05-{d:02d}" for d in range(2, 9)]
    assert all(b.job.owner == "karim" for b in bundles)
    assert all(b.job.state == "leased" for b in bundles)
    assert all(b.job.attempt_no == 1 for b in bundles)
    assert len({b.job.fence_token for b in bundles}) == 7
    assert all(len(b.records) == 1 and "Karim" in b.system_prompt for b in bundles)

    # Sensitive jobs on owner-device pool must never be handed to owner-device workers
    store.upsert_records(
        "karim",
        [Record(id="karim-sens", owner="karim", source="notes", at="2025-05-11T09:00:00Z", author="Karim", text="Sensitive item")],
    )
    jobs.enqueue("karim", "extract.live", ["karim-sens"], priority=0, pool="owner-device", sensitive_flag=True)
    device_worker = _make_worker("w-device", owner="karim")
    assert jobs.claim(device_worker, ["owner-device"]) == []


# ---------------------------------------------------------------------------
# Queue: claim_by_id duplicate delivery + worker zero extra LLM calls
# ---------------------------------------------------------------------------
def test_claim_by_id_prevents_duplicate_delivery(pg_db, monkeypatch: pytest.MonkeyPatch) -> None:
    store, _, by_day = _seed_owner_and_records(pg_db, days=["2025-05-01"])
    jobs = PostgresJobs(pg_db, store=store)
    job = jobs.enqueue("karim", "extract.day", by_day["2025-05-01"], priority=1, day="2025-05-01")

    w1 = _make_worker("w-1")
    w2 = _make_worker("w-2")
    b1 = jobs.claim_by_id(job.id, w1)
    b2 = jobs.claim_by_id(job.id, w2)
    assert b1 is not None
    assert b2 is None

    # End-to-end worker.run_job duplicate delivery test: 0 LLM calls on second delivery
    job2 = jobs.enqueue("karim", "extract.day", by_day["2025-05-01"], priority=0, day="2025-05-02")
    # Force distinct idempotency by using a second record
    store.upsert_records(
        "karim",
        [Record(id="karim-r2", owner="karim", source="whatsapp:friends", at="2025-05-02T10:00:00Z", author="Omar", text="Omar joined QamarTech")],
    )
    job2 = jobs.enqueue("karim", "extract.day", ["karim-r2"], priority=0, day="2025-05-02")

    llm_calls = 0

    def fake_extract_run(bundle: JobBundle, runner: str, model: str) -> Attempt:
        nonlocal llm_calls
        llm_calls += 1
        return Attempt(
            job_id=bundle.job.id,
            attempt_no=bundle.job.attempt_no,
            fence_token=bundle.job.fence_token or "",
            worker_id=bundle.job.worker_id or "w",
            worker_kind="internal-local",
            model=model,
            prompt_version=bundle.job.prompt_version,
            output=ExtractionOutput(
                entities=[OutEntity(ref="new:Omar", kind="person", aliases=["Omar"], relation_to_user="friend")],
                facts=[
                    OutFact(
                        text="Omar joined QamarTech.",
                        text_orig=None,
                        subject_path="work/career",
                        entities=[FactEntity(entity_id="new:Omar", role="colleague")],
                        op="new",
                        target=None,
                        valid_from="2025-05-02",
                        evidence=["karim-r2"],
                        sensitive=None,
                    )
                ],
                links=[],
            ),
            tokens_in=50,
            tokens_out=25,
            cost_usd=0.0,
        )

    monkeypatch.setattr(extract, "run", fake_extract_run)

    res1 = run_job(job2.id, runner="lmstudio", model="qwen-test", db=pg_db, jobs=jobs)
    res2 = run_job(job2.id, runner="lmstudio", model="qwen-test", db=pg_db, jobs=jobs)

    assert res1["status"] == "applied"
    assert res2 == {"status": "skipped", "job_id": job2.id}
    assert llm_calls == 1


# ---------------------------------------------------------------------------
# Queue: lease expiry -> requeue -> dead after 3 attempts
# ---------------------------------------------------------------------------
def test_expired_lease_requeue_and_dead_after_three_attempts(pg_db) -> None:
    store, _, by_day = _seed_owner_and_records(pg_db, days=["2025-05-01"])
    jobs = PostgresJobs(pg_db, store=store)
    job = jobs.enqueue("karim", "extract.day", by_day["2025-05-01"], priority=1, day="2025-05-01")
    worker = _make_worker("w-flaky")

    for attempt in (1, 2):
        claimed = jobs.claim_by_id(job.id, worker)
        assert claimed is not None
        assert claimed.job.attempt_no == attempt
        with pg_db.transaction() as conn:
            conn.execute(
                "UPDATE jobs SET lease_expires_at = now() - interval '10 minutes' WHERE id = %s",
                (job.id,),
            )
        stats = reconcile(pg_db, send_fn=lambda _j, _p: None)
        assert stats["requeued"] == 1
        assert stats["dead"] == 0

        with pg_db.connection() as conn:
            row = conn.execute("SELECT state, fence_token, worker_id FROM jobs WHERE id = %s", (job.id,)).fetchone()
        assert row["state"] == "queued"
        assert row["fence_token"] is None
        assert row["worker_id"] is None

    # 3rd attempt expires -> dead
    claimed_3 = jobs.claim_by_id(job.id, worker)
    assert claimed_3 is not None
    assert claimed_3.job.attempt_no == 3
    with pg_db.transaction() as conn:
        conn.execute(
            "UPDATE jobs SET lease_expires_at = now() - interval '10 minutes' WHERE id = %s",
            (job.id,),
        )
    stats3 = reconcile(pg_db, send_fn=lambda _j, _p: None)
    assert stats3["requeued"] == 0
    assert stats3["dead"] == 1

    with pg_db.connection() as conn:
        row = conn.execute("SELECT state FROM jobs WHERE id = %s", (job.id,)).fetchone()
    assert row["state"] == "dead"


# ---------------------------------------------------------------------------
# Queue: owner-device fallback + heartbeat fence check + submit
# ---------------------------------------------------------------------------
def test_owner_device_fallback_and_heartbeat_and_submit(pg_db) -> None:
    store, _, by_day = _seed_owner_and_records(pg_db, days=["2025-05-01"])
    jobs = PostgresJobs(pg_db, store=store)
    job = jobs.enqueue("karim", "extract.live", by_day["2025-05-01"], priority=0, pool="owner-device", day="2025-05-01")

    now = datetime.now(timezone.utc)
    early = reconcile(pg_db, send_fn=lambda _j, _p: None, now=now + timedelta(seconds=5))
    assert early["fallback_to_internal"] == 0

    late = reconcile(pg_db, send_fn=lambda _j, _p: None, now=now + timedelta(seconds=120))
    assert late["fallback_to_internal"] == 1

    internal_worker = _make_worker("w-int")
    bundles = jobs.claim(internal_worker, ["internal"], limit=1)
    assert len(bundles) == 1
    b = bundles[0]
    assert b.job.id == job.id
    assert b.job.fence_token

    assert jobs.heartbeat(job.id, "stale-fence") is False
    assert jobs.heartbeat(job.id, b.job.fence_token) is True

    # Stale fence submission must be rejected without clobbering active lease
    stale_attempt = Attempt(
        job_id=job.id,
        attempt_no=1,
        fence_token="stale-fence",
        worker_id=internal_worker.id,
        worker_kind=internal_worker.kind,
        model=internal_worker.model,
        prompt_version=b.job.prompt_version,
        output=ExtractionOutput(entities=[], facts=[], links=[]),
    )
    stale_verdict = jobs.submit(stale_attempt)
    assert stale_verdict.ok is False
    assert "fence_stale" in stale_verdict.reasons

    # Job must still be leased under valid fence_token
    assert jobs.heartbeat(job.id, b.job.fence_token) is True

    # Valid submission succeeds and persists fact + job_attempt
    valid_attempt = Attempt(
        job_id=job.id,
        attempt_no=1,
        fence_token=b.job.fence_token,
        worker_id=internal_worker.id,
        worker_kind=internal_worker.kind,
        model=internal_worker.model,
        prompt_version=b.job.prompt_version,
        output=ExtractionOutput(
            entities=[OutEntity(ref="new:Omar", kind="person", aliases=["Omar"], relation_to_user="friend")],
            facts=[
                OutFact(
                    text="Omar and Karim met at QamarTech cafe.",
                    text_orig=None,
                    subject_path="interests/social",
                    entities=[FactEntity(entity_id="new:Omar", role="friend")],
                    op="new",
                    target=None,
                    valid_from="2025-05-01",
                    evidence=[by_day["2025-05-01"][0]],
                    sensitive=None,
                )
            ],
            links=[],
        ),
        tokens_in=120,
        tokens_out=45,
        cost_usd=0.0,
    )
    verdict = jobs.submit(valid_attempt)
    assert verdict.ok is True
    assert len(verdict.applied_fact_ids) == 1
    assert jobs.heartbeat(job.id, b.job.fence_token) is False

    with pg_db.connection() as conn:
        attempts = conn.execute(
            "SELECT verdict, tokens_in, tokens_out FROM job_attempts WHERE job_id = %s ORDER BY finished_at ASC",
            (job.id,),
        ).fetchall()
    assert len(attempts) == 2
    assert attempts[0]["verdict"].startswith("rejected:")
    assert attempts[1]["verdict"] == "applied"
    assert attempts[1]["tokens_in"] == 120


# ---------------------------------------------------------------------------
# Extract: mocked unit tests for lmstudio / anthropic / agent-cli
# ---------------------------------------------------------------------------
def test_build_system_prompt_contains_owner_and_boundary() -> None:
    owner = Owner(id="k", label="Karim", display_name="Karim Haddad", self_aliases=["Kimo", "كريم"])
    prompt = extract.build_system_prompt(owner)
    assert "Karim Haddad" in prompt
    assert "Kimo" in prompt
    assert "<untrusted_records>" in prompt
    assert "text_orig" in prompt
    assert "role" in prompt


def test_extract_run_lmstudio_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = _sample_bundle()
    captured: dict[str, Any] = {}
    payload_json = {
        "entities": [{"ref": "new:Omar", "kind": "person", "aliases": ["Omar", "عمر"], "relation_to_user": "friend"}],
        "facts": [
            {
                "text": "Omar started working at QamarTech in Dubai.",
                "text_orig": "عمر بدأ شغل في قمر تك",
                "subject_path": "work/network",
                "entities": [{"entity_id": "new:Omar", "role": "colleague"}],
                "op": "new",
                "target": None,
                "valid_from": "2025-05-01",
                "evidence": ["r1"],
                "sensitive": None,
            }
        ],
        "links": [{"src": "new:Omar", "rel": "WORKS_AT", "dst": "new:QamarTech", "valid_from": "2025-05-01", "evidence": ["r1"]}],
    }

    def fake_post(url: str, *, json: dict[str, Any], timeout: float) -> Any:
        captured["url"] = url
        captured["json"] = json
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": "",
                            "reasoning_content": f"<think>hidden</think>{json_dumps(payload_json)}",
                        },
                    }
                ],
                "usage": {"prompt_tokens": 310, "completion_tokens": 95},
            },
        )

    json_dumps = json.dumps
    monkeypatch.setattr(extract.httpx, "post", fake_post)

    attempt = extract.run(bundle, "lmstudio", "qwen/qwen3-4b-2507")
    assert captured["json"]["temperature"] == 0
    assert captured["json"]["response_format"]["json_schema"]["strict"] is True
    assert captured["json"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert attempt.worker_kind == "internal-local"
    assert attempt.tokens_in == 310
    assert attempt.tokens_out == 95
    assert attempt.cost_usd == 0.0
    assert attempt.output is not None
    assert attempt.output.facts[0].text_orig == "عمر بدأ شغل في قمر تك"
    assert attempt.output.facts[0].entities[0] == FactEntity(entity_id="new:Omar", role="colleague")
    assert attempt.output.links[0].rel == "WORKS_AT"


def test_extract_run_anthropic_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = _sample_bundle()
    response_json = json.dumps(
        {
            "entities": [{"ref": "new:Omar", "kind": "person", "aliases": ["Omar"], "relation_to_user": "friend"}],
            "facts": [
                {
                    "text": "Omar works at QamarTech.",
                    "text_orig": None,
                    "subject_path": "work/network",
                    "entities": [{"entity_id": "new:Omar", "role": "engineer"}],
                    "op": "new",
                    "target": None,
                    "valid_from": "2025-05-01",
                    "evidence": ["r1"],
                    "sensitive": None,
                }
            ],
            "links": [],
        }
    )

    class FakeMessages:
        def create(self, **kwargs: Any) -> Any:
            assert kwargs["model"] == "claude-haiku-test"
            assert "<untrusted_records>" in kwargs["messages"][0]["content"]
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=response_json)],
                usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
            )

    class FakeAnthropic:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key
            self.messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-dummy")
    monkeypatch.setattr(extract, "anthropic", SimpleNamespace(Anthropic=FakeAnthropic))

    attempt = extract.run(bundle, "anthropic", "claude-haiku-test")
    assert attempt.worker_kind == "internal-cloud"
    assert attempt.model == "claude-haiku-test"
    assert attempt.tokens_in == 1000
    assert attempt.tokens_out == 200
    assert attempt.cost_usd > 0.0
    assert attempt.output is not None
    assert attempt.output.facts[0].entities[0].role == "engineer"


def test_extract_run_agent_cli_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = _sample_bundle()
    # Intentionally include trailing comma so json_repair exercises repair path
    malformed_inner = (
        '{"entities": [{"ref": "new:Omar", "kind": "person", "aliases": ["Omar"], "relation_to_user": "friend"}], '
        '"facts": [{"text": "Omar joined QamarTech.", "text_orig": null, "subject_path": "work/network", '
        '"entities": [{"entity_id": "new:Omar", "role": "colleague"}], "op": "new", "target": null, '
        '"valid_from": "2025-05-01", "evidence": ["r1"], "sensitive": null,}], "links": []}'
    )
    envelope = json.dumps(
        {
            "result": malformed_inner,
            "usage": {"input_tokens": 150, "output_tokens": 60},
            "total_cost_usd": 0.0,
        }
    )
    seen_cmd: dict[str, Any] = {}

    def fake_subprocess_run(cmd: list[str], *, input: str, **kwargs: Any) -> Any:
        seen_cmd["cmd"] = cmd
        seen_cmd["input"] = input
        return SimpleNamespace(returncode=0, stdout=envelope, stderr="")

    monkeypatch.setenv("TM_AGENT_CLI_CMD", "echo-agent --model {model} --json")
    monkeypatch.setattr(extract.subprocess, "run", fake_subprocess_run)

    attempt = extract.run(bundle, "agent-cli", "custom-model-1")
    assert seen_cmd["cmd"] == ["echo-agent", "--model", "custom-model-1", "--json"]
    assert "<untrusted_records>" in seen_cmd["input"]
    assert attempt.worker_kind == "agent-cli"
    assert attempt.model == "custom-model-1"
    assert attempt.tokens_in == 150
    assert attempt.tokens_out == 60
    assert attempt.cost_usd == 0.0
    assert attempt.output is not None
    assert attempt.output.facts[0].text == "Omar joined QamarTech."


def test_celery_app_config() -> None:
    assert celery_app.conf.task_ignore_result is True
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    queue_names = {q.name for q in celery_app.conf.task_queues}
    assert {"mem.p0", "mem.p1", "mem.p3"}.issubset(queue_names)
    assert celery_app.conf.beat_schedule["memory-reconcile-60s"]["task"] == "memory.reconcile"
    assert celery_app.conf.beat_schedule["memory-reconcile-60s"]["schedule"] == 60.0
