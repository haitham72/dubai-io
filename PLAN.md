# Dubai-io — Plan

**Updated:** 13 Oct 2026 (late) · **Status:** **Plan v1.5** · handoff: `demo/_ref/handoff.md` (Home v2 + temporal profiler + services loop in §7) · **Owner:** Haitham
This is the single plan. Scope, demo and phases live here, and nowhere else. (Decision log lives on `main`; `build` is code-only.)
**Founder lock (10 Oct, final): bidding/quote is ABSOLUTELY REJECTED. Every service opens as a modal HTML mini-app (services / shops / stores / rides) with published fixed prices.**
**Founder decision (12 Oct): the Resident/VIP arc (items 10–11) moves from LATER to IN, built after the visitor redesign. Providers answer slot/availability requests at published fixed prices. The quote lock above is unchanged.**
**Founder decisions (13 Oct):**
- The **temporal profiler is core** (visible hypotheses, `ARCHITECTURE.md §12`).
- **Home v2** (shader coverflow, soft reveal) and the universal **Services surface** come first.
- Service cases live in `demo/_ref/services/cases.md`, are picked one at a time (§7), and are ~1% of the app; the generic engine covers the rest.
- The quote lock is unchanged.

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
| 11 | **Service cases:** picked from `demo/_ref/services/cases.md` by C-ID (maid with visa, cloth try-on, barber, pets, food, video → map, …). Fixed prices, fictional demo providers | Services |
| 12 | **Temporal profile:** visible hypotheses that learn over time, "You, over time" card, "Because…" on every re-rank (`ARCHITECTURE.md §12`) | Companion |
| 13 | **Services surface:** data-driven category registry, map ↔ list, one bottom sheet for any provider (§7.3) | Services |

**If time runs out, cut in this order:** 11 → 10 → 9 → 5 → 4. Items 1, 2, 3, 6, 7, 8, **12 and 13** are the floor: memory + follow-through *is* the product.

### LATER (vision, not in the contest build)

Civic RAG with citations · resident bills and Salik/DEWA displays · community · background geofencing · ticket wallet · payments · media memory · Arabic RTL UI (Arabic answers are fine) · native app (Swift; ShipSwift originals, Liquid Glass, haptics, share extension) · live AR try-on · marketplace feeds via affiliate APIs.

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
- [ ] Update the sketch to arc v2: deadline-conflict branch, time-aware ride reasoning, RTA fields in the lost-item report, cyan host strip, remove Civic tab, compact backstage, "Scripted demo" label
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

**Handoff for the build agent.** Read order: `CLAUDE.md` → this section → `demo/_ref/redesign.md` (prompts and exact copy) → the images in `demo/_ref/`. Branch `redesign`. This section replaces the Next.js front-end assumptions in Phases 1–3; the backend phases are unchanged. Build the **visitor redesign to parity first**, then the Resident/VIP arc (items 10–11).

### 6.1 Definition of done

- Runs in **iPhone Safari at 390 × 844**, and Add to Home Screen works. No native iOS build. The only server is the small Luna API (6.9); the app still works without it (mock fallback).
- Same story as §3 (arrival → laundry deadline → taxi memory), plus Luna rows (community, shopping), the waypoint guide and the lost-item cash/card paths, all in the redesigned look.
- Every rule in `CLAUDE.md` still holds (truth in status, fixed prices, sandbox, approvals, no government execution, no quotes).
- Gates in 6.6 pass, with screenshots next to the reference images.

### 6.2 Structure

```
apps/web/
  index.html            viewport-fit=cover, theme-color, apple-mobile-web-app-*, apple-touch-icon (orb)
  public/miniapps/      dxb-guide.html, community.html, shop.html, merchants (copy from demo/miniapps)
  public/maps/          copy of demo/maps
  src/styles/           tokens.css (demo/styles.css tokens + glass), base.css
  src/data/             fixtures.ts  (from demo/data.js)
  src/luna/             client.ts (API first, mock fallback), mock.ts (from demo/luna.js, same contract)
  src/motion/           scroll reveal, spring + gesture, reduced-motion helpers (6.8)
  src/shaders/          HeroField.tsx + GLSL (WebGL2 canvas behind the Home hero) (6.8)
  src/bridge/           host.ts (scopes, handler table), MiniAppSheet.tsx (iframe sandbox="allow-scripts")
  src/state/            store.ts (one reducer or zustand; epoch guard, dedupe map)
  src/components/       AppBar, AISearch, GlassTabBar, Composer, Bubble, Card, Chip, Pill, StatusTag, Sheet, Banner
  src/screens/          io (Home), Maps, Services, Me, Backstage
  src/flows/            journey, rows, join, purchase, recovery, triggers, laundry, tickets, faith
apps/api/               Luna only: FastAPI + LangGraph (6.9). Not needed to run the web app
```

Dependencies (web): `react`, `react-dom`, `vite`, `typescript`, `vitest`, `@playwright/test`, a spring/gesture lib (`framer-motion` or `@use-gesture/react` + `react-spring`), a tiny WebGL helper (`ogl`, or raw WebGL2), founder-supplied effect libraries `border-beam`, `voice-glow`, `thinking-orbs`, plus `metal-fx` (silver only), `img-fx` (+`three`, lazy-loaded) and `liquid-gooey` (all npm-verified, MIT; pin exact versions, see `demo/_ref/visuals-libraries.md`), `zustand` optional. Plain CSS (CSS modules). No UI kit.

### 6.3 Reference map

| Screen / state | Reference | Build as |
|---|---|---|
| Home, idle | `01-home.png`, left half of `01a-chat-takeover.png` | AISearch top, GlassTabBar, HeroCard, QuestionCard, TryAsking |
| Chat active | right half of `01a-chat-takeover.png`, `02-rows.png` | compact header + back chevron, Composer replaces the tab bar, LunaChip, RowsCard |
| Guide (built-in mini-app) | `01c-guide-states.png`; spec only: prompt 1b in `redesign.md` (no image for stop 1) | `dxb-guide.html`, restyled; stop media from `public/maps` |
| Partner sheet | `02a-partner-sheet.png` | `community.html` (sign-in then signed in) |
| Shop sheet | no image; derive from `02a` + prompt 2b | `shop.html` |
| Approval + events | `03-approve-events.png` | ApprovalCard, StatusTrack, UpdateBubble, CalendarCard |
| Banner | `03a-banner.png` (Home behind it must show the glass bar) | Banner |
| Lost item | `04-lost-item.png`, `04a-driver-rta.png` | RecoveryFlow, DriverSheet, ReportSheet |
| Services / Me | `05-services-me.png` (add AI search + glass bar per 6.4) | ServicesScreen, MeScreen |
| Merchant + onboarding | `05a-merchant-onboarding.png` | merchant mini-app, shop review sheet |
| Backstage (≥ 1100 px) | `06-backstage.png` | inbox, trigger panel, tools status, event log |
| Arrival notification | `x-arrival-notification.png` | in-app Banner on first load (web cannot do Live Activities) |
| First-run tour | `x-home-onboarding.png` | 3-step coach marks over the AI search |
| Chat effects: Beam, Voice, Orb + ShipSwift `SWMetal` shader ideas | `demo/_ref/visuals-libraries.md` (prompts copied as supplied; our notes in Part 3) | Composer `BorderBeam` / `VoiceBeam`, bot avatar `ThinkingOrb`, GLSL ideas for L3 |
| Dark theme + map pin + permission card | `x-location-geofence-darkmode.jpg` (Apple Find My / Maps screenshot, **style reference only**, third-party names must not appear) | dark token set (`prefers-color-scheme` + manual), guide lightbox pin with an "approximate" ring, Me → Permissions "Notifications are off" card, detail-sheet pattern (title, status, two actions) |
| Resident/VIP | R-series prompts, no images yet | after visitor parity |
| Home v2 stage | `demo/_ref/carousel/carousel*.jpg` (aura above, glow below), `carousel/holographi ccards.mp4` (holo finishes), ShipSwift `SWMetal` (MIT) | §7.2 |
| Services surface + cases | `demo/_ref/services/` tree (pets = surface pattern; cloth, coffee, restaurants, "Pulled data services") | §7.3, `cases.md` |

Ignore `demo/_ref/_rejected/`. Fix on the way: `06` shows the real brand "Carrefour Express" (use "Marina Fresh (demo)"); `00`'s button reads "Indoor nav" (use "Arrival guide"; no indoor-position claims).

### 6.4 Navigation model (decided)

1. **Idle (13 Oct):** brand row on top, the **composer docked at the bottom** above a floating Liquid Glass tab bar **io · Maps · Services · Me** (Civic removed from the nav; civic stays LATER). Asking flies the Home cards up into the full-screen map (§7.3).
2. **Chat active** (typed, or a suggestion tapped): compact header (back chevron, "Dubai-io", search icon); the glass **Composer replaces** the tab bar. Never show both.
3. **Back chevron:** returns to idle.
4. Sheets cover the bar; banners slide over the top.
5. Companion keeps its label and the orb icon (as in the references). Rename to "Home" only if the founder says so.
6. Home chrome follows `01a` (left); the skyline art lives inside the hero card, not as a full-bleed background.

### 6.5 Port the logic, don't redesign it

Source of truth for behaviour is `demo/app.js`, `demo/data.js`, `demo/luna.js`. Port as typed modules:

| Behaviour | Demo source | Notes |
|---|---|---|
| Journey: setStep, confirmWaypoint, I'm lost | `app.js` journey section | state is host-owned, pushed down to the iframe |
| Luna first (API, then mock), regex router as fallback | `luna.js`, composer `onsubmit` | keep confidence ≥ 0.6, 22 fallback cards; log `via: langgraph \| mock-luna` |
| Rows: community + shopping, sign-in, join approval, purchase event → calendar | `providerRows`, `joinApproval`, `purchaseReported`, `signIn` | prices `AED x (demo)`; dedupe by order ref |
| Approval + fixed-order machine | `approval`, `createRequest`, `transition`, `FLOW`/`ALLOWED` | single approval, idempotent |
| Laundry deadline loop | `laundryDeadline`, `laundryMerchantFlow` | no re-quote |
| Recovery (card + cash, RTA report) | `recovery`, `traceByCard`, `traceByCash`, `rtaReport` | epoch guard; cash outcome alternates |
| Triggers + dedupe 2500 ms | `TRIGGERS`, `fireTrigger` | same-window messages only |
| Faith, parking, photo search, departure, day plan, tickets, onboarding sim | matching sections | keep fixtures |

Bridge: scopes in each manifest AND a handler in the host table; unknown or out-of-scope kinds log `BLOCKED` and reply `host.error`. Sandbox stays `allow-scripts` only; no `allow-same-origin`.

### 6.6 Build order and gates

| Step | Build | Gate (Playwright iPhone profile, 390 px) |
|---|---|---|
| 0 | **Home v2 lab → picked shell** (§7.2) ported in: scaffold, tokens, coverflow stage + shaders, soft reveal, "You, over time", Services surface | founder picked the shell on the iPhone; aura + glow visible; fallbacks work |
| P | **`apps/api` scaffold + temporal profiler** (`ARCHITECTURE.md §12`) before any other backend feature | golden timelines, property tests and tier-leak test pass; hot path p95 ≤ 300 ms |
| 1 | Chat takeover + **motion L2 (gesture + spring)**, Luna mock, rows, partner + shop sheets | composer replaces bar with a continuous, interruptible transition; rows match `02`; sign-in → signed in; purchase → calendar card |
| 1b | **Luna API** (`apps/api`, LangGraph) behind `LUNA.understand` | golden set passes; web works with the API off; `via` shows in the log |
| 2 | Guide, approvals + events, banner | six waypoints any order; belt saved; approval lists shared / never shared |
| 3 | Recovery, Services / Me, merchant + onboarding | cash and card paths end at `READY` or `PREPARED_NOT_FILED`; order accepted → ready-time |
| 4 | Backstage, tour, retouch list | triggers fire once; log filters |
| 5 | Resident/VIP arc (R-series) | Gate R in §4 |
| loop | **Next picked case** from `demo/_ref/services/cases.md` (§7.4) | that case's checks in `cases.md` |

Audits at every gate: bridge audit `rg "quote\.|QUOTED|cart\.request|rx\.request|pickup\.request|payment\.charge"` returns nothing · no `allow-same-origin` · every price says `(demo)` · status words only from the CLAUDE.md list · no real brands.

### 6.7 iPhone requirements

`viewport-fit=cover` and `env(safe-area-inset-*)` · `100dvh`, never `100vh` · `-webkit-backdrop-filter` beside `backdrop-filter` · inputs ≥ 16 px (no zoom) · `overscroll-behavior: none` on the shell · 44 px targets · no hover-only affordances · live compass needs HTTPS and a tap (`DeviceOrientationEvent.requestPermission`), so fall back to the manual bearing.

View it: `cd apps/web && npm run dev -- --host`, then `http://10.5.3.228:5173` on the iPhone (same Wi-Fi; allow the Windows firewall prompt), then Share → Add to Home Screen. HTTPS (tunnel or deploy) only when testing the compass or sharing a link.

### 6.8 Motion (Home): all three levels (founder: "use all")

Goal: scrolling and swiping Home feels fluid, with content coming into place under the finger. This is a web app, so "Metal shaders" means a **WebGL2 canvas** (Safari runs it through Metal). No native Metal. Palette stays locked.

| Level | What | How |
|---|---|---|
| **L1 Scroll-linked reveal** | Hero, question card and the three "Try asking" cards translate (24 px → 0), scale (.97 → 1) and fade **as the finger moves**, staggered. AI search compresses on scroll. Hero art parallaxes at ~0.4× | CSS scroll-driven animations (`animation-timeline: view()` / `scroll()`, `animation-range: entry 0% cover 35%`). Fallback when unsupported: `IntersectionObserver` + `requestAnimationFrame` writing CSS variables |
| **L2 Gesture + spring** | Home ↔ chat is one continuous, interruptible motion. Dragging up from the glass bar morphs the capsule into the composer; Home content slides up and dims; the chat header slides in. Back chevron or swipe down reverses it. Rubber-band at the ends | Spring physics (stiffness ~300, damping ~30) with pointer drag + velocity; shared-layout transition for bar → composer. Never block input mid-animation |
| **L3 Shader field** | A slow, fluid background behind the hero: domain-warped noise in the locked palette (cyan `#0A9CC2` → `#E3F6FB` → white). Scroll velocity and touch drive a soft ripple uniform. Optional: refraction highlight at the glass bar's edge | One `<canvas>` (WebGL2, GLSL ES 3.0) behind the hero only. Render at 0.5–0.75× scale, DPR cap 2, pause when hidden or off-screen |

Constraints: 60 fps target on iPhone 12 or newer; a single canvas; text contrast stays AA over the field (keep it low-contrast under cards); honour `prefers-reduced-motion` (no parallax, no ripple, static gradient); fall back to a static gradient if WebGL2 is missing or the frame budget is blown; no layout-thrashing reads in scroll handlers; `will-change` only during motion. Add a `?fps` overlay for on-device checks (there is no Mac Inspector assumed). The glass bar keeps `backdrop-filter` as its fallback look.

**Effect libraries (founder-supplied, copied as-is in `demo/_ref/visuals-libraries.md`):** `BorderBeam` (composer / goal-plan card while working), `VoiceBeam` + `useMicrophone` (mic button; needs HTTPS and a tap, so keep a typed fallback), `ThinkingOrb` (bot avatar and inline "working", replacing typing dots). Rules: palette locked (use `ocean` / `mono` or token `colors`), one glow at a time, pause under reduced motion, never imply a result. ShipSwift `SWMetal` is a learning source for L3 shader techniques only (re-implement in GLSL; check its licence before reusing code).

### 6.9 Luna service (LangGraph, `apps/api`)

Purpose: real user-understanding behind `LUNA.understand`. The web app is still a demo that works offline.

- **Endpoint:** `POST /luna/understand` with `{ text, context? }` → `{ intent, category, interests[], origin, item, trace, confidence, via, matched[] }`, **the same shape as `luna.js`**. Intents are a registry allowlist (`community.find`, `shopping.buy`, `lost_item.taxi`, `none`, later the resident/VIP intents). Luna returns understanding only; no actions, no HTML, no URLs (CLAUDE.md rule 7).
- **Graph v1:** `normalize` (language, light transliteration) → `understand` (one LLM node, structured output with a Pydantic model) → `validate` (clamp to the allowlist, drop unknown slots, set `confidence`). Specialist subgraphs and a supervisor come later (see `ARCHITECTURE.md`: read-only and propose-only, no interrupt/resume).
- **Config:** provider and model from config (`LLM_PROVIDER`, `LUNA_MODEL`, `LUNA_EFFORT`), keys server-side only, never in the web bundle or in git; log text redacted. **Founder decision 13 Oct: OpenAI `gpt-6-luna` (high reasoning) or `gpt-6.1-sol` (medium).** Slice built in `apps/api` (LangGraph, stated-fact memory, Places/Routes proxy); golden set 11/11 on both; latency 4–9 s per turn, so streaming or a cheaper first pass is needed (see `demo/_ref/handoff.md`).
- **Web client:** `src/luna/client.ts` tries the API (`VITE_LUNA_URL`, via the Vite dev proxy `/api` so the iPhone needs no CORS or mixed-content), waits at most 2.5 s, then uses `mock.ts`. The log shows `via: langgraph` or `mock-luna`. Same dispatch, same 0.6 threshold, regex router still behind it.
- **Run:** `uvicorn app.main:app --host 0.0.0.0 --port 8000` in `apps/api`; Vite proxies `/api` to it.
- **Tests:** a golden set (the 19 router routes, community/shopping/lost phrasings, typos such as `egyutians` / `taksi`, Arabic) as pytest; a contract test against the TS type. The API is optional: all web gates must pass with it off.

### 6.10 Open items (defaults apply unless the founder overrides)

- Missing references: `01b-guide` (stop 1 open) and `02b-shop-sheet`: derive from `01c` and `02a`.
- Tab label **Companion** vs **Home**: default Companion.
- No motion reference exists (the founder's "Wapi" example could not be identified): build from 6.8 and review on the phone; adjust easing and stagger by eye.
- **Dark mode:** not in the first pass. Reference captured (`x-location-geofence-darkmode.jpg`); build tokens as CSS variables so a dark set drops in at step 4 if the founder says go.
- **Location / geofencing:** the web app has no background geofencing (CLAUDE.md rule 8) and never claims an indoor position (rule 3). Proximity scenes stay operator-fired `Demo trigger`s; an optional foreground `navigator.geolocation` button may be added behind explicit consent, labelled as approximate. The pin on any map is a place the user confirmed.
- Out of scope here: memory persistence / checkpointer, Arabic RTL, real arrival-side maps and image licensing (retouch list in `redesign.md`).

## 7. Home v2 + services loop (13 Oct)

### 7.1 Platform order
- **HTML lab first** (`demo/lab/`, ES modules, no build; edit → reload → private Artifact link on the iPhone). Modules are laid out like `apps/web/src/{shaders,motion,…}`, so the port is a copy.
- **Vite + React second:** the picked shell and accepted cases are ported into `apps/web`.
- **Swift later** (needs a Mac + Xcode).
- Shaders match native (Safari runs WebGL2 on Metal). Native-only upgrades, kept for later: real Liquid Glass refraction, 120 Hz, haptics, share-sheet target, Live Activities.

### 7.2 Home v2 shell (lab: `demo/lab/home-v2-cyan.html`, `home-v2-chromatic.html`)
- **Layout:** glass AI search · **coverflow stage** · swatch rail · caption line · glass tab bar / composer. **No "Good morning {name}" + card list.**
- **Onboarding:** soft reveal, one card at a time (blur → sharp, `img-fx` sweep).
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
- **Palette:** two lab pages, cyan+purple vs chromatic (chromatic only inside shader media). The founder picks; if chromatic wins, the CLAUDE.md palette line is updated.
- **Dev flags:** `?tune` · `?fps` · `?scene=<case>` · `?asof=<iso>`.

### 7.3 Services surface (universal; from the pets ref's app style)
- **Category registry** is data (`demo/lab/fixtures/categories.json` → `registry.categories`): id, group `shops|service`, label, glyph, subcategories, sources (Places types / partners), answer types, linked case. A new category is a row, not code.
- **Surface:** glass category menu (All + categories + subcategories, searchable) · map ↔ list toggle (glyph pins / photo tiles) · one bottom sheet for any place.
  - The sheet shows: photo, name, category chip, ★ · Google, distance estimate, "Partner (demo)".
  - Its actions depend on what the provider supports: Directions / Call / Book / Order / Open app.
- **Placement (updated 13 Oct):** the **Maps** tab opens this surface (near me); cases open it pre-filtered. An ask with no matching category maps to the nearest one or "Other", and still shows results. The **Services** tab is a separate path: competing providers (partner/merchant mini-apps, websites, marketplaces) with published offers and Best-price / Fastest badges; mini-apps open sandboxed and end in one approval. **io** is chat + cards; asking flies the cards up.
- **Truth:** pins only from Places or partners; the user dot only with consent; Places on a Google Map with attribution (live).

### 7.4 The loop
| Step | Who | What | Done when |
|---|---|---|---|
| 1 Pick shell | Founder | Opens both lab Artifacts on the iPhone | Palette recorded |
| 2 Pick next case | Founder | Claude asks with `idea` / `rebuild` cases from `demo/_ref/services/cases.md` | `picked` |
| 3 Build | Claude | `?scene=<id>`, media, episodes → profile, Artifact republished, audits | `built`, link sent |
| 4 Review | Founder | On the iPhone; notes by message or Artifact comments | Logged in the case, `in review` |
| 5 Rebuild | Claude | Apply notes, re-audit, same link | Accept → `accepted`; else back to 4 |

New ideas follow `demo/_ref/services/intake.md` (see CLAUDE.md "Service intake"). A case enters this plan only as "needs plan change", after the founder agrees.
