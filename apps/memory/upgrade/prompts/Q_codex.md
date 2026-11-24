# Q_codex — your full queue for the temporal_note upgrade

Paste everything below the line into **Codex** once. It contains all your work; there are no follow-up prompts. Your queue is deliberately half the size of the others'.

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
| **Codex** (you) | **1** U0c → **2** U2 |
| **Gemini** | 0 harness rerun → 1 U1c → 2 U5 → 3 U7 (harness reruns after every merge) |
| **Cursor** | 1 U1b → 2 U3 → 3 UI (mobile) |
| **Claude** (integrator) | verifies each WP (Postgres tests + Gemini's harness), merges into `memory` / `ios`, pushes, writes reviews |
| Other PC, shared lead | CS-1 (Community/Messenger bridge tests in live mode) |

Already merged: U0a, and your U1a (`memory` @ `267b0cf`; verified 343 → 348 passed). Specs live in `prompts\<WP>_*.md`.

## How to work (no waiting, no follow-ups)

- **One branch and worktree per WP,** from the latest `memory`. Commit only on your branch. **Never merge into `memory` or `main`, and never push them;** Claude does that.
- **Before each WP, check its dependencies are merged:** `git -C G:\Haitham\VsCode\contest merge-base --is-ancestor <dep-branch> memory`. **Never build on another agent's unmerged branch.** You *may* stack U2 on your own unmerged U0c branch; say so in the report.
- **When a WP is done:** write `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\reports\<WP>.md` (branch, commit, files, test counts fake/Postgres, gate numbers, contract requests). Append one line to `reports\STATUS.md`: `<date time> | <WP> | codex | <branch> | <commit> | ready-for-review`. Then **start your next WP immediately**.
- **At the start of every WP,** check `reports\*.review.md` for your earlier WPs. If Claude asked for fixes, fix them first.
- **Tests run on Postgres** (the compose DB `:5442`, temporary schemas dropped with autocommit), not only on the fake store. Synthetic data only. Never touch `apps/web`, and never edit `G:\Haitham\VsCode\contest` (main).
- **Sub-agents:** at most 2, **gpt-6.2 sol only**. Re-run anything they claim.

## Your queue

**1. U0c — remove your U1a runtime DDL + contract v2** (triple fields, reason span, `place_type`, topic counter, the one 7-cluster taxonomy). Spec: `prompts\U0c_cleanup_and_contract_v2.md`. Dependencies: U0a ✅, U1a ✅. **Do this first and keep it tight:** U2, U3 and U5 all build on its names.

**2. U2 — instant triples + topic counter + per-session catch-up** (local Qwen first, Haiku fallback). Spec: `prompts\U2_instant_triples_topics_session.md`. Dependencies: U0c (yours) + U1b (Cursor). Its hard gate is the acceptance trap set (`acceptance\TRAPS.md`): every `no_triple` and `quarantine` item emits nothing.
