# Dubai-io — Scenario Library

**Purpose:** Product examples, capability design, test cases and future backlog.  
**IMPORTANT:** Names, prices, wait times, weather, route descriptions, fines, discounts, partner APIs and booking states previously mentioned in brainstorming were **illustrative and not verified**. Never render them as real unless a permitted data source confirms them at runtime.

## 1. Shared scenario template

Every scenario should include:

```yaml
scenario_id: S-XXX
name: Human-readable name
persona: visitor | resident | both
trigger: user_request | scheduled | context_event | provider_webhook | device_signal
intent: what the person actually wants
required_inputs: []
capabilities: []  # plan, guide, compare, recover, protect, contact, execute
allowed_sources: []
permissions: []
output_cards: []
action_boundary: information | handoff | merchant_request | verified_execution
fallback: safe action if API unavailable
success_evidence: actual way to know the task succeeded
status: research | prototype | verified_pilot | production
trigger_confidence: confirmed | inferred | estimated
notification_policy: {opt_in: true, ttl_seconds: 600, dedupe_key: null}
source_state: proposed | validated | live_authorized
```

## 2. Expanded scenario index

| ID | Scenario | User's real job | Reusable capabilities | Main blocker |
|---|---|---|---|---|
| S01 | DXB airport arrival | Get from arrival to hotel with minimum confusion | Guide, compare, plan | Airport indoor data, live queues, fare freshness |
| S02 | Skydiving + beach day | Coordinate weather, activity, travel, gear | Plan, compare, contact | Booking access, safety/operator validation |
| S03 | Holiday rental | Find lawful stay and understand terms | Compare, protect, execute | Verification data, deposits, smart lock access |
| S04 | Evening walk | Safe scenic route and useful pit stops | Guide, protect | Crossing/indoor accuracy; no speculative fines |
| S05 | Group dinner | Satisfy dietary needs across a group | Connect, compare, plan | Real allergen verification, group orders, payments |
| S06 | Used items marketplace | Buy/sell second-hand goods safely | Community, compare, recover | Fraud, escrow, delivery partnerships |
| S07 | Sick day | Find appropriate care and verify next steps | Protect, compare, contact | Insurance accuracy, medical regulation |
| S08 | Car ownership/driving | Understand parking, Salik, fines, detailing | Guide, compare, execute | Authorized account APIs and payments |
| S09 | Nightlife + safe return | Plan venue and transport home | Plan, compare, protect | Verified availability, driver confirmation |
| S10 | Consumer rights/visa | Resolve dispute, find official immigration status | Official RAG, recover | Legal accuracy; authenticated government access |
| S11 | Taxi/Metro lost property | Locate ride details and report loss | Recover, memory, guide | Official reporting integration |
| S12 | Dubai Mall lost vehicle | Find car and route back | Memory, guide | Indoor positioning accuracy |
| S13 | Tourism VAT refund | Validate eligible receipts before departure | Memory, protect, reminder | Rules, operator validation and live kiosk locations |
| S14 | Abu Dhabi day trip | Coordinate access rules, trip and transport | Plan, guide, compare | Accurate venue rules, admission authorization |
| S15 | Desert safari verification | Avoid misrepresented operator packages | Compare, protect | Verifiable license data and terms |
| S16 | Laundry / apartment cleaning | Get quote and arrange real service | Discover, contact, execute | Merchant availability and fulfillment |
| S17 | Café discounts + meetup | Find nearby authentic offer and invite people | Community, compare, connect | Real offers, moderation, consent |
| S18 | Personal video memory | Retrieve coffee-spill moment from user's video | Memory, search, verify | Storage privacy, timestamp accuracy |
| S19 | Rental deposit evidence | Track contract, photos and return timeline | Memory, recover, official RAG | Document rights, source freshness |
| S20 | Budget-aware day replanning | Respond to heat, delay or spending constraints | Plan, reminder, compare | Fresh external data and user permission |
| S21 | Proactive delivery-to-trip chain | Order update + packing reminders in ongoing chat | Events, memory, reminder | Authenticated provider data / user plan |
| S22 | Possible departure and destination arrival | Transition travel stages using permissions and signals | Context, geofence, guide | Native OS event support; inferred motion |
| S23 | Family ticket-ready message | Retrieve valid previously issued tickets at destination | Memory, tickets, protect | Authorized issuer assets and family permissions |
| S24 | Indoor landmark wayfinding | Find an Apple Store or exit with shop/floor cues | Guide, venue graph, manual check-in | Licensed/current venue maps and landmarks |
| S25 | Automatic parking memory and recall | Detect possible parking; save/recover floor, pillar and photo | Motion, memory, guide | Confirmation required; underground location accuracy |

## 3. Fully specified flagship examples

### S16 — Laundry request → actual confirmation → dispute (MVP hero)

**Prompt:** “I need five shirts ironed by tomorrow morning near Marina.”  
**Inputs:** area (shared or manually entered), deadline, quantity, pickup preference.  
**Tools:** `provider.search`, `quote.request`, `request.status`, optionally `civic.search` if there is a dispute.  
**Output:** providers with source/price freshness; quote action; request status; merchant response.  
**Execution:** user approves sending details -> provider dashboard acknowledges -> explicit confirmed status only after provider accepts.  
**Continuation:** user later complains of damaged clothing; companion retrieves the permitted prior request and helps attach receipt/photos, prepares a sourced complaint draft, opens official process.  
**Success evidence:** genuine merchant acknowledgement ID, not LLM-generated text.  
**Fallback:** contact link or merchant request form if no provider API.

### S01 — DXB arrival (early capability / optional demo)

**Prompt:** “I've arrived at DXB Terminal 3 at night; how do I reach Business Bay?”  
**Inputs:** arrival time, destination, party/luggage, mode preferences.  
**Tools:** official entry/terminal guidance, permitted routes API, current transport timetable, fare estimates.  
**Output:** human-readable next step, route options, approximate cost with `as_of`, official sources and operator handoffs.  
**Guardrails:** don't infer Smart Gate eligibility from nationality alone; don't invent baggage belt, counter direction, queue time, ticket issuance or live taxi booking. Indoor GPS may not work; manual step confirmation is acceptable.  
**Success evidence:** user selects/open route; booking only if actual provider confirms it.

### S02 — Skydiving + beach + services (aspirational orchestration demo)

**Prompt:** “I want to skydive tomorrow and visit JBR afterward.”  
**Tools:** weather, activity operator's public permitted availability, maps, shopping links, service registry.  
**Output:** trip plan, activity handoff, route, optional gear list and optional laundry quote.  
**Guardrails:** do not claim an operator-approved wind threshold; public weather alone does not establish jump safety; don't show prepaid parking, delivery guarantees, real discounts or one-tap bundle checkout without partner confirmations.  
**Success evidence:** independent statuses for each subtask, not one fabricated bundle-success state.

### S11 — Lost-item recovery (strong early feature)

**Prompt:** “I left my passport in a taxi 20 minutes ago.”  
**Inputs:** last ride details if available, approximate time, pickup/dropoff, receipt or trip proof.  
**Tools:** permissioned trip history, saved receipts, official contact/reporting handoff.  
**Output:** urgent checklist; vehicle/trip detail extracted only if actually found; official reporting link; incident summary.  
**Guardrails:** never pretend an official ticket was filed unless an official confirmation/ID exists; avoid broad exposure of passport data.  
**Success evidence:** official receipt or user-confirmed completion of reporting step.

### S13 — Tax-free VAT refund reminder (strong early feature)

**Prompt:** “I'm leaving tomorrow; which tax-free purchases need attention?”  
**Inputs:** receipts uploaded by user, departure date and airport, consent.  
**Tools:** receipt extraction, official current refund rules, scheduled reminder, official operator handoff.  
**Output:** eligible-looking receipts, missing data warnings, estimated refund (after applicable deductions), action checklist and timing.  
**Guardrails:** don't assert eligibility from an image alone; do not invent kiosk location or guarantee the refund.  
**Success evidence:** user has needed paperwork and valid official validation; follow up after departure if desired.

### S18 — Personal multimodal memory (longer-term)

**Prompt:** “When did I spill my coffee at Dubai Mall?”  
**Tools:** permissioned `media.search`, segment/time metadata, temporal reranker, original video viewer.  
**Output:** best-matching clip and approximate frame time, with uncertainty and an option to open/share.  
**Guardrails:** no semantic search over unauthorized chat/media. Treat “7.4 seconds” as an *example*, not a guaranteed retrieval resolution.

## 4. Reusable agent skills

- `plan`: decompose an intent and respect time/budget constraints.
- `guide`: step-by-step venue or transport assistance with source confidence.
- `compare`: shortlist options, current prices and conditions.
- `connect`: share a link, message, meetup or approved merchant request.
- `execute`: perform a permissioned, authenticated provider action.
- `recover`: assemble evidence, report an issue and monitor status.
- `protect`: surface relevant verified rules without claiming to predict law violations.
- `remember`: permissioned retrieval of user context, documents and media.

## 5. Evaluation design

For every scenario, store: user goal, known inputs, expected tool calls, prohibited tool calls, expected card type, provider response fixture, citation expectations, success state and safe fallback. Test tools returning stale data, no data, malformed API responses and authorization failures.

## 6. Tourist experience extensions — ten concrete journey cases

These refinements preserve the full ten-case research set as **candidate real-world workflows**, distinct from confirmed integrations. Values such as prices, zones, official permits, wind thresholds, discounts, queue times, booking/parking endpoints, and legal penalties in earlier examples were **unverified illustrations**. They must be checked at source and must never appear as confirmed actions without proof.

| Tourist case | Existing scenario | Expanded orchestration | Safe first implementation / boundary |
|---|---|---|---|
| T01 Skydiving + beach + post-event cleaning | S02 | Operator availability, weather context, route/parking, beach shopping, later cleaning | Official booking link + weather + itinerary card + opted-in laundry quote; no assumed Skydive booking API, parking reservation or arbitrary wind pass/fail threshold |
| T02 DXB airport stages + onward transfer | S01 | Arrival time, Smart Gate info, step-based baggage stages, SIM and transport comparison | Manual step confirmations, official guidance, routes; no fictional baggage carousel, queue time, indoor GPS or free SIM guarantee |
| T03 Rental-car parking and Salik | S08 | Identify parking zone, compute current tariff, estimate tolls, present payment handoff | Maps/geographic context + current official rules; **no automatic RTA/Parkin payments without credentials and rights**, no flat universal Salik price assumption |
| T04 Lost item in public transport | S11 | Find consented ride reference, time, contact, then assemble official lost-property report | Evidence checklist and authorized official link; no false claim of filing, driver dispatch or recovery |
| T05 Dubai Mall misplaced vehicle | S12/S25 | Detect parking transition, save photo+floor/pillar; later retrieve indoor guidance | Parking memory + manual landmarks; integrate official venue Find My Car where supported; no indoor GPS claim |
| T06 Nightlife and safe return | S09 | Venue search, rules, venue confirmations, designated driver request | Authorized reservation links + safe transport reminder; no automatic liquor permit or unconfirmed driver booking |
| T07 Medical problem, insurance, pharmacy | S07 | Symptom safety screening, insurer contact/network, licensed care and pharmacy handoff | Emergency escalation when appropriate, verified clinic/insurer links; no AI-issued medical certificate, e-prescription or coverage guarantee |
| T08 Abu Dhabi mosque day trip | S14 | Official visitor registration, current dress rules, route/transport, preparation checklist | Official venue info, ticket/pass handoff; vision check is suggestion only, never entry approval |
| T09 Desert safari operator comparison | S15 | Package comparison, operator documentation, reviews and safety questions | Merchant source records + official verification where accessible; no fake certified operator or automatic 15% discounts |
| T10 Tax-free receipts and departure | S13 | Receipt vault, eligibility screening, validation checklist, airport/departure notification | Official refund guidance, estimates and reminders; no fabricated QR validation or country-wide eligibility assumption |

### Further real-life flows that cut across cases

- **Laundry/ironing** (S16): a message appears with a provider-confirmed pickup window; user can accept/snooze, later recall the order when reporting damage.
- **Café/meetup** (S17): group participants see consented venue offers, poll for time, preserve a useful community recommendation and share a genuine booking link.
- **Multimodal memory** (S18): opt-in media indexing can retrieve approximate video segments; high-resolution timestamp search is a separate capability.
- **Rental dispute** (S19): retrieve photos, saved terms and prior support messages; draft a source-cited complaint but don't file an official case unless authorized and confirmed.

## 7. Proactive companion timeline — worked trip example (S21–S23)

**Example:** a family books a snorkeling trip for tomorrow and has ordered supplies. This is a *proposed sequence*, not a report of real provider events.

| Event / trigger | In-chat message and action card | Needed proof / fallback |
|---|---|---|
| Merchant delivery-status event or manually added expected window | “Your snorkeling kit is expected between 2–7 PM. Track delivery.” `delivery_window` | Authenticated order event; otherwise say user-estimated and open seller tracking |
| T-minus 10 minutes on user-confirmed trip schedule | “Your trip starts in 10 minutes. Remember the snorkeling gear and passports, if needed.” `trip_checklist` | Source trip time and user preferences; don't assert passport requirement absent provider instructions |
| Possible departure from home | “Looks like you may be heading out. Is your trip underway?” | Consented native geofence/activity signal; optional user check-in fallback |
| Approaching destination | “You're approaching your destination. Ready to open your family's tickets?” `ticket_wallet` | Authorized ticket assets + opted-in location; no created admission barcode |
| At the venue | “Need help getting to the right entrance? Which landmark do you see?” `indoor_route_step` | Trusted venue graph or official directory; manual landmark fallback |
| Returning | “Shall I retrieve your parking photo and pillar?” `parking_recall` | Previously user-confirmed saved parking data |

**Notification constraints:** each is persisted as a message in the user's authorized chat; deduped, time-bounded, relevant, optionally pushed, and user-controllable. Prefer neutral text on lock screens. A PWA cannot reliably replace native background motion/geofence monitoring.

## 8. Indoor navigation — user-confirmed landmarks (S24)

**Example prompt:** “I'm inside Dubai Mall and I want the Apple Store.”

1. Ask for the floor or nearest known entrance if unclear.
2. “Which shops are next to you?” Present only validated choices from a current licensed tenant directory.
3. Map the confirmed shop(s) to possible floor-graph nodes; disambiguate ambiguous names/branches.
4. Render the venue's route in Dubai-io's minimal visual design **only if usage/licensing and graph accuracy allow it**.
5. Show the next step, nearest escalator/lift/accessible route and a `Next` control, with manual correction at any time.
6. If venue data is not available, send an official mall navigation link or ask a staff member; never invent floor/shop positions.

**Completion criterion:** user confirms arrival or trusted map service provides arrival state; pressing Next alone does not establish position.

## 9. Parking detection and memory (S25)

**Possible event:** user consented to activity signals; device changes from in-vehicle to stationary/on-foot near a known destination (optionally car Bluetooth disconnects).

**Companion message:** “It looks like you've parked. Want to save a photo of the parking bay and note the floor/pillar?”

**Save:** parking venue name, photo, manually confirmed level/section/pillar, coarse position if available, timestamp and retrieval phrase. Avoid storing raw movement traces longer than needed.

**Recall:** “Where did I park?” -> original photo, level/pillar, optional official parking/venue navigation and nearby entrance. If the inference was wrong, user dismisses it and no parking memory is saved.

**Constraints:** neither GPS nor accelerometer identifies the parking floor or bay; check photography restrictions; no unsolicited continuous tracking; work only with proper mobile permissions.

## 10. Scenario evaluation extensions

Add separate tests for: event deduplication; delayed/out-of-order provider events; time-zone and daylight edge cases; revoked push/location permissions; false-positive car-to-walking transition; partially incorrect landmark selections; inaccessible floors; stale tenant directory; expired/cancelled tickets; family-member authorization; loss of offline connectivity; removing a parking memory; and correction of an inferred departure.
