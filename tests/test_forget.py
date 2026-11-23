"""WP-C Forget-by-source tests.

Runnable now: the pure evidence-split logic (`plan_forget`).
DB integration (needs WP-A `db/schema.sql`, the validator fence and the
`visible_facts` view) is marked xfail with its reason per the B-C prompt —
the SQL in forget.py targets the v2.1 standalone table names and activates
unchanged once the schema lands.
"""
import importlib.util
import os
from pathlib import Path

import pytest

from temporal_memory.privacy.forget import REQUEUEABLE_STATES, plan_forget

XFAIL_DB = pytest.mark.xfail(
    reason="WP-A db/schema.sql not landed on main; needs schema + validator "
           "generation fence + visible_facts view",
    strict=False,
)


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


@pytest.fixture()
def tm_db():
    """Live-DB fixture for the day WP-A's schema lands. Today it raises with
    the reason the xfail documents; the seed below matches the v2.1 §3.2
    standalone table names so the tests activate unchanged."""
    spec = importlib.util.find_spec("temporal_memory.db")
    roots = list(spec.submodule_search_locations or []) if spec else []
    schema = next((Path(r) / "schema.sql" for r in roots
                   if (Path(r) / "schema.sql").exists()), None)
    if schema is None:
        raise RuntimeError("db/schema.sql missing: WP-A has not landed the DDL")
    if not os.environ.get("TM_TEST_DATABASE_URL"):
        raise RuntimeError("TM_TEST_DATABASE_URL is not set")
    import psycopg

    admin = psycopg.connect(os.environ["TM_TEST_DATABASE_URL"], autocommit=True)
    ns = "tm_test_forget_wpC"
    admin.execute(f'DROP SCHEMA IF EXISTS "{ns}" CASCADE')
    admin.execute(f'CREATE SCHEMA "{ns}"')
    admin.execute(f'SET search_path TO "{ns}"')
    admin.execute(schema.read_text(encoding="utf-8"))
    admin.execute(
        "INSERT INTO records (id, owner, source, at, author, text, generation) VALUES "
        "('wab-0001','o1','whatsapp:fam','2026-10-26T10:00:00+04:00','mom','x',1),"
        "('g001','o1','gmail','2026-10-26T11:00:00+04:00','me','y',1)")
    admin.execute(
        "INSERT INTO facts (id, owner, text, subject_id, valid_from, status) VALUES "
        "('m_only','o1','t','s1','2026-10-26','active'),"
        "('m_shared','o1','t','s1','2026-10-26','active'),"
        "('m_other','o1','t','s1','2026-10-26','active')")
    admin.execute(
        "INSERT INTO fact_evidence (fact_id, record_id, record_generation, owner) VALUES "
        "('m_only','wab-0001',1,'o1'),('m_shared','wab-0001',1,'o1'),"
        "('m_shared','g001',1,'o1'),('m_other','g001',1,'o1')")
    admin.execute(
        "INSERT INTO jobs (id, owner, kind, priority, pool, input_ref, input_version,"
        " context_hash, prompt_version, day, state) VALUES "
        "('j1','o1','extract.day',1,'internal','{wab-0001}',1,'c','p','2026-10-26','queued')")

    def run(sql):
        with admin.cursor() as cur:
            cur.execute(f'SET search_path TO "{ns}"; ' + sql)
            try:
                return cur.fetchall()
            except Exception:
                return []

    yield run
    admin.execute(f'DROP SCHEMA IF EXISTS "{ns}" CASCADE')
    admin.close()


def test_requeueable_states_exclude_terminal():
    assert set(REQUEUEABLE_STATES) == {"queued", "expired", "submitted", "rejected"}
    assert "applied" not in REQUEUEABLE_STATES and "dead" not in REQUEUEABLE_STATES


@XFAIL_DB
def test_forget_erases_only_evidence_and_bumps_generation(tm_db):
    from temporal_memory.privacy.forget import forget_source

    out = forget_source("o1", ["wab-0001"])
    assert out["records"] == 1
    assert out["facts_erased"] == 1  # m_only
    assert out["facts_trimmed"] == 1  # m_shared keeps g001
    assert out["generation"] == 2
    rows = tm_db("SELECT id, erased_at FROM facts WHERE owner='o1' ORDER BY id")
    by_id = dict(rows)
    assert by_id["m_only"] is not None
    assert by_id["m_shared"] is None
    assert by_id["m_other"] is None
    ev = tm_db("SELECT fact_id FROM fact_evidence WHERE fact_id='m_shared'")
    assert [r[0] for r in ev] == ["m_shared"]


@XFAIL_DB
def test_forget_while_job_leased_late_submit_rejected(tm_db):
    """Lease a day job, forget its record, then submit the stale attempt:
    the validator fence (input_version < generation) must reject it."""
    from temporal_memory.privacy import forget as forget_mod

    tm_db("UPDATE jobs SET state='leased', fence_token='f1', attempt_no=1, "
          "worker_id='w1' WHERE id='j1'")
    forget_mod.forget_source("o1", ["wab-0001"])
    from temporal_memory.models import Attempt

    attempt = Attempt(job_id="j1", attempt_no=1, fence_token="f1", worker_id="w1",
                      worker_kind="internal-cloud", model="m", prompt_version="p",
                      output=None)
    from temporal_memory.core import validator  # WP-A

    verdict = validator.validate(
        __import__("temporal_memory.models", fromlist=["Job"]).Job(
            id="j1", owner="o1", kind="extract.day", priority=1, pool="internal",
            input_ref=["wab-0001"], input_version=1, context_hash="c",
            prompt_version="p", day="2026-10-26", state="leased",
            fence_token="f1"),
        None, attempt)
    assert verdict.ok is False
    assert any("fence" in r or "generation" in r for r in verdict.reasons)


@XFAIL_DB
def test_forget_one_of_two_records_keeps_fact_and_requeues_day(tm_db):
    from temporal_memory.privacy.forget import forget_source

    out = forget_source("o1", ["wab-0001"])
    assert out["facts_erased"] == 0
    assert out["facts_trimmed"] == 1
    assert out["jobs_requeued"] == 1
    state = tm_db("SELECT state FROM jobs WHERE id='j1'")[0][0]
    assert state == "queued"


@XFAIL_DB
def test_reimport_of_forgotten_source_blocked(tm_db):
    from temporal_memory.privacy.forget import forget_source

    forget_source("o1", ["wab-0001"])
    rules = tm_db("SELECT kind, value FROM forget_rules WHERE owner='o1'")
    assert ("item", "wab-0001") in rules
    # Capture-time contract: ingest/triage must refuse records matching a rule.
    from temporal_memory.ingest import triage  # WP-D

    assert triage.is_forgotten("o1", "wab-0001") is True


@XFAIL_DB
def test_visible_facts_excludes_forgotten(tm_db):
    from temporal_memory.privacy.forget import forget_source

    forget_source("o1", ["wab-0001"])
    from temporal_memory.core import graph_store  # WP-A

    visible = {f.id for f in graph_store.visible_facts("o1", limit=100)}
    assert "m_only" not in visible
    assert "m_shared" in visible
    assert "m_other" in visible
