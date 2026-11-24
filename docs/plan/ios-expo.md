# Dubai-io Mobile Companion — Expo Go Architecture & Build Plan (`ios` Branch)

**Date:** 23 Nov 2026 · **Status:** Approved Integration Plan (`HANDOFF_GEMINI.md` §4) · **Target Device:** iPhone 13 Pro Max running **Expo Go** (App Store, **no `$99` Apple Developer account, no Mac, no Xcode, no Swift**)

---

## 1. Canon Decision & One-Design-System Strategy

| Topic | Previous Canon (`PLAN.md` / `ARCHITECTURE.md`) | Updated Founder Ruling (23 Nov 2026) | Plan Action |
|---|---|---|---|
| Mobile stack | React `apps/site` + Capacitor (`UI paused 9 Nov`) | **Expo (React Native + TypeScript) + `expo-router` via Expo Go** (`apps/mobile/`) | Recorded in `docs/request-backlog.md` (`## Feature decisions`); `apps/ios` SwiftUI stays stopped; `apps/web` stays frozen (`mobile-pwa-baseline-2026-10-23`). |
| Shared design system | Single web codebase CSS variables | **`packages/design-tokens/`** (framework-agnostic TypeScript + JSON palette, spacing, radii, typography) consumed by `apps/mobile/` now and adoptable by `apps/site` / `apps/desktop/` later without refactoring `apps/site` on this branch. | Build `packages/design-tokens/` cleanly alongside `apps/mobile/`. |

---

## 2. Expo Go Constraints & LATER (`$99` Account) Boundary

**Hard invariant:** `apps/mobile/` uses **only standard Expo SDK / pure-JS modules** compatible with the App Store **Expo Go** runtime — zero custom native modules, zero Podfiles, zero custom Swift/Kotlin bridges.

### In Scope (Works Today on Windows + iPhone Expo Go)
- `expo` + `expo-router` (file-based 4-pillar tab/stack navigation)
- `expo-web-browser` + `expo-auth-session` (Google OAuth via server-side `/api/auth/google/start` + `dubaiio://` return)
- `expo-document-picker` (manual WhatsApp `.txt` export upload & Takeout `.zip`/`.json` backfill)
- `react-native-svg` (Memory Vault Constellation graphs)
- `expo-secure-store` (device token / configured API base URL)
- `expo-audio` / microphone UI trigger stub (honest recording/transcript preview — never fake speech-to-text if disabled)

### Deferred → `LATER ($99 Apple Developer Account / Custom Dev Build)`
- Remote APNs push notifications on standalone IPA builds
- TestFlight distribution & App Store release pipeline (`eas build` native binaries)
- iOS Share Extension (`Share to Dubai-io` directly from YouTube app — requires native target entitlement; in Expo Go users copy/paste URL or use Takeout → Drive)
- Background HealthKit / Contacts / local Chrome access (`unavailable` per `docs/connectors/README.md`)

---

## 3. Visual Design Spec (`design/20-11-2026/INDEX.md`)

Strictly implements the locked 20 Nov Quest visual language (`tokens` in `packages/design-tokens/`):
- **Surface & Lighting:** Light mode first (`#FFFFFF` canvas, `#FAF8F5` warm surface, `#1E2022` user bubble), **ZERO shadows** (`shadowOpacity: 0`, `elevation: 0`; separation solely via `1px` `#E8E8EC` / `rgba(0,0,0,0.06)` hairline borders and `#E8D5A3` gold borders).
- **Accents & Life Clusters:** Brand gold (`#C5A059`, `#D4AF37`, `#FDF8EE`), and the 6 theme hues (`Career #2F80ED`, `Projects #9B51E0`, `Learning #F2994A`, `Gaming #EB5757`, `Travel #00B4D8`, `Health #27AE60`).
- **Four-Pillar Bottom Capsule Dock:** **`Today` · `Chat` · `Quests` · `Memory`** with central floating audio waveform button.
- **Screen Contracts & Canon Rules (`CLAUDE.md` Rules 1–10):**
  1. **`Today`:** Personalized greeting (`Good morning, Karim`), Dubai location/date header, Weekly Recap hero card, 3:4 aspect-ratio horizontal card carousels (`~78%` viewport width so `~18%` of the next card peeks on the right), `"Because…"` chip backed by provenance, and a **`Demo data`** pill on synthetic/fixture cards.
  2. **`Chat`:** Plain AI text (not boxed), dark `#1E2022` user bubble, crisp white outlined action cards, warm gold **Proactive Ping & Memory Repair** card, Life Category drawer, and **`✓ Ingested into Temporal Memory`** badge rendered **strictly after** a real applied backend confirmation (`applied_fact_ids.length > 0` or `POST /api/memory/chat/turn` `ok: true` — **never** optimistically faked per Rule 1).
  3. **`Memory` (Knowledge Vault):** Segmented `[Subjects]` | `[People & Places]` switcher, SVG interactive constellation (`Subjects` clustered across the 6 themes; `People & Places` showing **`T1` Inner Circle** boundary), verified fact list, and tap-through **`/v1/owners/{owner}/why/{fact_id}`** evidence + `processed_by` + `as_of` drawer.
  4. **`Quests`:** Goal cards & honest milestone states (`done`, `in_progress`, `planned`) from `/v1/owners/{owner}/quests` — never fabricated `Done` states.

---

## 4. Networking & Backend Contract (`LAN IP` / `--tunnel`, Never `localhost`)

- A real iPhone cannot reach `http://localhost:8000`. `apps/mobile` reads an editable API Base URL (`SecureStore` / Settings screen, initialized from `EXPO_PUBLIC_API_URL` e.g. `http://192.168.x.x:8000` or tunnel URL) and explicitly validates against bare `localhost` warnings on real devices.
- **Endpoints consumed:**
  - `apps/api`: `GET /api/health`, `POST /api/luna/turn`, `POST /api/memory/chat/turn`, `GET /api/memory/chat/pings`, `GET /api/memory/timeline`, `GET /api/auth/google/start`, `POST /api/connectors/*`
  - `apps/memory` Vault API: `GET /v1/owners/{owner}/vault/subjects`, `GET /v1/owners/{owner}/vault/people`, `GET /v1/owners/{owner}/why/{fact_id}`, `GET /v1/owners/{owner}/quests`
- **Initial demo mode:** Defaults to synthetic owner **`karim`** (`Demo data` pill visible wherever fixture data is rendered or API is offline, never hiding fallback status).

---

## 5. Sign-In, Connectors & Onboarding (`docs/plan/onboarding-youtube-sources.md`)

- **Google Sign-In:** Opens `apps/api`'s server-side `/api/auth/google/start` inside `expo-web-browser` (`WebBrowser.openAuthSessionAsync`), returning to the app via deep link without storing Google client secrets in the mobile bundle.
- **YouTube Watch History Onboarding (Region-Aware per `onboarding-youtube-sources.md`):**
  - *Step 1 (Instant):* YouTube Data API v3 (`uploads`, `liked`, `subscriptions`, `playlists`).
  - *Step 2A (EEA / UK / Switzerland):* Google Data Portability API (`dataportability.myactivity.youtube`).
  - *Step 2B (UAE / Dubai & Global):* Guided Takeout schedule (`Export every 2 months for 1 year` → `Add to Drive`) auto-synced by `google_drive`, plus manual Takeout upload via `expo-document-picker`.
- **WhatsApp:** Manual `.txt` export upload only via `expo-document-picker` (no Baileys/linked-device automation).
- Onboarding progress cards show honest state transitions (`Not connected` → `Authorizing / Waiting for Takeout drop in Drive` → `Syncing` → `Ready (X days counted)`). Core 4-pillar screens ship first; onboarding card wires into the **Connect / Settings** flow right after.

---

## 6. Build Order & Verification Matrix

Disjoint split for parallel sub-agents / teams:
1. **`I-A` (`packages/design-tokens/` + core Expo shell):** Design tokens (`colors`, `spacing`, `radii`, `typography`), `expo-router` 4-pillar capsule dock + audio orb, `Today` 3:4 peeking carousels, `Chat` (proactive repair + Rule-1 `"✓ Ingested into Temporal Memory"` badge + drawer), API client (LAN/tunnel URL, synthetic `karim` demo fallback + `Demo data` pill), `apps/mobile/README.md`, Jest + React Native Testing Library tests.
2. **`I-B` (`apps/mobile/src/features/{vault,quests,connect}/`):** Dual-view Memory Vault (`Subjects` & `People & Places` SVG constellation + `T1` badge + `why/{fact_id}`), `Quests` milestones, `Connect / Onboarding` (Google OAuth via `expo-web-browser`, WhatsApp `.txt` upload via `expo-document-picker`, region-aware YouTube onboarding progress card), Jest + RTL tests.

Verify before merging any branch into `ios`: `npm test` (Jest/RTL green), `npx tsc --noEmit` (0 type errors), and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web`.

---

## 7. Run Instructions Summary (`apps/mobile/README.md`)

1. Install **Expo Go** from the App Store on the iPhone 13 Pro Max.
2. Start backend locally on PC bound to `0.0.0.0:8000`.
3. From `apps/mobile/`: run `npm install` then `npx expo start --tunnel` (or `npx expo start --lan` on the same Wi-Fi).
4. Scan the terminal QR code with the iPhone Camera app (opens in Expo Go).
5. In the app's **Connect / Settings** screen, set the API URL to your PC's LAN IP (`http://192.168.x.x:8000`) or tunnel URL (never `localhost`).
