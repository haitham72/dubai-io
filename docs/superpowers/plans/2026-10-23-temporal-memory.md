# Temporal Memory (Plan 6 of 8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Dubai-io a long-term, time-aware memory modelled on the founder's temporal_note — events, entities with validity windows, hybrid search, memory ops and due advice — feeding the assistant's context, the Me timeline, "I noticed", and Keeping-track recommendations.

**Architecture:** Port temporal_note's *engine and schema* (not its data, not its markdown source of truth) into `apps/api/app/memory/`. Postgres (`dubaiio` schema, pgvector) when `DATABASE_URL` is set; SQLite + FTS5 fallback otherwise (today's dev setup — `DATABASE_URL` is unset). The engine is exposed to the product through FastAPI endpoints and to coding agents through an optional MCP shim.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, existing `db` store, pgvector (Supabase), existing embedding model `sentence-transformers/all-MiniLM-L6-v2` (lazy, ML extras), `FAST_MODEL` for extraction.

**Spec:** `docs/plan/unified-app-design.md` §3. Source to learn/copy from (founder permission, 23 Oct): `~/VsCode/Claude---Cowork/temporal_note` — `schema_v1.sql` + migrations v2–v9, `mcp_server/transport.py` (36 tools), `bm25_index.py`, memory ops `memory_extract/consolidate/conflicts/salience/context`, `rrf_search`.

## Global Constraints

- Rule 9 (root `CLAUDE.md`): every stored item is visible and editable in Me; stated facts = `user_supplied` ("You told me"); inferred = hypotheses with `provenance: inferred`, confidence, evidence, valid time, Confirm / Edit / Not true / Forget.
- **Never infer** health, religion, ethnicity, nationality-as-trait, gender, sexuality, politics — extraction drops these categories before storage (deny-list + classifier check), with tests.
- Unconfirmed hypotheses only re-rank, with a visible "Because…" chip; never pre-fill, never on approval cards, never trigger proactive messages, never set status.
- Proactive advice fires only from the scheduler/outbox (rule 8), deduped, consented, quiet hours respected.
- Owner-scoped everywhere; forgetting deletes the row and its derived embeddings/links.
- Founder's personal temporal_note data is never imported.

## Review Focus

- "Forget" on a fact must also remove it from search results and the context pack immediately. (Task 4)
- A conflicting new fact ("moved to JLT") closes the old one's `valid_to` instead of keeping both as current. (Task 3)
- Extraction from text mentioning religion/health stores nothing for those categories. (Task 3)
- Another owner's memory never appears in search or context. (Task 2)
- SQLite fallback and Postgres return the same ordering for the same fixture. (Task 2)

---

### Task 1: Schema + migrations

**Files:** Create `apps/api/app/memory/schema.py`, `supabase/migrations/20261024000100_memory.sql`; Test `apps/api/tests/test_memory_schema.py`
**Interfaces — Produces tables (owner-scoped):** `mem_events(id, owner, at, kind, text, source, provenance, confidence, embedding?, content_hash)`, `mem_entities(id, owner, kind, name)`, `mem_entity_aliases`, `mem_relationships(owner, a, b, kind, valid_from, valid_to)`, `mem_event_entities`, `mem_patterns(id, owner, statement, confidence, evidence_json, status: hypothesis|confirmed|rejected)`, `mem_advice(id, owner, text, due_at, stale_after, status)`. RLS enabled on Postgres.
- [ ] Test: migrate on SQLite creates all tables; re-run is idempotent; Postgres path covered by `TEST_DATABASE_URL` run.
- [ ] FAIL → implement (adapt temporal_note `schema_v1.sql` + natural-key constraints v6) → PASS → commit.

### Task 2: Hybrid search

**Files:** Create `apps/api/app/memory/search.py`; Test `apps/api/tests/test_memory_search.py`
**Interfaces — Produces:** `search(store, owner, query: str, k: int = 10, kinds: set[str] | None = None) -> list[Hit]` where `Hit = {id, kind, text, at, score, why}`; BM25/FTS5 + vector (when embeddings available) fused with RRF (k=60, as temporal_note `rrf_search`); keyword-only when ML extras are absent (honest `why: "keyword"`).
- [ ] Tests: owner isolation; keyword-only fallback; same fixture → same top-3 ordering on SQLite and Postgres.
- [ ] FAIL → implement → PASS → commit.

### Task 3: Memory ops (extract, consolidate, conflicts, salience)

**Files:** Create `apps/api/app/memory/ops.py`, `apps/api/app/memory/sensitive.py`; Test `apps/api/tests/test_memory_ops.py`
**Interfaces — Produces:** `extract(text, source) -> list[Candidate]` (uses `FAST_MODEL`, JSON-only, text slots); `filter_sensitive(cands) -> list[Candidate]`; `consolidate(store, owner, cands) -> Result` (dedupe by content_hash/entity; on contradiction close previous `valid_to`); `salience(store, owner, now) -> list[(id, score)]`.
- [ ] Tests: "I moved to JLT" after "I live in Marina" → Marina `valid_to` set, JLT current; religion/health mentions → zero stored items; duplicate text → one event.
- [ ] FAIL → implement (copy temporal_note memory_* semantics) → PASS → commit.

### Task 4: Context pack + API + forget

**Files:** Create `apps/api/app/memory/api.py`; Modify `apps/api/app/main.py` (include router), `apps/api/app/luna/graph.py` (add context pack to the prompt); Test `apps/api/tests/test_memory_api.py`
**Interfaces — Produces:** `context_pack(store, owner, query, budget_chars=2000) -> str` (confirmed facts first, then salient events, hypotheses labelled as unconfirmed); endpoints `GET /api/memory/timeline?from&to`, `GET /api/memory/search?q`, `GET /api/memory/hypotheses`, `PUT /api/memory/hypotheses/{id}` (confirm|reject|edit), `DELETE /api/memory/items/{id}`.
- [ ] Tests: forget removes the item from timeline, search and context pack; hypotheses never appear in the context pack as facts; endpoints owner-scoped.
- [ ] FAIL → implement → PASS → commit.

### Task 5: Feeds — task write-ups, chats, facts

**Files:** Modify `apps/api/app/tasks.py` (on COMPLETED/CANCELLED write a task write-up event), `apps/api/app/main.py` session-fact edits → `mem_events` (`user_supplied`); Test `apps/api/tests/test_memory_feeds.py`
- [ ] Tests: completing a task stores one write-up event (what, sources, outcome); editing a "You told me" fact stores a `user_supplied` event and updates the entity; replays don't duplicate.
- [ ] FAIL → implement → PASS → commit.

### Task 6: Advice due → Keeping track (deterministic)

**Files:** Create `apps/api/app/memory/advice.py`; Modify the scheduler/outbox entry point used by `proactive.py`; Test `apps/api/tests/test_memory_advice.py`
**Interfaces:** `due_advice(store, owner, now) -> list[Advice]` (as temporal_note `pg_advice_due` / `pg_advice_stale_by_event`); outbox messages with `dedupe_key = "advice:" + id`, consent + quiet hours enforced.
- [ ] Tests: due advice produces exactly one outbox message; quiet hours defer; no consent → nothing.
- [ ] FAIL → implement → PASS → commit.

### Task 7 (dev tooling, optional): temporal_note MCP on this Mac

- [ ] Point the temporal-note plugin's `.mcp.json` at `mcp_server/run.sh` instead of `run.ps1` (founder OK needed — it edits their plugin config); verify `tools/list` returns 36 tools; add a `dubaiio` project entry so coding agents can query this repo's code graph.

---

UI for this plan (Me timeline, "I noticed" cards, "What Dubai-io can see") lands in the web app in Plan 5/6 UI tasks using these endpoints.
