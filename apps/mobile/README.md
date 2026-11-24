# Dubai-io on iPhone and web

Use Expo Go on iPhone and run `npm run web` for the website. The E2 acceptance flow signs in with Google on the PC and pairs the iPhone with an account QR. The Expo Go development QR opens the app. Manual API URL configuration (below) is development setup.

Companion shell for Today, Chat, Quests, and Memory. It runs in the App Store **Expo Go** app. No Apple Developer account, no Mac, and no custom native code.

Synthetic owner: **Karim Haddad**. Fixture cards show a **Demo data** pill. The `✓ Ingested into Temporal Memory` badge appears only after `POST /api/memory/chat/turn` returns `applied: true` or `ok: true`.

## Run on an iPhone (development setup)

1. Install **Expo Go** from the App Store.
2. On the PC, start the API bound to all interfaces, for example `uvicorn` on `0.0.0.0:8000`.
3. From this folder:

   ```powershell
   cd G:\Haitham\VsCode\contest-ios-app\apps\mobile
   npm install
   npx expo start --tunnel
   ```

   Same Wi-Fi can use `npx expo start --lan` instead of `--tunnel`.
4. Open the Camera app on the iPhone and scan the QR code in the terminal. It opens in Expo Go.
5. In the app, tap the gear on Today (Connect / Settings). Set the API base URL to the PC LAN address, such as `http://192.168.1.20:8000`, or to the tunnel URL. Do not use `localhost` — the phone cannot reach the PC that way. A localhost value shows a warning and chat stays on demo data.

`EXPO_PUBLIC_API_URL` is the default until a URL is saved on the device.

## Checks

```powershell
npm test
npx tsc --noEmit
```

Quests, Memory, and the full Connect onboarding screens mount from `src/lib/feature-slots.ts` when those feature modules exist. Until then the tabs show an honest fallback.
