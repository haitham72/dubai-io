# D-B — Cursor: Electron Renderer UI, Chrome Consent Flow, Session History & Packaging (`desktop` Branch)

Paste below the line into **Cursor**.

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and `docs/plan/desktop-electron.md` (on branch `desktop`) first.
- **Never edit `G:\Haitham\VsCode\contest`** (`main`), **never touch `apps/web`** or `apps/memory/`.
- **Zero shadows** in UI (`1px` hairline borders only), light mode first (`#FFFFFF` / `#FAF8F5` + gold `#C5A059`), consistent with `design/20-11-2026/INDEX.md` and `packages/design-tokens/` contract.
- **No real personal data** in fixtures or tests — reuse synthetic fixtures (`Karim Haddad` / `apps/memory/tests/fixtures/desktop/` shapes) and mark fixture cards with `Demo data`.
- Sub-agents: optional (1–2 on Cursor's fast model). Commit only on your own branch.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-desktop-ui -b desktop-ui desktop
cd G:\Haitham\VsCode\contest-desktop-ui
```

### Strictly Owned Paths (100% disjoint from Codex's `D-A` `electron/main` & `electron/preload`)
- `apps/desktop/renderer/` (React + TypeScript + Vite renderer)
  - `index.html`, `vite.config.ts`, `src/main.tsx`, `src/App.tsx`
  - `src/ipc/bridge.ts` (typed wrapper around `window.dubaiDesktop` preload bridge with clean browser-preview demo mock when `window.dubaiDesktop` is absent)
  - `src/panels/SessionHistoryPanel.tsx` (Orca-inspired: Scope `Workspace | Project | All` capped at 200 + pagination, Agent filter `Claude Code | Codex | All`, Search box, row viewer modal, Copy Resume Command button, Opt-in Send Selected Sessions to Memory button with count + R5 check)
  - `src/panels/BrowserImportPanel.tsx` (`"Import Chrome history"` preview-first consent screen: calls `browser:preview` -> displays `{domain: visits}` counts + explicit disclaimer `History & Bookmarks only — Cookies, Passwords & Autofill are NEVER touched` -> user confirms import)
  - `src/panels/SettingsPanel.tsx` (`owner-device` token setup, `"Process on your own Claude/Codex ($0 app cost)"` toggle with explicit model picker, per-source consent toggles default OFF, forget-by-source trigger)
  - `src/panels/AppShell.tsx` (4-pillar `Today` · `Chat` · `Quests` · `Memory` workspace layout + Desktop `Sessions` & `Local Import` tabs)
- `apps/desktop/tsconfig.renderer.json`
- `apps/desktop/electron-builder.yml` (unsigned Windows NSIS/portable dev build config; code signing documented as `LATER`)
- `apps/desktop/README.md` (how to run Vite + Electron locally, build unsigned Windows installer, and configure `owner-device` token)
- `apps/desktop/tests/renderer/` (Vitest + Testing Library unit tests for all panels + negative security/consent tests)

*(Do NOT edit `apps/desktop/electron/` or overwrite Codex's `package.json` keys — if you add `renderer` scripts/deps, keep them in a separate `apps/desktop/renderer/package.json` so merging `D-A` and `D-B` into `desktop` has **zero package.json conflicts**!)*

### Deliverables
1. **Session History Panel:** list, search, open log preview (redacted text only), copy safe resume argv command, explicit per-source consent before calling `sessions:scan` or sending selected sessions to memory.
2. **Import Chrome / Edge History Consent Flow:** MUST call preview first (`domain -> visit count`), create zero records during preview, display default denylist note (banking/health/gov portals excluded), and require explicit click confirmation before calling import.
3. **Owner-Hook Toggle:** `"Process on your own Claude/Codex ($0 app cost)"` switch wired cleanly to `hook:toggle` with required model selector (`claude-sonnet-4-5`, `claude-haiku-4-5`, `o3-mini`, etc.).
4. **Tests (`apps/desktop/tests/renderer/`):**
   - Session History filtering/search/pagination + copy-resume-command + no auto-scan before opt-in;
   - Browser preview renders domain counts without calling import; import runs only after explicit confirmation;
   - Owner-hook toggle passes non-empty model string.

**Done when** `npm test` and `npm run build` inside `apps/desktop/renderer/` pass, and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes. Commit on `desktop-ui` and report: branch and test counts.
