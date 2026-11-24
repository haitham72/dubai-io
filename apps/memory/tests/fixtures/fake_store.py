"""In-memory GraphStore + WP-B surface store fake seeded from karim_gold_slice.json."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterator

from temporal_memory.db.db import fold_text

from temporal_memory.live.context import invalidate_alias_cache
from temporal_memory.models import (
    Attempt,
    Candidate,
    Entity,
    EntitySubject,
    Fact,
    FactEntity,
    Job,
    Link,
    Milestone,
    Owner,
    Record,
    Subject,
    Worker,
)

FIXTURE_PATH = Path(__file__).parent / "karim_gold_slice.json"


class FakeGraphStore:
    """In-memory implementation of GraphStore and WP-B query/ops/reflect methods."""

    def __init__(self) -> None:
        self.owners: dict[str, Owner] = {}
        self.entities: dict[str, list[Entity]] = defaultdict(list)
        self.subjects: dict[str, list[Subject]] = defaultdict(list)
        self.records: dict[str, dict[str, Record]] = defaultdict(dict)
        self.facts: dict[str, list[Fact]] = defaultdict(list)
        self.links: dict[str, list[Link]] = defaultdict(list)
        self.milestones: dict[str, list[Milestone]] = defaultdict(list)
        self.quarantine: dict[str, dict[str, int]] = defaultdict(dict)
        self.user_mds: dict[str, str] = {}
        self.generations: dict[str, int] = defaultdict(int)
        self.forgotten_record_ids: dict[str, set[str]] = defaultdict(set)
        self.forgotten_fact_ids: dict[str, set[str]] = defaultdict(set)
        self.content_hashes: dict[str, dict[str, str]] = defaultdict(dict)
        self.forget_rule_values: dict[str, set[str]] = defaultdict(set)
        self._alias_ver: dict[str, int] = defaultdict(int)
        self._facts_ver: dict[str, int] = defaultdict(int)
        self.jobs: list[Job] = []
        self.job_created: dict[str, str] = {}
        self.workers: list[Worker] = []
        self.attempts: dict[str, Attempt] = {}

    @classmethod
    def from_karim_slice(cls, *, owner_override: str | None = None, owner_kind: str = "real") -> FakeGraphStore:
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        st = cls()
        ow = data["owner"]
        oid = owner_override or ow["id"]
        st.owners[oid] = Owner(
            id=oid,
            label=ow["label"],
            kind=owner_kind,  # type: ignore[arg-type]
            display_name=ow["display_name"],
            self_aliases=list(ow["self_aliases"]),
        )
        for e in data["entities"]:
            st.entities[oid].append(Entity(owner=oid, **e))
        for s in data["subjects"]:
            st.subjects[oid].append(Subject(owner=oid, **s))
        for r in data["records"]:
            st.records[oid][r["id"]] = Record(owner=oid, **r)
        for f in data["facts"]:
            f_copy = dict(f)
            f_copy["entities"] = [FactEntity(**fe) for fe in f_copy.get("entities", [])]
            if owner_kind == "demo":
                f_copy["provenance"] = "demo_fixture"
            st.facts[oid].append(Fact(owner=oid, **f_copy))
        for ln in data["links"]:
            st.links[oid].append(Link(owner=oid, **ln))
        for ms in data["milestones"]:
            st.milestones[oid].append(Milestone(owner=oid, **ms))
        st.quarantine[oid] = dict(data.get("quarantine", {}))

        now_iso = datetime.now(timezone.utc).isoformat()
        st.jobs = [
            Job(id="j1", owner=oid, kind="extract.day", priority=1, pool="internal", input_ref=["n001"], input_version=0, context_hash="c1", prompt_version="extract@3", day="2026-10-20", state="applied"),
            Job(id="j2", owner=oid, kind="extract.day", priority=1, pool="owner-device", input_ref=["g081"], input_version=0, context_hash="c2", prompt_version="extract@3", day="2026-11-01", state="queued"),
            Job(id="j-live", owner=oid, kind="extract.live", priority=0, pool="internal", input_ref=["n011"], input_version=0, context_hash="c3", prompt_version="extract@3", day="2026-11-19", state="leased"),
        ]
        st.job_created = {"j1": now_iso, "j2": "2026-11-23T08:00:00+00:00", "j-live": "2026-11-23T11:00:00+00:00"}
        st.workers = [
            Worker(id="w-haiku", kind="internal-cloud", model="claude-haiku-5-5", runner="anthropic", released=True),
            Worker(id="w-owner", kind="owner-hook", model="claude-code-hook", runner="claude-cli", owner=oid, released=True),
        ]
        st.attempts = {
            "att-haiku-1": Attempt(job_id="j1", attempt_no=1, fence_token="f1", worker_id="w-haiku", worker_kind="internal-cloud", model="claude-haiku-5-5", prompt_version="extract@3", output=None, tokens_in=4000, tokens_out=1200, cost_usd=0.01, started_at="2026-10-20T10:00:00+00:00"),
            "att-hook-1": Attempt(job_id="j2", attempt_no=1, fence_token="f2", worker_id="w-owner", worker_kind="owner-hook", model="claude-code-hook", prompt_version="extract@3", output=None, tokens_in=1_000_000, tokens_out=200_000, cost_usd=0.0, started_at="2026-11-01T10:00:00+00:00"),
        }
        # Attach verdict metadata dynamically for ops test
        st.attempts["att-haiku-1"].verdict = "applied"  # type: ignore[attr-defined]
        st.attempts["att-hook-1"].verdict = "applied"  # type: ignore[attr-defined]
        return st

    # ---- GraphStore protocol ----
    def visible_facts(
        self,
        owner: str,
        *,
        entity_ids: list[str] | None = None,
        subject_ids: list[str] | None = None,
        limit: int = 50,
    ) -> list[Fact]:
        forgotten_recs = self.forgotten_record_ids.get(owner, set())
        forgotten_fids = self.forgotten_fact_ids.get(owner, set())
        out: list[Fact] = []
        for f in self.facts.get(owner, []):
            if f.id in forgotten_fids:
                continue
            if f.evidence and all(rid in forgotten_recs for rid in f.evidence):
                continue
            if entity_ids and not any(fe.entity_id in entity_ids for fe in f.entities):
                continue
            if subject_ids and f.subject_id not in subject_ids:
                continue
            out.append(f)
            if len(out) >= limit:
                break
        return out

    def scoped_context(self, owner: str, records: list[Record], max_tokens: int = 3000) -> dict:
        return {"entities": self.list_entities(owner), "facts": self.visible_facts(owner), "subjects": self.list_subjects(owner)}

    # ---- Extensions used by WP-B ----
    def alias_version(self, owner: str) -> int:
        return self._alias_ver[owner]

    def facts_version(self, owner: str) -> int:
        return self._facts_ver[owner]

    def search_candidates(
        self, owner: str, query: str, *, entity_ids: list[str] | None = None,
        subject_ids: list[str] | None = None, date_from: str | None = None,
        date_to: str | None = None, source_prefix: str | None = None, limit: int = 50,
    ) -> list[Candidate]:
        query_tokens = set(fold_text(query).split())
        entity_filter = set(entity_ids or [])
        subject_filter = set(subject_ids or [])
        candidates: list[Candidate] = []
        for fact in self.iter_visible_facts(owner, date_from=date_from, date_to=date_to):
            if source_prefix is not None:
                records = self.get_records(owner, fact.evidence)
                if not records or len(records) != len(fact.evidence):
                    continue
                if not all(record.source.startswith(source_prefix) for record in records):
                    continue
            fact_tokens = set(fold_text(f"{fact.text} {fact.text_orig or ''}").split())
            lexical_hits = len(query_tokens & fact_tokens)
            if lexical_hits:
                candidates.append(Candidate(fact.id, float(lexical_hits), "fts"))
            elif any(entity.entity_id in entity_filter for entity in fact.entities):
                candidates.append(Candidate(fact.id, 1.0, "entity"))
            elif fact.subject_id in subject_filter:
                candidates.append(Candidate(fact.id, 1.0, "subject"))
            elif date_from is not None or date_to is not None:
                candidates.append(Candidate(fact.id, 1.0, "date"))
        return sorted(candidates, key=lambda candidate: (-candidate.score, candidate.fact_id))[:max(0, limit)]

    def get_facts(self, owner: str, fact_ids: list[str]) -> list[Fact]:
        visible = {fact.id: fact for fact in self._all_visible_facts(owner)}
        return [visible[fact_id] for fact_id in dict.fromkeys(fact_ids) if fact_id in visible]

    def fact_counts_by_subject(self, owner: str) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for fact in self._all_visible_facts(owner):
            counts[fact.subject_id] += 1
        return dict(counts)

    def iter_visible_facts(
        self, owner: str, *, date_from: str | None = None, date_to: str | None = None,
        after: tuple[str, str] | None = None, page_size: int = 500,
    ) -> Iterator[Fact]:
        if page_size < 1:
            raise ValueError("page_size must be positive")
        facts = sorted(self._all_visible_facts(owner), key=lambda fact: (fact.valid_from, fact.id), reverse=True)
        for fact in facts:
            day = fact.valid_from[:10]
            if date_from is not None and day < date_from:
                continue
            if date_to is not None and day > date_to:
                continue
            if after is None or (fact.valid_from, fact.id) < after:
                yield fact

    def _all_visible_facts(self, owner: str) -> Iterator[Fact]:
        for fact in self.visible_facts(owner, limit=len(self.facts.get(owner, []))):
            if fact.status != "history":
                yield fact

    def bump_privacy_revision(self, owner: str) -> int:
        entry = self.owners[owner]
        entry.privacy_revision += 1
        return entry.privacy_revision

    def owner_generation(self, owner: str) -> int:
        return self.generations[owner]

    def get_owner(self, owner: str) -> Owner | None:
        return self.owners.get(owner)

    def list_entities(self, owner: str) -> list[Entity]:
        return list(self.entities.get(owner, []))

    def list_subjects(self, owner: str) -> list[Subject]:
        return list(self.subjects.get(owner, []))

    def list_links(self, owner: str) -> list[Link]:
        return list(self.links.get(owner, []))

    def list_milestones(self, owner: str) -> list[Milestone]:
        return list(self.milestones.get(owner, []))

    def list_entity_subjects(self, owner: str) -> list[EntitySubject]:
        acc: dict[tuple[str, str, str | None], dict[str, Any]] = {}
        for f in self.visible_facts(owner, limit=10_000):
            if f.status in ("history", "hypothesis"):
                continue
            for fe in f.entities:
                key = (fe.entity_id, f.subject_id, fe.role)
                row = acc.setdefault(key, {"count": 0, "first": f.valid_from, "last": f.valid_from})
                row["count"] += 1
                if f.valid_from < row["first"]:
                    row["first"] = f.valid_from
                if f.valid_from > row["last"]:
                    row["last"] = f.valid_from
        return [
            EntitySubject(
                entity_id=eid, subject_id=sid, role=role, weight=float(v["count"]),
                fact_count=v["count"], first_seen=v["first"], last_seen=v["last"],
            )
            for (eid, sid, role), v in acc.items()
        ]

    def get_records(self, owner: str, record_ids: list[str]) -> list[Record]:
        forgotten = self.forgotten_record_ids.get(owner, set())
        recs = self.records.get(owner, {})
        return [recs[rid] for rid in record_ids if rid in recs and rid not in forgotten]

    def get_attempt(self, attempt_id: str) -> Attempt | None:
        return self.attempts.get(attempt_id)

    def get_quarantine_counts(self, owner: str) -> dict[str, int]:
        return dict(self.quarantine.get(owner, {}))

    def get_user_md(self, owner: str) -> str:
        return self.user_mds.get(owner, "")

    def set_user_md(self, owner: str, content: str) -> None:
        self.user_mds[owner] = content

    def add_alias(self, owner: str, entity_id: str, alias: str) -> None:
        for e in self.entities[owner]:
            if e.id == entity_id and alias not in e.aliases:
                e.aliases.append(alias)
        self._alias_ver[owner] += 1
        invalidate_alias_cache(owner)

    def add_hypothesis_fact(
        self, owner: str, *, text: str, subject_path: str, valid_from: str, evidence: list[str]
    ) -> str:
        fid = f"hyp-{len(self.facts[owner]) + 1}"
        subj_id = next((s.id for s in self.subjects[owner] if s.path == subject_path), "th_career")
        self.facts[owner].append(
            Fact(
                id=fid, owner=owner, text=text, subject_id=subj_id, valid_from=valid_from,
                evidence=evidence, status="hypothesis", provenance="inferred",
            )
        )
        self._facts_ver[owner] += 1
        return fid

    def add_hypothesis_milestone(
        self, owner: str, *, title: str, subject_path: str, state: str, evidence_fact_ids: list[str]
    ) -> str:
        mid = f"ms-hyp-{len(self.milestones[owner]) + 1}"
        subj = next((s for s in self.subjects[owner] if s.path == subject_path), None)
        if subj is None:
            subj = Subject(
                id=f"goal-{len(self.subjects[owner]) + 1}", owner=owner, path=subject_path,
                label=title, kind="goal", status="candidate",
            )
            self.subjects[owner].append(subj)
        self.milestones[owner].append(
            Milestone(id=mid, owner=owner, subject_id=subj.id, title=title, state=state, evidence_fact_ids=evidence_fact_ids)  # type: ignore[arg-type]
        )
        return mid

    def forget_source(self, owner: str, record_ids: list[str]) -> dict:
        forgotten = set(record_ids)
        self.generations[owner] += 1
        self.forgotten_record_ids[owner].update(forgotten)
        for rid in forgotten:
            self.forget_rule_values[owner].add(rid)
            hashed = self.content_hashes.get(owner, {}).get(rid)
            if hashed:
                self.forget_rule_values[owner].add(hashed)
        erased: list[str] = []
        trimmed: list[str] = []
        for fact in self.facts.get(owner, []):
            if not fact.evidence or not (set(fact.evidence) & forgotten):
                continue
            if set(fact.evidence) <= forgotten:
                erased.append(fact.id)
                fact.evidence = []
                self.forgotten_fact_ids[owner].add(fact.id)
            else:
                fact.evidence = [rid for rid in fact.evidence if rid not in forgotten]
                trimmed.append(fact.id)
        requeued = 0
        enqueued = 0
        requeueable = {"queued", "expired", "submitted", "rejected"}
        for job in list(self.jobs):
            if job.owner != owner or job.kind not in ("extract.day", "extract.live"):
                continue
            if not (set(job.input_ref) & forgotten):
                continue
            survivors = [rid for rid in job.input_ref if rid not in forgotten]
            if job.state in requeueable:
                if survivors:
                    job.input_ref = survivors
                    job.state = "queued"
                    job.input_version = self.generations[owner]
                    job.fence_token = None
                    requeued += 1
                else:
                    job.state = "dead"
                    job.fence_token = None
            elif job.state == "applied" and survivors:
                self.jobs.append(Job(
                    id=f"re-{job.id}-{self.generations[owner]}",
                    owner=owner,
                    kind="extract.day",
                    priority=1,
                    pool=job.pool,
                    input_ref=survivors,
                    input_version=self.generations[owner],
                    context_hash=job.context_hash,
                    prompt_version=job.prompt_version,
                    day=job.day,
                    state="queued",
                ))
                enqueued += 1
        self._facts_ver[owner] += 1
        invalidate_alias_cache(owner)
        return {
            "owner": owner,
            "generation": self.generations[owner],
            "records": len(forgotten),
            "records_forgotten": len(forgotten),
            "facts_erased": len(erased),
            "facts_trimmed": len(trimmed),
            "entity_subjects_recomputed": len(self.list_entity_subjects(owner)),
            "jobs_requeued": requeued,
            "jobs_enqueued": enqueued,
        }

    def check_fence(self, owner: str, claimed_generation: int) -> str:
        if claimed_generation < self.generations[owner]:
            return "fence_stale"
        return "ok"

    def forget_fact(self, owner: str, fact_id: str) -> None:
        self.generations[owner] += 1
        self.forgotten_fact_ids[owner].add(fact_id)
        self._facts_ver[owner] += 1
        invalidate_alias_cache(owner)

    # Ops methods
    def list_jobs(self) -> list[Job]:
        return list(self.jobs)

    def job_created_at(self, job_id: str) -> str | None:
        return self.job_created.get(job_id)

    def list_workers(self) -> list[Worker]:
        return list(self.workers)

    def list_attempts(self) -> list[Attempt]:
        return list(self.attempts.values())
