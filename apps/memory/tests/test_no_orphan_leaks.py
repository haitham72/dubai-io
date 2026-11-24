"""Quarantine must not leave a person, alias, label or link behind."""
from __future__ import annotations

import pytest

from temporal_memory.core.applier import apply
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema
from temporal_memory.models import (
    Attempt,
    ExtractionOutput,
    FactEntity,
    Job,
    OutEntity,
    OutFact,
    OutLink,
    Owner,
    Record,
)


@pytest.fixture()
def db_env():
    db, schema = create_test_schema()
    store = PostgresGraphStore(db)
    store.create_owner(
        Owner(id="karim", label="Karim Haddad", kind="demo", display_name="Karim Haddad", self_aliases=["Karim"])
    )
    yield db, store
    drop_test_schema(db, schema)


def _job(job_id: str, input_ref: list[str]) -> Job:
    return Job(
        id=job_id, owner="karim", kind="extract.day", priority=1, pool="internal",
        input_ref=input_ref, input_version=0, context_hash="ctx", prompt_version="extract@3",
        state="leased", attempt_no=1, fence_token="tok", worker_id="w",
    )


def _attempt(job_id: str, output: ExtractionOutput) -> Attempt:
    return Attempt(
        job_id=job_id, attempt_no=1, fence_token="tok", worker_id="w", worker_kind="internal-cloud",
        model="m", prompt_version="extract@3", output=output,
    )


def _rec(rid: str, text: str, at: str, author: str = "Omar") -> Record:
    return Record(id=rid, owner="karim", source="whatsapp:family", at=at, author=author, text=text, generation=0)


def test_quarantined_only_fact_leaves_no_entity_alias_or_link(db_env):
    db, store = db_env
    store.upsert_records("karim", [_rec("r1", "Layla's doctor changed her diabetes tablets", "2026-10-22T10:00:00Z")])
    out = ExtractionOutput(
        entities=[OutEntity(ref="new:Layla Haddad", kind="person", aliases=["Layla"], relation_to_user="family")],
        facts=[OutFact(
            text="Layla Haddad's doctor changed her diabetes tablets",
            text_orig=None, subject_path="family/health",
            entities=[FactEntity(entity_id="new:Layla Haddad", role="patient")],
            op="new", target=None, valid_from="2026-10-22", evidence=["r1"], sensitive=None,
        )],
        links=[OutLink(src="new:Layla Haddad", rel="RELATED_TO", dst="new:Karim Haddad", valid_from="2026-10-22", evidence=["r1"])],
    )
    verdict = apply("karim", _job("j-q", ["r1"]), _attempt("j-q", out), db=db)
    assert verdict.ok is True
    assert verdict.applied_fact_ids == []
    assert store.list_entities("karim") == []
    assert store.list_links("karim") == []
    with db.connection() as conn:
        aliases = conn.execute("SELECT alias FROM entity_aliases WHERE owner = 'karim'").fetchall()
    assert aliases == []


def test_mixed_day_links_cite_their_own_facts(db_env):
    db, store = db_env
    store.upsert_records("karim", [
        _rec("r-work", "Nadia joined Falcon Tech", "2026-10-05T09:00:00Z", author="Karim"),
        _rec("r-cafe", "Karim met Nadia at a cafe", "2026-10-05T18:00:00Z", author="Karim"),
    ])
    out = ExtractionOutput(
        entities=[
            OutEntity(ref="new:Nadia Mansour", kind="person", aliases=["Nadia"], relation_to_user="colleague"),
            OutEntity(ref="new:Falcon Tech", kind="org", aliases=[], relation_to_user=None),
        ],
        facts=[
            OutFact(
                text="Nadia Mansour joined Falcon Tech", text_orig=None, subject_path="work/team",
                entities=[
                    FactEntity(entity_id="new:Nadia Mansour", role="employee"),
                    FactEntity(entity_id="new:Falcon Tech", role="employer"),
                ],
                op="new", target=None, valid_from="2026-10-05", evidence=["r-work"], sensitive=None,
            ),
            OutFact(
                text="Karim met Nadia at a cafe", text_orig=None, subject_path="work/social",
                entities=[FactEntity(entity_id="new:Nadia Mansour", role="colleague")],
                op="new", target=None, valid_from="2026-10-05", evidence=["r-cafe"], sensitive=None,
            ),
        ],
        links=[OutLink(
            src="new:Nadia Mansour", rel="WORKS_AT", dst="new:Falcon Tech",
            valid_from="2026-10-05", evidence=["r-cafe"],
        )],
    )
    verdict = apply("karim", _job("j-mix", ["r-work", "r-cafe"]), _attempt("j-mix", out), db=db)
    assert len(verdict.applied_fact_ids) == 2
    links = store.list_links("karim")
    assert len(links) == 1
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT fact_id FROM link_evidence WHERE owner = 'karim' AND link_id = %s",
            (links[0].id,),
        ).fetchall()
        cited = conn.execute("SELECT text FROM facts WHERE id = %s", (links[0].evidence_fact_id,)).fetchone()
    assert cited["text"] == "Karim met Nadia at a cafe"
    assert {row["fact_id"] for row in rows} == {links[0].evidence_fact_id}


def test_two_day_promotion_keeps_inferred_provenance(db_env):
    db, store = db_env
    for day, rid in (("2026-10-01", "p1"), ("2026-10-02", "p2")):
        store.upsert_records("karim", [_rec(rid, "The team met at Zabeel Park", f"{day}T09:00:00Z", author="Omar")])
        out = ExtractionOutput(
            entities=[OutEntity(ref="new:Zabeel Park", kind="place", aliases=["Zabeel"], relation_to_user=None)],
            facts=[OutFact(
                text="The team met at Zabeel Park", text_orig=None, subject_path="places/parks",
                entities=[FactEntity(entity_id="new:Zabeel Park", role="venue")],
                op="new", target=None, valid_from=day, evidence=[rid], sensitive=None,
            )],
            links=[],
        )
        apply("karim", _job(f"j-{rid}", [rid]), _attempt(f"j-{rid}", out), db=db)
    place = next(e for e in store.list_entities("karim") if e.name == "Zabeel Park")
    assert place.status == "active"
    assert place.closeness_tier is None
    with db.connection() as conn:
        row = conn.execute(
            "SELECT provenance, closeness_tier FROM entities WHERE id = %s",
            (place.id,),
        ).fetchone()
    assert row["provenance"] == "inferred"
    assert row["closeness_tier"] is None


def test_first_person_statement_is_user_supplied(db_env):
    db, store = db_env
    store.upsert_records("karim", [_rec("mine", "I run at Zabeel on Fridays", "2026-11-01T07:00:00Z", author="Karim")])
    out = ExtractionOutput(
        entities=[OutEntity(ref="new:Karim Haddad", kind="person", aliases=["Karim"], relation_to_user="self")],
        facts=[OutFact(
            text="Karim runs at Zabeel on Fridays", text_orig=None, subject_path="health/running",
            entities=[FactEntity(entity_id="new:Karim Haddad", role="runner")],
            op="new", target=None, valid_from="2026-11-01", evidence=["mine"], sensitive=None,
        )],
        links=[],
    )
    apply("karim", _job("j-me", ["mine"]), _attempt("j-me", out), db=db)
    person = next(e for e in store.list_entities("karim") if e.name == "Karim Haddad")
    with db.connection() as conn:
        ent = conn.execute("SELECT provenance FROM entities WHERE id = %s", (person.id,)).fetchone()
        fact = conn.execute("SELECT provenance FROM facts WHERE owner = 'karim'").fetchone()
        subj = conn.execute(
            "SELECT provenance FROM subjects WHERE owner = 'karim' AND path = 'health/running'"
        ).fetchone()
    assert ent["provenance"] == "user_supplied"
    assert fact["provenance"] == "user_supplied"
    assert subj["provenance"] == "user_supplied"


def test_t1_suggestion_never_writes_tier_and_family_signal_suggests_nothing(db_env):
    db, store = db_env
    for day, rid in (("2026-10-01", "c1"), ("2026-10-03", "c2"), ("2026-10-04", "c3"), ("2026-10-05", "c4"), ("2026-10-06", "c5")):
        store.upsert_records("karim", [_rec(rid, "Nadia reviewed the API", f"{day}T09:00:00Z", author="Omar")])
        apply("karim", _job(f"j-{rid}", [rid]), _attempt(f"j-{rid}", ExtractionOutput(
            entities=[OutEntity(ref="new:Nadia Mansour", kind="person", aliases=["Nadia"], relation_to_user="colleague")],
            facts=[OutFact(
                text="Nadia reviewed the API", text_orig=None, subject_path="work/reviews",
                entities=[FactEntity(entity_id="new:Nadia Mansour", role="reviewer")],
                op="new", target=None, valid_from=day, evidence=[rid], sensitive=None,
            )],
            links=[],
        )), db=db)
    nadia = next(e for e in store.list_entities("karim") if e.name == "Nadia Mansour")
    with db.connection() as conn:
        row = conn.execute(
            "SELECT closeness_suggested, closeness_tier, closeness_suggested_evidence FROM entities WHERE id = %s",
            (nadia.id,),
        ).fetchone()
    assert row["closeness_suggested"] == "T1"
    assert row["closeness_tier"] is None
    assert row["closeness_suggested_evidence"]

    for day, rid in (("2026-11-01", "m1"), ("2026-11-02", "m2")):
        store.upsert_records("karim", [_rec(rid, "Mom visits on Thursday", f"{day}T09:00:00Z", author="Karim")])
        apply("karim", _job(f"j-{rid}", [rid]), _attempt(f"j-{rid}", ExtractionOutput(
            entities=[OutEntity(ref="new:Mariam Haddad", kind="person", aliases=["Mom"], relation_to_user="family")],
            facts=[OutFact(
                text="Mom visits on Thursday", text_orig=None, subject_path="family/visits",
                entities=[FactEntity(entity_id="new:Mariam Haddad", role="mother")],
                op="new", target=None, valid_from=day, evidence=[rid], sensitive=None,
            )],
            links=[],
        )), db=db)
    mom = next(e for e in store.list_entities("karim") if e.name == "Mariam Haddad")
    with db.connection() as conn:
        mom_row = conn.execute(
            "SELECT relation_to_user, closeness_suggested, closeness_tier FROM entities WHERE id = %s",
            (mom.id,),
        ).fetchone()
    assert mom_row["relation_to_user"] == "family"
    assert mom_row["closeness_suggested"] is None
    assert mom_row["closeness_tier"] is None


def test_late_update_of_superseded_target_stays_history(db_env):
    db, store = db_env
    store.upsert_records("karim", [
        _rec("a", "Karim lives in JLT", "2026-10-01T09:00:00Z", author="Karim"),
        _rec("b", "Karim lives in the Marina", "2026-10-10T09:00:00Z", author="Karim"),
        _rec("c", "Karim lives in Jaddaf", "2026-10-20T09:00:00Z", author="Karim"),
    ])
    first = apply("karim", _job("j-a", ["a"]), _attempt("j-a", ExtractionOutput(
        entities=[OutEntity(ref="new:Karim Haddad", kind="person", aliases=[], relation_to_user="self")],
        facts=[OutFact(
            text="Karim lives in JLT", text_orig=None, subject_path="home/residence",
            entities=[FactEntity(entity_id="new:Karim Haddad", role="resident")],
            op="new", target=None, valid_from="2026-10-01", evidence=["a"], sensitive=None,
        )],
        links=[],
    )), db=db)
    older_id = first.applied_fact_ids[0]
    second = apply("karim", _job("j-b", ["b"]), _attempt("j-b", ExtractionOutput(
        entities=[],
        facts=[OutFact(
            text="Karim lives in the Marina", text_orig=None, subject_path="home/residence",
            entities=[FactEntity(entity_id="Karim Haddad", role="resident")],
            op="update", target=older_id, valid_from="2026-10-10", evidence=["b"], sensitive=None,
        )],
        links=[],
    )), db=db)
    marina_id = second.applied_fact_ids[0]
    third = apply("karim", _job("j-c", ["c"]), _attempt("j-c", ExtractionOutput(
        entities=[],
        facts=[OutFact(
            text="Karim lives in Jaddaf", text_orig=None, subject_path="home/residence",
            entities=[FactEntity(entity_id="Karim Haddad", role="resident")],
            op="update", target=older_id, valid_from="2026-10-20", evidence=["c"], sensitive=None,
        )],
        links=[],
    )), db=db)
    with db.connection() as conn:
        older = conn.execute("SELECT status FROM facts WHERE id = %s", (older_id,)).fetchone()
        late = conn.execute("SELECT status, superseded_by FROM facts WHERE id = %s", (third.applied_fact_ids[0],)).fetchone()
        marina = conn.execute("SELECT status FROM facts WHERE id = %s", (marina_id,)).fetchone()
    assert older["status"] == "superseded"
    assert marina["status"] == "active"
    assert late["status"] == "history"
    assert late["superseded_by"] == older_id
