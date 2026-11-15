# Unified App Foundation (Plan 1 of 8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `apps/site` marketing site with the Dubai-io app shell — Mirsal-derived look in white + `#357F92`, three presentations, Assistant home with composer and briefing strip, task threads from real tasks, and first-run onboarding.

**Architecture:** A client-only React app under `apps/site/unified/` mounted at `/` via `next/dynamic(..., { ssr: false })`; Mirsal-redesign (`~/VsCode/Mirsal-redesign/src`) is the source for tokens, primitives, shell, `MacDesktop` and the phone frame, copied and recolored. All data comes from `apps/api` through the existing `/api/:path*` rewrite (same origin). Later plans add surfaces into the same shell.

**Tech Stack:** Next.js 16.4 / React 19.3 / TypeScript, CSS modules, `lucide-react`, Vitest (unit), Playwright (e2e).

**Spec:** `docs/plan/unified-app-design.md`

## Global Constraints

- Palette: accent `#357F92`, background `#FFFFFF`, secondary `#F6F7F8`; light home haze = accent ~8% + warm sand/lavender ~5% fading to white; dark = Graphite `#141618` / `#1B1E21` / `#202428`, accent `#6FA9B8`; system setting + user toggle.
- No shadows; plain AI text, tinted user box, white rounded action boxes (root `CLAUDE.md`).
- Truth rules: no status word (`Confirmed`, `Booked`, `Paid`…) without provider evidence; demo content shows a `Demo` pill; never invent progress %, ratings, or position.
- Desktop rail exactly: Assistant, Chats, Services, Maps, Dashboard, Me. Phone (≤820 px) tabs: Home, Chat, Services, Feed + Ask.
- Presentations: plain URL = website; `?desktop` = Mirsal `MacDesktop` window; `?device` = iPhone frame + Dynamic Island. Same live API in all three.
- Mic hidden. No new deps beyond `lucide-react`, `vitest`, `@playwright/test` (approved 23 Oct).
- Keep wrap-friendly for Capacitor/Tauri later: no server-only features in `unified/`, API base from `NEXT_PUBLIC_API_BASE ?? ""`.
- Do not touch `apps/web`, `apps/api`, `apps/ios`, `supabase`.

## Review Focus

- API down or `luna/turn` 503 → composer shows "Assistant unavailable — try again", never a fake reply. (Task 5 e2e)
- `/api/today` empty for a new visitor → 3 demo tasks shown with `Demo` pills, dismissible, real tasks listed above them. (Task 4 unit)
- Reload with onboarding half done → resumes at the next unanswered question; never re-asks saved facts. (Task 7 e2e)
- Width crossing 820 px live → layout swaps without losing the open thread or composer draft. (Task 3 e2e)
- Reduced motion → orb, haze and panel slides are static. (Task 7 e2e)

---

### Task 1: Tooling and dependencies

**Files:**
- Modify: `apps/site/package.json` (add deps + scripts `test`, `e2e`)
- Create: `apps/site/vitest.config.ts`, `apps/site/playwright.config.ts`, `apps/site/tests/unit/smoke.test.ts`, `apps/site/tests/e2e/smoke.spec.ts`

**Interfaces:** Produces `npm run test` (Vitest, jsdom) and `npm run e2e` (Playwright; `webServer` runs `npm run build && npm run start -- -p 3030` with `DUBAIIO_API_ORIGIN` from env, default `http://127.0.0.1:8030`).

- [ ] **Step 1:** `npm i lucide-react@0.460.0 && npm i -D vitest jsdom @playwright/test` in `apps/site`; `npx playwright install chromium`.
- [ ] **Step 2:** Smoke tests: unit `expect(1+1).toBe(2)`; e2e `page.goto('/')` returns 200.
- [ ] **Step 3:** Run `npm run test` and `npm run e2e` → both PASS.
- [ ] **Step 4:** Commit `chore(site): vitest + playwright + lucide`.

### Task 2: Tokens and primitives (Mirsal, recolored)

**Files:**
- Create: `apps/site/unified/tokens.css` (from Mirsal `src/tokens.css`), `apps/site/unified/ui/index.tsx` (from Mirsal `src/ui/index.tsx`), `apps/site/tests/unit/tokens.test.ts`

**Interfaces:** Produces CSS variables `--accent`, `--bg`, `--surface-2`, `--text`, `--text-2`, `--border`, `--home-haze` (light and `[data-theme="dark"]`), and primitives `Avatar, IconButton, Button, Badge, ListRow, Card, Segmented, SearchField, DemoPill({label?: string})`.

- [ ] **Step 1:** Test reads `tokens.css` and asserts `--accent: #357F92`, `--bg: #FFFFFF`, `--surface-2: #F6F7F8`, dark `--bg: #141618`, dark `--accent: #6FA9B8`, and no `box-shadow` / `--shadow` with non-`none` value.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Copy + recolor (Mirsal blue → accent, tinted wallpapers/frost → neutral, shadows → `none`), add `DemoPill`. **Step 4:** Run → PASS. **Step 5:** Commit.

### Task 3: Shell and three presentations

**Files:**
- Create: `apps/site/unified/App.tsx` (`'use client'`), `unified/shell/{Rail.tsx,Shell.tsx,MacDesktop.tsx,shell.module.css}`, `unified/mobile/{MobileApp.tsx,TabBar.tsx,DeviceFrame.tsx,DynamicIsland.tsx,useIsMobile.ts,mobile.module.css}`, `unified/presentation.ts`, `apps/site/tests/e2e/shell.spec.ts`
- Modify: `apps/site/app/page.tsx` (mount `dynamic(() => import('../unified/App'), { ssr: false })`); move current landing to `apps/site/app/about/page.tsx`

**Interfaces:**
- Produces `presentation(search: string): 'website' | 'desktop' | 'device'`; `type ScreenId = 'assistant'|'chats'|'services'|'maps'|'dashboard'|'me'`; `<Shell screen sidebar main/>`; `useIsMobile(): boolean` (≤820 px, client-only snapshot).
- Non-home screens render a placeholder card "Coming in plan N" (no fake content).

- [ ] **Step 1:** e2e: at 1440×900 `/` shows a rail with exactly the 6 labels in order; at 390×844 shows tab bar Home/Chat/Services/Feed + Ask; `/?device` shows `[data-testid=device-frame]`; `/?desktop` shows `[data-testid=mac-window]`; resizing 1440→390 keeps a typed composer draft.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement by porting Mirsal `src/App.tsx`, `src/shell/*`, `src/mobile/{MobileApp,useIsMobile,DynamicIsland}` (drop Mirsal stores/screens not in this plan). **Step 4:** Run → PASS. **Step 5:** Commit.

### Task 4: API client, task threads model, demo tasks

**Files:**
- Create: `apps/site/unified/data/api.ts`, `unified/data/tasks.ts`, `apps/site/tests/unit/tasks.test.ts`

**Interfaces:**
- `apiGet<T>(path: string): Promise<T>`, `apiPost<T>(path, body)`, `apiPut<T>(path, body)` — same-origin, `credentials: 'include'`, call `GET /api/session` once first; throw `ApiError {status, message}`.
- `type Lane = 'needs_you'|'running'|'scheduled'|'on_list'|'paused'|'completed'`
- `type TaskThread = { id: string; title: string; status: string; lane: Lane; preview: string; at: string; unread: boolean; demo: boolean }`
- `toThreads(today: TodayResponse, dismissedDemo: string[]): TaskThread[]` — title from `task.outcome`; real tasks ordered needs_you → running → scheduled → on_list → paused; then `DEMO_TASKS` (ids `demo-ac`, `demo-laundry`, `demo-dewa`; titles "AC repair", "Laundry pickup", "DEWA bill"; previews "needs your approval", "waiting for provider", "due Thursday"; `demo: true`) minus dismissed.
- `briefing(threads: TaskThread[]): { needsYou?: TaskThread; changed?: TaskThread; due?: TaskThread }`.

- [ ] **Step 1:** Tests: empty `/api/today` → 3 demo threads all `demo:true`; one real needs_you task → it is first and demo follow; `dismissedDemo=['demo-ac']` → 2 demo; `briefing` picks first needs_you / most recent / first scheduled.
- [ ] **Step 2–5:** FAIL → implement → PASS → commit.

### Task 5: Assistant home (direction C) + switch + composer

**Files:**
- Create: `apps/site/unified/assistant/{Home.tsx,Composer.tsx,BriefingStrip.tsx,ModeSwitch.tsx,assistant.module.css}`, `apps/site/tests/e2e/assistant.spec.ts`

**Interfaces:**
- Consumes `apiPost('/api/luna/turn', { text, thread_id })` → reply = last `history` item with `role === 'luna'`; `briefing()` from Task 4.
- `ModeSwitch` values `'assistant' | 'community'`; Community shows the placeholder card until Plan 3.

- [ ] **Step 1:** e2e (Playwright `page.route` mocks): greeting "Good evening/morning/afternoon" by local hour; submitting "hello" shows the mocked Luna reply; mocked 503 shows "Assistant unavailable — try again" and keeps the draft; briefing strip renders 3 cards from mocked `/api/today`; `[data-testid=home-haze]` is present in light theme, absent in dark, and has `animation-name: none`.
- [ ] **Step 2–5:** FAIL → implement → PASS → commit.

### Task 6: Task threads sidebar, thread view, Updates island

**Files:**
- Create: `apps/site/unified/tasks/{ThreadList.tsx,ThreadView.tsx,UpdatesIsland.tsx,tasks.module.css}`, `apps/site/tests/e2e/threads.spec.ts`

**Interfaces:**
- Consumes `toThreads`; thread view loads `GET /api/tasks/{id}` and `GET /api/tasks/{id}/activity`, renders each activity entry as an assistant message (no invented stages); demo threads open a read-only thread labelled `Demo` with a dismiss button.
- `UpdatesIsland` shows the first needs_you or running thread title + lane label; phone uses it inside `DynamicIsland`.
- Poll `/api/today` every 20 s while the tab is visible.

- [ ] **Step 1:** e2e: sidebar shows real then demo threads with `Demo` pills; clicking a real thread renders its mocked activity entries in order; dismissing `demo-ac` removes it and survives reload (localStorage `dubaiio.dismissedDemo`); hidden tab stops polling (assert no request for 25 s after `visibilitychange` hidden).
- [ ] **Step 2–5:** FAIL → implement → PASS → commit.

### Task 7: Onboarding (orb → setup is the chat)

**Files:**
- Create: `apps/site/unified/onboarding/{Onboarding.tsx,Orb.tsx,onboarding.module.css}`, `apps/site/tests/e2e/onboarding.spec.ts`

**Interfaces:**
- Shows once (localStorage `dubaiio.onboarded`); questions in order area → household → services → connectors; answers saved via `apiPut('/api/session/memory/{area|household|services}', { value })` (≤80 chars); connectors step lists Gmail/Calendar as "Not available yet" + "Later".
- Before asking, `GET /api/session/memory` → skip questions whose key already exists.

- [ ] **Step 1:** e2e: first visit shows orb + "Where in Dubai do you live?"; tapping "Dubai Marina" PUTs `area` and advances; reload mid-flow resumes at household; Skip lands on the composer and sets the flag; reduced motion → orb has no running animation.
- [ ] **Step 2–5:** FAIL → implement → PASS → commit.

### Task 8: Visual gate

- [ ] **Step 1:** With the API on 8030, capture `/`, `/?desktop`, `/?device` at 1440×900 and 390×844, light and dark, onboarding and home, into `output/unified-shots/plan1/`.
- [ ] **Step 2:** Main session reviews against `.superpowers/brainstorm/94241-1792742190/content/img/v3/{l01-home,l09-desktop-app,m01-chats,m05-onboard,d01-home-graphite}.jpg`; fix mismatches; commit.

---

## Roadmap (separate plans, each written when the previous lands)

2. **Backend: composer → real tasks** (Luna turn creates/links tasks; activity entries per step).
3. **Community + Chats ⇄ Calls** ported from `apps/web` (feed, post panel, AI replies polling; WhatsApp-style chats/calls/favorites/archive).
4. **Services + Maps + airport guide + lost-in-taxi** as flows/threads.
5. **Dashboard workspaces** (Weather, Prayer, News) + Connectors gallery + "What Dubai-io can see".
6. **Memory engine** (temporal_note port into Supabase) + Me timeline + "I noticed".
7. **Connectors + investigation loop** (Gmail, Outlook, GitHub/notes; `FAST_MODEL` fan-out; drafts in the originating app) — the Puffy run.
8. **Packaging + parity:** Capacitor iOS/Android, Tauri/Electron desktop; retire `apps/web` after parity sign-off.
