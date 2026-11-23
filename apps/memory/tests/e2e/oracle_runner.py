"""Zero-cost runner for the Docker E2E workers, backed by the synthetic ledger."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from functools import cache

from temporal_memory.models import Attempt, ExtractionOutput, FactEntity, JobBundle, OutEntity, OutFact

if __package__:
    from .gold import gold_dir, ledger_record_id, load_gold, subject_path
else:
    from gold import gold_dir, ledger_record_id, load_gold, subject_path


MODEL = "gold-oracle"
RUNNER = "oracle"
ROLES = {"WORKS_ON": "contributor", "TESTS": "tester", "ENROLLED_IN": "student"}


def _ref(name: str) -> str:
    return f"new:{name}"


@cache
def _ledger_indexes(_directory: Path) -> tuple[dict, dict, dict, dict]:
    ledger = load_gold()
    entities = {
        person["id"]: OutEntity(
            ref=_ref(person["canonical"]),
            kind="person",
            aliases=person["aliases"],
            relation_to_user={"manager": "colleague", "recruiter": None, "neighbour": None,
                              "other": None}.get(person["relation"], person["relation"]),
        )
        for person in ledger["people"]
    }
    for kind, items in [("org", ledger["orgs"]), ("place", ledger["places"])]:
        for item in items:
            entities[item["id"]] = OutEntity(_ref(item["name"]), kind, [], None)
    subjects = {subject["id"]: subject for subject in ledger["subjects"]}
    roles = {
        (edge["src"], edge["dst"]): ROLES[edge["rel"]]
        for edge in ledger["edges"]
        if edge["dst"] in subjects
    }
    by_anchor = defaultdict(list)
    for fact in ledger["facts"]:
        if fact["sensitive"] is None:
            by_anchor[fact["evidence"][0]].append(fact)
    return entities, subjects, roles, by_anchor


def project(bundle: JobBundle) -> ExtractionOutput:
    """Emit each public fact once, in its first evidence record's packet."""
    entities, subjects, roles, by_anchor = _ledger_indexes(gold_dir())
    record_ids = {ledger_record_id(record.id): record.id for record in bundle.records}
    # The output contract permits one subject leaf and evidence from this packet.
    # Snapshot-dependent edits are covered by the engine's temporal tests.
    found = sorted(
        (fact for record_id in record_ids for fact in by_anchor.get(record_id, ())),
        key=lambda fact: fact["id"],
    )
    output_entities = {}
    output_facts = []
    for fact in found:
        subject_id = next(iter(fact["subject_ids"]), None)
        mentioned = []
        for entity_id in [*fact["person_ids"], *fact["org_ids"], *fact["place_ids"]]:
            entity = entities[entity_id]
            output_entities[entity_id] = entity
            mentioned.append(FactEntity(entity.ref, roles.get((entity_id, subject_id))))
        output_facts.append(
            OutFact(
                text=fact["text"],
                text_orig=None,
                subject_path=subject_path(subjects.get(subject_id)),
                entities=mentioned,
                op="new",
                target=None,
                valid_from=fact["valid_from"],
                evidence=[record_ids[ref] for ref in fact["evidence"] if ref in record_ids],
                sensitive=None,
            )
        )
    # The gold ledger's other graph edges have no cited records of their own.
    return ExtractionOutput(list(output_entities.values()), output_facts, [])


def run(bundle: JobBundle, runner: str, model: str) -> Attempt:
    if runner != RUNNER or model != MODEL:
        raise ValueError(f"Expected the E2E oracle, got {runner!r} / {model!r}")
    started_at = datetime.now(timezone.utc).isoformat()
    output = project(bundle)
    return Attempt(
        job_id=bundle.job.id,
        attempt_no=bundle.job.attempt_no,
        fence_token=bundle.job.fence_token or "",
        worker_id=bundle.job.worker_id or MODEL,
        worker_kind="agent-cli",
        model=model,
        prompt_version=bundle.job.prompt_version,
        output=output,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc).isoformat(),
    )


def install() -> None:
    """Install only in Docker test workers; an unexpected runner fails closed."""
    from temporal_memory.core import extract
    from temporal_memory.privacy import sensitive

    def deterministic_screen(labels: list[str]) -> dict[str, str]:
        return {label: (sensitive.categories_hit(label) or ["none"])[0] for label in labels}

    extract.run = run
    sensitive._lmstudio_classifier = deterministic_screen
