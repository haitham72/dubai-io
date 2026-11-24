# D-C — Muse: Desktop Continuous Sync, `/v1/owners/{o}/onboarding-status` & User Analytics (`memory` + `desktop` Phase 2)

Paste below the line into **Muse** once `D-A` and `D-B` are merged on `desktop`.

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md`, `prompts\SUBAGENTS.md`, and `docs/plan/gamified-onboarding-and-analytics.md` (on branch `desktop`) first. **Sub-agents: Muse 1.3 Contributor only (never Wonder).**

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-desktop-analytics -b desktop-analytics desktop
cd G:\Haitham\VsCode\contest-desktop-analytics
```

### Deliverables
1. **Memory Engine Onboarding & Analytics Endpoint (`apps/memory/src/temporal_memory/api/vault.py` + `tests/test_vault.py`):**
   - Add `GET /v1/owners/{owner}/onboarding-status` returning deterministic JSON:
     - `completeness_pct` (`0–100`) and `breakdown` using the canonical weights (`gmail: 14`, `calendar: 10`, `youtube_api: 12` = **`36%` mobile base**; `whatsapp: 15`, `youtube_history: 12`, `browser: 18`, `agent_sessions: 19`);
     - `next_recommended_action` (e.g. `"install_desktop_and_sync"` when at `36%` mobile-only, `"enable_browser_or_sessions"` on desktop, etc.);
     - `known_so_far`: top verified facts grouped by theme with `id`, `text`, `subject_id`, `valid_from`, `evidence`, `provenance`, `as_of`;
     - `analytics`:
       - `by_source`: record & fact counts per source prefix (`gmail`, `youtube:interests`, `whatsapp`, `browser`, `agent:claude-code`, `agent:codex`, `ai:chatgpt`, `takeout:*`),
       - `by_theme`: fact counts across the 7 life spines + `rising_21d` subjects (last 21 days vs prior baseline),
       - `privacy_shield`: total `quarantine` / Rule-9 held-back counts by category (counts only, never raw text),
       - `compute_saved`: `owner_hook_facts`, `tokens_in`, `tokens_out`, `demo_cost_saved_usd`.
2. **Desktop Continuous Pull & Live Analytics Panel (`apps/desktop/`):**
   - When the user signs into **Dubai-io Desktop** with the same owner/token, adds an opt-in **"Keep Pulling Consented Sources (Every 60m / On Focus)"** scheduler in `electron/main/` for enabled sources (`Chrome/Edge History`, `Claude Code`, `Codex`) using `content_hash` idempotency so re-pulls only enqueue new day packets.
   - Adds **`Analytics & What I Know About You`** view in `apps/desktop/renderer/` showing the live jump from **`36%` (Mobile Google login)** → **`73%–100%` (after PC Chrome + AI sessions pull)**, the *"What your data says about you"* theme radar, rising 21-day topics, Rule-9 privacy shield counter, and `$0 app cost` owner-hook stats.
3. **Tests:**
   - Pytest tests in `apps/memory/tests/test_vault.py` verifying `36%` mobile-only baseline, `73%+` after browser + agent-session records, rising-21d calculation, and zero raw sensitive text in `privacy_shield`;
   - Vitest tests in `apps/desktop/tests/` verifying continuous pull idempotency (only enabled sources pulled, R1 denylist respected) and analytics panel rendering.

**Done when** both `pytest -q` in `apps/memory` and `npm test` in `apps/desktop` pass, and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes. Commit on `desktop-analytics` with a clear commit message and report branch + counts.
