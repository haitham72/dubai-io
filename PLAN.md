# Dubai-io — Plan

**Updated:** 10 Oct 2026 · **Status:** 🔒 **Plan v1.1: LOCKED. Planning is closed.** Next step: Phase 1 build · **Owner:** Haitham
This is the single plan. Scope, demo and phases live here, and nowhere else. Decisions go in `docs/DECISIONS.md`.
**Founder lock (10 Oct, final): bidding/quote is ABSOLUTELY REJECTED. Every service opens as a modal HTML mini-app (services / shops / stores / rides) with published fixed prices.**

> **🔒 Planning lock rules (10 Oct 2026).** §§1–3 don't change during the build. No new reviews, research runs, personas, beats or planning docs. A scope change needs (1) the founder to say so explicitly, (2) one row in `docs/DECISIONS.md`, and (3) something cut from §2 of equal size. New ideas go in `docs/VISION.md` → *Parked ideas* and are not discussed until after submission. The only planning work still allowed is ticking checkboxes and re-anchoring dates in §4.

---

## 1. What we're building

> **Dubai-io remembers your situation and follows through with local merchants, with you approving what gets shared.**

The companion is the product. Mini-apps are how it works with merchants. Photo onboarding is how more merchants join. Airport arrival is the introduction, not the product.

**Story:** short-stay business visitor → late-night DXB arrival → independent laundry with a deadline → taxi-memory payoff. Reported evidence per beat is in `docs/VISITORS.md §0`: strongest for lost items in taxis, weakest for the laundry deadline. Still open: why not the hotel concierge?

Contest: Create AI Agents Championship, category **Best Personal AI Agent** (§4.0 has the verified dates).

## 2. Scope

### IN for the contest build

| # | Capability | Pillar |
|---|---|---|
| 1 | Persistent chat (history and cards survive reload, streaming) | Companion |
| 2 | Proactive messages from deterministic triggers (flight landed, merchant replied, reminders), deduplicated | Companion |
| 3 | Memory the user gives (hotel area; taxi plate or receipt photo, roof colour, route, start time), recalled later without asking again | Companion |
| 4 | **DXB arrival guide:** step-by-step, user-confirmed, landmark "I'm lost", map with a terminal pin | Visitor |
| 5 | Ride recommendation that **reasons from time and terminal** (e.g. after the weekday Metro close or at T2 → no Metro → taxi; Friday service runs later, so the rule reads day + time from the verified schedule), with the alternative shown (estimates, handoff only) | Visitor |
| 6 | **Talabat-normal discovery → modal HTML mini-apps** (sandboxed, scoped bridge). List sorted closest + ★ rating + price-from + turnaround. Tap any row → its **own modal HTML mini-app** (services / shops / stores / rides). Fixed published prices only — **no bidding, no quote, no negotiation** | Services |
| 7 | Merchant loop with **deadline awareness** (fixed order, NO quote): approval → merchant accepts at published price → companion checks ready-time against user's deadline, flags conflict, asks for earlier slot → merchant confirms ready-time | Services |
| 8 | Memory payoff: "I left my bag in the taxi" → report pre-filled with RTA's fields (time, pickup/drop-off, roof colour, plate, receipt photo) from saved trip details, asks only for what's missing, hands off to the official channels (call centre / chat agent / app), stays "not recovered" | Companion |
| 9 | Merchant onboarding: price-list photo → AI-generated mini-app → operator approves → live | Platform |

**If time runs out, cut in this order:** 9 → 5 → 4. Items 1, 2, 3, 6, 7 and 8 are the floor: memory + follow-through *is* the product.

### LATER (vision, not in the contest build)

Civic RAG with citations · resident mode flows (bills, vehicle, Salik/DEWA displays) · community · background geofencing · ticket wallet · payments · media memory · Arabic RTL UI (Arabic answers are fine) · native app.

### NEVER

Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · government transactions · copying the official DubaiNow look · **bidding / quote / price negotiation in any form (`quote.request`, `QUOTED`, `QUOTE_ACCEPTED`)**.

## 3. Demo arc (v2, final)

One visitor, one continuous story: **an independent laundry with a deadline** (shirt pressed by 09:00 for tomorrow's meeting). Family sharing and belt recall are off the main path.

| Time | On screen | Presenter says |
|---|---|---|
| 0:00–0:12 | Arrival greeting, "Scripted demo" label, one button: *Guide me to arrivals* | "Dubai-io is a personal companion that remembers your situation and follows through with local merchants." |
| 0:12–0:35 | Compact airport guide. "I'm lost" → a landmark choice changes where the guide resumes | "It guides me from where I confirm I am, and resumes from what I can see." |
| 0:35–0:55 | It's 00:40 on a **weekday** (not Friday night), so the Metro has stopped: it recommends a taxi *with that reason*. Plate (or receipt photo), roof colour, route and start time saved, labelled "You told me" | "It knows the Metro has stopped, so it suggests a taxi, and saves what I'll need if something goes wrong." |
| 0:55–1:10 | "I've reached my hotel." User: *"I need a shirt pressed by 9 tomorrow."* | "My hotel area carries into the request." |
| 1:10–1:30 | Three laundries as Talabat-normal list (closest + ★ + price-from + turnaround), each row opens its **own modal HTML mini-app** | "Separate merchant experiences, same conversation." |
| 1:30–1:55 | Cyan host approval: named shop, fixed items + fixed total, hotel area, deadline. Pauses visibly | "The shop's mini-app can only ask. Dubai-io shows what's shared and waits for me." |
| 1:55–2:45 | Merchant inbox expands. **Accepted at fixed price** → ready-time **10:00** → companion flags "misses your 09:00 deadline" → asks for earlier → **08:30** → merchant confirms (price unchanged) | "Ten o'clock misses my deadline. It catches that, asks for earlier, and says confirmed only when the shop confirms." |
| 2:45–3:05 | Price-list photo → generated mini-app → owner review → appears in results | "Another shop joins from a photo, reviewed before it goes live." |
| 3:05–3:40 | **"I left my bag in the taxi!"** Report pre-filled with the fields RTA asks for, asks only for the bag description, official handoff, "not recovered" | "Over a hundred thousand lost items were reported in Dubai taxis last year. It already has the details the report needs." |
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

Gates are binary.

### 4.0 Contest facts (checked on the official page, 10 Oct 2026)

Source: [dubaichamberdigital.com/en/create-ai-agents](https://www.dubaichamberdigital.com/en/create-ai-agents)

| Fact | Official page says | What we do |
|---|---|---|
| Registration | Opened 7 Oct 2026. Closes "January 2027" on the timeline, but **"December 2026" in the FAQ** (the page contradicts itself) | **Register by 30 Nov 2026** |
| Submission | Prototype + pitch deck + demo video, "January 2027" (no exact day) | **Internal deadline: 31 Dec 2026** |
| Semi-final | 24 teams announced Jan 2027 (FAQ says Feb) · pitch day Mar 2027 · 12 finalists Mar 2027 | Phase 6 |
| Grand final | First week of May 2027, live on stage. **"A fully functional AI agent — not an MVP"** | Phase 6 hardens the build for live use |
| Judging | No rubric. "Validate" step: *demonstrate customer need, business potential and measurable impact* | Visitor interviews move from optional to Phase 5 |
| Eligibility | Idea/prototype/early MVP, not commercialised; ≤6 members; original, not copied from an existing repo; must protect personal data | No forks of existing agent repos |
| Prize | USD 150k per category winner; "AI Agent of the Year" gets more | — |
| IP terms | **Not stated.** The only Terms link is the site-wide Dubai Chambers footer, not contest rules | Ask the organisers by email before submitting |

Phase dates below are anchored to the 31 Dec internal deadline.

### Phase 0 — Sketch ✅ *complete*

- [x] Clickable HTML demo (`demo/`), iOS light style, DXB placeholder maps
- [x] Docs consolidated (this structure)
- [x] Two external LLM review rounds merged (`docs/DECISIONS.md`)
- [x] Hero: short-stay business visitor → independent laundry deadline → taxi-memory payoff
- [x] Desk research on reported visitor problems (`docs/VISITORS.md §0`)
- [x] Demo arc v2 locked (§3)

**Carried into Phase 1 (non-blocking):**
- [x] Deep research run (10 Oct) and closed: results in `docs/research/`, no re-runs
- [x] Contest rules checked on the official page (§4.0). IP terms not published: email organisers
- [x] Planning locked (10 Oct): reviews archived to `archive/reviews/2026-10-10/`

**Carried into Phase 1 (first week, build work, not planning):**
- [ ] Register for the championship (before 30 Nov 2026)
- [x] Patch the sketch to arc v2 in one pass (10 Oct, verified end to end in headless Chrome): three laundries (list → modal mini-app), fixed-price order with the 10:00 → 08:30 ready-time conflict, time+terminal ride reasoning, RTA fields in the lost-item report, cyan approval, no Civic tab, compact backstage, "Scripted demo" label, all bridge kinds → `order.request`, `merchant_reported` → `merchant_submitted`, no `+7`, no invented defaults for blank inputs
- [ ] Replace placeholder maps with arrival-side maps

### Phase 1 — Skeleton (13–26 Oct)

Monorepo scaffold (`apps/web`, `apps/api`, `apps/widgets`, `packages/contracts`), Postgres, contracts + codegen, auth with demo users, chat persistence + SSE, card renderer, one LLM turn with a read-only tool.
**Gate 1:** chat → typed card from a tool · reload restores everything · invalid card falls back to text.

### Phase 2 — Arrival companion (27 Oct – 9 Nov)

Arrival guide as cards, landmark matching, memory store, ride comparison, trigger/outbox pipeline with dedupe, demo-trigger endpoint.
**Gate 2:** a trigger fired twice → one message · the journey survives reload mid-way · saved memory is recalled by free text · 00:40 weekday or T2 → Metro disabled with a reason, Friday 00:40 at T3 → Metro offered (tests).

### Phase 3 — Mini-apps + merchant loop (10–30 Nov)

Registry and manifests, widget origin + sandbox + bridge (`order.request` only — `quote.*` forbidden), approval cards (single approval), fixed-order state machine with idempotency, merchant inbox with live updates.
**Gate 3:** merchant action → user chat in < 1 s · out-of-scope bridge call blocked (test) · double-tap approve = one order (idempotency) · accept/decline/cancel paths work. No quote path exists to test.

### Phase 4 — Payoff + platform (1–14 Dec)

Lost-item recovery using memory (checklist + official handoff, nothing "filed"). Photo → extracted catalog → generated mini-app → operator approval.
**Gate 4:** a new merchant goes live without code changes · the recovery flow uses only saved, user-given facts.

### Phase 5 — Polish + submit (15–31 Dec)

Rehearse 10×, record the demo video, deck, deploy, visitor interviews + one laundry owner (`docs/VISITORS.md §5`, the evidence for "customer need"), honest metrics ("27/30").
**Gate 5:** 10 clean runs ≤ 4:00 · demo video recorded · prototype + deck + video submitted by 31 Dec.

### Phase 6 — Semi-final → final (Jan–May 2027, only if selected)

Harden the same scope for live use: real merchant, real deployment, error paths. **No new scope:** "fully functional" means the §2 floor works live, not more features.
**Gate 6:** the full §3 arc runs live on the deployed app with one real merchant.

## 5. Not code, but critical

| Track | Needed by | Fallback |
|---|---|---|
| Registration | 30 Nov 2026 | — |
| IP terms (not published) | Before submitting | Ask organisers by email |
| 1 real merchant willing to answer on stage/video | Phase 3 | Clearly labelled sandbox merchant |
| Real arrival-side airport maps or a redrawn schematic | Phase 2 | Generic step schematic (already in demo) |
| Hosting + domain | Phase 5 | Local + tunnel |
