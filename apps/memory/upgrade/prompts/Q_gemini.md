# Q_gemini — your full queue for the temporal_note upgrade

Paste everything below the line into **Gemini** once. It contains all your work; there are no follow-up prompts.

---

## The goal

Upgrade **temporal_note** (`apps/memory/`, branch `memory`) so it powers the founder's **Knowledge Graph Vault** (`G:\Haitham\VsCode\contest\design\20-11-2026\Dubai-io Knowledge Graph Vault.jpg`, but with **the engine's 7 clusters**). It must be:
- cheap (R1);
- instant in conversation (R2, "person → buys → iPhone");
- deep in backfill: who / where / why / contradict / update / retrieve / story (R3);
- able to draw the graph (R4);
- truthful under Rule 9 (R5);
- able to remember places and topics (R6).

**Read first, fully:**
1. `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\TN_UPGRADE_PLAN.md`: the whole plan, v1, including §2b blockers, §3b baseline, §6 gates, §7 founder decisions.
2. `prompts\B0_common_rules.md`.
3. `G:\Haitham\VsCode\contest\CLAUDE.md` rules 1, 2 and 9.
4. `acceptance\BASELINE.md`.

## The team (everyone has this table)

| Agent | Queue, in order |
|---|---|
| **Gemini** (you) | **0** rerun the acceptance harness on `memory` → **1** U1c → **2** U5 → **3** U7 (harness reruns after every merge) |
| **Cursor** | 1 U1b → 2 U3 → 3 UI (mobile) |
| **Codex** (slow, half volume) | 1 U0c → 2 U2 |
| **Claude** (integrator) | verifies each WP (Postgres tests + your harness), merges into `memory` / `ios`, pushes, writes reviews |
| Other PC, shared lead | CS-1 (Community/Messenger bridge tests in live mode) |

Already merged: U0a, U1a (`memory` @ `267b0cf`). Specs live in `prompts\<WP>_*.md`.

## How to work (no waiting, no follow-ups)

- **One branch and worktree per WP,** from the latest `memory` (see each spec). Commit only on your branch. **Never merge into `memory`, `ios` or `main`, and never push them;** Claude does that.
- **Before each WP, check its dependencies are merged:** `git -C G:\Haitham\VsCode\contest merge-base --is-ancestor <dep-branch> memory`.
  - If one isn't merged yet, do the parts that don't need it, or go to your next WP whose dependencies are met.
  - **Never build on another agent's unmerged branch.**
  - You *may* stack your next WP on your own unmerged branch; say so in the report.
- **When a WP is done:** write `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\reports\<WP>.md` (branch, commit, files, test counts fake/Postgres, gate numbers, contract requests). Append one line to `reports\STATUS.md`: `<date time> | <WP> | gemini | <branch> | <commit> | ready-for-review`. Then **start your next WP immediately**.
- **At the start of every WP,** check `reports\*.review.md` for your earlier WPs. If Claude asked for fixes, fix them on that WP's branch first and note it in `STATUS.md`.
- **Tests run on Postgres** (the compose DB `:5442`, temporary schemas dropped with autocommit), not only on the fake store. Synthetic data only. Never touch `apps/web`, and never edit `G:\Haitham\VsCode\contest` (main).
- **Sub-agents:** at most 3, **lower Gemini tier only** (you are the lead). Re-run anything they claim.

## Your queue

**0. Rerun the acceptance harness on `memory`** (`acceptance\run.ps1 267b0cf`). U1a + U0a are merged, so S3 (Forget) and S4 (bridge on Postgres) should now pass. Write `reports\U7_267b0cf.md` with the pass/fail per suite vs plan §6 and the before → after against `e05371f`. Quick.

**1. U1c — Postgres retrieval everywhere + `/vault/graph`.** Spec: `prompts\U1c_sql_retrieval_and_vault_graph.md`. Dependencies: U0a ✅. Save **a sample `/vault/graph` response for both views** in `reports\U1c.md`: Cursor builds the phone UI against it.

**2. U5 — why + story.** Spec: `prompts\U5_why_and_story.md`. Dependencies: U1c (yours) + U0c (Codex). Also switch `api/vault.py` / `live/context.py` to `models.CLUSTERS`.

**3. U7 — acceptance reruns (ongoing).** Whenever `memory` gets a new merge (`git log memory`), run `acceptance\run.ps1 <commit>` and write `reports\U7_<commit>.md`. Build out the suites as features land:
- **S6** graph, after U1c;
- **S7** live-triple traps, after U2: hard gate, every `no_triple` and `quarantine` item emits nothing;
- **S8** places & topics, after U2 + U3;
- **S9** why / story, after U5.

Claude uses these reports as the merge gate. Never claim a number a run didn't produce.
