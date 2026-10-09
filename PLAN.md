# Dubai-io — Plan

**Updated:** 9 Oct 2026 · **Status:** **Plan v1.0, final.** Build starts when the founder asks · **Owner:** Haitham
This is the single plan. Scope, demo and phases live here, and nowhere else. Decisions go in `docs/DECISIONS.md`.

---

## 1. What we're building

> **Dubai-io remembers your situation and follows through with local merchants, with you approving what gets shared.**

The companion is the product. Mini-apps are how it works with merchants. Photo onboarding is how more merchants join. Airport arrival is the introduction, not the product.

**Story:** short-stay business visitor → late-night DXB arrival → independent laundry with a deadline → taxi-memory payoff. Reported evidence per beat is in `docs/VISITORS.md §0`: strongest for lost items in taxis, weakest for the laundry deadline. Still open: why not the hotel concierge?

Contest: Create AI Agents Championship, category **Best Personal AI Agent** (rules, deadline and IP terms still to verify; carried into Phase 1).

## 2. Scope

### IN for the contest build

| # | Capability | Pillar |
|---|---|---|
| 1 | Persistent chat (history and cards survive reload, streaming) | Companion |
| 2 | Proactive messages from deterministic triggers (flight landed, merchant replied, reminders), deduplicated | Companion |
| 3 | Memory the user gives (hotel area; taxi plate or receipt photo, roof colour, route, start time), recalled later without asking again | Companion |
| 4 | **DXB arrival guide:** step-by-step, user-confirmed, landmark "I'm lost", map with a terminal pin | Visitor |
| 5 | Ride recommendation that **reasons from time and terminal** (e.g. after midnight or at T2 → no Metro → taxi), with the alternative shown (estimates, handoff only) | Visitor |
| 6 | **Aggregator → per-merchant HTML mini-apps** (sandboxed, scoped bridge) | Services |
| 7 | Merchant loop with **deadline awareness**: approval → ack → quote → companion checks the quote against the user's deadline, flags a conflict, asks for an earlier slot → accept → confirm | Services |
| 8 | Memory payoff: "I left my bag in the taxi" → report pre-filled with RTA's fields (time, pickup/drop-off, roof colour, plate, receipt photo) from saved trip details, asks only for what's missing, hands off to the official channels (call centre / chat agent / app), stays "not recovered" | Companion |
| 9 | Merchant onboarding: price-list photo → AI-generated mini-app → operator approves → live | Platform |

**If time runs out, cut in this order:** 9 → 5 → 4. Items 1, 2, 3, 6, 7 and 8 are the floor: memory + follow-through *is* the product.

### LATER (vision, not in the contest build)

Civic RAG with citations · resident mode flows (bills, vehicle, Salik/DEWA displays) · community · background geofencing · ticket wallet · payments · media memory · Arabic RTL UI (Arabic answers are fine) · native app.

### NEVER

Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · government transactions · copying the official DubaiNow look.

## 3. Demo arc (v2, final)

One visitor, one continuous story: **an independent laundry with a deadline** (shirt pressed by 09:00 for tomorrow's meeting). Family sharing and belt recall are off the main path.

| Time | On screen | Presenter says |
|---|---|---|
| 0:00–0:12 | Arrival greeting, "Scripted demo" label, one button: *Guide me to arrivals* | "Dubai-io is a personal companion that remembers your situation and follows through with local merchants." |
| 0:12–0:35 | Compact airport guide. "I'm lost" → a landmark choice changes where the guide resumes | "It guides me from where I confirm I am, and resumes from what I can see." |
| 0:35–0:55 | It's 00:40, so the Metro has stopped: it recommends a taxi *with that reason*. Plate (or receipt photo), roof colour, route and start time saved, labelled "You told me" | "It knows the Metro has stopped, so it suggests a taxi, and saves what I'll need if something goes wrong." |
| 0:55–1:10 | "I've reached my hotel." User: *"I need a shirt pressed by 9 tomorrow."* | "My hotel area carries into the request." |
| 1:10–1:30 | Three laundries, two distinct mini-app previews, pick one | "Separate merchant experiences, same conversation." |
| 1:30–1:55 | Cyan host approval: named shop, shirt count, hotel area, deadline. Pauses visibly | "The shop's mini-app can only ask. Dubai-io shows what's shared and waits for me." |
| 1:55–2:45 | Merchant inbox expands. Ack → quote **10:00** → companion flags "misses your 09:00 deadline" → asks for earlier → **08:30** → accept → merchant confirms | "Ten o'clock misses my deadline. It catches that, asks for earlier, and says confirmed only when the shop confirms." |
| 2:45–3:05 | Price-list photo → generated mini-app → owner review → appears in results | "Another shop joins from a photo, reviewed before it goes live." |
| 3:05–3:40 | **"I left my bag in the taxi!"** Report pre-filled with the fields RTA asks for, asks only for the bag description, official handoff, "not recovered" | "Over a hundred thousand items were left in Dubai taxis last year. It already has the details the report needs." |
| 3:40–4:00 | Report beside the earlier taxi-memory card | Close: *"Dubai-io remembers your situation and follows through locally, with you approving what gets shared."* |

**Under the hood** goes compact: large events only ("Trip details saved", "Sharing approved", "Merchant confirmed"), with the raw log available for questions. The merchant inbox is labelled "Merchant role, simulated" until a real merchant exists.

### Jury objections (prepared answers)

| Objection | Answer |
|---|---|
| What does this add to DubaiNow / Careem / talabat / ChatGPT? | Continuity: the same companion carries your context into a local merchant's reply, quote and confirmation, and you approve what leaves the chat. We don't claim they lack AI or memory |
| Where's the agency beyond buttons? | It holds the deadline, interprets a conflicting reply and proposes the next step |
| Why keep it after the airport? | Arrival is the introduction; repeat local requests reuse your preferences and history |
| Why would merchants join? | A reviewed mini-app from a photo, plus a structured inbox, is less work than WhatsApp back-and-forth. To be validated with shop owners |
| What have you proved? | The interaction is reviewable. User need, repeat use and merchant participation are what we test next |

## 4. Phases

Gates are binary. Dates are relative until the contest deadline is verified; then re-anchor.

### Phase 0 — Sketch ✅ *complete*

- [x] Clickable HTML demo (`demo/`), iOS light style, DXB placeholder maps
- [x] Docs consolidated (this structure)
- [x] Two external LLM review rounds merged (`docs/DECISIONS.md`)
- [x] Hero: short-stay business visitor → independent laundry deadline → taxi-memory payoff
- [x] Desk research on reported visitor problems (`docs/VISITORS.md §0`)
- [x] Demo arc v2 locked (§3)

**Carried into Phase 1 (non-blocking):**
- [ ] ⏳ **Run `docs/research/research-prompt.md` in Gemini Deep Research / DeepSeek** and save the results in `docs/research/`. It fills the evidence gaps (laundry deadline, hotel concierge, competitors, contest rules)
- [ ] Verify contest rules: deadline, artifacts, judging criteria, IP terms (re-anchor phase dates)
- [ ] Update the sketch to arc v2: deadline-conflict branch, time-aware ride reasoning, RTA fields in the lost-item report, cyan host strip, remove Civic tab, compact backstage, "Scripted demo" label
- [ ] Replace placeholder maps with arrival-side maps
- [ ] Optional validation: visitor interviews and laundry tabletop (`docs/VISITORS.md §5`)

### Phase 1 — Skeleton (~2 weeks)

Monorepo scaffold (`apps/web`, `apps/api`, `apps/widgets`, `packages/contracts`), Postgres, contracts + codegen, auth with demo users, chat persistence + SSE, card renderer, one LLM turn with a read-only tool.
**Gate 1:** chat → typed card from a tool · reload restores everything · invalid card falls back to text.

### Phase 2 — Arrival companion (~2 weeks)

Arrival guide as cards, landmark matching, memory store, ride comparison, trigger/outbox pipeline with dedupe, demo-trigger endpoint.
**Gate 2:** a trigger fired twice → one message · the journey survives reload mid-way · saved memory is recalled by free text.

### Phase 3 — Mini-apps + merchant loop (~3 weeks)

Registry and manifests, widget origin + sandbox + bridge, approval cards, request state machine with idempotency, merchant inbox with live updates.
**Gate 3:** merchant action → user chat in < 1 s · out-of-scope bridge call blocked (test) · double approve = one request · decline/cancel paths work.

### Phase 4 — Payoff + platform (~2 weeks)

Lost-item recovery using memory (checklist + official handoff, nothing "filed"). Photo → extracted catalog → generated mini-app → operator approval.
**Gate 4:** a new merchant goes live without code changes · the recovery flow uses only saved, user-given facts.

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
