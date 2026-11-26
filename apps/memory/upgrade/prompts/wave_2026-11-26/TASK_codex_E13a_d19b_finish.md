# Task — Codex: Finish E13a (D19b Explicit-Recall Boost + Gates)

- **Agent:** Codex
- **Branch:** `e13a/lower-and-delete` (currently at WIP `b0785c3`)
- **Worktree:** `G:\Haitham\VsCode\contest-e13a`
- **Base / Target:** Rebase/merge onto `origin/main` (`e115077` or latest), open PR into `main`
- **Scope Note:** 57 files for D19 are already committed at `b0785c3`. Keep your remaining quota focused and surgical — finish **D19b**, verify **Google Limited Use**, reconcile `origin/main`, run all gates, and open the PR.

**Mandatory Reads First:**
- `docs/submissions/shared/founder-decisions.md` (**D19** and **D19b**)
- `apps/memory/upgrade/prompts/E13a_lower_weights_delete_my_data.md`
- `CLAUDE.md` (Rule 9, Google Limited Use, `apps/web` frozen)

---

## Step-by-Step Execution

### 1. Reconcile with `origin/main`
- Run `git fetch origin` inside `G:\Haitham\VsCode\contest-e13a` and rebase onto (or merge) `origin/main`.
- Carefully reconcile `apps/memory/src/temporal_memory/core/embed.py` with PR #9's `only_ids` + `facts_version` fixes (preserve both PR #9's lazy backfill/version fixes and E13a's cache clearing).

### 2. Verify & Implement D19b (100% Explicit Recall + Weight Boost)
Per `docs/submissions/shared/founder-decisions.md` **D19b**:
- Whenever the user explicitly triggers, searches, opens, or calls for a lowered or aged memory (`include_lowered=True`, explicit query, `/recall`, or Vault open):
  1. That memory MUST be **100% retrievable** (`include_lowered=True` / explicit-trigger path ignores the `0.10` passive surface threshold and `0.01` floor suppression).
  2. That explicit recall call MUST boost its weight:
     $$w_{\text{new}} = \min\big(1.0,\; \max(0.35,\; w_{\text{eff}} + 0.25)\big)$$
     and clear `lowered_at` + reset `last_refreshed_at` so it stays active again.
- Verify this across `apps/memory` (`core/retrieval.py`, `privacy/controls.py`, `api/vault.py`, `api/bridge.py`) and bridge/client paths (`apps/api/app/memory_bridge/**`, `apps/api/app/identity/**`).
- Add focused **unit + integration tests** verifying:
  - Passive `/context` / Today / recommendations still exclude lowered (`0.01`) and `< 0.10` memories.
  - Explicit trigger / `/recall` / `include_lowered=True` returns the lowered/aged memory 100% of the time AND updates weight to `min(1.0, max(0.35, w_eff + 0.25))`, clears `lowered_at`, and resets `last_refreshed_at`.

### 3. Verify D19 Google Limited Use Exclusion & Immediate Purge
Inspect `0008_memory_controls.sql`, `privacy/controls.py`, `api/bridge.py`, `api/vault.py`, and `apps/api/app/identity/router.py`:
- Confirm `training_backups` replaces owner UUID with salted hash / surrogate ID, scrubs PII (email, name, phone, tokens, credentials), and **excludes** all rows from `gmail`, `calendar`, `youtube`, `takeout_youtube`.
- Confirm **zero** public or bridge API routes can read `training_backups`.
- Confirm `"Delete my data"` purges owner Redis keys, clears in-process caches, revokes sessions/tokens, bumps owner generation/`facts_version`, and sets `deleted_from_external = true` so external queries return 0 rows / excluded immediately.
- Address any findings emitted by Claude's Phase A audit (`E13a` pre-audit) in one clean pass.

### 4. Run & Pass ALL Required Gates
Run inside `G:\Haitham\VsCode\contest-e13a`:
1. **`apps/memory` Postgres suite** (against `:5442` using `contest-memory` venv):
   - `$env:TM_TEST_DATABASE_URL="postgresql://tm:tm@localhost:5442/tm"`
   - `G:\Haitham\VsCode\contest-memory\apps\memory\.venv\Scripts\python.exe -m pytest -q`
2. **`apps/api` suite** (with `DATABASE_URL` unset):
   - `pytest -q tests`
3. **Affected client tests:**
   - `apps/messenger`: `npm run test:memory` (or `node tests/memory-ui/run.mjs`)
   - `apps/desktop`: renderer/main tests covering Settings/IPC memory controls
   - `apps/mobile`: vault / onboarding tests covering Lower/Restore & Delete-my-data
4. **Frozen `apps/web` check:**
   - `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` (MUST exit `0`).

### 5. Report, Commit, Push & Open PR (STOP Before Merge)
- Write a concise `apps/memory/upgrade/reports/E13a.md` documenting D19 + D19b + Google Limited Use verification and exact test results.
- Append 1 summary line to `apps/memory/upgrade/reports/STATUS.md`.
- Never stage the 3 founder untracked files or `apps/desktop/renderer/dist/`.
- Commit, `git push origin e13a/lower-and-delete`, open PR into `main`, and **STOP** (do NOT merge; wait for Claude's `E13a.review.md` `PASS` verdict).

---

## File Ownership Boundaries

- **ALLOWED:**
  - `apps/memory/src/temporal_memory/db/migrations/0008_memory_controls.sql`
  - `apps/memory/src/temporal_memory/privacy/controls.py`
  - D19/D19b weight/lower/recall/delete paths in `apps/memory/**`, `apps/api/app/memory_bridge/**`, `apps/api/app/identity/**`, `apps/api/app/ingest_routes.py`, `apps/api/app/messenger/routes_memory.py`, `apps/api/app/today_feed.py`
  - Client memory settings & vault/delete UI (`apps/mobile/**`, `apps/desktop/**`, `apps/messenger/**` memory settings)
  - `docs/PRIVACY_AND_MEMORY_FAQ.md`
  - Related tests in `apps/memory/tests/**`, `apps/api/tests/**`, client memory tests
  - `apps/memory/upgrade/reports/E13a.md` + `STATUS.md` (append row only)
- **FORBIDDEN (Do NOT touch):**
  - `apps/memory/src/temporal_memory/db/migrations/0009_*` (E13b ONLY)
  - `apps/memory/src/temporal_memory/vocab/similarity.py`, `vocab/shared_proposer.py`, `api/vocab_admin.py` (E13b ONLY)
  - `apps/community/**` and `apps/api/app/community/**` (E14 ONLY)
  - `apps/web/**` (frozen)
