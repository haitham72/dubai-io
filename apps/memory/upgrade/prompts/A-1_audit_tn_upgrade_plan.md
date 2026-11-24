# A-1 — Audit the temporal_note upgrade plan (any agent: Codex · Muse · Cursor · Gemini)

Paste below the line into each agent. Replace `<agent>` with `codex`, `muse`, `cursor` or `gemini`. Each agent audits independently and does not read the other agents' reports.

---

You are an **independent auditor**. Your job is to find what is wrong, missing, risky or more expensive than needed in a plan, with evidence. **This is read-only.** You write exactly one file: `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\tn_upgrade_audit_<agent>.md`, where `<agent>` is **your own tool's name in lower case** (codex, muse, cursor, gemini, deepseek, …), even if the prompt was pasted with another name. **If that file already exists, never overwrite it:** write `tn_upgrade_audit_<agent>-2.md` instead. (On 24 Nov a second auditor overwrote another auditor's report.)

## What you audit

1. **The plan:** `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\TN_UPGRADE_PLAN.md` (draft v0). It upgrades temporal_note so it powers the founder's Knowledge Graph Vault cheaply and fast.
2. **Its evidence:** Gemini's T-1 run in `G:\Haitham\lab-data\memory-bakeoff\realbench\20261124-0916\` (`RESULTS.md`, `GAPS.md`, `NOT_TESTED.md`, `raw/`, `proof/`, and the scripts beside them).

Read these too:
- the code: `G:\Haitham\VsCode\contest-memory\apps\memory\` (branch `memory` @ `e05371f`). Start with `CLAUDE.md`, `README.md`, `src/temporal_memory/models.py` and `db/schema.sql`;
- the target screen: `G:\Haitham\VsCode\contest\design\20-11-2026\Dubai-io Knowledge Graph Vault.jpg`, and its spec `design/20-11-2026/INDEX.md`;
- the mobile screens: `git -C G:\Haitham\VsCode\contest show ios:apps/mobile/src/features/vault/<file>`;
- the root rules: `G:\Haitham\VsCode\contest\CLAUDE.md`, especially rules 1, 2 and 9;
- the gold data: `memory-bakeoff/gold/` (`ledger.json`, `probes.json`, `README.md`).

## Hard rules

- **Read-only.** Don't edit, commit or push anything in any repo or worktree. Never edit `G:\Haitham\VsCode\contest` or `apps/web`.
- You **may** run things to check a claim: the memory test suite, the scripts in `realbench/`, SQL against the local Postgres on `:5442`. Do it **only in a temporary schema that you drop afterwards**, as `realbench/reference/tn_latency_bench.py` does. Put any throwaway scripts in `memory-bakeoff/audit_scratch/<agent>/`.
- **Synthetic data only.**
- **Every finding needs evidence:** a `file:line`, a command and its output, or a number from a run folder. A finding without evidence is marked `UNVERIFIED`.
- **No competitor comparisons.** The founder doesn't want Hindsight, mem0 or Honcho as targets. Judge only against the plan's requirements R1–R5.
- **Sub-agents:** at most 3, on the cheap model only: **Muse → Muse 1.3 Contributor** (never Wonder); **Gemini → a lower Gemini tier**, not Neo; **Codex → gpt-6.2 sol**; **Cursor → its fast model**. Re-check any sub-agent finding yourself before you write it down.

## Questions to answer

**A. Is the current-state table true?** Check every row of `TN_UPGRADE_PLAN.md` §2 against the code. In particular:
- Are there exactly 11 load-all `visible_facts(owner, limit=10_000)` sites, or more or fewer?
- Is `closeness_tier` really never written?
- Is the provenance bug (`api/vault.py:117,177,250`) real, and does it actually turn auto-promoted items into "You told me"?
- Does live chat really cost one LLM call per message?
- Are the day-boundary mismatch and the missing per-day size cap real?

Mark each row `CONFIRMED`, `WRONG` (say what is true) or `PARTLY`.

**B. Is the evidence valid?** For the T-1 run:
- Which numbers can be trusted?
- Was T2b really "held equal"? Did temporal_note get gold entities, aliases or subjects that mem0 didn't?
- How was coverage matched to gold facts: by ID or by judge?
- Is the "temporal_note stays" verdict supported by what was actually run?
- What is the **per-bucket** breakdown (contradiction, two-hop, person, Arabic, sensitive, alias, noise)? Compute it from `raw/` if it isn't reported.

**C. Does the design meet each requirement?** For R1–R5, say whether U1–U7 are enough, and what is missing. Specifically:
- **R2:** can a code-only extractor (alias index + action lexicon + things gazetteer) reliably produce `person → buys → iPhone` in **EN / Arabic / Arabizi**? Name the failure cases: negation ("didn't buy"), plans vs past ("going to buy"), questions, a third party vs the user, sarcasm. What is the honest precision you would expect?
- **R3:** how should "why" and "tell a story" work, and is U5 cheap and safe (citations, no invented facts)?
- **R4:** can `/vault/graph` produce both views exactly as in the design (centre node, clusters, counts, T1 ring, relation count, "+N more") at **< 150 ms with 20k facts**? What should the node and edge schema be?
- **R5:** where could the plan leak a sensitive or inferred item into the graph, the story or a live triple?

**D. Simpler or cheaper ways?** For each WP, name any simpler way to reach the same gate:
- Postgres-only alternatives;
- smaller models;
- fewer schema changes, e.g. triples as `Fact` fields vs new `LinkRel` values vs a `thing` `EntityKind`;
- whether the local multilingual embedding model (U4) is needed at all, or whether Postgres FTS + aliases + `text_orig` gets there.

Back each one with a measurement or a citation.

**E. Risks and order.** What breaks if U1–U6 land in the proposed order? Consider contract changes to `models.py`, migrations on existing data, re-embedding cost, Forget and the generation fence, the CR-TM bridge routes used by Community and Messenger (`api/bridge.py`), and the mobile `vaultApi.ts` contract.

**F. Are the gates right?** Is each gate in §5 measurable, and not invented? Propose missing gates, for example for the precision of live triples.

**G. Founder decisions.** For D-a, D-b and D-c, give your recommendation and why, in two lines each. The founder decides.

## Output format (`tn_upgrade_audit_<agent>.md`)

1. **Verdict, in 5 lines max:** is the plan sound, sound with fixes, or not sound?
2. **Findings table, most severe first:** `ID | severity (blocker / major / minor) | section (A–G) | finding | evidence | suggested fix`.
3. **§2 row check:** one line per row: `CONFIRMED`, `WRONG` or `PARTLY`, with evidence.
4. **T-1 validity:** which numbers stand, and which don't; plus the per-bucket table.
5. **Per-WP notes (U1–U7):** missing steps, simpler alternatives, size (S/M/L), contract changes.
6. **Recommendations on D-a / D-b / D-c.**
7. **What you could not check, and why.**

Keep it under about 250 lines. Finish by listing the commands you ran, and confirm that you edited nothing outside `memory-bakeoff/` and dropped every temporary schema.
