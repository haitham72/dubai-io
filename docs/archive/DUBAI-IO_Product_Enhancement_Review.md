# DUBAI-IO — Product Enhancement Review

**Version:** 1.0 — proposal for founder and engineering review  
**Prepared:** 18 October 2026 (Asia/Dubai)  
**Audience:** Founder/product owner; Claude, Codex, and any engineering/research agents working with the repository  
**Purpose:** Preserve and evaluate the existing working *simulated* demo; reconcile new ideas with existing specifications, implementation realities, public APIs, compliance, and a contest-ready agentic proof.  
**Decision status:** **NOT APPROVED FOR IMPLEMENTATION**. Every recommendation requires inspection of the latest repository and product-owner sign-off.  
**Evidence cutoff:** Public documentation reviewed 18 October 2026. No credentials, project billing console, current source code, contractual relationships, production API access, live RTA workflow, or deployed agent service were inspected in this review.

> **North star:** *Today's AI can answer. Dubai-io should remember, coordinate, follow through, and produce real-world outcomes.*  
> **Identity:** *Your Intelligent Dubai Companion.* An AI-native life assistant for visitors **and** residents; **not** an airport-only app, fine-appeal bot, shopping aggregator, directory, or clone of DubaiNow or Google Maps.

---

## 0. How to use this document

This is a **product enhancement review, strategic/technical investigation, and decision register**, not a rewrite of the existing design and not a blanket build request.

1. **Read the existing repo first.** Establish actual code, implemented routes, component names, end-to-end working flows, and tests. A prior spec's claim is not evidence that code exists.
2. **Respect document authority.** Existing `00-MVP-FREEZE.md` and `05-CONTEST-MVP-AND-VALIDATION.md` remain the contest implementation scope authorities until the owner consciously changes them. `01–04` define vision/architecture/integration contracts; `06–08` are libraries/vision/narrative. This file is a **candidate amendment** only.
3. **Preserve the existing beautiful demo.** The prototype already simulates arrival, notifications, embedded services, and journeys. Do not discard screens, refactor the app into a different product, or break storyboard timing to install an agent framework.
4. **Classify each element:** `BUILT_AND_TESTED`, `BUILT_SIMULATED`, `PARTIALLY_INTEGRATED`, `PROPOSED`, `VERIFIED_EXTERNAL_INTEGRATION`, or `UNVERIFIED_PARTNER_DEPENDENCY`. A product feature can be beautiful and compelling without having completed backend functionality.
5. **Do not confuse the stage performance and the underlying product.** Cinematic scenes may simulate elapsed days and external partner messages; a separate, bounded **live agent proof** must be real and demonstrable.
6. **Return options, evidence, and specific questions**, including the disadvantages and dependencies. The founder chooses. Do not silently implement features from this file.

### What we know, what we do not know

| Item | Confidence/status | Action |
|---|---|---|
| Existing attractive multi-screen Dubai-io demo with staged interactions | Founder report: exists | Inspect actual repo; preserve |
| Google Maps APIs integration started | Founder report: partial | Inspect keys, services, live response and attribution |
| Real persistent AI agents | Founder report: **not yet present** | Establish one minimal agent execution loop |
| $300 Google credit | Founder reports access to $300 | Verify exact **billing account, product coverage, balance, and expiry**; not a general grant for all APIs |
| Noon/Amazon/RTA/police/DXB integration | Not demonstrated as authorized | No claims of live integration before proof |
| Stage video and simulated iOS/settings/airport/onboarding | Storyboard/demo components | Distinguish cinematic/simulated from real platform screens |
| Live voice control | Desired | Test ASR, intent, wake phrase, mic permissions, latency, stage noise |
| Proactive geofencing | Demonstrated via manual simulation | Real background OS events are a later phase, not inferred from a PWA |
| Commercial merchant partnerships, airport campaigns, coupons | Aspirational | Require permission and actual issued agreements |
| Competition entry rules/deadlines | Prior conversational reports conflict | Recheck official organizer and archive dated proof before submission |

---

## 1. Product proposition and competitive boundary

### 1.1 The product is **outcome orchestration**

Dubai-io combines four ongoing domains within **one memory-bearing companion**:

- **Visitor lifecycle:** airport arrival, journey, hotel, activities, lost items, help, local discovery, departure.
- **Resident lifecycle:** civic reminders, vehicle/utility records, home/maid/visa services, payments via authorized providers, family life.
- **Services/commerce:** comparison, quote, confirmation, fulfillment watches, handoff to official/merchant web experiences; expandable merchant mini-app ecosystem.
- **People/community:** find nearby groups and events, culturally relevant matches, outreach consent, group/meetup attendance.

**The differentiator is not Maps search, conversational UX, a list of 50 features, or an individual API.** Google Maps/Gemini can retrieve impressive place-related information. Dubai-io's defensible product thesis is continuity across domains, authorized action execution, ongoing task state, human recovery, proactive event handling, and a consistent interface.

### 1.2 Stage argument

**Question:** “Why not use Google Maps, ChatGPT, Gemini, DubaiNow, Noon, and WhatsApp separately?”

**Answer direction:** “They each own a valuable part of the journey. Dubai-io coordinates the whole journey with the user's permission: remembers intent, finds the appropriate service, follows up while the user moves on, escalates exceptions, and brings the answer back.”

**Avoid saying:** “We replace every platform,” “Google Maps cannot do this,” or “our app already pays/appeals/books across them.” The comparison is a proposed user experience, not proven superiority.

### 1.3 One capability, multiple expressions

The same **durable mission** pattern applies across scenes:

`USER_INTENT or AUTHORIZED_EVENT → CONTEXT → PLAN → TOOLS → CANDIDATES → APPROVAL → EXECUTION/HANDOFF → WATCH → VERIFIED_STATUS → PROACTIVE_MESSAGE → CLOSE/RECOVER`

Examples: forgotten ID in taxi, haircut booking, airport ticket reminder, order tracking, find Egyptian AI engineers in Dubai, government complaint draft, meal delivery, maid-visa administrative support. These are **one architecture with domain policies**, not fifty unique hard-coded agents.

---

## 2. Current cinematic demo — preserve and improve

### 2.1 Full narrated story, spanning **one week in the visitor's life**

The **film's timeline** can span seven days; the stage presentation should be a selected cut of **approximately four minutes**, extendable to ~7–8 minutes if the format allows. Do **not** make the live demo seven days long. Video, ellipses, VFX overlays, and live phone inserts compress elapsed time.

| Beat | Visitor experience | Engineering/demo truth |
|---|---|---|
| 1. Arrival / welcome | Visitor lands at DXB. Stylized iOS Wi-Fi/settings sequence suggests the Dubai-io app. Assistant welcomes visitor. | Clearly cinematic concept. Official Wi-Fi captive-portal placement, airport signage and government endorsement require agreements. |
| 2. Wayfinding | “I am lost.” Assistant asks for an image and landmarks, suggests the next waypoint, checks user confirmation. | User-confirmed wayfinding; avoid fabricated indoor coordinates or unsupported exact navigation. |
| 3. Transport | Compare metro/taxi/car; retrieve route info, ticket access if actually issued, and clearly identified possible offers. | Google Maps can help discover/route; RTA tickets/QR and vouchers require issuer/partner access. Do not fabricate passes or redeemable discounts. |
| 4. Hotel arrival | Companion remembers hotel and arrival itinerary (with consent). | Store typed, minimal trip context; never silently assume travel records. |
| 5. Lost item | “I left my ID in the taxi.” Remembers route/time and builds a shortlist; simulated taxi image/driver, optional evidence/report, human follow-up, delivery coordination. | Official authority/taxi operator data unavailable unless approved. Pilot with a real operator or mark record as demo fixture. Do not expose real driver personal information without authority. |
| 6. Services in a chat | Toothbrush, breakfast, pharmacy; compare providers; open embedded custom UI or merchant site; approval and order tracking. | One authorized merchant flow should be genuinely live; others can be labeled illustration/handoff. |
| 7. People | Voice: “Find Egyptian AI engineers in Dubai.” Discover a suitable group/event, show what data will be shared, send/join/RSVP after approval. | Real community data must be from a permitted source; no auto-enroll or messages to strangers without authorization. |
| 8. Day in Dubai | Trip reminders, parking photograph, nearby attraction tickets, pre-event checklist, hair appointment with optional hairstyle image preview. | User-triggered or manually simulated location event drives **real logic**; no false claim of background geofencing. AI images are suggestions, not guaranteed haircut outcomes. |
| 9. Fine notice | Consented Gmail connects a notice. Agent verifies sender/source, brings it to attention, explains uncertainty, drafts a polite request for review and asks permission to submit. | Gmail access requires OAuth/verification; official filing requires lawful channel and authorization. Email text alone is **not proof** of an official fine. |
| 10. Pending appeal | Companion continues monitoring while visitor goes to a haircut, dinner, activities. If the authority requests evidence, the visitor can resume an authenticated official page. | Persist case status, source, next action. No background tampering or fictitious official replies. |
| 11. Return to airport | “Passport, baggage, tickets, departures.” Case still pending; taxi and travel checklist reminders appear. | Do not claim smart gate, fast-track, exit clearance, or airport access unless an operator confirms eligibility and integration. |
| 12. Final twist | Just before goodbye, a **simulated** authoritative message reports the authority has independently approved the appeal. Robot waves on mobile and video wall; final farewell. | The government decision is independent of AI. Agent **noticed, prepared, tracked, and notified**; it did not persuade regulators or guarantee forgiveness. |

**Fine-appeal dramatic structure:** Pending → reminder near airport → audience uncertainty → external approval update → joyful closure. The emotional payoff belongs to the authority's independent action and the assistant's persistent follow-through, not a claim that AI can erase penalties. Do **not** claim a parking/traffic fine necessarily prevents departure or is automatically payable at airport exit; such rules depend on circumstances.

### 2.2 The dual-format stage

- **A-roll:** presenter speaking to audience and **occasionally** to the assistant: “Hey, Dubai-io, can you handle this?”
- **Phone feed:** screen-recorded or mirrored app, with live voice moments clearly recognizable.
- **B-roll:** photoreal/cinematic traveller scenes across a week; VFX notifications hovering in space; traveller raises phone toward POV to show specific UI results.
- **Stage events:** operator uses existing trigger panel to simulate entering a location or moving to Day N, but the triggered **agent task, state transition, and notification logic should run genuinely** where claimed.
- **Human view:** audience sees the consequence, **not a scrolling API request log**. Technical logs are optional evidence for judges during Q&A.
- **Resolution:** airport farewell/robot waving is a delightful epilogue, not a reason to add needless integrations.

### 2.3 Three demo cuts

**A. 90-second wow teaser:** 0:00 arrival; 0:15 voice mission; 0:35 real merchant handoff/acknowledgement; 0:55 companion proactively remembers open fine; 1:15 official decision update (simulated); 1:25 goodbye.

**B. Four-minute contest cut:** 0:00–0:35 arrival/voice; 0:35–1:25 context and two options; 1:25–2:30 **one real agentic action with a test merchant**; 2:30–3:15 an independent proactive reminder and case state; 3:15–4:00 rapid week montage + airport fine twist, labelled cinematic concept. The proof lives in the real action, not the film.

**C. Eight-minute expandable cut:** adds lost taxi item, voice community match, widget handoff, operator human escalation, and verifiable Q&A receipts. Do not make it the default.

**Suggested proof anchor:** a service-request mission initiated by **natural voice**, with a real model-driven tool selection, real persistence, a **separate merchant operator** accepting the request, and an authentic updated status displayed in the same conversation. This requires no major platform partnership and proves capabilities reusable across the dream scenarios. Lost-property and official fine outcomes remain cinematic unless verified partner access emerges.

---

## 3. Google as infrastructure — capabilities and limits

**Core distinction:** Google offers separate products, billing, terms, quotas, scopes, and legal responsibilities. **There is no universal “Google API” that can search and buy from any merchant, appeal government fines, generate official transport passes, or read every private site.**

### 3.1 API applicability matrix

| Need | Candidate interface | What it can really supply | What it **does not** grant | Confidence |
|---|---|---|---|---|
| Find nearby barbers, laundries, restaurants | Google Places API (New): Text Search/Nearby Search/Details | Places, coordinates, address, hours, selected listing data, images with license conditions | Merchant-side prices, appointment slots, payment, platform order status | Verified docs |
| Route and ETA | Routes API / Maps SDK | Routing, time/distance and supported modes | RTA fare entitlement, live Dubai taxi booking, physical-location certainty | Verified docs |
| Geocode addresses | Geocoding API | Address ↔ approximate coordinates | Indoor floor, gate, lift location or actual presence | Verified docs |
| Contextual location Q&A | Gemini grounding with Google Maps | Maps-grounded location-aware answers | General-purpose booking authority and permanent provider database | Verified docs |
| General grounded answers | Gemini Grounding with Google Search, or independent compliant search vendor | Web-backed answers with source context | Legal permission to scrape/reuse third-party data or execute transactions | Verified docs |
| Consented mail notice | Gmail API OAuth (e.g. read-only) | User-permitted mail search and reading | Government-source confirmation; ability to submit an RTA appeal | Verified docs; integration not built |
| Personal schedule | Calendar API | Read/create reminders/events within approved OAuth scopes | Ticket purchase, event venue permissions | Known product; validate scopes |
| Phone camera / user position | Browser/device APIs and Maps SDK | Foreground camera/location on permitted devices | Reliable persistent geofence when PWA is suspended | Architecture judgment |
| Voice dialogue | ASR + LLM + TTS (Google or another provider) | Intent recognition, responses, speech experience | Guaranteed low latency in auditorium, agent autonomy by itself | Evaluate with tests |
| Merchant leads | Maps/Places candidate discovery, partner directories | Discovery of businesses under data/terms limits | Permission to scrape numbers for mass cold calls, retain data indefinitely or contact people unsolicited | Legal/policy review |

Google reference docs: [Places API (New)](https://developers.google.com/maps/documentation/places/web-service/overview/), [Places pricing](https://developers.google.com/maps/billing-and-pricing/pricing), [Maps grounding](https://ai.google.dev/gemini-api/docs/maps-grounding), [Gemini Search grounding](https://ai.google.dev/gemini-api/docs/google-search), [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies), [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes).

### 3.2 What the reported $300 credit actually means

Google Cloud's standard new-customer trial advertises **$300 credit over 90 days** for **eligible** Cloud services, subject to product restrictions and account status. **It is not unlimited, not automatically transferrable to any API, and may already be partly consumed or time-expired.** Google documentation explicitly states the welcome credit cannot be used to pay **Gemini API in Google AI Studio** costs, and partner model charges are also excluded; Vertex AI eligibility and quota differ from the Gemini Developer API. Some Maps products have monthly free usage caps per SKU independent of the trial.

**Do this before coding:**

1. Open actual Cloud Billing → **Credits**, **Reports**, **Budgets**, billing account status; record account and expiry, not just an older promo email.
2. For each enabled API list: SKU, active project, quota, price, trial applicability, credentials restrictions, owner and approved use.
3. Separate Maps/Places, Gemini Developer API, Vertex AI, Gmail OAuth, and Search vendors in the cost ledger.
4. Set quota caps and budget alerts; **budget alerts are not automatic hard spending limits**. Keep server-side project/API keys restricted.
5. Model `monthly_searches × cost_per_Search + details + route + grounding + speech + LLM + media + queue + storage`; compare three load profiles (stage, 100 testers, 10k users). Do not project from one response.

**As-of Oct 2026 example (official list, subject to change):** Places API (New) **Text Search Pro** currently lists 5,000 free monthly calls per SKU and $32 per 1,000 beyond the free usage cap in its first paid volume tier; field masks affect the billable tier. This is not a guarantee of future pricing, and simply requesting IDs may fall in a different SKU. Calculate using the actual call plan and official calculator, not this illustrative figure.

References: [Cloud Free Program](https://docs.cloud.google.com/free/docs/free-cloud-features), [Cloud trial FAQ](https://cloud.google.com/signup-faqs), [Maps price list](https://developers.google.com/maps/billing-and-pricing/pricing), [Places billing/field masks](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing).

### 3.3 The critical platform-policy trap

Google Places **is not a license to create a permanent shadow copy of Google's listings** or to export/store reviews and photographs freely. There are display/attribution rules and strong storage/caching restrictions, with some exceptions such as place IDs. Do not build a persistent cross-platform merchant prospecting directory from unrestricted Google listings. Treat `place_id` as an external pointer and fetch allowed content as needed.

References: [Places policy](https://developers.google.com/maps/documentation/places/web-service/policies), [Maps JS attribution/cache policy](https://developers.google.com/maps/documentation/javascript/policies).

### 3.4 Google Search API caution

**Do not build a new product on the old Custom Search JSON API.** Its official documentation says the API is **closed to new customers**, and existing customers must transition by **1 January 2027**. An already-working account should still have a sunset plan. Examine Gemini Search grounding, a licensed search provider, target-site search/feeds and authorized website fetches instead.

Reference: [Custom Search JSON API overview](https://developers.google.com/custom-search/v1/overview).

---

## 4. Amazon, Noon, and other commercial API pathways

### 4.1 Integration levels — do not blur them

- **L1 Discover:** link to known provider/product; source and freshness.
- **L2 Contact/Handoff:** open real merchant page, official app or approved contact channel; perhaps prefill only where the destination explicitly supports it.
- **L3 Quote:** submit a request to an authorized provider-controlled inbox; receive acknowledgement, still **not booked**.
- **L4 Execute:** real order/reservation/booking through an authorized integration, with consent, payment and provider confirmation.
- **L5 Fulfill/Recover:** genuine webhook/API status, cancellation, refund, returns, escalation.

A powerful UX can exist at L1–L3. Do not imply L4 just because a button opened a shopping cart.

### 4.2 Amazon

**Yes, there is an official Amazon product-discovery API route, with prerequisites.** Amazon's current **Creators API** documentation lists catalog search, item details, variations and browse nodes, aimed at enrolled Associates/creators. Its docs indicate eligibility involving an Associates membership and **10 qualifying sales in the preceding 30 days** for access; confirm the locale/eligibility for UAE specifically. Amazon documents **PA-API 5.0 as deprecated** and specifies migrating to Creators API. Creators API is **catalog/affiliate discovery**, **not carte-blanche access to place Amazon orders in the end user's account**.

**Recommended now:** use **authorized affiliate/deep links** to Amazon.ae, verify program terms before displaying catalog images/prices, and research Creators API access for UAE. If unavailable, retain ordinary official-site handoff without pretending you can inspect the user's Amazon basket or delivery status.

References: [Amazon Creators API introduction](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction), [Onboarding](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/onboarding), [Migration/deprecation](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/migrating-to-creatorsapi-from-paapi).

### 4.3 Noon

**Important finding:** Noon has actual, documented **Noon Partners APIs** with authentication, catalog, offers, pricing, orders, fulfillment and webhooks. The intended clients are **sellers, integrators and approved partners**, including seller-consented OAuth access. **This does not establish an anonymous, public consumer API for searching all Noon product listings or purchasing on arbitrary customers' behalf.**

**Options:**

- **First:** official Noon website/app/deep-link handoff for consumer shopping; label cart and checkout as user actions.
- **Next:** build a seller-facing service module for a consenting Noon seller/merchant if user benefit is demonstrated; onboarding and tenant consent required.
- **Strategic:** propose a licensed discovery/checkout integration with Noon business development only when there is a validated partnership use case. The idea of approaching its leadership is a potential introduction, not evidence of a deal.

References: [Noon Partners API documentation](https://noon-docs.noonpartners.dev/), [Noon API Platform intro](https://noon-docs.noonpartners.dev/docs/getting-started/intro), [Noon OAuth for integrators](https://noon-docs.noonpartners.dev/docs/authorization/getting-credentials-oauth), [Noon seller help](https://helpcenter.noon.partners/en/category/global-selling/noon-api-platform).

### 4.4 Broad provider strategy (proposed evaluation)

| Domain | Realistic starting point | Deep integration dependency |
|---|---|---|
| Food delivery | Discover venue through Places; user opens merchant/platform official ordering page | Partner checkout, fulfillment status and support endpoints |
| Laundry / haircut / tailor | Discover + **pilot merchant inbox** + quote/slot flow | Merchant approval and real slots; avoid assuming Google opening hours equals availability |
| Tour/events | Discovery + issuer booking link + a real ticket already supplied by user | Authorized ticket inventory and QR assets |
| RTA / public transport | Official-source instructions, map routes, official app/site handoff | Issuance or reading private transport tickets needs issuer access |
| Civic fine / dispute | Gmail notification + official verification + draft + deep link | Filing and outcome retrieval need authorized government integration or manual/user-supplied status |
| Banking/payment | User-approved handoff to financial institution/payment processor | Licensed open-finance/payment providers, scopes, strong auth and compliance |
| Domestic staff / visa | Compare licensed agencies, checklist, quote, case handoff and human support | Regulated agency/licensing, immigration/government submission, sensitive identity data |
| Communities | Curated provider/event URLs and platform-approved data, user opt-in | Partnerships, posting/joining permissions and moderation |

**No partner API?** Build a **first-class truthful handoff**, not a fragile pretend checkout. Use provider-side mini-apps or user-controlled browser transitions only where technically and legally permitted.

---

## 5. Agentic website research, crawling, browser handoff and document parsing

### 5.1 A three-tier web research approach

1. **Structured/approved APIs:** preferable for live prices, places, product feeds, business availability and official records.
2. **Search + fetch + extraction:** a licensed search API/grounding result leads to an approved public URL; fetch accessible HTML, extract JSON-LD / visible text, parse embedded documents, cite the URL and timestamp.
3. **Bounded interactive browser:** only when a task genuinely requires a human-like workflow. Use a browser operator with an **allowlist**, human approval for sensitive steps, credential handling through an approved OAuth/session bridge, explicit audit, no CAPTCHA/anti-bot bypass, and stop when blocked by the site's policies.

**Key distinction:** indexing public information does **not** authorize clicking "Pay", "Submit appeal", “Book”, changing passwords, bypassing CAPTCHAs, or treating an HTML DOM as a stable API.

### 5.2 PDF/DOC processing — **Docling**

The tool is **Docling** (not “Duckling”); it parses PDFs and many document formats into structured representations/Markdown/JSON, including layout and table information. Good for RTA rules, consumer guidance, merchant price lists **where access and reuse rights permit**. Avoid blindly trusting scanned legal text: keep source URL, document date, extraction confidence, page location, and review against official source. Scanned/Arabic documents need targeted QA; public-page versions can supersede PDFs.

Reference: [Docling GitHub](https://github.com/docling-project/docling).

### 5.3 Proposed research toolchain

`Intent → trusted domain or search provider → URL policy check → fetch (HTTP) → parse (HTML/Docling) → provenance + expiry → claim checker → actionable typed card → official handoff`.

Store: `source_url`, `retrieved_at`, `source_domain`, `license_status`, `content_date`, `hash`, `jurisdiction`, `access_method`, `extraction_method`, `confidence`, `permitted_cache_until` and downstream citations. Never use public sites as trusted prompts/instructions: page contents are **untrusted data** (prompt injection risk).

**Security:** prevent SSRF via blocklists/allowlists for private IP ranges/cloud metadata; enforce size/time limits; do not follow redirects to internal hosts; sanitize rendered HTML; permission checks before browser navigation; robot/terms compliance. Use normal search for an answer, interactive browser for an approved task only.

### 5.4 Fine dispute handoff proposal

User gets a Gmail notice → source/classification check → agent asks to verify official record → official-source guidance → case draft and required evidence checklist → consent review → (a) human submits on official website, or (b) licensed adapter submits and records acknowledgement → case watch → **actual** response/source or **demo fixture** update.

If authority asks for a photograph unavailable to the user, agent may provide a truthful explanation and draft a follow-up request. It must **not** demand a private shop's CCTV or image of a stranger without permission or suggest it can retrieve such data automatically. A restaurant-camera inquiry, if pursued later, is human-mediated with lawful authorization.

**Do not promise seamless prefilled authenticated government pages.** Many identity-verified forms will intentionally reject deep links, transferred sessions and automated form submission. Save the user's draft/evidence in Dubai-io for **copy/paste, export or guided handoff** unless the site explicitly supports a safe integration.

---

## 6. Proactive companion architecture: “WhatsApp messages, but with an ongoing mission”

**Design requirement:** The assistant can initiate **relevant, authorized, deduplicated messages** even while the user is not chatting. Avoid promotional noise and unverified location assumptions.

### 6.1 Events and state

Event examples: `trip.departure_soon`, `geo.destination_approaching_simulated`, `ticket.open_existing`, `service.quote_updated`, `order.delivery_window`, `case.official_response_seen`, `parking.user_saved`, `calendar.event_tomorrow`.

Event design:

- `event_id`, `source`, `source_auth`, `subject_user_id`, `mission_id`, `kind`, `occurred_at`, `received_at`, `confidence`, `consent_scope`, `payload_schema_version`, `dedupe_key`.
- **Durable outbox** makes transitions persist across browser closure; retries are bounded and idempotent.
- The message appears in **chat history** even when push is disabled; push itself respects per-topic opt-in and quiet hours.
- User can say “not going,” “I already paid,” “do not remind me,” and revoke background access.
- Distinguish **manual simulation** from real OS geofence, real webhook and user-supplied data in operator/dev telemetry.

### 6.2 Spatial realism

Phone/PWA constraints differ by OS, background state and permissions. Foreground geolocation is not an always-on geofence. On stage, **manual simulated trigger → real orchestrator → persisted notification** is technically honest and reliable. For production background motion detection, research native iOS/Android APIs, battery impact, false positives and consent; do not assume accelerometer can prove a car is parked. Parking photo/floor/pillar records should be user-confirmed.

### 6.3 Voice-controlled pivot

When the presenter says “Hey, Dubai-io”, the system should not simply play an attractive canned answer. A real proof could:

- Hear a natural utterance through microphone with approved consent.
- Transcribe (show graceful failure/retry at noisy venue).
- Route to a bounded task agent that selects **approved** capabilities.
- Ask a single necessary clarification or send an approval card.
- Execute or submit a request to a separate real demo merchant inbox and show its acknowledged result.
- Preserve state after switching scenes; respond to a new user request in the **same mission ledger**.

Measure p50/p95 time-to-first-feedback and mission success; prep an explicit stage fallback if network/audio fails. **Wake word and emotion are UX layers, not the agent's proof.**

---

## 7. The human-in-the-loop recovery team

The user described low-tier human developers/support/operators who recover complex tasks—e.g. arranging a domestic worker's visa—when agents hit blockers, need clarification or handle high-consequence transactions. **This is a business operations role, not automatically a software developer role**; propose **case coordinators** with specialized escalation to legal/licensed operators.

### 7.1 Proposed responsibility split

- **Agent:** identify intent, collect minimal necessary facts, compare authorized providers, draft request, follow up, detect blockers, summarize evidence.
- **User:** authorize sharing/price, inspect choices, provide missing evidence, make decisions with lasting legal/financial effects.
- **Case coordinator:** contact provider under approved process, verify required documents, resolve ambiguous requests, maintain records, report actions transparently.
- **Licensed specialist:** when the matter falls under immigration, banking, formal law or regulated activity; human support is **not** a substitute for legal authorization.
- **Provider/authority:** owns the actual approval, refusal, booking or fulfillment decision.

### 7.2 Minimum case schema

`case_id`, `mission_id`, `case_type`, `priority`, `reason_for_escalation`, `risk_tier`, `consent_artifacts`, `assigned_to`, `status`, `next_due_at`, `evidence_refs`, `provider_refs`, `financial_ceiling`, `last_verified_external_state`, `audit_log`, `retention_policy`.

### 7.3 Stop rules

Automatically escalate or halt on: disputed identity, price changes, uncertain legal responsibility, permission denied, a third party asks for sensitive ID documents, payment recipient mismatch, unverified company, failed provider authentication, contradictory government sources, case beyond employee's authority, or a claimed outcome without trustworthy evidence.

**Economics to model:** support hours per mission, escalation rate, recovered mission percentage, gross margin after human labour, time to close. If every complex request needs a human for 40 minutes, it is a concierge service, not a scalable autonomous platform; that's acceptable as a niche pilot if stated honestly.

---

## 8. Automated merchant acquisition — business opportunity, **legal hold**

### 8.1 Idea and verdict

Idea: agents find ~1,000 merchants per day, call them to request coupons and integration permission, qualify leads, negotiate terms, then pass serious opportunities to humans for contract signature.

**Technical possibility is not commercial or legal permission.** This is **HIGH-RISK** as mass unsolicited outbound calling or WhatsApp messaging. **Do not deploy autonomous cold-calling, bulk WhatsApp, auto-diallers or scraping-based phone prospecting until a UAE-qualified lawyer and relevant telecom/platform compliance specialist approve the exact B2B workflow and data sources.** Do not assume “B2B” or “an AI voice” is exempt.

### 8.2 Verified UAE context

UAE **Cabinet Resolution No. 56 of 2024** regulates telemarketing; **No. 57 of 2024** addresses penalties. Official UAE guidance describes authority permissions, licensed company phone numbers, identifying caller/company and purpose, DNCR practices, restrictions on call times **9:00–18:00**, limits on repeated calls, non-deceptive conduct, and telling a person about call recording. Government guidance notes automated communication systems may be used **subject to the regulations**; this is **not a blanket permit to make 1,000 unsolicited daily calls**. Exact applicability to a particular B2B integration solicitation (rather than consumer sales marketing), business licenses and recorded AI calls requires counsel review.

Primary references: [UAE Cabinet Resolution 56/2024 PDF](https://u.ae/-/media/Information-and-services/Infrastructure/Cabinet-Resolution-No-56-of-2024-Concerning-the-Telemarketing-Regulations-1.pdf), [Official UAE Ministry briefing](https://www.moet.gov.ae/en/-/ministry-of-economy-and-telecommunications-and-digital-government-regulatory-authority-review-regulatory-legislations-in-organizing-operational-mechanisms-for-telemarketing-companies-in-the-uae-and-enhancing-consumer-protection-in-line-with-best-practices), [UAE legislation penalties 57/2024](https://uaelegislation.gov.ae/en/legislations/2523).

### 8.3 WhatsApp ≠ unrestricted outreach channel

Meta/WhatsApp says business-initiated messages on the **WhatsApp Business Platform** require **approved templates**, emphasizes user opt-in/preferences, and enforces restrictions against spam and unwanted marketing. WhatsApp Business App vs Platform APIs have different terms. Unofficial browser automation of WhatsApp Web, bulk unsolicited contacts, or disguised human identities create account-enforcement and legal risk.

References: [Meta, business chat control](https://about.fb.com/news/2025/04/ways-to-manage-your-businesses-chats-on-whatsapp/), [WhatsApp Business terms hub](https://whatsappbusiness.com/terms-and-conditions/).

### 8.4 Safer graduated rollout — **proposed**

| Phase | Implementation | Need before starting |
|---|---|---|
| 0 | **No messaging.** Build candidate business categories using permitted sources; score possible value proposition; assemble merchant one-pagers. | Data rights, source attribution, retention review |
| 1 | **Inbound opt-in.** Merchant-facing site with “list your business/get integration/coupon pitch” and human-led outreach to existing introductions. | Merchant consent and true representation |
| 2 | Human-approved targeted **B2B partnership enquiries** through business-approved channels, each logged and opt-out honoured. | Legal analysis of channel, recipient and solicitation, licenced org processes |
| 3 | AI assists human agent **during opted-in conversations**: notes, answers, proposes terms, schedules human call. | Recording disclosure, data processing approval, provider terms |
| 4 | Only if counsel explicitly approves: capped AI-initiated calls to validated opted-in contacts, with clear AI identity, human handoff and audit. | Written counsel sign-off, permissions, approved telecom provider, recording/data policies, capacity and complaint monitoring |

**Negotiation scope:** Agents can propose a coupon, expiry and integration outline but may **never bind the company** or say “contract signed” without authorized human signature. Merchant offer is not published until pricing, redemption and availability are independently confirmed.

### 8.5 Discovery must not become scraping for spam

Do not indiscriminately copy Google Maps business phone numbers or harvest personal contacts for outreach; Places licensing and privacy apply independently of telemarketing law. Prefer partnerships, opt-in forms, licensed business directories and direct introductions.

---

## 9. Share-a-video commerce discovery (optional plugin, **not MVP**) 

Proposed feature: user shares an Instagram/TikTok video to Dubai-io and asks “What car/product/location is this, and where can I find it?”

**Pipeline:** user-initiated share link or media → permissions/platform terms check → accessible metadata/caption → permitted transcription/audio/frames → multimodal object/entity hypotheses → confirm ambiguity → licensed/allowed catalog or web search → source-linked price/availability cards → merchant handoff.

**Critical constraints:** social platforms often do **not** provide unrestricted media downloads, metadata, captions, comments or third-party-account access. A public URL does not confer extraction and redistribution rights. Never bypass login, DRM, CAPTCHAs or anti-bot mechanisms; restrict to user-owned/licensed content or explicitly permitted inputs. Keep audio/copyright/privacy controls. Avoid claiming exact product identification from one frame when confidence is low.

**Status:** optional research spike after one contest end-to-end journey works. Choose one narrow demo: identify a generic car model from an image **with confidence and non-guaranteed price source**; no cross-platform automation dependency.

---

## 10. Technical architecture proposal — repo audit first

### 10.1 Conceptual layers (adapt to code, don't rebuild for diagram purity)

```text
VISITOR / RESIDENT (voice, chat, camera, embedded mini-app)
       │
       ▼
SESSION + CONSENT + UI STATE
       │
       ▼
MISSION ORCHESTRATOR (bounded planning, memory, policies)
       ├── Context & schedule / authenticated events
       ├── Discovery gateway (Google Places, licensed web search, partner feeds)
       ├── Civic-source retrieval / Docling extraction
       ├── Authorized provider adapters / merchant inbox
       ├── Handoff builder (user-guided official page, saved draft)
       ├── Case coordination / human escalation
       └── Notification/watch engine
       │
       ▼
TRUSTED STATE / AUTH / AUDIT / STATUS + DURABLE EVENT OUTBOX
       │
       ▼
TYPED CARDS → SANDBOXED WIDGETS → USER ACTION/APPROVAL → VERIFIED RESULT
```

MCP is a **tool interface/protocol** where useful; it does **not** confer official access to RTA, merchants or banks. Do not invent a separate MCP server for each shop; use capability manifests + shared adapters/gateways. An LLM cannot decide unilaterally that a source has L4 execution permissions.

### 10.2 Durable `Mission` abstraction

Example core fields: `mission_id`, `user_id`, `intent`, `user_goal`, `risk_class`, `created_at`, `status`, `input_context_snapshot`, `plan_version`, `approved_steps`, `provider_capabilities`, `external_refs`, `events`, `pending_action`, `next_check_at`, `escalation_id`, `last_verified_at`, `resolution_evidence`.

**Mission state:** `DRAFT → OPTIONS_READY → AWAITING_APPROVAL → SUBMITTED → PROVIDER_ACKNOWLEDGED → QUOTED/CONFIRMED → COMPLETED` plus `BLOCKED`, `ESCALATED`, `CANCELLED`, `EXPIRED`, `UNKNOWN_STATUS`. **Reuse repo/04's authoritative canonical enum**; don't silently fork it. Propose new statuses only via migration/approval. Genuine provider acknowledgement is not completion.

### 10.3 Three-layer rendering contract

1. **Compact card** in chat for quick facts and next action.
2. **Expanded inner-HTML widget** for provider-specific forms and browsing, in a sandboxed, versioned iframe with capability-scoped `postMessage` bridge. The assistant cannot arbitrarily execute third-party HTML.
3. **Full official web/native handoff** where sensitive login, payment or official procedure is safer on the provider's property. Preserve task context internally; provide compliant deep link or copyable prepared draft, *not claimed auto-filled sessions*.

**Trust model:** LLM produces structured intentions and safe draft data; deterministic server authorizes/executes an approved tool; verified external response controls user-visible `CONFIRMED`, `PAID`, `CANCELLED`, `APPROVED` states. Keep credentials exclusively on trusted backend.

### 10.4 Build **one** real integration first

The existing canonical MVP specification proposes laundry/cleaning merchant quote request, and the user now has a higher-emotion stage story. Use both without blowing scope:

- **Live verification strand:** voice → provider discovery/search → approval → request arrives at separate merchant inbox → human accepts/responds → durable update in same chat; verifies agent/tool/action lifecycle.
- **Cinematic vision strand:** one-week multi-domain companion, simulated government/taxi/payment responses, arrival-to-departure story.

The strands can interleave, but on-stage labels and Q&A must make status clear. At least one **real** agent must make a bounded decision/tool call and handle a novel variation; do not label an onClick state-machine-only simulation as agentic AI.

---

## 11. Trust, privacy, official claims and financial boundaries

**High-impact guardrails:**

- **No implied endorsement:** Government office, airport Wi-Fi, DubaiNow, RTA, police, Noon, Amazon, named investors or proposed sponsors must not be presented as active supporters or official integrations without written authority. Demo can say “proposed partner experience,” “concept,” “sandbox data.”
- **User identity/data:** limit collection of Emirates ID, passports, visa documents, travel itinerary, legal evidence, location and bank information; ensure retention/deletion, encryption, access logs and explicit purpose limitation. Review applicable UAE data-protection rules and any sector-specific requirements with counsel.
- **Financial actions:** no silent transfer between banks, taxi charges, third-party purchases or emergency reserves. Display source, amount, provider, fees, approval and real bank/processor receipt. Open Finance needs appropriate authorized integrations—not generic Google APIs.
- **Legal actions:** agent may give sourced information and prepare a draft; filing/appeal and waiver decisions belong to the competent authority. A staged approval is not a real successful appeal.
- **Travel / documents:** do not show AI-created boarding passes, metro/barcode tickets or smart-gate privileges. Existing tickets may be **displayed** only if issuer/authentication rights permit.
- **Agent action control:** transparent confirmations for booking/purchase/data sharing/submissions. Durable audit, replay prevention, provider allowlist, human escalation.
- **Content rights:** provider/product images, social videos, Google Maps results and scraped documents need correct permitted usage and attribution.

### Truth-labelling standard

Tag every stage event/data record as one of:

- `live_authorized` — actual external API call and provider confirmation.
- `live_internal` — real Dubai-io service, test merchant or agent action inside controlled sandbox.
- `simulated_external` — canned fictional response standing in for RTA/noon/airport/taxi.
- `future_concept` — animation of what may be possible with partners.

The visible narrative need not constantly show technical badges, but the **pitch, slides, and judge evidence** must never materially mislead about what is connected.

---

## 12. Prioritized recommendations — proposed, not approved

| Priority | Proposal | Why | Exit test |
|---|---|---|---|
| P0 | Repo audit and feature/scene truth inventory | Stops duplicate builds and ungrounded claims | Inventory maps scenes → actual code/tests/source |
| P0 | Real single-agent service mission | Establishes contest credibility | Natural-language variation executes approved tools and shows a real acknowledgement |
| P0 | Durable state + notification/event outbox | Makes companion proactive across scenes | User closes/reopens app; prior mission and notification survive |
| P0 | Provider/civic source provenance and state gating | Avoids fictitious real-world success | UI never displays fulfilled/approved without evidence |
| P0 | Stage cut + honest demo fixture replay | Makes presentation reliable | 4-minute rehearsal repeatable with offline fallback |
| P1 | Google Places & Maps cost/policy integration | Uses existing $300 only where eligible | Real local shortlist with traceable places + cost report |
| P1 | Website/document research + Docling | Provides answers without private integrations | User asks from 3 official URLs; cited, versioned answers with abstention |
| P1 | First-class website/user handoff | Works without partner APIs | Draft/next step survive until user returns to app |
| P1 | Small merchant-operator pilot | Real external-world outcome | Real pilot acknowledges and updates user |
| P1 | Gmail notice watcher (opt-in) | Strong vehicle/fine narrative | OAuth-compliant test mail → source warning + draft, no fake filing |
| P2 | Community match and RSVP | High visitor value | Match from authorized directory; explicit data-sharing approval |
| P2 | Amazon Creators API eligibility / Noon partnership pathway | Better product discovery | Documented allowed endpoint or honest deep-link fallback |
| P2 | Human case desk | Recovers blocked journeys | Assigned case lifecycle tested without sensitive-data leakage |
| P3 | Native geofencing and issuer ticket access | Adds proactive relevance | Native consent, false positive measures, issuer-approved assets |
| P3 | Social-video shared-media lookup | Optional delightful plugin | Licensed asset → grounded match + official link |
| HOLD | 1,000 AI prospecting calls/day | Regulatory and reputation exposure | Written counsel/channel approval and controlled opt-in experiment |
| HOLD | Bank transfer and government fine write actions | Regulated/high-stakes | Official contractual, security and regulatory clearance |

---

## 13. Real product decisions — **18 questions the founder should decide**

These are nontrivial choices with **alternatives and a recommended direction**. AI reviewers should challenge the recommendation where repo evidence suggests a better option. The founder decides; no implementation is implied.

**D01 — What qualifies as a successful “agentic proof” on stage?**  
**A:** real user intent → actual pilot merchant request → acknowledgement (recommended). **B:** dynamic recommendation only (weaker). **C:** authoritative government case outcome (stronger-looking but partner-dependent). **D:** browser agent completing arbitrary websites (fragile).  
**Decision required:** pick a core proof that is both real and resilient. **Recommendation A.**

**D02 — Should live voice be always-on, push-to-talk, or a presenter-triggered wake state?**  
**A:** always-listening (natural, noisy/risky); **B:** tap-to-talk (reliable but visibly less magical); **C:** wake phrase followed by push-to-talk fallback (recommended); **D:** prerecorded dialogue (cinematic, no live proof).  
**Decision:** how much live risk is acceptable in a noisy auditorium?

**D03 — What should the user see when no merchant API exists?**  
**A:** comparison + official deep link (honest, limited); **B:** embedded merchant webpage only where permission permits; **C:** Dubai-io-owned quote inbox for a cooperating merchant (recommended for pilot); **D:** browser control of unknown third-party checkout (high risk).  
**Decision:** permitted L1–L3 alternatives by service category, and default fallback.

**D04 — Which moment best establishes *proactivity*, not just reminders?**  
**A:** timed trip checklist (reliable); **B:** manual geo-trigger event with real state and ticket wallet (stronger stage impression); **C:** live OS location trigger (ambitious); **D:** provider-authenticated order change (high-trust).  
**Recommendation:** B on stage plus a real persisted A or D. **Decision:** what is genuinely in scope before the contest?

**D05 — Do we treat the fine appeal as the emotional climax or central live product proof?**  
**A:** climax only, clearly simulated external authority (recommended); **B:** actual government filing (requires partner); **C:** user-supplied status and genuine watcher (could be feasible); **D:** remove fine story entirely.  
**Decision:** how to balance emotional ending and verifiable legitimacy?

**D06 — How are third-party web sessions handled?**  
**A:** ordinary link + copyable draft (recommended default); **B:** compliant official deep-link/prefill when supported; **C:** OAuth delegated integration; **D:** user credentials injected into browser automation (reject by default).  
**Decision:** which services warrant investing in B/C?

**D07 — Which Google products should get the first share of the budget?**  
**A:** Places/Routes first (recommended for user-facing demo); **B:** Gemini web/maps grounding first (more conversational but licensing/billing differences); **C:** Gmail/calendar first (more proactive); **D:** video/media first (least essential).  
**Decision:** allocate based on actual trial coverage and measured per-mission costs.

**D08 — When should the mini-app be internal versus the provider's own website?**  
**A:** typed native cards by default, mini-app only for complex forms (recommended); **B:** always embed partner HTML; **C:** always open Safari; **D:** AI generates runnable HTML for each request (security/maturity risk).  
**Decision:** which provider capabilities justify a dynamic UI at all?

**D09 — What business can Dubai-io honestly promise users on launch?**  
**A:** discovery + quality handoff; **B:** discovery + one tested merchant confirmation (recommended pilot); **C:** universal checkout; **D:** concierge staffed completion.  
**Decision:** choose initial service level, category and service area.

**D10 — What stays in memory and for how long?**  
**A:** minimal typed trip/task info and retention controls (recommended); **B:** extended persistent transcript; **C:** automatic full media archive; **D:** device-only contextual memory.  
**Decision:** trade personalization against security, privacy, cost and deletion.

**D11 — Should human recovery be a user-facing feature?**  
**A:** visible “case coordinator is helping” with ETA (recommended); **B:** invisible back office; **C:** entirely AI and self-service; **D:** paid concierge tier.  
**Decision:** transparency, cost model and escalation threshold.

**D12 — How does Dubai-io source local community events?**  
**A:** limited curated approved sources (recommended); **B:** user-generated events; **C:** scraping social media; **D:** partner calendar integrations.  
**Decision:** moderation/cold-start strategy versus data rights.

**D13 — How do merchant discounts enter the product?**  
**A:** merchant-submitted signed offer with expiration (recommended); **B:** affiliate campaigns; **C:** scraped promotional copy; **D:** universal Dubai-io discount (reject without sponsors).  
**Decision:** who is commercially responsible for redemption?

**D14 — Should outbound merchant growth use AI calling?**  
**A:** discovery only; **B:** opt-in merchant portal + human outreach (recommended); **C:** AI support during consented calls; **D:** mass autonomous cold-call engine (legal hold).  
**Decision:** legal clearance threshold and what evidence would justify higher automation.

**D15 — Do agent/browser actions execute automatically when a user says “do the rest”?**  
**A:** bounded low-risk reads only; **B:** explicit per-transaction approval for writes (recommended); **C:** broad delegated recurring mandates with financial caps (advanced); **D:** unrestricted autonomous payments/official submissions (reject).  
**Decision:** build trust by granular permissions or invest in a more sophisticated mandate system?

**D16 — Who is the actual first user?**  
**A:** one-week DXB visitor (powerful stage story); **B:** new resident onboarding; **C:** established Dubai resident with household tasks; **D:** concierge/business travel.  
**Recommendation:** A for pitch, but choose a **real pilot** based on service access/retention economics, not stage appeal. **Decision:** can primary persona differ from initial pilot segment?

**D17 — How much of the stage experience can be a film?**  
**A:** 90s cinematic + 2m real interaction + 30s closing (recommended four-minute composition); **B:** fully live phone walkthrough; **C:** entirely edited film; **D:** 8m long live theatre.  
**Decision:** proof vs reliability, and contest format once confirmed.

**D18 — Where does commercialization start, without pretending to replace a super-app?**  
**A:** fees/commission from a small verified merchant vertical; **B:** enterprise/municipal licensed distribution; **C:** affiliate product discovery; **D:** paid concierge subscription.  
**Recommendation:** evaluate **A + B** as distinct paths; C is auxiliary, D requires strong unit economics. **Decision:** 12-month business objective and dependence on partner approvals.

### Required founder feedback format (when ready)

`D## | choice A/B/C/D/custom | reason/constraint | approved for discovery / approved for implementation / rejected / defer`.  
The AI team should not require instant answers to all 18. Prioritize D01, D03, D05, D07, D14, D17 before taking architectural actions. Most questions are for **future alignment**, not blockers to preparing the review.

---

## 14. Deliverables for Claude and Codex — **read-only evaluation phase first**

### Phase R0 — establish truth

1. Inventory repo: actual routes/screens/widgets, simulated handlers, provider adapters, agent framework (if any), Google setup, tests, seed fixtures, static media.
2. Compare this report against `00`, `01–08`, implementation plan and current code. Note conflicts rather than overwriting specs.
3. Create a **scene-to-capability matrix** with four statuses (real, partial, simulated, future) and evidence path/file references.
4. Flag security surprises: exposed API keys, fake government-branded screens presented as live, user-permission holes, hard-coded sensitive credentials.
5. Deliver concise findings; **no code changes, feature removals, new accounts, outbound contacts or production API spending** without owner go-ahead.

### Phase R1 — targeted spikes, separately approved

- **Spike G (Google):** 3 real representative Places queries with source/attribution, field masks, latency, cost estimate, permitted cache behavior; evaluate routing and maps grounding separately.
- **Spike M (Merchant):** single quote request via existing/mini merchant inbox; verify cross-session state, human approval, callbacks, unknown status, no fabricated confirmation.
- **Spike W (Web/Docling):** 3 permitted URLs including one official PDF; parse, cite, version and detect changed document.
- **Spike V (Voice):** 20 live phrases in noisy room; measure recognition, intent errors and stage fallback.
- **Spike N (Notifications):** manually trigger 2 events twice each; deliver **one** persisted message per event, respect quiet hours.
- **Spike H (Handoff):** build a copyable complaint draft + official link; verify return-to-case workflow without assuming session transfer.

Each spike outputs: evidence links, screenshots/recordings, status, cost, failure mode, confidence, recommendation, *decision needed*.

### Phase R2 — proposed implementation plan, not direct deployment

After owner approves scope, return **diff-oriented changes** against existing code, estimate dev time and dependencies, order by minimal changes and highest showcase value. Start with durable mission state and one real merchant flow, not mass third-party APIs.

### Explicit acceptance criteria

- [ ] Existing simulated demo remains intact and runs identically.
- [ ] At least one live bounded task uses real AI reasoning/tool selection, not a script-only switch.
- [ ] Separate pilot merchant accepts/acknowledges a request, changing correct user state.
- [ ] App restores user mission and proactive message after reload.
- [ ] Every paid/official/confirmed result is backed by legitimate source evidence or labelled `simulated_external`.
- [ ] Errors/timeouts/denied permission present safe recovery options.
- [ ] No unauthorized WhatsApp message, automated phone campaign, money transfer, or government filing occurs.
- [ ] Government/airport/sponsor branding appears only with verified permission or as clearly labelled concepts.
- [ ] A 4-minute stage cut works with a fallback path; at least one open-ended voice variation succeeds.

---

## 15. Research source register (checked 18 October 2026)

These are **entry points**, not assertions that the product has been integrated with the service. Provider terms and dates change; validate just before implementation.

| Area | Source | Key evidence / action |
|---|---|---|
| Google Cloud credit | https://docs.cloud.google.com/free/docs/free-cloud-features | $300/90-day eligible trial; product exclusions |
| Maps pricing | https://developers.google.com/maps/billing-and-pricing/pricing | Free monthly SKU usage caps and tiered costs |
| Places APIs | https://developers.google.com/maps/documentation/places/web-service/overview/ | Search, nearby, details |
| Places API terms | https://developers.google.com/maps/documentation/places/web-service/policies | Attribution, storage/content restrictions |
| Maps grounding | https://ai.google.dev/gemini-api/docs/maps-grounding | Gemini place-aware answers, not actions |
| Google Search grounding | https://ai.google.dev/gemini-api/docs/google-search | Grounded web responses/citations |
| Legacy Custom Search | https://developers.google.com/custom-search/v1/overview | Closed to new customers; transition before Jan 2027 |
| Gmail API OAuth | https://developers.google.com/workspace/gmail/api/auth/scopes | Sensitive/restricted OAuth scopes, verification/security assessment conditions |
| Amazon Creators API | https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction | Catalog/affiliate use, eligibility, not checkout API |
| Amazon migration | https://affiliate-program.amazon.com/creatorsapi/docs/en-us/migrating-to-creatorsapi-from-paapi | PA-API 5 deprecation and successor |
| Noon Partners | https://noon-docs.noonpartners.dev/ | Seller/partner catalog, orders, webhooks |
| Noon integrator OAuth | https://noon-docs.noonpartners.dev/docs/authorization/getting-credentials-oauth | Seller consent/delegated service accounts |
| Docling | https://github.com/docling-project/docling | Structured PDF/HTML/document conversion |
| UAE calling rules | https://u.ae/-/media/Information-and-services/Infrastructure/Cabinet-Resolution-No-56-of-2024-Concerning-the-Telemarketing-Regulations-1.pdf | Marketing calls compliance |
| UAE govt telecom overview | https://u.ae/en/information-and-services/infrastructure/telecommunications | Cabinet resolutions 56/57 |
| Ministry calling rules explanation | https://www.moet.gov.ae/en/-/ministry-of-economy-and-telecommunications-and-digital-government-regulatory-authority-review-regulatory-legislations-in-organizing-operational-mechanisms-for-telemarketing-companies-in-the-uae-and-enhancing-consumer-protection-in-line-with-best-practices | Licensed caller, 9am–6pm, consumer protections and automation caveat |
| UAE penalties | https://uaelegislation.gov.ae/en/legislations/2523 | Resolution 57/2024 remains listed active |
| WhatsApp Business | https://about.fb.com/news/2025/04/ways-to-manage-your-businesses-chats-on-whatsapp/ | Business-initiated templates, opt-in, messaging restrictions |
| WhatsApp policy index | https://whatsappbusiness.com/terms-and-conditions/ | Current business platform terms |
| Contest official page | https://www.dubaichamberdigital.com/en/create-ai-agents | Reconfirm registration and submission rules; do not rely on old dates |

### Research explicitly not completed

- Account-specific Google trial **balance, expiry, enabled APIs**; actual existing keys; usage costs.
- Confirmed Amazon UAE Associates/Creators credentials and current eligibility for this account.
- Consumer-facing Noon all-catalog availability, checkout/affiliate partner deal, or exact API scopes negotiated with Noon.
- Any actual RTA/police/airport/UAE PASS access, official ticket issuance, direct bank payment integration or visa workflow.
- Current repository code inspection, tests and deployment state (not accessible in this document-generation session).
- Formal **UAE legal opinion** on mass AI-initiated *business-to-business* calls, relevant licensing, recording/AI disclosure, and outreach source permissions.
- Current competition deadlines/IP/submission specifics; organizer verification is required.

---

## 16. Ten additional enhancement flags for reviewers

1. **Provenance drift:** Google/vendor listing freshness and demo fixture age can diverge; show timestamps and periodic recheck instead of silently converting estimates to promises.
2. **Mission ownership:** user changing identity or device must not expose taxi/visa/legal records to others; tenant isolation and revocation matter more than animation.
3. **Event race conditions:** manual double trigger, delayed webhook and user cancellation must not cause double purchases or duplicate notifications.
4. **Human cost explosion:** one human per blocked request is not sustainable at arbitrary volume; triage by severity and target a measured escalation rate.
5. **Voice scene mismatch:** presenter's narrative must not accidentally be ingested as a command; explicit listening mode, visual state and barge-in control.
6. **False “present now” geofence:** location/accelerometer transitions are probabilities; request confirmation before auto-delivery or ticket presentation.
7. **Fake partner credibility:** using famous brand/government logos plus mock checkouts may mislead; add a short stage disclosure and internal provider-state labels.
8. **Search result ownership:** a search result is evidence, not a provider relationship; price, license, coupon, capacity and booking must be independently confirmed.
9. **Stale official content:** cite document issue date, not just crawler date; don't use LLM summaries in place of an official policy or decision.
10. **Scope inflation:** “we can do 50 tasks” should become **one tested reusable contract** and a prioritized service registry; avoid fifty half-functional flows.

---

## 17. Final recommendation and next action

**Preserve the spectacular narrated Dubai experience** as product vision and persuasive storytelling. **Prove just one rigorous mission lifecycle** with real natural-language input, contextual memory, an approved tool, a separate provider acknowledgement, persistence, and a proactive update. Supplement it with official-source retrieval and a user-controlled handoff. This is the credible architecture beneath the promise that Dubai-io **does things**, rather than merely talks.

**Do not start with mass calling, financial transfers, official account writes, universal third-party checkout, or native always-on location.** These are contingent businesses and compliance projects, not general API toggles.

**Immediate ask to Claude/Codex:** *Perform Phase R0 READ-ONLY, produce the actual implementation gap matrix, challenge the D01–D18 recommendations with evidence, and propose the smallest safe change set. Stop for product-owner approval before coding.*

---

*End of Product Enhancement Review v1.0.*
