# SH-1 — Community: iPhone app (Expo) + desktop app (Electron) as thin shells around the website

For the agent working on **Community** (branch `societal`). Paste below the line.

---

Read `docs/submissions/CLAUDE.md` on `societal` first. It covers the paths, gates (§4) and rules (§5). Work on lane branch **`cm/shells`** from `societal`. The lead merges `--no-ff` after the gates pass.

## Founder decision (24 Nov)

Every product ships as **an iPhone app, a website and a desktop app**. **Wrap the existing website; don't rewrite it.**
- **iPhone only, through Expo Go:** no Android, no $99 Apple account.
- **Hosting on the founder's PC** for now: a LAN URL for development; the Cloudflare Tunnel https URL (D13) when the domain exists.

## Owned paths (new; inside Community's own folder)

- `apps/community/mobile/`: an Expo app
- `apps/community/desktop/`: an Electron app
- `docs/submissions/community/shells.md`

**Nothing else.** Never touch `apps/web`, `main`, other entries or shared paths.

## Deliverables

1. **iPhone shell (`apps/community/mobile/`, Expo SDK compatible with Expo Go).**
   - One screen: `react-native-webview` loading `COMMUNITY_URL` from `app.config` / env. Default is the PC's LAN address `http://<pc-ip>:3060`; switch to the tunnel https URL when it exists.
   - Must have:
     - a native top-safe-area and an offline / error screen with Retry;
     - pull-to-refresh;
     - links to other origins open in the system browser;
     - the session cookie kept across launches;
     - the app name **"Dubai-io Community"** and its own icon. No third-party marks.
   - Run with `npx expo start`, then scan the QR in Expo Go on the founder's iPhone.
   - Document the LAN steps: the PC firewall rule for :3060, and the server bound to `0.0.0.0`.
2. **Desktop shell (`apps/community/desktop/`, Electron).**
   - A `BrowserWindow` loading `COMMUNITY_URL` (default `http://localhost:3060`).
   - Security: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, **navigation allowlisted to that origin**, external links opened with `shell.openExternal`, no remote module, a CSP-respecting load.
   - App menu, window state remembered, an offline / error page with Retry.
   - An unsigned Windows build via `electron-builder` (signing is LATER).
   - Reuse the security patterns of Dubai-io's desktop app (`git show desktop:apps/desktop/electron/main/security.ts`, `window.ts`): read-only reference; copy the patterns, don't import them.
3. **One start script** (`apps/community/shells.md` + `scripts/` in the same folder): start the Community server bound for LAN, then the desktop shell, then print the Expo QR.
4. **Tests:**
   - desktop: navigation outside the origin is blocked; an external link opens in the browser; `nodeIntegration` is off;
   - mobile: the URL config loads; the error screen shows when the server is down.
   - Plus the §4 gates; `apps/community` `npm test && npm run build` still pass.

**Done when:** the desktop `.exe` opens Community from the PC; the iPhone (Expo Go) opens Community over the LAN; the gates pass. Add an entry to `docs/submissions/community/log.md` with screenshots: desktop window + an iPhone screenshot.
