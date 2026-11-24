# E2 — Google sign-in on the PC, QR pairing for the iPhone, and the app wired to the real account (Gemini; reassigned from Cursor 24 Nov)

Read `E0_real_data_round.md` first. Branch `e2/signin` from `main`.

## What exists (build on it; don't rebuild)

- **`apps/api/app/identity/`** (prefix `/api/identity`): `/me`, `/sessions` (create / delete / revoke-all), **`/links/start` + `/links/complete`** (device linking), **`/memory-device-token`** (an account-scoped token for the memory engine), `/adopt-session`, `/ws-ticket`. Verified on local Supabase GoTrue (Gate S).
- **`apps/api/app/oauth.py`** + **`apps/api/app/connectors/`** (Google OAuth helpers; encrypted token storage in `crypto.py`).
- **`apps/mobile`** uses `DEMO_OWNER_ID` and a `demo` flag in `app/chat.tsx`, `memory.tsx`, `quests.tsx`; settings in `useApiSettings`; `ConnectScreen` / `ConnectFallback` take a manual API URL.

## Owned files

- `apps/mobile/**` (not `features/vault` styling: function only)
- `apps/desktop/**` (sign-in + token only)
- `apps/api/app/identity/**` only if the sign-in / pairing flow needs a missing piece (say what and why)
- tests for all of the above

## Deliverables

1. **Sign in with Google on the PC.**
   - **Website (Expo web):** "Sign in with Google" → the OAuth through `apps/api` / GoTrue with a **localhost redirect** → the `apps/api` session → `/api/identity/me` shows the founder.
   - **Desktop app:** the same flow (localhost loopback), stored in the OS keychain (`safeStorage`).
   - Report the exact redirect URIs the founder must add in Google Cloud Console.
2. **QR pairing for the iPhone.**
   - The signed-in website shows "Pair your iPhone" → `/links/start` → a QR with a short-lived, one-time code (≤ 5 min).
   - The Expo Go app scans it (`expo-camera`) → `/links/complete` → the phone gets **its own session** (listed and revocable in `/sessions`).
   - The phone never sees Google tokens or service tokens.
   - Failure paths: expired code, reused code, wrong network: clear messages.
3. **The real account everywhere.**
   - **Remove `DEMO_OWNER_ID` from normal mode.** Every screen (Today, Chat, Quests, Memory, Connect) uses the signed-in owner through `apps/api`, the single gateway (the phone never calls the memory engine directly).
   - The demo stays available **only** behind an explicit "Demo mode" toggle, with the Demo data pill.
   - A sign-out, and "Signed-in devices" with revoke.
4. **Desktop sync uses the same account.** The continuous-sync and import IPC use the owner's `memory-device-token` from `/memory-device-token` (owner-scoped, revocable).
5. **App side of E4:**
   - **Chat** sends turns to E4's chat endpoint and renders its reply with citation chips.
   - **Today** renders E4's feed DTO (image, title, source chip, `as_of`, "Because…").
   - Until E4 lands, use the DTO from `reports\E4.md` if present; otherwise show a clear "Feed not ready" state (not fake data).
6. **Isolation test:** two synthetic accounts. A's facts, cards and graph never appear for B (API tests + one app-level test).
7. **Tests:**
   - jest + `tsc` (`apps/mobile`), vitest (`apps/desktop`), pytest for any `apps/api` changes;
   - plus the manual run sheet in the report: sign in on PC → pair iPhone → see own name on both → revoke the phone → the phone is signed out.

**Report** → `reports\E2.md`, with the redirect URIs and the manual run sheet.
