# Sol independent review: Dubai-io contest scope and execution

**Reviewed:** 19 October 2026 · **Code baseline:** `678c083`, with the working-tree documents present during review.  
**Status:** Independent recommendation; this file does not amend the canonical plan or authorize implementation.

The strongest contest entry is the existing arrival → fixed-price laundry deadline → taxi-memory story, with one observable merchant execution loop. Keep the approved visual identity and modal mini-apps. Spend the engineering effort on proving that an approved request reaches a separate operator and that their response changes the conversation. Remove the fine-appeal ending from the contest cut.

The repository has useful working foundations, but it is not an end-to-end agent demonstration yet. In particular, the default entry disables Luna, the service mini-app path simulates merchant responses, and the durable action engine has no runtime provider adapters. These are more consequential than adding another cinematic scene.

## 1. Authority and scope reconciliation

The precedence is explicit: `CLAUDE.md` → `PLAN.md` → `ARCHITECTURE.md`; handoff and reviews describe or challenge these documents but cannot override them. The enhancement review itself says it is **NOT APPROVED FOR IMPLEMENTATION**. Its references to older numbered scope documents are stale in this monorepo.

| Issue | Canonical requirement | Enhancement proposal / downstream drift | Arbitration |
|---|---|---|---|
| Commercial interaction | `PLAN.md` §2 and founder lock prohibit quotes, bidding and price negotiation | Enhancement §§1.1, 4.4, 6.1, 10.4 and spike M retain quote language and `service.quote_updated` | Reject that language and those contracts. Use published items, fixed totals and availability/ready-time changes only. |
| Story and climax | `PLAN.md` §3 locks arrival, laundry deadline and taxi memory | Seven-day montage and a simulated government appeal approval; handoff §4 repeats the fine twist | Retain the canonical story. The handoff is inconsistent with its authority. |
| Government actions | Fines display-only; no government execution; civic RAG LATER | Fine drafting, Gmail watching, official case tracking and an eventual appeal outcome | Defer the whole workflow. A simulation label does not bring an out-of-scope feature into scope. |
| Provider UI | Every service row opens its own modal HTML mini-app; native fallback on failure | Enhancement D08 recommends native cards by default | Keep host cards plus sandboxed mini-apps. Gemini's §6 correction is right. |
| Platform breadth | One reusable service engine; selected cases | E-commerce L1–L5 pathways, website research, Docling and human case desks | Keep the integration-level vocabulary for claims; defer the additional systems. |
| Proactivity | Deterministic, consented, deduplicated messages; background geofencing LATER | Manual location simulation is acceptable, but proposed wallet/community scenes exceed scope | An operator trigger may demonstrate real notification logic with a visible `Demo trigger` label. No wallet or background-location claim. |
| Memory | Stated facts **and** persistent temporal profile are IN; items 12/13 are part of the floor | Narrow memory-only recommendations can be read as replacing the profiler | Do not silently remove the profiler. Resolve the implementation-order conflict below. |
| Acquisition | No requirement to build outbound growth automation | AI telemarketing is on HOLD in enhancement §8 | Preserve that hold; build no acquisition engine for the contest. This review does not independently certify the cited legal analysis. |

**Cut order:** use `PLAN.md` §2's existing order: extra cases (11), Resident/VIP (10), photo onboarding (9), ride recommendation (5), extended airport guide (4). These are permitted cuts if time runs out, not a declaration that all are now cancelled. Preserve the floor: durable conversation, deterministic updates, user memory, mini-apps, deadline-aware merchant follow-through, taxi-memory payoff, temporal profile and universal Services surface.

Defer human coordinator CRM, Docling/civic ingestion, Gmail/calendar watchers, shopping checkout/fulfillment gateways, arbitrary browser agents, community, tickets, native geofencing, payments and wake words. Retain the polished arrival/coverflow shell; compress its stage time. A React migration is not on the critical path: newer `PLAN.md` §7.1 explicitly puts the current HTML app first.

### A conflict inside the canon needs an explicit decision

`PLAN.md` §6.6 Step P and `ARCHITECTURE.md` §12.5 require the persistent profiler and its evaluation **before other backend features**. Gemini's merchant-first roadmap bypasses that gate. The profiler currently is not implemented, so that roadmap cannot be described as fully plan-compliant.

My recommendation is a **narrow sequencing amendment**: allow the merchant proof to be implemented first, retain the profiler as a completion gate, and leave its inference restrictions unchanged. This exposes the most important integration risk early without declaring the profile complete. This is a proposed founder decision, not an amendment made by this review. Without it, implement and pass Step P before the merchant backend sprint below. If the complete floor cannot fit the verified deadline, explicitly revise the floor; do not relabel fixture playback as a persistent profiler.

## 2. What the code actually proves

Evidence below refers to the reviewed working tree; function names remain useful if line numbers move.

| Area | Observed evidence | Consequence |
|---|---|---|
| Default entry | `apps/api/app/main.py:root` redirects `/` to `/index.html`; `apps/web/chat.js:18` enables Luna only for paths starting `/lab/` | The normal entry uses the labelled router, even with a configured model. Fix the gate and verify the real request in the browser. |
| Luna | `app/luna/schema.py:Understanding` returns allowlisted intent/slots; `graph.py:build` runs normalize → understand → validate → remember with `InMemorySaver` | This is real model understanding when enabled. It does not emit or execute an order. Host orchestration must turn validated intent and confirmed facts into a prepared action. |
| Action engine | `app/actions.py:ActionEngine.prepare/approve` binds snapshot hash/revision, deduplicates preparation/approval and requires adapter evidence | Reuse it. All runtime capabilities have `adapter=None`; complete drafts become `BLOCKED`. The seven service capabilities currently accept only request/area/provider, not structured order lines or deadlines. |
| Two service paths | `service-workflow.js:renderResult` uses the API and suppresses Send for blocked actions. `offers.js:approval` creates a random reference and adds acceptance/slot events after delays | The most visual order path bypasses the durable engine. Its later events are visibly simulated, but even the initial “Sent to merchant” is local. It cannot count as live dispatch. |
| Catalog and bridge | `offers.js:onBridge` checks frame source/version/kind; `p.items` uses host prices, but the other branch trusts widget-supplied price. `p.prices` is not used there | The comment promising host-owned prices is not true for every template. Payload validation, per-frame token, approved manifests, timeout fallback and separate-origin hosting remain gates. |
| Merchant lifecycle | No merchant inbox module/page or registered merchant adapter in the inspected source; engine stops at dispatch result | Accept/ready/decline commands, role isolation and subsequent authoritative events must be built. An adapter reference proves receipt, not acceptance or fulfillment. |
| Chat and updates | `session-state.js` saves browser snapshots; `chat.js` restores status as a paused plain-text demo timeline. No implemented SSE/outbox delivery path in the inspected modules | Same-browser continuity exists. Server replay of typed cards, durable pending approvals and cross-device updates are unfinished. |
| Profile | `app.js` calls `profileAt(EPISODES, HYPOTHESES, ...)`; `profile.js` evaluates synthetic timelines. Luna stores extracted stated facts in JSON | Neither is the persistent temporal profiler in architecture §12. Keep the fixture label visible. |
| Taxi recovery | `recovery-state.js:prepareReport` excludes non-user-supplied saved facts and returns `PREPARED_NOT_FILED`; `simulateTrace` returns separate fixtures | Report preparation is useful, tested behavior. A simulated driver match is not recovery evidence. Backend `recovery.rta` remains blocked. |
| Google | Places/Routes proxies exist in `google_maps.py`; map uses MapLibre/OSM and local place fixtures | Endpoints are not proof of live discovery in the UI. A fixture tagged `why: 'google'` is not a live Google result. |
| OAuth and isolation | Prepared OAuth implementation exists; session cookie scopes actions and newer memory routes. Legacy `/api/memory/{user_id}` routes remain caller-addressed | “No session handling exists” would be wrong. Production authorization and legacy-route exposure still need work before a public deployment. Google identity connection does not grant Gmail access. |

Gemini correctly identifies the default-path gate, divergent order paths and missing merchant loop. Three qualifications matter:

1. Its `thanks` warning is overstated: `thanks` is a local-router intent; the model prompt maps thanks into greeting/smalltalk, both supported by the client. Align documentation/intent handling, but this is not evidence that ordinary model thank-you turns necessarily fail.
2. An in-process stream queue alone is not durable delivery. Persist events, messages and an outbox transactionally; use SSE as transport and polling/replay as recovery.
3. Returning `provider_confirmed` plus a reference string satisfies today's adapter interface, but the string is not independent verification. A registered internal adapter must first commit a recipient-owned inbox record. Label the merchant as sandbox; keep authenticated actor/event evidence for acceptance.

### Verification performed

- Backend: `.venv\Scripts\python.exe -m pytest -q tests -p no:cacheprovider --basetemp ../../output/sol-review-pytest-approved` from `apps/api`: **40 passed, 11 skipped**. The first sandbox run hit temporary-directory permissions; an approved rerun succeeded.
- Frontend: the profile, recovery and Luna-client commands in `apps/web/tests`: **92 + 8 + 7 = 107 passing checks**, zero failures. The handoff's 100 excludes the seven Luna-client checks.
- These are offline checks. I did not run paid live golden cases, contact merchants, inspect credentials/billing, perform device/browser parity checks or establish a deployed end-to-end proof. Green unit tests do not establish those outcomes.

## 3. Live proof and cinematic boundaries

**Adopt one live merchant proof**, with a stronger definition than “the model selected laundry.” The complete chain is:

`Typed/PTT request → Luna structured intent and stated facts → host-validated fixed catalog → merchant mini-app → exact approval snapshot → durable merchant inbox receipt → authenticated merchant event → deadline check → persisted chat update`.

For “press my shirt by 09:00,” the merchant first proposes 10:00. The system compares timezone-aware timestamps, identifies the miss and proposes asking for an earlier time. The user approves that message if it creates a new side effect; it is not a second price approval. The merchant replies 08:30 at the unchanged published price. Do not mark the shirt `READY` at 08:30 merely because that is its promised completion time; readiness needs its own merchant event. Keep time commitments as event metadata under the canonical lifecycle, not `SLOT_CONFIRMED` as a new status.

This demonstrates bounded agency: extracting a goal, preserving a constraint, detecting failure and proposing a corrective action. Fixed catalog math, authorization and status transitions should remain deterministic. Do not manufacture an LLM-dependent step merely to make the system look more autonomous.

| Moment | Honest stage treatment | Claim to avoid |
|---|---|---|
| Captive Wi-Fi / install | Visible scripted prototype label; explain that airport distribution is a concept | Actual DXB Wi-Fi partnership or a real OS installation |
| Merchant order | Real application dispatch and separate operator action; persistent `Sandbox merchant` label until an actual participating shop exists | Real commercial fulfillment from an internal test operator |
| Taxi memory | Recall explicitly supplied trip facts; ask only for missing fields; show `Prepared, not filed; not recovered` | A driver found, an RTA case filed or a bag recovered without evidence |
| Location/proactivity | Operator-only trigger, visibly `Demo trigger`; real deduplication and persisted message | Background PWA geofencing |
| Fine appeal | Remove from four-minute contest story. Any separately approved vision film must keep `Concept simulation — no filing or authority decision` visible throughout | An actual appeal, official notification or penalty waiver |
| Network/model failure | Visible failure/labelled router; blocked or unknown execution state; identify a fallback recording as recorded | Silent playback or a timer masquerading as a live response |

These distinctions reduce misleading claims; they do not guarantee eligibility. The repository has unresolved organizer-rule questions, and this review did not verify a current rulebook or disqualification standard. The four-minute limit here is the repository's rehearsal target, not a newly verified contest rule.

`PLAN.md` §3 permits an official-channel recovery handoff, while §7.8 says guidance/copying alone is not completed agentic execution and records rejection of the old C6 handoff. Preserve both truths: show memory and honest preparation, leave unavailable dispatch blocked, and describe taxi execution as unfinished. Resolve that product acceptance conflict explicitly before claiming C6 complete; do not invent an RTA adapter to close it.

## 4. Arbitration on the founder decisions

| Decision | Recommendation | Reason and boundary |
|---|---|---|
| **D01** | **A: pilot merchant inbox dispatch and live acknowledgement** | Recommendations alone show retrieval, while arbitrary browser execution adds unstable external dependencies. Use one fixed-price laundry with an actual operator. An internal sandbox proves the software path, not merchant-market validation. |
| **D02** | **B: push-to-talk, with text as an immediate fallback** | A deliberate press prevents presenter narration becoming commands. Display/edit the transcript before action preparation. No always-on wake word. Ship voice only after it passes microphone, HTTPS, permission-denial and noisy-room checks on the stage device. |
| **D05** | **D: remove the fine story from the contest cut** | Taxi memory already closes the continuity story. A fine waiver introduces a second product, government authority and an unproved outcome. I disagree with Gemini's retained simulated climax. Labelling improves honesty but does not fix scope or timing. |
| **D07** | **A: Places/Routes before Gemini grounding, after the merchant proof** | The existing model already handles understanding. Add one bounded search/route benefit rather than a second model stack. Verify billing account, applicable products and quotas before allocating money; no percentage allocation is justified without access. |

D07 has a concrete implementation trap: this app calls Places web-service endpoints and renders a MapLibre map. Google's current [Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies) require mapped Places API results to use a Google map. A compliant attributed list without plotting those results is a possible first step; otherwise use a Google map for that view. Do not assume rules for a different Google UI product apply to these REST results.

The current [Gemini billing documentation](https://ai.google.dev/gemini-api/docs/billing) also has account/timing-specific credit conditions. The reported $300 is not proof that Gemini Developer API usage is covered. Check the actual account instead of repeating either a blanket coverage or exclusion claim. Neither Google feature should block a clearly labelled fixture-based rehearsal of the merchant loop.

For the remaining decisions: use the pilot inbox with fixed orders (D03), real merchant-change updates before simulated location (D04), explicit approved side effects (D15), visitor persona (D16), and one tested vertical (D09). D08 is constrained by the mini-app lock; D10 cannot erase the profiler requirement; D11 does not require a CRM; D12 community remains LATER. D14 retains the acquisition hold. D17's film-heavy timing should yield to the canonical live deadline-conflict sequence. D18 monetization hypotheses need merchant validation, not contest infrastructure.

## 5. Concrete sprints and release gates

These are dependency-based work packages, not a promise that the unbuilt architecture fits a few days. Establish dates after confirming the official deadline and available engineering capacity. Keep changes in the existing ES modules/FastAPI monolith; do not add another agent framework.

### Sprint 0 — reconcile the contract and establish a baseline

1. Record the narrow sequencing decision above in `PLAN.md` if approved; otherwise schedule Step P first. Preserve hard scope locks.
2. Correct stale entry/legacy paths in the canon and handoff, remove the handoff's fine-twist requirement, and distinguish implemented functionality from targets. Treat this as proposed documentation work, not changes performed by this review.
3. Verify and archive organizer evidence for deadline, artifacts, presentation format, prototype expectations, simulation policy, eligibility and IP. Do not infer them from another review.
4. Fix `chat.js` Luna enablement at `/index.html` with API availability handling and visible fallback. Verify `/`, `/index.html` and `/lab/` behavior; live golden tests require configured credentials and a deliberate live run.
5. Capture current iPhone 390 × 844 screens against approved references and list only material parity gaps. Preserve working shell/navigation.

**Exit:** one unambiguous stage story, declared sequencing, and an observed real model call from the normal entry. Measure latency; choose model effort through config based on results, not an assumed eight-second performance guarantee.

### Sprint 1 — one durable, approved order reaches a merchant

1. Extend Pydantic action/catalog contracts for provider ID, catalog version, SKU quantities, fixed line totals, deadline and timezone. Server validates SKU/quantity limits and recomputes totals; arbitrary model/widget prices are rejected. Include recipient, exact shared fields and effect in the approval snapshot.
2. Route `offers.js` and `service-workflow.js` through that same preparation/approval path. Remove timed submission/acceptance from the live path. Replace hard-coded “Dubai Marina (you told me)” with a confirmed fact or a missing-field prompt.
3. Complete the widget host gate: approved bundle on a separate origin, sandbox without `allow-same-origin`, restrictive CSP, per-frame token/source/schema checks, `order.request` only, host-owned catalog values and timed native fallback.
4. Add merchant inbox tables/API and `merchant.html`/`merchant.js` or an equivalent dedicated view. Merchant identity is server-bound to one provider; user sessions cannot issue merchant commands or inspect other merchants' requests.
5. Register one internal laundry adapter. Commit a recipient-owned inbox request with a stable reference and idempotency key before acknowledging receipt. Avoid unnecessary loopback HTTP within the monolith. Preserve sandbox provenance alongside live execution evidence.
6. Add authenticated idempotent accept/decline/ready commands and legal state transitions. Keep draft discard separate from dispatched cancellation; implement supported provider cancellation or show it unavailable.

**Exit:** approve once or twice → one inbox request; user/merchant isolation holds; merchant command is required for acceptance. Tampered price, stale snapshot, bad bridge payload and uncertain dispatch fail honestly. Restarting either view does not lose the request.

### Sprint 2 — deadline follow-through and durable conversation

1. Persist typed conversation messages and action-event references on the server; reconstruct pending approvals/status cards from those records on reload. Close legacy caller-controlled memory access before exposing the deployment publicly.
2. Write each merchant transition, outbox item and resulting conversation update transactionally. Implement stable event IDs/cursors and deduplication; never acknowledge a stream event as durable merely because it entered a process queue.
3. Deliver via authenticated SSE, with bounded polling and cursor replay fallback. Test reconnect, duplicate delivery and process restart. Measure the canonical merchant-to-chat target of <1 second under rehearsal conditions.
4. Add provider-sourced `ready_at`, deterministic deadline comparison in `Asia/Dubai`, and an approval for the exact earlier-time request. Reject price drift. Retain the immutable event history when the merchant changes its promised time.
5. Add scheduler/outbox consent, quiet hours, dedupe keys and one operator-only demo-trigger endpoint. Duplicate trigger → one persisted message; a stale/irrelevant reminder is suppressed.
6. Connect saved trip facts to report preparation across reload, preserving evidence tiers and missing values. Keep fixture driver tracing outside the live-proof path; unavailable official submission stays explicitly blocked.

**Exit:** 10:00 → deadline conflict → user-approved earlier-time request → merchant's 08:30 reply appears in chat at the same price. No fake readiness, filing or recovery; no duplicated notification after reconnect.

### Sprint P — persistent profile, mandatory before claiming the canonical floor

Run this before Sprint 1 if the current gate remains unchanged; otherwise complete it before release.

1. Implement architecture §12's persistent episodes/facts/intents/routines/snapshots and required Postgres/pgvector foundation, with migrations and user ownership. Keep JSON memory migration explicit.
2. Implement deterministic evidence weights, decay, contradiction closure, as-of reads and idempotent ingestion/rebuild; share vectors with the current JS math.
3. Surface Confirm/Edit/Not true/Forget and evidence for hypotheses. Keep confirmed memory distinct from inferred ranking input; avoid sensitive-trait inference.
4. Connect the real persistent profile to the Services surface and visible “Because…” explanations. Do not promote synthetic episodes into user history.
5. Pass golden timeline, tier-leak, rebuild/property and hot-path p95 ≤300 ms gates from architecture §12.5. Ensure forgotten facts are not reintroduced through retained model checkpoint context.

**Exit:** the displayed profile is backed by persisted user events, survives restart and cannot leak an inference into approval, prefill or proactive sends. If incomplete, show the fixture honestly and report the canonical gate as unmet.

### Sprint 3 — stage reliability and presentation

1. Add PTT only if it passes target-device checks; otherwise use live typed intent. Keep actual model/dispatch time in the run budget.
2. Check touch targets, safe areas, keyboard/composer behavior, mini-app scrolling, WebGL fallback and readable status/provenance labels on the actual iPhone. Verify what Add to Home Screen really does separately from the scripted install scene.
3. Prepare separate presenter and merchant devices, a trained operator, one reset/seed procedure for synthetic data and a visible connection/health check. Do not rehearse using real personal trip data.
4. Run negative scenarios: model unavailable, denied microphone, offline widget, duplicate approval, merchant decline, expired approval, dispatch timeout and stream reconnect. `UNKNOWN_STATUS` means reconcile by reference; do not automatically resend an ambiguous order.
5. Rehearse ten complete runs ≤4:00. Record an honest fallback video and identify it as recorded if used. Freeze features after the release gates; use measured success/latency results in the deck.

**Exit:** ten clean timed runs, fallback available, readable evidence log, and no dependence on an unconfigured government/Google/commerce integration.

## 6. Four-minute rehearsal cut

This preserves the canonical story and uses its permitted cut of photo onboarding. It is a proposed timing adjustment, not a replacement plan.

| Time | Screen and proof |
|---|---|
| 0:00–0:15 | Scripted arrival/coverflow; one sentence explaining the companion |
| 0:15–0:45 | Compact confirmed-location guide and user-given taxi/hotel facts; transport reasoning only if verified and ready |
| 0:45–1:15 | Live “shirt by 09:00” request; model source visible; fixed-price rows and merchant mini-app |
| 1:15–1:40 | Exact host approval, shared fields, fixed total; visible user tap |
| 1:40–2:40 | Separate sandbox merchant receives request, accepts, proposes 10:00; deadline conflict; approval to ask earlier; merchant replies 08:30 |
| 2:40–3:00 | Persisted update survives reload; one brief profile/evidence view, clearly fixture-labelled if its release gate is unmet |
| 3:00–3:40 | “I left my bag in the taxi”; saved facts prefill report, missing description requested; prepared/not filed/not recovered |
| 3:40–4:00 | Close on memory plus follow-through; disclose sandbox merchant and unavailable integrations |

The rehearsal can honestly demonstrate a narrower prototype before every gate is done. Calling it the completed canonical MVP requires the floor above to pass, including profile, durable chat and provider evidence. The priority is one inspectable chain from user intent to an independently generated merchant event, with the existing story making that chain memorable.
