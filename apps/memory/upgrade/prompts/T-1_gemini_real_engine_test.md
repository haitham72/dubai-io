# T-1 — Gemini: real head-to-head of temporal_note vs Hindsight vs mem0 vs Honcho

Paste below the line into **Gemini** (a fresh session; you are the test lead, not a builder).

---

## Why this test exists

The founder must choose between two routes, using real numbers:
- **Route A:** adopt Hindsight (+ Honcho).
- **Route B:** upgrade our own engine, temporal_note.

**Every previous comparison was invalid.** In `memory-bakeoff/runs/*hindsight*`, real Hindsight produced **115 memories**. The harness (`weekbench/configs/hindsight.py`) had told it to end every fact with a custom `[[policy=…; ids=…]]` tag. Hindsight doesn't produce that tag, so the converter dropped all 115 as "unclassified" and scored Hindsight **0%**. Its graph export was also empty. **mem0 was never run.** **Search quality was never measured for any engine.** Your job is to produce the first honest comparison.

## Hard rules: what makes a result count

1. **Real engines only.** Use the official image or package for each engine, at a pinned version. No mocks, stubs, fakes, simulated responses or re-implementations (including `FakeTemporalMemoryClient`). No "adapter that imitates" an engine. If an engine can't be installed or run, **stop and report the blocker**. Never substitute something for it.
2. **Prove each engine works before scoring it.** Save in `proof/<engine>/`:
   - the version, image digest or `pip freeze`, and `docker ps`;
   - a smoke test: write 3 synthetic facts through the engine's own API, read them back through its own recall/search, and save the raw request and response JSON.

   An engine that fails its smoke test is **not scored**. Report it as a setup failure, not as 0%.
3. **Save the raw I/O.** Every engine call (request + response) goes to `raw/<engine>/*.jsonl`. Every LLM call goes to `llm/<engine>.jsonl` with the model, tokens in/out, latency and cost.
4. **Never force our format onto an engine.** Feed each engine through its own API with its own concepts. Map its output back to gold IDs:
   - **(a)** through native source fields where the engine supports them (Hindsight `document_id` / `metadata`, mem0 `metadata`, temporal_note `evidence`);
   - **(b)** otherwise, through **one blind judge**: the same prompt, model and temperature 0 for every engine, with the engine's name removed.

   Spot-check 10% of judge decisions by hand, and list any disagreements.
5. **Same inputs for every engine:**
   - the same synthetic corpus (`gold/`, persona "Karim");
   - the same ingest order (`gold/ingest_order.json`, including the 4 late records);
   - the same extraction LLM: **Claude Haiku via the subscription hook, medium effort**. Engines that need an OpenAI-compatible endpoint use `weekbench/hookproxy.py`. No Gemini API calls for extraction;
   - the same embedding model wherever the engine lets you choose (see Setup).

   Each engine also gets **one run with its own documented defaults**, labelled `defaults`.
6. **Synthetic data only.** No real personal data, ever.
7. **Repo:** never edit anything in `G:\Haitham\VsCode\contest` (main) or `apps/memory/`. You **run** temporal_note; you don't change it. All your code and results live in `G:\Haitham\lab-data\memory-bakeoff\realbench\`. Read `prompts/B0_common_rules.md`.
8. **Sub-agents:** lower Gemini tier only, at most 3. You re-run anything a sub-agent reports before you trust it.
9. **Never claim a number a run didn't produce.** "Not measured" is a valid cell.

## Setup (pin and record everything)

| Engine | Install | Notes from `research/libraries.md` |
|---|---|---|
| **temporal_note** | `G:\Haitham\VsCode\contest-memory\apps\memory` at commit **`e05371f`**, `docker compose up -d postgres rabbitmq redis api worker-p0 worker-p1 beat`. Import with the `tm import … --owner <id>` CLI. Workers run Haiku via the hook (`TM_WORKER_RUNNER` / CLI runner). | Search goes through `POST /v1/owners/{o}/context` and `GET /v1/owners/{o}/search`, plus the MCP `memory_search`. Test all three; they are different code paths. |
| **Hindsight** | Official `ghcr.io/vectorize-io/hindsight`, **v1.2.3 or later, pinned by digest**. A container is already on `:8788` from the old bakeoff: verify its version or recreate it. | Recall runs 4 channels (semantic + BM25 + graph + temporal), merged with RRF and reranked by `ms-marco-MiniLM-L-6-v2`. Default embeddings are English: do a defaults run **and** a multilingual-embedding run. Known issues: #6778 (reranks 300 candidates; record recall latency), #6767 (floods results). Feed with `retain_batch`, one item per record, `document_id` = record ID, plus `timestamp`. Wait for consolidation to drain before scoring. |
| **mem0 (open source)** | `pip install mem0ai==<pin>` in its own venv. Use **local Qdrant**, **not pgvector**: bug #7983 hard-codes 1536 dimensions. | The open-source version has no graph and no BM25 (graph is paid-cloud only); record that as a gap, don't work around it. Use `add(..., metadata={"record_ids": [...]})` and `search(query, filters={"user_id":…}, top_k=…)`; test both with and without its reranker. |
| **Honcho** | Official v3.6.1+ compose (`weekbench/docker/honcho.compose.yml`; a stack is up on `:8790`, so verify it). | AGPL licence. Its deriver uses an LLM per batch, and the dialectic uses 1–11 LLM calls per query. Score both its search and its dialectic at `low` level. |

**Embeddings for the "same model" run:** one multilingual model (Arabic + English) served on one OpenAI-compatible endpoint (for example LM Studio), used by Hindsight, mem0 and Honcho. Record its name and size. temporal_note has no embeddings today; that is one of the gaps you are measuring.

## Test suites

**T1 — Writing (extraction quality).** Run the `week1` and `month` corpora. Per engine, measure:
- fact recall vs `gold/ledger.json` (110 facts), and precision (true / noise / wrong);
- people found and duplicates, relation correct, edges found (out of 43);
- contradictions handled: is the current fact active and the old one ended or superseded? Include the 4 late records: older evidence must not overwrite newer;
- sensitive items leaked vs held.

Reuse the definitions in `weekbench/score.py` and `harness/score.py`, but feed them the normalized output of each engine. Check that the scorer has no temporal_note-specific assumptions.

**T2 — Search quality (the never-tested part).** On each engine's own memory from the T1 `month` run, ask all **40 probes** in `gold/probes.json`:
- Use the engine's native search, with top-k 8 and 16, a ~1.5k-token budget, and the probe's time as the query time wherever the engine supports one.
- Score **gold facts covered in the top 8 and top 16**, against `gold_context_fact_ids` / `context_memory_ids`, through native IDs or the blind judge.
- Score **per bucket:** contradiction 10, two-hop 8, person 7, Arabic 6, sensitive 4, person_alias 3, noise 2.
- Also report: `must_not_contain` leaks; items and tokens returned (flooding); for contradiction probes, whether the current fact ranks above the outdated one; for noise probes, whether irrelevant facts are returned.

**T2b — Search only, with the facts held equal (if possible).** Load the **same gold facts** directly into each engine (mem0 `infer=False`; Hindsight retain without extraction, if supported; temporal_note by direct database load as in `realbench/reference/tn_latency_bench.py`) and repeat T2. This separates search quality from extraction quality. Where an engine can't do this, write "not possible" and explain why.

**T3 — Speed.**
- Search latency p50 / p95, warm and cold, on the month corpus.
- At **1k / 5k / 20k facts**, using synthetic scale-up through each engine's cheapest no-LLM insert path. If an engine needs an LLM call per insert, cap the size by budget and report the cap.
- For temporal_note, also measure while a backfill is running.
- Also: ingest throughput (records per minute), and time until a new fact is searchable.

**T4 — Cost.** LLM calls, tokens in/out and API-equivalent dollars, for writing a week and a month of data and for each search, per engine. Include background work (Hindsight consolidation, the Honcho deriver and dialectic).

**T5 — Forget.** Delete one source (`whatsapp_family`):
- all facts derived from it must leave search results;
- they must not come back after consolidation, reflect or re-import.

Use each engine's native delete.

**T6 — Running it.** Containers, measured RAM (`docker stats`), disk, licence, behaviour when the LLM is down, and how many steps it took to install.

## Decision rules (already locked in `DECISION.md`; apply them exactly)

- **Hindsight replaces temporal_note** if it beats temporal_note by **+10 points** on facts or links (T1), **or on search coverage in the top 16 (T2)**, at **≤ 2× cost**.
- **Honcho is added** only if it is **+15 points** on profile and milestone questions vs temporal_note's weekly reflect.
- Otherwise temporal_note stays. Its T2/T3 gaps become its upgrade list, and this same harness is rerun after the upgrade.
- Privacy is a gate, not a score: **any engine that leaks sensitive items** in T1 or T2 must show it can be blocked (for example with Hindsight's `OperationValidatorExtension`) before it can win.

## Deliverables (`realbench/<YYYYMMDD-HHMM>/`)

- `proof/`, `raw/`, `llm/`, `normalized/`, `scores/<engine>.json`
- **`RESULTS.md`:** one table per suite, a per-bucket table for T2, and the decision-rule verdict. Every number links to its run folder.
- **`GAPS.md`:** for each engine, what it lacks vs each of the others. For each gap give the evidence (the probe IDs it missed, the latency, the cost) and its size. Write temporal_note's gaps as an upgrade list.
- **`NOT_TESTED.md`:** everything you couldn't run and why.
- `run.ps1`: one command that reproduces everything.

**Stop and report** (don't improvise) if an engine fails its smoke test, if the hook or proxy can't serve an engine, or if the corpus or probes look wrong.
