# Dubai-io — Plan

**Updated:** 19 Oct 2026 (monorepo cleanup + docs review) · **Status:** **Plan v1.7** · handoff: `docs/handoff.md` (Home v2 + temporal profiler + services loop in §7) · **Owner:** Haitham
This is the single plan. Scope, demo and phases live here, and nowhere else. (Decision log lives on `main` and `docs/`; current working branch is `redesign`.)
**Founder lock (10 Oct, final): bidding/quote is ABSOLUTELY REJECTED. Every service opens as a modal HTML mini-app (services / shops / stores / rides) with published fixed prices.**
**Founder decision (12 Oct): the Resident/VIP arc (items 10–11) moves from LATER to IN, built after the visitor redesign. Providers answer slot/availability requests at published fixed prices. The quote lock above is unchanged.**
**Founder decisions (13 Oct):**
- The **temporal profiler is core** (visible hypotheses, `ARCHITECTURE.md §12`).
- **Home v2** (shader coverflow, soft reveal) and the universal **Services surface** come first.
- Service cases live in `docs/services/cases.md`, are picked one at a time (§7), and are ~1% of the app; the generic engine covers the rest.
- The quote lock is unchanged.
- **Palette: cyan selected.** C1’s laser/chromatic reflection is the approved style for every stage card, at 70% of its previous intensity. This does not select the chromatic page/theme.

**Current implementation:** Phase 0 is complete. The active frontend is `apps/web/` (with Wi-Fi captive arrival and coverflow onboarding); `apps/api/` serves `apps/web` directly at `/` and implements Luna, SQLite persistence, JSON stated-fact memory and Google Places/Routes proxies. The obsolete legacy prototype in `demo/` has been retired.

---

## 1. What we're building

> **Dubai-io remembers your situation and follows through with local merchants, with you approving what gets shared.**

The companion is the product. Mini-apps are how it works with merchants. Photo onboarding is how more merchants join. Airport arrival is the introduction, not the product.

**Story:** short-stay business visitor → late-night DXB arrival → independent laundry with a deadline → taxi-memory payoff. Evidence: strongest for lost items in taxis (104k+ RTA 2025), medium for laundry deadline (Nov 2025 two-day concierge failure). Concierge verdict: serious but inconsistent competitor. Still open: preference for Dubai-io vs hotel.

Contest: Create AI Agents Championship, category **Best Personal AI Agent**. Official materials contradict: registration Dec 2026 (FAQ/launch) vs Jan 2027 (timeline); global eligibility vs Dubai-licence requirement for non-residents; no published rubric. Portal-only verification carried into Phase 1 — do NOT hard-code dates.

## 2. Scope

### IN for the contest build

| # | Capability | Pillar |
|---|---|---|
| 1 | Persistent chat (history and cards survive reload, streaming) | Companion |
| 2 | Proactive messages from deterministic triggers (flight landed, merchant replied, reminders), deduplicated | Companion |
| 3 | Memory the user gives (hotel area; taxi plate or receipt photo, roof colour, route, start time), recalled later without asking again | Companion |
| 4 | **DXB arrival guide:** step-by-step, user-confirmed, landmark "I'm lost", map with a terminal pin | Visitor |
| 5 | Ride recommendation that **reasons from time and terminal** (e.g. after midnight or at T2 → no Metro → taxi), with the alternative shown (estimates, handoff only) | Visitor |
| 6 | **Talabat-normal discovery → modal HTML mini-apps** (sandboxed, scoped bridge). List sorted closest + ★ rating + price-from + turnaround. Tap any row → its **own modal HTML mini-app** (services / shops / stores / rides). Fixed published prices only — **no bidding, no quote, no negotiation** | Services |
| 7 | Merchant loop with **deadline awareness** (fixed order, NO quote): approval → merchant accepts at published price → companion checks ready-time against user's deadline, flags conflict, asks for earlier slot → merchant confirms ready-time | Services |
| 8 | Memory payoff: "I left my bag in the taxi" → report pre-filled with RTA's fields (time, pickup/drop-off, roof colour, plate, receipt photo) from saved trip details, asks only for what's missing, hands off to the official channels (call centre / chat agent / app), stays "not recovered" | Companion |
| 9 | Merchant onboarding: price-list photo → AI-generated mini-app → operator approves → live | Platform |
| 10 | **Resident/VIP arc** (second arc, after the visitor redesign): a goal ("renew my car licence") becomes a plan. Agents read provider sites / APIs / MCP tools, prepare each step and send **slot requests at published fixed prices**: papers check (user-supplied facts only) → provider rows → runner proposal → insurance choice → provider-confirmed done, with a per-step calendar timeline to the second. A private runner makes the visit; Dubai-io never submits to RTA/Tasjeel | Resident |
| 11 | **Service cases:** picked from `docs/services/cases.md` by C-ID (maid with visa, cloth try-on, barber, pets, food, video → map, …). Fixed prices, fictional demo providers | Services |
| 12 | **Temporal profile:** visible hypotheses that learn over time, "You, over time" card, "Because…" on every re-rank (`ARCHITECTURE.md §12`) | Companion |
| 13 | **Services surface:** data-driven category registry, map ↔ list, one bottom sheet for any provider (§7.3) | Services |

**If time runs out, cut in this order:** 11 → 10 → 9 → 5 → 4. Items 1, 2, 3, 6, 7, 8, **12 and 13** are the floor: memory + follow-through *is* the product.

### LATER (vision, not in the contest build)

Civic RAG with citations · resident bills and Salik/DEWA displays · community · background geofencing · ticket wallet · payments · media memory · Arabic RTL UI (Arabic answers are fine) · native app (Swift; ShipSwift originals, Liquid Glass, haptics, share extension) · live AR try-on · marketplace feeds via affiliate APIs.

**Scope conflicts to resolve before porting affected flows:** §6 and `redesign.md` contain historical community and ticket fixtures, although community and ticket wallet remain LATER here. Their presence in v1 does not approve production features or make them parity gates. Likewise, reference scopes `auth.signin`, `community.join_request`, `purchase.report` and `policy.select` are not approved additions to the order-only business bridge. Resolve these in this scope section before implementing them.

### NEVER

Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · government transactions (a private runner may visit the centre; Dubai-io never submits, pays, or marks anything renewed without a provider event; fines are display-only) · copying the official DubaiNow look · **bidding / quote / price negotiation in any form (`quote.request`, `QUOTED`, `QUOTE_ACCEPTED`)**.

## 3. Demo arc (v2, final)

One visitor, one continuous story: **an independent laundry with a deadline** (shirt pressed by 09:00 for tomorrow's meeting). Family sharing and belt recall are off the main path.

| Time | On screen | Presenter says |
|---|---|---|
| 0:00–0:12 | Arrival greeting, "Scripted demo" label, one button: *Guide me to arrivals* | "Dubai-io is a personal companion that remembers your situation and follows through with local merchants." |
| 0:12–0:35 | Compact airport guide. "I'm lost" → a landmark choice changes where the guide resumes | "It guides me from where I confirm I am, and resumes from what I can see." |
| 0:35–0:55 | It's 00:40, so the Metro has stopped: it recommends a taxi *with that reason* (official cream RTA taxi, not solicitors; Hala has no airport pickup). Plate (or receipt photo — explicitly prompted "snap this receipt"), roof colour, route and start time saved, labelled "You told me" | "It knows the Metro has stopped, so it suggests a taxi, and saves what I'll need if something goes wrong." |
| 0:55–1:10 | "I've reached my hotel." User: *"I need a shirt pressed by 9 tomorrow."* | "My hotel area carries into the request." |
| 1:10–1:30 | Three laundries as Talabat-normal list (closest + ★ + price-from + turnaround), each row opens its **own modal HTML mini-app** | "Separate merchant experiences, same conversation." |
| 1:30–1:55 | Cyan host approval: named shop, fixed items + fixed total, hotel area, deadline. Pauses visibly | "The shop's mini-app can only ask. Dubai-io shows what's shared and waits for me." |
| 1:55–2:45 | Merchant inbox expands. **Accepted at fixed price** → ready-time **10:00** → companion flags "misses your 09:00 deadline" → asks for earlier → **08:30** → merchant confirms (no re-quote, price unchanged) | "Ten o'clock misses my deadline. It catches that, asks for earlier, and says confirmed only when the shop confirms." |
| 2:45–3:05 | Price-list photo → generated mini-app → owner review → appears in results | "Another shop joins from a photo, reviewed before it goes live." |
| 3:05–3:40 | **"I left my bag in the taxi!"** Report pre-filled with the fields RTA asks for (time, pickup/drop-off, roof colour, plate, receipt), asks only for the bag description, official handoff (SMS workflow), "not recovered" — never a recovery probability | "Over a hundred thousand items were left in Dubai taxis last year. It already has the details the report needs." |
| 3:40–4:00 | Report beside the earlier taxi-memory card | Close: *"Dubai-io remembers your situation and follows through locally, with you approving what gets shared."* |

**Under the hood** goes compact: large events only ("Trip details saved", "Sharing approved", "Merchant accepted", "Ready confirmed"), with the raw log available for questions. The merchant inbox is labelled "Merchant role, simulated" until a real merchant exists.

### Jury objections (prepared answers)

| Objection | Answer |
|---|---|
| Google Maps already has Ask Maps (Gemini, Mar 2026) | Ask Maps answers place questions with a personalised map, and coverage reports no booking or acting for you. It launched in the US + India; nothing found for the UAE. Dubai-io follows through: a fixed-price order to the merchant, your approval of what is shared, merchant-confirmed status, and a profile you can see and forget |
| What does this add to DubaiNow / Careem / talabat / ChatGPT? | Continuity: the same companion carries your context into a local merchant's fixed order and ready-time confirmation, and you approve what leaves the chat. We don't claim they lack AI or memory |
| Where's the agency beyond buttons? | It holds the deadline, checks a fixed ready-time against it and proposes the next step (no price negotiation) |
| Why keep it after the airport? | Arrival is the introduction; repeat local requests reuse your preferences and history |
| Why would merchants join? | A reviewed mini-app from a photo, plus a structured inbox, is less work than WhatsApp back-and-forth. To be validated with shop owners |
| What have you proved? | The interaction is reviewable. User need, repeat use and merchant participation are what we test next |

## 4. Phases

Gates are binary. Dates are relative until the contest deadline is verified; then re-anchor.

### Phase 0 — Sketch ✅ *complete*

- [x] Clickable HTML demo (`demo/`), iOS light style, DXB placeholder maps
- [x] Docs consolidated (this structure)
- [x] Two external LLM review rounds merged (on `main`)
- [x] Hero: short-stay business visitor → independent laundry deadline → taxi-memory payoff
- [x] Desk research on reported visitor problems (on `main`)
- [x] Demo arc v2 locked (§3)

**Carried into Phase 1 (non-blocking):**
- [x] ✅ Forum/first-hand research DONE (on `main`). Do NOT re-run.
- [ ] Verify contest rules on the official portal ONLY (`dubaichamberdigital.com`, Dubai Media Office / WAM): deadline (Dec 2026 vs Jan 2027 conflict), artifacts (prototype + deck + video + summary report?), judging criteria (no rubric published), IP (non-exclusive licence claim), eligibility (global vs licence), physical attendance + security. Then re-anchor phase dates
- [ ] Complete lab parity with arc v2: deadline-conflict branch, time-aware ride reasoning, full recovery sheets and RTA fields, cyan host strip, compact backstage and "Scripted demo" label. V1 implementations and lab stubs are not completion of this gate.
- [ ] Replace placeholder maps with arrival-side maps
- [ ] Optional validation: visitor interviews and laundry tabletop (script on `main`)

### Phase 1 — Skeleton (~2 weeks)

Monorepo scaffold (`apps/web`, `apps/api`, `apps/widgets`, `packages/contracts`), Postgres, contracts + codegen, auth with demo users, chat persistence + SSE, card renderer, one LLM turn with a read-only tool.
**Gate 1:** chat → typed card from a tool · reload restores everything · invalid card falls back to text.

### Phase 2 — Arrival companion (~2 weeks)

Arrival guide as cards, landmark matching, memory store, ride comparison, trigger/outbox pipeline with dedupe, demo-trigger endpoint.
**Gate 2:** a trigger fired twice → one message · the journey survives reload mid-way · saved memory is recalled by free text.

### Phase 3 — Mini-apps + merchant loop (~3 weeks)

Registry and manifests, widget origin + sandbox + bridge (`order.request` only — `quote.*` forbidden), approval cards (single approval), fixed-order state machine with idempotency, merchant inbox with live updates.
**Gate 3:** merchant action → user chat in < 1 s · out-of-scope bridge call blocked (test) · double-tap approve = one order (idempotency) · accept/decline/cancel paths work. No quote path exists to test.

### Phase 4 — Payoff + platform (~2 weeks)

Lost-item recovery using memory (checklist + official handoff, nothing "filed"). Photo → extracted catalog → generated mini-app → operator approval.
**Gate 4:** a new merchant goes live without code changes · the recovery flow uses only saved, user-given facts.

### Resident/VIP arc (starts after the visitor redesign ships)

- [ ] Resident/VIP design prompts generated and imported (`redesign.md`, R-series)
- [ ] Goal-to-plan card: agents at work, per-step status with timestamps to the second
- [ ] Car-licence renewal: papers check → fixed-price rows + slot replies → runner proposal → insurance → provider-confirmed done + calendar timeline
- [ ] Home services rows (fix it / maid / renovation) from marketplace apps and found shops
**Gate R:** every step shows a provider-sourced status · no quote path · nothing marked renewed or paid without a provider event · fines display-only.

### Phase 5 — Polish + submit (to deadline)

Rehearse 10×, record a fallback video, deck, deploy, small user test, honest metrics ("27/30").
**Gate 5:** 10 clean runs ≤ 4:00 · fallback video recorded.

## 5. Not code, but critical

| Track | Needed by | Fallback |
|---|---|---|
| Contest rules, deadline, IP | Phase 0 | — |
| 1 real merchant willing to answer on stage/video | Phase 3 | Clearly labelled sandbox merchant |
| Real arrival-side airport maps or a redrawn schematic | Phase 2 | Generic step schematic (already in demo) |
| Hosting + domain | Phase 5 | Local + tunnel |

## 6. Redesign build plan (`apps/web`, Vite + React + TS)

**Handoff for the build agent.** Read order: `CLAUDE.md` → this section → `docs/references/redesign.md` (prompts and exact copy) → the images in `design/references/`. Branch `redesign`. This section replaces the Next.js front-end assumptions in Phases 1–3; the backend phases are unchanged. Build the **visitor redesign to parity first**, then the Resident/VIP arc (items 10–11).

### 6.1 Definition of done

- Runs in **iPhone Safari at 390 × 844**, and Add to Home Screen works. No native iOS build. The only server is the small Luna API (6.9); the app still works without it (mock fallback).
- Same story as §3 (arrival → laundry deadline → taxi memory), the waypoint guide and the lost-item cash/card paths, all in the redesigned look. Historical community/ticket flows require the scope resolution in §2 before becoming required parity work.
- Every rule in `CLAUDE.md` still holds (truth in status, fixed prices, sandbox, approvals, no government execution, no quotes).
- Gates in 6.6 pass, with screenshots next to the reference images.

### 6.2 Structure

**Target structure, not the current tree.** Current active code lives in `apps/web/` and `apps/api/`. Historical community/ticket/faith entries below are reference candidates, subject to §2 scope. Provider widget bundles use `apps/widgets` on a separate origin (§6 of `ARCHITECTURE.md`); host-owned assets stay in `public/`.

```
apps/web/
  index.html            viewport-fit=cover, theme-color, apple-mobile-web-app-*, apple-touch-icon (orb)
  miniapps/             bloom, foldpress, marinaexpress, nightowl, palmleaf, palmquick, provider
  fixtures/             dubai-map.json, profile-vectors.json
  media/                app photography and icons
  arrival.js            Wi-Fi settings, captive portal, install mock
  app.js / chat.js      stage coverflow, companion chat
apps/api/               FastAPI + LangGraph Luna + stated memory + Places/Routes proxies (6.9)
```

Dependencies (web): `react`, `react-dom`, `vite`, `typescript`, `vitest`, `@playwright/test`, a spring/gesture lib (`framer-motion` or `@use-gesture/react` + `react-spring`), a tiny WebGL helper (`ogl`, or raw WebGL2), founder-supplied effect libraries `border-beam`, `voice-glow`, `thinking-orbs`, plus `metal-fx` (silver only), `img-fx` (+`three`, lazy-loaded) and `liquid-gooey` (all npm-verified, MIT; pin exact versions, see `docs/references/visuals-libraries.md`), `zustand` optional. Plain CSS (CSS modules). No UI kit.

### 6.3 Reference map

| Screen / state | Reference | Build as |
|---|---|---|
| Home / Services | `01-home.png`, left half of `01a-chat-takeover.png` in `design/references/` | Home uses the cyan coverflow (§7.2); `01-home.png` hero/card layout becomes the top of Services (§7.5). One bottom composer |
| Chat active | right half of `01a-chat-takeover.png`, `02-rows.png` | compact header + back chevron, Composer replaces the tab bar, LunaChip, RowsCard |
| Guide (built-in mini-app) | `01c-guide-states.png`; spec only: prompt 1b in `redesign.md` (no image for stop 1) | `dxb-guide.html`, restyled; stop media from `public/maps` |
| Partner sheet (historical community fixture) | `02a-partner-sheet.png` | visual sheet anatomy only until §2 scope/bridge decision |
| Shop sheet | no image; derive from `02a` + prompt 2b | fixed-order mini-app; historical `purchase.report` scope needs §2 decision |
| Approval + events | `03-approve-events.png` | ApprovalCard, StatusTrack, UpdateBubble, CalendarCard |
| Banner | `03a-banner.png` (Home behind it must show the glass bar) | Banner |
| Lost item | `04-lost-item.png`, `04a-driver-rta.png` | RecoveryFlow, DriverSheet, ReportSheet |
| Services / Me | `05-services-me.png` (apply current bottom-composer navigation in 6.4) | ServicesScreen, MeScreen |
| Merchant + onboarding | `05a-merchant-onboarding.png` | merchant mini-app, shop review sheet |
| Backstage (≥ 1100 px) | `06-backstage.png` | inbox, trigger panel, tools status, event log |
| Arrival notification | `x-arrival-notification.png` | in-app Banner on first load (web cannot do Live Activities) |
| First-run tour | `x-home-onboarding.png` | coach-mark hierarchy adapted to the current bottom composer |
| Chat effects: Beam, Voice, Orb + ShipSwift `SWMetal` shader ideas | `docs/references/visuals-libraries.md` (prompts copied as supplied; our notes in Part 3) | Composer `BorderBeam` / `VoiceBeam`, bot avatar `ThinkingOrb`, GLSL ideas for L3 |
| Dark theme + map pin + permission card | `x-location-geofence-darkmode.jpg` (Apple Find My / Maps screenshot, **style reference only**, third-party names must not appear) | dark token set (`prefers-color-scheme` + manual), guide lightbox pin with an "approximate" ring, Me → Permissions "Notifications are off" card, detail-sheet pattern (title, status, two actions) |
| Resident/VIP | R-series prompts, no images yet | after visitor parity |
| Home v2 stage | `design/references/carousel/carousel*.jpg` (aura above, glow below), `carousel/holographi ccards.mp4` (holo finishes), ShipSwift `SWMetal` (MIT) | §7.2 |
| Services surface + cases | `docs/services/` tree (pets = surface pattern; cloth, coffee, restaurants, "Pulled data services") | §7.3, `cases.md` |

Ignore `design/references/_rejected/`. Fix on the way: `06` shows the real brand "Carrefour Express" (use "Marina Fresh (demo)"); `00`'s button reads "Indoor nav" (use "Arrival guide"; no indoor-position claims).

### 6.4 Navigation model (decided)

1. **Idle (13 Oct):** brand row on top, the **composer docked at the bottom** above a floating Liquid Glass tab bar **io · Maps · Services · Me** (Civic removed from the nav; civic stays LATER). Asking lifts the Home cards into chat; place results can then open Maps (§7.3).
2. **Chat active** (typed, or a suggestion tapped): compact header (back chevron, "Dubai-io", search icon); the glass **Composer replaces** the tab bar. Never show the tab bar during active chat. Idle deliberately has the composer above the tab bar.
3. **Back chevron:** returns to idle.
4. Sheets cover the bar; banners slide over the top.
5. Tab labels are **io · Maps · Services · Me**, with the orb on io. Older Companion/Civic labels in image prompts are superseded.
6. Home uses the coverflow stage (§7.2). The older hero/card layout from `01-home.png` belongs at the top of Services (§7.5).

### 6.5 Port the logic, don't redesign it

Current shell/flows live in `demo/lab/`. Use `demo/app.js`, `demo/data.js`, `demo/luna.js` as legacy behaviour references for missing approved flows, especially laundry and recovery. Port as typed modules only after lab review:

| Behaviour | Demo source | Notes |
|---|---|---|
| Journey: setStep, confirmWaypoint, I'm lost | `app.js` journey section | state is host-owned, pushed down to the iframe |
| Luna API integration (local wiring implemented) | `lab/chat.js` router + `apps/api/app/luna/schema.py` | map the actual contract in 6.9; keep confidence ≥ 0.6; distinguish `langgraph` from `lab router` |
| Historical community + shopping rows | `providerRows`, `joinApproval`, `purchaseReported`, `signIn` | subject to §2 scope and bridge decisions; not automatic parity requirements |
| Approval + fixed-order machine | `approval`, `createRequest`, `transition`, `FLOW`/`ALLOWED` | single approval, idempotent |
| Laundry deadline loop | `laundryDeadline`, `laundryMerchantFlow` | no re-quote |
| Recovery (card + cash, RTA report) | `recovery`, `traceByCard`, `traceByCash`, `rtaReport` | epoch guard; cash outcome alternates |
| Triggers + dedupe 2500 ms | `TRIGGERS`, `fireTrigger` | same-window messages only |
| Other legacy fixtures: faith, parking, photo search, departure, day plan, tickets, onboarding sim | matching sections | port only approved scope; fixture presence does not promote LATER features |

Bridge: scopes in each manifest AND a handler in the host table; unknown or out-of-scope kinds log `BLOCKED` and reply `host.error`. Sandbox stays `allow-scripts` only; no `allow-same-origin`.

### 6.6 Build order and gates

| Step | Build | Gate (Playwright iPhone profile, 390 px) |
|---|---|---|
| 0 | **Home v2 lab → picked shell** (§7.2) ported in: scaffold, tokens, coverflow stage + shaders, soft reveal, "You, over time", Services surface | founder picked the shell on the iPhone; aura + glow visible; fallbacks work |
| P | **`apps/api` scaffold + temporal profiler** (`ARCHITECTURE.md §12`) before any other backend feature | golden timelines, property tests and tier-leak test pass; hot path p95 ≤ 300 ms |
| 1 | Chat takeover + **motion L2 (gesture + spring)**, lab router, approved provider rows and order sheets | composer replaces bar continuously; rows match `02`; any extra sign-in/purchase scope waits for §2 decision |
| 1b | **Wire the existing Luna API** (`apps/api`, LangGraph) using the 6.9 contract | golden set passes; web works with the API off; source shows in the log |
| 2 | Guide, approvals + events, banner | six waypoints any order; belt saved; approval lists shared / never shared |
| 3 | Recovery, Services / Me, merchant + onboarding | cash and card paths end at `READY` or `PREPARED_NOT_FILED`; order accepted → ready-time |
| 4 | Backstage, tour, retouch list | triggers fire once; log filters |
| 5 | Resident/VIP arc (R-series) | Gate R in §4 |
| loop | **Next picked case** from `docs/services/cases.md` (§7.4) | that case's checks in `cases.md` |

Audits at every gate: bridge audit `rg "quote\.|QUOTED|cart\.request|rx\.request|pickup\.request|payment\.charge"` returns nothing · no `allow-same-origin` · every price says `(demo)` · status codes follow `ARCHITECTURE.md` §4; success words follow CLAUDE.md rule 1 · no real brands.

### 6.7 iPhone requirements

`viewport-fit=cover` and `env(safe-area-inset-*)` · `100dvh`, never `100vh` · `-webkit-backdrop-filter` beside `backdrop-filter` · inputs ≥ 16 px (no zoom) · `overscroll-behavior: none` on the shell · 44 px targets · no hover-only affordances · live compass needs HTTPS and a tap (`DeviceOrientationEvent.requestPermission`), so fall back to the manual bearing.

View it: `cd apps/web && npm run dev -- --host`, then `http://<pc-ip>:5173` on the iPhone (same Wi-Fi; allow the Windows firewall prompt), then Share → Add to Home Screen. HTTPS (tunnel or deploy) only when testing the compass or sharing a link.

### 6.8 Motion (Home): all three levels (founder: "use all")

Goal: scrolling and swiping Home feels fluid, with content coming into place under the finger. This is a web app, so "Metal shaders" means a **WebGL2 canvas** (Safari runs it through Metal). No native Metal. Palette stays locked.

| Level | What | How |
|---|---|---|
| **L1 Scroll-linked reveal** | Hero, question card and the three "Try asking" cards translate (24 px → 0), scale (.97 → 1) and fade **as the finger moves**, staggered. AI search compresses on scroll. Hero art parallaxes at ~0.4× | CSS scroll-driven animations (`animation-timeline: view()` / `scroll()`, `animation-range: entry 0% cover 35%`). Fallback when unsupported: `IntersectionObserver` + `requestAnimationFrame` writing CSS variables |
| **L2 Gesture + spring** | Home ↔ chat is one continuous, interruptible motion. Dragging up from the glass bar morphs the capsule into the composer; Home content slides up and dims; the chat header slides in. Back chevron or swipe down reverses it. Rubber-band at the ends | Spring physics (stiffness ~300, damping ~30) with pointer drag + velocity; shared-layout transition for bar → composer. Never block input mid-animation |
| **L3 Shader field** | A slow, fluid background behind the hero: domain-warped noise in the locked palette (cyan `#0A9CC2` → `#E3F6FB` → white). Scroll velocity and touch drive a soft ripple uniform. Optional: refraction highlight at the glass bar's edge | One `<canvas>` (WebGL2, GLSL ES 3.0) behind the hero only. Render at 0.5–0.75× scale, DPR cap 2, pause when hidden or off-screen |

Constraints: 60 fps target on iPhone 12 or newer; a single canvas; text contrast stays AA over the field (keep it low-contrast under cards); honour `prefers-reduced-motion` (no parallax, no ripple, static gradient); fall back to a static gradient if WebGL2 is missing or the frame budget is blown; no layout-thrashing reads in scroll handlers; `will-change` only during motion. Add a `?fps` overlay for on-device checks (there is no Mac Inspector assumed). The glass bar keeps `backdrop-filter` as its fallback look.

**Effect libraries (founder-supplied, copied as-is in `demo/_ref/visuals-libraries.md`):** `BorderBeam` (composer / goal-plan card while working), `VoiceBeam` + `useMicrophone` (mic button; needs HTTPS and a tap, so keep a typed fallback), `ThinkingOrb` (bot avatar and inline "working", replacing typing dots). Rules: palette locked (use `ocean` / `mono` or token `colors`), one glow at a time, pause under reduced motion, never imply a result. ShipSwift `SWMetal` is the shader reference; the later MIT/notice note in `demo/_ref/visuals-libraries.md` supersedes its earlier do-not-copy note.

### 6.9 Luna service (LangGraph, `apps/api`)

Purpose: real user-understanding behind the lab router. The backend and local frontend wiring are implemented, with serial turns and an explicit 15 s fallback. This contract differs from the legacy `demo/luna.js` mock.

- **Implemented endpoint:** `POST /api/luna/turn`, input `{ text, thread_id?, user_id? }`; text is 1–600 characters. The client must retain a stable thread id to continue a conversation; omitting it creates a new thread. `user_id` is currently caller-supplied with default `demo-user` (local demo only; auth/isolation remain planned).
- **Output:** `intent`, `confidence`, `item`, `where_lost`, `service`, `category`, `subcategory`, `terminal`, `stated_facts`, `reply`, `clarify`, plus `via: "langgraph"`, `model`, `ms`, `remembered`, `told`, `turns`. Source: `apps/api/app/luna/schema.py` and `graph.py`. Intents: `lost_item`, `airport_guide`, `service_offers`, `places_near`, `greeting`, `smalltalk`, `unclear`.
- **Graph:** `normalize` (whitespace/length) → `understand` (OpenAI structured output) → `validate` (intent slots, allowed subcategories, confidence gate, URL/phone stripping) → `remember` (model-extracted stated facts). Reply/status and stated-fact restrictions also exist in the prompt; deterministic enforcement is incomplete and must not be described as guaranteed.
- **Current memory:** `InMemorySaver` per thread and `apps/api/data/memory.json` for told facts. `GET /api/memory/{user_id}` reads current facts; `DELETE /api/memory/{user_id}/{key}` removes that key from the JSON store. Same-browser plain-text chat/report continuity and durable local SQLite action drafts are implemented. Server chat persistence and the temporal profiler remain planned; full forgetting across checkpoint history is not implemented.
- **Config:** OpenAI SDK in `apps/api/app/config.py`, using `LUNA_MODEL`, `LUNA_EFFORT`, `LUNA_TIMEOUT_S` (default 20 s). `LLM_PROVIDER` does not yet implement provider switching; `FAST_MODEL`/`FAST_EFFORT` are not a routed fast pass. Keys stay server-side. Defaults: `gpt-6-luna` / `high`; configurable alternative `gpt-6.1-sol` / `medium`. The handoff reports earlier live 11/11 runs and multi-second latency; these were not rerun during step 00.
- **Client to build:** call the same-origin endpoint when served by the API; retain the lab router as fallback. Use the handoff’s **15 s client wait budget** initially, with a working indicator; the older 2.5 s proposal is superseded. Map API `confidence/category/subcategory` to the lab’s `conf/cat/sub`, handle all allowed intents, and prevent late replies from dispatching a second flow after fallback. Frontend cancellation alone does not cancel server work or memory writes; streaming/fast-pass behavior still needs a decision.
- **React port later:** add a Vite `/api` proxy; no Vite client/proxy exists today. Published Artifacts remain the scripted lab.
- **Other implemented endpoints:** `/api/health`, `/api/places/search`, `/api/route`; `/` redirects to `/lab/home-v2-cyan.html`. Live Places/map wiring remains pending.
- **Run/tests:** see `demo/run.md`. Current offline coverage is recorded in the handoff; 11 optional live golden cases remain separate; profile JS suite: 92 checks. TS contract testing, browser parity and persistent-profiler gates are not implemented.

### 6.10 Open items (defaults apply unless the founder overrides)

- Missing references: `01b-guide` (stop 1 open) and `02b-shop-sheet`: derive from `01c` and `02a`.
- Tab labels are decided: **io · Maps · Services · Me**. Older Companion/Civic prompts are historical.
- No motion reference exists (the founder's "Wapi" example could not be identified): build from 6.8 and review on the phone; adjust easing and stagger by eye.
- **Dark mode:** not in the first pass. Reference captured (`x-location-geofence-darkmode.jpg`); build tokens as CSS variables so a dark set drops in at step 4 if the founder says go.
- **Location / geofencing:** the web app has no background geofencing (CLAUDE.md rule 8) and never claims an indoor position (rule 3). Proximity scenes stay operator-fired `Demo trigger`s; an optional foreground `navigator.geolocation` button may be added behind explicit consent, labelled as approximate. The pin on any map is a place the user confirmed.
- Durable chat memory and the persistent temporal profiler are IN (§2, step P); the lab currently uses fixtures and the API uses JSON/in-memory stand-ins. Arabic RTL stays LATER. Arrival-side maps and image licensing remain unfinished verification tasks.

## 7. Home v2 + services loop (13 Oct)

### 7.1 Platform order
- **HTML web app first** (`apps/web/`, ES modules, served directly by `apps/api` at `/`). Modules are laid out like `apps/web/src/{shaders,motion,…}`, so any future React port is a copy.
- **Vite + React second:** the picked shell and accepted cases are ported into `apps/web` if needed.
- **Swift later** (needs a Mac + Xcode).
- Shaders match native (Safari runs WebGL2 on Metal). Native-only upgrades, kept for later: real Liquid Glass refraction, 120 Hz, haptics, share-sheet target, Live Activities.

### 7.2 Home v2 shell (`apps/web/index.html`)
- **Layout:** brand row · **coverflow stage** · swatch rail · caption line · bottom composer above the idle glass tab bar (§6.4). **No "Good morning {name}" + card list.**
- **Onboarding:** soft reveal, one card at a time (blur → sharp). Current web app uses its own shader sweep; `img-fx` is a React-port option. Founder feedback below requires slower, smoother card motion.
- **"You, over time" card:** the profile with a timeline scrubber; chips glow by confidence.
- **"Try:" cards** come from `cases.md`.
- **Stage shader:** one WebGL2 canvas behind the DOM cards.
  - Centre card's band: **top aura** (dual-Kawase blur, ~1.35× width × 0.45× height) + **bottom glow** (mirrored, 24–40 px, 10–15%). Side cards get neither.
  - Rendering: linear light, filmic tone map, blue-noise dither. Band at 1.0× DPR (cap 3), aura at 0.5×. Tiers A/B/C (C = video poster); reduced motion → static.
- **Shader ports** (ShipSwift `SWMetal`, MIT, notice kept):
  - GrainGradient / AnimatedMeshGradient: bands
  - Foil: best price
  - PolishedAluminum + IntenseBling: fastest/premium
  - Glitter: provider events only
  - ChromaticGlass: paperwork
  - LiquidChrome: totals
  - `metal-fx` silver on the one primary CTA
  - One glow at a time.
- **Palette:** cyan selected on 13 Oct, with the approved purple fringe. The chromatic page/branches remain only until cleanup. C1’s reflection style is approved on all stage cards at 70% of its former `0.55` strength (`0.385`); keep the cyan theme.
- **Implemented flags:** `?tune`, `?fps`, `?nogl`, `?intro`, `?wifi`, `?services`, `?maps`, `?guide`, `?profile` (or dot-separated hash flags). `?scene=<case>` and `?asof=<iso>` are planned; the current app does not parse their values.

### 7.3 Services surface (universal; from the pets ref's app style)
- **Current category registry:** `CATEGORIES` in `apps/web/data.js`; competing service/provider data is `SERVICE_GROUPS` in `apps/web/offers.js`. `fixtures/categories.json` does not exist. Planned `registry.categories` fields: id, group `shops|service`, label, glyph, subcategories, sources, answer types, linked case. Add categories as data rows and match their `keywords`/`subKeys` in the current router; new answer types/actions may still need code or a plan change.
- **Surface:** glass category menu (All + categories + subcategories, searchable) · map ↔ list toggle (glyph pins / photo tiles) · one bottom sheet for any place.
  - The sheet shows: photo, name, category chip, ★ · Google, distance estimate, "Partner (demo)".
  - Its actions depend on what the provider supports: Directions / Call / Book / Order / Open app.
- **Placement (updated 13 Oct):** the **Maps** tab opens this surface (near me); cases open it pre-filtered. An ask with no matching category maps to the nearest one or "Other", and still shows results. The **Services** tab is a separate path: competing providers (partner/merchant mini-apps, websites, marketplaces) with published offers and Best-price / Fastest badges; mini-apps open sandboxed and end in one approval. **io** is chat + cards; asking flies the cards up.
- **Truth:** pins only from Places or partners; the user dot only with consent; Places on a Google Map with attribution (live).

### 7.4 The loop
| Step | Who | What | Done when |
|---|---|---|---|
| 1 Pick shell | Founder | Cyan selected on 13 Oct; review remaining motion/reference details on the iPhone | Palette recorded; remaining UI notes logged |
| 2 Pick next case | Founder | Claude asks with `idea` / `rebuild` cases from `docs/services/cases.md` | `picked` |
| 3 Build | Claude | implemented web flow flags (scene IDs remain planned), media, episodes → profile, Artifact republished, audits | `built`, link sent |
| 4 Review | Founder | On the iPhone; notes by message or Artifact comments | Logged in the case, `in review` |
| 5 Rebuild | Claude | Apply notes, re-audit, same link | Accept → `accepted`; else back to 4 |

New ideas follow `docs/services/intake.md` (see CLAUDE.md "Service intake"). A case enters this plan only as "needs plan change", after the founder agrees.

### 7.5 Gaps found by the founder (13 Oct, end of session): do these next

The web app rebuilt onboarding, the chat flows and the map, but most of the approved `design/references/` screens were never carried over. **This was not by design. Every surface must match its reference image.**

1. **Home reference (`01-home.png`) becomes the top of Services.** Use its hero and its card layout. Swiping up reveals more services. Drop the repeated "AI assistant" boxes in that image: the one composer at the bottom is the only chat input.
2. **Services are too verbose.** Group them logically as in `01-home.png`, with short labels and few words per card. Keep competing offers one level down.
3. **The lost-item / transport story is lost and too rigid.** Rebuild C6 to `04-lost-item.png` and `04a-driver-rta.png`: the driver detail sheet, the RTA report sheet, and the card and cash trace paths from v1 (`demo/app.js` `recovery`, `traceByCard`, `traceByCash`, `rtaReport`). The initial chat-only report was a stub. The local draft/simulation exists (§7.7), but the founder rejected its manual handoff (§7.8); C6 is back in rebuild pending supported agentic execution and phone/reference approval.
4. **Port the rest of the reference set** (`01a`–`06`, `x-*`) to the §6.3 reference map. Check each screen against its image with a 390 px screenshot before calling it done.
5. **Palette: cyan, picked by the founder on 13 Oct.** Remove the chromatic page and its branches.

### 7.6 Step 00 and current visual feedback

- [x] Step 00: align canon, handoff, routed references and run instructions with the actual lab/API state; keep scope conflicts in §2 explicit.
- Founder note (verbatim): "cards flying up in onbording should be smoother and slower, now they are super fast".
- Founder reference: `Try · C1`, "A new maid with visa, before 1 Nov.", has the preferred laser/chromatic reflection. Apply the same effect to every stage card at **70% of its previous intensity**, including C1.
- Local implementation: first intro reveal 2.0 s, subsequent reveal 1.8 s, slower onboarding spring, eased upward exit 1.5 s with 90 ms staggering; onboarding-to-chat lift 1.5 s. Reduced motion remains immediate. Reflection strength is `0.55 × 0.70 = 0.385`, with a static no-WebGL fallback.
- Phone review remains pending; local file changes do not republish the private Artifacts.

### 7.7 In-app pages and account connections (13 Oct founder decision)

- Apply one navigation policy throughout the host: registered HTML pages open inside Dubai-io; ordinary external HTTPS links first open an in-app page/handoff. Back preserves host form values. Browser continuation must be explicit. Provider widget navigation still belongs to the separately owned sandbox/bridge task.
- Local implementation: `page-host.js` owns registered pages/destinations, Back/Close and host link routing; Me and C6 use it; `provider-pages.js` gives provider cards a uniform whole-card Open action and routes website/marketplace cards into shared request preparation. `accounts.js` consumes provider metadata from `/api/auth/connections`. Google is visibly **not configured**, Connect is disabled and `/api/auth/google/start` returns 503. Other OAuth providers can join the metadata registry. The configured connector can save encrypted grants; no live grant has been created in this development session.
- Founder answer: **Prepare the integration; OAuth client is not configured yet.** Live Google connection now needs the public client ID, web-client secret in the server environment and registered callback. Anonymous local sessions and the tested encrypted connector are implemented; production account/role handling remains pending. API keys for Places/Routes are separate from Google OAuth.
- Reuse each provider’s authorized grants across host capabilities with appropriate consent/scopes. App sign-in does not confer third-party website cookies or authorize every merchant. Tokens never enter HTML cards, srcdoc, URLs or localStorage. Additional scopes require provider consent.
- PWA boundary: RTA’s official page returns `X-Frame-Options: SAMEORIGIN`; its host-owned HTML guidance stays in-app, while the real portal is an explicit continuation. Google prohibits embedded user agents for OAuth: use its secure browser flow, then return to the app. An unrestricted Instagram-style website viewer requires a native browser container; native packaging remains outside the current contest PWA.
- C6 rebuilt locally: card/cash simulated match and no-match paths, cancellable trace, fictional driver details/chat, user-supplied report facts, prepared report and the shared saved-request flow. The rejected static guidance page was removed; manual copy is secondary only. No government filing or recovered claim. Reference/phone review remains pending. Services landing rebuilt around the visitor hero, area choices, short suggestions and fixed-price categories.
- Separate LLM owns step 03 on an isolated `feat/miniapp-bridge` branch: `offers.js`, provider mini-apps and bridge validation/tests. Do not edit or merge that work until its progress/diff/report is reviewed.
- Local browser checks: 390 × 844 Chromium, WebGL active; nested navigation/report preservation and input during intro exit pass. iPhone review and private Artifact publication remain pending.

### 7.8 Shared agentic execution requirement (founder correction, 13 Oct)

- Applies to **all services**, including taxi lost items. The founder rejected the “Official guidance / Your report stays here” substitute and a required copy/paste report. §7.7 describes existing scaffolding, not acceptance of that flow.
- Required loop: understand the outcome → reuse confirmed facts → ask only for missing data → select a registered provider capability → prepare the action → show recipient, exact data, cost and effect for approval → execute via a supported API or browser adapter → return provider evidence/reference and track the outcome in chat. HTML cards are controls for this work, not pretend provider pages.
- Prefer provider APIs; use a registered server-side browser adapter where supported. Preserve provider-specific authorized sessions centrally. User interaction is limited to facts, consent/approval and authentication challenges the adapter cannot complete. A website opening or successful field fill is not a submitted order/report.
- Manual copy/paste, generic guidance and fictional website previews cannot fulfill this gate. Optional manual alternatives may remain secondary, explicitly manual. When no adapter is available, report the specific blocker and retain the prepared action; never show a fake working Submit/Agent button or infer success.
- The local shared action engine, draft persistence and anonymous sessions are implemented (§7.9); production provider adapters and cross-device account sessions remain pending. Google OAuth is still unconfigured. C6 remains a draft/simulation; its current handoff is rejected and requires another rebuild. Browser rendering checks do not establish agentic completion.
- This direction supersedes manual handoffs as the default service product. It does not authorize an actual transaction/report in this development session. The existing government-execution restriction needs a narrowly registered, reviewed capability before any future RTA submission; other government payments/bookings are not implicitly added.
- Build the shared executor/capability contract once, then add adapters per service. Keep the separately assigned order-only mini-app bridge isolated; no new widget auth/business scopes are implied.

### 7.9 OAuth-independent implementation completed locally

- `chat.js` + `luna-client.js`: real `/api/luna/turn` client on the API origin, stable thread, serialized requests, allowlist/confidence mapping, labelled 15 s fallback and stale-response/reset guards. Source/model/latency and remembered facts are visible. Browser integration was checked with an offline response; no paid model call was made.
- `actions.py`: eight registered preparation capabilities (seven service categories + taxi report), typed user-supplied inputs, private anonymous cookie sessions, durable local SQLite drafts and events, payload-bound preparation retries, snapshot/revision/recipient/effect/price-bound approval, single dispatch, evidence gate and UNKNOWN_STATUS after ambiguous outcomes/restart. Discard is allowed only before dispatch. No live adapter is registered.
- `service-workflow.js`: shared preparation/review UI, missing-field handling, per-provider local drafts and Me → Saved requests. Taxi Continue uses this flow. Unsupported execution reports its blocker; there is no fake Send action or required copying. Existing merchant widget orders stay in the separately owned bridge scope.
- `session-state.js` + saved details: same-browser plain-text conversation/report continuity, restored report controls, persistent user-given details and scoped view/edit/forget API. Luna checkpoints are scoped to the cookie owner when present and to the thread. Production server transcript replay/roles are still pending.
- `oauth.py` + `auth.py`: Google state/PKCE browser flow, exact callback/origin check, verified userinfo, encrypted grants, backend-only token reuse/scope checks, serialized refresh and revocation. Google remains unconfigured until server credentials/callback are supplied. Identity scopes alone do not authorize other Google services or merchant websites.
- Cyan cleanup: removed the retired chromatic entry point and CSS/map/palette branches; the approved cyan reflection remains.
- Still required: live provider/RTA adapter validation, bridge branch review, remaining reference screens, iPhone review/publication, production React/Postgres/widget hosting/SSE/outbox/profiler and cross-device auth. OAuth credentials alone do not supply merchant/RTA execution access.
