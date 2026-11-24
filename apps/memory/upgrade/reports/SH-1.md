# SH-1 Report — Community Mobile (Expo Go) + Desktop (Electron + Windows `.exe`) Shells

- **Branch / Commit:** `cm/shells` @ `d93d6f7` (branched from `societal` @ `aad53cc`; **not merged** into `societal`)
- **Worktree:** `G:\Haitham\VsCode\contest-cm-shells`
- **Scope (`31 files changed, 2130 insertions(+)`):** Strictly within owned paths (`apps/community/mobile/`, `apps/community/desktop/`, `apps/community/scripts/start-shells.ps1`, `docs/submissions/community/shells.md`, `docs/submissions/community/log.md` append-only). Zero edits to `apps/web`, `main`, `societal`, or `apps/community/src/`.

## Deliverables

1. **iPhone Expo Go Shell ([apps/community/mobile/](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/mobile/))**
   - Standalone Expo SDK 58 (`expo ~58.0.26`) TypeScript app (`@dubai-io/community-mobile`) wrapping `EXPO_PUBLIC_COMMUNITY_URL` / [app.config.ts](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/mobile/app.config.ts) (`http://localhost:3060` fallback + editable URL override persisted in `@react-native-async-storage/async-storage`).
   - Uses `react-native-webview` (`14.0.1`) + `react-native-safe-area-context` (`~5.11.1`) in [App.tsx](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/mobile/App.tsx) with cookie persistence (`sharedCookiesEnabled`), pull-to-refresh, single-origin allowlist routing ([url.ts](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/mobile/src/config/url.ts)), external Safari handoff via `Linking.openURL`, unsafe scheme blocking (`javascript:`, `file:`, `data:`), and offline retry UI ([OfflineFallback.tsx](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/mobile/src/components/OfflineFallback.tsx)).

2. **Electron Desktop Shell & Unsigned `.exe` ([apps/community/desktop/](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/desktop/))**
   - Standalone Electron (`^39.2.0`) TypeScript wrapper (`@dubai-io/community-desktop`) loading `COMMUNITY_URL` (default `http://localhost:3060`).
   - Hardened `webPreferencesBase` (`contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, `webSecurity: true`, `webviewTag: false`) and `attachNavigationGuards` (`will-navigate`, `setWindowOpenHandler`, `will-attach-webview`) in [security.ts](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/desktop/electron/security.ts), window bounds persistence ([windowState.ts](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/desktop/electron/windowState.ts)), and CSP-hardened offline retry fallback.
   - Unsigned portable Windows `.exe` built via `electron-builder` ([electron-builder.yml](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/desktop/electron-builder.yml), `signAndEditExecutable: false`):
     - `G:\Haitham\VsCode\contest-cm-shells\apps\community\desktop\dist\Dubai-io-Community-0.1.0-win-x64.exe` (**93,873,422 bytes**, gitignored).

3. **Start Script & Docs**
   - [start-shells.ps1](file:///G:/Haitham/VsCode/contest-cm-shells/apps/community/scripts/start-shells.ps1): detects active LAN IPv4 (`10.5.3.228`), checks TCP `3060` Windows Firewall rule (prints exact elevated `netsh` command when non-admin), binds Next.js on `0.0.0.0:3060`, launches Electron and Expo Go QR (`-CheckOnly` supported).
   - [shells.md](file:///G:/Haitham/VsCode/contest-cm-shells/docs/submissions/community/shells.md) + dated entry in [log.md](file:///G:/Haitham/VsCode/contest-cm-shells/docs/submissions/community/log.md#L82-L93).

## Lead Verification (`cm/shells` @ `d93d6f7`)

| Check | Command | Result |
|---|---|---|
| Mobile typecheck & tests | `npm.cmd run typecheck; npm.cmd test` (`apps/community/mobile`) | **exit 0** — 2 files, **8 passed** (`tests/url.test.ts`, `tests/storage.test.ts`) |
| Desktop typecheck & tests | `npm.cmd run typecheck; npm.cmd test` (`apps/community/desktop`) | **exit 0** — 2 files, **11 passed** (`tests/security.test.ts`, `tests/windowState.test.ts`) |
| Unsigned `.exe` artifact | `Get-Item apps/community/desktop/dist/*.exe` | **exists** — `Dubai-io-Community-0.1.0-win-x64.exe` (**93,873,422 bytes**) |
| Start script dry check | `start-shells.ps1 -CheckOnly` | **exit 0** — LAN IPv4 `10.5.3.228`, prints `http://10.5.3.228:3060`, `exp://10.5.3.228:8081`, TCP `3060` `netsh` hint |
| Community web tests & build | `npm.cmd test; npm.cmd run build` (`apps/community`) | **exit 0** — Vitest 2 files, **9 passed**; `next build` exited 0 on retry (7 static routes; Next.js 16.4.2 security advisory printed) |
| §4 Gate 1 (API pytest) | `G:\Haitham\VsCode\contest\apps\api\.venv\Scripts\python.exe -m pytest -q` (`apps/api`) | **585 passed, 15 skipped, 1 failed** (pre-existing env miss: `tests/test_ops.py::test_failed_job_exposes_only_id_and_category` — `No module named 'redis'` in `contest\apps\api\.venv`) |
| §4 Gate 2 (`apps/web` untouched) | `git diff --quiet societal HEAD -- apps/web` | **exit 0** |
| §4 Gate 3 (owned paths only) | `git diff --stat aad53cc HEAD` | **31 files**, all inside owned paths |
| §4 Gate 5 (`merge-tree`) | `git merge-tree --write-tree cm/shells origin/{memory,ios,desktop}` | **exit 0** on all 3 targets (clean merge) |
