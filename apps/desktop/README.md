# Dubai-io Desktop

Windows shell. Dubai-io's Electron main process and preload are in `electron/`, and the Vite UI is in `renderer/`. Follow E1 for the full local stack, E2 for PC Google sign-in, and E3 for consented desktop sources (`apps/memory/upgrade/prompts/`). The standalone renderer and owner-device instructions below are development setup.

Light canvas, gold accent, 1px borders. Fixture rows say **Demo data**. No real personal history is in the repo.

## Run the renderer

```powershell
cd apps\desktop\renderer
npm install
npm run dev
```

Open `http://127.0.0.1:5174`. Without Electron, the page uses a demo bridge and does not read your disk.

To load it inside Electron after both packages are installed, start the renderer, then launch Electron with the main entry pointing at that URL. The preload exposes `window.dubaiDesktop`. The renderer calls only those allowlisted methods.

## Checks

```powershell
cd apps\desktop\renderer
npm test
npm run build
```

## Owner-device token (development setup)

The token is encrypted in the main process (`safeStorage`). Settings shows a mask, never the bearer string. In the app, open **Settings**, pick a model (`claude-sonnet-4-5`, `claude-haiku-4-5`, or `o3-mini`), then turn on **Process on your own Claude/Codex ($0 app cost)**. Source consent switches start off.

## Unsigned Windows build

Code signing is **LATER** (no certificate). From `apps/desktop`, after `npm install` in both this folder and `renderer/`, and after `npm run build` inside `renderer/`:

```powershell
npx electron-builder --win --config electron-builder.yml
```

That writes an unsigned NSIS installer and a portable exe under `dist-electron/`. `signAndEditExecutable` is false.
