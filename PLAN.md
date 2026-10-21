# Dubai-io — Plan

**Updated:** 21 Oct 2026 · **Owner:** Haitham · **Branches:** `redesign` (web baseline), `ios-swift` (native work) · Status of record: `handoff.md` · Review checklist: `docs/user-app-review-guide.md`
This is the single plan. Done work lives in git history; this file keeps locks, scope, the demo arc and what remains.

## Founder locks and decisions

- **No bidding, quotes or negotiation, ever** (10 Oct). Fixed published prices; every service row opens its own sandboxed modal HTML mini-app.
- **Temporal profile is core** (13 Oct): visible hypotheses with Confirm / Not true / Forget (`ARCHITECTURE.md` §7).
- **Cyan palette** with the approved purple fringe; C1 reflection on stage cards at 0.385 (13 Oct).
- **No shadows anywhere;** chat looks like ChatGPT/Claude: plain AI text, tinted user box, white rounded action boxes (19 Oct).
- **19 Oct:** one order path through the server engine · fine appeal removed · C6 (lost item) = prefilled report + official handoff + "not recovered" · Postgres + pgvector for the backend · Resident/VIP arc and photo onboarding out of the January submission (May-final candidates) · no new service cases before submission.
- **21 Oct:** founder authorized starting native Swift iOS on `ios-swift` after documenting and pushing the current web baseline. Founder has a Mac and iPhone 13 Pro Max. Supabase is the selected backend; local database integration and review-record import are now verified. Hosted deployment and production identity remain pending. Preserve the native in-app browser requirement, Wi-Fi/gradient onboarding and browse-to-chat transition. Other queued features remain in `docs/request-backlog.md`.

- **21 Oct, latest priorities:** native feature work is parked for Mac/iPhone testing; local Supabase is now running and the API uses it. Continue the moderate recommender, then selected-card context/draft plans, events/occasion suggestions, sponsored food discovery and remaining review fixes. Google OAuth is last for the single tester. These explicit requests authorize their read-only discovery/planning work; purchases, government execution and other NEVER items remain excluded.
- **Durable execution detail:** [docs/implementation-plan.md](docs/implementation-plan.md) contains nested tasks, dependencies, implemented-versus-pending status and acceptance gates. It is subordinate to this plan. **Next task: REC-03 (trusted candidate eligibility and wider recommendation surfaces).**

## 1. What we're building

> **Dubai-io remembers your situation and follows through with local merchants, with you approving what gets shared.**

**Persona:** short-stay business visitor (visitor/resident is a user setting, never detected). **Main competitor:** the hotel concierge.

**Evidence and pitch guardrails** (desk research 9 Oct + Deepseek deep research; full text in git, `main:docs/VISITORS.md`, `main:docs/research/`):
- **Lost item in a taxi:** strongest beat (official data) — 104,000+ items lost in Dubai taxis in 2025 (incl. ~3,000 passports); recovery depends on exactly what the companion remembers (time, pickup/drop-off, roof colour, plate, receipt).
- **Late-night arrival:** real constraint — the Metro stops around midnight and T2 has no station; the ride recommendation reasons from it.
- **Laundry deadline / concierge:** *reported* in forums and reviews (unverified LLM research): hotel laundry ~AED 35–50 per shirt, 2–3 day waits; concierges outsource with ~10 h minimum turnaround and no requests after 11 PM. Pitch as "reported by travellers", not as a measured pain, until sources are checked.
- Say "it coordinates and follows through with your permission"; never "we replace Google/Careem/DubaiNow" or claim live government/partner integrations. Strong post-contest candidate: car-rental deposit disputes (#1 tourist complaint).

Contest: Create AI Agents Championship, **Best Personal AI Agent**. Portal (checked 19 Oct): submission **January 2027** (day not stated: prototype + pitch deck + demo video); Grand Final **first week of May 2027**; global eligibility; no published rubric; IP terms not stated.

## 2. Scope

### IN (contest build)

| # | Capability | State |
|---|---|---|
| 1 | Persistent chat (history and cards survive reload) | ✅ |
| 2 | Proactive messages from deterministic triggers, deduplicated | ✅ (reminders + Demo triggers; real flight feed needs a key) |
| 3 | Memory the user gives, recalled later | ✅ |
| 4 | DXB arrival guide, user-confirmed, "I'm lost" | ✅ (reference-image parity pending) |
| 5 | Ride recommendation reasoning from time and terminal | ✅ (live Google ETA) |
| 6 | Talabat-normal list → sandboxed modal mini-apps, fixed prices | ✅ |
| 7 | Merchant loop with deadline awareness (no quote) | ✅ |
| 8 | Lost-item payoff from saved trip details, official handoff | ✅ |
| 9 | Merchant onboarding from a price-list photo | ⏸ out of the January cut |
| 10 | Resident/VIP arc | ⏸ LATER for January |
| 11 | Service cases from `docs/services/cases.md` | ⏸ frozen until after submission |
| 12 | Temporal profile, visible hypotheses, "Because…" | ✅ |
| 13 | Services surface (registry, list, sheets) | ✅ (live Places and Google 2D map with pins; separate 3D demo) |
| 14 | Native iOS client | Authorized 21 Oct; first slice on `ios-swift`, not feature parity or device acceptance |

### LATER

Civic RAG with citations · resident bills and Salik/DEWA displays · community · background geofencing · ticket wallet · **payments and third-party purchasing** · media memory · Arabic RTL UI · live AR try-on · affiliate marketplace feeds. Native iOS moved to active work on 21 Oct (§6).

### NEVER

Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · government transactions (fines display-only) · copying the official DubaiNow look · bidding / quote / price negotiation in any form.

## 3. Demo arc (4:00)

One visitor: late-night DXB arrival → laundry with a deadline → taxi-memory payoff. Start the phone at `#demo.wifi` (shows the "Scripted demo" label); merchant + operator on a second device at `/merchant.html`.

| Time | On screen | Presenter says |
|---|---|---|
| 0:00–0:12 | Arrival, "Scripted demo" label, *Guide me to arrivals* | "A personal companion that remembers your situation and follows through with local merchants." |
| 0:12–0:35 | Guide; "I'm lost" resumes from a landmark | "It guides me from where I confirm I am." |
| 0:35–0:55 | 00:40 → Metro stopped → taxi, live Google ETA; plate, roof, hotel area saved as "You told me" | "It knows the Metro has stopped, and saves what I'll need if something goes wrong." |
| 0:55–1:10 | "I need a shirt pressed by 9 tomorrow." | "My hotel area carries into the request." |
| 1:10–1:30 | Laundries closest + ★ + price + turnaround; each opens its own mini-app | "Separate merchant experiences, same conversation." |
| 1:30–1:55 | One approval: shop, fixed items + total, area, deadline | "The mini-app can only ask. Dubai-io shows what's shared and waits for me." |
| 1:55–2:45 | Merchant accepts at fixed price, ready 10:00 → "misses your 09:00" → ask for 08:30 → merchant confirms | "It catches the deadline and says confirmed only when the shop confirms." |
| 2:45–3:05 | "Remind me" → operator fires `fast forward reminders` → **Demo trigger** message | "It follows up on its own, only because I asked, and labels a staged trigger." |
| 3:05–3:40 | "I left my bag in the taxi!" → report prefilled from the saved trip, asks only for the bag | "It already has the details the report needs." |
| 3:40–4:00 | Report beside the taxi-memory card | "Remembers your situation, follows through locally, with you approving what gets shared." |

**Jury answers:** *Ask Maps / ChatGPT?* They answer; Dubai-io follows through: a fixed-price order, your approval of what is shared, merchant-confirmed status, a profile you can see and forget. *Agency beyond buttons?* It holds the deadline, checks the shop's ready time and proposes the next step. *Is the merchant real?* A sandbox operator; the engine, approval binding and evidence gate are the production path. *What have you proved?* The interaction is reviewable; user need and merchant participation are next.

**Product decisions (D01–D18, ruled 19 Oct):**

| # | Decision | Ruling |
|---|---|---|
| D01 | Agentic proof | Real request → sandbox merchant inbox → merchant tap updates chat (built) |
| D02 | Voice | Push-to-talk only, transcript visible, typed fallback (optional) |
| D03 | No merchant API | Partner mini-app → Dubai-io inbox; others are deep-link handoffs |
| D04 | Proactivity on stage | User reminder + labelled Demo trigger; real order updates (built) |
| D05 | Fine appeal | Removed |
| D06 | Third-party web sessions | Link + handoff; never inject user credentials |
| D07 | Google budget | Places + Routes (live); no Gemini grounding |
| D08 | Native cards vs mini-apps | Mini-app per row (lock); native card only as fallback |
| D09 | Launch promise | Discovery + one tested merchant vertical (laundry) |
| D10 | Memory retention | Typed, visible facts with Forget; no transcript mining |
| D11 | Human recovery desk | LATER; at most a status line |
| D12 | Community events | LATER |
| D13 | Discounts | Merchant-published fixed offers only |
| D14 | Merchant growth | Inbound opt-in; **AI cold-calling / bulk WhatsApp on HOLD** (UAE Cabinet Res. 56–57/2024; counsel sign-off required) |
| D15 | "Do the rest" autonomy | One explicit approval per side effect |
| D16 | First user | Arriving visitor for the pitch; real pilot chosen by merchant access |
| D17 | Stage format | Live app walkthrough (§3) with fallback video |
| D18 | Commercial model | Merchant commission on fixed services first; affiliate links auxiliary |

## 4. Remaining, in execution order

The detailed, nested task breakdown and acceptance gates are in [docs/implementation-plan.md](docs/implementation-plan.md). Completed work and requests remain traceable in `docs/request-backlog.md`.

1. **ACTIVE - moderate recommender:** REC-01 is implemented on Supabase. REC-02 Edit/evidence controls, aggregate repetition caps, cache invalidation and timeline labels are implemented and verified. Next: REC-03 trusted candidate constraints, wider surfaces and variety/stability, followed by REC-04 measurements/retention. Do not call the entire proposed recommender complete.
2. **Assistant context and draft plans:** CTX-01 whole-place focus, bounded recent history and checkpoint forgetting are implemented. Finish CTX-02 selected fragments, server entity/plan validation and ticket-availability guard; then PLAN-01 revision-bound itinerary proposals, locked constraints, explicit assumptions and reviewable before/after changes. No external booking/purchase is implied.
3. **Suggestions/events:** SUG-01 confirmed occasions and EVT-01 dated, sourced future events. Reuse configured search first; distinguish organizer verification from news and live ticket stock. Use existing consent/dedupe/quiet-hours rules for any notification.
4. **Sponsored food discovery:** ADS-01 relevant food context, clear Sponsored/Why labels, organic alternatives, caps/dismissal and separate eligible first-party evidence. Current observations are organic-only. Empty inventory means no sponsored card.
5. **Review/release:** REV-01 public proxy quotas and merchant login throttling/roles, REV-02 visual/device validation, REV-03 demo/provider access. Founder walkthrough, ten clean <=4-minute rehearsals and fallback video remain pending.
6. **Independent database follow-up:** DB-02 recover/export the original unhealthy Postgres without resetting its volume. Current Supabase contains imported SQLite review records, not the original Postgres data. DB-03 hosted setup and production identity require deliberate configuration; Google OAuth is explicitly last.
7. **Native work PARKED:** first slice built on `ios-swift` with seven package tests and unsigned Simulator build passing; Mac/iPhone visual testing and substantial feature parity remain. See `handoff-ios.md`. No Windows Swift/Expo workaround is required.
8. **Submission package:** internal target Fri 18 Dec 2026 for deck, demo video, hosting/tunnel and small user test; submission January 2027. Try for one real merchant before the May final. Optional voice, real flight feed and Calendar remain credential/device-dependent work, not automatic blockers.

## 5. Not code, but critical

| Track | Needed by | Fallback |
|---|---|---|
| Archive a dated screenshot of the portal rules | before submission | — |
| One real merchant willing to answer on video | May final | Labelled sandbox merchant (current) |
| Hosting + domain | submission | Local + tunnel |
| Purchasing / payments decision | before any purchase feature | Deep-link handoff only |

## 6. Native iOS app (authorized, now parked for Mac testing)

A second client of the same `apps/api`. SwiftUI, iOS 26 Liquid Glass, no added shadows, with ShipSwift (`signerlabs/ShipSwift`, MIT) and Libraries.dev retained as references. Use platform components first; add dependencies only when justified. The founder has a Mac + iPhone. Current authoring environment is Windows without Swift/Xcode; compilation must be verified on a macOS runner or Mac. Detailed slices, browser policy and validation gates: `docs/references/ios-swift-plan.md`.

| Web today | Native |
|---|---|
| `/openapi.json` | Small typed URLSession client for initial endpoints; code generation can follow when contracts stabilize |
| Cookie sessions | Existing anonymous session for first read/chat slice; Supabase Auth/bearer identity and ownership migration before production |
| SSE streams | `URLSession` async bytes; APNs from the outbox when backgrounded |
| Order card | Live Activity + Dynamic Island, updated only by merchant events |
| Sandboxed mini-apps | `WKWebView`, non-persistent store, `WKContentRuleList` blocking network, `order.request`-only message handler |
| Luna | Same API; Speech framework push-to-talk; App Intents ("Is my shirt ready?") |
| Profile | Native view over `/api/profile/me` |
| Third-party links | Safari browsing sheet; dedicated authentication session for sign-in; custom WebKit only when needed |

When native work resumes, build order: typed API/session foundation + native onboarding/browse/chat/discovery/browser → production auth/roles and migration → approved mini-app/order/SSE parity → APNs/Live Activity → voice/App Intents. The first slice does not pretend to implement merchant execution or account migration. Full parity gate remains the §3 arc on the founder's iPhone with provider evidence and explicit approvals.
