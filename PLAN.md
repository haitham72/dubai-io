# Dubai-io — Plan

**Updated:** 21 Oct 2026 · **Owner:** Haitham · **Branches:** `redesign` (web baseline), `ios-swift` (native work) · Status of record: `handoff.md` · Review checklist: `docs/user-app-review-guide.md`
This is the single plan. Done work lives in git history; this file keeps locks, scope, the demo arc and what remains.

## Founder locks and decisions

- **No bidding, quotes or negotiation, ever** (10 Oct). Fixed published prices; every service row opens its own sandboxed modal HTML mini-app.
- **Temporal profile is core** (13 Oct): visible hypotheses with Confirm / Not true / Forget (`ARCHITECTURE.md` §7).
- **Cyan palette** with the approved purple fringe; C1 reflection on stage cards at 0.385 (13 Oct).
- **No shadows anywhere;** chat looks like ChatGPT/Claude: plain AI text, tinted user box, white rounded action boxes (19 Oct).
- **19 Oct:** one order path through the server engine · fine appeal removed · C6 (lost item) = prefilled report + official handoff + "not recovered" · Postgres + pgvector for the backend · Resident/VIP arc and photo onboarding out of the January submission (May-final candidates) · no new service cases before submission.
- **21 Oct:** founder authorized starting native Swift iOS on `ios-swift` after documenting and pushing the current web baseline. Founder has a Mac and iPhone 13 Pro Max. Supabase is the selected backend direction; migration remains pending. Preserve the native in-app browser requirement, Wi-Fi/gradient onboarding and browse-to-chat transition. Other queued features remain in `docs/request-backlog.md`.

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

## 4. Remaining

0. **Native iOS authorized:** snapshot/push web baseline, branch `ios-swift`, implement and compile the first slice. Detailed plan: `docs/references/ios-swift-plan.md`. Founder web review remains outstanding but no longer blocks starting native work.
1. **Founder review** with `docs/user-app-review-guide.md`; log notes in `handoff.md`. Current assessment: `docs/review-findings-2026-10-21.md`.
2. **Rehearsal:** 10 timed runs ≤ 4:00 on phone + second device; record the fallback video. Gate: 10 clean runs.
3. **Submission package** (target Fri 18 Dec 2026): deck, demo video, hosting (or tunnel), small user test.
4. **Reference-image parity:** chat surfaces done (`02-rows`, `03-approve-events`); remaining: `01-home` (Services top), `01c` guide, `04`/`04a` lost item, `05` Services/Me, `x-*`. Keep: no shadows, AI text unboxed unless dynamic output.
5. **Keys-dependent (optional):** real flight-landed trigger, interactive Google Maps JS upgrade, Calendar scopes/connector via OAuth (`docs/references/api-catalog.md`).
6. **Optional:** push-to-talk voice (transcript visible, typed fallback).
7. **Try for one real merchant** before the May final (§5).
8. **Founder access requests:** Amazon Associates (affiliate → Creators API); official portals (RTA, DEWA…) for API permission. Services get added where real data is blocked.

## 5. Not code, but critical

| Track | Needed by | Fallback |
|---|---|---|
| Archive a dated screenshot of the portal rules | before submission | — |
| One real merchant willing to answer on video | May final | Labelled sandbox merchant (current) |
| Hosting + domain | submission | Local + tunnel |
| Purchasing / payments decision | before any purchase feature | Deep-link handoff only |

## 6. Native iOS app (authorized 21 Oct)

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

Build order: typed API/session foundation + native onboarding/browse/chat/discovery/browser → production auth/roles and migration → approved mini-app/order/SSE parity → APNs/Live Activity → voice/App Intents. The first slice does not pretend to implement merchant execution or account migration. Full parity gate remains the §3 arc on the founder's iPhone with provider evidence and explicit approvals.
