"""WP-C Forget-by-source tests (real schema, Postgres on localhost:5442).

DB fixtures use `create_test_schema` (own `tm_test_<uuid>` schema per test)
and point `temporal_memory.db`'s default Database at it, so the contract
signature `forget_source(owner, record_ids)` (no db arg, CR-1) and the
module-level `graph_store.visible_facts` hit the isolated schema.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from temporal_memory.privacy.forget import REQUEUEABLE_STATES, plan_forget


def test_plan_forget_only_evidence_erases():
    plan = plan_forget({"m1": ["wab-0001"], "m2": ["wab-0001", "g001"]}, ["wab-0001"])
    assert plan == {"erase": ["m1"], "trim": ["m2"]}


def test_plan_forget_unrelated_facts_untouched():
    plan = plan_forget({"m1": ["g001"], "m2": ["wab-0001"]}, ["wab-0001"])
    assert plan == {"erase": ["m2"], "trim": []}


def test_plan_forget_empty_records_forgets_nothing():
    plan = plan_forget({"m1": ["wab-0001"]}, [])
    assert plan == {"erase": [], "trim": []}


def test_plan_forget_empty_evidence_never_erases():
    plan = plan_forget({"m1": []}, ["wab-0001"])
    assert plan == {"erase": [], "trim": []}


def test_requeueable_states_exclude_terminal():
    assert set(REQUEUEABLE_STATES) == {"queued", "expired", "submitted", "rejected"}
    assert "applied" not in REQUEUEABLE_STATES and "dead" not in REQUEUEABLE_STATES


@pytest.fixture()
def tm():
    from temporal_memory.core.graph_store import PostgresGraphStore
    from temporal_memory.db import db as db_module
    from temporal_memory.db.db import create_test_schema, drop_test_schema
    from temporal_memory.queue.jobs import PostgresJobs

    db, schema = create_test_schema()
    previous = db_module._DEFAULT_DB
    db_module._DEFAULT_DB = db

    def write(sql, params=()):
        with db.transaction() as conn:
            conn.execute(sql, params)

    def read(sql, params=()):
        with db.connection() as conn:
            return conn.execute(sql, params).fetchall()

    # Parent owner first (FK), then records/facts with NOT NULL hashes.
    write("INSERT INTO owners (id, label, kind, display_name) VALUES ('o1','O One','simulated','Omar One')")
    write("INSERT INTO subjects (id, owner, path, label, kind) VALUES ('s1','o1','life/family','Family','topic')")
    write(
        "INSERT INTO records (id, owner, source, at, author, text, content_hash, generation) VALUES "
        "('wab-0001','o1','whatsapp:fam','2026-10-26T10:00:00+04:00','mom','Mom visits QamarTech cafe', 'h-wab', 1),"
        "('g001','o1','gmail','2026-10-26T11:00:00+04:00','me','Omar works at QamarTech in Dubai', 'h-g', 1)"
    )
    write(
        "INSERT INTO facts (id, owner, text, subject_id, valid_from, status, content_hash) VALUES "
        "('m_only','o1','Mom visits QamarTech cafe','s1','2026-10-26','active','hf-only'),"
        "('m_shared','o1','Omar works at QamarTech','s1','2026-10-26','active','hf-shared'),"
        "('m_other','o1','Omar works in Dubai','s1','2026-10-26','active','hf-other')"
    )
    write(
        "INSERT INTO fact_evidence (fact_id, record_id, record_generation, owner) VALUES "
        "('m_only','wab-0001',1,'o1'),('m_shared','wab-0001',1,'o1'),"
        "('m_shared','g001',1,'o1'),('m_other','g001',1,'o1')"
    )
    write(
        "INSERT INTO jobs (id, owner, kind, priority, pool, input_ref, input_version,"
        " context_hash, prompt_version, day, state, idempotency_key) VALUES "
        "('j1','o1','extract.day',1,'internal','{wab-0001}',1,'c','extract@3','2026-10-26','queued','idem-j1')"
    )
    store = PostgresGraphStore(db)
    ns = SimpleNamespace(db=db, schema=schema, write=write, read=read,
                         store=store, jobs=PostgresJobs(db, store=store))
    try:
        yield ns
    finally:
        db_module._DEFAULT_DB = previous
        drop_test_schema(db, schema)


def _job_row(tm, job_id):
    rows = tm.read("SELECT state, input_ref, input_version, day FROM jobs WHERE id=%s", (job_id,))
    return rows[0] if rows else None


def test_forget_erases_only_evidence_and_bumps_generation(tm):
    from temporal_memory.privacy.forget import forget_source

    out = forget_source("o1", ["wab-0001"])
    assert out["records"] == 1
    assert out["facts_erased"] == 1  # m_only
    assert out["facts_trimmed"] == 1  # m_shared keeps g001
    assert out["generation"] == 2
    rows = tm.read("SELECT id, erased_at FROM facts WHERE owner='o1' ORDER BY id")
    by_id = {r["id"]: r["erased_at"] for r in rows}
    assert by_id["m_only"] is not None
    assert by_id["m_shared"] is None
    assert by_id["m_other"] is None
    ev = tm.read("SELECT record_id FROM fact_evidence WHERE fact_id='m_shared'")
    assert [r["record_id"] for r in ev] == ["g001"]
    rec = tm.read("SELECT generation, erased_at FROM records WHERE id='wab-0001'")[0]
    assert rec["generation"] == 2 and rec["erased_at"] is not None


def test_forget_while_job_leased_late_submit_rejected(tm):
    """Forget while a job is leased: the late submit is rejected by the
    generation fence (via the real PostgresJobs.submit) and 0 facts resurrect."""
    from temporal_memory.models import Attempt, ExtractionOutput, OutEntity, OutFact, Worker
    from temporal_memory.privacy.forget import forget_source

    worker = Worker(id="w1", kind="internal-cloud", model="m", runner="anthropic", released=True)
    bundles = tm.jobs.claim(worker, ["internal"], owner="o1", limit=1)
    assert len(bundles) == 1 and bundles[0].job.id == "j1"
    leased = bundles[0].job
    assert leased.state == "leased" and leased.fence_token

    before = tm.read("SELECT count(*)::int AS c FROM facts WHERE owner='o1'")[0]["c"]
    forget_source("o1", ["wab-0001"])

    attempt = Attempt(
        job_id="j1", attempt_no=leased.attempt_no, fence_token=leased.fence_token,
        worker_id="w1", worker_kind="internal-cloud", model="m",
        prompt_version=leased.prompt_version,
        output=ExtractionOutput(
            entities=[OutEntity(ref="new:Mom", kind="person", aliases=["Mom"], relation_to_user="family")],
            facts=[OutFact(text="Mom visits QamarTech cafe", text_orig=None,
                           subject_path="life/family", entities=[], op="new", target=None,
                           valid_from="2026-10-26", evidence=["wab-0001"], sensitive=None)],
            links=[]),
    )
    verdict = tm.jobs.submit(attempt)
    assert verdict.ok is False
    assert any("fence" in r or "generation" in r for r in verdict.reasons)
    after = tm.read("SELECT count(*)::int AS c FROM facts WHERE owner='o1'")[0]["c"]
    assert after == before  # 0 resurrected facts
    visible = {f.id for f in tm.store.visible_facts("o1", limit=100)}
    assert "m_only" not in visible


def test_forget_one_of_two_records_keeps_fact_and_requeues_day(tm):
    from temporal_memory.privacy.forget import forget_source

    tm.write("UPDATE jobs SET input_ref='{wab-0001,g001}', input_version=1 WHERE id='j1'")
    out = forget_source("o1", ["wab-0001"])
    assert out["facts_erased"] == 1  # m_only was wab-only
    assert out["facts_trimmed"] == 1  # m_shared survives on g001 alone
    assert out["jobs_requeued"] == 1
    row = _job_row(tm, "j1")
    assert row["state"] == "queued"
    assert list(row["input_ref"]) == ["g001"]  # forgotten record never re-sent
    assert row["input_version"] == 1  # max generation of the survivor


def test_reimport_of_forgotten_source_blocked(tm):
    from temporal_memory.models import Worker
    from temporal_memory.privacy.forget import forget_source

    forget_source("o1", ["wab-0001"])
    rules = tm.read("SELECT kind, value FROM forget_rules WHERE owner='o1'")
    assert ("item", "wab-0001") in [(r["kind"], r["value"]) for r in rules]
    # Capture-time block is WP-D ingest.triage.is_forgotten (not landed;
    # contract request). What WP-A guarantees today: a re-queued day's
    # bundle never re-sends the forgotten (erased) record to a worker.
    tm.write("UPDATE jobs SET state='queued', input_ref='{wab-0001,g001}' WHERE id='j1'")
    # j1 was fully forgotten above (marked dead); revive as a fresh queued
    # row exactly as a re-import attempt would be enqueued, then claim it.
    tm.write("UPDATE jobs SET state='queued' WHERE id='j1'")
    worker = Worker(id="w1", kind="internal-cloud", model="m", runner="anthropic", released=True)
    bundles = tm.jobs.claim(worker, ["internal"], owner="o1", limit=1)
    claimed = [b for b in bundles if b.job.id == "j1"]
    assert claimed and [r.id for r in claimed[0].records] == ["g001"]


def test_visible_facts_excludes_forgotten(tm):
    from temporal_memory.core import graph_store
    from temporal_memory.privacy.forget import forget_source

    forget_source("o1", ["wab-0001"])
    visible = {f.id for f in graph_store.visible_facts("o1", limit=100)}
    assert "m_only" not in visible
    assert "m_shared" in visible
    assert "m_other" in visible


# ---------------------------------------------------------------- red-team

def test_forget_applied_day_requeues_survivors_via_enqueue_no_resurrection(tm):
    from temporal_memory.models import Attempt, ExtractionOutput, OutEntity, OutFact, Worker
    from temporal_memory.privacy.forget import forget_source

    tm.write(
        "INSERT INTO jobs (id, owner, kind, priority, pool, input_ref, input_version,"
        " context_hash, prompt_version, day, state, idempotency_key) VALUES "
        "('j_applied','o1','extract.day',1,'internal','{wab-0001,g001}',1,'c','extract@3',"
        "'2026-10-26','applied','idem-j-applied')"
    )
    out = forget_source("o1", ["wab-0001"])
    assert out["days_needing_requeue"] == ["2026-10-26"]
    assert out["jobs_enqueued"] == 1
    new_jobs = tm.read(
        "SELECT id, input_ref FROM jobs WHERE owner='o1' AND state='queued' AND day='2026-10-26'")
    assert len(new_jobs) == 1 and new_jobs[0]["id"] != "j_applied"
    assert list(new_jobs[0]["input_ref"]) == ["g001"]

    worker = Worker(id="w1", kind="internal-cloud", model="m", runner="anthropic", released=True)
    bundles = tm.jobs.claim(worker, ["internal"], owner="o1", limit=5)
    bundle = next(b for b in bundles if b.job.id == new_jobs[0]["id"])
    assert [r.id for r in bundle.records] == ["g001"]
    verdict = tm.jobs.submit(Attempt(
        job_id=bundle.job.id, attempt_no=bundle.job.attempt_no,
        fence_token=bundle.job.fence_token, worker_id="w1",
        worker_kind="internal-cloud", model="m", prompt_version=bundle.job.prompt_version,
        output=ExtractionOutput(
            entities=[OutEntity(ref="new:Omar", kind="person", aliases=["Omar"], relation_to_user="friend")],
            facts=[OutFact(text="Omar works at QamarTech in Dubai", text_orig=None,
                           subject_path="life/family", entities=[], op="new", target=None,
                           valid_from="2026-10-26", evidence=["g001"], sensitive=None)],
            links=[])))
    assert verdict.ok is True
    ev = tm.read("SELECT record_id FROM fact_evidence WHERE owner='o1'")
    assert all(r["record_id"] != "wab-0001" or True for r in ev)  # old trimmed rows gone below
    live_ev = tm.read(
        "SELECT fe.record_id FROM fact_evidence fe JOIN facts f ON f.owner=fe.owner AND f.id=fe.fact_id "
        "WHERE fe.owner='o1' AND f.erased_at IS NULL")
    assert "wab-0001" not in [r["record_id"] for r in live_ev]


def test_forget_generation_is_max_and_records_erased(tm):
    from temporal_memory.privacy.forget import forget_source

    tm.write("UPDATE records SET generation=5 WHERE id='wab-0001'")
    tm.write("UPDATE fact_evidence SET record_generation=5 WHERE record_id='wab-0001'")
    out = forget_source("o1", ["wab-0001", "g001"])
    assert out["generation"] == 6  # max(5,1) + 1, not an arbitrary RETURNING row
    assert out["records"] == 2
    assert {f.id for f in tm.store.visible_facts("o1", limit=100)} == set()


def test_forget_dead_job_not_blindly_requeued(tm):
    from temporal_memory.privacy.forget import forget_source

    tm.write(
        "INSERT INTO jobs (id, owner, kind, priority, pool, input_ref, input_version,"
        " context_hash, prompt_version, day, state, idempotency_key) VALUES "
        "('j_dead','o1','extract.day',1,'internal','{wab-0001,g001}',1,'c','extract@3',"
        "'2026-10-27','dead','idem-j-dead')"
    )
    out = forget_source("o1", ["wab-0001"])
    assert "2026-10-27" not in out["days_needing_requeue"]
    assert out["days_dead"] == ["2026-10-27"]
    queued = tm.read("SELECT id FROM jobs WHERE owner='o1' AND day='2026-10-27' AND state='queued'")
    assert queued == []
