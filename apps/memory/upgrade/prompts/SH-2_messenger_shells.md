# SH-2 — Messenger: iPhone app (Expo) + desktop app (Electron) as thin shells around the website

For the agent working on **Messenger** (branch `business`). Paste below the line.

---

Read `docs/submissions/CLAUDE.md` on `business` first. It covers the paths, gates (§4), rules (§5) and the D1 name gate. Work on lane branch **`mg/shells`** from `business`. The lead merges `--no-ff` after the gates pass.

## Founder decision (24 Nov)

Every product ships as **an iPhone app, a website and a desktop app**. **Wrap the existing website; don't rewrite it.**
- **iPhone only, through Expo Go:** no Android, no $99 Apple account.
- **Hosting on the founder's PC** for now: a LAN URL for development; the Cloudflare Tunnel https URL (D13) when the domain exists.

## Owned paths (new; inside Messenger's own folder)

- `apps/messenger/mobile/`: an Expo app
- `apps/messenger/desktop/`: an Electron app
- `docs/submissions/messenger/shells.md`

**Nothing else.** Never touch `apps/web`, `main`, other entries or shared paths. **Old-name gate:** `git grep -n -i -e "m[i]rsal" -- apps/messenger apps/api/app/messenger` must print nothing.

## Deliverables

1. **iPhone shell (`apps/messenger/mobile/`, Expo SDK compatible with Expo Go).**
   - One screen: `react-native-webview` loading `MESSENGER_URL` (default: the PC's LAN address for the Vite app; the tunnel https URL later).
   - **WebSocket chat must work inside the WebView.** The Origin-bound WS tickets accept the configured host through env (D13), never hard-coded.
   - Microphone permission prompt for voice notes (Expo Go supports `expo-av` permissions); photo picker for media and cut-out stickers (`expo-image-picker`) bridged to the web upload.
   - Plus: an offline / error screen with Retry; external links opened in the system browser; the session kept across launches.
   - App name **"Messenger"** (working name, D11) and its own icon. No old-name marks.
   - Run with `npx expo start`, then Expo Go on the founder's iPhone.
2. **Desktop shell (`apps/messenger/desktop/`, Electron).**
   - A `BrowserWindow` loading `MESSENGER_URL` (default `http://localhost:5173`, or the built app + API `:8070`).
   - Security: `contextIsolation`, no `nodeIntegration`, `sandbox`, an origin allowlist, external links opened in the browser.
   - Desktop notifications for new messages through the web Notification API (no Node).
   - Window state, tray icon optional, an unsigned Windows build via `electron-builder`.
   - Copy the security patterns from Dubai-io's desktop app (`git show desktop:apps/desktop/electron/main/security.ts`): reference only.
3. **One start script** + `shells.md`: start the API (:8070) and web app bound for LAN, the desktop shell, and the Expo QR. Document the PC firewall and LAN steps.
4. **Tests:**
   - desktop: off-origin navigation blocked, external links handled, `nodeIntegration` off;
   - mobile: URL config, the error screen, the WS connect smoke test against the local API.
   - Plus §4 gates, the Messenger test / build commands, the old-name gate.

**Done when:** the desktop `.exe` opens Messenger from the PC with live two-user chat; the iPhone (Expo Go) sends and receives a message over the LAN; the gates pass. Add an entry to `docs/submissions/messenger/log.md` with screenshots.
