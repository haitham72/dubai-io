# Task: harden temporal_note memory engine — targeted enhancements, no redesign

You are working in the Dubai-io repo, branch `memory` (worktree `G:\Haitham\VsCode\contest-memory`).
Read first, in this order:
1. `MEMORY_ARCHITECTURE.md` (the current spec — trust its ✅/🔧/📋 labels and its measured numbers)
2. `memory-bakeoff/TN_UPGRADE_PLAN.md` (plan v1 + gates)
3. `acceptance/BASELINE.md` and `acceptance/results/…` (measured scores)
4. `docs/plan/Memory/memory.md` on `main` — treat as an OLD doc, but two of its ideas are being
   reintroduced below (TreeSetter AST, Pointer-Not-Payload); do not otherwise follow it.

Do NOT redesign the architecture. Do NOT remove tables, do NOT rewrite the write path, do NOT
add a new queue, do NOT touch the privacy gate's categories. The scope is exactly the work
packages below, in this order. Each one is a separate branch `mem-wp<X>-<slug>`, with a test
and a one-line entry in `reports/STATUS.md`.

## Hard constraints
- Postgres 17 + pgvector, RabbitMQ + Celery, FastAPI — unchanged.
- Python 3.12+, `apps/memory/`, package `temporal_memory`. Match existing style.
- `pytest -q` must stay green. Add tests for every change.
- Synthetic persona "Karim" only. No real data in the repo, ever.
- No runtime DDL. Migrations only via `db/migrations/000N_*.sql` (U0a/U0c pattern).
- Rule 9 stays enforced: provenance + `as_of` on every read surface; "You told me" only for
  `user_supplied`; family/health/faith never inferred. Do not weaken the sensitive gate.
- Any change to the read path must keep p95 < 150 ms at 20k facts over HTTP, measured during
  a concurrent backfill too.

---

## WP-A (do first, ~1 day) — make the validator per-fact, not per-job
Problem: `core/extract.py` validator is all-or-nothing per job; one bad fact discards a whole
day (U3 diagnosis cause 1).
Change: validate each fact/link independently. Reject only the failing item, keep the rest,
record the rejection reason on `job_attempts` (new nullable column via migration) so the U3
diagnosis can count rejection causes. Quarantined items still go to `quarantine` as today.
Test: a 10-fact payload with 1 invalid evidence span yields 9 approved facts, 1 rejection row,
job status `partial` (new status value; update the enum + STATUS doc).
Acceptance: S2 recall on the gold month moves off 66.7 % with no precision regression.

## WP-B (same branch as WP-A if small) — show the model the target fact
Problem: the model isn't shown the fact it must `update`/`end` (U3 diagnosis cause 2).
Change: in `extract@4`, for every candidate op `update` or `end`, the prompt must include the
target fact's current `text`, `valid_from`, `status`, and `superseded_by` (if any). Bump the
prompt version; the idempotency key already includes it.
Test: gold-month fixture with 8 supersedes / 5 ends / 4 late updates; assert ≥ 6 / 4 / 3 correct.
Acceptance: S2 changes bucket moves off 1/8 · 0/5 · 0/4.

## WP-C (U1c, split it) — SQL-candidate retrieval, cap the context pack
Problem: context pack loads up to 10,000 facts per call (413 ms p95 at 20k; facts past 10k
invisible); 6 Vault endpoints load all facts.
Change, in this order, each its own commit:
  C1. `POST /owners/{o}/context` and MCP `memory_context` fetch SQL candidates only:
      FTS GIN over `facts.tsv` + entity/alias match (EN/AR/Arabizi) + 1-hop link + subject +
      date window → RRF. Hard cap at candidates before ranking. Never `SELECT * FROM facts`.
  C2. Same for `GET /search` (ranked candidates in SQL) and MCP `memory_search`
      (remove the 1k hydration limit).
  C3. Same for the 6 Vault endpoints that currently load all facts.
  C4. Render stored provenance (`facts.provenance`) everywhere instead of deriving from
      `status` (the 4 places called out in §6). This is the S5 gate.
  C5. `/vault/graph?view=subjects|people` DTO: versioned nodes/edges/counts, 7 clusters,
      Rule-9 gating server-side, `+N more`, T1 from confirmed tier, suggestions as
      "I noticed". Plus `POST /vault/people/{id}/tier`.
Test: 20k-fact fixture; assert p95 < 150 ms during backfill; assert old facts (>10k) are
retrievable; assert a quarantined fact never appears in any surface.
Acceptance: S1 retrieval gate passes; S5 Rule 9 surfaces pass.

## WP-D (pull U4 forward, ~1 day) — local multilingual embeddings
Problem: "no vectors used yet"; U4 is deferred until after U1c+U3 — backwards, you need it to
know whether U1c+U3 are enough. Pure BM25 will underperform on Arabic and paraphrase.
Change: local multilingual sentence embedder (e.g. `paraphrase-multilingual-MiniLM-L12-v2`),
stored in `facts.embedding` (pgvector). Index over `text` + `text_orig`. Used as an additional
RRF arm in C1/C2, not as the primary retriever. No cloud calls.
Test: gold-month retrieval; report recall delta vs C-only.
Acceptance: measurable recall lift on Arabic and paraphrase buckets; if no lift, leave the
embedding arm disabled by flag and say so in `reports/STATUS.md`.

## WP-E (~1 day) — person-card read view (replaces Honcho's job)
Problem: the PDF said "add Honcho back only if person-level conclusions are missing"; the new
doc has no "what should the agent understand about this person" surface.
Change: read-only `GET /people/{id}/card` and MCP `memory_person_card`. Derive from existing
`facts` + `links` + `entity_subjects` + `closeness_suggested`: current state, open loops,
recent signals, evidence links per bullet. Every bullet cites visible evidence. No new
extraction, no new LLM call on the read path. Rule-9 gated; family/health/faith never stated
as inference — mark "I noticed" with Confirm/Edit/Not true/Forget.
Test: Karim fixture; assert every bullet has ≥ 1 evidence id; assert a quarantined category
is absent.

## WP-F (~0.5 day) — reintroduce TreeSetter AST (zero-token pre-LLM extraction)
Source idea from old `memory.md` §6.1 — reintroduce narrowly:
- Deterministic regex/grammar pass over raw records BEFORE the LLM call, for: devices
  (`brand/model/condition/date`), purchases (`merchant/item/amount/currency`), dates, order
  IDs, amounts in AED.
- Emit typed slots copied verbatim into `ExtractionOutput`; the LLM is told these are
  pre-filled and must not change them.
- Invariant: numbers, dates, order IDs, model names are copied verbatim, never LLM-rewritten.
Test: fixtures for iPhone receipt and Amazon.ae order; assert verbatim extraction and reduced
LLM output tokens (report the delta in the PR).

## WP-G (doc-only, ~1 hour) — reintroduce Pointer-Not-Payload rule
Source idea from old `memory.md` §12. Add a short section to `MEMORY_ARCHITECTURE.md`:
resident files (`SOUL.md`, `PROFILE_RUNTIME.md`, system prompts) carry identity, rules and
POINTERS — never raw facts, lists or historical logs. Exceeding the resident character ceiling
is a build failure. Any fact found in a resident file is moved to the bank and replaced by a
pointer. No code change.

## WP-H (doc + CI, ~0.5 day) — thin `MemoryBackend` seam and a kill criterion
Change: put retrieval behind one interface `MemoryBackend.search(...)` and
`MemoryBackend.context(...)`, with `TemporalNoteBackend` as the only implementation today.
No behaviour change. This is an exit hatch, not a redesign.
Then add to `MEMORY_ARCHITECTURE.md` §10, as a locked decision:
  "Kill criterion: if S1 and S2 do not pass after U1c (WP-C) + U3 + embeddings (WP-D), fall
   back to Hindsight as the retrieval backend only (writes / Forget / privacy stay on
   temporal_note)."
CI: a `pytest -q -k backend_contract` test that runs the same assertions against whichever
backend is configured.

## WP-I (harness only, ~0.5 day) — restore the bake-off signal
Problem: "No competitor comparisons" removes the only signal that says whether 0.36 recall is
good-for-custom or bad-vs-off-the-shelf.
Change: run the SAME gold month through Hindsight, Mem0 and Graphiti using the `MemoryBackend`
seam from WP-H, and record recall / p95 / cost in `acceptance/BASELINE.md`. This is a
measurement, not a product decision. Do NOT swap backends based on it; the kill criterion in
WP-H decides that.

---

## Sequencing (do not parallelize the chain)
WP-A → WP-B → WP-C (C1→C5) → WP-D → WP-E → WP-F → WP-G → WP-H → WP-I.
U2 (instant triples, topic counter, per-session catch-up) and U5 (why/story) stay 📋 and are
NOT in scope for this task.

## Definition of done
- Every WP is a separate branch `mem-wp<X>-<slug>` with a test and a `reports/STATUS.md` line.
- `pytest -q` green, 364+ passing.
- Acceptance harness (`TM_RUN_E2E=1`) rerun after the chain; S1–S5 results pasted into the PR.
- `MEMORY_ARCHITECTURE.md` updated: labels flipped from 📋/🔧 to ✅ only for what is merged
  and verified on Postgres; measured numbers replaced with the new ones.
- Do not weaken Rule 9, the sensitive gate, Forget, or provenance. If a WP cannot be done
  without weakening any of these, stop and write a one-paragraph note in `reports/STATUS.md`
  instead of implementing it.