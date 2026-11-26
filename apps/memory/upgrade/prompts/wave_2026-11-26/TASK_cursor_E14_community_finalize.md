# Task — Cursor: Finalize E14 Community Replica + Two-Tower + Context Engine

- **Agent:** Cursor
- **Branch:** `e14/community-replica-recommender` (currently at WIP `1275b25`)
- **Worktree:** `G:\Haitham\VsCode\contest-e14-community`
- **Base / Target:** Rebase onto `origin/main` (latest), open PR into `main`
- **Mandatory Reads First:**
  - `apps/memory/upgrade/prompts/HANDOFF_integrator_2026-11-25b.md`
  - `docs/submissions/community/FACEBOOK_REDDIT_RECOMMENDER_PLAN.md`
  - `docs/submissions/shared/founder-decisions.md` (D3, D11, D14, D19, D22)
  - `CLAUDE.md` (Rules 8, 9, Google Limited Use, light mode / zero drop shadows, `apps/web` frozen)

---

## Claude Phase A Mandatory Fixes (Include in This PR)

1. **`cm_usage_settings.context_aware_enabled` DEFAULT `0` (Opt-In per D22):**
   - Currently `DEFAULT 1` — change schema/migration/init default to `0` so context-aware usage is strictly opt-in per **D22**.
2. **`user_state` and `area_coarse` Strictly Ephemeral with Short TTL (`A1 #3`):**
   - `apps/api/app/community/context_profile.py:129-161` currently persists `user_state` and `area_coarse` permanently.
   - Store them **ONLY** in TTL-bounded Redis (`cm:ctx:{owner}`) + an in-memory TTL dict fallback — **never** persist `user_state` or `area_coarse` permanently in SQLite/Postgres.
3. **`purge_owner_community_data(owner_id: str)` Deletion Hook (`A1 #2`):**
   - Add `purge_owner_community_data(owner_id: str)` in `apps/api/app/community/context_profile.py` to delete `cm_interaction_events`, `cm_usage_profile`, `cm_usage_settings`, Redis `cm:ctx:{owner}`, and the in-process fallback cache.
   - Add a unit test verifying `purge_owner_community_data(owner_id)` clears all Community tables, Redis key, and in-process fallback cache so E13a's `"Delete my data"` clears Community data immediately.
4. **Google Limited Use (`A1 #4`):**
   - Exclude any rows derived from `gmail`, `calendar`, `youtube`, `takeout`, or `google` in `scripts/train_community_two_tower.py`.
5. **Ownership & Rebase Guards (`A1 #8` + `A3`):**
   - Preserve E13a's D19 `erased_at is None` checks in `apps/api/tests/test_community_demo_scenes.py` and `apps/api/tests/test_community_memory.py` (the one allowed overlap with E13a `b0785c3`).
   - Keep the Rule 9 fix strictly inside `apps/api/app/community/**` (never touch `memory_bridge`).
   - Preserve `origin/main`'s LAN helpers (`getApiBase`, `getDubaiApi`) and the `"Pair with PC code"` UI in `apps/community/src/app/signin/page.tsx`.
6. **D11 + D14 Merge Gate (`A1 #7`):**
   - **D14** = native-social look (no serif/cream/gold, icon action row, stop for founder approval after Feed); light mode / zero drop shadows is enforced by `CLAUDE.md`.
   - **D11** = founder visual review of a staged preview is **REQUIRED** before merging UI work — after Claude's `E14.review.md` `PASS`, stage a preview for **founder visual approval** before merging (**E14 MUST NOT merge on Claude's review alone**).

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
- **Keep both:** PR #9 + `main` fixes **and** the LAN `getApiBase` / `getDubaiApi` hostname logic + `"Pair with PC code"` UI in `apps/community/src/app/signin/page.tsx` so controlled same-network Wi-Fi iPhone/LAN testing works without hardcoding `localhost`.
- Preserve `apps/community/src/styles/feed.css`, D14 native-social styling (no serif/cream/gold, icon action row), and `CLAUDE.md` rules (light mode, zero drop shadows).

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

### 5. Report, Commit, Push & Open PR (STOP for Review + Founder Visual Approval)
- Write `apps/memory/upgrade/reports/E14.md` with exact commands run, test counts, benchmark ms, and compliance check against D3 (no P2P messaging), D11 (18+ gate + staged visual preview required), D14 (native-social look: no serif/cream/gold, icon action row) + `CLAUDE.md` (light mode / no shadows), Rule 8 & D22 (opt-in `context_aware_enabled DEFAULT 0`, ephemeral TTL `user_state`/`area_coarse`, foreground-only sensors, no background geofencing, no stored coordinates), Rule 9 (zero health/sensitive inference), Google Limited Use (`train_community_two_tower.py` exclusion), and D19 (`purge_owner_community_data` + preserved `erased_at is None` checks).
- Append a single summary row to `apps/memory/upgrade/reports/STATUS.md`.
- Check `git status` — **NEVER** stage `apps/community/tsconfig.tsbuildinfo` or any of the 3 founder untracked files.
- Commit, `git push origin e14/community-replica-recommender` (no `--force` unless rebased with care — coordinate if needed, prefer clean rebase before push or standard push), open PR into `main`, and **STOP** (do NOT merge; Claude must complete `E14.review.md` `PASS` **AND** founder must visually approve a staged preview per **D11** before merge).

---

## File Ownership Boundaries

- **ALLOWED:**
  - `apps/api/app/community/**`
  - `apps/api/tests/test_community_*.py` (preserving E13a's D19 `erased_at is None` checks in `test_community_demo_scenes.py` and `test_community_memory.py`)
  - `apps/community/**` (excluding `tsconfig.tsbuildinfo`)
  - `scripts/train_community_two_tower.py`
  - `apps/memory/upgrade/reports/E14.md`
  - `apps/memory/upgrade/reports/STATUS.md` (append row only)
- **FORBIDDEN (Do NOT modify):**
  - `apps/web/**` (frozen)
  - `apps/memory/src/**` and `apps/memory/tests/**` (owned by E13a & E13b)
  - `apps/api/app/memory_bridge/**` (keep Rule 9 fix strictly inside `apps/api/app/community/**`)
  - `apps/messenger/**`, `apps/mobile/**`, `apps/desktop/**`
  - `docs/PRIVACY_AND_MEMORY_FAQ.md`
