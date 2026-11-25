# Handoff: the integrator role, from Claude to Gemini (Neon), 25 Nov 2026

You are now the **integrator** for the contest monorepo at `g:\Haitham\VsCode\contest`. That means you plan, write agent prompts, verify branches, merge them into `main` and push. Under D16 you may merge gated work into `main` and push it.

Read first: root `CLAUDE.md`, `apps/memory/CLAUDE.md`, `apps/memory/upgrade/reports/MORNING.md` (§E open issues, §F housekeeping), and `docs/submissions/shared/founder-decisions.md` (D16–D18).

## Hard rules (unchanged)

- **`apps/web` is frozen.** Before every merge, run `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web`; it must exit 0.
- **Protected references:** never delete or move `docs/plan/Memory/_archive/**` or `design/references/quest/**`.
- **No new top-level `*.md` files.**
- **No force-push.** Never stage these 3 untracked founder files in main:
  - `design/20-11-2026/Dubai-io Quest Milestones Showcase.jpg`
  - `docs/Researches/new tools research.md`
  - `docs/plan/Memory/deepseek_markdown_20261124_fbeb70.md`
- **Deletions are the founder's call.** That covers worktrees, branches and `docs/submissions/shared/canon-patches/`. Nothing gets deleted without the founder.
- **D18:** the founder said "I only allow lower weights, not forget". New work adds **no delete paths**; weights go down to the floor. Don't remove the existing Forget (E8) until the founder chooses (a) or (b) below.
- **Self-review:** E10 is your own build as the Gemini builder, so give it an independent verification pass (a separate sub-agent), not a self-review.

## State of `main`: 2b03c6f (pushed)

- 5c67119: E10/E11 prompts and D17.
- ea8919d: D18, with E10 §4 rewritten so nothing is deleted.
- 0fd304d: the E12 prompt.
- 2b03c6f: doc-audit pass 2, merged (6 fixes plus dated "superseded" notes).
- **Status board:** `apps/memory/upgrade/reports/STATUS.md`.

## The integration queue, in order

1. **E11a (Codex)**
   - Local only, branch `e11a/temporal-fixes`, worktree `G:/Haitham/VsCode/contest-e11a`, commits 2d6af51 and 722aa37. **Verified: MERGE.**
   - Tests: memory 524 passed, 8 skipped, 0 failed, with Postgres. Scope is clean: `validator.py`, and `_late_superseder` with its helpers in `applier.py`.
   - S2 shows no drop against main on identical inputs: base and branch both score 5/8 or 6/8 depending on the judge run, with 5/5 ended and 3/4 late. The 7/8 superseded target is still unmet; record that as open.
   - The merge conflicts only in `STATUS.md`. Keep both sides' lines.
   - Push the branch first if you want a remote copy, then `git merge --no-ff`, run the gate, and push main.
2. **E11b (Devin), PR #7, branch `e11b/review-fixes`** (local worktree `G:/Haitham/VsCode/contest-e11b`, 61f230d)
   - **Verified by Claude: MERGE.**
     - **Conflict:** only `STATUS.md`, so keep both sides.
     - **Scope:** clean. The `applier.py` change is a single line, the `ensure_embeddings` call site. It doesn't touch `_late_superseder` or E10's files.
     - **Each item:** B1–B6 are all OK, with happy-path and failure-path tests.
     - **Tests:**
       - `apps/api`: 671 passed, 16 skipped.
       - Messenger: memory tests pass (MEMDOM 13/13), and typecheck is clean.
       - Desktop: 32/32 passed.
       - `apps/memory`, run with the api venv: 453 passed and 4 failed. All 4 failures happen because that venv lacks `onnxruntime`, and 3 of them fail the same way on main. Rerun once in the full memory venv (`contest-memory`, which has `mcp` and `onnxruntime`) to confirm Devin's count of 482 passed, 8 skipped.
     - **Follow-ups for Devin:** low priority, so fold them into E12's PR.
       - `test_failed_model_load_is_cached_for_backoff_window` should stub `onnxruntime` or use `importorskip`.
       - B1's `_PENDING` queue should recheck that a fact is not quarantined before embedding it.
     - The checklist below shows what was checked.
   - Check B1–B6 against `prompts/E11_review_fixes.md` Part B:
     - B1, `core/embed.py`: embedding continues across calls until done; the version is marked done only at the end; there is a time budget; the model never loads in a user request; a failed load is cached with backoff.
     - B2: pairing consumes the code before issuing the session, in one transaction.
     - B3: `privacy/sensitive.py` `_agent_cli_classifier` sends an item with a number but no category to screening.
     - B4: the Messenger approval-card click-through test.
     - B5: the warning for desktop `DUBAI_APP_URL`.
     - B6: the PID-reuse check in `stop-all`.
   - **Watch:** the branch also changes `core/applier.py`, `api/app.py` and `STATUS.md`. `applier.py` was not assigned to Devin. Merge E11a first, then check that the E11b applier hunk doesn't touch `_late_superseder` or the E10 new-terms area.
   - Run the suites listed under "Test recipes" below.
3. **E10 (Gemini), `e10/topic-tree`**
   - Spec: `prompts/E10_topic_tree.md`, which records D17, and its §4 uses D18 weights.
   - Check:
     - the fixture names (`fitzone`, `peakform`, `autohub`, `camry`, `testflight`, `الوكلاء`) are **gone** from the curated data;
     - learned terms are scoped per owner;
     - there are no delete paths;
     - the 150 ms p95 gate at 20k facts still holds;
     - S1 and S2 are reported for each probe;
     - the cost change is reported against $0.00517 per day;
     - `models.py` changed only for `NewTerm` and `new_terms`.
   - Then the E6 rerun, which writes `reports/U7_post_E11.md`.
4. **E12 (Devin), `e12/community-wiring`.** The prompt was sent to Devin on 25 Nov.
   - Spec: `prompts/E12_community_wiring.md`.
   - Check:
     - the feed calls `getFeed()`;
     - fixtures appear only when signed out or offline, with the `Demo data` pill;
     - the two-user Playwright end-to-end test passes;
     - `apps/api/app/community/**` is untouched (it is read-only for Devin).

## Test recipes (learned the hard way)

- **`apps/memory`:**
  - Run `python -m pytest -q` with `TM_TEST_DATABASE_URL=postgresql://tm:tm@localhost:5442/tm`. The container is `temporal-memory-postgres-1`.
  - Agent worktrees have no `.venv`. Use `G:/Haitham/VsCode/contest-memory/apps/memory/.venv` with `PYTHONPATH=<worktree>/apps/memory/src`.
- **`apps/api`:**
  - Run it from the branch worktree, not the main checkout. In main, `apps/api/.env` `DATABASE_URL` causes about 14 false Postgres timeouts.
  - Venv: `g:/Haitham/VsCode/contest/apps/api/.venv`. It may import the engine from the main checkout; note that in the review.
- **S2:** `acceptance/run_s2_replay.sh` uses an LLM judge (subscription calls), and its scores move between judge runs. Compare base and branch with the same judge pass.
- **Don't** run `git checkout` in the main checkout to test other commits. Use `git worktree add --detach <path> origin/main` and remove the worktree afterwards.

## Decisions still with the founder (ask; don't decide)

1. **Forget (D18):**
   - (a) replace Forget everywhere with "Lower": the weight drops to the floor, the item leaves chat and cards, and it stays visible in memory; or
   - (b) do (a), plus keep one account-level "Delete my data" for legal erasure requests (UAE PDPL; YouTube API revoke).
   - Claude recommended (b). Rule 9 in `CLAUDE.md` and `ARCHITECTURE.md` §7 still list Forget, so change them only after the choice.
2. **Canon patches:** archive the 4 `canon-patches/*.patch.md` drafts? Should `ARCHITECTURE.md` gain the shared-identity and cross-app memory section from `ARCHITECTURE.patch.md`, which describes what E5 built? Should the NEVER list add `PLAN.patch.md`'s "Meta marks" and "Builder code"?
3. **Vocabulary (D17):** learned words are per user only. Should words that many users propose ever be promoted to the shared list?
4. **Community, not built:** reposts, hashtags, blocking and muting, a learned recommender (today's is rule-based keyword and follow scoring with "Why this?"), and separate consent for saved discussions vs public posts (§E #8).

## Still open (from MORNING §E)

- **Extraction cost** is $0.00517 per day against the $0.0044 target.
- **Today cards on real data:** at least 5 live cards, still not shown.
- **No real-phone end-to-end run** (§E #16).
- **The founder's real-data walkthrough** (MORNING §B) is not done yet.

## How to report to the founder

- Keep it short and plain, with no jargon.
- Give paste-ready prompts for agents, with each agent's full queue in one prompt and no follow-ups. Codex gets about half the volume. Muse is unavailable.
- Record every merge as a line in `STATUS.md`.
