# Task — Claude: Plan Review & Independent Security / Rule Gatekeeper

- **Agent:** Claude
- **Role:** Read-only Plan Reviewer & Independent Gatekeeper
- **Quota Rule:** **NEVER edit application/feature code or rewrite implementations.** Write **ONLY** review findings / `.review.md` reports (`E14.review.md`, `E13a.review.md`, `E13b.review.md`) so your quota is preserved for high-leverage verification.

---

## Phase A — COMPLETE (Archival Reference Only)

> **Status:** Phase A (`A1`, `A2`, `A3`) is **COMPLETE**. All Phase A findings (`A1 #2`–`#8`, `A2 E1`–`E7`, `A3` LAN/Wi-Fi testing) have been incorporated into the wave plan, builder task files, and Phase B review checklists below. Kept for archival reference only.

### 1. Plan & Wave Conflict Review *(Completed — `A1`)*
Inspect the 4 wave files in `apps/memory/upgrade/prompts/wave_2026-11-26/`:
- `WAVE_PLAN_2026-11-26.md`
- `TASK_cursor_E14_community_finalize.md`
- `TASK_codex_E13a_d19b_finish.md`
- `TASK_muse_E13b_shared_vocab.md`

Check for:
- Hidden file-ownership collisions (especially `core/retrieval.py`, `api/vault.py`, `core/embed.py`, `FeedScreen.tsx`, `layout.tsx`, `api.ts`).
- Migration ordering hazards (`0007_learned_terms.sql` -> `0008_memory_controls.sql` -> `0009_shared_vocab_proposals.sql`).
- Any missing privacy, security, or test gate against `founder-decisions.md` (D3, D11, D14, D17–D22, D19b) and `CLAUDE.md` (Rules 8, 9, Google Limited Use, frozen `apps/web`).
- **Output:** Emit a concise `OK` or `FIX BEFORE MERGE` summary directly to the orchestrator.

### 2. Pre-Audit of `origin/e13a/lower-and-delete` (`b0785c3`) Privacy & Compliance *(Completed — `A2 E1`–`E7`)*
Audit `G:\Haitham\VsCode\contest-e13a` (read-only) specifically on:
- `apps/memory/src/temporal_memory/db/migrations/0008_memory_controls.sql`
- `apps/memory/src/temporal_memory/privacy/controls.py`
- `apps/memory/src/temporal_memory/api/bridge.py`
- `apps/memory/src/temporal_memory/api/vault.py`
- `apps/api/app/identity/router.py`

Verify:
1. `training_backups` scrubs **all** PII (owner UUID replaced with one-way salted hash / surrogate ID; email, name, phone, tokens, credentials stripped).
2. `training_backups` strictly **excludes** Google Workspace & YouTube sources (`gmail`, `calendar`, `youtube`, `takeout_youtube`) — honoring Google API Limited Use policy.
3. **Zero** public, identity, or bridge endpoints can read `training_backups`.
4. `"Delete my data"` purges all owner Redis keys (`TM_REDIS_URL`), clears all in-process caches, revokes sessions/tokens, bumps owner generation/`facts_version`, and excludes external queries immediately with zero data leaks.
- **Output:** Emit a concrete, line-referenced defect list (or `CLEAN` confirmation) so Codex can fix any gap in a single pass alongside D19b.

### 3. Quick Sanity Check of `main` (`start-all.ps1 -Shells` + LAN URL Fix) *(Completed — `A3`)*
Read-only check on `G:\Haitham\VsCode\contest` (`main`):
- Inspect `scripts/dev/start-all.ps1`, `scripts/dev/health.ps1`, `scripts/dev/stop-all.ps1`, and the Messenger/Community LAN API URL config for any blocker to 3×3 testing (3 web apps + 3 Expo mobile + 3 Electron desktops).
- **Output:** Flag any concrete blocker to the orchestrator.

---

## Phase B — Run As Each PR Opens (Independent Gate Sign-Off)

For each PR in merge order (**E14**, then **E13a**, then **E13b**), independently inspect the diff + test outputs and write:
- `apps/memory/upgrade/reports/E14.review.md`
- `apps/memory/upgrade/reports/E13a.review.md`
- `apps/memory/upgrade/reports/E13b.review.md`

Each `.review.md` MUST include:
1. **Verdict:** `PASS` or `BLOCKERS` (explicitly blocking merge if any hard rule fails).
2. **Hard-Rule Checklist (exact observed evidence):**
   - `apps/web` frozen check (`git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` exits `0`).
   - **D3 (E14):** Zero P2P / direct messaging in Community.
   - **D11 (E14):** 18+ age gate intact **AND** explicitly note that **founder visual review of a staged preview is REQUIRED before merging UI work** (**E14 must NOT merge on Claude's review alone**).
   - **D14 & `CLAUDE.md` (E14):** Verify **D14** native-social look (no serif/cream/gold, icon action row, stop for founder approval after Feed) separately from **`CLAUDE.md`** visual rules (light mode only, zero drop shadows).
   - **D22 / Rule 8 / Community Deletion & Google Limited Use (E14):**
     - `cm_usage_settings.context_aware_enabled` defaults to `0` (opt-in).
     - `user_state` and `area_coarse` are strictly ephemeral with short TTL in Redis `cm:ctx:{owner}` + in-memory TTL dict fallback (never persisted permanently in SQLite/Postgres).
     - `purge_owner_community_data(owner_id)` exists in `apps/api/app/community/context_profile.py`, deletes `cm_interaction_events`, `cm_usage_profile`, `cm_usage_settings`, Redis `cm:ctx:{owner}`, and in-process fallback cache, and has a passing unit test.
     - `scripts/train_community_two_tower.py` excludes rows derived from `gmail`, `calendar`, `youtube`, `takeout`, `google`.
     - Foreground-only sensors, zero background geofencing, zero stored coordinates.
     - Preserves E13a's `erased_at is None` checks in `test_community_demo_scenes.py` and `test_community_memory.py`, keeps Rule 9 fix strictly inside `app/community` (out of `memory_bridge`), and preserves `main` LAN helpers (`getApiBase`, `getDubaiApi`) + `"Pair with PC code"` in `apps/community/src/app/signin/page.tsx`.
   - **D19, D19b & Phase A Audit Defects `E1`–`E7` / `A1 #6` (E13a):**
     - Lower weight floor `0.01`, surface cutoff `0.10`, non-deletion of DB rows.
     - **`E1`:** `include_lowered=True` / explicit-trigger recall + boost (`w_new = min(1.0, max(0.35, w_eff + 0.25))`) ONLY on explicit user-device calls — NEVER on admin, worker, `/context`, Today, or recommender; never mutates provenance/status or counts toward Rule 9's two-visit rule.
     - **`E2 + A1 #6`:** `last_refreshed_at` + per-memory recall weight override beats inherited topic/source/record `0.01` lowering without altering `valid_from`; migration placement safe (`0008` ONLY if `version = 8` was not in `schema_migrations`, else `0010_d19b_recall_boost.sql`, never `0009`).
     - **`E3`:** Empty `TM_REDIS_URL` on delete fails closed (error) instead of returning `redis_purged: false` success (except explicit test fake client injection).
     - **`E4`:** Second Redis purge executes **after** Postgres commits `deleted_from_external = true`.
     - **`E5 + A1 #2`:** `apps/api/app/identity/router.py` purges `apps/api` Redis (`*{owner}*` and `cm:ctx:{owner}`), clears in-process caches, and invokes optional `purge_owner_community_data(owner)`.
     - **`E6`:** Automated test asserts zero API routes or MCP tools reference `training_backups`.
     - **`E7`:** `E13a.md` documents that sibling worker processes rely on `owner_deleted` DB check (`retrieval.py:382`) for cross-process cache safety.
     - **Google Limited Use (E13a):** `gmail`, `calendar`, `youtube`, `takeout_youtube` excluded from `training_backups` with zero public/API/MCP read routes.
   - **D21 & Phase A Privacy Fixes `A1 #4`, `A1 #5` (E13b):**
     - Multi-owner threshold `>= 3`, aggregate counts only, zero owner ID leaks, admin-only `403` enforcement, no auto-edits to `vocab/tree.json`, clean `0009` migration after `0008`/`0010`.
     - **`A1 #4`:** `learned_terms` from `gmail`, `calendar`, `youtube`, `takeout`, `google` dropped before clustering or LLM calls.
     - **`A1 #5`:** `vocab_query_signals` uses server-keyed **HMAC-SHA256** (`TM_SIGNAL_HMAC_KEY`), NEVER plain unkeyed SHA-256; logs ONLY user-typed queries (never `/context` calls); excludes deleted owners from `distinct_owners` and provides `purge_owner_query_signals(conn, owner_id)` with passing unit tests.
   - **Rule 9:** Zero health/sensitive inference; `user_state` never reaches `temporal_memory`; fail-closed sensitive filtering.
   - **Hygiene:** No `.env` values printed; none of the 3 founder untracked files or `tsconfig.tsbuildinfo` / `dist/` committed; no unapproved deletions.
3. **Observed Gate Results:** Exact commands and pass/fail counts observed (never extrapolate or claim unrun checks).
