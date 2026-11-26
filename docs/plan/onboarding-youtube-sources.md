# Onboarding Progress & Multi-Path YouTube Watch-History Ingestion

**Date:** 23 Nov 2026 · **Status:** Proposed Product/Connector Entry (for Orchestrator Review) · **Related:** `33ea030` (`docs/connectors/README.md`, `docs/plan/data-ingestion-runbook.md`, `docs/plan/Memory/memory.md`), `mem-wpF` (`ingest/youtube.py`), `mem-wpG` (`ingest/desktop/browser.py`)
**Date:** 23 Nov 2026 · **Status:** Reference Copy on `ios` (Source on `memory`: `0a0e5b7`) · **Related:** `33ea030`, `docs/plan/ios-expo.md`

---

## 1. Product Goal

New-user onboarding should show a clear **per-source progress experience** while choosing the lowest-friction watch-history pathway for the user's region and device — without forcing manual file exports where an automatic path exists, and without breaking Rule 9 or Google API rules.

---

## 2. Region & Platform Routing Matrix

| Lane | Who it covers | Transport | Automation & UX |
|---|---|---|---|
| **1. YouTube Data API v3 (Instant OAuth)** | All users (mobile & web, global) | Live OAuth (`youtube.readonly`) → `uploads`, `liked` (`LL`), `subscriptions`, `user playlists` | **Automatic incremental sync.** (Watch History `HL` was removed in 2016; Watch Later `WL` is restricted.) |
| **2. EEA / UK / Switzerland (Mobile or Web)** | Users located in EEA member states, UK, or Switzerland | **Google Data Portability API** (`dataportability.myactivity.youtube`) | **Automatic recurring sync** via OAuth (one-time or **30/180-day** recurring grants with time filters). Requires Google restricted-scope verification. |
| **3. Rest of World incl. UAE / Dubai (Mobile or Web)** | Users outside EEA/UK/CH | **Google Takeout → Scheduled "Add to Drive"** (`Export every 2 months for 1 year`, JSON `watch-history.json`) pulled by our Google Drive connector | **One-time setup, then automatic every 2 months** (plus optional immediate manual Takeout upload for instant backfill and OS Share Sheet per video). |
| **4. Desktop Logged-In Companion (Opt-In)** | Any user who also signs in on desktop | **Desktop Browser Consent Import** (`apps/memory` WP-G `ingest/desktop/browser.py`: `preview` → domain denylist → aggregated daily counts) | **One-click consent sync** of local Chrome/Edge/Brave history — lets watch history arrive when signing in on desktop without waiting for Takeout. |

---

## 3. Onboarding Progress Flow (New User UX)

During onboarding, each connected signal renders an explicit, honest state badge instead of a black box:

1. **YouTube Signals (Data API v3):** `Not connected` → `Syncing uploads/likes/subscriptions` → `Ready (N items)`
2. **Watch History (branching card by region/device):**
   - **EEA / UK / CH:** `Connect Google Data Portability (YouTube Activity)` → `Authorizing` → `Syncing` → `Ready (X days counted · Y sensitive held back)`
   - **UAE / Global (Mobile/Web):** Guided wizard:
     - Step A: `Open Google Takeout` (YouTube JSON only → `Add to Drive` → `Every 2 months for 1 year`)
     - Step B: `Waiting for first Takeout drop in Drive` (or `Upload Takeout JSON now` for instant backfill)
     - Step C: `Pulling from Google Drive` → `Ready (Next automatic refresh: +60 days)`
   - **Signed in on Desktop (Additive Banner / Step):** `Optional: Import Chrome/Edge history on this PC` → `Preview domain counts` (consent gate) → `Imported X days`
3. **Rule 9 Guardrail (all lanes):** Watch history enters `youtube:interests` strictly as **aggregated daily channel & coarse topic counts** (never individual video facts), with sensitive topics (`health`, `religion`, `politics`, `credential`, `third_party_private`) **always held back** before persistence.

---

## 4. Implementation Prerequisites for Orchestrator Check

1. **Google Drive Takeout-Archive Pull (`google_drive` connector):** `docs/connectors/README.md` currently restricts `google_drive` to **metadata only** (no file-byte download). Supporting the UAE/Global scheduled Takeout-to-Drive flow requires adding a **user-consented scoped read** specifically for `Google Takeout/*.zip` (extracting `watch-history.json` in memory and feeding `ingest/youtube.py`).
2. **Region Detection & Onboarding State Machine:** Surface country/eligibility selection (or IP/region hint with manual override) during onboarding to present **Data Portability API** vs **Takeout → Drive**, track per-source onboarding progress states, and detect desktop sessions to offer the **WP-G `browser.py` preview → consent** step.
3. **Cross-Source Convergence:** Ensure both EEA Data Portability JSON, Takeout `watch-history.json`, and desktop WP-G browser YouTube visits flow through the same Rule 9 daily aggregator (`youtube:interests`) and `content_hash` / `yt-day-YYYY-MM-DD` idempotency.

## 5. Gamified onboarding and cross-device analytics (merged from `docs/plan/gamified-onboarding-and-analytics.md`, 26 Nov)

Founder-approved end goal (23 Nov), executes after the initial `ios` and `desktop` builds. Full original: `git show 1ea0d3b:docs/plan/gamified-onboarding-and-analytics.md`.

- **Rule: never block app entry.** Sign-in on mobile pulls fast signals, opens the full 4-pillar app at once, and shows a "Context Completeness" meter ("Dubai-io knows you 36%") plus a "Here is what I know about you for now" reveal card. The reference Quest app's hard wall (refuses to open until archives are uploaded) is the anti-pattern. "Skip - explore app now" is always enabled.
- **Completeness is deterministic**, computed from connected source watermarks and verified fact/day-packet coverage across the 7 life themes, never a random number.
- **Weights:** (1) mobile instant login +36% (Gmail Primary 30d 14% + Calendar 10% + YouTube Data API v3 12%); (2) mobile deepening, optional, +27% (WhatsApp `.txt` export 15% + YouTube watch history via Data Portability or scheduled Takeout 12%); (3) desktop companion login and continuous pull +37% (Chrome/Edge history 18% + local AI/coding sessions 19%), reaching 73-100%.
- **Analytics surface** (mobile Memory/Connect, desktop Analytics & Sources drawer), evidence-backed from `/v1/owners/{owner}/vault/*`, `/v1/ops/memory` and source watermarks: completeness ring + next-best-action banner ("Log in on Dubai-io Desktop to add Chrome & AI session context (+37%)", one-tap pair / copy setup link); "What I know about you so far" cards with Confirm / Edit / Not true / Forget, each with `src:` and `as_of`; life-theme radar over the 7 spines with rising 21-day interests; cross-source signal mix (counts per source); Rule 9 shield counter ("N sensitive items held back") with Forget by source; compute attribution badge (your Claude/Codex at $0 app cost vs internal worker).
- **Build sequence:** (1) memory API `GET /v1/owners/{owner}/onboarding-status` (or extend `vault/summary`) returning `completeness_pct`, per-source counts, rising 21-day deltas, Rule 9 held-back counts and top facts; (2) mobile (`I-C`) banner, reveal cards, pairing card, analytics in Memory/Connect; (3) desktop (`D-C`) pairing, continuous/scheduled pull toggle, live completeness jump, analytics dashboard.
