# SH-2 Report — Messenger Mobile (Expo Go) + Desktop (Electron + Windows `.exe`) Shells

- **Branch / Commit:** `mg/shells` @ `fb3eed4` (branched from `business` @ `346b5e7`; **not merged** into `business`)
- **Worktree:** `G:\Haitham\VsCode\contest-mg-shells`
- **Scope (`27 files changed, 1910 insertions(+)`):** Strictly within owned paths (`apps/messenger/mobile/`, `apps/messenger/desktop/`, `apps/messenger/scripts/start-shells.ps1`, `docs/submissions/messenger/shells.md`, `docs/submissions/messenger/log.md` append-only). Zero edits to `apps/web`, `main`, `business`, `apps/messenger/src/`, or `apps/api/`.

## Deliverables

1. **iPhone Expo Go Shell ([apps/messenger/mobile/](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/mobile/))**
   - Standalone Expo TypeScript project (`@messenger/mobile`) using `react-native-webview`, `react-native-safe-area-context`, `expo-av`, and `expo-image-picker` ([package.json](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/mobile/package.json)).
   - Single-origin allowlist & WS URL derivation ([config.ts](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/mobile/src/config.ts)), persistent cookies (`sharedCookiesEnabled`), LAN URL switcher bar, external Safari handoff (`Linking.openURL`), offline Retry card ([App.tsx](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/mobile/src/App.tsx)), and JS bridge ([bridge.ts](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/mobile/src/bridge.ts)) supporting `REQUEST_MIC`, `START_VOICE_RECORDING`, `STOP_VOICE_RECORDING`, `PICK_MEDIA`, and `PICK_STICKER` (1:1 crop + base64).

2. **Electron Desktop Shell & Unsigned `.exe` ([apps/messenger/desktop/](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/desktop/))**
   - Standalone Electron TypeScript project (`@messenger/desktop`) loading `MESSENGER_URL` (default `http://localhost:5173`).
   - Hardened `webPreferencesBase` (`contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, `webSecurity: true`, `webviewTag: false`) in [security.ts](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/desktop/electron/security.ts), single-origin `will-navigate` / `setWindowOpenHandler`, `app.setAppUserModelId("app.messenger.desktop")`, fail-closed origin-gated `notifications` & `media` permission handlers in [main.ts](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/desktop/electron/main.ts), preload IPC (`window.messengerDesktop`), and offline retry fallback ([offline.html](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/desktop/electron/offline.html)).
   - Unsigned portable Windows `.exe` built via `electron-builder` ([electron-builder.yml](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/desktop/electron-builder.yml), `signAndEditExecutable: false`):
     - `G:\Haitham\VsCode\contest-mg-shells\apps\messenger\desktop\dist\Messenger-portable-0.1.0.exe` (**93,959,774 bytes**, gitignored; unpacked `Messenger.exe` `210,896,896` bytes).

3. **Start Script & Docs**
   - [start-shells.ps1](file:///G:/Haitham/VsCode/contest-mg-shells/apps/messenger/scripts/start-shells.ps1): detects LAN IPv4 (`10.5.3.228`), populates `MESSENGER_API_URL=http://127.0.0.1:8070` and `MESSENGER_ALLOWED_ORIGINS` (local + LAN `:5173`/`:4173`) so `/api/messenger/ws` allows LAN iPhone + desktop clients, checks TCP `5173` and `8070` firewall rules with `netsh` fallback hints, and launches `:8070` + `:5173` (`-CheckOnly` supported).
   - [shells.md](file:///G:/Haitham/VsCode/contest-mg-shells/docs/submissions/messenger/shells.md) + dated entry in [log.md](file:///G:/Haitham/VsCode/contest-mg-shells/docs/submissions/messenger/log.md#L194-L219).

## Lead Verification (`mg/shells` @ `fb3eed4`)

| Check | Command | Result |
|---|---|---|
| Mobile typecheck & tests | `npm.cmd run typecheck; npm.cmd test` (`apps/messenger/mobile`) | **exit 0** — 1 file, **8 passed** (`tests/mobile.test.ts`) |
| Desktop typecheck & tests | `npm.cmd run typecheck; npm.cmd test` (`apps/messenger/desktop`) | **exit 0** — 1 file, **6 passed** (`tests/security.test.ts`) |
| Unsigned `.exe` artifact | `Get-Item apps/messenger/desktop/dist/*.exe` | **exists** — `Messenger-portable-0.1.0.exe` (**93,959,774 bytes**) |
| Start script dry check | `start-shells.ps1 -CheckOnly` | **exit 0** — LAN IPv4 `10.5.3.228`, `MESSENGER_ALLOWED_ORIGINS` set, TCP `5173`/`8070` `netsh` hints |
| Messenger web gates | `npm.cmd run typecheck; npm.cmd run build; npm.cmd run test:photo-window; npm.cmd run test:store` | **exit 0** — `tsc` OK, Vite built `1710` modules (`7.85s`), `photo-window` PASS, `store-wiring` 8/8 `(a)`–`(h)` PASS |
| §4 Gate 1 (API pytest) | `G:\Haitham\VsCode\contest\apps\api\.venv\Scripts\python.exe -m pytest -q` (`apps/api`) | **545 passed, 16 skipped, 1 failed** (pre-existing env miss: `tests/test_ops.py::test_failed_job_exposes_only_id_and_category` — `No module named 'redis'` in `contest\apps\api\.venv`) |
| §4 Gate 2 (`apps/web` untouched) | `git diff --quiet business HEAD -- apps/web` | **exit 0** |
| §4 Gate 3 (owned paths only) | `git diff --stat 346b5e7 HEAD` | **27 files**, all inside owned paths |
| §4 Gate 4 (D1 old-name gate) | `git grep -n -i -e "m[i]rsal" -- apps/messenger apps/api/app/messenger docs/submissions/messenger/shells.md` | **exit 1** — **0 matches** (and 0 occurrences in SH-2 `log.md` entry) |
| §4 Gate 5 (`merge-tree`) | `git merge-tree --write-tree mg/shells origin/{memory,ios,desktop}` | **exit 0** on all 3 targets (clean merge) |
