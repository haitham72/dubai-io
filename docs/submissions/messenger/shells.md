# Messenger Shells — iPhone (Expo Go) + Desktop (Electron)

Thin native shells wrapping the Messenger web app (`apps/messenger`) without rewriting the UI or touching `apps/web` or `main`.

## Architecture

- **Web app (`apps/messenger/`)**: Vite + React client on `:5173`, proxying `/api/identity` and `/api/messenger` (HTTP + WebSocket) to `MESSENGER_API_URL` (default `http://127.0.0.1:8070`).
- **Backend (`apps/api/app/messenger/server.py`)**: FastAPI server on `:8070` serving `/api/identity/*`, `/api/messenger/*`, and the Origin-bound `/api/messenger/ws` WebSocket (`app/messenger/hub.py` + `app/messenger/routes_chat.py`).
- **iPhone shell (`apps/messenger/mobile/`)**: Expo Go TypeScript app using `react-native-webview`, `react-native-safe-area-context`, `expo-av`, and `expo-image-picker`.
- **Desktop shell (`apps/messenger/desktop/`)**: Electron TypeScript app with hardened `webPreferences`, single-origin allowlist, origin-gated `notifications` & `media` permissions, offline retry fallback, and `electron-builder` unsigned Windows `.exe` packaging.

## LAN & WebSocket Origin Environment (`MESSENGER_ALLOWED_ORIGINS`)

`apps/api/app/messenger/routes_chat.py` validates the WebSocket `Origin` header on `/api/messenger/ws` against `get_allowed_origins()` (`apps/api/app/messenger/hub.py`), which reads comma-separated origins from `MESSENGER_ALLOWED_ORIGINS`.

To allow both local Electron (`http://localhost:5173`) and an iPhone on the same Wi-Fi/LAN (`http://<LAN_IP>:5173`) to connect to `/api/messenger/ws`:

```powershell
$env:MESSENGER_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://<LAN_IP>:5173,http://localhost:4173,http://127.0.0.1:4173,http://<LAN_IP>:4173"
$env:MESSENGER_API_URL = "http://127.0.0.1:8070"
```

When using a Cloudflare Tunnel URL (D13), append its HTTPS origin (e.g. `https://<host>.trycloudflare.com`) to `MESSENGER_ALLOWED_ORIGINS` (or set `MESSENGER_TUNNEL_URL` before running `start-shells.ps1`) and set `MESSENGER_TUNNEL_HOST` for Vite.

## Windows Firewall (TCP `5173` and `8070`)

For an iPhone running Expo Go on the same Wi-Fi network to reach your PC, Windows Firewall must allow inbound TCP traffic on ports `5173` (Vite web app) and `8070` (FastAPI backend). Run in an **elevated (Administrator) PowerShell**:

```powershell
netsh advfirewall firewall add rule name="Messenger Dev TCP 5173" dir=in action=allow protocol=TCP localport=5173
netsh advfirewall firewall add rule name="Messenger Dev TCP 8070" dir=in action=allow protocol=TCP localport=8070
```

## One-Command Start Script (`apps/messenger/scripts/start-shells.ps1`)

The start script auto-detects the active LAN IPv4 address, populates `MESSENGER_ALLOWED_ORIGINS` and `MESSENGER_API_URL`, checks Windows Firewall rules for TCP `5173` and `8070` (printing the `netsh` commands cleanly when non-admin), and starts the API (`0.0.0.0:8070`) and Vite (`0.0.0.0:5173`):

```powershell
# Preflight check only (no background servers started)
pwsh -File apps/messenger/scripts/start-shells.ps1 -CheckOnly

# Start API (:8070) + Vite (:5173) bound on 0.0.0.0
pwsh -File apps/messenger/scripts/start-shells.ps1

# Optional flags: -LaunchDesktop, -LaunchExpo, -ConfigureFirewall (when elevated), -LanIp <ip>
```

## iPhone Expo Go Shell (`apps/messenger/mobile/`)

### Features
- Loads `EXPO_PUBLIC_MESSENGER_URL` (defaults to `http://localhost:5173`) inside `react-native-webview` with cookie/session persistence (`sharedCookiesEnabled`), safe-area layout, an in-app **LAN URL** switcher, and an offline/error screen with **Retry**.
- Enforces single-origin navigation inside the WebView (`src/config.ts`); external `http:`/`https:`/`mailto:`/`tel:` links open in iOS Safari / system handler via `Linking.openURL`.
- **WebView JS Bridge (`src/bridge.ts`)** injected before content loads (`window.__messengerMobileBridge` / `window.ReactNativeWebView` ↔ `injectJavaScript` `messenger:native` event):
  - `REQUEST_MIC`: prompts `Audio.requestPermissionsAsync()` (`expo-av`) and enables iOS recording mode.
  - `START_VOICE_RECORDING` / `STOP_VOICE_RECORDING`: records audio via `expo-av` `Audio.Recording` and returns `{ uri, durationMs }`.
  - `PICK_MEDIA`: requests photo library permission (`expo-image-picker`) and returns selected image/video URI + metadata + `base64`.
  - `PICK_STICKER`: opens `expo-image-picker` with `1:1` square crop editing and `base64` output for sticker sharing/cut-out.

### Run on iPhone (Expo Go)

```powershell
cd apps\messenger\mobile
npm install
$env:EXPO_PUBLIC_MESSENGER_URL = "http://<LAN_IP>:5173"
npx expo start
```

Scan the QR code with the iOS Camera / Expo Go app on the same Wi-Fi network (or tap **LAN URL** in the top bar to enter `http://<LAN_IP>:5173` directly).

## Electron Desktop Shell (`apps/messenger/desktop/`)

### Features & Security
- Loads `MESSENGER_URL` (or `VITE_MESSENGER_URL`, default `http://localhost:5173`).
- Hardened `webPreferences` (`electron/security.ts`): `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, `webSecurity: true`, `allowRunningInsecureContent: false`, `webviewTag: false`.
- Blocks off-origin `will-navigate` and `setWindowOpenHandler`, forwarding safe external links to `shell.openExternal`.
- Persists window bounds/maximized state in `userData/window-state.json` and shows an offline/retry screen (`electron/offline.html`) on main-frame load failure.
- **Origin-gated permissions & Windows desktop notifications**:
  - Sets `app.setAppUserModelId("app.messenger.desktop")` for Windows toast notifications.
  - `session.defaultSession.setPermissionCheckHandler` and `setPermissionRequestHandler` allow `notifications` and `media` (microphone) **only** for the configured Messenger origin; all other origins and permissions are denied fail-closed.
  - Supports the web `Notification` API as well as `window.messengerDesktop.notify(title, body)` via allowlisted preload IPC.

### Run & Build Unsigned Windows `.exe`

```powershell
cd apps\messenger\desktop
npm install
npm start          # TypeScript build + launch Electron against MESSENGER_URL
npm run build      # Compiles TS and builds unsigned portable Windows .exe in dist/
```

The unsigned portable executable is written to `apps/messenger/desktop/dist/Messenger-portable-0.1.0.exe` (`win.signAndEditExecutable: false`).

## Verification & Test Commands

```powershell
# Mobile unit tests & typecheck
cd apps\messenger\mobile
npm run typecheck
npm test

# Desktop unit tests, typecheck & unsigned .exe build
cd apps\messenger\desktop
npm run typecheck
npm test
npm run build

# Messenger web app gates
cd apps\messenger
npm run typecheck
npm run build
npm run test:photo-window
npm run test:store

# D1 old-name gate (must return 0 matches / exit 1)
git grep -n -i -e "m[i]rsal" -- apps/messenger apps/api/app/messenger docs/submissions/messenger
```
