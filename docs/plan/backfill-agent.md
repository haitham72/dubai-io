# Backfill Agent & Goal-Loop Architecture

**Date:** 17 Nov 2026 · **Status:** Locked design (`PLAN.md` §2, SRE Supervisor Report P2-7) · **Gate:** Do not run historical backfill before AC-1 through AC-3 (`tests/test_live_hindsight_llm.py`) are green.

---

## 1. Purpose

Historical backfill ingests multi-year user exports (WhatsApp `.txt`, Gmail `.mbox` / OAuth history, Google Calendar `.ics`, Contacts `.vcf`) into the temporal memory backend and SQLite catalog without burning frontier tokens on routine classification or silently poisoning memory when extraction quality degrades.

**Core rule:** Never run an autonomous backfill loop over unproven extraction. A goal loop over unverified extraction loops faster over bad facts. Backfill execution is strictly gated on **AC-1** (live Hindsight LLM-provider fact/entity/supersession verification), **AC-2** (card lifecycle state machine), and **AC-3** (orchestrator query rewriter).

---

## 2. Agent Topology: One Accountable Lead + Bounded Delegation

- **Default topology:** **One accountable lead orchestrator** with bounded, stateless worker delegation.
  - The lead owns the backfill run plan, cursor progression, budget enforcement, `ScopeGuard` audit log, and the testable `"done"` contract for each slice.
  - Delegated workers receive a single bounded slice (e.g., one chat export window or one email thread batch) and return structured JSON matching a strict schema; workers never spawn sub-workers or mutate global state directly.
- **No standing specialist multi-agent mesh by default:** Introduce standing specialist agents only when measured throughput or accuracy on a benchmarked slice proves a single lead + bounded worker delegation insufficient.

---

## 3. Model Routing: Frontier Plans / Cheap Executes

| Role | Model Tier | Responsibility | Forbidden Actions |
| :--- | :--- | :--- | :--- |
| **Tier 1: Rules** | Deterministic Python | Known senders, receipts, unsubscribe headers, RFC/regex date & amount extraction, `content_hash` dedupe, `forget_rules` pre-check (`is_blocked`), layer-1 `sensitive.py` regex screen. | Never infers semantics or overrides a `forget_rule`. |
| **Tier 2: Local Classifier** | Local Qwen 1.5B–3B fine-tune (`~0.07s/email`) | Closed-set classification: `{category, status, sender_cluster}` and confidence score. Flags borderline items (`confidence < threshold`, target `<10%` of volume). | **Never creates tasks, never rewrites queries, never resolves contradictions, never routes workflows.** |
| **Tier 3: Temporal Backend** | Hindsight (with LLM provider verified via AC-1) | `retain` absolute-dated facts and entities; `reflect` contradictions; emit supersession links (`old_id -> new_id`). | Never deletes by age (`§R-ND` decay-with-floor applies); never exposes unconfirmed sensitive traits. |
| **Tier 4: Lead Orchestrator** | Frontier / Planner LLM | Writes the backfill slice plan, rewrites unscoped queries into `ScopedQuery` (AC-3), adjudicates multi-message contradictions, evaluates the goal-loop `"done"` contract, and triages escalated items. | Never fabricates provider statuses (Rule 1) or bypasses `ScopeGuard`. |

---

## 4. Durable SQLite Queue & Human Review (`blocked`) State

All backfill work is persisted in a durable SQLite table (`backfill_jobs`) so interrupted runs resume cleanly without re-processing completed slices or losing borderline items:

```sql
CREATE TABLE IF NOT EXISTS backfill_jobs (
    job_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    source TEXT NOT NULL,              -- 'whatsapp' | 'email' | 'google_calendar' | 'google_contacts'
    source_ref TEXT NOT NULL,          -- file/thread/slice identifier + byte/msg range
    content_hash TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued', -- 'queued' | 'running' | 'done' | 'blocked' | 'failed'
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    classifier_confidence REAL,
    blocked_reason TEXT,               -- set when state = 'blocked' (human review required)
    error_detail TEXT,                 -- set when state = 'failed'
    done_contract_json TEXT NOT NULL,  -- assertions required before state -> 'done'
    audit_json TEXT,                   -- counts, retained IDs, superseded IDs, elapsed_ms
    lease_expires_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_backfill_jobs_owner_state ON backfill_jobs(owner_id, state, created_at);
```

### State Machine
$$\texttt{queued} \longrightarrow \texttt{running} \longrightarrow \begin{cases} \texttt{done} & \text{(all done-contract assertions pass)} \\ \texttt{blocked} & \text{(human review required)} \\ \texttt{failed} & \text{(transient error after max\_attempts)} \end{cases}$$

### When a Job Transitions to `blocked` (Human Review Queue)
A slice **must** transition to `blocked` (and never auto-commit to confirmed memory) when any of the following hold:
1. **Borderline classification (`<10%` target):** The local Qwen classifier confidence falls in the uncertainty band and the cheap verifier cannot disambiguate the category/status.
2. **Ambiguous identity / alias:** A person or entity in the slice does not match `circle.json` and fails the deterministic alias distance check.
3. **High-stakes contradiction:** A new fact appears to contradict an existing `user_supplied` confirmed fact (rather than an older inferred fact).
4. **Ambiguous privacy screen:** Layer-2 `sensitive.screen()` flags a label as ambiguous between an ordinary and a sensitive reading (fail-closed per Rule 9 / AC-4).

Items in `blocked` surface in the owner's review queue (`Confirm / Edit / Not true / Forget`) and do not feed proactive Morning Brief card generators until resolved.

---

## 5. Goal Loop = Testable "Done" Contract

The lead orchestrator does not mark a backfill job `done` based on LLM self-certification. Every `backfill_jobs` row carries a machine-checked `done_contract_json` verified in code before `state = 'done'`:

1. **Completeness invariant:** `seen == retained + duplicates + blocked_by_forget_rule + sensitive_withheld + escalated_to_blocked`. Zero silent drops.
2. **Temporal anchor invariant (AC-1):** Every retained fact has an absolute ISO timestamp (`valid_at` / `ts`), never an unresolved relative phrase (`"yesterday"`, `"next week"`).
3. **Provenance & source-range invariant (Rule 2):** Every retained fact cites a valid `source_ref` message/thread range and carries `provenance` and `as_of`.
4. **Sensitive-category gate (Rule 9 / AC-4):** Zero unconfirmed rows in `health`, `religion`, `ethnicity_nationality`, `gender_sexuality`, `politics`, `third_party_private`, or `credential` have non-empty `memory` or `user_text`.
5. **Backend idle barrier:** If the swappable backend indexes asynchronously (`retain_batch`), the worker waits for `pending_operations == 0` and asserts `failed_operations == 0` before committing `state = 'done'`.

---

## 6. Operational Playbook: Multi-Agent Weekly WhatsApp Retain (`mamty-hindsight`, AC-L2–AC-L4)

When running offline multi-agent weekly extraction over large WhatsApp exports (the `G:\Haitham\lab-data\mamty-hindsight\` **prompt-level retain lab run**):

1. **Strict boundary:** All prompts (`RUN.md`, `AGENT_PROMPT*.md`), claim state (`weeks.json`, `claims.md`), and output slices (`weeks/*.json`) live outside the repository under `G:\Haitham\lab-data\mamty-hindsight\`. Worker prompts explicitly forbid reading repo docs (`CLAUDE.md`, `PLAN.md`, `docs/`) so workers never drift from extraction.
2. **Granularity & ordering:** Claim one ISO week (`Mon–Sun`) at a time in `recent → older` order; segment each week into day packets of `~40–80` messages; preserve Egyptian Arabic / Arabizi verbatim; emit an evidence-limits line for skipped calls/media.
3. **Immutability of completed slices (`P1-5`):** Once a week is marked `status = "done"` in `weeks.json`, workers must **never** overwrite that week file unless a supervisor explicitly marks it `reopen`.
4. **Four-step promotion gate before `mem_*` (`AC-L3`, `AC-L4`):**
   $$\texttt{weeks/*.json} \xrightarrow{\text{AC-L3 schema check (no list\_root)}} \texttt{circle.json alias normalize} \xrightarrow{\text{AC-L4 sensitive.py}} \texttt{"I noticed" hypothesis} \xrightarrow{\text{user confirm}} \texttt{mem\_*}$$
   - Reject any week file whose JSON root is a bare `list` (`list_root`, e.g. `2026-04-27_...`); require an object `{week_id, agent, facts[]}`.
   - Normalize bilingual/role-suffixed entity drift (`Hadil`/`هديل`, `Asr`/`Aser`/`أسر`, `mamty (user's mother)` → `mamty`) via `circle.json`.
   - Filter every fact through `sensitive.py` (`filter_statement` + `screen()`); never promote health or family facts as plain confirmed facts.
   - Run cross-week consolidation (`unrelated | repeats | changes | ends` + `observations[]`) as Phase 2 only after SRE **AC-1** passes.

