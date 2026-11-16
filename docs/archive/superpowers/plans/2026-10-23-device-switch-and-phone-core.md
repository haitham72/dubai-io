# Device Switch + Phone Core (Plan 2 of 8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee the existing mobile demo is never lost — an Original ⇄ New toggle inside the iPhone frame — and bring the phone's core moments into the new app: a richer phone Home (best of `design/references/01-home.png`), the DXB airport guide, and lost-item-in-taxi recovery.

**Architecture:** Frontend-only in `apps/site/unified/`. "Original" = the untouched `apps/web` PWA, served by the API at its origin, embedded in the device frame via iframe. New screens port behaviour from `apps/web` (`arrival.js`, `guide.js`, taxi/recovery UI) to React, using existing API endpoints only.

**Tech Stack:** as Plan 1 (Next 16 / React 19, CSS modules, lucide-react, Vitest, Playwright).

**Spec:** `docs/plan/unified-app-design.md` (§1 cases that must survive; §0.1 final delivery).

## Global Constraints

- **Founder priorities (23 Oct, final word for this stage):** no rush to ship — polished, refined, high quality, working, and **easy to change all the time**: a design change must be **one edit that echoes everywhere** (website, desktop, iOS/Android). So: **one React codebase** (`apps/site`), one central design system (tokens + shared components; no per-screen styling forks), and every screen ported from the **original mobile app** looking **as close as possible to it**. **Light mode first**; dark (Graphite) comes after light is polished. Option 'wrap the original as the phone app' was considered and declined.
- Port, don't reinvent: each new phone screen reproduces the original `apps/web` screen (layout, structure, copy) using shared components/tokens; deviations only where the founder asked (Services uplift).

- All Plan 1 global constraints apply (palette, no shadows, truth rules, rail/tabs, presentations, wrap-friendly).
- **Never modify `apps/web/**`, `apps/api/**`, `apps/ios/**`, `supabase/**`.** Check before every commit: `git diff --name-only HEAD | grep -E '^apps/(web|api|ios)/|^supabase/'` must be empty.
- Airport guide: never claim an indoor position, belt, gate or queue time the user didn't confirm; map pins = user-confirmed places only; times labelled estimates (root rule 3).
- Taxi recovery: RTA adapter is BLOCKED — no fake send; show blocker + official portal + copy; staged replies labelled demo; outcome "Not recovered yet" until evidence.
- 01-home's "visitor" identity is superseded (everyday life): reuse its *components*, not "Hello, visitor" copy; airport card appears only when the user said they're at the airport / has a travel task, or as a labelled `Demo trigger`.

## Review Focus

- Original iframe can't load (API down) → the frame shows "Original app unavailable — start the API" with the URL, never a blank phone. (Task 1)
- Toggle choice survives reload and presentation switches (`?device` ⇄ website). (Task 1)
- Guide "I'm lost" with no confirmed landmark → asks for the nearest sign, does not guess. (Task 3)
- Taxi report with missing saved details → fields shown as "Not told yet — add", never invented. (Task 4)
- Phone Home with zero tasks/facts → teaching empty states, no fake "At DXB" chip. (Task 2)

---

### Task 1: Original ⇄ New toggle in the device frame

**Files:** Create `apps/site/unified/mobile/OriginalFrame.tsx`, `apps/site/unified/mobile/DeviceToggle.tsx`; Modify `apps/site/unified/mobile/DeviceFrame.tsx`; Test `apps/site/tests/e2e/device-toggle.spec.ts`, `apps/site/tests/unit/original-url.test.ts`
**Interfaces:** `originalUrl(loc: {protocol: string; hostname: string}, env?: string): string` → `env` (`NEXT_PUBLIC_ORIGINAL_URL`) if set, else `${protocol}//${hostname}:8030/index.html#home`; toggle values `'original' | 'new'`, stored in localStorage `dubaiio.deviceMode` (default `'new'`). **Route: `/?devices`** (founder, 23 Oct) = iPhone frame with the Original ⇄ New toggle; `?device` stays as an alias; `presentation()` returns `'device'` for both.
- [ ] Tests: unit for `originalUrl` (env wins; default port 8030); e2e: toggle visible above the frame at `/?devices` (and `?device`), absent on plain website; switching to Original renders `iframe[data-testid=original-frame]` with the expected src; choice persists across reload; mocked load failure shows the unavailable message.
- [ ] FAIL → implement → PASS → commit.

### Task 2: Phone Home (best of 01-home)

**Files:** Create `apps/site/unified/mobile/PhoneHome.tsx`, `phoneHome.module.css`; Modify `MobileApp.tsx` (Home tab → PhoneHome); Test `apps/site/tests/e2e/phone-home.spec.ts`
**Interfaces:** consumes `apiGet('/api/session/memory')` (told facts), `toThreads`/`briefing` (Plan 1). Layout: soft Dubai hero band behind "Ask Dubai-io anything…" search (opens Ask), quick chips **Find a group · Buy something · I lost something** (route: Community, Services, taxi-recovery start), "you told me" chips from facts (e.g. "Dubai Marina · you told me"), briefing card (Needs you / Changed / Due), orb + one question chip row when onboarding facts are missing.
- [ ] Tests: with mocked facts `{area: Dubai Marina}` shows "Dubai Marina · you told me"; with none shows no fact chips and shows the orb question; "I lost something" opens the taxi recovery start (Task 4); hero has no photo-of-people.
- [ ] FAIL → implement → PASS → commit.

### Task 3: DXB arrival guide

**Files:** Create `apps/site/unified/guide/{ArrivalGuide.tsx,steps.ts,guide.module.css}`; Test `apps/site/tests/unit/guide-steps.test.ts`, `apps/site/tests/e2e/guide.spec.ts`
**Interfaces:** port step data + rules from `apps/web/guide.js` / `arrival.js` (read them; terminals, steps, late-night notes, "I'm lost" landmark flow). `nextStep(state: GuideState, confirmed: string[]): Step`; `lostPrompt(state): string`. Reachable from Ask chip "Guide me through arrivals", the phone Home airport card, and as a task thread.
- [ ] Tests: unit — only confirmed steps are ticked; "I'm lost" with no confirmed landmark returns the "nearest sign" question; late-night note present when hour ≥ 23 or < 5 (Metro closes ~midnight, T2 no station). e2e — confirming Passport ticks it and advances; map card lists only confirmed places.
- [ ] FAIL → implement → PASS → commit.

### Task 4: Lost item in a taxi

**Files:** Create `apps/site/unified/recovery/{TaxiRecovery.tsx,report.ts,recovery.module.css}`; Test `apps/site/tests/unit/report.test.ts`, `apps/site/tests/e2e/taxi.spec.ts`
**Interfaces:** port from `apps/web` recovery/taxi UI (find it via `grep -rn "taxi\|recovery\|lost" apps/web/*.js`) and the existing API (`POST /api/tasks/from-report`, task `commands` for staged replies — read `apps/api/app/tasks.py` TAXI-02, do not modify it). `buildReport(facts, answers): ReportField[]` where missing values are `{value: null, label: 'Not told yet'}`. Thread shows staged progress, the report card ("from your saved details"), blocker "RTA submission not connected — open official portal", buttons **Open RTA portal** (official URL already used in `apps/web`) / **Copy report**, status chip "Not recovered yet".
- [ ] Tests: unit — missing roof colour → "Not told yet"; e2e — starting from "I lost something" creates a task via mocked `from-report`, thread renders the report card and blocker; no button says Submit/Sent.
- [ ] FAIL → implement → PASS → commit.

### Task 5: Visual gate

- [ ] Capture `/?devices` (New and Original), phone 390 Home / guide / taxi, light + dark into `output/unified-shots/plan2/`; compare with `v3/m03-airport.jpg`, `v3/m04-taxi.jpg`, `v3/m01-chats.jpg` and `design/references/01-home.png`; fix; commit.

---

## Finalize roadmap (updated 23 Oct)

| Plan | Scope | Owner |
|---|---|---|
| 1 ✅ | Shell, presentations, Assistant home, threads, onboarding | done (`eb6568f`) |
| **2** | **Original ⇄ New device toggle; phone Home; airport guide; lost-in-taxi** | Sonnet subagent |
| 2b | Backend: composer → real tasks + activity per step | Claude (main) |
| 3 | Community + Chats ⇄ Calls (port from `apps/web`) | Sonnet subagent |
| 4 | Services + Maps (Google Places key is set). **Services gets a quality uplift to the Feed screen's level** (founder: Services is the weakest original screen, Feed the best) | Sonnet subagent |
| 5 | Dashboard (Weather, Prayer, News — keys set) + Connectors gallery + "What Dubai-io can see" | Sonnet subagent |
| 6 | Memory engine (`2026-10-23-temporal-memory.md`) | Sonnet + Claude review |
| 7 | Connectors (Gmail/Outlook/GitHub; Google OAuth when founder adds keys) + investigation loop | Claude + Sonnet |
| 8 | Packaging (Capacitor iOS/Android, Tauri/Electron desktop) + parity check → retire the original only on founder approval | Sonnet + Claude |
