# I-B — Muse: `apps/mobile` Memory Vault, Quests & Onboarding/Connectors (`ios` Branch)

Paste below the line into **Muse**.

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md`, `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\SUBAGENTS.md`, `docs/plan/ios-expo.md`, and `docs/plan/onboarding-youtube-sources.md` (on branch `ios`) first. **Sub-agents: Muse 1.3 Contributor only (never Wonder).** Key rules:
- **Never edit `G:\Haitham\VsCode\contest`** (`main`), **never touch `apps/web`** or `apps/ios`.
- **Expo Go safe only:** pure-JS / standard Expo SDK modules (`expo-web-browser`, `expo-auth-session`, `expo-document-picker`, `expo-secure-store`, `react-native-svg`) — no custom native iOS modules.
- **No real personal data** in fixtures or tests — use synthetic **Karim Haddad** corpus only, and show `Demo data` pill on every fixture view (`CLAUDE.md` Rule 2).

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-ios-vault -b ios-vault ios
cd G:\Haitham\VsCode\contest-ios-vault
```

### Strictly Owned Paths (100% disjoint from Cursor's I-A scaffold)
Create everything inside:
- `apps/mobile/src/features/vault/` (`VaultScreen.tsx`, `SubjectsConstellation.tsx`, `PeoplePlacesConstellation.tsx`, `WhyProvenanceSheet.tsx`, `vaultApi.ts`, `vaultFixtures.ts`)
- `apps/mobile/src/features/quests/` (`QuestsScreen.tsx`, `questsApi.ts`, `questsFixtures.ts`)
- `apps/mobile/src/features/connect/` (`ConnectScreen.tsx`, `YoutubeOnboardingCard.tsx`, `WhatsappImportCard.tsx`, `connectApi.ts`)
- `apps/mobile/__tests__/features/` (`vault.test.tsx`, `quests.test.tsx`, `connect.test.tsx`)

*(Do NOT edit `packages/design-tokens/`, `apps/mobile/package.json`, `apps/mobile/app/`, or `apps/mobile/src/components/` — Cursor owns those in `I-A`. Rely on standard React Native + `expo-web-browser`, `expo-document-picker`, `expo-secure-store`, `react-native-svg`, and accept `apiBaseUrl` / `owner` props + optional theme defaults.)*

### Deliverables
1. **Memory Vault (`src/features/vault/` — `design/20-11-2026/` Screen 3A & 3B):**
   - Light canvas `#FFFFFF` / `#FAF8F5`, **zero shadows** (`1px` hairline borders only).
   - Segmented control switching cleanly between **`Subjects`** (cluster colors for Career/Projects/Learning/Gaming/Travel/Health) and **`People & Places`** (showing **`T1` Inner Circle** badge & relationship tiers).
   - Interactive SVG constellation (`react-native-svg`) + Key Knowledge / Relationships verified list (`✓`).
   - Tap any verified fact to open **`WhyProvenanceSheet`**: fetches `GET /v1/owners/{owner}/why/{fact_id}` showing source records, `provenance`, `as_of`, `model` / `"your Claude"` badge (`cost_badge`), and falls back cleanly to synthetic Karim fixtures labeled `Demo data`.
   - **Rule 9 safety:** never surface quarantined sensitive categories or suppressed health/religion traits in Vault lists.
2. **Quests (`src/features/quests/`):**
   - Fetches `GET /v1/owners/{owner}/quests` (with synthetic Karim fallback labeled `Demo data`).
   - Displays goal cards and milestone chips strictly with honest states **`done`**, **`in_progress`**, or **`planned`** — never fabricate `done` (`CLAUDE.md` Rule 1).
3. **Connect & Onboarding Progress (`src/features/connect/` — per `docs/plan/onboarding-youtube-sources.md`):**
   - **API Server URL & Demo Toggle:** Editable PC LAN IP (`http://192.168.x.x:8000`) or `--tunnel` URL saved via `expo-secure-store`, with an explicit warning badge if `localhost` is entered on a mobile device, plus a **Test Connection** check against `GET /api/health` (honest reachable vs offline status).
   - **Google OAuth (`expo-web-browser`):** Launches `GET {apiBaseUrl}/api/auth/google/start` cleanly via `WebBrowser.openAuthSessionAsync` (never bundles client secrets).
   - **Region-Aware YouTube Onboarding Progress Card (`YoutubeOnboardingCard.tsx`):**
     - Region selector (`EEA / UK / Switzerland` vs `UAE / Rest of World`), defaulting cleanly and persisting choice.
     - Instant step: **YouTube Data API v3** (`uploads`, `liked`, `subscriptions`, `playlists`) status progress (`Not connected` → `Syncing` → `Ready`).
     - EEA branch: **Google Data Portability API** (`dataportability.myactivity.youtube`) OAuth connect state.
     - UAE / Global branch: guided **Google Takeout → Scheduled "Add to Drive"** (`Export every 2 months for 1 year`, `watch-history.json`) card showing `Waiting for first Takeout drop in Drive` + optional manual `Upload Takeout JSON/ZIP now` via `expo-document-picker` (and explicit note that only daily Rule-9 interest counts are stored, sensitive topics held back).
   - **WhatsApp Manual Export (`WhatsappImportCard.tsx`):** `expo-document-picker` picking `.txt` chat exports and uploading them cleanly (never Baileys/linked-device automation).
4. **Tests (`apps/mobile/__tests__/features/`):**
   - Note: run Jest or standalone TypeScript/React Native tests cleanly inside a scratch dev environment (or ensure pure TypeScript + `@testing-library/react-native` compatibility with standard `jest-expo`).
   - Test: `[Subjects]` ↔ `[People & Places]` toggle + `T1` badge + `WhyProvenanceSheet` (`as_of`, `provenance`, `"your Claude"` badge); honest Quests states; `localhost` warning on LAN URL input; EEA Data Portability vs UAE Takeout-to-Drive branching; WhatsApp document picker happy path + error handling; `Demo data` pills present when offline/fixture.

**Done when** `npx tsc --noEmit` (strict TS check on your files) and your feature test suite pass cleanly, and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes. Commit on `ios-vault` and report: branch, test counts, any contract requests for `I-A` integration.
