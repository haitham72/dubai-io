"""Exercise recovery and isolation against actual RabbitMQ deliveries."""

import json
from uuid import uuid4

import pytest

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.models import Owner, Record

from .race_runner import DUPLICATE_TASK_PREFIX, RACE_SOURCE


pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def race_stack(stack):
    with stack.db.transaction() as conn:
        conn.execute("""
            CREATE TABLE tm_e2e_race_gates (
                record_id TEXT PRIMARY KEY,
                attempt_no INTEGER NOT NULL
            );
            CREATE TABLE tm_e2e_race_calls (
                id BIGSERIAL PRIMARY KEY,
                job_id TEXT NOT NULL,
                attempt_no INTEGER NOT NULL,
                fence_token TEXT NOT NULL,
                worker_id TEXT NOT NULL
            );
            CREATE TABLE tm_e2e_race_outcomes (
                id BIGSERIAL PRIMARY KEY,
                task_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                status TEXT NOT NULL
            );
        """)
    return stack


@pytest.fixture
def owner(race_stack):
    owner = Owner(f"e2e_race_{uuid4().hex}", "Synthetic queue owner", "simulated")
    return PostgresGraphStore(race_stack.db).create_owner(owner).id


def _enqueue(stack, owner, slot, *, priority=1, block=False):
    record = Record(
        id=f"race_{uuid4().hex}",
        owner=owner,
        source=RACE_SOURCE,
        at="2026-11-01T10:00:00+04:00",
        author="Synthetic Owner",
        text=f"The ceramic workshop scheduled session {slot}.",
    )
    PostgresGraphStore(stack.db).upsert_records(owner, [record])
    if block:
        stack.rows(
            "INSERT INTO tm_e2e_race_gates (record_id, attempt_no) VALUES (%s, 1) RETURNING record_id",
            (record.id,),
        )
    kind = "extract.live" if priority == 0 else "extract.day"
    return stack.jobs.enqueue(owner, kind, [record.id], priority, day=record.at[:10]), record


def _unblock(stack, *records):
    stack.rows(
        "DELETE FROM tm_e2e_race_gates WHERE record_id = ANY(%s) RETURNING record_id",
        ([record.id for record in records],),
    )


def _calls(stack, job):
    return stack.rows(
        "SELECT attempt_no, fence_token, worker_id FROM tm_e2e_race_calls WHERE job_id = %s ORDER BY id",
        (job.id,),
    )


def _wait_started(stack, job):
    return stack.wait(lambda: _calls(stack, job), description=f"oracle invoked for {job.id}", timeout=25)[0]


def _fact_texts(stack, job):
    return [row["text"] for row in stack.rows(
        "SELECT text FROM facts WHERE owner = %s AND job_id = %s AND erased_at IS NULL",
        (job.owner, job.id),
    )]


def test_killed_worker_recovers_after_lease_expiry(race_stack, owner):
    stack = race_stack
    job, record = _enqueue(stack, owner, 1, block=True)
    first_call = _wait_started(stack, job)
    original = stack.wait_job(job.id, "leased", timeout=5)
    assert original["fence_token"] == first_call["fence_token"]
    stack.compose("kill", "-s", "SIGKILL", "worker-p1")
    try:
        requeued = stack.wait_job(job.id, "queued", timeout=25)
        assert requeued["attempt_no"] == 1
        assert requeued["fence_token"] is None
        assert requeued["updated_at"] >= original["lease_expires_at"]
        assert _fact_texts(stack, job) == []
    finally:
        _unblock(stack, record)
        stack.compose("start", "worker-p1")

    recovered = stack.wait_job(job.id, "applied", timeout=25)
    calls = _calls(stack, job)
    assert recovered["attempt_no"] == 2
    assert [call["attempt_no"] for call in calls] == [1, 2]
    assert calls[0]["fence_token"] != calls[1]["fence_token"]
    assert _fact_texts(stack, job) == [record.text]


def test_duplicate_broker_delivery_only_invokes_oracle_once(race_stack, owner):
    stack = race_stack
    job, record = _enqueue(stack, owner, 1, block=True)
    try:
        _wait_started(stack, job)
        duplicate_id = f"{DUPLICATE_TASK_PREFIX}{uuid4().hex}"
        stack.broker.send_task("memory.run_job", args=[job.id], queue="mem.p1", task_id=duplicate_id)
        outcomes = stack.wait(
            lambda: stack.rows("SELECT status FROM tm_e2e_race_outcomes WHERE task_id = %s", (duplicate_id,)),
            description=f"worker processed duplicate for {job.id}",
            timeout=7,
        )
        assert outcomes == [{"status": "skipped"}]
        assert len(_calls(stack, job)) == 1
    finally:
        _unblock(stack, record)

    stack.wait_job(job.id, "applied", timeout=25)
    assert [call["attempt_no"] for call in _calls(stack, job)] == [1]
    assert _fact_texts(stack, job) == [record.text]


def test_forget_source_while_import_packet_is_leased(race_stack, owner):
    stack = race_stack
    prior, prior_record = _enqueue(stack, owner, 1)
    stack.wait_job(prior.id, "applied", timeout=25)
    assert _fact_texts(stack, prior) == [prior_record.text]

    inflight, inflight_record = _enqueue(stack, owner, 2, block=True)
    try:
        _wait_started(stack, inflight)
        outcome = stack.compose(
            "exec", "-T", "api", "python", "-c",
            "import json, sys; from temporal_memory.privacy.forget import forget_source; "
            "print(json.dumps(forget_source(sys.argv[1], sys.argv[2:])))",
            owner, prior_record.id, inflight_record.id,
            timeout=8,
        )
        assert json.loads(outcome.stdout)["records"] == 2
        assert _fact_texts(stack, prior) == []
    finally:
        _unblock(stack, inflight_record)

    completed = stack.wait(
        lambda: stack.rows("SELECT status FROM tm_e2e_race_outcomes WHERE job_id = %s ORDER BY id", (inflight.id,)),
        description="worker finishes the extraction that began before Forget",
        timeout=25,
    )
    assert completed[0]["status"] in {"rejected", "skipped"}
    assert _fact_texts(stack, inflight) == []
    assert stack.rows("SELECT text FROM visible_facts WHERE owner = %s", (owner,)) == []


def test_p1_import_flood_cannot_starve_p0_outbox_delivery(race_stack, owner):
    stack = race_stack
    blockers = [_enqueue(stack, owner, slot, block=True) for slot in (1, 2)]
    try:
        for job, _ in blockers:
            _wait_started(stack, job)
            stack.wait_job(job.id, "leased", timeout=5)
        backlog = [_enqueue(stack, owner, slot)[0] for slot in range(3, 13)]
        live, record = _enqueue(stack, owner, 13, priority=0)

        stack.wait_job(live.id, "applied", timeout=7)
        assert _fact_texts(stack, live) == [record.text]
        queued = stack.rows(
            "SELECT count(*) AS n FROM jobs WHERE id = ANY(%s) AND state = 'queued'",
            ([job.id for job in backlog],),
        )
        assert queued[0]["n"] == len(backlog)
        for job, _ in blockers:
            current = stack.wait_job(job.id, "leased", timeout=5)
            assert current["attempt_no"] == 1
    finally:
        _unblock(stack, *(record for _, record in blockers))

    for job in [*(job for job, _ in blockers), *backlog]:
        stack.wait_job(job.id, "applied", timeout=25)
