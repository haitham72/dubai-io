# Dubai-io — Championship MVP, Roadmap & Validation

**Purpose:** Preserve the expansive Dubai companion vision while shipping a small, reliable agent for the Dubai Create AI Agents Championship.  
**Date:** 8 October 2026. **All contest dates/rules must be rechecked against official organizers before submission.**
**Authority:** This file + `00-MVP-FREEZE.md` override `06/07/08` and the implementation plan on scope disputes. `06` is reference library, `07` is post-MVP vision, `08` is narrative synthesis — none add MVP scope.

## 1. Final product decision

- **Brand:** Dubai-io — *Your Intelligent Dubai Companion*.
- **Primary proposed category:** Best Personal AI Agent (subject to official category criteria).
- **MVP strategy:** Companion-first **plus** one real service integration and one official-source recovery workflow.
- **Do not rename this** to Civic Compliance Bot. Civic information is a trust layer, not the entire product.
- **Contest insight:** The user experience stays simple while new verified services can be added through an AI-assisted integration factory.

## 2. The three MVP capabilities

### A. Persistent Companion
- FastAPI/Next.js app with login and stored user conversations.
- Consent-based location/area preference, language, budget and recent task state.
- Single orchestrator choosing from approved tools.
- Typed action cards showing source, status and next action.
- Manual triggers first; **one real persisted proactive in-chat reminder** from a user-confirmed schedule is a small, valuable MVP extension. Test `trip.departure_soon` and optional provider status update. Background geofence/activity features depend on native mobile work and are not MVP blockers.

### B. Services Integration Factory (+ inner-HTML widget)
- Merchant onboarding form + import of CSV/catalog data.
- AI-assisted normalization, operator review and capability validation.
- Search/compare providers and services, with location where appropriate.
- **One real request flow:** user asks for laundry/cleaning quote; provider dashboard receives and acknowledges; user sees actual updated state. **Rendered as standard card first, inner-HTML widget second (sandboxed iframe + manifest v-pin + `fallback_card: service_comparison`). HTML posts intent; host executes.**
- A different merchant can be added without writing a new companion interface.

### C. Verified City Knowledge & Recovery
- Official-source retrieval (versioned pages/PDFs with jurisdiction, URLs and timestamps).
- User can attach receipt/order/photo as evidence.
- Clear consumer-problem guidance plus a sourced complaint draft and **official handoff**.
- Optional low-dependency extension: taxi lost-property evidence checklist or VAT refund deadline assistant.

## 3. 4-minute illustrative demo script

**0:00–0:30 — Context.** User says: “I'm in Marina until Sunday. I need five shirts ironed tomorrow.” Companion confirms missing inputs and shows permitted location context.  
**0:30–1:20 — Discovery.** Calls registry/search, shows provider comparison card with source/freshness and states whether prices are quotes or estimates.  
**1:20–2:10 — Real action.** User approves quote/pickup request; a test merchant receives it in a real dashboard and acknowledges; agent displays correlation ID and accurate request state.  
**2:10–3:10 — Recovery.** “The cleaner damaged my shirt.” The same conversation retrieves order details, organizes evidence and retrieves official consumer guidance with citations; creates a draft, not a fake government filing.  
**3:10–4:00 — Platform expansion.** An operator imports another authorized merchant; AI maps fields; human approves; the same search/action cards can discover the new service.  

If development remains on schedule, add a **short optional follow-up clip**: trip scheduled -> event fires -> the assistant sends a persisted reminder card and opens an already-saved checklist. Do not displace the actual merchant flow, and do not fake background geofence support in a browser.

Demo can use a **clearly labelled consenting pilot merchant**; no fictional discounts or government integrations. A test merchant may be a sandbox service, but show it as sandbox, not commercial fulfillment.

## 4. Delivery schedule (proposed)

| Phase | Goal | Exit condition |
|---|---|---|
| Oct 8–18 | Finalize spec, check official competition registration/IP and data sources | Written scope, current rule links, first evaluation cases |
| Oct 19–Nov 8 | Persistent app and orchestrator | Two tool calls + typed card + stored authorized context |
| Nov 9–29 | Registry and merchant flow | Provider onboarding and real acknowledgement to user |
| Nov 30–Dec 20 | Civic RAG, privacy, partner/user tests | Sourced answer suite, audit logs and consent tests |
| Dec–Jan | Submission quality + video/deck | Repeatable live flow, source inventory, working fallbacks |
| Feb–May (if selected) | Hardening + genuine user traction | Independent user evidence and failure-resistant live demo |

Avoid a schedule in which payment, E2EE messaging, social platform moderation or government account integrations become critical paths.

## 5. Evaluation gates (targets, not achieved metrics)

| Test | Target |
|---|---|
| Scripted end-to-end tasks | >=30 varied test cases |
| Service request state consistency | No fabricated `CONFIRMED`, `PAID`, `COMPLETED` |
| Merchant request | At least one externally acknowledged request |
| Official RAG | >=95% fully supported answers on independently checked corpus-based evals |
| Provider API faults | Correct timeout/fallback and `UNKNOWN_STATUS` handling |
| Permission tests | No cross-user/media leakage, denied actions blocked |
| User pilot | 20–30 testers, evidence of useful time saved |
| Merchant pilot | 3–5 willing providers, measured acceptance/time-to-response |

Don't call these facts or achievements until measured. Log task completion rates, tool errors, cost, latency, user dropout, citations and incidents.

## 6. What is deliberately **not** in the contest MVP

Full Reddit-like social network, universal peer messaging, E2EE media platform, indexed personal video vault, integrated payments/escrow, medical insurance approvals, **reliable background geofencing and motion inference in a PWA**, live indoor GPS/venue routing without authorized maps, guaranteed vouchers, government account write APIs and country-spanning VAT flows.

Keep contracts and extension points for these; do not deliver half-functional versions as supposed proof of completion.

## 7. Research and verification register (must resolve)

| Question | Why it matters | Source to verify |
|---|---|---|
| Exact application and prototype deadlines | Avoid missing entry | `https://www.dubaichamberdigital.com/en/create-ai-agents` |
| Competition category, judging, IP and submission artifacts | Determines demo and employment ownership risk | Official rules and FAQ |
| Merchant registration and legal obligations | Safe provider marketplace | UAE/Dubai licensing and consumer regulations |
| Digital Dubai / Dubai Pulse access and redistribution rights | Avoid assumed backend government API permissions | `https://developer.dubai.gov.ae/` and provider terms |
| RTA/Parkin/Salik live API authorization | Distinguish link/estimate from payment | Official RTA/Parkin/Salik developer policies |
| Dubai Consumer Rights complaint process and current law | Correct civic assistance | `https://consumerrights.gov.ae/en/` and official legislation |
| Mapping/Places storage and attribution | License-compliant catalog | Google Maps Platform policy |
| UAE privacy rules and social/chat requirements | Permissions, moderation, data residency and user rights | Current official UAE regulatory sources |
| Multimodal embedding model naming/license and temporal accuracy | Future private media vault | Current official model card/benchmarks |
| iOS/Android background geofence and activity signal policy | Native module vs PWA scope, OS limitations and privacy | Official Apple/Android developer documentation |
| Venue floor maps, indoor directory and commercial reuse | Can we generate a styled route without violating licenses? | Individual venue/map provider terms |
| Family tickets and barcodes | Only display real authorized documents | Issuer API/terms and purchaser records |
| UAE PASS/Aani integration rights | Avoid invented onboarding and payment flows | Official providers and agreements |

**Particular claims requiring verification before any UX copy:** exact smart gate eligibility/direction, baggage belt, parking zone and price, Salik schedule, taxi base fare, departure kiosk locations, operator discounts, medical documents, official fines, and guaranteed delivery times.

## 8. Risks and mitigations

- **Scope overload:** freeze MVP to three capabilities with strict exit tests.
- **Merchant cold start:** recruit a few genuine cooperating providers early; no fake accounts/reviews.
- **Partner API absence:** build legitimate handoffs and merchant portal instead of simulated direct bookings.
- **Civic RAG hallucinations:** versioned official sources, citation verification, human escalation.
- **Cost/rate limits:** provider timeouts, cache permitted static content, bounded tools and model calls.
- **Sensitive data:** scoped auth, minimum retention, export/deletion process, no cross-tenant embeddings.
- **Demo reliability:** test with blocked/stale API fixtures; show unknown rather than success without receipt.

## 9. Acceptance decision

**GO** if the team can demonstrate: (a) one coherent user journey, (b) a real service action or truthful partner handoff, (c) source-grounded civic guidance, (d) a new provider integrated through a repeatable workflow, and (e) measured user value.

**NARROW FURTHER** if provider access stalls: retain a real provider-operated request portal and focus on supported discovery, task tracking and official-source recovery. Do not pivot the entire product to a fines-only bot.

## 10. Post-MVP: Proactive Companion capability track

**Preserve this as a first-class architectural capability; do not allow it to quietly expand contest scope.**

| Milestone | Feature | Acceptance evidence |
|---|---|---|
| P0 / core | Persist system-initiated assistant messages in the existing chat history | User returns and still sees event notification and attached card |
| P1 / contest stretch | Scheduled “trip starts in 10 minutes” reminder with checklist, timezone, snooze and notification consent | Event logged once, message deduped, correct target trip and no false claims |
| P2 / early app | Provider-authenticated order updates and delivery-window messages | Order mapped to correct user, webhook validated, delivery status labelled accurately |
| P3 / native mobile | User-consented departure/arrival geofencing and driving-to-walking transition | OS-permitted activity events, measurable false-positive rate, easy opt-out |
| P4 / venue integration | Landmark-based indoor map and user-confirmed steps | Current licensed floor/POI data; route QA, uncertain start-state correction |
| P5 / user memory | Parking photo + level/pillar recall in conversation | Photo access controls, exact record retrieval, delete/export tests |
| P6 / ticket wallet | Family ticket card on destination approach | Issuer-provided ticket asset and per-person authorization; expiry and cancellation tests |

**Scope priority when constrained:** Persistent messaging and scheduled reminder first; manual parking photo and trip checklist can ship without sensors. Real background event sensing, licensed indoor maps and issuing/aggregating third-party ticket credentials are separate integration projects.

**Failure cases:** missing push permission -> still display chat message; stale provider update -> show `as_of`/estimate; geofence false positive -> ask confirmation; no floor plan -> open official directory; missing ticket -> say unavailable and link official booking.
