# I-C — Cursor: Non-Blocking Gamified Onboarding ("Knows You 36%") & Mobile Context Reveal (`ios` Branch, Phase 2)

Paste below the line into **Cursor** once `I-A` and `I-B` are merged on `ios`.

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and `docs/plan/gamified-onboarding-and-analytics.md` (on branch `ios`) first.
- **Never block app entry:** unlike the old Quest app (which refused to open until WhatsApp and YouTube archives were uploaded), Dubai-io opens immediately after Google login at **`36%` context completeness** and uses gamified progress + live reveal cards to guide the user to log in on **Dubai-io Desktop** on their PC.
- **Zero shadows** (`1px` hairline borders only), light mode first, `Demo data` pill on synthetic Karim fixtures.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-ios-gamified -b ios-gamified ios
cd G:\Haitham\VsCode\contest-ios-gamified
```

### Deliverables (`apps/mobile/`)
1. **Gamified Context Completeness Ring & Banner (`src/features/connect/CompletenessRingCard.tsx`):**
   - Deterministic percentage calculator matching `docs/plan/gamified-onboarding-and-analytics.md` §3:
     - Mobile Google OAuth (Gmail `14%` + Calendar `10%` + YouTube Data API v3 likes/subscriptions/playlists `12%`) = **`36%`** immediately after mobile sign-in.
     - Optional mobile exports: WhatsApp `.txt` (`+15%`), YouTube Watch History (`+12%`).
     - Desktop companion sources: Chrome/Edge history (`+18%`), local AI/coding sessions (`+19%`).
   - Renders: **`"Dubai-io knows you 36% · Log in on Dubai-io Desktop on your PC to add more context (+37%)"`** with a one-tap *"Pair Desktop / Copy PC Setup Link"* CTA and an always-enabled *"Explore App Now"* dismissal (never blocks navigation).
2. **"Here Is What I Know About You for Now…" Reveal Section (`src/features/connect/InitialRevealCard.tsx`):**
   - Lists top verified facts & active interests discovered so far (grouped by life theme, with `src:` evidence, `as_of`, and `Confirm` / `Edit` / `Not true` / `Forget` actions).
3. **User Analytics Summary (`src/features/vault/UserAnalyticsCard.tsx`):**
   - Life-Theme distribution across the 7 spines + **Rising 21-Day Interests vs. Baseline** badge;
   - Cross-source signal mix (`gmail`, `youtube:interests`, `whatsapp`, `browser`, `agent:claude-code`, `agent:codex`, `ai:chatgpt`, `takeout:*`);
   - **Rule-9 Privacy Shield Counter** (`N sensitive items held back — health, faith, politics, credentials never inferred`) + `$0 app cost` owner-hook attribution counter.
4. **Tests (`apps/mobile/__tests__/gamifiedOnboarding.test.tsx`):**
   - Fresh Google sign-in computes `36%` and **never blocks** the 4-pillar dock;
   - Connecting Desktop Chrome + AI sessions jumps completeness from `36%` → `73%+`;
   - Reveal cards render `Confirm` / `Forget` and `src:` evidence;
   - Rule-9 held-back count and `Demo data` pill render accurately.

**Done when** `npm test` and `npx tsc --noEmit` in `apps/mobile/` pass and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes. Commit on `ios-gamified` with a clear commit message and report branch + test counts.
