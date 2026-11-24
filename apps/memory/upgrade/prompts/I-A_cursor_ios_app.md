# I-A — Cursor: `packages/design-tokens` + `apps/mobile` Expo Go Core (`Today`, `Chat`, 4-Pillar Dock)

Paste below the line into **Cursor**.

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and `docs/plan/ios-expo.md` (on branch `ios`) first. Key rules:
- **Never edit `G:\Haitham\VsCode\contest`** (`main`), **never touch `apps/web`** or `apps/ios` (SwiftUI stays stopped), **never touch `apps/site`** on this branch.
- **No `$99` Apple Developer account / no Mac / no custom native code:** use only pure-JS / standard **Expo Go** SDK packages (`expo`, `expo-router`, `expo-secure-store`, `react-native-svg`, etc.).
- **No real personal data** in fixtures or components — synthetic **Karim Haddad** demo data only, and every fixture view MUST show a visible `Demo data` pill (`CLAUDE.md` Rule 2).
- **Zero shadows** (`shadowOpacity: 0`, `elevation: 0`): crisp hairline `1px` borders only (`design/20-11-2026/INDEX.md`).

Sub-agents: optional (1–2 on Cursor's fast model). Commit only on your own branch.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-ios-app -b ios-app ios
cd G:\Haitham\VsCode\contest-ios-app
```

### Strictly Owned Paths (do NOT create files inside `apps/mobile/src/features/{vault,quests,connect}/` — Muse owns those in I-B)
- `packages/design-tokens/` (new shared TS + JSON design tokens package: colors, 6 life-theme hues `#2F80ED/#9B51E0/#F2994A/#EB5757/#00B4D8/#27AE60`, brand gold `#C5A059/#D4AF37/#FDF8EE/#E8D5A3`, light canvas `#FFFFFF/#FAF8F5`, radii, spacing, typography, `cardAspectRatio: 3 / 4`, `shadow: 'none'`)
- `apps/mobile/` scaffold (`package.json`, `app.json`, `tsconfig.json`, `babel.config.js`, `jest.config.js`, `README.md`)
- `apps/mobile/app/` (`_layout.tsx`, `index.tsx` -> `Today`, `chat.tsx` -> placeholder/host, plus tab slots mounting `VaultScreen` / `QuestsScreen` / `ConnectScreen` cleanly or clean fallback stubs if `src/features/*` isn't merged yet)
- `apps/mobile/src/components/` (`CapsuleDock.tsx`, `DemoPill.tsx`, `TodayCarouselCard.tsx`, `ChatMessageList.tsx`, `ProactiveRepairCard.tsx`, `MemoryIngestedBadge.tsx`, `LifeDrawer.tsx`)
- `apps/mobile/src/lib/` (`api.ts`, `fixtures.ts`, `types.ts`)
- `apps/mobile/__tests__/` (Jest + React Native Testing Library tests)

### Deliverables
1. **`packages/design-tokens/`:** Exports TypeScript constants + JSON matching `design/20-11-2026/INDEX.md` (`light` mode first, zero shadows).
2. **`apps/mobile/` Expo Go App Scaffold & 4-Pillar Dock:**
   - Bottom floating capsule dock (`Today` · `Chat` · `Quests` · `Memory`) with central audio waveform orb button (press shows honest `"Voice capture preview"` toast/modal — never fake transcription).
   - Export clean navigation props / interfaces in `src/lib/types.ts` so Muse's `src/features/{vault,quests,connect}/` drop cleanly into the tabs on merge.
3. **Screen 1 — `Today` (`design/20-11-2026/` Screen 1A & 1B):**
   - Header (`Dubai-io` serif branding + `Quest VIP` badge + gear icon linking to Connect/Settings), greeting (`Good morning, Karim`), Dubai location/date line, Weekly Recap hero card.
   - 3:4 horizontal carousels (`~78%` viewport card width so next card peeks `~18%` on the right), `"Because…"` provenance chip, and `Demo data` pill on synthetic Karim cards.
4. **Screen 2 — `Chat` (`design/20-11-2026/` Screen 2A & 2B):**
   - Plain unboxed AI text, `#1E2022` user bubbles, crisp white outlined action boxes, `#FDF8EE` Proactive Memory Repair card (`Apology Accepted 👍`).
   - **Rule 1 Temporal Memory Badge (`✓ Ingested into Temporal Memory`):** MUST render **only** when `POST /api/memory/chat/turn` (or Vault apply) returned real applied confirmation (`applied === true` / `ok === true`); never show it optimistically on send failure or offline demo turns.
   - Slide-in Life Category & Thread History drawer (`2B`).
5. **Networking (`src/lib/api.ts`) & `apps/mobile/README.md`:**
   - Configurable API Base URL (defaulting from `EXPO_PUBLIC_API_URL`, warning if bare `localhost` is entered on a real device; calls `/api/health`, `/api/luna/turn`, `/api/memory/chat/turn`, `/api/memory/chat/pings`).
   - Honest fallback to synthetic `karim` fixtures when offline, visibly tagged `Demo data`.
   - `apps/mobile/README.md`: step-by-step guide for iPhone 13 Pro Max (**App Store Expo Go** -> `npx expo start --tunnel` -> scan QR -> set PC LAN IP or tunnel URL in Connect/Settings).
6. **Tests (`apps/mobile/__tests__/`):**
   - Token palette & zero-shadow invariants;
   - `Today` renders 3:4 cards, `"Because…"` chip, and `Demo data` pill;
   - `Chat` renders `✓ Ingested into Temporal Memory` **strictly** after confirmed backend response (negative test: omitted when API errors/offline);
   - API client handles LAN URL validation (warns on `localhost`) and unreachable backend fallback.

**Done when** `npm test` and `npx tsc --noEmit` in `apps/mobile/` are green, and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes. Commit on `ios-app` and report: branch, counts, README run command.
