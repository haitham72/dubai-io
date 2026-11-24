"""Integration tests for transactional applier against PostgreSQL 17 (WP-A)."""
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
        Owner(
            id="karim",
            label="Karim Haddad",
            kind="demo",
            display_name="Karim Haddad",
            self_aliases=["Karim", "Kimo"],
        )
    )
    yield db, store
    drop_test_schema(db, schema)


def _job(job_id: str, input_ref: list[str], input_version: int = 0) -> Job:
    return Job(
        id=job_id,
        owner="karim",
        kind="extract.day",
        priority=1,
        pool="internal",
        input_ref=input_ref,
        input_version=input_version,
        context_hash="ctx",
        prompt_version="extract@3",
        state="leased",
        attempt_no=1,
        fence_token="tok-1",
        worker_id="w-1",
    )


def _attempt(job_id: str, output: ExtractionOutput) -> Attempt:
    return Attempt(
        job_id=job_id,
        attempt_no=1,
        fence_token="tok-1",
        worker_id="w-1",
        worker_kind="internal-cloud",
        model="claude-haiku-4-5-20251001",
        prompt_version="extract@3",
        output=output,
    )


def test_gold_day_apply_with_role_and_entity_subjects(db_env):
    db, store = db_env
    store.upsert_records(
        "karim",
        [
            Record(
                id="wa-1",
                owner="karim",
                source="whatsapp:work",
                at="2026-10-05T09:00:00Z",
                author="Karim",
                text="Met Nadia Mansour at Falcon Tech for backend interview.",
                generation=0,
            )
        ],
    )
    out = ExtractionOutput(
        entities=[
            OutEntity(ref="new:Karim Haddad", kind="person", aliases=["Kimo"], relation_to_user="self"),
            OutEntity(ref="new:Nadia Mansour", kind="person", aliases=["نادية"], relation_to_user="colleague"),
            OutEntity(ref="new:Falcon Tech", kind="org", aliases=["Falcon"], relation_to_user=None),
        ],
        facts=[
            OutFact(
                text="Nadia Mansour interviewed Karim at Falcon Tech",
                text_orig=None,
                subject_path="career/job-search/interview-prep",
                entities=[
                    FactEntity(entity_id="new:Karim Haddad", role="candidate"),
                    FactEntity(entity_id="new:Nadia Mansour", role="interviewer"),
                    FactEntity(entity_id="new:Falcon Tech", role="prospective_employer"),
                ],
                op="new",
                target=None,
                valid_from="2026-10-05",
                evidence=["wa-1"],
                sensitive=None,
            )
        ],
        links=[
            OutLink(src="new:Nadia Mansour", rel="WORKS_AT", dst="new:Falcon Tech", valid_from="2026-10-05", evidence=["wa-1"])
        ],
    )

    verdict = apply("karim", _job("j-1", ["wa-1"]), _attempt("j-1", out), db=db)
    assert verdict.ok is True
    assert len(verdict.applied_fact_ids) == 1

    facts = store.visible_facts("karim")
    assert len(facts) == 1
    assert facts[0].text == "Nadia Mansour interviewed Karim at Falcon Tech"
    assert facts[0].evidence == ["wa-1"]
    assert {fe.role for fe in facts[0].entities} == {"candidate", "interviewer", "prospective_employer"}

    entities = {e.name: e for e in store.list_entities("karim")}
    # Policy rule (WP-C): 1-day self stays candidate until seen across >= 2 distinct days;
    # third-party people always stay candidate without explicit user confirmation.
    assert entities["Karim Haddad"].status == "candidate"
    assert entities["Nadia Mansour"].status == "candidate"
    assert entities["Falcon Tech"].status == "candidate"

    # Seeing self + org on a 2nd distinct day promotes self & org via policy.may_promote, never third-party Nadia
    store.upsert_records(
        "karim",
        [Record(id="wa-2", owner="karim", source="whatsapp:work", at="2026-10-06T09:00:00Z", author="Karim", text="Follow-up at Falcon Tech.", generation=0)],
    )
    out_day2 = ExtractionOutput(
        entities=[],
        facts=[
            OutFact(
                text="Karim followed up with Falcon Tech",
                text_orig=None,
                subject_path="career/job-search/interview-prep",
                entities=[
                    FactEntity(entity_id="Karim Haddad", role="candidate"),
                    FactEntity(entity_id="Falcon Tech", role="prospective_employer"),
                    FactEntity(entity_id="Nadia Mansour", role="interviewer"),
                ],
                op="new",
                target=None,
                valid_from="2026-10-06",
                evidence=["wa-2"],
                sensitive=None,
            )
        ],
        links=[],
    )
    v2 = apply("karim", _job("j-2", ["wa-2"]), _attempt("j-2", out_day2), db=db)
    assert v2.ok is True
    entities_d2 = {e.name: e for e in store.list_entities("karim")}
    assert entities_d2["Karim Haddad"].status == "active"
    assert entities_d2["Falcon Tech"].status == "active"
    assert entities_d2["Nadia Mansour"].status == "candidate"

    es = store.list_entity_subjects("karim")
    by_role = {row.role: row for row in es}
    assert by_role["interviewer"].fact_count == 2
    assert by_role["interviewer"].weight == 2.0
    assert by_role["interviewer"].first_seen == "2026-10-05"
    assert by_role["interviewer"].last_seen == "2026-10-06"

    subjects = {s.path: s for s in store.list_subjects("karim")}
    assert set(subjects) == {"career", "career/job-search", "career/job-search/interview-prep"}
    assert subjects["career/job-search/interview-prep"].fact_count == 2

    links = store.list_links("karim")
    assert len(links) == 1 and links[0].rel == "WORKS_AT"

    with db.connection() as conn:
        fv = conn.execute("SELECT facts_version FROM owners WHERE id = 'karim'").fetchone()["facts_version"]
    assert fv == 2


def test_late_evidence_never_overwrites_newer(db_env):
    db, store = db_env
    store.upsert_records(
        "karim",
        [
            Record(id="wa-10", owner="karim", source="whatsapp", at="2026-10-10T10:00:00Z", author="Karim", text="Moved to Dubai Marina", generation=0),
            Record(id="wa-02", owner="karim", source="whatsapp", at="2026-10-02T10:00:00Z", author="Karim", text="Staying in JLT", generation=0),
        ],
    )
    out1 = ExtractionOutput(
        entities=[OutEntity(ref="new:Karim Haddad", kind="person", aliases=[], relation_to_user="self")],
        facts=[
            OutFact(
                text="Karim lives in Dubai Marina",
                text_orig=None,
                subject_path="home/residence",
                entities=[FactEntity(entity_id="new:Karim Haddad", role="resident")],
                op="new",
                target=None,
                valid_from="2026-10-10",
                evidence=["wa-10"],
                sensitive=None,
            )
        ],
        links=[],
    )
    v1 = apply("karim", _job("j-newer", ["wa-10"]), _attempt("j-newer", out1), db=db)
    target_id = v1.applied_fact_ids[0]

    # Now older evidence arrives attempting op="update" against target_id
    out2 = ExtractionOutput(
        entities=[],
        facts=[
            OutFact(
                text="Karim lives in JLT",
                text_orig=None,
                subject_path="home/residence",
                entities=[FactEntity(entity_id="Karim Haddad", role="resident")],
                op="update",
                target=target_id,
                valid_from="2026-10-02",
                evidence=["wa-02"],
                sensitive=None,
            )
        ],
        links=[],
    )
    v2 = apply("karim", _job("j-older", ["wa-02"]), _attempt("j-older", out2), db=db)
    assert v2.ok is True
    older_id = v2.applied_fact_ids[0]

    # Target remains active in visible_facts; late fact is history and hidden from visible_facts
    vis = store.visible_facts("karim")
    assert [f.id for f in vis] == [target_id]
    assert vis[0].status == "active"

    with db.connection() as conn:
        row = conn.execute("SELECT status, superseded_by, valid_to FROM facts WHERE id = %s", (older_id,)).fetchone()
    assert row["status"] == "history"
    assert row["superseded_by"] == target_id
    assert row["valid_to"] == "2026-10-10"


def test_update_and_end_transition_target(db_env):
    db, store = db_env
    store.upsert_records(
        "karim",
        [
            Record(id="r1", owner="karim", source="notes", at="2026-10-01T09:00:00Z", author="Karim", text="Interviewing at Acme"),
            Record(id="r2", owner="karim", source="notes", at="2026-10-15T09:00:00Z", author="Karim", text="Withdrew from Acme"),
        ],
    )
    v1 = apply(
        "karim",
        _job("j1", ["r1"]),
        _attempt(
            "j1",
            ExtractionOutput(
                entities=[OutEntity(ref="new:Acme", kind="org", aliases=[], relation_to_user=None)],
                facts=[
                    OutFact(
                        text="Karim is interviewing with Acme",
                        text_orig=None,
                        subject_path="career/job-search",
                        entities=[FactEntity(entity_id="new:Acme", role="target_company")],
                        op="new",
                        target=None,
                        valid_from="2026-10-01",
                        evidence=["r1"],
                        sensitive=None,
                    )
                ],
                links=[],
            ),
        ),
        db=db,
    )
    f1 = v1.applied_fact_ids[0]

    v2 = apply(
        "karim",
        _job("j2", ["r2"]),
        _attempt(
            "j2",
            ExtractionOutput(
                entities=[],
                facts=[
                    OutFact(
                        text="Karim withdrew from Acme interview",
                        text_orig=None,
                        subject_path="career/job-search",
                        entities=[FactEntity(entity_id="Acme", role="target_company")],
                        op="end",
                        target=f1,
                        valid_from="2026-10-15",
                        evidence=["r2"],
                        sensitive=None,
                    )
                ],
                links=[],
            ),
        ),
        db=db,
    )
    assert v2.ok is True
    f2 = v2.applied_fact_ids[0]
    by_id = {f.id: f for f in store.visible_facts("karim")}
    assert by_id[f1].status == "ended"
    assert by_id[f1].valid_to == "2026-10-15"
    assert by_id[f1].superseded_by == f2
    assert by_id[f2].status == "active"


def test_fence_stale_after_generation_bump_and_erasure(db_env):
    db, store = db_env
    store.upsert_records(
        "karim",
        [Record(id="wa-5", owner="karim", source="whatsapp", at="2026-10-05T09:00:00Z", author="Karim", text="Hello", generation=0)],
    )
    # Simulate Forget-by-source bumping record generation after job was enqueued at input_version=0
    with db.transaction() as conn:
        conn.execute("UPDATE records SET generation = generation + 1 WHERE owner = 'karim' AND id = 'wa-5'")

    out = ExtractionOutput(
        entities=[],
        facts=[
            OutFact(
                text="Karim said hello",
                text_orig=None,
                subject_path="social/chat",
                entities=[],
                op="new",
                target=None,
                valid_from="2026-10-05",
                evidence=["wa-5"],
                sensitive=None,
            )
        ],
        links=[],
    )
    verdict = apply("karim", _job("j-stale", ["wa-5"], input_version=0), _attempt("j-stale", out), db=db)
    assert verdict.ok is False
    assert verdict.reasons == ["fence_stale"]
    assert store.visible_facts("karim") == []


def test_sensitive_quarantine_and_forget_rules(db_env):
    db, store = db_env
    store.upsert_records(
        "karim",
        [
            Record(id="wa-s1", owner="karim", source="whatsapp", at="2026-10-06T09:00:00Z", author="Karim", text="Blood test at clinic"),
            Record(id="wa-s2", owner="karim", source="whatsapp", at="2026-10-06T10:00:00Z", author="Karim", text="OTP is 998811"),
            Record(id="wa-s3", owner="karim", source="whatsapp", at="2026-10-06T11:00:00Z", author="Karim", text="Forgotten secret item"),
        ],
    )
    with db.transaction() as conn:
        conn.execute("INSERT INTO forget_rules (owner, kind, value) VALUES ('karim', 'text', 'forgotten secret')")

    out = ExtractionOutput(
        entities=[],
        facts=[
            OutFact(
                text="Karim had a blood lab test at the clinic",
                text_orig=None,
                subject_path="personal/wellness",
                entities=[],
                op="new",
                target=None,
                valid_from="2026-10-06",
                evidence=["wa-s1"],
                sensitive=None,  # caught by Layer-1 gate too
            ),
            OutFact(
                text="Karim OTP passcode is 998811",
                text_orig=None,
                subject_path="finance/auth",
                entities=[],
                op="new",
                target=None,
                valid_from="2026-10-06",
                evidence=["wa-s2"],
                sensitive=None,
            ),
            OutFact(
                text="Forgotten secret item noted by Karim",
                text_orig=None,
                subject_path="notes/misc",
                entities=[],
                op="new",
                target=None,
                valid_from="2026-10-06",
                evidence=["wa-s3"],
                sensitive=None,
            ),
        ],
        links=[],
    )
    verdict = apply("karim", _job("j-priv", ["wa-s1", "wa-s2", "wa-s3"]), _attempt("j-priv", out), db=db)
    assert verdict.ok is True
    assert verdict.applied_fact_ids == []
    assert verdict.quarantined == {"family_third_party": 1}
    assert store.get_quarantine_counts("karim") == {"family_third_party": 1}
    assert store.visible_facts("karim") == []

    # Verify sensitive text is never stored in facts or quarantine
    with db.connection() as conn:
        fact_count = conn.execute("SELECT COUNT(*)::int AS c FROM facts WHERE owner = 'karim'").fetchone()["c"]
        q_rows = conn.execute("SELECT category, record_ids FROM quarantine WHERE owner = 'karim'").fetchall()
    assert fact_count == 0
    assert len(q_rows) == 1
    assert q_rows[0]["category"] == "family_third_party"
    assert q_rows[0]["record_ids"] == ["wa-s1"]


def test_stated_fact_is_user_supplied_and_inferred_fact_is_not(db_env):
    db, store = db_env
    store.upsert_records(
        "karim",
        [Record(
            id="ugh", owner="karim", source="whatsapp:me", at="2026-11-02T09:00:00Z",
            author="Karim", text="ugh work again",
        )],
    )
    out = ExtractionOutput(
        entities=[],
        facts=[
            OutFact(
                text="Karim said ugh work again", text_orig=None, subject_path="career/mood",
                entities=[], op="new", target=None, valid_from="2026-11-02",
                evidence=["ugh"], sensitive=None, stated=True,
            ),
            OutFact(
                text="Karim wants a different project", text_orig=None, subject_path="career/mood",
                entities=[], op="new", target=None, valid_from="2026-11-02",
                evidence=["ugh"], sensitive=None, stated=False,
            ),
        ],
        links=[],
    )
    apply("karim", _job("j-stated", ["ugh"]), _attempt("j-stated", out), db=db)
    with db.connection() as conn:
        rows = conn.execute("SELECT text, provenance FROM facts WHERE owner = 'karim'").fetchall()
    by_text = {row["text"]: row["provenance"] for row in rows}
    assert by_text["Karim said ugh work again"] == "user_supplied"
    assert by_text["Karim wants a different project"] == "inferred"


def test_restaurant_loved_it_stores_place_type_and_preference(db_env):
    db, store = db_env
    store.upsert_records(
        "karim",
        [Record(
            id="meal", owner="karim", source="whatsapp:me", at="2026-11-03T19:00:00Z",
            author="Karim", text="Loved dinner at Alserkal Cafe.",
        )],
    )
    out = ExtractionOutput(
        entities=[OutEntity(
            ref="new:Alserkal Cafe", kind="place", aliases=["Alserkal Cafe"],
            relation_to_user=None, place_type="restaurant",
        )],
        facts=[
            OutFact(
                text="Karim ate at Alserkal Cafe", text_orig=None, subject_path="events/restaurants",
                entities=[FactEntity(entity_id="new:Alserkal Cafe", role=None)],
                op="new", target=None, valid_from="2026-11-03", evidence=["meal"], sensitive=None,
                stated=True,
            ),
            OutFact(
                text="Karim loved Alserkal Cafe", text_orig=None, subject_path="events/restaurants",
                entities=[FactEntity(entity_id="new:Alserkal Cafe", role=None)],
                op="new", target=None, valid_from="2026-11-03", evidence=["meal"], sensitive=None,
                stated=True,
            ),
        ],
        links=[],
    )
    apply("karim", _job("j-place", ["meal"]), _attempt("j-place", out), db=db)
    place = next(entity for entity in store.list_entities("karim") if entity.name == "Alserkal Cafe")
    with db.connection() as conn:
        row = conn.execute("SELECT place_type FROM entities WHERE id = %s", (place.id,)).fetchone()
        texts = {r["text"] for r in conn.execute("SELECT text FROM facts WHERE owner = 'karim'")}
    assert row["place_type"] == "restaurant"
    assert "Karim loved Alserkal Cafe" in texts


def test_phone_query_finds_iphone_fact_by_subject_alias(db_env):
    db, store = db_env
    store.upsert_records(
        "karim",
        [Record(
            id="handset", owner="karim", source="notes", at="2026-11-04T08:00:00Z",
            author="Karim", text="Picked up the iPhone 13 Pro Max today.",
        )],
    )
    out = ExtractionOutput(
        entities=[],
        facts=[OutFact(
            text="Karim bought an iPhone 13 Pro Max", text_orig=None,
            subject_path="home-money/devices/phone", entities=[],
            op="new", target=None, valid_from="2026-11-04", evidence=["handset"],
            sensitive=None, stated=True,
        )],
        links=[],
    )
    verdict = apply("karim", _job("j-phone", ["handset"]), _attempt("j-phone", out), db=db)
    fact_id = verdict.applied_fact_ids[0]
    for query in ("phone", "mobile"):
        hits = store.search_candidates("karim", query)
        matched = [hit for hit in hits if hit.fact_id == fact_id]
        assert matched and matched[0].channel == "subject"
        assert "phone" not in "Karim bought an iPhone 13 Pro Max".lower().split()
