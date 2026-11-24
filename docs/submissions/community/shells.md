# Dubai-io Community Shells (Mobile Expo Go + Desktop Electron)

Thin native shells wrapping the existing Community web app (`apps/community/`) without rewriting its UI.

## Architecture

- **Web app (`apps/community/`)**: Next.js server on port `3060` (bound to `0.0.0.0:3060` for LAN access).
- **iPhone shell (`apps/community/mobile/`)**: Expo SDK 58 TypeScript app (`@dubai-io/community-mobile`) for **Expo Go** using `react-native-webview` and `react-native-safe-area-context`.
  - Reads `EXPO_PUBLIC_COMMUNITY_URL` (via `app.config.ts` / env) with fallback `http://localhost:3060` and an in-app **Server URL** sheet persisted via AsyncStorage.
  - Enforces same-origin in-app navigation (`isAllowedOrigin`), opens external `http`/`https`/`mailto`/`tel` links in Safari (`Linking.openURL`), blocks unsafe schemes (`javascript:`, `file:`, `data:`), preserves cookies across launches (`sharedCookiesEnabled`), supports pull-to-refresh, and renders an offline/error card with **Retry** and LAN troubleshooting hints.
- **Desktop shell (`apps/community/desktop/`)**: Electron TypeScript wrapper (`@dubai-io/community-desktop`) loading `COMMUNITY_URL` (default `http://localhost:3060`).
  - Hardened `webPreferences` (`contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, `webSecurity: true`, `webviewTag: false`).
  - Single-origin allowlist (`will-navigate` + `setWindowOpenHandler`), external `http`/`https`/`mailto` links via `shell.openExternal`, application menu, persisted window bounds (`window-state.json`), and a CSP-hardened offline fallback page with **Retry**.
  - Unsigned Windows portable `.exe` packaged via `electron-builder` (`signAndEditExecutable: false`).

## Prerequisites & LAN Setup (Windows PC + iPhone)

1. **Install dependencies** (first time):
   ```powershell
   cd apps\community
   npm ci
   cd mobile && npm install
   cd ..\desktop && npm install
   ```
2. **Allow Windows Firewall inbound TCP port 3060** (run once in an elevated PowerShell/CMD if your iPhone cannot reach the PC):
   ```powershell
   netsh advfirewall firewall add rule name="Dubai-io Community Dev 3060" dir=in action=allow protocol=TCP localport=3060
   ```
3. **Bind the Community server to `0.0.0.0:3060`**:
   ```powershell
   cd apps\community
   npm run dev -- -H 0.0.0.0 -p 3060
   ```

## One-Command Start Script

`apps/community/scripts/start-shells.ps1` detects your primary LAN IPv4 address, checks/adds the TCP `3060` firewall rule, starts the Next.js server bound to `0.0.0.0:3060`, launches the desktop shell, and starts Expo to print the QR code:

```powershell
# Full launch (web on 0.0.0.0:3060 + desktop shell + Expo Go QR)
powershell -ExecutionPolicy Bypass -File apps\community\scripts\start-shells.ps1

# Diagnostics only (prints LAN IPv4, firewall status, Expo & Electron commands)
powershell -ExecutionPolicy Bypass -File apps\community\scripts\start-shells.ps1 -CheckOnly
```

## Running on iPhone (Expo Go)

1. Connect your iPhone and Windows PC to the **same Wi-Fi** network.
2. Run `start-shells.ps1` (or manually set `$env:EXPO_PUBLIC_COMMUNITY_URL = "http://<PC-LAN-IP>:3060"` and run `npx expo start` inside `apps/community/mobile`).
3. Scan the QR code with the iPhone Camera app to open **Dubai-io Community** in **Expo Go**.
4. To switch later to a Cloudflare Tunnel HTTPS URL, tap **URL** in the top bar and enter `https://<tunnel-domain>`.

## Building & Running the Desktop Windows `.exe`

```powershell
cd apps\community\desktop
npm run pack:win
```

Output (gitignored under `apps/community/desktop/dist/`):
- `apps/community/desktop/dist/Dubai-io-Community-0.1.0-win-x64.exe` (unsigned portable Windows x64 executable).

To run in dev mode against a custom URL:
```powershell
cd apps\community\desktop
$env:COMMUNITY_URL = "http://localhost:3060"
npm start
```

## Tests & Verification

```powershell
# Community web app
cd apps\community
npm test
npm run build

# Mobile shell (URL normalization, origin allowlist, navigation classification, override storage)
cd apps\community\mobile
npm run typecheck
npm test

# Desktop shell (webPreferences invariants, origin allowlist, external link guard, window state)
cd apps\community\desktop
npm run typecheck
npm test
```
