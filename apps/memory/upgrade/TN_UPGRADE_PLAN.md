# temporal_note upgrade plan — power the Knowledge Graph Vault

**Status:** `approved for build` — **v1, 24 Nov 2026** (Claude). Merges the independent audits by Codex, Cursor, Gemini and DeepSeek (`tn_upgrade_audit_{codex,cursor,gemini,deepseek}.md`; DeepSeek's mostly confirms the other three). Muse's audit is pending and can still amend it. v0 is superseded. **Founder decisions recorded 24 Nov (§7).**
**Engine:** `apps/memory/` (package `temporal_memory`), on `main` (24 Nov; originally branch `memory` @ `e05371f`). Paths below are relative to `apps/memory/src/temporal_memory/`.
**Target screen:** `design/20-11-2026/Dubai-io Knowledge Graph Vault.jpg` (founder-supplied, 20 Nov), with two views:
- **Subjects:** clusters + counts.
- **People & Places:** relation + **T1 ring**, places, projects, relation count.

The mobile screens exist on `ios` (`apps/mobile/src/features/vault/*`) and read `/vault/subjects`, `/vault/people` and `/timeline`.
**Out of scope (founder):** comparisons with other engines. temporal_note is judged only on R1–R6.

## 1. Requirements

| ID | Requirement |
|---|---|
| R1 | **Low cost** |
| R2 | **Fast in conversation:** obvious fields extracted instantly, e.g. `person → buys → iPhone` |
| R3 | **Backfill:** who · where · why · contradict · update · retrieve · tell a story |
| R4 | **Graph map:** Subjects and People & Places, as in the design |
| R5 | Root `CLAUDE.md` rules 1, 2 and 9: no false status; provenance + `as_of`; inferences are "I noticed" with Confirm / Edit / Not true / Forget; two-visit qualification; health, family and faith are **never inferred** |
| R6 | **Places and topics (founder, 24 Nov):** if the user talks about a restaurant or keeps asking about a topic, the agent remembers it and can retrieve it later |

## 2. Current state (v0 table, corrected by the audits)

| Need | Verified state | Evidence |
|---|---|---|
| R1 cost | About **$0.0044 per extraction day** (31 calls, $0.1368) **from the weekbench adapter, not `apps/memory`'s own worker**. Cost on the shipped worker is unmeasured. The bridge's default is **one `extract.live` job per posted batch**, not per message; nothing in the engine turns a chat turn into that call. | `runs/20261123-140525_tn_update-day_month/calls.jsonl`; `api/bridge.py:40,150-158` |
| R2 | No instant extraction. No action fields (buys / wants / likes / visits). `LinkRel` has `OWNS` and `ATTENDS` only. | `models.py:19,26-29` |
| R3 who/where | Aliases in EN/AR/Arabizi ✓. But `/vault/people` drops `project` and `event` entities, and the new-name detector is Latin-only. | `api/vault.py:182-184`; `live/context.py:22` |
| R3 why | `/why` returns source records; no `reason` field. It can 404 on old facts (10k cap). | `api/vault.py:579-623` |
| R3 contradict/update | `new / update / end` + late history ✓. "6/8" is a weekbench score that ignores the 4 standalone `ended` facts. Multi-step late chains break (`applier.py:288`). Privacy false positives drop gold facts `f039`, `f045`, `f109`. | `weekbench/score.py:93-105`; `tests/e2e/test_gold_month.py:20-27` |
| R3 retrieve | **12** `visible_facts(limit=10_000)` sites (v0 said 11; it missed `mcp/server.py:517`), **plus** MCP search's 1,000-row hydration that drops FTS hits past 1k (`mcp/server.py:485`), plus unbounded scans (`queue/jobs.py:436`, `api/vault.py:401`, `ingest/triage.py:214,220`). | audits A |
| R3 story | `/timeline` is a raw list. | `api/vault.py:287-326` |
| R4 Subjects | **Three different taxonomies:** the extractor's 12 `CATEGORIES`, the vault's 7 `LIFE_SPINES`, and the design's 6. No graph DTO. `/vault/subjects` omits `sensitive_cat`. | `core/extract.py:46-59`; `api/vault.py:337`; `ios:vaultApi.ts:13` |
| R4 People & Places | `closeness_tier` has **no writer** in extraction or import (only tests and fixtures seed it). **`salience` has no writer at all** (always 0.0), so "top-N by salience" is arbitrary. | `models.py:72,74,89`; `core/applier.py:174` |
| R5 provenance | `status == "active"` → `user_supplied` at `api/vault.py:117,177,250` **and `live/context.py:504`**, plus hard-coded `user_supplied` envelopes (`vault.py:135,200,323,573,615`, `context.py:546`). Auto-promotion after 2 days applies to **places, orgs, projects, events and self, not third-party people**. Reproduced: a place went `candidate/inferred` → `active/user_supplied` with no confirmation. | `privacy/policy.py:51-65`; Codex §2 F05 |
| R6 places/topics | A restaurant becomes a `place` entity only if the LLM judges the fact "lasting". The keep-list (`people, work, projects, plans, dates, decisions, purchases, prices, changes`) has **no likes, preferences or places visited**. No `food` theme. No place *type* ("restaurant"), so a later query with the word "restaurant" won't match "dinner at Zuma". **Questions the user asks** are not facts, and **nothing counts repeated topics**, so "you keep asking about AI agents" is never noticed. | `core/extract.py:46-59,180-181` |
| Backfill hygiene | No per-day size cap. Day-boundary mismatch (`at[:10]` vs the owner's timezone, also in `bridge.py:158`). `split_import` hard-codes `pool='internal'`. | `ingest/triage.py:266`; `queue/jobs.py:288-299` |

### 2b. Blockers the audits found (not in v0)

| ID | Blocker | Proof |
|---|---|---|
| **B1** | **The CR-TM bridge used by Community and Messenger works only on the in-memory fake store.** On Postgres, `POST /records` and `/facts/{id}/resolve` return **HTTP 500** (`AttributeError: PostgresGraphStore has no attribute records`). Source-scoped search returns 0 of 2 valid facts. The "B-M merged, 335 passed" result came from fake-store tests. | Codex and Gemini both reproduced it; `api/bridge.py:111,141,152,174,199,241,278`; `tests/test_crtm_handoff.py:14-25` |
| **B2** | **Quarantined facts leave readable entities and edges.** After its only fact was quarantined, a relative still appeared with a `family` label and a `RELATED_TO` link. Links are anchored to the day's first applied fact, or to null, which `/vault/people` always renders. | Codex reproduced it; `core/applier.py:195-206,399-411`; `api/vault.py:192` |
| **B3** | **Forget doesn't fully forget.** `POST /forget` with a fact ID returns 200/ok with `facts_erased=0`, and the fact stays. Source Forget never bumps `facts_version`, so a **warm `context_pack` still returns the erased fact**. It also doesn't recompute counts. Its idempotency is process-local. | Codex reproduced it; `privacy/forget.py:75-195`; `api/bridge.py:63,174-195` |
| **B4** | **Schema changes won't reach existing databases.** `migrate()` only runs `CREATE TABLE IF NOT EXISTS`. Bumping `PROMPT_VERSION` re-extracts and triggers `duplicate_fact` rejections. | `db/db.py:103-112`; `core/validator.py:295-306` |

## 3. Evidence (what stands)

- **Speed (stands):**
  - `context_pack` warm p50 / p95 = 26 / 27 ms at 1k facts, 175 / 182 ms at 5k, 287 / 308 ms at 20k. Old facts are missed at 20k.
  - Sample sizes were small (n = 15), so re-measure in U0 with n ≥ 100 over HTTP.
- **T-1 search quality (does not stand as a baseline):**
  - temporal_note got **no entities, aliases, subjects or links** (pure BM25).
  - Sensitive and superseded facts were loaded as active, which gave **23 / 40 leaking probes**.
  - Per bucket at top-16: Arabic **0.31**, contradiction 0.68 (with the old value returned on every probe), sensitive 4 / 4 leaking.
- **Ablation in a temporary schema (Gemini):** Postgres FTS + entity joins + 1-hop subject expansion + RRF, over the **gold** graph, scored **0.772 / 0.863** at top-8 / top-16, Arabic about 0.78–0.83, at about **3 ms on 20k facts**. On the same machine, graph SQL took 0.36–12.8 ms. This is an **upper bound**: real extraction won't be as clean as gold. It is still strong evidence that **Postgres alone may be enough and embeddings can wait**.

### 3b. U0b baseline on `e05371f` (Gemini, `acceptance/results/e05371f-20261124-1059/BASELINE.md`)

- **S1 retrieval:**
  - gold graph `/context` 0.671 / 0.726 (top-8 / top-16), 0 leaks;
  - **extracted graph 0.361 / 0.413**;
  - `/search` and MCP score 0.0 (whole-question substring matching);
  - 20k over HTTP: `/context` p95 **411 ms** (435 ms with a concurrent writer), and the needle is missed on all 3 paths.
- **S2 extraction on `apps/memory`'s own worker** (`claude-haiku-5-5`):
  - **recall 66.7 %, precision 59 %** (85 true / 57 noise / 2 wrong);
  - **changes: 1/8 superseded, 0/5 ended, 0/4 late**;
  - 0 privacy leaks; 6.86 % false positives;
  - **mean $0.00492 per day** (p95 $0.0075, max $0.0082).

  This is far below the weekbench adapter's 92 % / 6 of 8, partly because the scorer is stricter and the model differs. **U3 must find how much is a real regression:** prompt, schema or applier parity with `weekbench/configs/tn_update.py`.
- **S3 / S4 failed on `e05371f`;** both are addressed by U1a and must be rerun on `267b0cf`.
- **S5** failed: the quarantine leak, auto-promoted `user_supplied`, and faith shown in `/vault/subjects` and export (U1b / U1c).
- **S6–S9** are not yet built. The 84-item trap set is ready (`acceptance/TRAPS.md`).

### 3c. Progress

> **24 Nov:** the engine and Vault clients are on `main`. This v0 progress table and the assignments are historical. U1c, U2, U3, U4, U5 and the Vault UI are merged; U4 provides hybrid keyword + local multilingual embedding search; U6 has a paused handoff. Use E0-E4 for current execution and `reports/STATUS.md` for gate evidence.

| WP | State |
|---|---|
| U0a | ✅ merged `3923366` → `memory` `267b0cf` (Claude verified: 348 passed; Postgres migration, bridge and Forget tests 26 passed). Follow-up **U0a-2**: remove U1a's runtime DDL; repair the `forget_requests` FK. |
| U0b | ✅ harness + baseline (above). Rerun on `267b0cf`. |
| U1a | ✅ merged `afcec62` → `memory` `9ac5875` (Claude verified: 343 passed; 21 Postgres tests). The contest-shared suite was fake-only, so request **CS-1** goes to the shared lead on the other PC. |
| U1b, U1c | ready to start from `267b0cf` |

**Roster and queues (founder, 24 Nov):**
- no Muse;
- **Codex is slow, so it gets half the volume;**
- every agent gets its **full queue in one prompt** (no follow-ups): `prompts\Q_gemini.md`, `Q_cursor.md`, `Q_codex.md`.

| Agent | Queue |
|---|---|
| Gemini | harness rerun → **U1c** → **U5** → **U7** reruns after every merge |
| Cursor | **U1b** → **U3** (Part A can start now) → **UI** (`ios`) |
| Codex | **U0c** (cleanup + contract v2) → **U2** |
| Claude | verify (Postgres + harness) → merge `memory` / `ios` → push → `reports\<WP>.review.md` |

Status board: `reports\STATUS.md`. U0a-2 is folded into U0c. U4 (embeddings) stays deferred.

## 4. Design (v1)

```
IN CONVERSATION (instant, ~$0)                 BACKFILL (daily)                              ON DEMAND
narrow code templates, first-person,           1 call per day packet (token-split):          SQL candidates only:
explicit assertions only; reject negation,     who/where/why(reason span)/changes            FTS + entity/alias + 1-hop
questions, plans, third parties, sarcasm        + actions + places & preferences              + subject + date → RRF
 → triple stored on the Fact                    + place type (restaurant/café/gym)            /vault/graph (Rule 9 gated)
 + topic counter (no LLM): subjects touched     two-visit topic interests → "I noticed"      story: cited timeline first,
 per session → after 2 separate sessions:                                                     LLM narration optional
 "I noticed you're into X" hypothesis
catch-up pass per session (D-b)
```

## 5. Work packages (v1 order)

| WP | What | Fixes | Size |
|---|---|---|---|
| **U0** | **Baseline and contract freeze.** Rebuild the harness:
- extracted graph plus gold graph, with aliases;
- sensitive facts gated, superseded facts kept as history;
- per-bucket scores with leaks counted as failures;
- HTTP latency with n ≥ 100;
- Forget, bridge-on-Postgres and why/story probes;
- a labelled trap set for live triples (negation, questions, plans, third party, sarcasm, AR/Arabizi).

Freeze one `models.py` change request for U1–U3. Add versioned, idempotent migrations to `migrate()`. | B4, evidence | M |
| **U1** | **Correctness and speed core:**
- (a) **Port the bridge to Postgres** and pass `contest-shared`'s `test_memory_bridge_*` HTTP suite (B1);
- (b) **Forget:** transactional, bumps `facts_version` + generation, recomputes counts, idempotency persisted in the DB (B3);
- (c) **Applier:** no entity, alias or link without surviving, approved evidence, and each link anchored to its own fact (B2);
- (d) **Provenance:** stored, never derived from `status`, at all 4 sites + envelopes; add `user_confirmed_at`;
- (e) **SQL retrieval** at all 12 sites + MCP hydration: ranked IDs for search, exact lookup for `/why`, SQL aggregates for counts, windows or cursors for timeline, export and reflect;
- (f) **salience** computed in SQL;
- (g) **`/vault/graph?view=subjects|people`**, versioned DTO (§5.1), **Rule 9 gated server-side** (U6 rules ship *here*). `/vault/subjects` and `/vault/people` stay backward-compatible. | R1 R3 R4 R5, B1–B3 | L |
| **U3** | **Backfill:**
- one owner-timezone day function everywhere, and token-budgeted chunks with chunk-aware idempotency;
- a cited `reason` span, validated against the source records;
- fix late chains (`applier.py:288`) and the privacy false positives (`f039`, `f045`, `f109`);
- **R6:** add *places visited, likes and preferences* to the keep-list, plus a **place type** (restaurant, café, gym, …); food and outings go under **Events**;
- **one taxonomy (D-a = the engine's 7).** The extractor emits the 7 cluster roots directly: `career`, `learning`, `projects`, `people-family`, `events`, `home-money`, `travel`. Held-back `health` and `faith` roots are **never clusters**: a health fact the user stated shows only in search, why and its own detail.
  - Today `travel` is never produced, and `interests`, `devices`, `background`, `identity` and `wellbeing` map to no cluster (`core/extract.py:46-59` vs `api/vault.py:339-346`).
  - The agent proposes an old → new mapping for existing facts in its report, and the founder confirms it. | R3 R6 | M |
| **U2** | **Instant triples:**
- triples as **optional fields on `Fact`** (actor, predicate, object, polarity/modality, event time, cited span); **no `thing` entity kind** (all three audits agree);
- narrow first-person templates with reject lists, gated by `pre_write` (no health, family or faith);
- `user_supplied` only for explicit first-person assertions that pass the precision gate; everything else stays a hypothesis;
- dedupe against the later backfill by content hash;
- **R6 topic counter:** subjects matched per session, with no LLM; at ≥ 2 separate sessions, create an "I noticed" hypothesis; sensitive topics are never counted;
- a new `extract.session` job kind wired into the queue and Forget (D-b). | R1 R2 R5 R6 | M |
| **U5** | **Why and story:**
- why = exact fact + cited reason span, or "reason unknown";
- story = a **deterministic cited timeline first**, with LLM narration optional and capped (~2k tokens);
- every citation is checked against the visible facts; Rule 9 screen on the output;
- cache keyed by generation + `facts_version` + query;
- falls back to the template when over budget. | R3 R5 | S–M |
| **U7** | Rerun U0's harness after each WP; full run at release. | all | M |
| **U4** | **Embeddings: deferred.** Only if U7 shows an Arabic or paraphrase bucket below its floor after U1–U3. Try `pg_trgm` + a small EN↔AR synonym map first; then local multilingual embeddings, with exact scoring on the candidate pool; HNSW only if needed. | R3 | L, if needed |

**Order:** U0 → U1 → U3 → U2 → U5 → U7 → (U4 only if needed). The mobile app switches to `/vault/graph` only after U1 passes its Rule 9 and Forget gates (on `main` through an additive adapter in `vaultApi.ts`; the demo fallback stays labelled).

### 5.1 `/vault/graph` DTO (merged from the audits)

`{version, owner, view, center_id, as_of, provenance, demo_data, counts:{total_nodes, shown_nodes, people, places, projects, relations, hidden_by_group}, nodes:[{id, kind, label, subtitle, group, tier, fact_count, salience, provenance, review_state, as_of, evidence_fact_ids}], edges:[{id, src, dst, rel, kind: observed|membership, provenance, review_state, valid_from, valid_to, evidence_fact_ids}], key_items}`

- Every edge connects visible nodes.
- `+N more` = `hidden_by_group` (authorized omitted nodes only).
- Counts are computed over the same gated projection, before capping.
- The client draws the T1 ring from `tier`.

## 6. Acceptance gates (v1; proposals except where marked "existing")

- **Retrieval:** p95 < 150 ms at 20k facts (**existing L1 target**), over HTTP with n ≥ 100, including during a backfill; the old-fact needle is found.
- **Search quality:** per-bucket floors **set from the U0 baseline on the extracted graph**. Auditor proposal on the gold graph: top-8 ≥ 0.78, top-16 ≥ 0.85, Arabic ≥ 0.80. **0 sensitive leaks** on every surface: graph, context, why, story, export, MCP, caches.
- **Live triples:** precision on the U0 trap set; auditors propose **≥ 90 %** (Gemini) to **≥ 98 %** for `user_supplied` emissions (Codex). The founder picks. No LLM per message.
- **Backfill:** **mean** cost per original owner-day (all chunks, retries and fallbacks) ≤ today's measured ~$0.0044, **measured on `apps/memory`'s own worker**. Also report p95 and max: in the month run, 11 of 31 days were already above $0.0045 (max $0.0056), so a per-day cap would fail on day one. Changes: **8/8 superseded + 4/4 ended + 4/4 late** on `apps/memory`. Privacy false positives ≤ 2 % on clean gold facts.
- **Forget:** 0 survivors across facts, links, entities, counts, caches and stories, warm and cold, with a job in flight.
- **Bridge:** `contest-shared`'s HTTP contract suite passes against Postgres.
- **Graph:** p95 < 150 ms at 20k; true counts; no orphan edges; T1 only per D-c.
- **Why/story:** every factual clause resolves to a visible evidence span; unknown reasons stay unknown.
- **R6:** a restaurant mentioned once with a lasting signal can be retrieved by name, by area and by "restaurant". A topic asked about in ≥ 2 separate sessions yields one "I noticed" hypothesis; a topic asked once yields none.

## 7. Founder decisions (24 Nov 2026)

| | Decision | Consequence |
|---|---|---|
| **D-a clusters** | **The engine's 7:** Career, Learning, Projects, People & family, Events, Home & money, Travel. The design changes to match. | One taxonomy from extraction to API to app (U3). There is **no Health cluster**. **People & family** is a sensitive cluster (Rule 9), so it shows only facts the user stated or confirmed. The phone's `THEME_COLORS` (`ios:vaultApi.ts:61-63`, now the design's 6) move to the 7 in the UI task. |
| **D-b catch-up pass** | **Local Qwen first, Haiku as fallback**, once per session (on idle or close), not per message | U2 adds an `extract.session` job: it goes to the owner-device / local pool (`qwen/qwen3-4b-2507` via LM Studio, `config.py:15`) and falls back to Haiku after the existing fallback delay (`p1_fallback_seconds`, `config.py:25`). Both report their model (existing Attempt fields). |
| **D-c T1** | **Suggested, then confirmed.** The engine suggests T1 from interaction frequency and recency and shows it as "I noticed". A person joins the ring only when the user confirms. | U1/U6: store a `closeness_suggested` (+ evidence) separately from `closeness_tier`; only a confirm action writes `closeness_tier`, with a timestamp. Suggestions never use family or other sensitive signals as input. |

Auditor votes are in `tn_upgrade_audit_{codex,cursor,gemini}.md` §6.
