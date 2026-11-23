"""Exercise the full synthetic month through the Docker queue and read APIs."""
from __future__ import annotations

from collections import Counter, defaultdict
from io import BytesIO
from zipfile import ZipFile

import pytest

from temporal_memory.core.graph_store import PostgresGraphStore

from .gold import import_gold, ledger_record_id, load_gold, subject_path
from .oracle_runner import MODEL, ROLES


pytestmark = pytest.mark.e2e

# Known disagreements between the synthetic labels and the canonical privacy gate.
# Exact IDs keep an unrelated missing fact from fitting within a count tolerance.
CANONICAL_QUARANTINES = {
    "f017": "family_third_party",
    "f039": "family_third_party",
    "f049": "ethnicity_nationality",
    "f061": "ethnicity_nationality",
    "f084": "religion",
}
TRIAGED_PUBLIC_FACTS = {"f045", "f109"}


def test_gold_month_through_queue(stack):
    ledger = load_gold()
    persona = next(person for person in ledger["people"] if person["relation"] == "self")
    owner = stack.owner(persona["canonical"], self_aliases=persona["aliases"])
    store = PostgresGraphStore(stack.db)
    records = import_gold(stack, owner)
    # The five source files contain 1,172 records before deterministic triage.
    assert len(records) == 1010
    record_ids_by_day = defaultdict(set)
    days_by_record_id = {}
    for record in records:
        day = record.at[:10]
        record_ids_by_day[day].add(record.id)
        days_by_record_id[ledger_record_id(record.id)] = day
    assert len(record_ids_by_day) == 31
    assert [min(record_ids_by_day), max(record_ids_by_day)] == ledger["persona"]["window"]

    parent = stack.jobs.enqueue(owner, "import.split", [record.id for record in records], 1)
    stack.wait_job(parent.id, "applied")
    days = stack.rows(
        """
        SELECT id, day, priority, input_ref
        FROM jobs WHERE owner = %s AND kind = 'extract.day' ORDER BY day
        """,
        (owner,),
    )
    assert [str(row["day"]) for row in days] == sorted(record_ids_by_day)
    for row in days:
        assert row["priority"] == 1
        assert set(row["input_ref"]) == record_ids_by_day[str(row["day"])]
        stack.wait_job(row["id"], "applied")

    public = {fact["text"]: fact for fact in ledger["facts"] if fact["sensitive"] is None}
    assert len(public) == 102
    assert {
        fact["id"] for fact in public.values() if fact["evidence"][0] not in days_by_record_id
    } == TRIAGED_PUBLIC_FACTS
    excluded = TRIAGED_PUBLIC_FACTS | CANONICAL_QUARANTINES.keys()
    expected = {text: fact for text, fact in public.items() if fact["id"] not in excluded}
    subjects = {subject["id"]: subject for subject in ledger["subjects"]}
    subject_paths = {subject.id: subject.path for subject in store.list_subjects(owner)}
    facts = store.visible_facts(owner, limit=1000)
    assert Counter(fact.text for fact in facts) == Counter(expected.keys())
    for fact in facts:
        gold_fact = expected[fact.text]
        first_subject = next(iter(gold_fact["subject_ids"]), None)
        assert subject_paths[fact.subject_id] == subject_path(subjects.get(first_subject))
        assert fact.valid_from == gold_fact["valid_from"]
        # f008 has a citation on an adjacent day.
        anchor_day = days_by_record_id[gold_fact["evidence"][0]]
        assert {ledger_record_id(rid) for rid in fact.evidence} == {
            rid for rid in gold_fact["evidence"] if days_by_record_id.get(rid) == anchor_day
        }
    assert store.get_quarantine_counts(owner) == dict(Counter(CANONICAL_QUARANTINES.values()))

    response = stack.api.get(f"/v1/owners/{owner}/vault/subjects").raise_for_status().json()
    assert response["total_facts"] == len(expected)
    assert response["themes"]
    response = stack.api.get(f"/v1/owners/{owner}/vault/people").raise_for_status().json()
    expected_people = {person["id"]: person["canonical"] for person in ledger["people"]}
    assert len(expected_people) == 25
    assert Counter(person["name"] for person in response["people"]) == Counter(expected_people.values())
    assert {
        (person["name"], person["status"]) for person in response["people"] if person["name"] != persona["canonical"]
    } == {(name, "candidate") for name in expected_people.values() if name != persona["canonical"]}
    expected_roles = {
        (expected_people[edge["src"]], subject_path(subjects[edge["dst"]]), ROLES[edge["rel"]])
        for edge in ledger["edges"] if edge["dst"] in subjects
    }
    assert len(expected_roles) == 9
    assert {
        (person["name"], subject_paths[subject["subject_id"]], subject["role"])
        for person in response["people"] for subject in person["subjects"] if subject["role"]
    } == expected_roles

    response = stack.api.get(f"/v1/owners/{owner}/export/md.zip").raise_for_status()
    assert response.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.testzip() is None
        index = archive.read("memory/MEMORIES.md").decode("utf-8")
        assert "## People" in index
        assert "raseef-side-project-app" in index
        assert "memory/people/omar-farouk.md" in archive.namelist()
        exported = "\n".join(archive.read(path).decode("utf-8") for path in archive.namelist())
        assert all(fact["text"] not in exported for fact in ledger["facts"] if fact["sensitive"])

    attempts = stack.rows(
        """
        SELECT a.job_id, a.model, a.verdict, a.cost_usd
        FROM job_attempts a JOIN jobs j ON j.id = a.job_id
        WHERE j.owner = %s AND j.kind = 'extract.day'
        """,
        (owner,),
    )
    assert Counter(row["job_id"] for row in attempts) == Counter(row["id"] for row in days)
    assert {(row["model"], row["verdict"], row["cost_usd"]) for row in attempts} == {
        (MODEL, "applied", 0.0),
    }
    ops = stack.api.get("/v1/ops/memory").raise_for_status().json()
    assert ops["attempts_by_verdict_per_model"][MODEL]["applied"] >= len(days)
