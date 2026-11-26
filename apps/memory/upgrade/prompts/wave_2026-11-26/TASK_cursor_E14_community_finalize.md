# Task — Cursor: Finalize E14 Community Replica + Two-Tower + Context Engine

- **Agent:** Cursor
- **Branch:** `e14/community-replica-recommender` (currently at WIP `1275b25`)
- **Worktree:** `G:\Haitham\VsCode\contest-e14-community`
- **Base / Target:** Rebase onto `origin/main` (`e115077` or latest), open PR into `main`
- **Mandatory Reads First:**
  - `apps/memory/upgrade/prompts/HANDOFF_integrator_2026-11-25b.md`
  - `docs/submissions/community/FACEBOOK_REDDIT_RECOMMENDER_PLAN.md`
  - `docs/submissions/shared/founder-decisions.md` (D3, D11, D14, D19, D22)
  - `CLAUDE.md` (Rules 8, 9, `apps/web` frozen)

---

## Step-by-Step Execution

### 1. Rebase onto `origin/main`
- Run `git fetch origin && git rebase origin/main` inside `G:\Haitham\VsCode\contest-e14-community`.
- Resolve expected conflicts in:
  - `apps/community/src/components/feed/FeedScreen.tsx`
  - `apps/community/src/app/layout.tsx`
  - `apps/community/src/lib/api.ts`
  - `apps/community/src/lib/session.ts`
  - `apps/community/src/app/signin/page.tsx`
- **Keep both:** PR #9 fixes already on `main` **and** the LAN `getApiBase` / `getDubaiApi` hostname logic so iPhone/LAN testing does not hardcode `localhost` when accessed via LAN IP.
- Preserve `apps/community/src/styles/feed.css` and D14 rules (light mode, zero drop shadows).

### 2. Wire the 2 Missing Backend Seams
1. **`apps/api/app/community/server.py`:** Include `context_profile.router` so all context-profile endpoints are mounted on the Community server.
2. **`apps/api/app/community/agents.py`:** Call `recommender.rank_discovery` inside discovery (`GET /api/community/discovery`), while preserving **all** existing discovery response keys:
   - `items`, `candidates`, `reason`, `empty`, `features_used`, `source`, `why_chip`.

### 3. Fix the 2 Failing Tests (Without Weakening Assertions)
1. `apps/api/tests/test_community_context_profile.py::test_rule9_zero_health_facts_from_user_state_and_sensitive_topics`
   - Enforce Rule 9 strictly: `user_state` (and any sensitive/health topic signals) MUST never reach `temporal_memory`. Fix the production code path (`context_profile.py` / bridge call), NOT the test assertion.
2. `apps/api/tests/test_community_two_tower.py::test_benchmark_2000_posts_under_150ms_and_trained_weights`
   - Ensure ranking 2,000 posts executes in `< 150 ms` and exercises trained weights cleanly.

### 4. Run & Pass ALL Required Gates
Run inside `G:\Haitham\VsCode\contest-e14-community` (unset `DATABASE_URL` so SQLite is used for API tests; never print `.env` values):
1. `apps/api` community pytest (`DATABASE_URL` unset, `PYTHONPATH` pointing to worktree `apps/api`):
   - `pytest -q tests/test_community_*.py` (and full `apps/api/tests` if clean).
2. Two-tower trainer synthetic smoke:
   - `python scripts/train_community_two_tower.py --synthetic-smoke`
3. `apps/community` Web UI:
   - `npm test`
   - `npx tsc --noEmit`
   - `npm run build`
4. `apps/community/mobile` & `apps/community/desktop`:
   - `npm test` / `tsc` in both packages.
5. Playwright E2E:
   - `apps/community/tests/e2e/test_community_web_e2e.py`
6. Frozen `apps/web` check:
   - `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` (MUST exit `0`).

### 5. Report, Commit, Push & Open PR (STOP Before Merge)
- Write `apps/memory/upgrade/reports/E14.md` with exact commands run, test counts, benchmark ms, and compliance check against D3 (no P2P messaging), D11 (18+), D14 (light mode / no shadows), Rule 8 (foreground-only sensors, no background geofencing, no stored coordinates), Rule 9 (zero health/sensitive inference), and D19 (lower/recall).
- Append a single summary row to `apps/memory/upgrade/reports/STATUS.md`.
- Check `git status` — **NEVER** stage `apps/community/tsconfig.tsbuildinfo` or any of the 3 founder untracked files.
- Commit, `git push origin e14/community-replica-recommender` (no `--force` unless rebased with care — coordinate if needed, prefer clean rebase before push or standard push), open PR into `main`, and **STOP** (do NOT merge; Claude must complete `E14.review.md` first).

---

## File Ownership Boundaries

- **ALLOWED:**
  - `apps/api/app/community/**`
  - `apps/api/tests/test_community_*.py`
  - `apps/community/**` (excluding `tsconfig.tsbuildinfo`)
  - `scripts/train_community_two_tower.py`
  - `apps/memory/upgrade/reports/E14.md`
  - `apps/memory/upgrade/reports/STATUS.md` (append row only)
- **FORBIDDEN (Do NOT modify):**
  - `apps/web/**` (frozen)
  - `apps/memory/src/**` and `apps/memory/tests/**` (owned by E13a & E13b)
  - `apps/messenger/**`, `apps/mobile/**`, `apps/desktop/**`
  - `docs/PRIVACY_AND_MEMORY_FAQ.md`
