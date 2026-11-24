"""Day bucketing, packet chunks, and the cluster-root proposal."""
from __future__ import annotations

from pathlib import Path

import pytest

from temporal_memory.core.applier import apply
from temporal_memory.core.daytime import local_day
from temporal_memory.core.extract import PROMPT_VERSION, build_system_prompt
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema
from temporal_memory.ingest import triage
from temporal_memory.models import (
    Attempt,
    ExtractionOutput,
    OutFact,
    Owner,
    Record,
    Worker,
)
from temporal_memory.queue.jobs import PostgresJobs


@pytest.fixture()
def pg_db():
    db, schema = create_test_schema()
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


def _owner(store: PostgresGraphStore) -> None:
    store.create_owner(Owner(
        id="karim", label="Karim Haddad", kind="demo", display_name="Karim Haddad",
        self_aliases=["Karim"], timezone="Asia/Dubai",
    ))


def test_local_day_2030z_is_the_next_dubai_day_on_every_path(pg_db, monkeypatch):
    assert local_day("2026-10-20T20:30:00Z", "Asia/Dubai") == "2026-10-21"
    assert local_day("2026-10-20T10:00:00Z", "Asia/Dubai") == "2026-10-20"
    assert local_day("2026-10-20T10:00:00", "Asia/Dubai") == "2026-10-20"

    store = PostgresGraphStore(pg_db)
    _owner(store)
    early = Record(
        id="early", owner="karim", source="notes", at="2026-10-20T10:00:00Z",
        author="Karim", text="Morning notes about the marina walk.",
    )
    late = Record(
        id="late", owner="karim", source="notes", at="2026-10-20T20:30:00Z",
        author="Karim", text="Late notes after the marina walk.",
    )
    ingested = triage.ingest_records(pg_db, "karim", [early, late])
    assert ingested["days"] == ["2026-10-20", "2026-10-21"]

    jobs = PostgresJobs(pg_db, store=store)
    parent = jobs.enqueue("karim", "import.split", ["early", "late"], 1)
    worker = Worker(id="w", kind="internal-local", model="m", runner="lmstudio", owner=None, released=True)
    bundle = jobs.claim_by_id(parent.id, worker)
    assert bundle is not None and bundle.job.id == parent.id
    assert jobs.split_import(bundle.job) == 2
    with pg_db.connection() as conn:
        days = {row["day"] for row in conn.execute(
            "SELECT day FROM jobs WHERE owner = 'karim' AND kind = 'extract.day'"
        )}
    assert days == {"2026-10-20", "2026-10-21"}
    monkeypatch.setenv("TM_PACKET_TOKEN_BUDGET", "4000")


def test_heavy_day_chunks_and_the_later_chunk_sees_the_new_fact(pg_db, monkeypatch):
    monkeypatch.setenv("TM_PACKET_TOKEN_BUDGET", "30")
    store = PostgresGraphStore(pg_db)
    _owner(store)
    blob = "word " * 80
    records = [
        Record(
            id="c1", owner="karim", source="notes", at="2026-10-21T08:00:00Z",
            author="Karim", text=blob + "first cafe visit",
        ),
        Record(
            id="c2", owner="karim", source="notes", at="2026-10-21T09:00:00Z",
            author="Karim", text=blob + "second cafe visit",
        ),
    ]
    store.upsert_records("karim", records)
    jobs = PostgresJobs(pg_db, store=store)
    created = jobs.enqueue_day_packet(
        "karim", records, pool="internal", day="2026-10-21", sensitive_flag=False,
    )
    assert len(created) == 2
    again = jobs.enqueue_day_packet(
        "karim", records, pool="internal", day="2026-10-21", sensitive_flag=False,
    )
    assert {job.id for job in again} == {job.id for job in created}

    worker = Worker(id="w", kind="internal-local", model="m", runner="lmstudio", owner=None, released=True)
    first = jobs.claim(worker, ["internal"], owner="karim", limit=1)[0]
    fact = OutFact(
        text="Karim visited the first cafe", text_orig=None, subject_path="events/cafes",
        entities=[], op="new", target=None, valid_from="2026-10-21",
        evidence=[first.records[0].id], sensitive=None, stated=True,
    )
    apply(
        "karim",
        first.job,
        Attempt(
            job_id=first.job.id, attempt_no=first.job.attempt_no, fence_token=first.job.fence_token,
            worker_id="w", worker_kind="internal-local", model="m", prompt_version=PROMPT_VERSION,
            output=ExtractionOutput(entities=[], facts=[fact], links=[]),
        ),
        db=pg_db,
    )
    second = jobs.claim(worker, ["internal"], owner="karim", limit=1)[0]
    shown = {row["id"] for row in second.context["facts"]}
    assert shown
    assert any(row["text"] == "Karim visited the first cafe" for row in second.context["facts"])


def test_split_import_uses_owner_device_when_a_device_is_active(pg_db):
    store = PostgresGraphStore(pg_db)
    _owner(store)
    record = Record(
        id="plain", owner="karim", source="notes", at="2026-10-22T09:00:00Z",
        author="Karim", text="Reviewed the marina notes.",
    )
    store.upsert_records("karim", [record])
    with pg_db.transaction() as conn:
        conn.execute(
            "INSERT INTO tokens (id, token_hash, role, owner, label) VALUES (%s, %s, %s, %s, %s)",
            ("tok-u3", "hash-u3", "owner-device", "karim", "phone"),
        )
    jobs = PostgresJobs(pg_db, store=store)
    jobs.enqueue("karim", "import.split", ["plain"], 1)
    worker = Worker(id="w", kind="internal-local", model="m", runner="lmstudio", owner=None, released=True)
    bundle = jobs.claim(worker, ["internal"], owner="karim", limit=1)[0]
    assert jobs.split_import(bundle.job) == 1
    with pg_db.connection() as conn:
        row = conn.execute(
            "SELECT pool FROM jobs WHERE owner = 'karim' AND kind = 'extract.day'"
        ).fetchone()
    assert row["pool"] == "owner-device"


def test_prompt_roots_and_cluster_proposal_mapping():
    assert PROMPT_VERSION == "extract@4"
    prompt = build_system_prompt(Owner(
        id="karim", label="Karim", kind="demo", display_name="Karim Haddad",
    ))
    for root in ("career", "learning", "projects", "people-family", "events", "home-money", "travel", "health", "faith"):
        assert root in prompt
    assert "stated" in prompt and "place_type" in prompt

    proposal = Path(__file__).parents[1] / "src" / "temporal_memory" / "db" / "proposals" / "cluster_roots.sql"
    text = proposal.read_text(encoding="utf-8")
    assert "Do not run" in text
    mapping = {
        "background": "career",
        "devices": "home-money",
        "family": "people-family",
        "health": "health",
        "identity": "people-family",
        "interests": "events",
        "learning": "learning",
        "lifestyle": "home-money",
        "money": "home-money",
        "projects": "projects",
        "wellbeing": "health",
        "work": "career",
    }
    for old, new in mapping.items():
        assert f"{old} -> {new}" in text or f"{old:<10} -> {new}" in text
