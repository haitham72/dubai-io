# Dubai-io — Plan

**Updated:** 9 Oct 2026 · **Stage:** Sketch (Phase 0) · **Owner:** Haitham
This is the single plan. Scope, demo and phases live here, and nowhere else. Decisions go in `docs/DECISIONS.md`.

---

## 1. What we're building

> A personal AI companion for Dubai that greets you when you land, walks you through the airport, remembers what matters, and opens local services as mini-apps right inside the chat, with real merchants answering real requests.

Contest: Create AI Agents Championship, category **Best Personal AI Agent** (rules, deadline and IP terms still to verify, see Phase 0).

## 2. Scope

### IN for the contest build

| # | Capability | Pillar |
|---|---|---|
| 1 | Persistent chat (history and cards survive reload, streaming) | Companion |
| 2 | Proactive messages from deterministic triggers (flight landed, merchant replied, reminders), deduplicated | Companion |
| 3 | Memory the user gives: hotel area, belt number, taxi number; recalled later | Companion |
| 4 | **DXB arrival guide:** step-by-step, user-confirmed, landmark "I'm lost", map with a terminal pin | Visitor |
| 5 | Ride comparison: taxi vs Metro (estimates, handoff only) | Visitor |
| 6 | **Aggregator → per-merchant HTML mini-apps** (sandboxed, scoped bridge) | Services |
| 7 | Real merchant loop: approval → inbox → ack → quote → user accepts → confirm | Services |
| 8 | Memory payoff: "I left my bag in the taxi" → recovery checklist + official handoff using saved details | Companion |
| 9 | Merchant onboarding: price-list photo → AI-generated mini-app → operator approves → live | Platform |

**If time runs out, cut in this order:** 9 → 8 → 5. Items 1, 2, 4, 6 and 7 are the floor.

### LATER (vision, not in the contest build)

Civic RAG with citations · resident mode flows (bills, vehicle, Salik/DEWA displays) · community · background geofencing · ticket wallet · payments · media memory · Arabic RTL UI (Arabic answers are fine) · native app.

### NEVER

Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · government transactions · copying the official DubaiNow look.

## 3. Demo arc (proposed, lock at the end of Phase 0)

| Time | Beat | Shows |
|---|---|---|
| 0:00–0:20 | Phone wakes: **"Hello, visitor."** Flight landed at DXB T3 | Proactive |
| 0:20–1:10 | Arrival guide: gate → passport → baggage (*"Belt 7: remembered"*) → customs → arrivals, map pin, "I'm lost" once | Guidance + memory |
| 1:10–1:40 | Taxi vs Metro, choose taxi, save taxi number, share trip with family (approval) | Consent |
| 1:40–2:40 | At the hotel: "Need anything?" → aggregator → three merchants, each its **own mini-app** → order → approval → merchant inbox on the split screen acks/quotes live → accept → confirmed | Mini-apps + real action |
| 2:40–3:15 | *"I left my bag in the taxi!"* The agent already knows the taxi number, time and route, and prepares the lost-property report and official contact | **Memory payoff** |
| 3:15–3:50 | Operator: a new shop's price-list photo → generated mini-app → live in search | Platform wow |
| 3:50–4:00 | Close line | — |

The "Under the hood" panel stays visible throughout. Open question for Phase 0: is pharmacy the right merchant category, or the unlisted long tail (laundry, tailor)?

## 4. Phases

Gates are binary. Dates are relative until the contest deadline is verified; then re-anchor.

### Phase 0 — Sketch ← *we are here* (now → ~19 Oct)

- [x] Clickable HTML demo (`demo/`), iOS light style, DXB placeholder maps
- [x] Docs consolidated (this structure)
- [ ] External review: run the LLM review prompt, plus show the demo to 5 people (visitors/residents)
- [ ] Decide: hero merchant category, final demo arc (§3)
- [ ] Verify contest rules: deadline, required artifacts (video? deck?), judging criteria, IP terms
- [ ] Start talking to 1 real merchant
- [ ] Replace placeholder airport maps (arrival side: immigration, baggage, arrivals hall)

**Gate 0:** demo arc locked · rules known with links · one merchant conversation started.

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
