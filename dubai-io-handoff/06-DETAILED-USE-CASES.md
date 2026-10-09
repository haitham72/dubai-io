# Dubai-io — Detailed Use Cases & Agent Experience Specification

**Version:** 1.2 · **Baseline:** 8 October 2026  
**Document role:** Canonical *expanded examples* and testable experience specifications for product/UX agents, backend engineers, integration teams, evaluators, and ChatGPT Work.  
**Brand:** Dubai-io (`dubai-io.com` is an intended name, not a claim of domain ownership).  
**Positioning:** **Your Intelligent Dubai Companion.** WeChat-inspired continuity and services, Reddit-inspired authentic community intelligence, and an AI-native contextual orchestrator.

> **READ FIRST — Scope and truthfulness.** This is a **design document**, not proof of enabled government APIs, airline reservations, live indoor positioning, partnered discounts, eligibility, booking confirmation, medical coverage, licensing, or real-time availability. User-supplied prices, routes, wind thresholds, queues, legal penalties, permit rules, dates, floor numbers, and sample merchants from brainstormed scenarios are **not verified facts**. Production agents must verify current official/authorized sources, record `as_of` and provenance, handle uncertainty, and never claim a payment or booking succeeded without an authoritative receipt. Any literal prices/IDs in code examples are fictional test fixtures. Nothing here authorizes scraping, uncontrolled third-party tool execution, identity sharing or regulated activity.

## 0. How to use this document

- **Canonical IDs:** `S01`–`S25` match `03-SCENARIO-LIBRARY.md`. `T01`–`T10` are *tourist refinements of existing S cases*, **not ten duplicate independent products**. `X01`–`X14` are *new candidate scenarios*, deliberately outside the canonical 25 until approved.
- **Companion-first interface:** one quiet, clean conversation with inline typed cards, optional Discover and Community surfaces. The agent can initiate relevant messages, but users control notification types, context sharing, location, data retention and proactive frequency.
- **Delivery stages:** `MVP` = contest candidate, `PILOT` = useful soon after MVP, `FUTURE` = vision/research. They are *suggestions*, not confirmed commitments. Do not implement all scenarios at once.
- **Action capability levels:** `L1_DISCOVER`, `L2_CONTACT`, `L3_QUOTE`, `L4_EXECUTE`, `L5_FULFILL`. A directory entry/CSV provides L1, not L4.
- **Confirmation policy:** An in-app deep link is a **handoff**. `Booked`, `Paid`, `Issued`, `Delivered`, `Filed`, `Confirmed` require trusted issuer/provider evidence. `Awaiting confirmation` is preferable to optimistic fiction.
- **Cross-references:** `01-PRODUCT-VISION.md` = identity; `02-SYSTEM-ARCHITECTURE.md` = modules/states; `03-SCENARIO-LIBRARY.md` = compact index; `04-SERVICE-INTEGRATION-STANDARD.md` = provider contract; `05-CONTEST-MVP-AND-VALIDATION.md` = scope and scoring. This document is a **superset of concrete interactions**, not a replacement for architecture.

## 1. User experience contract

### 1.1 What the user sees

A single chat timeline mixing human conversations, assistant messages, verified provider updates, and small action cards. Avoid feature labyrinths. Never show an artificial system activity log in the user feed unless the user requests details. Do not give every service its own app tab. When necessary, open a dedicated map viewer, image/video player, accessible form, or provider checkout; return the user to the conversation afterward.

**Universal message anatomy:**

1. One natural sentence: what happened or what the companion thinks the user needs.
2. Zero or one primary action card; use a short list only for genuine alternatives.
3. Card source status: `Official`, `Provider-confirmed`, `Merchant-submitted`, `Community opinion`, `User-provided`, `Estimate`, or `Demo simulation`.
4. Timestamp/freshness for live conditions, terms, and costs; no decorative spurious precision.
5. One clear primary action, plus dismiss/change/correct. Require approval before data sharing, booking, purchasing, messaging others, or filing.

### 1.2 Minimal action card library

| Card | Typical fields | Primary interaction |
|---|---|---|
| `next_step` | heading, 1–3 instructions, confidence, source | Next / Correct location |
| `route_options` | transport modes, time, estimated price, luggage/accessibility, freshness | Compare / Open route |
| `service_comparison` | providers, distance, range, reviews provenance, hours, capability level | Contact / Request quote |
| `offer_voucher` | participating merchant, terms, verified expiry, issuer token | Reveal verified voucher |
| `group_plan` | participants, preferences, time poll, privacy scope | Vote / Share within group |
| `activity_plan` | checklist, weather, booking links, task statuses | Review plan |
| `notification_reminder` | why sent, due time, source, snooze | Done / Snooze |
| `delivery_window` | order ref, merchant status, expected window, tracking | Track order |
| `ticket_wallet` | ticket holder, issuer, admission date, signed QR/barcode asset | View valid ticket |
| `civic_answer` | short answer, jurisdiction, cited passages, source date, official route | View source / Prepare form |
| `evidence_bundle` | receipts, chat excerpts, photos, permissions, missing pieces | Preview / Export |
| `media_moment` | thumbnail, source video, time offset, confidence | Play at time |
| `indoor_route_step` | venue/floor, anchor shop, destination, next landmark | Next / I'm somewhere else |
| `parking_photo_prompt` | inferred event, venue guess, camera, level/pillar fields | Save parking spot |
| `parking_recall` | photo, manually saved level/section/pillar, time, entrance | Guide me back |
| `action_status` | request id, per-task actual state, external receipt, retry/failure | Review / Retry safely |

### 1.3 Companionship without creepiness

- Prefer **user-owned plans** and opted-in order updates over surveillance. Inference never equals confirmation: “Looks like you may have parked” rather than “You parked at Bay P3.”
- Event-driven push notifications are **also persisted as assistant messages** in the same conversation, with a reason, dedupe key, expiry and user preference. Marketing offers require separate opt-in.
- Native/background sensor signals need OS permission. A PWA alone does not guarantee always-on departure, motion, Bluetooth, or geofencing detection. Manual `I'm here`/`Next` controls must work as fallback.
- Never leak medical details, children's names/tickets, passport scans, or travel plans in lock-screen preview by default.
- **System safety:** Severe symptoms trigger appropriate emergency guidance, not a friendly shopping card; unsupported legal claims do not become authoritative warnings; allergy labels must not imply guaranteed safety.

## 2. Shared execution contract and test taxonomy

```yaml
scenario_id: SXX
version: 1
stage: MVP | PILOT | FUTURE
persona: visitor | resident | both
user_goal: sentence
trigger:
  type: user_request | schedule | authorized_provider_event | opted_in_device_event
  confidence: confirmed | inferred | estimated
required_inputs: []
optional_context: []
permissions: []
capabilities: []  # e.g. maps.route, civic.retrieve, merchant.request_quote
minimum_provider_level: L1_DISCOVER
experience:
  assistant_message: sentence
  card_type: registered_type
  primary_action: registered_action_id
execution:
  approval_required: true
  terminal_success_proof: real provider reference or user confirmation
fallback: simple human-usable next step
observability:
  expected_tool_trace: []
  banned_claims: []
  tests: []
```

**Task lifecycle:** `DRAFT → OPTIONS_READY → AWAITING_APPROVAL → SUBMITTED → PROVIDER_ACKNOWLEDGED → CONFIRMED → COMPLETED`, with `CANCELLED`, `FAILED`, `EXPIRED`, `UNKNOWN_STATUS`. Status is **per subtask**, not automatically shared by an entire travel bundle. Retry execution only with idempotency/deduplication protection.

**Tool/result provenance classes:** `official_current`, `official_historical`, `approved_partner_live`, `licensed_aggregator_live`, `merchant_submitted`, `user_uploaded`, `community_unverified`, `model_inferred`, `demo_fixture`. Use numeric confidence only when calibrated; prefer interpretable evidence labels in the UI.

**Scenario acceptance suite:** every case must have (a) happy path, (b) missing-field handling, (c) no-data/API timeout, (d) stale/contradictory information, (e) rejected permission, (f) denied/cancelled action, (g) duplicate-trigger test if proactive, (h) user correction and deletion if memory-bearing, and (i) accessibility/localization checks. Verify external source, authorization and actual state transitions.

---

# PART I — 25 CANONICAL SCENARIOS, FULL EXPANSIONS

## S01 — Airport arrival: immigration to hotel

**Stage:** PILOT / optional contest demo · **Persona:** arriving visitor, family, international traveler · **Trigger:** user states arrival or shares flight; optionally opted-in arrival geofence or valid flight event.  
**User says:** “We landed in Dubai Terminal 3. Two kids, three suitcases; get us to Business Bay.”

**Agent loop:**
1. Request or retrieve the user's confirmed flight/terminal, destination, party/luggage/accessibility, language, transport preference, arrival time, and phone connectivity. Confirm the airport; do not guess from a network SSID.
2. Build a **human-step arrival state machine**: aircraft exit → arrival signs/entry → baggage → customs exit → transport pickup. Use manual `Next` and `I'm here` checkpoints. Explain immigration rules only from current official material; route Smart Gate questions to official eligibility verification.
3. If a permitted source supplies the actual belt, show it with timestamp; otherwise explicitly tell the user to check airport displays. For Wi-Fi/SIM/ATM/WC requests, surface sourced facility information or generic overhead-sign guidance.
4. Compare Metro, taxi, ride-hailing and rental based on current operating times, accessible transfers, walking distance and **estimated** total cost. Do not treat hotel proximity to a Metro station as door-to-door feasibility.
5. Display one compact `route_options` card, with `next_step` when navigating airport stages. External booking/ticket purchase stays `HANDOFF` until provider confirms.
6. If delayed arrival invalidates the selected Metro route, propose an updated alternative; notify only with user's permission.

**Visible example:** “You're at baggage claim. Check the screen for your belt. Next: would you prefer the simplest ride with the kids, or the lowest-cost route?” `[Taxi estimate] [Metro route] [Rental counter]`.

**Required tools/data:** user trip state; verified airport/immigration guidance; permitted route/transit feeds; current fare rules; licensed place/facility sources; approved rental catalog only if available.  
**Permissions:** trip data; coarse location optional; push optional; share location with taxi operator only after approval.  
**Failure/risks:** no indoor GPS; security-sensitive areas; unverified queue times/belt numbers, free-SIM claims, counter directions, direct Nol issuance, booking APIs and promotional discounts. No automated border/visa decisions.  
**Success proof:** visitor confirms stage complete; route opened; actual receipt if transport purchased.  
**Tests:** wrong terminal, overnight Metro closure, diverted flight, no internet, passport ineligible for gates, wheelchair/luggage, stale fares, two different airport locations.

## S02 — Skydiving, beach day and post-event logistics

**Stage:** PILOT / flagship orchestration · **Persona:** adventure tourist · **Trigger:** “Plan skydiving tomorrow, then JBR beach.”

**Agent loop:**
1. Clarify date/participant count, approximate budget, eligibility/age where required, hotel origin and whether the user has an existing operator reservation.
2. Retrieve the operator's current public instructions, opening/booking links and weather context. **The skydive operator alone determines operational safety and jump approval.** A generic wind value is not a PASS/FAIL threshold.
3. Assemble an itinerary that accounts for check-in, activity duration uncertainty, transport, meal breaks and sunset/heat. Handle cancellation or weather delays gracefully.
4. Estimate route/parking from licensed mapping and published parking rules. Do not promise that a public parking space can be reserved or prepaid without actual capability.
5. Offer an optional equipment checklist (towel, sunscreen, pouch), linking to legitimate merchants; product shipping times are merchant estimates and may not arrive before departure.
6. Suggest *optional* laundry/cleaning quote for later, not a default auto-scheduled paid service. Keep each item independently pending or confirmed.

**Visible example:** “I've prepared a plan. Your jump slot needs operator confirmation. Weather may change—let's keep the beach portion flexible.” `[Open official slot calendar] [Review route] [Pack checklist] [Request laundry quote]`.

**Tools/data:** `weather.forecast`, `maps.route`, `operator.public_booking_link`, `merchant.search`, `merchant.request_quote`, `itinerary.save`.  
**Permissions:** share date/origin with providers only on approval; no default purchase.  
**Failure/risks:** absent live slot API, delayed weather, unsafe inferred wind threshold, “all-in-one checkout” without cross-merchant agreements, fabricated 15% discount, guaranteed delivery, false parking reservation.  
**Success proof:** individually sourced booking ref, actual courier ETA, merchant-confirmed laundry request where available.  
**Tests:** skydiving cancelled, forecast changed, guest under eligibility requirements, no partner laundries, Amazon listing removed, budget exceeded, stage recovery.

## S03 — Short-stay rental, legality and check-in

**Stage:** FUTURE · **Persona:** visitor needing 2-week accommodation · **Trigger:** “Find a studio in Business Bay for tonight.”

**Agent loop:**
1. Ask dates, occupancy, budget, accessibility, check-in urgency, and preferences; do not assume a furnished holiday home is governed by the same process as an annual tenancy.
2. Search authorized holiday-home providers; show the source of licensing claims and booking terms. Verify any official permit only through permitted authoritative interfaces or evidence, without claiming a government database lookup that is unavailable.
3. Extract deposit, cancellation, guest-identification and check-in conditions; flag missing information rather than inventing a fine or building rule.
4. Explain property-specific smoking, quiet hours, security and visitor registration **only from actual listing/contract and authoritative relevant rules**. Do not assert a fixed Dubai-wide hotel-apartment smoking penalty.
5. Provide approved booking handoff; ask before sharing identity documents. If smart locks are supported, retrieve codes through authorized secure channels only after valid check-in.

**Card:** `property_comparison` → `terms_summary` → `action_status`.  
**Tools:** listing provider APIs/links, public official guidance, `document.extract_terms`, `evidence.save`.  
**Permissions:** sensitive ID/personal travel details, explicit share scope.  
**Risks:** fraud, unlawful subletting, fake permits, deposit escrow, identity exposure, legal conflation of tenancy/holiday-home rules.  
**Success proof:** provider booking reference and validated check-in instructions.  
**Tests:** outdated listing, double booking, conflicting deposits, cancellation terms, undocumented permit, false smoke penalty.

## S04 — Evening walk with climate and pedestrian guidance

**Stage:** PILOT · **Persona:** visitor or resident · **Trigger:** “Plan a scenic 5 km walk in Marina, start 7 PM.”

**Agent loop:**
1. Resolve start/end, distance, pace, accessibility, stroller/pet needs and temperature tolerance.
2. Request pedestrian routing and heat/humidity forecast; prioritize approved crossings and accessible pathways; reject car-road approximations masquerading as walkable routes.
3. Create a scenic loop with optional hydration and rest stops; offer one or two legitimate participating merchants, not fabricated offers.
4. Present useful official pedestrian and scooter rules only in relevant context. A GPS geofence cannot determine intent to jaywalk or enforce legal compliance; avoid alarming fine popups.
5. If heat increases, propose postponing, shorter indoor options or a hydration stop; never claim a medical determination.

**Card:** `walking_route` with accessible directions, heat context and **optional** café card.  
**Tools:** pedestrian route, forecast, public rule retrieval, permitted places.  
**Permissions:** foreground location optional; background tracking separately consented.  
**Risks:** non-accessible bridge, street-level mismatch, incorrect fine value, unsafe route suggestion, intrusive notifications.  
**Tests:** route crosses highway, user requests stroller path, sudden rain/heat alert, GPS drifts, no merchant offers.

## S05 — Four-person dinner with dietary needs

**Stage:** FUTURE / simplified group poll PILOT · **Persona:** friend/family group · **Trigger:** “Order dinner for four—two vegetarian, one nut allergy.”

**Agent loop:**
1. Obtain a consented summary of dietary preferences; do not secretly aggregate private chats or infer clinical allergy severity.
2. Search permitted restaurants that actually publish dietary and allergen information. Present **“allergen information not verified”** if kitchens cannot confirm cross-contact controls.
3. Create a group poll or shared basket invitation; each participant controls their choices and what is shared.
4. Pull menu/pricing from a legitimate provider. Check live restaurant open state, delivery region, charges and earliest ETA.
5. Request separate verification for serious allergy needs; never label “nut-free verified” based solely on an LLM reading a menu.
6. Order/payment only through approved integrations; offer an official delivery-app handoff otherwise. Bill splitting needs a licensed payment provider and consent.

**Card:** `group_plan`, `menu_choices`, `action_approval`; costs visibly **estimated until provider checkout**.  
**Tools:** provider menu API, food/dietary data, group state, merchant checkout when authorized.  
**Permissions:** group membership and dietary details; minimal retention.  
**Risks:** allergy harm, misleading food-grade claim, unauthorised shared medical information, invented dispatch, payment splitting.  
**Tests:** conflicting food restrictions, hidden nuts, participant declines, restaurant closes, price changes at checkout.

## S06 — Second-hand items, trust and delivery

**Stage:** FUTURE · **Persona:** resident/tourist buying used item · **Trigger:** “Find a used 27-inch monitor in Marina, or help sell my table.”

**Agent loop:**
1. Match desired model, condition, warranty preferences, pickup location, budget and urgency to permitted listings.
2. Surface seller-supplied evidence, listing age, pricing comparison, provenance and clearly marked user reputation. Never assert UAE PASS verification without real verified identity flow.
3. Let buyer ask questions in a moderated merchant/peer chat with abuse controls and no off-platform payment pressure.
4. Suggest in-person inspection and anti-fraud checklist; delivery only after courier supports it and both parties consent to addresses.
5. Do **not** hold escrow funds without appropriately licensed provider and contractual safeguards. A safe pilot uses chat, handoff and manually documented handover.

**Card:** `classified_listing` with condition checklist and explicit payment warning.  
**Tools:** listings DB, moderation, optional permitted courier quote.  
**Permissions:** profile visibility, photo/data ownership, address sharing only on approval.  
**Risks:** counterfeit goods, stolen goods, misleading condition, fake ratings, payment fraud, prohibited merchandise.  
**Tests:** duplicated listing, seller unverified, suspected phishing URL, item no longer available, shipping mismatch.

## S07 — Sick day: urgent guidance, clinic and insurance handoff

**Stage:** FUTURE / low-risk care-navigation PILOT · **Persona:** visitor/resident with symptoms · **Trigger:** “I have severe fever and stomach pain.”

**Agent loop:**
1. Identify emergency red flags with conservative, clinically reviewed decision logic; if urgent, offer official emergency number/nearest emergency care and advise seeking immediate help. **Do not delay emergency advice to upsell a clinic.**
2. With permission, inspect insurer name and non-sensitive plan/network information. Do not promise coverage until insurer or provider actually verifies eligibility.
3. Find current licensed care providers and show official contact/telehealth handoff when available; prioritize care needs, not commission ranking.
4. Explain that prescriptions and sick-leave certificates come from authorized clinicians and official workflows; no AI-issued prescription or fabricated DHA-stamped PDF.
5. Optionally organize documents for insurer reimbursement only with verified genuine invoices/receipts from the provider.

**Card:** `care_options` with emergency escalation at top where indicated.  
**Tools:** official emergency directory, verified clinic registry, insurer authorized lookup, permitted appointment links.  
**Permissions:** sensitive health/insurance, explicit retention and sharing.  
**Risks:** harmful triage, insurance misrepresentation, drug restrictions, forged medical documents, geolocation error.  
**Tests:** emergency red flags, no insurance, different country policy, unsupported telehealth, request for controlled medication.

## S08 — Driving, parking, Salik, fines and detailing

**Stage:** PILOT for guidance / FUTURE for financial execution · **Persona:** car user · **Trigger:** “Am I okay for tolls on the way to Abu Dhabi?”

**Agent loop:**
1. Ask whether vehicle is owned/rented and whether authorized vehicle account connection exists; use plate/account details only through secure scoped integrations.
2. Generate a route with current toll guidance and known toll gate estimates; account for variable tariffs, time windows and changes.
3. If no authenticated Salik or fine-data access, explicitly state “I can't check your balance/fines” and link to official portals.
4. For a possible parking event, request zone confirmation and show authorized official payment route. Never mark parking paid from GPS alone.
5. Recommend optional verified mobile detailing if vehicle will remain parked; require actual quote and confirmation.

**Card:** `route_toll_summary`, `vehicle_account_handoff`, `parking_status`, optional `service_quote`.  
**Tools:** route API, official tariff retrieval, authorized account connectors, merchant registry.  
**Permissions:** vehicle identifiers, accounts, location, payments.  
**Risks:** wrong toll balance, assuming flat Salik rate, false “no fines”, double parking payment, unauthorized plate lookup.  
**Tests:** rental plate, user refuses auth, off-peak vs peak, non-Dubai tolls, toll data stale, duplicate top-up.

## S09 — Dining/nightlife reservation and safe return

**Stage:** PILOT for venue/transport links · **Persona:** adult visitor/resident · **Trigger:** “Rooftop lounge in DIFC tonight; safe ride afterward.”

**Agent loop:**
1. Clarify party size, desired time window, transport need, accessibility, venue preferences, and applicable age eligibility without collecting unnecessary identity data.
2. Search venues and verify their stated booking, minimum-spend, dress and admission terms. Times are **not available** unless a reservation provider confirms them.
3. Offer one safe-return plan: taxi or designated driver with authenticated handoff; don't schedule a driver automatically on inference of alcohol consumption.
4. Provide current official legal information as relevant; avoid sweeping deportation/penalty claims or inventing tourist permits.
5. Show separate confirmed states for venue booking and driver assignment.

**Card:** `reservation_options`, `safe_return`, `action_status`.  
**Tools:** venue booking providers, route/driver partner links, official civic RAG.  
**Permissions:** party info, booking, optional location; no stored alcohol preference by default.  
**Risks:** invented live tables, wrong door policy, false licensed permit, unconfirmed driver, unnecessary sensitive profiling.  
**Tests:** no tables, delayed departure, driver declines, venue minimum changes, underage account.

## S10 — Consumer dispute, civic guidance and visa-status handoff

**Stage:** MVP for complaint assistant / FUTURE for authenticated visa checks · **Persona:** visitor or resident · **Trigger:** “Dry cleaner damaged my suit, and when does my visa expire?”

**Agent loop:**
1. Split into separate goals: (A) damaged service claim; (B) immigration/visa status. Do not merge personally sensitive information across providers.
2. Ask for receipt, service date, merchant terms, damage photos and previous support communication; extract only relevant evidence and clearly identify missing facts.
3. Retrieve official, dated UAE/Dubai consumer rules **with exact cited text and jurisdiction**. State uncertainties and distinguish contract clauses from law.
4. Draft an editable complaint letter, refund request or official escalation checklist; open the verified filing portal. Claim filed only when user or portal supplies acknowledgement.
5. For visa expiry, use an authorized government connector if actually granted; otherwise direct to official status checking and allow user-entered dates for reminders (clearly user-supplied).

**Card:** `evidence_bundle`, `civic_answer`, `reminder`, `official_handoff`.  
**Tools:** document extraction, official-source RAG, draft generator, reminder engine, approved gov links.  
**Permissions:** user documents and sensitive identifiers; no automatic external submission.  
**Risks:** hallucinated statutory article/fine, wrong authority, false visa expiry, privacy/defamation, unverified outcome.  
**Tests:** missing invoice, contradictory receipt, outdated law, wrong emirate, unknown visa type, duplicate complaint.

## S11 — Lost property in taxi, ride-hailing or public transport

**Stage:** MVP candidate / high-value recovery demo · **Persona:** worried visitor · **Trigger:** “I left my wallet in the taxi 20 minutes ago!”

**Agent loop:**
1. Respond promptly with calm next action. Ask the time, pickup/drop-off, transport type, payment mode, and whether loss includes passport, cards or phone. For safety-critical documents, surface relevant official steps.
2. With permission, search authorized itinerary, saved ride receipt, e-mail attachment/user uploaded payment record, or user-entered trip details. Do not invent a vehicle plate, driver number or RTA reference.
3. Determine the correct lost-and-found channel based on taxi/Metro/ride-hailing provider and official up-to-date processes. Offer a concise incident summary with only the details that are needed.
4. If direct reporting integration is absent, open the official form/number with a prefilled note the user can copy; ask the user to record the resulting ticket number.
5. Store a minimal `lost_property_case` with follow-up reminders and recovery status; do not advertise “driver dispatched” without actual external acknowledgement.

**Message/card:** “I can help you report this. I found your ride receipt from 20 minutes ago; may I use its reference to prepare the report?” `[Review trip details] [Open official reporting]`.  
**Tools:** `trip.find_recent`, `media.receipt_extract`, `official.process_lookup`, `case.draft`, `reminder.create`.  
**Permissions:** trip and payment metadata; passport number excluded unless strictly necessary.  
**Risks:** urgent loss, duplicate claims, sharing travel history, fake official report, missing ride ID.  
**Success proof:** official case ID or user-confirmed contact; recovery requires separate evidence.  
**Tests:** ride receipt missing, Metro not taxi, wrong vehicle, phone also missing, night-time official support, user with no local number.

## S12 — Dubai Mall lost vehicle and parking-memory recall

**Stage:** PILOT · **Persona:** mall visitor · **Trigger:** “Where did I leave the car at Dubai Mall?”

**Agent loop:**
1. Search the user's confirmed `parking_memories` and camera-note metadata, prioritizing the latest explicitly saved mall spot.
2. Show original photo of pillar/section, manually entered level and zone, and saved time. Explicitly say if metadata was inferred rather than confirmed.
3. If venue supports an official Find My Car or navigation experience, provide authorized handoff; otherwise navigate to the *relevant entrance/known landmark*, then use user-confirmed floor and signage to guide.
4. If there are multiple possible parking sessions, ask the user which date/vehicle they mean. Do not pretend indoor GPS tracked the exact bay.
5. Let user delete the memory after return, or expire it by policy.

**Card:** `parking_recall` with photo, floor/pillar, route-to-entrance, `Found it`.  
**Tools:** user-scoped memory, permitted mall directory, optional venue link, routing.  
**Permissions:** photo and location; local-only/on-device storage option preferred for privacy.  
**Risks:** reused parking images, another family member's vehicle, incorrect entrance, inaccessible floor, photo policies.  
**Tests:** photo blurred, no floor saved, two cars, no connection underground, user parked elsewhere, deleted memory.

## S13 — Tourist tax-free receipt vault and airport departure

**Stage:** MVP candidate / proactive reminders · **Persona:** international visitor shopping in Dubai · **Trigger:** receipt upload or “I'm leaving tomorrow; did I forget VAT refunds?”

**Agent loop:**
1. Offer opt-in receipt scan. Extract merchant, date, amount, tax, tax-free program/issuer markers and receipt quality. Store source image plus extraction confidence.
2. Retrieve *current and applicable* UAE tourist refund eligibility, minimums, authorized operator workflow, deductions and validation timing from official sources. Don't automatically assume any receipt is enrolled or refund-eligible.
3. Group purchases into a checklist: `likely ready`, `needs validation`, `missing evidence`, `ineligible/uncertain`. Show estimates only when the calculation basis and deductions are actually known.
4. Based on confirmed departure, remind user before baggage drop if required by the actual refund program; route to the legitimate official operator/airport directions.
5. Distinguish `Receipt collected` → `Operator registration found` → `Validated` → `Refund initiated` → `Refund received` only with appropriate user/provider proof.

**Card:** `refund_checklist` and `departure_reminder`.  
**Tools:** document understanding, official program sources, travel dates, reminders, authorized validation handoff.  
**Permissions:** receipts, passport/boarding data only if strictly required; sensitive lock-screen content hidden.  
**Risks:** wrong VAT arithmetic, ineligible merchant, unregistered receipt, inaccurate kiosk, alternate countries' refund rules.  
**Tests:** duplicate receipt, unclear OCR, domestic resident, nonparticipating shop, airport changes, late-arrival flight, multi-country itinerary.

## S14 — Abu Dhabi cultural day trip from Dubai

**Stage:** PILOT · **Persona:** family/couple visiting mosque/landmarks · **Trigger:** “Take us to Sheikh Zayed Grand Mosque tomorrow.”

**Agent loop:**
1. Confirm date, party size, ages, mobility needs, departure neighborhood, mode preference, and time budget.
2. Retrieve current official visitor rules, opening/closure information, ticket or registration process and dress-code guidance. Do not claim automatic entry acceptance from image classification.
3. Produce Dubai→Abu Dhabi travel options, realistic intercity travel and onward transfer; estimate return time and heat exposure.
4. Optionally allow user-uploaded outfit photos for **advisory** dress-code checklist; show uncertainty and official links. Do not store photos without consent or certify compliance.
5. Save itinerary and remind users to open *legitimately issued* passes/documents. Other city/country services require geographic context switching.

**Card:** `day_trip_plan`, `travel_options`, `entry_checklist`.  
**Tools:** official mosque information, intercity routes, weather, ticket issuer link, optional vision.  
**Permissions:** images, mobility requirements, family tickets.  
**Risks:** religious-content contest eligibility uncertainty, changed access times, inaccurate clothing advice, inappropriate attendance reminders.  
**Tests:** prayer/event closures, non-English instructions, wheelchair route, user declines image upload, children need documentation.

## S15 — Desert safari offer comparison and operator trust

**Stage:** PILOT for discovery · **Persona:** visitors comparing safari packages · **Trigger:** “Find a trustworthy safari for four under AED 900.”

**Agent loop:**
1. Collect group ages, motion tolerance, pickup location, dietary needs, dune-driving preference, timeframe and budget.
2. Discover eligible provider listings from merchant-submitted/licensed sources, separating marketing claims from independently verifiable official status.
3. Normalize inclusions/exclusions: pickup, seating, 4x4 activity, camel/buggy add-ons, meals, cancellation, insurance statements and accessibility.
4. Show common consumer-check questions: vehicle operator, licensed activity provider, exact pickup windows, refund policy, safety brief. Never declare a seller “government verified” unless such verification exists.
5. Link to or submit an approved quote request. Any 10–15% member offer must be backed by a real contract and valid voucher.

**Card:** `safari_comparison`, `terms_summary`, `quote_request`.  
**Tools:** merchant registry, source/provenance service, official verification when permitted, maps.  
**Permissions:** pickup area/group details if requesting quote.  
**Risks:** unverified insurance, fabricated provider license, supplier cancellation, false discount, unsafe add-on suggestions.  
**Tests:** two similarly named operators, offer excludes pickup, children too young, checkout price differs, fake review reports.

## S16 — Laundry and cleaning: from request to resolution

**Stage:** **MVP hero** · **Persona:** visitor/resident · **Trigger:** “I need five shirts ironed before 9 AM tomorrow near Marina.”

**Agent loop:**
1. Parse garment count, deadline, pickup/dropoff address or area, delicate/fabric requirements and contact preference. Request only what is needed.
2. Retrieve registered merchants within serving range. Filter by **verified** capacity and the actual integration level; quote examples are marked estimates.
3. Display up to three providers with transparent total terms: per-item rates, delivery fees, minimum order, cutoffs, damage/claim policy. If unspecified, show `Ask merchant`.
4. User taps `Request quote` and approves exact payload. Adapter creates idempotent request; merchant dashboard or provider API replies with price/window.
5. User approves quote; only then request confirmation. Send delivery/pickup-window updates to the same conversation from actual merchant updates.
6. After service, let user rate/rebook. If damage is reported, open `S10` / `S19` evidence workflow using order ID, receipt, agreed terms and photos.

**Message/card:** “Two laundries serve Marina. One accepts a pickup request; the others have contact links.” `service_comparison` → `quote_approval` → `action_status` → `delivery_window`.  
**Tools:** `provider.search`, `provider.request_quote`, `provider.status`, `provider.confirm`, `events.subscribe`, `civic.retrieve`.  
**Permissions:** location/contact/address sharing; order history retention; push opt-in.  
**Risks:** merchant never responds, cutoff passed, unauthorized address exposure, optimistic status, double order, invented discount.  
**Success proof:** merchant acknowledgement/confirmed order ID, separately from completion.  
**Tests:** deadline impossible, merchant rejects, duplicate request, no provider, pickup window changed, damaged clothing, offline user, cancellation/refund.

## S17 — Café offers, breakfast meetup and genuine community context

**Stage:** PILOT · **Persona:** solo visitor/group · **Trigger:** “Find a budget breakfast at JBR and see if anyone wants to join.”

**Agent loop:**
1. Separate two intents: nearby affordable café and optional social meetup. Never auto-publish public location or invite strangers without consent.
2. Search licensed Places/merchant data for café location/opening, budget suitability and actual offers. Present review provenance and expiry; a menu price is not a binding checkout quote.
3. Retrieve opt-in community posts or publicly permitted information, cite originals and distinguish human reviews from official business facts.
4. Create a time poll/invitation visible only to consenting group members; moderators enforce no impersonation/spam and appropriate age restrictions.
5. Issue a signed, provider-backed discount voucher only when the partner supports redemption; otherwise display normal offer information or contact link.

**Card:** `cafe_comparison` → `community_summary` → `group_plan` → `offer_voucher` when verified.  
**Tools:** location search, community search, group post/poll, merchant offer registry.  
**Permissions:** public post, group membership, optional live location sharing, marketing opt-in separate.  
**Risks:** fake meetups, stalking, discount fraud, empty community, false reviews, age moderation.  
**Tests:** offer expired, café closed, participant cancels, private/public scope mismatch, user declines location.

## S18 — Personal multimodal memory: find a moment inside video

**Stage:** FUTURE / independent research showcase · **Persona:** visitor with saved media · **Trigger:** “When did I spill my coffee at Dubai Mall?”

**Agent loop:**
1. Ask whether to search the user's **own consented media library**; do not search other people's private chats or albums by default.
2. Retrieve video candidates using metadata (date, place, album), thumbnail/clip embeddings and transcription where available. Photo/video location metadata is optional and may be absent or inaccurate.
3. Rank candidate segments. Use a visual-language verifier on a narrow timestamp window to check whether a **spill action** is visible, rather than returning any image containing a cup.
4. Refine time by denser sampling around candidate segments; report `approximately 7.4s` only if corresponding temporal analysis supports it. Never claim exact frame accuracy from coarse 1fps indexing.
5. Return `media_moment` with scrubber anchored to time, confidence/evidence, open original and **user-approved** share flow.
6. Support deletion cascades for source, thumbnails, embeddings, cache and derived tags; honor encryption boundaries and child/group permissions.

**Card:** `media_moment`: thumbnail, approximate timestamp, video source, `Play here`, `Show alternatives`.  
**Tools:** `media.search`, `media.segment_rerank`, `media.verify_visual`, `media.open`, `media.delete`.  
**Permissions:** explicit gallery selection / searchable library opt-in; no silent indexing of encrypted chats.  
**Risks:** false positives, wrong event date, other people's faces, shared family media, embedding leakage, retention cost.  
**Tests:** two coffee clips, no actual spill, event outside sampled frames, encrypted message attachment, revoked permission, deleted video.

## S19 — Rental-deposit evidence and post-transaction protection

**Stage:** PILOT · **Persona:** visitor/resident using rental car or holiday stay · **Trigger:** “I returned the car a week ago and haven't received my deposit.”

**Agent loop:**
1. Identify rental category and agreement; extract provider, return date, deposit, refund window, exclusions and dispute jurisdiction from the actual contract.
2. Find authorized payment receipt, check-in/out photos, handover record and message history, with source and timestamps; ask for missing evidence.
3. Present a neutral timeline without declaring a merchant liable. Cite relevant current official consumer guidance only when jurisdiction applies.
4. Draft reminder and formal dispute request with receipts/photos attached only after user review and consent. Offer the appropriate official escalation path.
5. Track promised refund date and follow-up; never mark money returned without provider/payment/user evidence.

**Card:** `deposit_timeline`, `evidence_bundle`, `civic_answer`, `official_handoff`.  
**Tools:** `documents.parse`, `memory.search`, `reminder.schedule`, `civic.retrieve`, `draft.create`.  
**Permissions:** payment, contracts, photographs, merchant correspondence; protect unrelated private messages.  
**Risks:** changing rental terms, misleading claims of refund rights, legal conclusions, duplicate filings, document exposure.  
**Tests:** mixed currencies, damage fees, partial refund, missing signature, denied file access, different emirate.

## S20 — Budget-aware adaptive city plan

**Stage:** MVP/PILOT · **Persona:** visitor with limited daily budget · **Trigger:** “I have AED 300 left today; make a fun evening plan.”

**Agent loop:**
1. Ask group size, start area, end time, fixed commitments and any excluded spending categories; remember daily budget only with permission.
2. Construct a small itinerary with route time, entry fees, meal estimates, breaks, geographic viability and weather alternatives.
3. Rank genuine deals or free attractions, but don't fabricate availability. Provide a cost envelope including uncertain tax/transport/add-ons.
4. When an external condition changes—rain, heat, closure, delay—replan with user approval rather than silently cancelling bookings.
5. Optionally track **user-entered** expenditure without connecting bank accounts; never imply a complete bank balance.

**Card:** `budget_plan` with current estimates and savings tradeoffs.  
**Tools:** itinerary planner, maps, weather, approved places/prices, optional reminders.  
**Permissions:** location, spending preferences, access to existing bookings.  
**Risks:** underestimated costs, late closures, stale reviews, false discount, public transport access limits.  
**Tests:** party size changes, fixed time conflict, no money for return transport, heat warning, chosen place closes.

## S21 — Delivery updates and snorkeling-trip countdown as assistant messages

**Stage:** MVP for scheduled reminders; PILOT for provider webhooks · **Persona:** family preparing a trip · **Trigger:** confirmed order event, manually saved delivery estimate and itinerary.

**Agent loop:**
1. User saves tomorrow's snorkeling trip and ordered items. Delivery interval may come from an authenticated vendor update or user entry; label origin.
2. When window becomes known, store deduplicated `order.delivery_window_updated` event linked to appropriate order ID.
3. Send an unobtrusive in-chat message: “Your order is *expected* between 2–7 PM. Open tracking.” Refrain from saying `delivered` before receipt.
4. At user-chosen T−10 minutes (or realistic travel departure time, not tour start time), trigger packing checklist. Include passports only when applicable to itinerary/operator requirements or explicitly in user's checklist.
5. If an item remains unconfirmed close to departure, recommend alternative purchase or proceeding without it after the user decides.

**Card:** `delivery_window` → `trip_checklist`, each with snooze/dismiss and task state.  
**Tools:** provider event ingest, itinerary, scheduler, inventory/checklist.  
**Permissions:** notifications and order history.  
**Risks:** stale estimated window, user changed plan, timezone, duplicate notifications, sensitive child details on lock screen.  
**Tests:** late webhook, delayed order, cancel event, duplicate event ID, revoked push, midnight rollover, no tracking API.

## S22 — Motion/geofence-based departure and near-destination check-in

**Stage:** FUTURE native app / manual MVP fallback · **Persona:** traveler on a saved itinerary · **Trigger:** consented geofence/motion transition or `I'm leaving` button.

**Agent loop:**
1. User explicitly enables journey-aware notifications and chooses which trip(s) may use device signals.
2. Native OS detects geofence exit near saved origin combined with relevant motion context. Device emits a minimal derived event; **not raw continuous accelerometer traces**.
3. Agent checks the user's actual trip time and avoids multiple messages. It asks: “Looks like you're heading out. Has the trip started?” with yes/no actions.
4. If user confirms, mark `trip.in_progress`, adjust ETA from mapping where authorized and suppress irrelevant home reminders.
5. On approaching destination, offer tickets or next steps only if tickets and destination are known and notification allowed.

**Card:** `journey_status` / `next_step` / `ticket_wallet` where appropriate.  
**Tools:** native motion/geofence bridge, itinerary, routing, events.  
**Permissions:** background location separate from notifications, clear opt-out and battery behavior.  
**Risks:** taxi/passenger mismatch, bus stop treated as destination, geofence jitter, background app restrictions.  
**Tests:** user never left, motion false positive, no OS permission, GPS unavailable, same trip repeatedly entered/exited geofence.

## S23 — Family attraction ticket readiness and admission

**Stage:** PILOT / actual ticket import · **Persona:** family with several issued tickets · **Trigger:** “We're nearly at the attraction; show everyone's tickets.”

**Agent loop:**
1. User connects or imports legitimate issued tickets; parse issuer/order, participants, date, entry rules and optional QR/barcode asset.
2. Detect duplicates and expired/cancelled tickets. Don't create fresh scannable admission credentials or alter signed barcodes.
3. Group authorized tickets for the family in one `ticket_wallet`, with user-friendly labels and minimal child data. Where issuer offers offline display, store encrypted offline asset within allowed terms.
4. If venue arrival is confirmed or near in opt-in geofence, send an in-chat prompt to open tickets, plus entry gate directions from permitted source.
5. After admission, present the next itinerary step without assuming successful scanning unless verified/user-confirmed.

**Card:** `ticket_wallet`, multi-ticket swipe, `Show next ticket`, `Open official app`.  
**Tools:** media/document parsing, ticket storage, issuer status when available, itinerary.  
**Permissions:** family member access, sharing/forwarding policies, ticket security.  
**Risks:** expired QR, screenshots disallowed by issuer, child access, leakage on lock screen, changed gate, fraudulent ticket generation.  
**Tests:** duplicate child tickets, one ticket voided, no network at gate, name mismatch, user denies sharing.

## S24 — Mall indoor navigation using nearby shops as landmarks

**Stage:** FUTURE research, manual guided pilot · **Persona:** indoor visitor · **Trigger:** “I need Apple Store in Dubai Mall, but GPS isn't working.”

**Agent loop:**
1. Confirm venue, desired store/POI and known floor/entrance. Check currently licensed venue tenant directory and route graph; **do not assume shop placement from generic model knowledge**.
2. If location is unknown, present candidate nearby *verified* shops or landmarks and ask “Which of these can you see?” One to three disambiguating questions narrow the starting graph node.
3. Confirm inferred position, then compute a route respecting accessible lifts, escalators, closed corridors, floor links, shops and source freshness.
4. Render **Dubai-io-styled schematic** only when map licenses permit derivative presentation; otherwise link official maps or show textual directions with required attribution.
5. Each `Next` advances **instruction progress**, not automatically verified physical position. Ask user to confirm recognizable next landmark and allow `I'm somewhere else` corrections.

**Card:** `indoor_route_step` with “You seem to be near [confirmed landmark]” and a minimal floor graphic when available.  
**Tools:** venue directory, spatial graph, landmark matcher, route planner.  
**Permissions:** foreground location optional, manual landmark input sufficient.  
**Risks:** incorrect floor/shop, tenant moves, map copyright, stair-only routing, accessibility, venue photography/safety.  
**Tests:** same chain on multiple floors, user misidentifies shop, store relocated, escalator closed, no venue graph, user cannot walk stairs.

## S25 — Automatic parking memory: vehicle → walking → photo → recall

**Stage:** FUTURE native; manual parking-save MVP/PILOT · **Persona:** vehicle user at mall/attraction · **Trigger:** probable parking event, optionally driver-initiated.

**Agent loop:**
1. With **explicit** OS permissions, native device may observe `in_vehicle → stationary → walking` and optional car Bluetooth disconnect near a known destination; raw motion is locally processed where practical.
2. Emit a low-resolution `parking.possible_stop` **hypothesis**. Do not assert driver ownership, exact bay or floor. Check notification frequency, confidence, and whether a recent prompt was dismissed.
3. Send: “Did you just park? Save a photo of your spot so you can find it later.” Provide camera and manual inputs: venue, floor, section/color, pillar number and vehicle label optional.
4. User confirms and saves photo (with consent, encrypted storage and expiry). Show “Saved: Fashion Parking, P3, Pillar [user-entered].” The example label is not a claimed real location.
5. Later “Where did I park?” retrieves user-confirmed details and photo; optional official route to parking entrance and manual landmark navigation indoors.
6. Provide `Delete`/`Not my car` controls. False positives must not persist a parking memory.

**Card:** `parking_photo_prompt` → `parking_recall`.  
**Tools:** native OS activity/geofencing where available, user camera, memory vault, optional venue maps.  
**Permissions:** background motion/location; photo; retention; never default-enable.  
**Risks:** motion false positives, passenger gets out, underground drift, battery drain, unrelated private photos, venue shooting rules.  
**Tests:** traffic jam, taxi drop-off, two cars, photo without metadata, manual mode, airplane mode, memory deletion.

---

# PART II — 10 TOURIST CASE STUDIES: OPERATIONAL DECOMPOSITION

These correspond to the user's later ten-scenario proposal. They **extend** S cases with cross-provider choreography, UI milestones, and an honest path from a minimal prototype to integration maturity. Their IDs are `T01`–`T10`; do not create duplicate data domains or agent classes for each one.

## T01 — Skydive + beach + parking + gear + cleaning (`S02`, `S16`, `S20`)

**User intent:** “I want a jump tomorrow morning, beach afterward, and to avoid logistical surprises.”  
**Proposed cross-domain journey:** operator booking discovery → weather context → routing/parking → shopping fulfillment → optional laundry quote → reminders.

**Decomposition and truthful states:**

1. `[PENDING_OPERATOR]` Query only permitted published slots or open the official Skydive booking flow. Record exact operator booking number *after* confirmation. Wind is an input to operator decisions, not an app-issued safety clearance.
2. `[ROUTE_READY]` Calculate hotel→drop-zone route, likely arrival window and parking guidance. Parking-zone identification requires actual on-site/official data; even a published zone does not prove an empty reserved space. Surface official payment handoff.
3. `[SHOPPING_OPTIONS]` Search legitimate retailer feeds for optional towel, sunscreen, pouch and confirm delivery promise **for the exact order/address/checkout**. Never assert generic next-day shipping applies to this specific hotel.
4. `[QUOTE_REQUESTED]` Ask whether user wants post-event laundry; if yes, call an approved merchant quote request with a *real* accepted offer. Default remains `Not requested`.
5. `[ACTIVITY_DAY]` Check time constraints and actual weather/merchant changes, then send one consolidated status message with drill-down rather than four push notifications.

**Action card UX:** header `Tomorrow's adventure`, four task rows with independent statuses, subtotal only for known/quoted items, `Review remaining actions`. A fabricated bundle total or `Approve all` purchase across disconnected vendors is prohibited.

**MVP:** route + official activity handoff + packing plan + one registered cleaning-service request.  
**Full integration gate:** signed operator/parking/e-commerce/merchant APIs, legal use rights, idempotent execution, refund/error handling, and actual booking proofs.  
**Eval:** weather cancellation, delivery arrives late, no parking, unconfirmed laundry, two people with different eligibility.

## T02 — DXB airport step-guide + late arrival (`S01`, `S21`–`S23`)

**User intent:** “I'm exhausted at 2 AM. Guide me from airplane to hotel without confusion.”  
**Proposed journey:** flight/terminal confirmation → immigration advisory → baggage display check → connectivity → onward transport decision → hotel arrival state.

**Decomposition:**

1. `[LANDED_OR_USER_CONFIRMED]` Use flight feed where authorized; otherwise manually check in. Connecting to airport Wi-Fi alone does not prove a flight landed or user is inside a specific restricted area.
2. `[ENTRY_GUIDE]` Render one instruction per stage, with current official Smart Gate criteria. Avoid fabricated time saved, left/right gate claims, or passport eligibility from nationality alone.
3. `[BAGGAGE]` Show actual belt only from authentic flight-linked data. Otherwise “Check arrival displays for belt assignment.”
4. `[CONNECTIVITY]` Show licensed/official SIM options, not guaranteed free data allocations.
5. `[TRANSFER]` Compare train/taxi/rental by time, luggage, child safety seats, last service and hotel destination; use live/cited fares as estimates until checkout.
6. `[HOTEL]` On confirmed departure or arrival, offer check-in reminder and optional food near hotel, not another full-page app.

**Card UX:** `Arrival journey · Stage 3 of 5` with concise copy and `Next`/`Go back`/`Not here`, plus a final transport choice.  
**MVP:** user-driven stages + permitted mapping and fare guidance.  
**Full gate:** facility coordinates, belt data, booking API, consented geofence/mobile capability, airport branding license.  
**Eval:** diverted to DWC, roaming off, Metro unavailable, inaccessible route, no bag, user changes hotel.

## T03 — Rental car parking, mParking and toll awareness (`S08`, `S25`)

**User intent:** “Avoid parking mistakes, toll surprises and roaming-SMS issues.”

1. Detect **possible** stop and user-select parking task. GPS can place the user near a curb but not reliably identify the exact parking code; ask for a photo/sign or official zone confirmation.
2. Retrieve current Parkin/RTA payment options, tariffs and allowed payment mechanisms; show official app/web handoff if no approved direct payment connector.
3. Ask user to specify planned parking duration. If purchased through an authorized API, store proof/expiry and remind before it ends. If handoff only, say “Payment status unknown” until receipt is provided.
4. Compare toll-free versus tolled route with **current dynamic toll rules**; never apply a fixed AED 4 to all gates and hours.
5. For rentals, explain that tolls/parking fines may be billed by the agency later; locate the agency's actual contract terms.

**Card:** `parking_zone_confirmation` → `parking_payment_handoff` → `parking_expiry_reminder`; optional `route_toll_summary`.  
**MVP:** official tariff explanation, expiry reminder after user-confirmed purchase.  
**Partnership gates:** direct parking payment, account reads and toll recharge authorization.  
**Eval:** international number, paid-zone edge, changing peak toll, user is passenger, off-street private parking.

## T04 — Taxi/Metro lost property urgent workflow (`S11`)

**User intent:** “Recover important property quickly even without ride number.”

1. Classify urgency: passport, wallet, prescription, phone, personal safety. Surface the appropriate immediate actions for severe situations.
2. Search recent authorized trip evidence (ticket, receipt, chat, geotemporal history **only with consent**) and ask no more than essential clarifying questions.
3. Prepare incident: mode, start/end, approximate time, payment/receipt, item description and preferred contact. Avoid unnecessary full passport details.
4. Navigate to official current lost-property reporting; if direct integration approved later, submit *once* with idempotency and store real case ID.
5. Remind user to follow up, log actual response and mark recovery only upon proof/user confirmation.

**Card:** `recovery_case` with case details, `Copy report`, `Open official reporting`, `Set follow-up`.  
**MVP:** evidence organizer + official handoff.  
**Full gate:** reporting API and actual return logistics contract.  
**Eval:** no trip proof, lost phone is current device, wrong RTA/operator jurisdiction, duplicate official report, user finds item later.

## T05 — Dubai Mall lost-car rescue (`S12`, `S24`, `S25`)

**User intent:** “Find the exact parking area in a huge mall.”

1. The optional native mobile bridge detects an *inferred* car-to-walk transition; ask to save a photo and label.
2. Capture user-entered floor, pillar/zone color and entrance; extract text from photo only as a **suggestion for correction**, not proof.
3. When user wants to return, retrieve record, show original photo and manually confirmed labels.
4. Optional indoor directions start from user-selected current shop/level using a current authorized venue graph, plus official Find My Car if available.
5. Show uncertainty if building map lacks a route; fall back to official mall directory/staff assistance.

**Card:** `parking_photo_prompt` / `parking_recall` / `indoor_route_step`.  
**MVP:** save and retrieve parking photo+floor/pillar.  
**Full gate:** licensed routing graph and phone OS trigger support.  
**Eval:** repeated entrances, underground GPS drift, floor changed, pillar partially visible, user parked in hotel valet.

## T06 — Nightlife, lawful retail guidance and safe driver (`S09`)

**User intent:** “Plan dinner/lounging and safe transport without legal surprises.”

1. Clarify date/time/party and transport needs; surface age/venue restrictions only from venue/official source. Avoid collecting passport by default.
2. Search venues via permitted reservation source; list authentic time slots, minimum spend and cancellation policy. Don't invent bookings.
3. If user asks about retail alcohol, guide to current applicable official/licensed-retailer process and age rules. A tourist license cannot be “issued by the agent” without a formal authorized flow.
4. Offer taxi/designated-driver choices. If user is driving, encourage safe non-driving alternative and ask before scheduling any driver.
5. Status timeline shows `Table pending/confirmed` and `Driver pending/confirmed` separately.

**Card:** venue card + `safe_return`, maybe official licensing handoff.  
**MVP:** venue discovery and safe return planning.  
**Full gate:** booking and driver dispatch integration, verified license process.  
**Eval:** venue cancels, no driver at proposed hour, alcohol not relevant, unverified venue policy.

## T07 — Heat illness, emergency help, insurer and pharmacy (`S07`)

**User intent:** “I'm ill in my hotel and need safe, legitimate help.”

1. Detect high-risk symptoms and prioritize urgent medical advice/official emergency service over commerce.
2. Ask only actionable questions: condition severity, basic safety context, current location if user wishes, emergency contact availability. No unsupported diagnosis.
3. Present approved nearby care/telehealth access and practical insurance verification options; match insurer-network lists only where accessible/verified. A network listing does not guarantee exact claim coverage.
4. Medication delivery requires licensed pharmacy and lawful prescription. The companion may display legitimate provider links; never generate doctor-stamped invoices/sick notes itself.
5. Help upload genuine documents into a user-owned reimbursement packet, with explicit sharing.

**Card:** `care_options`, `insurance_handoff`, `document_checklist`; emergency action prominent when needed.  
**MVP:** conservative care navigator and official link.  
**Full gate:** licensed clinical/insurer/pharmacy partners.  
**Eval:** severe symptoms, no local insurance, international insurer unknown, prescription restricted, vulnerable child.

## T08 — Sheikh Zayed Grand Mosque day-trip preparation (`S14`)

**User intent:** “Avoid wasted travel due to entry/dress-rule surprises.”

1. Fetch current visitor times/registration and official access rules; display closure uncertainty for special occasions.
2. Compare intercity transit, hired car and bus connection for user's party/access needs.
3. Offer culturally respectful dress guidance based on current rules, optionally reviewing user's own outfit photo with consent, explicitly `Advisory only`.
4. Link genuine official visitor pass workflow and retain *real issued document*, not generated entry QR.
5. Remind before trip about confirmed documents, accessible entrance and route.

**Card:** `day_trip_plan` + `entry_checklist` + issued `ticket_wallet` if available.  
**MVP:** official preparation and route; future photo check research.  
**Full gate:** authorized pass/availability endpoints.  
**Eval:** last-minute visitor schedule change, inaccessible path, user with limited mobility, no pass issued, wrong place/time.

## T09 — Desert safari operator comparison and scam avoidance (`S15`)

**User intent:** “Find an authentic, transparent desert experience at a fair price.”

1. Capture location, ages, activity preferences, budget and pickup expectations.
2. Normalize inclusions across participating offers: dune ride, food, transfer, duration, kids restrictions, optional paid activities, cancellation.
3. Show actual trade-license evidence or permitted official lookup when available; otherwise label `not verified by Dubai-io`, not `government certified`.
4. Separate authentic attributable community reviews from merchant marketing copy; never generate reviews or fake social proof.
5. Contact/quote via authorized service layer, verify discount before displaying coupon, retain quote terms for possible dispute.

**Card:** `safari_comparison` plus `trust_checklist`, followed by quote action.  
**MVP:** provider checklist, sourced comparison, quote request.  
**Full gate:** official license lookup and live supplier inventory.  
**Eval:** listing missing safety terms, misleading inclusions, canceled trip, operator identity conflict, fake discount.

## T10 — Departure VAT refund and Europe cross-over (`S13`)

**User intent:** “Recover eligible shopping tax refunds without forgetting airport steps.”

1. Separate jurisdiction from outset: UAE versus countries in Europe; **do not assume London/UK and EU share the same traveler refund system**.
2. Import relevant receipts as user documents; identify potential tax-free operator enrollment, purchase date, receipt status and departure airport.
3. Compute potential refund only if eligibility and current operator deductions are known. Flag unknown items explicitly.
4. Create airport checklist specifying validation sequence and when documents/goods must be available, citing current operator/airport source—not fixed kiosk coordinates from model memory.
5. Remind at the appropriate stage and show genuine source receipt QR if present. Mark `Validated` only with authorized evidence.

**Card:** `refund_checklist`, `ticket_wallet` for original receipts, `departure_reminder`.  
**MVP:** UAE-specific receipt organizer, current rules and reminders.  
**Future:** jurisdiction adapters for each country, not one global refund engine.  
**Eval:** domestic resident, non-enrolled receipts, dual-airport transit, altered kiosk, refunds refused, duplicate invoices.

---

# PART III — ADDITIONAL EXPANSION IDEAS (NEW CANDIDATES)

These have new `X` IDs and should enter `03-SCENARIO-LIBRARY.md` only when the product owner approves them. They are inspired by the city-companion vision, not derived from confirmed integrations.

## X01 — Broken phone: find a repair shop and protect personal data

**User:** “I broke my iPhone screen in Downtown. Can it be fixed today?”  
**Agent:** detect manufacturer/model/urgent needs; compare nearby qualified providers, honest price ranges, part type, turnaround and warranty; request an actual quote; remind to back up data and avoid sharing device passcodes unnecessarily.  
**Card:** `repair_comparison` with `Ask exact quote`.  
**Value:** practical resident/visitor issue; a registry-driven L1→L3 expansion.  
**Boundary:** no guaranteed genuine parts, 1-hour repair promise, or Apple authorization without documentation.  
**Test:** model unknown, waterproofing issue, no same-day stock, traveler flies tonight.

## X02 — Apartment cleaning with optional recurring schedule

**User:** “Clean my apartment Friday before guests arrive.”  
**Agent:** gather size, time, supplies, pets, special requirements and address; search providers; ask for exact final quote; schedule actual booking only with confirmed provider; reminders for building access. Repeat schedule requires user opt-in and clear cancellation.  
**Card:** `service_comparison`, `quote_approval`, `action_status`.  
**Boundary:** do not send building access PIN automatically; avoid claiming staff vetting without merchant proof.  
**Test:** merchant staff unavailable, keys/access restricted, cleaners delayed, address changed.

## X03 — Affordable/midrange/premium product discovery

**User:** “Where can I buy a laptop backpack, cheap but not low quality?”  
**Agent:** ask budget, features, willingness to travel; compare legitimate prices and stock claims among online/local merchants, show `budget / balanced / premium` options; provide directions or retailer handoff; cite live data and warranty information.  
**Card:** `product_compare`, `store_route`.  
**Boundary:** no fake stock, counterfeit detection certainty or fabricated in-store discounts.  
**Test:** listing discontinued, budget AED 100, warranty excluded, seller in another emirate.

## X04 — Community post to real-world service action

**User:** “Someone recommended an affordable tailor in our Marina discussion—who was it?”  
**Agent:** search only public/permitted group posts, extract relevant cited recommendation, resolve named tailor to real business identity where possible, compare with verified merchant listing, and ask before messaging provider.  
**Card:** `community_summary` + `provider_card`.  
**Boundary:** source attribution, respect deleted posts and blocked users, treat opinions as unverified.  
**Test:** two tailors same name, post deleted, merchant denies connection, malicious prompt embedded in comment.

## X05 — Clinic fit: “Does my insurance cover this?”

**User:** “I need a dermatologist near Marina; I have [insurer/network].”  
**Agent:** with consent, inspect plan metadata and permitted insurer network sources; find licensed providers and likely specialty; show insurer contact/eligibility check; direct urgent cases to appropriate medical care.  
**Card:** `care_provider_match` with explicit `coverage not confirmed`.  
**Boundary:** coverage depends on exact plan, treatment, approvals and insurer confirmation; sensitive health data needs protections.  
**Test:** expired insurance, cash-pay clinic, excluded procedure, no verified insurer API.

## X06 — Electric vehicle charging and parking

**User:** “I'm driving to Dubai Mall; find EV charging I can actually use.”  
**Agent:** vehicle compatibility, connectors, verified available chargers (if authorized real-time feed), tariffs and route; reserve only if provider explicitly supports booking; otherwise open operator app and remember time to move car.  
**Card:** `charging_options`, `parking_reminder`.  
**Boundary:** parking/charger availability cannot be invented; occupancy feed freshness shown.  
**Test:** connector incompatible, charger offline, garage inaccessible, plan changes.

## X07 — Flight cancellation and missed connections

**User:** “My flight is cancelled and I have a nonrefundable hotel tonight.”  
**Agent:** confirm airline/status from legitimate source; separate airline rights and hotel terms by jurisdiction/contract; draft airline/hotel message; search route alternatives; save evidence and actual rebooking numbers.  
**Card:** `disruption_plan`, `evidence_bundle`.  
**Boundary:** no claims of automatic refund eligibility or actual rebooking without provider receipt.  
**Test:** delay not cancellation, two airlines, international transit visas, no internet, hotel refuses.

## X08 — Memory correction and privacy controls

**User:** “Forget that I like rooftop bars and stop asking where I am.”  
**Agent:** identify relevant saved preference and location subscription, explain exact impact, update deletion/opt-out controls, clear pending triggers and derived profile in appropriate systems, respect group/private data boundaries.  
**Card:** `memory_permissions` with preview and confirmation.  
**Value:** demonstrates trustworthy AI companion, not just memory accumulation.  
**Test:** preference inferred from old chat, scheduled alert pending, data retained by merchant, multiple devices.

## X09 — Heat-adaptive family day

**User:** “We have toddlers; can we visit an outdoor attraction this afternoon?”  
**Agent:** retrieve heat and forecast, identify shade/cooling/accessibility, suggest earlier/later or indoor alternatives, review stroller travel and travel time; provide choices, not health guarantees.  
**Card:** `family_plan`, `weather_context`.  
**Boundary:** no precise on-site temperature without data; no medical claims.  
**Test:** heat alert, venue closed, stroller barrier, no nearby indoor option.

## X10 — Accessible route across transport and venue

**User:** “I use a wheelchair. Get me from my hotel to a museum without stairs.”  
**Agent:** confirm actual access preferences, query accessible transport paths/elevators and venue entrances, label unknown lift service states, verify with operators as needed; provide contingency and official contact.  
**Card:** `accessible_route` with accessible segments and warnings.  
**Boundary:** routing engine must not infer accessible features from a generic walking route.  
**Test:** lift broken, construction diversion, inaccessible taxi, venue door closed.

## X11 — Verified community help without fake seeding

**User:** “I just moved to JVC. Which areas are good for affordable groceries?”  
**Agent:** combine clearly attributed real member experiences with current merchant/store locations; highlight disagreement or stale reports; invite verified residents to contribute; allow corrections.  
**Card:** `community_digest` + `store_options`.  
**Boundary:** no bot impersonating residents; reputation signals must reflect actual behavior and moderation.  
**Test:** manipulated reviews, sponsor conflict, outdated post, harmful rumor.

## X12 — Move-in day: utilities, cleaning, deliveries, building rules

**User:** “I'm moving into a new apartment next Saturday.”  
**Agent:** checklist of user-confirmed tenancy/permit conditions, utilities account links, mover/cleaner quotes, elevator booking inquiry, address update, deliveries and parking; preserve source provenance.  
**Card:** `move_checklist` with subtask states.  
**Boundary:** no unauthorized DEWA activation, Ejari registration or landlord interactions; requirements differ by building and contract.  
**Test:** move date changes, landlord form missing, weekend access unavailable, user not yet tenant.

## X13 — Dinner booking followed by changing schedule

**User:** “We want dinner at 8, but the kids may be tired after the aquarium.”  
**Agent:** search real reservable options and meal suitability; show exact provider-verified availability; book with approval, track reference; if visitor later asks to move, check provider's modification policy and obtain confirmation.  
**Card:** `reservation_options`, `action_status`.  
**Boundary:** no claiming a reservation based on opening a venue URL.  
**Test:** no times available, deposit required, date timezone mismatch, venue cancellation.

## X14 — Multilingual help resolving a merchant dispute

**User:** “The shopkeeper only speaks Arabic. Tell them the shoes I bought are defective.”  
**Agent:** translate user-reviewed message into Arabic/English, optionally include receipt and desired remedy, avoid insulting/defamatory allegations, ask approval to send via authorized channel; store translation with originals for evidence.  
**Card:** `translation_draft`, `evidence_bundle`.  
**Boundary:** translation is not legal certification; no automatic merchant message without permission.  
**Test:** dialect ambiguity, source contains incorrect assumption, merchant responds with unexpected terms, user revokes consent.

---

## X15 — Real messaging with search and controlled AI participation

**User:** “Ask Ahmed and Sara if they want breakfast Saturday, and show me their replies.”  
**Agent:** create a real group chat (not a simulated conversation), select recipients from explicitly authorized contacts, compose the invitation for user review, send through Dubai-io's own messaging backend when those accounts exist, and present delivery/read statuses only from messaging records. Summarize responses in the group only after member permissions allow AI access.  
**Storage:** conversation, membership, per-message sender, text/media refs, timestamps, edit/delete events, moderation flags and retention. Realtime delivery via WebSocket/SSE or approved messaging system.  
**Card:** `group_invitation`, `poll` and `conversation_summary`.  
**Boundary:** never use AI to impersonate contacts; never treat an unsent draft as an invitation; encryption may require client-side consented AI processing.  
**Tests:** recipient not registered, blocked user, failed delivery, group exit, missing consent, deleted message and reconnect after offline.

## X16 — Search old conversation and share a personal media moment

**User:** “Find the video I sent Ahmed when we spilled coffee and send it to our family group.”  
**Agent:** respect access to the original chat, search file/message metadata and permitted video-index; verify event candidate and show thumbnail with timestamp; ask the owner to confirm media identity, rights and target group; share via genuine messaging backend with an actual sent message ID.  
**Card:** `media_moment` → `share_approval` → `message_status`.  
**Boundary:** if the original media is end-to-end encrypted, backend search cannot silently decrypt; user may have to enable on-device indexing or manually select a file.  
**Tests:** media deleted, user lacks rights, group has new members, similar videos, large upload, encryption key unavailable.

## X17 — AI-assisted merchant onboarding, live new category

**Operator/merchant:** “Add my ironing pickup service to Dubai-io; here's my service spreadsheet and API description.”  
**System:** merchant application → identity/legitimacy review → CSV/schema extraction by AI → normalized service/category/area/prices/terms → capability manifest proposal → safe fixture generation → sandbox invocation/permission tests → human approval → versioned registry publish. Once published, the same end-user chat can discover the service with no new custom screen.  
**Cards:** internal `provider_validation_report`, `capability_preview`, `publish_approval`; user-facing `service_comparison`.  
**Boundary:** untrusted merchant documents must not override system prompts or deployment rules; AI-generated adapter code cannot auto-deploy to production. Capability level L4/L5 requires genuine provider contract and validation.  
**Tests:** malformed CSV, ambiguous prices, duplicate company, invented API endpoint, schema-breaking API update, attempted malicious tool URL, unapproved discount.

## X18 — Low-connectivity itinerary and offline-safe essentials

**User:** “We'll be underground in the Metro; I don't want to lose our directions or tickets.”  
**Agent:** cache permitted, user-requested itinerary/checklist, previously issued tickets according to issuer policy and most recent route summary with data-age banner. Queue only safe local note-taking actions while offline; retry external execution after reconnection **with user confirmation**.  
**Card:** `offline_trip_bundle`.  
**Boundary:** live prices, closures and booking status cannot be trusted while offline; never queue payment invisibly.  
**Tests:** ticket QR requires live refresh, expired route, phone storage pressure, device shared, disconnected mid-booking.

## X19 — Proactive household/visitor service after a real event

**User:** “I spilled coffee on the hotel carpet. What should I do?”  
**Agent:** ask whether anyone is injured and whether venue rules require notifying staff; provide safe non-destructive first steps from appropriate source, offer to draft a truthful note for hotel management, and suggest optional licensed cleaning provider only if hotel permits it. Retain photos with consent for possible damage/deposit discussion.  
**Card:** `incident_help`, optional `service_quote`, `evidence_bundle`.  
**Boundary:** don't recommend secretly bypassing hotel procedures or claim insurance coverage.  
**Tests:** expensive carpet, hotel demands fee, health/safety hazard, no service available, user does not want storage.

## X20 — Community trust and moderation workflow

**User:** “A local group says this rental operator scams everyone. Is it true?”  
**Agent:** retrieve dated posts and actual reports only from permitted scope, clearly separate anecdote and verified findings, avoid stating allegations as fact, identify relevant published official license/complaint checks, provide safe buying checklist. Users can report malicious or false content to human moderation.  
**Card:** `community_summary` with cited original discussion and `trust_checklist`.  
**Boundary:** false accusations, defamation, brigading, fake reviews, private identities, legal sensitivity.  
**Tests:** one anonymous allegation, commercial competitor attack, deleted post, unverified screenshot, prompt injection inside forum comment.

---

# PART IV — CROSS-SCENARIO STORIES: WHAT MAKES THIS A COMPANION

## Journey A — Family snorkeling day, 36-hour conversation

A single chat should evolve across time and services; **it must not become five separate mini-apps**.

| Relative time | Trigger | Companion message | Card/action | Evidence required |
|---|---|---|---|---|
| Previous evening | User saves trip for next day | “I've saved your snorkeling trip. Want a packing checklist?” | `trip_checklist` | User-confirmed itinerary |
| Day before | Real merchant order status or user estimate | “Your package is expected between 2 and 7 PM. Want tracking?” | `delivery_window` | Provider event or user-provided estimate |
| Night before | User-specified reminder | “Trip tomorrow: check confirmed tickets, gear, transport and any required documents.” | `notification_reminder` | Confirmed trip details |
| Departure minus 10 minutes | Scheduled user opt-in | “Leaving soon. Your checklist has two incomplete items.” | `trip_checklist` | Accurate event schedule |
| Possible exit from home | Optional native motion/geofence | “Looks like you're heading out. Has the trip started?” | `journey_status` | Inferred OS event, user confirmation |
| Approaching venue | Optional location/route event | “Would you like to open your group's tickets?” | `ticket_wallet` | Legitimately issued and authorized ticket assets |
| Parked near destination | Possible activity transition | “Did you park? Want to save a picture of the bay?” | `parking_photo_prompt` | Confirmation; user photo |
| Walking inside venue | User asks | “Which entrance or nearby shop can you see?” | `indoor_route_step` | Licensed or officially sourced venue data |
| Returning to car | User requests | “Here is your parking photo and saved pillar.” | `parking_recall` | Saved user data |
| After trip | User opt-in | “Would you like to save highlights or review your experience?” | `media_summary` / `community_post_draft` | Media permissions and editorial approval |

**Essential design:** the assistant does not repeatedly announce where it thinks the user is. It responds to user-owned itinerary state, known provider events and carefully controlled signals. The user can dismiss any unhelpful suggestion and correct false inference.

## Journey B — Laundry order → pickup → damaged shirt → consumer resolution

1. User requests ironing via `S16` and receives a transparent quote card.
2. Merchant acknowledges and **actually** confirms the requested pickup; confirmed order/terms are saved.
3. A real provider window update creates an in-chat message. The app never fabricates delivery tracking.
4. User reports damage. The companion retrieves authorized order and original agreed terms, asks for photo and service receipt, and creates a neutral timeline.
5. `S10` official-source RAG retrieves relevant current consumer guidance; the agent explains where rules are uncertain.
6. User previews an editable complaint, removes irrelevant private details and authorizes transmission or official handoff.
7. Follow-up reminders attach to the same case; resolution remains `UNKNOWN_STATUS` unless externally confirmed/user-reported.

**Why it matters:** demonstrates the combined value of memory, service registry, execution, provider events and civic RAG without needing a bank or government transaction API.

## Journey C — Reddit-style recommendation → meetup → actual café offer

1. User asks for an inexpensive breakfast in JBR.
2. AI searches approved merchant data and authentic community content, returning attributed opinions rather than synthetic endorsements.
3. User selects café and proposes an opt-in breakfast meetup in an existing Dubai-io group.
4. Members vote on time, with group preferences only if members authorized sharing.
5. An actual café partner (if any) issues a valid voucher to an eligible user; the signed token can be displayed, but not forged.
6. Following visit, companions are invited—not forced—to contribute an honest, clearly human-authored review.

**Why it matters:** the WeChat service layer and Reddit community become reciprocal sources of utility. Empty social graphs remain a launch risk; invitations and real contributions are necessary.

## Journey D — Airport delay → hotel route invalid → replanning

1. User's arrival is delayed (authentic flight event or user confirmation).
2. Agent checks whether the existing Metro itinerary still fits the latest permitted timetable.
3. If not, user sees one actionable message: “Your previous Metro plan may no longer work at your arrival time. Compare alternatives?”
4. Agent produces options with current evidence, approximate total cost and child/luggage/accessibility constraints.
5. User chooses; booking remains pending until the provider actually confirms.
6. Companion keeps only relevant arrival information, not every raw location point.

**Why it matters:** genuinely proactive, yet low-friction and honest about uncertainty.

## Journey E — Video memory + social share + venue context

1. User asks, “When did I spill my coffee in Dubai Mall?”
2. After explicit permission, companion searches own uploaded/accessible videos and narrows candidate segments.
3. It visually verifies the candidate and returns a clip around the actual event with approximate timestamp and an uncertainty label.
4. User says, “Send this to our friends in the breakfast group.”
5. Companion asks for message/share confirmation, then sends via authenticated chat if group/membership rights are valid.
6. Later, the user can remove that video's embedding index without losing unrelated chats.

**Why it matters:** the memory and messaging layer are meaningful product capabilities, not disconnected novelty demos. This is **future-stage**, not required for the first contest build.

## Journey F — A new laundry provider joins without a new end-user app

1. Merchant submits a real service listing and approved structured data.
2. AI integration assistant proposes category mapping, normalized pricing fields, service-area polygons, capability contracts, typed card mapping and unit tests.
3. Human reviewer verifies business identity, commercial offer and allowed operations.
4. Registry publishes a versioned `laundry.request_quote` capability.
5. End-user asks “Iron shirts tomorrow” and receives the new provider in the **existing** service comparison card.
6. The merchant dashboard receives an actual quote request; responses update the user's existing chat.
7. If provider later adds a verified booking API, its capability may be promoted L3→L4 after tests/approval, without redoing the consumer navigation.

**Why it matters:** this is Dubai-io's expandable platform thesis in one demonstrable workflow. Success means a new business can be integrated with less marginal UX work, **not** that every booking integration is free.

---

# PART V — SPECIFICATIONS FOR IMPLEMENTATION AGENTS

## 1. Canonical event and message model (illustrative)

```json
{
  "event_id": "evt_demo_42",
  "event_type": "trip.departure_soon",
  "occurred_at": "2026-10-09T08:50:00+04:00",
  "user_id": "demo_user",
  "subject_ref": "trip_demo_9",
  "origin": "user_confirmed_itinerary",
  "confidence_class": "confirmed",
  "required_permission": "trip_reminders",
  "dedupe_key": "trip_demo_9:departure_10min",
  "expires_at": "2026-10-09T09:05:00+04:00",
  "payload": {"minutes_until_planned_departure": 10}
}
```

Processing: authenticate emitter → validate schema → authorize subject/user → normalize timestamps → dedupe → evaluate consent/quiet hours/relevance → create assistant message in persistent chat → optionally send push → record delivery status. Model involvement is limited to context-sensitive wording or selection of safe typed content; **the event system is deterministic and auditable**.

## 2. Example multi-action plan payload

```json
{
  "plan_id": "demo_plan_17",
  "user_goal": "Prepare a beach day with the family",
  "source_status": "illustrative_demo",
  "subtasks": [
    {
      "id": "activity",
      "capability": "operator.booking_handoff",
      "status": "OPTIONS_READY",
      "execution_level": "L2_CONTACT",
      "proof": null
    },
    {
      "id": "transport",
      "capability": "maps.route",
      "status": "OPTIONS_READY",
      "execution_level": "L1_DISCOVER",
      "proof": null
    },
    {
      "id": "laundry",
      "capability": "laundry.request_quote",
      "status": "AWAITING_APPROVAL",
      "execution_level": "L3_QUOTE",
      "proof": null
    }
  ],
  "card_type": "activity_plan",
  "notes": ["Provider bookings and prices are not confirmed"]
}
```

Do not consolidate independent vendor payments into `single_click_checkout` until every constituent transaction, price, cancellation term, authorization and order reference has a real supported protocol.

## 3. Indoor wayfinding graph contract (proposed)

```yaml
venue_id: venue_example
source: licensed_venue_directory_required
source_version: unknown
nodes:
  - id: entrance_demo
    floor: G
    kind: entrance
    label: Example entrance
  - id: lift_demo
    floor: G
    kind: lift
    label: Example lift
edges:
  - from: entrance_demo
    to: lift_demo
    accessible: true
    closed: false
user_anchor:
  type: user_confirmed_landmark
  node_id: entrance_demo
  confidence: confirmed
route_status: DEMO_ONLY
```

Venue data is not automatically transferable from a picture into a reliable navigable graph. A map screenshot/color transformation is not a license, nor does it prove floor-level topology. Construction, tenant changes, accessibility and store directions need source versioning and updates.

## 4. Parking candidate contract (proposed)

```yaml
candidate_id: parking_demo_21
trigger:
  type: in_vehicle_to_on_foot
  source: opted_in_native_device_signal
  confidence: inferred
context:
  near_known_destination: true
  gps_accuracy_meters: unknown
user_response: pending
memory:
  save_only_after_confirmation: true
  venue: null
  floor: null
  pillar: null
  photo_asset_id: null
  expires_at: configurable
```

No background location, raw accelerometer stream, or persistent parking record should be enabled merely because a user once asked for directions.

## 5. Provider integration maturity tests

| L-level | Required before claiming capability | Negative test |
|---|---|---|
| L1 discover | Legitimate listing, fresh source, category/location, permitted storage | Remove/stale a listing; no fabricated availability |
| L2 contact | Valid official link, callable contact path, safe data minimization | Broken link, phishing endpoint, wrong merchant |
| L3 quote | User approval, real request receipt, merchant quote status | Timeout, provider ignores request, quote expires |
| L4 execute | Authentication, confirmed price/terms, user approval, idempotent adapter, provider booking/order reference | Payment succeeds but order fails; retry does not double book |
| L5 fulfill | Authorized webhooks/status, cancellation/refund semantics, audit trail | Duplicate webhook, out-of-order events, disputed completion |

## 6. Model and retrieval responsibilities

| Function | Deterministic software | AI assistance | Source of authority |
|---|---|---|---|
| Event scheduling | Jobs/timezones/dedupe | Brief message phrasing | Trip/provider event |
| Motion detection | Native OS activity APIs | Optional context interpretation | User confirmation |
| Indoor routing | Verified POI graph and path algorithm | Landmark disambiguation | Licensed map + user anchor |
| Shopping comparisons | Product schema / verified prices | Query understanding, ranking explanation | Merchant/approved API |
| Legal guidance | Source ingestion/versioning + exact citation refs | Summarize and compare | Current official laws/portals |
| Chat | Membership, delivery, data access | Opt-in assistant in conversation | Actual message records |
| Video search | Timestamps, storage and retrieval | Semantic embeddings/verifier | Original media + consent |
| Execution | Approved adapters/status machine | Choose action, explain result | Provider-confirmed receipt |
| Merchant onboarding | Validation/sandbox/deploy gate | Schema mapping/test proposals | Human-approved data + API rights |

## 7. Trust, consent and abuse cases

- **Prompt injection:** merchant CSV, linked websites, community posts and uploaded documents are untrusted input. They cannot redefine tool permissions, disclose secrets, or approve transactions.
- **Payment and identity:** no storing card numbers or pretending to perform UAE PASS/OIDC verification unless actually authorized; use licensed processors for restricted payments/escrow.
- **Health:** emergency prioritization and licensed referrals; no diagnosis, invented prescription, fabricated medical stamps or unsafe allergy guarantees.
- **Children:** ticket sharing, family visibility, community age controls and location exposure must be tightly restricted.
- **Community:** no synthetic travelers or fake reviews presented as human; label AI curation; remove spam and harassment; distinguish firsthand experiences from claims of fact.
- **Law:** no uncited fines/penalties, fixed amounts across all years, conclusive eligibility determinations or live enforcement prediction. Preserve source version and jurisdiction.
- **Location and memory:** consent can be withdrawn, and derived indexes, event subscriptions and stale caches should be addressed in deletion policy.
- **Merchant rankings:** distinguish paid placement from relevance; avoid the companion secretly optimizing only for affiliate revenue.

## 8. Evaluation matrix for the MVP

| Scenario/test | Happy-path evidence | Must not happen |
|---|---|---|
| S16 Laundry request | Approved request; real merchant acknowledgement and response | `CONFIRMED` based only on model output |
| S10 Consumer dispute | Draft cites retrieved dated official source | Invented article, guaranteed remedy or automatic filing |
| S01 Arrival planning | Current grounded route options; manual step progression | Fictional baggage belt or queue time |
| S11 Lost item | Relevant official handoff and saved evidence checklist | Fabricated case ID or ride plate |
| S21 Delivery reminder | Message created once from trusted event/user schedule | Repeated spam, guaranteed delivery based on estimate |
| S13 VAT reminders | Eligible-looking receipts flagged accurately with uncertainty | Forged operator validation or invented kiosk |
| S25 Parking | Prompt as possible event, record after approval | Assert underground bay from GPS |
| S24 Wayfinding | User-anchored route in permitted venue graph | Hallucinated shop position/floor |
| S18 Media retrieval | Correct source video, approximately correct clip and permission check | Retrieval from unauthorized private chat |
| X17 Merchant onboarding | New L1/L3 provider appears using existing card with approved schema | AI deploys untested connector in production |

### Proposed release gates

**Prototype Gate:** User can chat; agent uses real tools or clearly labelled fixtures; cards render safely; at least one L3 merchant request and one civic knowledge workflow are testable; all outcomes preserve state.  
**Pilot Gate:** One verified real provider, secure auth, consent controls, accessible UI, source freshness/observability, tested failure paths and real user validation.  
**Production Gate:** Threat model, operational support, incident handling, legal review, provider contracts, data retention/deletion, moderation where applicable, and licensed regulated actions.

## 9. Research and partnership verification backlog

Use **official provider documentation and formal contacts**, not assumptions from marketing pages. Classify each integration `public_data`, `public_documentation_only`, `sandbox_granted`, `production_authorized`, `partner_required`, or `unavailable`.

| Dependency | Research/approval needed | Safe fallback |
|---|---|---|
| Airport stage/baggage/facilities | Airport operator authoritative data, terminal/facility license, permitted usage | Manual Next, airport display and official link |
| RTA transit, taxi, parking, tolls | Current tariff, feeds, commercial access and payment permission | Estimator + official payment/route handoff |
| Venue indoor geometry | Floor graphs, POI freshness, derivative map licensing | Official map/deep link, manual landmarks |
| Flights/activities | Availability/refund policies and approved bookable interface | Official booking link, no simulated confirmations |
| Food and travel offers | Real merchant agreement, expiry, redemption token/terms | Normal listing, no discount badge |
| Clinics/insurance/pharmacies | Licensed directories, insurer network, e-prescribing restrictions | Official phone/website handoff; emergency advice when indicated |
| Government status data | UAE PASS/GDRFA/ICP/DET auth, proper scopes, government authorization | Official portal handoff + user-entered date |
| Payments/escrow | Licensed provider, settlement, refund/dispute contracts | Outside-app provider checkout |
| VAT refunds | Actual operator eligibility, calculation, authentication, validation points | Receipt checklist, current official program instructions |
| Media models | Model capabilities/license, tested temporal precision, privacy design | Ordinary user-selected media search and playback |
| Native background events | iOS/Android permission modes, geofence budget and false-positive research | Foreground/manual check-ins and scheduled events |

## 10. Work mode / coding-agent execution instructions

When given this file alongside `01`–`05`:

1. **Do not translate each S/T/X use case into a separate standalone app, database or LLM agent.** Extract reusable domain services (`itinerary`, `events`, `service_registry`, `merchant_request`, `civic`, `memory`, `chat`, `venue`) and use stable API contracts.
2. Build and test the **shared primitives first**: session, typed cards, state machine, source registry, consent check, provider abstraction, event dedupe and action audit.
3. Select **at most three end-to-end MVP stories** from `05-CONTEST-MVP-AND-VALIDATION.md`; this file's many cases are future acceptance specifications, not scope commitments.
4. Implement only approved provider capabilities. For unavailable integrations, use honest external handoff or a **prominently labelled demo fixture** inside dev/test environments.
5. Keep the interface minimal and conversational. Display action cards with genuine source/status signals, avoid walls of text or a sub-app drawer per domain.
6. For each implemented workflow create: `scenario.yaml`, fixtures, happy/negative integration tests, source/license manifest, approval points, offline/failure flow, and one 45-second screen-recording demo.
7. Never let LLM prose mutate booking/payment status. A verified adapter response/event or explicit user-completion signal must drive state.
8. Track work in feature branches and keep unverified APIs/partnerships in a separate research backlog. Propose changes to the architecture documents only after review.
9. Build multilingual support from the schema/UI layer (English/Arabic first as a plan); avoid assuming every provider supports both languages.
10. Prefer useful real completion over ten visually polished fabricated transactions.

### Suggested first three Work implementation tickets

**Ticket 1 — Persistent companion:** FastAPI + PostgreSQL user/session/message persistence, simple chat UI, tool traces available for QA, typed card registry with one demo service comparison and consent management.

**Ticket 2 — Real merchant lifecycle:** one internally controlled demo laundry merchant dashboard, intake/listing/quote/acknowledgement events, idempotency and user-visible status transitions; simulate only clearly labelled data until a real pilot merchant is onboarded.

**Ticket 3 — Trust and continuation:** cite-and-link official consumer process, evidence attachment, editable dispute message, provider event/itinerary reminders, and tests for misleading confirmation claims.

---

## 11. What to preserve as product identity

Dubai-io is neither “only an airport assistant” nor “only a municipal fine-warning bot.” The city companion can eventually:

- **Talk** with people and authorized AI; maintain real chat history and consented memory.
- **Discover** places, verified providers, community discussions and relevant offers.
- **Plan** complete activities and contingencies across domains and time.
- **Guide** users with source-based steps, maps, manual indoor landmarks and reminders.
- **Act** using approved service APIs, forms, booking handoffs and eventually transactions.
- **Recover** when things go wrong, using evidence, official channels and prior context.
- **Remember** user-owned photos, documents, video moments and relationships with revocable access.
- **Grow** via an AI-assisted, human-approved service integration factory instead of cluttering the interface.

**Short formulation:** *One simple conversation. A growing, trustworthy network of city capabilities.*
