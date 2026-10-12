# Dubai-io — Plan

**Updated:** 12 Oct 2026 · **Status:** **Plan v1.4** (build plan for `apps/web` in §6) · **Owner:** Haitham
This is the single plan. Scope, demo and phases live here, and nowhere else. (Decision log lives on `main`; `build` is code-only.)
**Founder lock (10 Oct, final): bidding/quote is ABSOLUTELY REJECTED. Every service opens as a modal HTML mini-app (services / shops / stores / rides) with published fixed prices.**
**Founder decision (12 Oct): the Resident/VIP arc (items 10–11) moves from LATER to IN, built after the visitor redesign. Providers answer slot/availability requests at published fixed prices. The quote lock above is unchanged.**

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
| 11 | **Home services:** "fix it / maid / renovation" → rows from marketplace apps and found shops, each opens its own modal mini-app, fixed prices (fictional demo providers) | Resident |

**If time runs out, cut in this order:** 11 → 10 → 9 → 5 → 4. Items 1, 2, 3, 6, 7 and 8 are the floor: memory + follow-through *is* the product.

### LATER (vision, not in the contest build)

Civic RAG with citations · resident bills and Salik/DEWA displays · community · background geofencing · ticket wallet · payments · media memory · Arabic RTL UI (Arabic answers are fine) · native app.

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

- Runs in **iPhone Safari at 390 × 844**, and Add to Home Screen works. No native iOS build, no backend.
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
  src/luna/             mock.ts      (from demo/luna.js, same understand() contract)
  src/bridge/           host.ts (scopes, handler table), MiniAppSheet.tsx (iframe sandbox="allow-scripts")
  src/state/            store.ts (one reducer or zustand; epoch guard, dedupe map)
  src/components/       AppBar, AISearch, GlassTabBar, Composer, Bubble, Card, Chip, Pill, StatusTag, Sheet, Banner
  src/screens/          Home, Chat, Services, Civic, Me, Backstage
  src/flows/            journey, rows, join, purchase, recovery, triggers, laundry, tickets, faith
```

Dependencies: `react`, `react-dom`, `vite`, `typescript`, `vitest`, `@playwright/test` (+ `zustand` optional). Plain CSS (CSS modules). No UI kit, no router needed beyond screen state, no backend client.

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
| Resident/VIP | R-series prompts, no images yet | after visitor parity |

Ignore `demo/_ref/_rejected/`. Fix on the way: `06` shows the real brand "Carrefour Express" (use "Marina Fresh (demo)"); `00`'s button reads "Indoor nav" (use "Arrival guide"; no indoor-position claims).

### 6.4 Navigation model (decided)

1. **Idle:** AI search at the top, floating Liquid Glass tab bar (Companion, Services, Civic, Me) at the bottom, on every tab, no composer.
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
| Luna first, regex router as fallback | `luna.js`, composer `onsubmit` | keep confidence ≥ 0.6, 22 fallback cards |
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
| 0 | Scaffold, tokens, Home idle | matches `01-home` / `01a` left; glass bar visible; no composer |
| 1 | Chat takeover, Luna, rows, partner + shop sheets | composer replaces bar; rows match `02`; sign-in → signed in; purchase → calendar card |
| 2 | Guide, approvals + events, banner | six waypoints any order; belt saved; approval lists shared / never shared |
| 3 | Recovery, Services / Me, merchant + onboarding | cash and card paths end at `READY` or `PREPARED_NOT_FILED`; order accepted → ready-time |
| 4 | Backstage, tour, retouch list | triggers fire once; log filters |
| 5 | Resident/VIP arc (R-series) | Gate R in §4 |

Audits at every gate: bridge audit `rg "quote\.|QUOTED|cart\.request|rx\.request|pickup\.request|payment\.charge"` returns nothing · no `allow-same-origin` · every price says `(demo)` · status words only from the CLAUDE.md list · no real brands.

### 6.7 iPhone requirements

`viewport-fit=cover` and `env(safe-area-inset-*)` · `100dvh`, never `100vh` · `-webkit-backdrop-filter` beside `backdrop-filter` · inputs ≥ 16 px (no zoom) · `overscroll-behavior: none` on the shell · 44 px targets · no hover-only affordances · live compass needs HTTPS and a tap (`DeviceOrientationEvent.requestPermission`), so fall back to the manual bearing.

View it: `cd apps/web && npm run dev -- --host`, then `http://10.5.3.228:5173` on the iPhone (same Wi-Fi; allow the Windows firewall prompt), then Share → Add to Home Screen. HTTPS (tunnel or deploy) only when testing the compass or sharing a link.

### 6.8 Open items (defaults apply unless the founder overrides)

- Missing references: `01b-guide` (stop 1 open) and `02b-shop-sheet`: derive from `01c` and `02a`.
- Tab label **Companion** vs **Home**: default Companion.
- Real Luna (LangGraph) stays behind `LUNA.understand`; no keys in the web app.
- Out of scope here: backend, Arabic RTL, dark mode, real arrival-side maps and image licensing (retouch list in `redesign.md`).
