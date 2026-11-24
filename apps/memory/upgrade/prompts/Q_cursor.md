# Q_cursor — your full queue for the temporal_note upgrade

Paste everything below the line into **Cursor** once. It contains all your work; there are no follow-up prompts.

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
| **Cursor** (you) | **1** U1b → **2** U3 → **3** UI (mobile, branch `ios`) |
| **Gemini** | 0 harness rerun → 1 U1c → 2 U5 → 3 U7 (harness reruns after every merge) |
| **Codex** (slow, half volume) | 1 U0c → 2 U2 |
| **Claude** (integrator) | verifies each WP (Postgres tests + Gemini's harness), merges into `memory` / `ios`, pushes, writes reviews |
| Other PC, shared lead | CS-1 (Community/Messenger bridge tests in live mode) |

Already merged: U0a, U1a (`memory` @ `267b0cf`). Specs live in `prompts\<WP>_*.md`.

## How to work (no waiting, no follow-ups)

- **One branch and worktree per WP,** from the latest `memory` (or `ios` for the UI). Commit only on your branch. **Never merge into `memory`, `ios` or `main`, and never push them;** Claude does that.
- **Before each WP, check its dependencies are merged:** `git -C G:\Haitham\VsCode\contest merge-base --is-ancestor <dep-branch> memory`.
  - If one isn't merged yet, do the parts that don't need it (U3 Part A needs nothing), or go to your next WP whose dependencies are met.
  - **Never build on another agent's unmerged branch.** You *may* stack your next WP on your own unmerged branch; say so in the report.
- **When a WP is done:** write `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\reports\<WP>.md` (branch, commit, files, test counts fake/Postgres, gate numbers, contract requests). Append one line to `reports\STATUS.md`: `<date time> | <WP> | cursor | <branch> | <commit> | ready-for-review`. Then **start your next WP immediately**.
- **At the start of every WP,** check `reports\*.review.md` for your earlier WPs. If Claude asked for fixes, fix them on that WP's branch first and note it in `STATUS.md`.
- **Tests run on Postgres** (the compose DB `:5442`, temporary schemas dropped with autocommit), not only on the fake store: B-M's bridge passed on the fake store and returned HTTP 500 on Postgres. Synthetic data only. Never touch `apps/web`, and never edit `G:\Haitham\VsCode\contest` (main).
- **Sub-agents:** at most 3, **Cursor's fast model only**. Re-run anything they claim.

## Your queue

**1. U1b — no leaks from quarantined facts + stored provenance + T1 suggestions.** Spec: `prompts\U1b_applier_leaks_and_provenance.md`. Dependencies: U0a ✅.

**Already started:** a previous agent ran out of quota mid-way. **Read `reports\U1b.handoff.md` first.** Continue in its worktree `G:\Haitham\VsCode\contest-mem-wpU1b` (branch `mem-wpU1b`): it's already fast-forwarded to `memory` @ `267b0cf`, with the venv installed. Its analysis of the 3 false positives (`f039`, `f045`, `f109`) and of the e2e masks is done; no code has been written yet.

**2. U3 — backfill quality.** Spec: `prompts\U3_backfill_quality.md`.
- **Part A (the diagnosis of why the shipped extractor scores 66.7 % recall / 59 % precision / 1 of 8 changes) needs nothing.** You may do it while waiting for U1b's review.
- Part B needs U1b (yours) + U0c (Codex).

**3. UI — the mobile Memory Vault on `/vault/graph`** (branch `ios`). Spec: `prompts\UI_vault_graph_mobile.md`. Dependency: U1c (Gemini), whose `/vault/graph` sample is in `reports\U1c.md`.
