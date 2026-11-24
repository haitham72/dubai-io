# temporal_note upgrade audit — cursor

Read-only check of `TN_UPGRADE_PLAN.md` (draft v0) against `memory` @ `e05371f` and `realbench/20261124-0916`. Judged only against R1–R5.

## 1. Verdict

Sound with fixes. The latency gap, the missing graph payload, the unset T1 tier, and the provenance relabel are real. The plan over-counts a clean "11 sites" list, overstates the live-chat cost path, and treats a search-only bake-off as proof the engine should stay. Do not adopt the `> 0.668` gate: it is another engine's score, and that run loaded sensitive gold facts as ordinary active facts. Ship U1 (including the 12th load-all and a citation check) before any embedding index.

## 2. Findings

| ID | severity | section | finding | evidence | suggested fix |
|---|---|---|---|---|---|
| F1 | blocker | B, F | T2b is not a held-equal *graph* test, and its sensitive probes leak. Both engines were given the 110 ledger fact texts. temporal_note got no gold entities, aliases, or subjects (one dummy subject `s1`). Coverage is an ID intersection, not a judge. All 4 sensitive probes leak in top 16, including a credential, family health, and a third party's private life. Noise probes (empty gold ids) are dropped from the mean (38 of 40). | `run_tn_t2b.py:49-58`; `run_t2b_equal.py:43-55`; recompute below | Do not use 0.644 / 0.668 as the quality bar. Rebuild T2b with entities and aliases withheld from both sides, sensitive facts not inserted, and a per-bucket table that counts leaks as failures. |
| F2 | blocker | C, E | U5 can narrate a secret, and its cache key misses Forget. `forget.py` never updates `facts_version` (the applier does, at `core/applier.py:449-451`). A story cached on `facts_version` survives Forget. T2b already returns gated text inside `context_pack`. | `privacy/forget.py` has no `facts_version`; `raw/temporal_note/t2b_results.json` probes t35–t38 | Retrieve only `active` user-stated facts that pass `pre_write`. Verify every citation id server-side. Invalidate on generation as well as `facts_version`. Run U6's filter before U5. |
| F3 | major | A | There are 12 `visible_facts(..., limit=10_000)` sites, not 11. The plan omits MCP `memory_vault`. MCP search is not FTS-only: it still loads 1,000 facts for a Python fallback. | `mcp/server.py:485` and `:517`. The listed 11 are real: `live/context.py:406`, `api/bridge.py:280`, `api/vault.py:92,152,215,264,299,430,587`, `api/export_md.py:50`, `reflect.py:117`. GIN index: `db/schema.sql:112` | Add `mcp/server.py:517` to U1. Stop the 1,000-row fallback or cap it in SQL. |
| F4 | major | A, C | The provenance bug is real, but it does not auto-promote third-party people. `status == "active"` is rewritten to `user_supplied` for subjects, people, and quests. `may_promote` promotes places, orgs, projects, events, and `self` after 2 distinct days with `user_confirmed=False`. A third-party person stays `candidate` unless the user confirms. The words "You told me" are the product label for `user_supplied`, not a string in `vault.py`. | `api/vault.py:117,177,250`; `privacy/policy.py:51-65`; `core/applier.py:171` and `:373-374` | Return the stored provenance. Map `candidate` to "I noticed". Never infer `user_supplied` from `status`. |
| F5 | major | A | "One LLM call per live message" is only the bridge default. The only `extract.live` enqueue in `src/` is `POST /records` when the client omits `enqueue`. Nothing in the engine turns a chat turn into that call. The worker still does one model call per claimed job. | `api/bridge.py:40,150-158`. Grep of `src/**/*.py` for `extract.live` hits bridge, the `JobKind` literal, and the forget requeue filter only | Say "default bridge enqueue is one `extract.live` job per posted batch". Gate R1 on jobs created per session, not on a chat loop that is not in this package. |
| F6 | major | C, E | `/vault/graph` as specified does not match the screen or the mobile client. The JPG wants a centre node, six clusters with counts (142 / 98 / 76 / 64 / 41 / 37), a T1 ring, and People 28 / Places 19 / Relations 132. `INDEX.md` also says the vault has seven life themes. `vaultApi.ts` loads `/vault/subjects`, `/vault/people`, and `/timeline` into a tree and a tiered layout. It has no `{nodes, edges}` type. `closeness_tier` is selected and displayed, never written. | `design/20-11-2026/INDEX.md:117-150` and `:197`; `models.py:72`; `core/applier.py:174` (INSERT has no tier); `git show ios:apps/mobile/src/features/vault/vaultApi.ts` (`loadVault`, `buildPeopleNodes`) | Schema below. Add an adapter in `vaultApi.ts` in the same change as the route. Do not claim the current constellation is the JPG. |
| F7 | major | F | Two gates are the wrong number. `> 0.668` is mem0's top-16 on this run. `< 50 ms` and `8/8` are unmeasured for the new live extractor. The month score `6/8` is a backfill change score (`LEADERBOARD.md` row `20261123-140525`), not live-triple precision. | `RESULTS.md` §2; `LEADERBOARD.md:10` | Gates in §6 of this audit. |
| F8 | minor | A | Day-boundary mismatch and missing size cap are real. CLI/triage buckets by `at[:10]`. `split_import` converts to `owners.timezone`. The day loop enqueues every id. `$0.14` / 32 calls is the leaderboard row; `0.1402/32` is about `$0.0044`, and that 32 is the published call count, not a pure extract-only count I re-summed. | `ingest/triage.py:266-276`; `queue/jobs.py:288-299`; `LEADERBOARD.md:10` | One timezone helper. Split a day when the packet exceeds a token budget. Quote `$0.1402` for 32 calls until extract-only is re-summed. |

## 3. §2 row check

| Need | Result | Evidence |
|---|---|---|
| R1 cost | PARTLY | Leaderboard: 32 calls, `$0.1402`, not a measured per-message chat cost. Live path is F5. |
| R2 instant triples | CONFIRMED | `models.py:19` has no `thing`. `models.py:26-28` has no buys/wants/likes/visits. No code extractor. |
| R3 who/where | CONFIRMED | Alias table `db/schema.sql:53-63`. Not exercised by T2b (no alias rows inserted). |
| R3 why | CONFIRMED | `why_fact` starts at `api/vault.py:579` and returns evidence records, not a because-field. |
| R3 contradict/update | CONFIRMED | `LEADERBOARD.md:10` column `6/8`. |
| R3 retrieve | PARTLY | 10k cap and slow `context_pack` are real (F3, T3). The "11 sites" count is 12. MCP search also loads 1,000 rows. |
| R3 story | CONFIRMED | Timeline route is a dated list (`api/vault.py` around the `/timeline` handler; plan cites `:287`). No narrative route. |
| R4 Subjects | CONFIRMED | `LIFE_SPINES` at `api/vault.py:337-338`. No `/vault/graph`. |
| R4 People & Places | CONFIRMED | `closeness_tier` is read (`graph_store.py:440`, `vault.py:171`) and never assigned in an INSERT/UPDATE in `src/`. |
| R5 provenance | PARTLY | Relabel is real (F4). Third-party people are not auto-promoted. |
| Backfill hygiene | CONFIRMED | String-prefix vs owner timezone, and no per-day size cap (F8). |

## 4. T-1 validity

Trust, as measurements of this run only:

- Smoke at `e05371f`: `proof/temporal_note/version.txt` and `RESULTS.md` §1. I did not re-smoke.
- T3, from `raw/temporal_note/t3_latency.txt` (schema `audit_bench_e32d316d`, then dropped by that script): warm p50/p95 `26/27`, `175/182`, `287/308` ms at 1k/5k/20k. Needle at 20k is miss/miss/hit. Postgres FTS `0.8 ms`.
- T2b arithmetic. Recomputed from `raw/*/t2b_results.json`: temporal_note top-8/16 `0.607/0.644`; mem0 `0.535/0.668`; both means use 38 probes.

Do not trust:

- "Facts held equal" as equal retrieval machinery. Same 110 texts. temporal_note had no gold entities or aliases (`run_tn_t2b.py:49-58`). mem0 stored `metadata.fact_id` and searched embeddings with `infer=False` (`run_t2b_equal.py:43-55`).
- Coverage as a judge. `score_hits` intersects `gold_context_fact_ids` with returned ids (`run_tn_t2b.py:23-33`).
- "temporal_note stays" (`RESULTS.md` §6). T2b was not run on the other two engines (`NOT_TESTED.md`). T1, T4, end-to-end T2, and Forget on temporal_note were not run. p50 `11.7 ms` is the 110-fact pack, not the 20k pack.
- Sensitive coverage. Scoring those probes rewards retrieving the gated fact. Top-16 leaks for temporal_note include t35 family health, t36 a third party's private matter, t37 a credential, t38 family health.

Per-bucket top-8 / top-16 (temporal_note, then mem0). Leak column is probes with any top-16 `must_not_contain` hit.

| bucket | n | tn 8 / 16 | tn leaks | mem0 8 / 16 | mem0 leaks |
|---|---:|---|---:|---|---:|
| person | 7 | 0.631 / 0.667 | 2 | 0.595 / 0.750 | 1 |
| person_alias | 3 | 0.889 / 0.889 | 2 | 0.778 / 0.889 | 2 |
| twohop | 8 | 0.906 / 0.938 | 2 | 0.688 / 0.938 | 2 |
| contradiction | 10 | 0.680 / 0.680 | 10 | 0.700 / 0.780 | 10 |
| arabic | 6 | 0.264 / 0.306 | 3 | 0.167 / 0.306 | 3 |
| sensitive | 4 | 0.083 / 0.250 | 4 | 0.083 / 0.083 | 4 |
| noise | 2 | excluded | 0 | excluded | 0 |

Arabic is the weak retrieval bucket. Contradiction top-16 returns the old value on every probe (the harness treats that as a leak). Two-hop looks strong only because the fact texts already contain both names; no edge was stored.

## 5. Per-WP notes

**U1 — M. Contract: new `GraphStore` search methods.** Include the 12th site and `memory_search`'s 1,000-row load. Simpler path: SQL `ts_rank` + alias join + date, `LIMIT` the candidates, RRF in Python. T3 already shows that GIN hits the old fact in 0.8 ms while the load-all pack misses it. That is the retrieval fix. Do not wait for U4 to find the needle.

Graph schema that can draw both views without inventing nodes:

- `center`: `{id: owner, label: display_name}`.
- `nodes[]`: `{id, kind: subject|person|place|org, label, count, tier: T1|T2|T3|null, provenance, as_of, noticed: bool}`.
- `edges[]`: `{src, dst, rel, fact_ids[], provenance, as_of}`.
- `counts`: `{shown, people, places, relations, more_by_cluster}`.
- Cap each cluster. `more_by_cluster` is the "+N more" number, not a fake node. The client draws the T1 ring from `tier == "T1"`.

p95 `< 150 ms` at 20k is plausible for a capped SQL aggregate (FTS was 0.8 ms) and is not measured for this payload. Current pack p95 is 308 ms (`t3_latency.txt`).

**U2 — M. Contract: additive `EntityKind` and either new `LinkRel` values or fields on `Fact`.** `entities.kind` and link `rel` are unconstrained `TEXT` (`schema.sql:40`, no CHECK). Prefer fields on `Fact` (`action`, `object`, `polarity`, `because`) over a new entity kind: Forget, `visible_facts`, and `content_hash` already apply to facts. A `thing` entity splits the same claim across a row the applier does not yet know.

A lexicon will not reliably emit `person → buys → iPhone`. The 40 probes contain no "buy" sentence. They do contain the failure classes: negation is absent but the same matcher would need it; plans and updates (`t11` "moved again", `t14` "starts Dec 1 now"); questions (`t21` "Can Sherif intro me"); third party vs user (`t02` Salma asked, `t10` Khalid scored); noise (`t39` `ok`). Arabizi (`t30`, `t32`) is where top-8 coverage is already 0.264. Precision is **unmeasured**. I would not ship without a labelled set that scores negation, question, future, third-party, and sarcasm as true negatives. Expect the first lexicon, with no speaker or polarity filter, to be wrong on those classes often enough that R5 fails.

**U3 — S.** One timezone function used by triage and `split_import`. A token cap that splits a day into more than one `extract.day` job. The `8/8` target replays the month harness; it does not prove live triples. Dedup a live triple against the later backfill by `content_hash`, or the parallel U2/U3 order writes the same action twice.

**U4 — L, and not required for the needle.** Local embeddings are a second channel for the Arabic and paraphrase gap (top-16 0.644 vs 0.668 on this unequal setup). Measure U1 first. If Arabic top-16 is still bad, add embeddings. Held-back text must not be embedded. `forget.py` must delete the vector in the same transaction. Backfill cost is not in this run (`NOT_TESTED.md`: the multilingual LM Studio endpoint was offline).

**U5 — S, after the filter in F2.** "Why" stays `/why/{id}` plus an optional `because` span copied from the source record, not a new model guess. "Tell a story" is one call over a retrieved timeline, every sentence tied to a fact id, cache keyed by `facts_version` **and** owner generation. Drop any citation that is not in the retrieved set. That is the cheap safe version. An unconstrained narrative is not.

**U6 — S, but it is the Rule 9 gate for the graph.** A Health cluster on the JPG (`INDEX.md:125`) is a leak surface if inferred gym/sleep/illness nodes are drawn. Inferred edges render as "I noticed" and do not count toward the verified checkmarks. Family, faith, and health nodes appear only when `provenance` is `user_supplied` or `provider_confirmed` after an explicit confirm.

**U7 — M.** Rewrite the harness before calling the new numbers a gate. Per-bucket table is mandatory. Add live-triple probes. Do not average away noise and sensitive.

Order: U1 (with bridge and MCP) → U6 filter → U2/U3 → remeasure → U4 only if a bucket fails → U5 → U7. U4 in parallel with U1 spends the backfill before you know FTS was enough. U5 in parallel with U6 can narrate t35–t38.

## 6. Founder decisions

- **D-a.** Keep the engine's seven spines in the API. The JPG's six and `INDEX.md:197`'s seven disagree, and Health as a default cluster fights Rule 9. Map Gaming under Events or Learning until someone confirms a Gaming subject. Do not invent a Health galaxy from inferred facts.
- **D-b.** Code-only for the live triple, and keep the existing one Haiku call per day packet for the correction. A per-session Haiku or a local Qwen adds a cost this run did not measure, and the lexicon's errors should be fixed by the backfill, not by a second model on every conversation.
- **D-c.** T1 only when the user sets it. Frequency and recency would infer closeness, including family, which Rule 9 does not allow. Show no T1 ring until at least one tier is user-confirmed.

## 7. Not checked

- I did not re-run pytest, T3, or T2b, and I did not open Postgres. T3's own log says it dropped `audit_bench_e32d316d`. I created no schema.
- I did not re-sum `calls.jsonl`, so the `$0.0045` per packet figure stays "about `$0.1402` / 32 calls".
- I did not read the JPG pixels. Cluster counts are from `INDEX.md`.
- Live-triple precision is unmeasured. No throwaway script was kept; the two Python aggregations ran in the shell.

## Commands

- `git -C G:\Haitham\VsCode\contest-memory rev-parse HEAD` → `e05371f52c40a94e97e053a3b9d390cfde5465bf`
- `git -C G:\Haitham\VsCode\contest show ios:apps/mobile/src/features/vault/vaultApi.ts`
- Python aggregation of `raw/temporal_note/t2b_results.json` and `raw/mem0/t2b_results.json` (means and per-bucket leaks)

Edited nothing outside this file. No repo or worktree was modified. No temporary schema was created.
