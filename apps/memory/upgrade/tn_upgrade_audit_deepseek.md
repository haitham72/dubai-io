# TN Upgrade Plan — independent audit (deepseek — originally saved as tn_upgrade_audit_codex.md by mistake)

Scope: `P:\TN_UPGRADE_PLAN.md` (draft v0) + the T-1 evidence in `P:\realbench\20261124-0916\`.
Engine under audit: `M:` = `G:\Haitham\VsCode\contest-memory\apps\memory` (branch `memory` @ `e05371f`, package `temporal_memory`). `P:` = `G:\Haitham\lab-data\memory-bakeoff`.
Read-only. No repo file edited. Findings without evidence are marked UNVERIFIED.

---

## 1. Verdict (A)

**Sound with fixes.** The direction is right and cheap: SQL-backed candidates (U1), code-only instant triples (U2), per-session dedupe (U3), a graph endpoint built from derived tables (U1/U6), and a story cache (U5) all fit the founder's rules and the measured postgres latencies. But four things must be fixed before work starts:

1. **R5 is not closed by the proposed graph contract.** `{nodes, edges, counts}` carries no `sensitive_cat`, no per-node `provenance`, no `as_of`. Today's `/vault/subjects` and `/vault/people` already omit `sensitive_cat` while the mobile filter reads it (`M:api/vault.py:108-121,164-180`; `apps/mobile/src/features/vault/vaultApi.ts` `filterSubjects`). Shipping U1/U6 as written makes the leak permanent.
2. **U5's cache key is unsafe.** The plan caches the story "until `facts_version` changes", but `Forget` bumps only `records.generation` and never `owners.facts_version` (`M:privacy/forget.py:82-92`; no `facts_version` in the file). A forgotten fact can be re-narrated from cache.
3. **R2 has a latency gate but no accuracy gate.** "Live triples <50 ms" measures speed only. Nothing gates negation/plan/question/third-party false positives, and the plan labels derived wants/likes `user_supplied`.
4. **The T-1 evidence cannot justify U4** (§2 below): the "FTS+alias 0.644" label is wrong and the Arabic bucket is a harness artifact.

Also: §2 says 11 load-all sites — there are **12**; §2's Subjects row conflates `/vault/subjects` with the 7 life spines; the §5 cost gate is set below today's measured per-day cost.

---

## 2. Is the T-1 evidence valid? (B)

### 2.1 What was actually run
- T2b (110 gold facts, 40 probes), T3 (latency at 1k/5k/20k), T5 sealed (engine only, not TN), T6. **T1, T2 end-to-end, and T4 were not run; Forget was not run on TN** (`P:\realbench\20261124-0916\NOT_TESTED.md`). "temporal_note stays" is therefore a provisional verdict on 2 of 4 tracks, not a four-track result.
- Coverage is exact fact-ID set intersection (`gold_context_fact_ids`), averaged per probe. **No precision, no nDCG, no judge.** Two noise probes have 0 gold slots, so only **38/40** probes enter the mean.

### 2.2 Numbers (verified from `raw/*/t2b_results.json`)

| bucket | TN top8 | TN top16 | ref top8 | ref top16 | gold slots |
|---|---|---|---|---|---|
| person | 0.631 | 0.667 | 0.595 | 0.750 | 27 |
| person_alias | 0.889 | 0.889 | 0.778 | 0.889 | 10 |
| contradiction | 0.680 | 0.680 | 0.700 | 0.780 | 45 |
| twohop | 0.906 | 0.938 | 0.688 | 0.938 | 32 |
| arabic | 0.264 | 0.306 | 0.167 | 0.306 | 21 |
| sensitive | 0.083 | 0.250 | 0.083 | 0.083 | 12 |
| **mean** | **0.6066** | **0.6439** | 0.5351 | **0.6680** | 147 |
| **micro** | 0.6259 | 0.6599 | 0.5578 | 0.6939 | 147 |

TN p50 11.6–11.7 ms vs 64.4 ms (`raw/temporal_note/t3_latency.txt`, UTF-16). Contradictions 6/8 (`LEADERBOARD.md`, day log).

### 2.3 Four validity defects (material)

1. **The TN run had no graph at all.** `run_tn_t2b.py:49` inserts one subject `s1/life/general`; `:56` inserts `(id, owner, text, text_folded, subject_id, valid_from, status, content_hash)` only — **no `text_orig`, no entities, no aliases, no `fact_entities`**. The leftover schema still proves it: `facts=110, entities=0, aliases=0, subjects=1, fact_entities=0`. So "FTS+alias 0.644" is **BM25 + date only**; the alias channel the plan proposes to beat was empty. The plan's claim "above the best single channel measured (FTS+alias 0.644)" is unsupported.
2. **The Arabic bucket is not an engine result.** Ledger facts have no `text_orig` at all, and the harness never populated it; the probes are AR/ARZ queries against English facts. 0.306 measures the absence of a cross-lingual channel, not TN's search. It cannot be used to size U4 either way.
3. **TN is structurally capped.** It returned <16 items on 14/40 probes and 0 on t29/t31/t33/t39/t40, so its "top-16" is partly a packing artifact.
4. **Rule 9 is not measured.** The harness inserted all 110 facts raw, bypassing `pre_write`; both engines therefore "leak" in all 4 sensitive probes and 10/10 contradiction probes. `gold.gated` is a list of `{category,count}` (e.g. `family_health`), and the harness ignores it — it only checks `must_not_contain`. T2b cannot substantiate either "0 leaks" or "no leak", and the plan's Rule 9 gate needs a different test (ingest through the gate, then query context/graph/story).

**B verdict:** the *recall at k* numbers are real for the channel tested (BM25+date), and the latency/who-where/forget results are usable. The U4 evidence, the "FTS+alias" label, the Arabic bucket, and any Rule 9 claim are not.

---

## 3. §2 row checks (C)

| §2 row | Verdict | Evidence |
|---|---|---|
| **R1** load-all sites 11 + `/search` 4.6 s | **PARTLY** | There are **12** `limit=10_000` sites: `api/vault.py:92,152,215,264,299,430,587`, `api/bridge.py:280`, `api/export_md.py:50`, `reflect.py:117`, `live/context.py:406`, `mcp/server.py:517` (missed), plus `mcp/server.py:485` `limit=1000`. Search numbers match T3. |
| **R2** no action triples | **CONFIRMED** | `Fact`/`LinkRel` are state/relation only; 23 of the 28 gold edge rels (COFOUNDS, TEAMMATE, BEST_FRIEND, ENGAGED_TO, RECRUITS, EX_COLLEAGUE, COACHES, TRAINS_AT, TEACHES, ENROLLED_IN, CLASSMATE, NEIGHBOUR, FATHER_OF, SISTER_OF, COUSIN_OF, DENTIST_OF, AGENT_FOR, WORKED_AT, …) are outside `LinkRel` (`M:models.py`, `M:core/validator.py:28`, `M:core/extract.py:62`). `buys`/`wants`/`likes` likewise absent. The month run found 28/42 edges — the closed set is already the binding constraint, not the LLM. |
| **R3** who/where needs aliases | **CONFIRMED** | Alias tables + folding exist (`live/context.py:162`), AR/Arabizi aliases are seeded in `tests/fixtures/karim_gold_slice.json:11-14`. Nothing new needed. |
| **R4** Subjects = LIFE_SPINES(7) | **WRONG** | `/vault/subjects` returns the **subject table** built by the extractor (`vault.py:85-138`, `subjects.llm_categories` semantics), whose themes come from `extract.py:46 CATEGORIES` = 12 (background, devices, family, health, identity, interests, learning, lifestyle, money, projects, wellbeing, work). `LIFE_SPINES` is 7 and is used only by `/profile` (`vault.py:434`, `_SPINE` map). The fixture shows `lifestyle/*`, `money/*` roots, not spines. D-a's premise ("today's seven") is false. |
| **R5** Stays; gaps are new surfaces | **PARTLY** | No `/vault/graph` exists (true). But `sensitive_cat` is never written for subjects (no writer; only read at `graph_store.py:331,453`), and no vault response returns it — so the "new surfaces inherit the gate" assumption fails at the API layer. `export_md.py:119` gates only `theme == "health"`, while CATEGORIES also has `wellbeing`/`lifestyle`. |
| **Cost** $0.0045/day | **WRONG as a gate** | `runs_month_tn_day.log`: 31 day rows, sum $0.1368, **mean $0.00441, max $0.00562; 11/31 exceed $0.0045, 4/31 exceed $0.0050**. 32 LLM calls / $0.1402. The gate fails today, before U3 adds output fields. |
| **Contradictions 6/8** | **CONFIRMED** | Day log + `LEADERBOARD.md`. |
| **Latency** | **CONFIRMED** | T3 matches; my 20k bench: `visible_facts(10k)=168-172 ms`, `/subjects` 170-173 ms, `/people` 178-186 ms, SQL counts 4.9-5.5 ms, people aggregate 48.6-49.5 ms, pg FTS p50 4.9-5.4 / p95 5.9 ms, derived-table graph p50 3.2-3.6 / p95 4.0 ms (3 runs, synthetic 20k, temp schema). |
| **Provenance bug "3 sites, active→user_supplied"** | **PARTLY** | Real, but 4 sites: `api/vault.py:117`, `:177`, `:200`, and `live/context.py:504`. Auto-promote at ≥2 days is `applier.py:171`, `:373-383` + `privacy/policy.py:63-65`; it applies to self + non-person entities only (third-party persons need an explicit tap), so "including entities auto-promoted" is true for places/orgs/projects/events, not people. |
| **No per-message LLM call** | **CONFIRMED, with nuance** | `bridge.py:40` defaults `enqueue="extract.live"`, `:155` priority 0; one POST creates one job → one extraction call per record. A client can batch or opt out (`enqueue="none"`), so the claim is a default, not a guarantee. `direct_fact` (`bridge.py:137-144`) writes `status="active"`, `provenance` default `user_supplied`. |
| **Day packet split + day boundary** | **CONFIRMED** | `ingest/triage.py:266` `day=(rec.at or "")[:10]` vs `queue/jobs.py:288-293` `ZoneInfo(owner.timezone)`+`astimezone`. Example: `2026-11-20T22:30Z` → CLI day `2026-11-20`, Dubai day `2026-11-21` (computed). All CLI paths go through `ingest_records` (`ingest/cli.py:136,178,200,222,264`), so the mismatch affects every import path. No size cap: `extract.py:224-237` concatenates every `bundle.records` with no truncation. |
| **closeness_tier never written** | **CONFIRMED** | Only read (`graph_store.py:320,415,440`, `vault.py`, `export_md.py:175`); the only values come from test fixtures (`karim_gold_slice.json:10-14`). `export_md` therefore defaults everyone to T3. |

---

## 4. Findings (most severe first)

### 4.1 Blockers

**F1 — U5 cache can serve forgotten text (R5).** `P:\TN_UPGRADE_PLAN.md` §4 U5 says "cached until `facts_version` changes"; `M:privacy/forget.py` never touches `facts_version` (it bumps `records.generation`, sets `erased_at`, re-queues jobs). Live context caches BM25 keyed on `facts_version` (`live/context.py:310-316`) and is only cleared because `bridge.forget` calls `invalidate_alias_cache` (`bridge.py:192`); a `/story` route would not. **Fix:** bump `owners.facts_version` in `forget_source`, and key the story cache on `(facts_version, owner_generation)`.

**F2 — The graph contract cannot enforce Rule 9 (R5).** `{nodes, edges, counts}` has no `sensitive_cat`, no per-node `provenance`/`as_of`. The mobile screen filters on `sensitive_cat` (`vaultApi.ts` `filterSubjects`/`filterEntities`), which the current API never returns (`vault.py:108-121,164-180`) and the DB never writes (no writer for `subjects.sensitive_cat`). Result: a `health`/`family_health` node would render, and counts would include held-back facts. **Fix:** include `sensitive_cat`, `provenance`, `as_of` per node/edge; filter server-side before counting; add a contract test.

**F3 — R2's gate measures only speed.** §5: "Live triples <50 ms with no LLM call per message (proposed)". There is no precision/recall gate, no false-positive rate for negation ("I'm *not* buying"), plans ("I'll buy"), questions ("should I buy?"), hypotheticals, or third-party statements. And labelling any self-statement `user_supplied` makes an inferred want look like a user fact (`live/context.py:504` is the same pattern). **Fix:** a 40+ turn gold set (live + AR/ARZ), gate on precision ≥0.9 and FP ≤5% by construction class; only literal, present-tense self-statements are `user_supplied`; everything derived is `status="hypothesis"`, `provenance="inferred"`.

**F4 — T-1 cannot justify U4.** See §2.3. The proposed gate "top-16 > 0.668" is a +2.4-point target on a 110-fact corpus where the alias channel was empty and the Arabic bucket invalid; U4 is the largest work package (column, HNSW, backfill, re-embed on edit/forget) and its gain is UNVERIFIED. **Fix:** rerun T2b with entities/aliases/`text_orig` populated; only then decide U4.

### 4.2 Major

**F5 — §2 off by one.** 12 `limit=10_000` sites, not 11 (adds `mcp/server.py:517`; also `:485 limit=1000`). U1's scope must include both.

**F6 — §2 R4 / D-a premise is wrong.** No design/engine "six vs seven" choice exists as stated: the design has **two different sixes** — graph clusters (Career, Projects, Learning, Gaming, Travel, Health; 458 = 142+98+76+64+41+37) and drawer themes (Today, Career & Projects, People & Family, Gaming & Hardware, Travel & Places, Home & Money) — while the engine ships 12 extraction categories and a 7-spine profile map. `/vault/subjects` serves the 12, not the 7. **Fix:** resolve as a display mapping, one module, storage unchanged (see D-a).

**F7 — Provenance fix is under-scoped.** 4 sites (F2/§3), and the auto-promote half only concerns non-person entities. Third-party people are safe by `policy.py:63-65`; the plan's wording overstates the blast radius but still needs the 4th site.

**F8 — U1 does not remove the in-process cache.** `context_pack` builds and caches a Python BM25 index from `visible_facts` (`live/context.py:406`, `:310-316`) and invalidates on every `facts_version` bump — i.e. on every apply. T3 shows 398 ms for "the first search after +1 fact" at 20k; the §5 gate "p95 <150 ms including during a backfill" therefore fails even after U1 unless the cache is removed, not just the candidate query. **Fix:** make U1 delete the Python index path, and say so.

**F9 — R4 graph schema is undefined.** Counts 458/179 are node counts by the design's own arithmetic, while `fact_count` is what the API returns. "+N more" behaviour, edge direction, and self-node absence are unspecified. **Fix:** define node = subject|entity|self, edge = Link (+ action triple later), with explicit `kind` and counts.

**F10 — U2/U3 closed-set churn is understated.** Adding `buys`/`wants`/`likes`/`visits`/`moves` requires changes in `models.py` (`LinkRel`), `validator.py:28` (`VALID_LINK_RELS`), `extract.py:62` (`LINK_RELS`), the prompt JSON (`extract.py:200-201`), and the applier. 23/28 gold rels are already outside the enum and only 28/42 edges were found — adding "action relations" one by one repeats a known mismatch. **Fix (cheaper):** store actions as **Fact fields** (`action`, `thing_id`, `polarity`, `modality`) with `status="hypothesis"`; derive an edge only for stable relations. No enum churn, no validator change.

**F11 — Cost gate fails today and U3 makes it worse.** 11/31 day rows exceed $0.0045, max $0.00562. U3 adds actions/things/reasons to the extraction output (more tokens). **Fix:** gate on mean and p95 (e.g. mean ≤ $0.0050, p95 ≤ $0.0060), and re-baseline after U3.

**F12 — The coverage gate can be gamed and is incomplete.** Recall-only, 38/40 probes, TN returned <16 on 14 probes. Returning 16 facts always would raise coverage while lowering relevance. **Fix:** add precision@k or nDCG on the same probes; require ≥16 returned or count the missing slots as zero (already effectively done).

**F13 — U2 bypasses the privacy gate and inherits `direct_fact` defaults.** `bridge.py` calls `pre_write` on records (`:109`) and `direct_fact` text (`:127`), but a U2 code extractor writing facts directly would not; and `direct_fact` writes `status="active"` with caller-chosen provenance, default `user_supplied` (`:137-144`). A third-party family/health statement would become an active "user-supplied" fact. **Fix:** route every U2 triple through `pre_write`/`gate_fact`; third-party or sensitive → quarantine, never a triple.

**F14 — The day-packet fix is in the wrong layer.** The plan puts "split into day packets by token budget" under U3 (extraction prompt). The packet is built in `ingest/triage.py:266` (day) and consumed in `queue/jobs.py`; `format_user_prompt` concatenates every record (`extract.py:224-237`). Splitting inside the prompt still sends one giant job. **Fix:** split at triage/job creation, unify bucketing on `owner.timezone`, and cap records per job.

### 4.3 Minor

| # | Finding | Evidence |
|---|---|---|
| F15 | Benchmark/test runs leave temp schemas behind (`t2b_tn_baaedc05` 110 facts, 3 `smoke_*`, 3 `tm_test_*`) — the "drop in `finally`" pattern does not always run. | psql inventory; not mine, left untouched. |
| F16 | `export_md` health gate is exact-slug `"health"`, so `wellbeing/*`/`lifestyle/*` health facts bypass it (mitigated by `pre_write`). | `export_md.py:119` vs `extract.py:46` |
| F17 | `closeness_tier` is dead data; export defaults to T3. | `graph_store.py:440`; fixtures only |
| F18 | "Why" as a *reason* needs a new field/contract; the plan says "prompt bump". | `vault.py` `/why` returns evidence only |
| F19 | "One LLM call per message" is a default, not an invariant (`enqueue="none"`, client batching). | `bridge.py:40,150` |
| F20 | `visible_facts` at 20k is 168-172 ms; at ~50k it will exceed the gate before U1. | own bench, synthetic |

---

## 5. Per-work-package notes (E)

**U1 (candidates from SQL + graph endpoint) — keep, M.** Measured: derived-table graph 3.2-3.6 ms p50 / 4.0 ms p95; SQL subject counts 4.9-5.5 ms; people aggregate 48.6-49.5 ms (the only non-trivial one — index `entity_subjects(owner)`); pg FTS 5.9 ms p95 vs `visible_facts` 170 ms. Also: delete the Python BM25 path (F8), include `sensitive_cat`/`provenance`/`as_of` (F2), use `13` sites (F5), and freeze the `/vault/graph` JSON + TS type before coding.

**U2 (instant triples) — riskiest, L.** Code-only viability is plausible for explicit patterns, not for negation/plan/question/third party. Honest expectation 0.6-0.75 precision on a first cut, unmeasured. Cheaper than the plan: Fact-field triples (F10) avoid the enum/validator/extractor contract churn. Must gate through `pre_write` (F13) and must not use `direct_fact`'s active/user_supplied defaults. Add a gold set before writing code — otherwise U7 cannot measure it.

**U3 (actions/reasons/things) — M, but split the work.** `reason` is a new Fact column + `OutFact` field + applier + `/why` contract (F18). Action fields are part of U2's shape (F10), not a separate pass. Day splitting belongs in triage/jobs (F14). Budget: +10-20% output tokens → re-baseline cost (F11).

**U4 (embeddings) — defer (L).** The only measured gain is +2.4 points mean / +3.4 micro on 110 facts with the alias channel empty and an invalid Arabic bucket (F4). Alternatives first: populate `text_orig` (FTS already includes it), alias→entity→fact expansion (works for AR/ARZ entity queries, which most Arabic probes are), and date priors. If still needed: pgvector is already in the image; HNSW build/re-embed cost and Forget tombstone behaviour are UNVERIFIED here.

**U5 (story/why) — M.** One call, cached. Fix the cache key (F1), filter sensitive facts and mark provenance on every sentence, and require a citation per clause. "Why" needs the `reason` field (F18). A story generated from `visible_facts(10_000)` inherits the 10k truncation — use the U1 SQL path.

**U6 (graph UI mapping) — S/M.** One mapping module + server-side filtering. T1 stays user-set (D-c). Two six-way taxonomies exist (F6); do not rename storage.

**U7 (evaluation rewrite) — L, and it is the actual blocker for U2/U4.** Needs: live-triple gold (FP by construction class), story/why gold (citation fidelity, 0 unsupported, 0 sensitive), Rule 9 through the gate (§2.3-4), precision@k/nDCG, per-bucket AR/ARZ, and a second run "before/after". Without it, U2 and U4 are unfalsifiable.

---

## 6. Decisions (D)

**D-a — taxonomy: use the design's graph six as a *display layer*, not the storage tree.** Recommend: graph = Career, Projects, Learning, Gaming, Travel, Health (the target screen), with an explicit `ROOT→cluster` table and an "Other" bucket for roots with no design home (family, money, home, events). Drawer keeps its own six (a different surface). Health is user-stated only (rule 9). This is ~100 lines of mapping; no migration, no extractor change. Rejecting "engine's seven": they are a profile-only abstraction and are not what the vault serves (F6).

**D-b — code-only first, no per-message LLM.** Yes. Code-only is $0, instant, and testable; a local Qwen adds an ops dependency that was already absent during T-1 (LM Studio offline, per NOT_TESTED). One Haiku catch-up per *session close* is acceptable only if U7 shows code precision <0.9 — and it must never sit on the message path. This keeps the plan's own "no LLM per message" promise.

**D-c — T1 by explicit user action only.** A frequency-derived "inner circle" is an inference that changes who gets the highest trust boundary; rule 9 forbids inferring it, and the design calls T1 a trust boundary. Allow "I noticed" suggestions for T2 at most; never auto-T1.

---

## 7. Unknowns, commands, cleanliness (G)

**Could not verify**
- Design pixels: I read `design/20-11-2026/INDEX.md`, not the JPG; cluster/trust details come from the index + mobile source.
- U4 embedding quality/cost (LM Studio offline); HNSW build and Forget tombstone behaviour.
- T1/T2 end-to-end/T4 and TN Forget: not run by T-1.
- Real multi-tenant behaviour: my 20k bench is single-owner synthetic.
- Mobile UI runtime (static source only).

**Commands run (read-only unless noted)**
- `rg`/`Get-Content`/`ConvertFrom-Json` over `P:\`, `M:`, `apps\mobile\src\features\vault`, `design\20-11-2026`.
- `pytest tests/test_vault.py tests/test_crtm_handoff.py -q` in `M:` with `PYTHONPATH=src` → **13 passed** (the provenance bug is untested).
- Python day-boundary check (`ZoneInfo('Asia/Dubai')` vs `[:10]`).
- `docker exec temporal-memory-postgres-1 psql -U tm -d tm` — schema inventory and counts on `t2b_tn_baaedc05`.
- `python audit_scratch\codex\graph_probe.py` ×3 (20k facts; temp schemas `audit_graph_*`, dropped).
- `git -C … status --porcelain` on both repos.

**Cleanliness**
- `contest-memory`: working tree **clean**.
- `contest`: no modifications; only pre-existing untracked `design/20-11-2026/Dubai-io Quest Milestones Showcase.jpg` and `docs/Researches/new tools research.md` (not mine).
- No file written outside `P:\`; the only file created is this one.
- All **my** temp schemas dropped (`audit_graph_*` absent, verified). The DB also holds pre-existing leftovers I did not create and left untouched: `t2b_tn_baaedc05` (T-1, 110 facts — counts captured above), `smoke_2ab0c116`, `smoke_9895751a`, `tm_test_2002730258ca`, `tm_test_59c5a63bf91c`, `tm_test_forget_wpC`.
