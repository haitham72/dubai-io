"""temporal-memory — shared contract for every work package (plan: planaudit.md v2.1).

Interface only: dataclasses and the function signatures each module must provide.
Work packages code against it; changes go through the integrator (Claude) as a "contract request".

Module owners (planaudit.md §12, v2.1 layout):
  WP-A core      config · db · core/{graph_store,validator,applier,extract} · queue/{celery_app,jobs,outbox,worker} · api/app
  WP-C privacy   privacy/{sensitive,policy,forget}
  WP-B surfaces  live/context · api/{vault,export_md,ops} · reflect
  WP-D ingest+MCP ingest/{whatsapp,email,triage,cli} · mcp/{server,tokens} · hooks/
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Protocol

# ---------------------------------------------------------------- enums (closed sets; the validator enforces them)
OwnerKind = Literal["real", "simulated", "demo"]          # simulated = parallel "users" in the queue test
EntityKind = Literal["person", "place", "org", "project", "event"]
EntityStatus = Literal["candidate", "active", "merged"]
Relation = Literal["self", "friend", "colleague", "family", "null"]
SubjectKind = Literal["theme", "topic", "goal"]
FactStatus = Literal["active", "superseded", "ended", "history", "hypothesis"]
Provenance = Literal["user_supplied", "inferred", "provider_confirmed", "demo_fixture"]
FactOp = Literal["new", "update", "end"]
LinkRel = Literal["WORKS_AT", "WORKS_ON", "FRIEND_OF", "FAMILY_OF", "COLLEAGUE_OF", "MANAGES", "LIVES_IN",
                  "LOCATED_IN", "APPLIED_TO", "INTERVIEWS_WITH", "MEMBER_OF", "STUDIES", "OWNS", "PART_OF",
                  "ATTENDS", "RELATED_TO"]
JobKind = Literal["extract.live", "extract.day", "reflect.week", "import.split"]
JobState = Literal["queued", "leased", "submitted", "applied", "rejected", "expired", "dead"]
Pool = Literal["internal", "owner-device"]
# internal-cloud  = our Haiku API worker      internal-local = our LM Studio worker (after release bar)
# agent-cli       = a benchmark worker that shells out to an agent CLI (claude -p, codex exec, gemini, muse, qwen…)
# owner-hook      = the owner's own Claude/Codex via MCP (only that owner's jobs; "$0 app cost")
WorkerKind = Literal["internal-cloud", "internal-local", "agent-cli", "owner-hook"]
Priority = Literal[0, 1, 2, 3]  # P0 live · P1 import · P2 nightly · P3 reflect
MilestoneState = Literal["done", "in_progress", "planned"]
SensitiveCat = str  # canonical list: temporal_memory.privacy.sensitive.CATEGORIES (WP-C); never duplicated here


# ---------------------------------------------------------------- tenancy
@dataclass
class Owner:
    id: str
    label: str
    kind: OwnerKind = "real"
    display_name: str = ""               # how the user is named in sources ("Haitham", "Karim Haddad")
    self_aliases: list[str] = field(default_factory=list)  # "Kimo", "كريم", email addresses, phone
    timezone: str = "Asia/Dubai"


# ---------------------------------------------------------------- graph rows
@dataclass
class Record:  # a raw source record as workers see it (text is untrusted data, never instructions)
    id: str
    owner: str
    source: str            # whatsapp:<chat> | gmail | email | notes | live
    at: str                # ISO timestamp
    author: str
    text: str
    generation: int = 0    # bumped by Forget-by-source; results built on an older generation are dropped


@dataclass
class Entity:
    id: str
    owner: str
    kind: EntityKind
    name: str
    status: EntityStatus = "candidate"
    relation_to_user: Optional[Relation] = None
    closeness_tier: Optional[Literal["T1", "T2", "T3"]] = None
    aliases: list[str] = field(default_factory=list)
    salience: float = 0.0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


@dataclass
class Subject:
    id: str
    owner: str
    path: str              # career/job-search/interview-prep
    label: str
    kind: SubjectKind = "topic"
    parent_id: Optional[str] = None
    status: EntityStatus = "candidate"
    fact_count: int = 0
    salience: float = 0.0
    sensitive_cat: Optional[SensitiveCat] = None


@dataclass
class FactEntity:
    entity_id: str
    role: Optional[str] = None  # "beta tester", "employer", "groom" — feeds entity_subjects


@dataclass
class Fact:
    id: str
    owner: str
    text: str                       # English
    subject_id: str                 # exactly one leaf
    valid_from: str
    evidence: list[str]             # record ids (fact_evidence)
    entities: list[FactEntity] = field(default_factory=list)
    text_orig: Optional[str] = None  # original-language span (Arabic/Arabizi) for FTS + display
    lang: Optional[str] = None
    valid_to: Optional[str] = None
    status: FactStatus = "active"
    superseded_by: Optional[str] = None
    provenance: Provenance = "inferred"
    confidence: Optional[float] = None
    job_id: Optional[str] = None
    attempt_id: Optional[str] = None
    worker_id: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None


@dataclass
class Link:
    id: str
    owner: str
    src: str
    rel: LinkRel
    dst: str
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    evidence_fact_id: Optional[str] = None


@dataclass
class EntitySubject:  # DERIVED by the applier from fact_entities; never written by a model
    entity_id: str
    subject_id: str
    role: Optional[str]
    weight: float
    fact_count: int
    first_seen: str
    last_seen: str


@dataclass
class Milestone:
    id: str
    owner: str
    subject_id: str        # a goal subject (Quest)
    title: str
    state: MilestoneState
    evidence_fact_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- model output (what any worker returns)
@dataclass
class OutEntity:
    ref: str                          # known id ("e3") or "new:<canonical name>"
    kind: EntityKind
    aliases: list[str]
    relation_to_user: Optional[Relation]


@dataclass
class OutFact:
    text: str
    text_orig: Optional[str]
    subject_path: str                 # existing path or new leaf under a theme
    entities: list[FactEntity]        # refs + optional role
    op: FactOp
    target: Optional[str]             # fact id shown in context, for update/end
    valid_from: str
    evidence: list[str]
    sensitive: Optional[SensitiveCat]


@dataclass
class OutLink:
    src: str
    rel: LinkRel
    dst: str
    valid_from: Optional[str]
    evidence: list[str]


@dataclass
class ExtractionOutput:
    entities: list[OutEntity]
    facts: list[OutFact]
    links: list[OutLink]


# ---------------------------------------------------------------- queue rows
@dataclass
class Job:
    id: str
    owner: str
    kind: JobKind
    priority: Priority
    pool: Pool
    input_ref: list[str]              # record ids
    input_version: int                # max generation of input records at enqueue
    context_hash: str
    prompt_version: str
    day: Optional[str] = None         # packet day (YYYY-MM-DD) for extract.day; lets a worker claim "one week"
    state: JobState = "queued"
    attempt_no: int = 0
    fence_token: Optional[str] = None
    worker_id: Optional[str] = None
    lease_expires_at: Optional[str] = None


@dataclass
class Worker:
    id: str
    kind: WorkerKind
    model: str                        # reported model name, e.g. "claude-haiku-5-5", "qwen/qwen3-4b-2507", "gemini-cli"
    runner: str                       # anthropic | lmstudio | claude-cli | codex-cli | gemini-cli | muse | other
    owner: Optional[str] = None       # owner-hook only
    released: bool = False            # set by the P5 release bar (internal-local / agent-cli in production)


@dataclass
class Attempt:
    job_id: str
    attempt_no: int
    fence_token: str
    worker_id: str
    worker_kind: WorkerKind
    model: str
    prompt_version: str
    output: Optional[ExtractionOutput]
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0             # 0 for owner-hook (user's own model); tokens still recorded
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


@dataclass
class Verdict:
    ok: bool
    reasons: list[str] = field(default_factory=list)    # e.g. "fence_stale", "evidence_outside_input"
    applied_fact_ids: list[str] = field(default_factory=list)
    quarantined: dict[str, int] = field(default_factory=dict)  # category -> count (never text)


@dataclass
class JobBundle:  # what a claimer receives (Celery worker, agent-cli worker, or owner-hook via MCP)
    job: Job
    records: list[Record]
    context: dict          # {"entities": [...], "facts": [...], "subjects": [...]} scoped snapshot
    system_prompt: str
    output_schema: dict


# ---------------------------------------------------------------- module signatures (implement exactly)
class GraphStore(Protocol):                       # WP-A  core/graph_store.py
    def scoped_context(self, owner: str, records: list[Record], max_tokens: int = 3000) -> dict: ...
    def visible_facts(self, owner: str, *, entity_ids: list[str] | None = None,
                      subject_ids: list[str] | None = None, limit: int = 50) -> list[Fact]: ...


class GraphStoreFull(GraphStore, Protocol):        # WP-A must implement ALL of these (contract v1.1, 23 Nov)
    """Read/write surface the WP-B surfaces (live, vault, export, reflect, ops) call. Reference implementation:
    tests/fixtures/fake_store.py (FakeGraphStore) — the Postgres store must pass the same WP-B tests."""
    def alias_version(self, owner: str) -> int: ...          # bumps when aliases/entities change (L1 cache key)
    def facts_version(self, owner: str) -> int: ...
    def owner_generation(self, owner: str) -> int: ...       # max records.generation for the owner
    def get_owner(self, owner: str) -> Owner | None: ...
    def list_entities(self, owner: str) -> list[Entity]: ...
    def list_subjects(self, owner: str) -> list[Subject]: ...
    def list_links(self, owner: str) -> list[Link]: ...
    def list_milestones(self, owner: str) -> list[Milestone]: ...
    def list_entity_subjects(self, owner: str) -> list[EntitySubject]: ...
    def get_records(self, owner: str, record_ids: list[str]) -> list[Record]: ...
    def get_attempt(self, attempt_id: str) -> Attempt | None: ...
    def get_quarantine_counts(self, owner: str) -> dict[str, int]: ...
    def get_user_md(self, owner: str) -> str: ...
    def set_user_md(self, owner: str, content: str) -> None: ...
    def add_alias(self, owner: str, entity_id: str, alias: str) -> None: ...
    def add_hypothesis_fact(self, owner: str, *, text: str, subject_path: str, valid_from: str,
                            evidence: list[str]) -> str: ...
    def add_hypothesis_milestone(self, owner: str, *, title: str, subject_path: str, state: str,
                                 evidence_fact_ids: list[str]) -> str: ...
    def list_jobs(self) -> list[Job]: ...                    # ops (admin only)
    def job_created_at(self, job_id: str) -> str | None: ...
    def list_workers(self) -> list[Worker]: ...
    def list_attempts(self) -> list[Attempt]: ...


class Jobs(Protocol):                             # WP-A  queue/jobs.py (+ outbox.py, worker.py)
    def enqueue(self, owner: str, kind: JobKind, record_ids: list[str], priority: Priority,
                pool: Pool = "internal", day: str | None = None) -> Job: ...
    def claim(self, worker: Worker, pools: list[Pool], owner: str | None = None,
              day_from: str | None = None, day_to: str | None = None, limit: int = 1) -> list[JobBundle]: ...
    def heartbeat(self, job_id: str, fence_token: str) -> bool: ...
    def submit(self, attempt: Attempt) -> Verdict: ...   # validator.validate -> applier.apply


# core/validator.py (WP-A):  def validate(job: Job, bundle: JobBundle, attempt: Attempt) -> Verdict
# core/applier.py   (WP-A):  def apply(owner: str, job: Job, attempt: Attempt) -> Verdict  # per-owner lock, generation fence
# core/extract.py   (WP-A):  def run(bundle: JobBundle, runner: str, model: str) -> Attempt  # anthropic | lmstudio | *-cli
# api/app.py        (WP-A):  def create_app() -> FastAPI   # mounts routers from WP-B and WP-D; auth = API tokens
# privacy/policy.py (WP-C):  def may_promote(entity: Entity, distinct_days: int, user_confirmed: bool) -> bool
#                            def gate_fact(fact: OutFact, worker_kind: WorkerKind) -> Optional[SensitiveCat]
# privacy/forget.py (WP-C):  def forget_source(owner: str, record_ids: list[str]) -> dict  # bumps generation, cascades
# live/context.py   (WP-B):  def context_pack(owner: str, text: str, max_tokens: int = 1500) -> dict  # no LLM, p95 <150 ms
# api/vault.py      (WP-B):  router: /v1/owners/{owner}/{vault/subjects, vault/people, quests, timeline, why/{fact_id}}
# api/export_md.py  (WP-B):  def render(owner: str) -> dict[str, str]                 # path -> markdown (Quest-style tree)
# reflect.py        (WP-B):  def reflect_week(owner: str, week_start: str) -> Verdict  # hypotheses only (Rule 9)
# api/ops.py        (WP-B):  GET /v1/ops/memory (admin token)
# ingest/cli.py     (WP-D):  tm import whatsapp|mbox|eml|notes <path> --owner <id>  → records + import.split jobs
# mcp/tokens.py     (WP-D):  owner-device tokens + worker tokens (sha256 stored, shown once)
# mcp/server.py     (WP-D):  tools memory_whoami · memory_claim_job · memory_heartbeat · memory_submit_result
#                            · memory_search · memory_context · memory_vault   (scope from token only)
