# Residence companion + memory MCP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Dubai-io a residence companion that is *user-aware* via a temporal_note-shaped memory engine and ontology, with coarse UI domain-bots, fully planned demos, and (later) civic sandbox — without shipping the founder's local vault MCP as the product.

**Architecture:** Two MCP/memory tracks stay separate. (A) **Product memory** lives in `apps/api/app/memory/` — schema, hybrid search, context pack, Me APIs, demo resident seed; ontology paths from `docs/superpowers/specs/2026-11-02-residence-ontology-tree.md` roll up to UI bots (Lifestyle / Career / Social / Household / Money / Travel). (B) **Builder MCP** is an optional shim + ontology-restructure subagent for coding agents — tools to validate paths, seed fixtures, query memory in dev — not end-user UX. Deep trees never appear as sidebar folders.

**Tech Stack:** FastAPI, existing `apps/api` store (SQLite FTS5 / Postgres pgvector), Next.js `apps/site`, Pydantic v2, optional MCP SDK for builder shim; learn/copy from `temporal_note` (engine only; never import personal data). Path note: founder copy may live under `Documents/Claude/Projects/temporal_note` or Cowork tree — use whichever is present; do not commit personal vault files.

**Specs:** `docs/superpowers/specs/2026-11-02-residence-companion-design.md`, `docs/superpowers/specs/2026-11-02-residence-ontology-tree.md`.  
**Session front door:** repo-root `PLAN.md` (this file = detailed tasks).  
Status and parking for this plan: `PLAN.md` §5. Shell craft reference: `docs/plan/unified-app-design.md`. Plan 6 schema work can be reused inside Phase C without deleting Plan 6.

## Global Constraints

- Truth rules (CLAUDE.md): no Confirmed/Booked/Paid/Filed without authoritative evidence; every number has provenance + as_of; demo/sandbox pills visible.
- Memory rule 9: You told me / I noticed; Forget works; never infer health/religion/ethnicity/nationality-as-trait/gender/sexuality/politics.
- Demos that are `{demo}` must be **fully planned** — never “what’s my gym?” / “what phone?” / “license plate first.”
- UI bots are **app-owned** and compacted; ontology is fine-grained in memory only.
- Taxi: “Let’s track your ride” → ride-share/card (Demo trip card + paste receipt) vs cash (where+when → RTA draft).
- UAE Pass / pay bills = feature demo (sandbox → draft → Waiting/Blocked), not the product spine.
- Do not modify `apps/web` without founder approval (frozen tag `mobile-pwa-baseline-2026-10-23`).
- No top-level `*.md` beyond canon; agent docs stay nested.

## Phase overview (do in order)

| Phase | Name | Outcome |
|---|---|---|
| **A** | Demo resident + 5 journey scripts | Card-by-card plans + fixture entity list (docs only → then seed JSON) |
| **B** | UI domain bots on `apps/site` | Sidebar shows Lifestyle/Career/Social/Household/Money/Travel; threads roll up |
| **C** | Product memory engine + Me | temporal_note-slim in API; context pack; demo pack load; no stupid re-ask |
| **D** | Builder MCP + ontology subagent | Dev MCP tools + subagent brief to normalize ontology / seed |
| **E** | Wire journeys 1–5 on site | Fully planned demos runnable on PC |
| **F** | Civic appendix | UAE Pass sandbox + pay-all-bills draft |
| **G** | Optional | Browser-agent screenshots; AR/RTV labelled demo |

**Not in this plan’s critical path:** Plan 2 phone frames, Swift, live government payment, full 36-tool vault MCP for users.

---

### Task A1: Demo resident one-pager

**Files:**
- Create: `docs/superpowers/specs/2026-11-02-demo-resident.md`
- Modify: none

**Interfaces:**
- Produces: Named fixture person “Sam Resident” (or founder-chosen name), area JLT, household, gym entity, school years, insurance network label, one vehicle, DEWA placeholder, one Careem-style trip fixture, sizes XL — all `demo_fixture` / `user_supplied` as appropriate.

- [ ] **Step 1:** Write the resident doc with a table: entity id, ontology path, display name, provenance, used by which of the 5 demos.
- [ ] **Step 2:** Founder skim — adjust names only; no coding.
- [ ] **Step 3:** Commit when founder asks (do not commit secrets).

---

### Task A2: Five journey card scripts

**Files:**
- Create: `docs/superpowers/specs/2026-11-02-demo-journeys.md`

**Interfaces:**
- Consumes: Demo resident entities; taxi §4.1 + no-stupid-ask rules from companion design.
- Produces: For each demo — trigger utterance, UI bot, ontology leaves, card sequence, approval points, honest terminal statuses.

Demos (fixed order):

1. School + home (KHDA) → Household  
2. Insurance clinic near me → Money (insurance admin)  
3. Mamzar day (Yes-to-all + +1h replan) → Lifestyle  
4. Lost bag — track your ride (B+A) → Travel  
5. Guests tonight (clean + food Yes-to-all) → Household  

Appendix script (not blocking E): Pay bills + UAE Pass sandbox → Money.

- [ ] **Step 1:** Write all five scripts at taxi-§4.1 depth (no plate-first; gym-class known entities).
- [ ] **Step 2:** Cross-check each card against ontology paths; fix missing leaves in ontology tree doc if needed.
- [ ] **Step 3:** Founder review gate before Phase B coding.

---

### Task B1: Replace site domain IDs with UI bots

**Files:**
- Modify: `apps/site/unified/data/domains.ts`
- Modify: `apps/site/unified/data/tasks.ts` (thread.domain type)
- Modify: group helpers + tests under `apps/site/tests/unit/domains.test.ts`
- Test: `apps/site/tests/unit/domains.test.ts`

**Interfaces:**
- Produces: `UiBotId = "lifestyle" | "career" | "social" | "household" | "money" | "travel" | "general"`
- Produces: `rollupToUiBot(ontologyPath: string) -> UiBotId` (static map from ontology roots)
- Consumes: ontology root → UI bot cheat sheet in ontology-tree spec

- [ ] **Step 1:** Write failing tests for rollup (`lifestyle/sports/gym` → lifestyle; `travel/taxi_recovery` → travel; `money/bills_utilities/dewa` → money).
- [ ] **Step 2:** Run `cd apps/site && npm test -- domains` — expect FAIL.
- [ ] **Step 3:** Implement `UiBotId`, labels, rollup map; migrate `classifyDomain` to return ui bot + optional ontology hint.
- [ ] **Step 4:** Tests PASS; sidebar grouping uses UI bots.
- [ ] **Step 5:** Commit when asked.

---

### Task B2: Compact idle bots + active threads UI

**Files:**
- Modify: `apps/site/unified/assistant/Home.tsx` (or sidebar card component in shell)
- Modify: CSS modules for compact bot rows
- Test: `apps/site/tests/e2e/threads.spec.ts` (update expectations)

**Interfaces:**
- Produces: Idle bot row (icon, label, “Waiting”); active shows thread list under bot; Needs you unread affordance.
- Constraint: Do not render ontology depth in sidebar.

- [ ] **Step 1:** e2e expectation — six bots visible; gym demo thread under Lifestyle when present.
- [ ] **Step 2:** Implement compact list; only expand bots with threads (or always show bots compacted).
- [ ] **Step 3:** e2e green on Chromium.

---

### Task C1: Memory schema (absorb Plan 6 Task 1)

**Files:**
- Create: `apps/api/app/memory/schema.py`
- Create: `supabase/migrations/20261102000100_memory.sql`
- Test: `apps/api/tests/test_memory_schema.py`

**Interfaces:**
- Produces tables (owner-scoped): `mem_events`, `mem_entities`, `mem_entity_aliases`, `mem_relationships` (with valid_from/to), `mem_event_entities`, `mem_patterns` (hypothesis|confirmed|rejected), `mem_advice`, plus `mem_ontology_paths` (path text PK, ui_bot, label) seeded from a checked-in JSON slice of the ontology tree (start with paths needed by demo resident only; full tree can load later).

- [ ] **Step 1:** Failing migration/schema test on SQLite.
- [ ] **Step 2:** Implement schema + idempotent migrate.
- [ ] **Step 3:** PASS; no founder personal data.

---

### Task C2: Hybrid search + extract/consolidate (Plan 6 Tasks 2–3 slim)

**Files:**
- Create: `apps/api/app/memory/search.py`, `ops.py`, `sensitive.py`
- Test: `apps/api/tests/test_memory_search.py`, `test_memory_ops.py`

**Interfaces:**
- `search(store, owner, query, k=10) -> list[Hit]`
- `extract` / `filter_sensitive` / `consolidate` (close valid_to on conflict)
- Deny-list tests for religion/health inferences.

- [ ] **Step 1:** Failing tests (owner isolation, JLT replaces Marina, religion → zero stores).
- [ ] **Step 2:** Implement minimal port from temporal_note semantics.
- [ ] **Step 3:** PASS.

---

### Task C3: Context pack + Me API + “what do you know?”

**Files:**
- Create: `apps/api/app/memory/api.py`
- Modify: `apps/api/app/main.py`, `apps/api/app/luna/graph.py` (inject context pack)
- Modify: `apps/site/unified/me/MeView.tsx` — edit/forget wired
- Test: `apps/api/tests/test_memory_api.py`

**Interfaces:**
- `context_pack(store, owner, query, budget_chars=2000) -> str`
- Endpoints: timeline, search, hypotheses confirm/reject, DELETE item
- Luna must prefer known gym/phone/car from pack — regression test: demo resident gym name never prompts “what gym?”

- [ ] **Step 1:** API tests + one Luna/unit test that context includes Fitness First (fixture).
- [ ] **Step 2:** Implement; wire Me Forget to DELETE.
- [ ] **Step 3:** PASS.

---

### Task C4: Demo resident seed loader

**Files:**
- Create: `apps/api/app/fixtures/demo_resident.json` (from Task A1)
- Create: `apps/api/app/memory/seed_demo_resident.py`
- Modify: API startup (SQLite preview path) to load when `DEMO_RESIDENT=1` or always in empty SQLite preview — labelled demo_fixture
- Test: `apps/api/tests/test_demo_resident_seed.py`

**Interfaces:**
- Produces: entities + relationships for gym, trip, school, insurance category, vehicle, DEWA placeholder.

- [ ] **Step 1:** Seed test asserts gym entity exists at `lifestyle/sports/gym`.
- [ ] **Step 2:** Implement loader with provenance demo_fixture.
- [ ] **Step 3:** PASS.

---

### Task D1: Builder MCP shim (dev agents only)

**Files:**
- Create: `apps/api/app/memory/mcp_server.py` (or `apps/api/mcp/memory_mcp.py`)
- Create: `docs/superpowers/plans/mcp-builder-readme.md` (how to point Cursor at it)
- Test: list_tools smoke test

**Interfaces:**
- Tools (small set, not 36): `memory_search`, `memory_context_pack`, `ontology_list_paths`, `ontology_rollup`, `demo_resident_status`, `memory_forget` (owner test id only)
- Explicitly **out of product UI**. Optional `.mcp.json` example for this repo — do not overwrite founder's personal temporal_note plugin without ask.

- [ ] **Step 1:** Tool list test.
- [ ] **Step 2:** Implement read-mostly tools over same store as C.
- [ ] **Step 3:** Document run command; PASS.

---

### Task D2: Ontology restructure subagent brief

**Files:**
- Create: `docs/superpowers/specs/2026-11-02-ontology-subagent-brief.md`

**Interfaces:**
- Produces: Instructions for a subagent to merge synonyms, emit `ontology_paths.json`, validate rollup table, flag rule-9 leaves — **docs/JSON only**, no product UI.

- [ ] **Step 1:** Write brief referencing the huge tree.
- [ ] **Step 2:** Founder approves before dispatching subagent.
- [ ] **Step 3:** Subagent output checked into `apps/api/app/fixtures/ontology_paths.json`.

---

### Task E1–E5: Implement five demos on site (one task per demo)

**Files (each):**
- Modify: `apps/site/unified/tasks/ThreadView.tsx` (or journey-specific components under `apps/site/unified/journeys/`)
- Modify: API fixtures / task templates as needed
- Test: e2e journey file per demo under `apps/site/tests/e2e/journeys/`

**Shared rules:** Cards → detail/plan → approve; Demo pills; no stupid asks; statuses honest.

| Task | Demo | Pass criterion |
|---|---|---|
| E1 | KHDA school+home | Shortlist cards → approve enquiry draft |
| E2 | Insurance network | Fixture list → matched clinics → no invented coverage |
| E3 | Mamzar | Yes-to-all → +1h → meal/parking step updates |
| E4 | Taxi recovery | Track ride → B+A or cash where/when → RTA draft; **zero** plate required |
| E5 | Guests tonight | Multi-step plan Yes-to-all; known home context |

- [ ] For each Ei: failing e2e → implement → e2e PASS → commit when asked.

Replace/remove plate-first `demo-taxi` and empty `demo-gym` stubs as part of E4 / a Lifestyle gym micro-flow under E or a small E0 if needed for “known gym renew.”

---

### Task F1: UAE Pass sandbox + pay bills (appendix)

**Files:**
- Create: adapter stub `apps/api/app/adapters/uae_pass_sandbox.py` (connect + identity claims fixture only)
- Modify: Money journey UI + approval draft for bills
- Test: `apps/api/tests/test_uae_pass_sandbox.py`

**Interfaces:**
- Connect → `Connected (sandbox)` / `Blocked` if unset
- Pay → lines stay Waiting/Blocked; never Paid without provider evidence

- [ ] **Step 1:** Tests for status honesty.
- [ ] **Step 2:** Implement stub + UI.
- [ ] **Step 3:** PASS.

---

## Relation to PLAN.md

Since 15 Nov, `PLAN.md` is the single plan and lists this plan under Parked. Overlap (e.g. memory, taxi, Services) is coordinated by the founder.

## Verification (founder PC)

```text
API :8030 (DATABASE_URL whitespace / SQLite) + DEMO resident loaded
site http://localhost:3000/
Run demos 1–5 utterances; Me “what do you know?”; Forget one fact; taxi never asks plate first
```
