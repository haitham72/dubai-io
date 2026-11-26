# Task — Claude: Plan Review & Independent Security / Rule Gatekeeper

- **Agent:** Claude
- **Role:** Read-only Plan Reviewer & Independent Gatekeeper
- **Quota Rule:** **NEVER edit application/feature code or rewrite implementations.** Write **ONLY** review findings / `.review.md` reports (`E14.review.md`, `E13a.review.md`, `E13b.review.md`) so your quota is preserved for high-leverage verification.

---

## Phase A — Run IMMEDIATELY (While Builders Execute)

### 1. Plan & Wave Conflict Review
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

### 2. Pre-Audit of `origin/e13a/lower-and-delete` (`b0785c3`) Privacy & Compliance
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

### 3. Quick Sanity Check of `main` (`start-all.ps1 -Shells` + LAN URL Fix)
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
   - **D3:** Zero P2P / direct messaging in Community (for E14).
   - **D11:** 18+ age gate intact (for E14).
   - **D14:** Light mode only, zero drop shadows (for E14).
   - **D19 & D19b:** Lower weight floor `0.01`, surface cutoff `0.10`, non-deletion of DB rows, 100% explicit-trigger recall + weight boost `min(1.0, max(0.35, w_eff + 0.25))` (for E13a).
   - **D21:** Multi-owner threshold `>= 3`, aggregate counts only, zero owner ID leaks, admin-only `403` enforcement, no auto-edits to `vocab/tree.json` (for E13b).
   - **D22 / Rule 8:** Foreground-only sensors, zero background geofencing, zero stored coordinates (for E14).
   - **Rule 9:** Zero health/sensitive inference; `user_state` never reaches `temporal_memory`; fail-closed sensitive filtering.
   - **Google Limited Use:** `gmail`, `calendar`, `youtube`, `takeout_youtube` excluded from `training_backups` with zero public/bridge read routes.
   - **Hygiene:** No `.env` values printed; none of the 3 founder untracked files or `tsconfig.tsbuildinfo` / `dist/` committed; no unapproved deletions.
3. **Observed Gate Results:** Exact commands and pass/fail counts observed (never extrapolate or claim unrun checks).
