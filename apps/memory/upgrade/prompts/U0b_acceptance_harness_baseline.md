# U0b — Acceptance harness + honest baseline (outside the repo; parallel with U0a)

Suggested agent: **Gemini**. Its audit ablation (the gold graph in Postgres) is the starting point. Any agent may take it.

Paste below the line.

---

You build the **acceptance test** that every temporal_note work package is measured against. Measuring *is* your job here. Read:
- `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\TN_UPGRADE_PLAN.md` v1: §1 (R1–R6), §3, §6 (gates) and §7;
- the audits `tn_upgrade_audit_{codex,cursor,gemini,deepseek}.md`, especially what was wrong with T-1.

**Work only in `G:\Haitham\lab-data\memory-bakeoff\acceptance\`.** Never edit any repo or worktree. You *run* temporal_note at a given commit; you don't change it. Synthetic data only (`gold/`).

**Sub-agents:** at most 3, cheap tier only: Gemini → a lower tier, Codex → gpt-6.2 sol, Muse → Muse 1.3 Contributor, Cursor → its fast model. Re-run anything a sub-agent reports before you trust it.

## Fix what made T-1 invalid

- **Load a real graph.** Two modes:
  - **(gold)** load the gold entities, aliases, subjects, links and `text_orig`;
  - **(extracted)** run `apps/memory`'s **own** worker over the `month` corpus. That's real extraction through its runner: Haiku via the subscription hook, or `TM_WORKER_RUNNER` as configured. Record the model.
- **Sensitive facts follow the engine's own gate;** superseded facts are kept as history, not active.
- **Leaks count as failures.** Report results per bucket: person, person_alias, contradiction, two-hop, Arabic, sensitive, noise. Score the noise probes (they should return nothing relevant) instead of dropping them.
- **Latency over authenticated HTTP**, n ≥ 100 per scenario, p50 / p95 / p99, at 1k / 5k / 20k facts, warm and cold, **and while a writer is applying facts**. Record the hardware.
- **Temporary schemas** are dropped with autocommit. Also drop the schemas T-1 leaked: `t2b_tn_*` and `smoke_*`, only after checking they are T-1's.

## Suites (each produces pass/fail against plan §6)

| Suite | What |
|---|---|
| S1 retrieval | The 40 gold probes in both modes: top-8 / top-16 per bucket, leaks, plus the 20k old-fact needle. Use `context_pack`, `/search` and MCP `memory_search` (three separate paths). |
| S2 extraction + cost | Month run on `apps/memory`'s worker: fact recall / precision, people + duplicates, edges; changes as **8 superseded + 4 ended + 4 late**; privacy false positives on clean gold facts. **Cost per original owner-day: mean, p95, max.** |
| S3 Forget | Forget one source and one fact ID (through the bridge and directly). Assert 0 survivors across facts, entities, aliases, links, counts, the warm `context_pack` cache and `/why`, with a job in flight. |
| S4 bridge on Postgres | Start the real API on Postgres. Run `contest-shared`'s `apps/api/tests/test_memory_bridge_*.py` HTTP contract suite against it (worktree `G:\Haitham\VsCode\contest-sub-contest-shared`, read-only) using the real `HttpTemporalMemoryClient`. Also `POST /records`, `/facts/{id}/resolve`, and source-prefix search. |
| S5 Rule 9 surfaces | No sensitive or inferred-as-`user_supplied` item on any surface: vault subjects/people/quests/hypotheses/timeline/why, context, export, MCP. Includes the quarantined-fact → entity/link leak (Codex F01) and the auto-promoted place → `user_supplied` case (Codex F05). |
| S6 graph | Once `/vault/graph` exists: p95 at 20k, true counts, `+N more` = hidden-authorized only, no orphan edges, T1 only when confirmed. Until then: **NOT YET BUILT**. |
| S7 live-triple trap set | Write a **labelled set** (≥ 80 items) in EN / Arabic / Arabizi. Positives: "I bought an iPhone yesterday", "booked Zuma for Friday", "had dinner at Zuma in DIFC, loved it". Traps: negation, questions, plans, third party, quoted text, sarcasm, code-switching. Each item lists the expected triple or "no triple". Scored once U2 exists; until then **NOT YET BUILT**. |
| S8 R6 places & topics | A restaurant mentioned once with a lasting signal can be retrieved by name, by area and by the word "restaurant". A topic asked about in 2 separate sessions gives exactly one "I noticed"; asked once, none. Until U2/U3: **NOT YET BUILT** (record today's behaviour). |
| S9 why / story | Every claim cites a visible evidence span; unknown reason → "unknown". Until U5: **NOT YET BUILT**. |

## Deliverables (`acceptance\`)

- `run.ps1 <commit>`: runs everything against a given `memory` commit and writes `results\<commit>-<time>\`.
- **`BASELINE.md`** for **`e05371f`**: one table per suite, every number linked to raw files, and a pass/fail column against plan §6. Most suites are expected to fail today; that is the point.
- `TRAPS.md`: the S7 labelled set and how it's scored.
- `NOT_TESTED.md`: what couldn't run, and why.

**Never claim a number a run didn't produce. "Not yet built" and "not measured" are valid cells.** Report: the paths, the headline pass/fail per suite, the cost of the S2 run, and any engine bug you hit (with file:line; don't fix it).
