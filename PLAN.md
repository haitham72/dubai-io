# Dubai-io — Plan

Current state: [docs/status.md](docs/status.md).

**Updated:** 22 Oct 2026 · **Owner:** Haitham · **Branches:** see `docs/status.md` · Runtime checkpoint: `handoff.md` · Review checklist: `docs/user-app-review-guide.md`
This is the single plan. Done work lives in git history; this file keeps locks, scope, the demo arc and what remains.

## Founder locks and decisions

- **Current verified navigation checkpoint:** Home cards -> complete inline task history -> attributed News now works; adaptive current-source cards/starter recommendations, flat Services, standard Ask chat history/profile, full-screen intro and left stacked dock are implemented. SQLite 175 passed/11 skipped; JS and both phone sizes/motion settings passed. Projects workspaces now group chats, tasks and explicit shared context; a synthetic live scope check passed without writing global facts. Real Decisions and scheduled checks remain required. This supersedes the older 154-test/next-Decisions checkpoint and all earlier Today-as-sheet instructions.

- **Latest 22 Oct navigation correction:** permanent adaptive Tasks home (live tasks, otherwise 3-5 usage/preference/recommendation starters) -> ordinary vertical task history -> personalized news. Services starts new tasks. Full-screen Wi-Fi/gradient intro stays. Ask uses standard chat history/Projects sidebar top left and profile top right; four tabs collapse **left** into a stacked icon and expand again, per Apple TV. This supersedes Today-as-modal, a fixed deck and the right/down-collapse interpretation. Projects group chats, tasks and shared context. Exact statuses and nested acceptance: newest section of `docs/implementation-plan.md`. Home/feed/chat/Projects and the local headline pilot are verified; check-backs and broader source/release gates remain pending.

- **22 Oct, clarification of full throttle:** finish the existing app and plan; this is not a redesign request. Preserve the approved Home/onboarding/palette/navigation. Add the missing behavior and connections within those surfaces; avoid a new visual concept or architecture rewrite.
- **Earlier DX-C checkpoint (historical):** DX-C source/report/order/task/chat connections and reviewed chat edits are implemented. SQLite 154 passed/11 skipped; both phone sizes/motion settings passed connected journeys, explicit before/after application and stale/retry protection. Two synthetic live Luna checks passed a task-date proposal and original taxi lost-item intent. No task suggestion/track operation sends a request or changes provider state. Next: genuine service decisions, then staged recovery/check-backs/Reading/connector/routines and preserved quality work. PG/device/hosting/OAuth adoption remain explicit gates; the app is not declared finished.
- **22 Oct, newest full-build authorization:** founder requested "do everything full throttle" after discussing incomplete adoption of the design references. This lifts the bounded pass's Keep-track/taxi/Reading/worker/Gmail holds for the web/backend assistant experience. Execute connected task/report/order/chat flow first, then actual decisions, staged recovery, durable consented check-backs, source-admitted pull-only Reading, one scoped connector and reviewed routines. Continue the preserved recommendation/context/release queue where dependencies permit. Implement and verify coherent slices, update nested status, commit/push/sync; do not treat a partial slice as the completed experience. Native remains parked for Mac/device testing. No purchasing, government execution, unapproved external sends, destructive database reset or paid hosting/budget is authorized by this direction. Physical-device/OAuth/provider dependencies must remain explicit.
- **No bidding, quotes or negotiation, ever** (10 Oct). Fixed published prices; every service row opens its own sandboxed modal HTML mini-app.
- **Temporal profile is core** (13 Oct): visible hypotheses with Confirm / Not true / Forget (`ARCHITECTURE.md` §7).
- **22 Oct, adaptive suggestions:** suggestions evolve with recent activity and repeated visits; they are never a constant feed or a permanent label inferred from one visit. Explicit current intent and constraints take priority. A single visit can influence this visit; inferred across-visit influence requires repeated, separated visits. Keep relevant variety, explain influence and let the user correct or pause learning. The temporal behavior contract and nested implementation gates are in `docs/references/recommender-plan.md` and `docs/implementation-plan.md`.
- **Cyan palette** with the approved purple fringe; C1 reflection on stage cards at 0.385 (13 Oct).
- **No shadows anywhere;** chat looks like ChatGPT/Claude: plain AI text, tinted user box, white rounded action boxes (19 Oct).
- **19 Oct:** one order path through the server engine · fine appeal removed · C6 (lost item) = prefilled report + official handoff + "not recovered" · Postgres + pgvector for the backend · Resident/VIP arc and photo onboarding out of the January submission (May-final candidates) · no new service cases before submission.
- **21 Oct:** founder authorized starting native Swift iOS on `ios-swift` after documenting and pushing the current web baseline. Founder has a Mac and iPhone 13 Pro Max. Supabase is the selected backend; local database integration and review-record import are now verified. Hosted deployment and production identity remain pending. Preserve the native in-app browser requirement, Wi-Fi/gradient onboarding and browse-to-chat transition. Other queued features remain in `docs/request-backlog.md`.

- **21 Oct, latest priorities:** native feature work is parked for Mac/iPhone testing; local Supabase is now running and the API uses it. Continue the moderate recommender, then selected-card context/draft plans, events/occasion suggestions, sponsored food discovery and remaining review fixes. Google OAuth is last for the single tester. These explicit requests authorize their read-only discovery/planning work; purchases, government execution and other NEVER items remain excluded.
- **22 Oct, branch/finalization instruction:** finish and commit the current work on `redesign`; native work remains parked. There is one repository/checkout. No iOS merge, branch switch or native implementation is part of this finalization.
- **22 Oct, product change superseding visitor-first scope:** the founder requested learning from OpenAI Dots, Grok Bot and Claude Duet and explicitly rejected a visitor-companion identity. DubaiIO is for everyday life and work in Dubai. The old visitor persona and hotel-concierge comparison no longer define the product. Feature selection and pilot prioritization are the active planning task; this does not authorize all proposed integrations or resume native work.
- **22 Oct, extended experience request:** plan a targeted Today/task UX redesign while preserving the approved visual identity. Add a swipe-up personalized briefing for relevant published news/newsletters, arts, media, regional topics, explicitly selected politics and source-verified UAE regulation updates. New topic/source/privacy contracts and gesture/accessibility states are planning requirements, not implemented features. Email newsletters are a later optional source; an external LLM review prompt was requested.
- **22 Oct, build authorization:** start building from the reconciled review on `redesign`; update plan and handoff. Gate A is persistent manual tasks + Today, followed by delayed check-back, one service vertical, optional briefing, one connector and one routine. No native work. The [review reconciliation](docs/references/assistant-review-decisions.md) records accepted changes, corrections, nested gates and preserved backlog. The [independent critique](docs/references/assistant-experience-review.md) is evidence/opinion, not an override of founder locks. Keep the everyday life/work promise, staged connectors and requested swipe/tap briefing; payments remain LATER and absent from this release.
- **22 Oct, latest Home/Today decision:** preserve Wi-Fi/gradient onboarding and the full photo/gradient Home carousel. Today opens from a dedicated handle by swipe-up, tap, Enter or ArrowUp; no bottom-edge/tab-bar gesture capture. Show saved owner-scoped counts, manual tasks On your list by due date, paused work and Dubai-time urgency flags. Reserve Needs you for real decisions, hide empty lanes; keep focus/announcements, inline Cancel confirmation and cached refresh. DX-14's hide-the-deck premise is superseded. **Keep-track bridge, taxi staged replies, Reading, cron/worker and Gmail are explicitly out of this pass.** Neither independent review report may be edited.
- **Durable execution detail:** [implementation plan](docs/implementation-plan.md), [direction](docs/references/personal-assistant-direction.md), [experience plan](docs/references/assistant-experience-plan.md), [review prompt](docs/references/assistant-plan-review-prompt.md). **Current checkpoint: bounded Home/Today/copy correction implemented and SQLite/browser verified; founder walkthrough/device acceptance and Supabase adoption remain.** REC-03C/04 and the earlier backlog remain preserved. Do not automatically start excluded work, reset data or silently replace the configured runtime.

**Latest review inputs:** [Claude design/interaction/use-case prompt](docs/references/assistant-design-interaction-review-prompt.md), all 12 [Duet reference frames](design/references/claude%20duet/README.md), and `docs/references/assistant-design-interaction-review.md`. Both reports are preserved unchanged. The [reconciliation](docs/references/assistant-review-decisions.md) records the founder's Home override, verified bounded fixes and remaining findings. Staged taxi/airport/RTA/driver replies first, Gmail later and freely licensed imagery remain queued requirements. No external contact, mailbox monitoring or delivery integration is claimed.

## 1. What we're building

> **DubaiIO helps keep your everyday life and work moving: it remembers the relevant context, prepares useful next steps and brings you decisions that need you.**

**Audience:** people whose everyday life and work take place in Dubai. First pilot cohort is open; an individual living/working in Dubai is the working proposal, not a confirmed restriction. Household and business/team variants require a deliberate choice. Visiting/arriving is a situation, not the default identity. **Product comparison:** general personal agents and fragmented manual workflows across communication, calendars and local services. The hotel concierge is no longer the primary comparison.

The proposed core is persistent responsibilities, a Today/decision view, inspectable context and controlled background follow-through. Connected communications, planning, adaptive discovery and merchant execution support those outcomes. Detailed features are proposals in the direction document, not claims of current functionality. Existing safeguards and completed source work remain valid.

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
| 10 | Everyday life/work audience; VIP features separate | Visitor-first framing superseded 22 Oct; new assistant features are proposed, not built. VIP-specific features remain deferred. |
| 11 | Service cases from `docs/services/cases.md` | ⏸ frozen until after submission |
| 12 | Temporal profile, visible hypotheses, "Because…" | ✅ |
| 13 | Services surface (registry, list, sheets) | ✅ (live Places and Google 2D map with pins; separate 3D demo) |
| 15 | Manual tasks + Today | Manual slice plus preserved visual Home/swipe-up Today implemented. SQLite 145 passed/11 skipped (17 task checks); 390x844 and 428x926 normal/reduced-motion keyboard/gesture-scope/no-shadow browser checks passed. Physical iPhone/screen-reader and PostgreSQL adoption unverified; no worker/connector implied. |
| 14 | Native iOS client | First slice on `ios-swift`, parked; no feature parity/device acceptance or resumed native work |

### IN since 23 Oct (founder)

Demo-grade **community**: Chat (groups, community threads, contacts with an in-app call log), Feed (communities, posts, comments, stories). Seeded people and posts are labelled Demo; real multi-user accounts arrive with Supabase Auth. Payment history means Dubai-io's own fixed-price orders and receipts only ("No payment taken"); bills remain LATER, and the DubaiNow look remains NEVER.

### LATER

Civic RAG with citations · resident bills and Salik/DEWA displays · background geofencing · ticket wallet · **payments and third-party purchasing** · media memory · Arabic RTL UI · live AR try-on · affiliate marketplace feeds. A broader audience does not automatically activate these features. Native remains parked (§6). Everyday resident life/work is the product direction, separate from these deferred capabilities.

### NEVER

Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · government transactions (fines display-only) · copying the official DubaiNow look · bidding / quote / price negotiation in any form.

## 3. Existing demo arc (historical visitor scenario)

This working scenario is preserved as implementation evidence, not the new product definition or selected future pitch. The 22 Oct direction calls for an ordinary life/work demonstration; audience, two useful recurring jobs and the revised script are still to be selected. Keep Wi-Fi/gradients available without forcing an airport story on every user.

Historical script: one visitor, late-night DXB arrival → laundry with a deadline → taxi-memory payoff. Start at `#demo.wifi` ("Scripted demo" label); merchant + operator on a second device at `/merchant.html`.

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
| D16 | First user | Visitor-first ruling superseded 22 Oct. First everyday life/work pilot cohort and two responsibilities are open decisions. |
| D17 | Stage format | Live app walkthrough (§3) with fallback video |
| D18 | Commercial model | Earlier assumption: merchant commission on fixed services, affiliates auxiliary. Reassess against the new assistant pilot; no replacement pricing/model is approved. |

## 4. Remaining, in execution order

The detailed, nested task breakdown and acceptance gates are in [docs/implementation-plan.md](docs/implementation-plan.md). Completed work and requests remain traceable in `docs/request-backlog.md`.

**Reordering authorized 22 Oct:** first review the [personal assistant feature proposal](docs/references/personal-assistant-direction.md), choose the pilot responsibilities and convert the selected slices into an implementation sequence. Recommended foundation: responsibilities + Today + inspectable context, then one useful connected/planning/service loop, then routines and optional additional channels. This is a proposal; the unfinished implementation tasks below are preserved, not automatically the next execution order. Database write health/ownership remain necessary implementation gates. Native stays parked.

1. **Preserved - moderate recommender:** REC-01/02 are implemented. REC-03A/B add separated-visit qualification, signed influence, trusted live-place retrieval/filtering, stable ordering, variety, visible reasons and item hiding. Verified on SQLite and in controlled browser scenarios; local Supabase test writes stalled on 22 Oct, so PostgreSQL validation/reconciliation is outstanding. REC-03C trusted services/products and verified completions and REC-04 measurement/retention remain pending dependencies of the revised product. Do not call the entire proposed recommender complete.
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
