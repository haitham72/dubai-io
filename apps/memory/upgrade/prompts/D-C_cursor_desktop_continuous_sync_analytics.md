# D-C (Part 2) — Cursor: Desktop Continuous Sync & Live User Analytics Panel (`desktop-analytics`)

Paste below the line into **Cursor** (Muse completed Part 1 `/v1/owners/{owner}/onboarding-status` in `apps/memory` before running out of quota, and `D-B` renderer UI is already merged into `desktop-analytics`).

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md`, `docs/plan/desktop-electron.md`, and `docs/plan/gamified-onboarding-and-analytics.md` first. **Sub-agents: Composer 2 Fast only.**

Work directly in the existing worktree `G:\Haitham\VsCode\contest-desktop-analytics` on branch `desktop-analytics` (which already contains `D-A`, `D-B`, and Muse's verified `D-C Part 1` `GET /v1/owners/{owner}/onboarding-status` endpoint):

```powershell
cd G:\Haitham\VsCode\contest-desktop-analytics
git status
```

### What Is Already Done on `desktop-analytics` (Do NOT Rewrite)
- `apps/memory/src/temporal_memory/api/vault.py` + `apps/memory/tests/test_vault.py` (`GET /v1/owners/{owner}/onboarding-status` returning `completeness_pct`, `breakdown`, `sources_present`, `next_recommended_action`, `known_so_far`, and `analytics` with `by_source`, `by_theme`, `rising_21d`, `privacy_shield`, `compute_saved` — **7/7 pytest tests passing**).
- `apps/desktop/electron/{main,preload}/` (`D-A`) and `apps/desktop/renderer/` (`D-B`: `AppShell.tsx`, `SessionHistoryPanel.tsx`, `BrowserImportPanel.tsx`, `SettingsPanel.tsx`).

### Deliverables (Part 2 — Desktop Continuous Sync & User Analytics UI)
1. **Desktop Continuous Pull Scheduler (`apps/desktop/electron/main/` + `preload/` if needed):**
   - Add an opt-in **"Keep Pulling Consented Sources (Every 60m / On Focus)"** controller (e.g. `apps/desktop/electron/main/continuousSync.ts`) for enabled sources (`Chrome/Edge History`, `Claude Code`, `Codex`).
   - Uses `content_hash` / seen-packet idempotency so repeated pulls only enqueue new day packets, and strictly respects `localReader.ts` R1 security (credential denylist + symlink rejection + disabled sources never read).
   - Expose status/toggle (`enabledSources`, `intervalMinutes`, `syncOnFocus`, `lastSyncAt`, `runSyncNow()`) to the renderer via the preload allowlist bridge (`apps/desktop/renderer/src/ipc/bridge.ts`).
2. **Live `Analytics & What I Know About You` Panel (`apps/desktop/renderer/src/panels/`):**
   - Add `AnalyticsPanel.tsx` and wire it as a primary tab in `AppShell.tsx` (alongside `SessionHistoryPanel`, `BrowserImportPanel`, `SettingsPanel`).
   - Renders data from `GET /v1/owners/{owner}/onboarding-status` (with deterministic Karim synthetic fallback when offline, carrying the `"Demo data"` badge):
     - **Completeness jump hero:** shows the progression from **`36%` (Mobile Google login)** → **`73%–100%` (after PC Chrome/Edge `+18%` + AI sessions `+19%` pull)** plus the continuous sync toggle/status bar;
     - **"What your data says about you" 7-Theme Radar / Bar Breakdown:** `Career`, `Learning`, `Projects`, `People & family`, `Events`, `Home & money`, `Travel` + **`rising_21d`** badges (`+delta` over last 21 days);
     - **Cross-source mix (`by_source`)** and **"Known so far" verified facts** grouped by theme;
     - **Rule-9 Privacy Shield card:** displays `held_back_total` and `by_category` counts only (never raw held-back text);
     - **Compute & Cost Saved card:** displays `owner_hook_facts`, `tokens_in`, `tokens_out`, and `processed on your Claude/Codex · $0 app cost` (`demo_cost_saved_usd`).
3. **Tests (`apps/desktop/tests/`):**
   - Main-process Vitest test (`apps/desktop/tests/main/continuousSync.test.ts`) verifying continuous sync only pulls consented sources, skips duplicate `content_hash` packets on re-pull, and respects R1 denylist.
   - Renderer Vitest test (`apps/desktop/tests/renderer/analytics.test.tsx`) verifying the `36% -> 73%+` completeness jump UI, 7-theme breakdown + `rising_21d`, Rule-9 privacy shield counter, `$0 app cost` badge, and continuous-sync toggle.

**Done when** both main and renderer Vitest suites pass (`npm test` in `apps/desktop` and `apps/desktop/renderer`), `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes, and all changes are committed on `desktop-analytics`. Report branch + commit SHA + test counts.
