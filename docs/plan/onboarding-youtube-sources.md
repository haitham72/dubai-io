# Onboarding Progress & Multi-Path YouTube Watch-History Ingestion

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
