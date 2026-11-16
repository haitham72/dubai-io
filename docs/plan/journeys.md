# DubaiIO: Useful Journeys and Demo Design

**Status (9 Nov 2026):** Do-pillar journey research; identity in `PLAN.md` §1.

**Updated:** 29 Oct 2026 (moved to docs/plan; website-first on main)

**Branch:** main
**Status:** Product design and researched source opportunities. This document does not claim these journeys are implemented. Runtime status remains in `docs/status.md`; implementation scope remains in `PLAN.md`.

## 1. Founder direction

The product owns a useful outcome across preparation, travel, services, decisions and follow-through. Its value comes from keeping the whole situation in mind and coordinating the next step.

Founder statements, 26 Oct:

> flight: i can use normal bookings from open api

> parking: there is a new app called parkin

> khda: that was super idea, this goes higher in the demo, fantastic idea i love it

> what does my insurance allow me to go for a hospital neaer me quickly?

> for insurance i rememeber that i kept for hours calling insurance and presenting my insurance card level and recieved an email for allowed hospitals that had many levels that mine happened to be 'B+' category and i had to manually check

> parking: user wouldnt open dubai-io for the sole purpose of 'finding parking spot' no, it would prepare the trip for 'mamzar beach' -> already prepared items from noon-now with beach toys in 15 minutes -> prepare trip using maps -> book parking tickets/parking rta -> when reached prepare qr code for entry -> go back find a hot meal waiting

> all of this with user pressing y/n on steps or y to all

*(Superseded 9 Nov by the founder: no "y to all". Rule 6 strict: one explicit tap per side effect.)*

> i am discussing the app design not necessarily the api endpoint

> even if an api doesnt exist there is an option that i invest to create it with a service if it is needed down the line

> investigate how the app can actually help more, as chatgpt can answer questions aswell, but not actually book or purchase

**Design consequence:** define the desired journey first. A public API, a provider integration, an MCP tool, a reusable skill, a document workflow or a service commissioned by the founder may supply a capability. Current endpoint availability affects delivery sequencing, not whether an idea belongs in the product design.

KHDA is promoted to a leading demo candidate. Insurance navigation is a second leading candidate grounded in the founder's own experience. The beach outing is the reference for how individual services become one coordinated journey. The additional journeys below are proposals for selection.

## 2. The shared experience

1. **Understand the outcome.** Ask for the few constraints that change the plan. Reuse relevant facts the user has explicitly saved.
2. **Prepare together.** Assemble options, costs, dependencies and timing into one understandable plan. Work on independent steps in parallel.
3. **Approve simply.** Offer Yes / No / Change on each step of the displayed plan; every side effect gets its own explicit tap (rule 6 strict, founder 9 Nov; no Yes to all). A declined step should revise the plan without discarding the whole task.
4. **Carry it forward.** Keep bookings, route, documents, tickets, receipts and unresolved decisions together in the task and its chat.
5. **Adapt when something changes.** Recalculate downstream timing and surface the decision that needs the user. Preserve already confirmed arrangements.
6. **Finish the outcome.** Follow through to the meal arriving, reimbursement pack being ready, or the moving checklist being completed; retain the evidence and useful context.

### Execution value and the current competitive baseline

Research on 26 Oct changes the comparison: OpenAI documents website booking/payment actions through ChatGPT Work, subject to access, rollout and confirmation. Approved commerce partners can also support checkout inside ChatGPT. It would be inaccurate to base the pitch on a blanket claim that ChatGPT cannot book or purchase. Sources: [ChatGPT browser capabilities](https://learn.chatgpt.com/docs/browser), [commerce](https://developers.openai.com/commerce/guides/key-concepts).

Careem already offers several daily-service categories and publishes agent tools for ordering, checkout and tracking. Production access needs review, and its sandbox produces scenario responses rather than real orders. A catalogue of service buttons or a generic booking tool is therefore an insufficient differentiation claim. Sources: [Careem MCP](https://builders.careem.com/), [production access](https://builders.careem.com/request-access/), [sandbox](https://builders.careem.com/docs/sandbox/).

**Product hypothesis to validate:** DubaiIO completes selected Dubai journeys with fewer user calls, repeated explanations, app switches and interventions, and follows through when providers or timing change. Local supplier access, a reusable understanding of the user's exact constraints, reliable execution and accountable recovery are potential advantages to build and measure. None is claimed as a proven exclusive capability.

### What must actually happen after approval

| Journey | Concrete execution target | Evidence the user gets | Recovery that remains part of the job |
|---|---|---|---|
| KHDA / schools | Send approved admissions enquiries, obtain tour appointments, coordinate the visits and track applications the user chooses to pursue. | School replies, appointment references, dated costs and the next decision. Admission remains the school's decision. | Chase an unanswered enquiry through an approved channel; resolve conflicting visits; substitute another shortlisted school when appropriate. |
| Insurance / visit | Obtain the exact branch/service eligibility response and arrange the chosen appointment; coordinate travel if requested. | Insurer/provider response, any approval reference, appointment confirmation and the user's next required step. | Resolve a missing referral or unclear network match; search another eligible appointment if the first is unavailable. Clinical decisions remain with professionals. |
| Mamzar outing | Purchase approved essentials, arrange the selected parking/entry products, and place the approved meal order in coordination with the return plan. | Merchant order references, issued passes, fulfilment updates and meal status. | Handle an unavailable item, delayed delivery, changed return time or cancelled reservation within the approved alternatives. |
| Guests arriving tonight | Book the selected fixed-price cleaning/laundry service, purchase approved supplies and coordinate food against the arrival deadline. | Confirmed service window, order receipts and completion updates. | Replace an unavailable slot, show what still fits the deadline, and revise dependent orders. |
| Business trip | Book the selected travel products and approved home/airport services, retain itinerary and receipts, then coordinate changes and the return home. | Ticket/booking confirmations and a unified task timeline. | Rework affected transfers/services after a disruption; show cancellation fees and request approval when needed. |
| Reimbursement | Submit the reviewed pack through a permitted channel and continue tracking missing-document requests and the resulting decision. | Submission receipt, outstanding items and settlement/decline evidence from the payer. | Request the missing receipt or signature with approval; follow up on the actual response. An estimated claim is never a guaranteed refund. |
| Repair / breakdown | Arrange the selected assistance/repair route and onward transport; track the vehicle or home-service job through collection/completion. | Provider acceptance, appointment/job reference and progress evidence. | Handle a provider no-show or missed window and offer the approved alternative. |

These are future execution targets, not current wired capabilities. An answer, a prepared form, a pending request and a confirmed booking are separate useful states; the interface must show which was actually achieved.

### Build a service where the missing capability matters

The founder is willing to invest in a service connection. Evaluate that investment by the complete job it unlocks. A small provider-facing operation could receive an approved request, check eligibility or availability, obtain a confirmation from the relevant organisation and return status updates to the app. Start with a limited set of providers and an explicit service promise. Human assistance can supply some steps initially if its role is visible.

For example, a school-admissions coordination service could maintain contact routes, organise approved enquiries and visits, and return school confirmations. An insurance access service could maintain network mappings and obtain member-specific answers through permitted insurer/provider channels. Neither service can grant a school place or coverage independently of the authoritative organisation.

The user experiences one continuing task. The app keeps execution records and coordinates dependencies; the delivery team chooses provider connections, reusable skills, MCP tools or disclosed operations assistance behind that experience. A skill or MCP wrapper alone does not establish fulfilment.

### How to prove the difference

- Compare the same real task using ChatGPT plus the user's usual apps and DubaiIO; do not assume the general assistant fails.
- Measure user time, calls, app switches, repeated information entry and interventions until the chosen job is completed.
- Count confirmed outcomes and unresolved/partially completed steps. Record time waiting for a provider separately from the user's effort.
- Include a disruption: unavailable item, delayed provider, rejected slot or changed departure. Evaluate how much work the user must do to recover.
- Keep visible source and provider evidence so the result is assessable. No invented savings, success rates or competitor limitations.

### One tap per side effect

The user sees a clear plan with its actions, prices, timing, necessary information sharing and permitted alternatives. Each step with a side effect (a share, send, order or booking) is approved with its own explicit tap on an approval card listing exactly the fields and amount. The assistant then performs each approved step as its dependencies become ready. It asks again, with a new tap, when a material change falls outside that approval, such as a higher total, different recipient or unavailable preferred option.

Optional steps remain independently selectable. An unchanged step should not repeatedly demand approval. Any real booking or completion shown in the app must have provider evidence. A demo can use labelled staged provider events while presenting the intended complete experience.

Founder decision, 9 Nov: rule 6 strict. There is no "Yes to all" or batch approval; this matches the current per-action approval engine. This document does not authorize real purchases or external messages now.

## 3. Leading journey: choose schools and a home together

**Illustrative request:** "We are moving to Dubai. My children need Year 3 and Year 7, British curriculum. Help me find schools we can afford and somewhere to live with a manageable school run."

### Experience

1. Capture exact curriculum/year groups, combined school budget, intended start term, work location and preferred maximum journey time. Keep rent and education budgets separate unless the user gives one combined budget.
2. Shortlist schools that actually offer both year groups. Explain the fit using the user's priorities, the dated KHDA inspection result and published fees.
3. Compare the full education cost: tuition by year group, published mandatory charges and any selected extras. Flag costs still awaiting a school answer. Apply sibling discounts only when documented for that school and family situation.
4. Make the trade-off visible: the stronger inspection result, shorter school run or lower combined cost may lead to different choices. Inclusion and wellbeing information can be shown without inferring a child's needs.
5. Compare suitable residential areas using DLD registered-rent evidence and route estimates for the intended school/work times. Use current property listings separately when available. A registered rent is a historical comparison, not an available apartment.
6. With approval, request the chosen school visits and coordinate school-confirmed appointments, travel, parking and questions to ask. Keep a request pending until the school confirms. GEMS Metropole, for example, publishes tour times and a mandatory pre-booking route; KHDA supplies comparison evidence, while the school supplies the appointment.
7. Save the shortlist and carry out the user's approved next steps through the selected delivery service: enquiries, document preparation, chosen applications and reminders. Track replies and missing items; do not leave the user to repeat the research across each school.
8. Revisit the plan when a school answers or the user changes a constraint. Keep confirmed choices and show what changed.

**Why it is valuable:** parents can assess school, home, money and daily travel as one decision. The assistant continues from research into the practical move.

**Useful evidence:** KHDA directory, school detail pages, fee sheets and academic calendars; school admissions responses; DLD registered transactions; maps/routes; user-supplied budgets and dates.

**Important source details:** preserve the inspection year, fee academic year and selected branch. Do not treat Year 5 and Grade 5 as interchangeable. A school offering a year group does not establish that a seat is available.

## 4. Leading journey: where can I go with my insurance?

**Founder problem:** hours of calls and manual searching through a provider list for the correct B+ category.

**Illustrative request:** "Here is my insurance card and the hospital list they emailed me. Which suitable nearby branch can I visit under my plan?"

### Experience

1. Read the card and insurer/claims-administrator material supplied by the user. Confirm the insurer, administrator, exact network/category and policy dates. B+ is an exact source label to match, not a universal insurance tier or a hospital quality grade.
2. Read the provider spreadsheet, PDF, email attachment or member-specific directory. Preserve its date, legend, exclusions and branch identifiers. Have the user confirm ambiguous card text or column headers.
3. Match the exact category deterministically to the provider rows. Distinguish a positive match, an exclusion and an unknown; a blank cell is not approval. Do not substitute the insurance company's name for the actual network.
4. Resolve the matched facility branches on a map. Rank appropriate options by the user's requested service, travel time, opening hours and stated preferences. Coverage matching and route ranking remain separate steps.
5. Present a compact result: branch, distance/route estimate, why it matches the network, source date, direct-billing status where documented, and anything still requiring confirmation.
6. Check the particular visit against available benefit documents and insurer/provider confirmation: outpatient versus inpatient, referral, pre-authorisation and patient contribution. Network membership alone does not guarantee that a particular treatment will be paid.
7. With approval, arrange the chosen visit through the selected provider/service, share only the agreed details, and coordinate the route and documents. Keep an unanswered booking request pending; retain the provider's confirmation when it arrives. Medcare publishes appointment booking and warns that accepted insurance differs by branch, supporting the need to connect eligibility verification to the booking.
8. Keep any receipt, approval reference or follow-up task together for the user. Offer a reimbursement checklist when relevant.

**Skills and connections:** a reusable workflow can read documents, match the network column, resolve branch locations, build a map and prepare a verification request. A first version can work from the user's existing provider list. A live eligibility connection or a service commissioned by the founder can later update and confirm the answer. An MCP connection is one possible interface to that service; it does not itself grant insurer access.

**Product boundary:** this is healthcare access and insurance administration. Clinical assessment and treatment decisions remain with qualified professionals. Use the exact source wording for coverage; the final coverage decision belongs to the insurer/provider. Keep policy identifiers out of public map/search queries and never infer health conditions from this activity. Let the user choose whether documents are retained for future use.

**Why it is valuable:** a complex table becomes a short, usable list at the moment someone needs care, while preserving the distinction between a network match and confirmed eligibility.

## 5. Reference journey: Mamzar beach day, from preparation to dinner

**Illustrative request:** "Prepare a Mamzar beach afternoon for us. We need beach toys and I want a hot meal at home when we get back."

| Stage | Assistant coordinates | What the user sees or decides |
|---|---|---|
| Prepare | Check the user's party, timing, budget, beach essentials already owned and meal preferences. Assemble the missing items and a delivery slot using a suitable merchant such as Noon Now. | Review basket, published prices and provider delivery estimate. The founder's 15-minute delivery is a scenario target that needs the merchant's current confirmation. |
| Plan | Choose the destination/entrance and route; align departure with supplies arriving. Include travel, parking and entry arrangements appropriate to the selected beach area. | One trip plan with costs and timing; approve each step with its own tap. |
| Arrange | Obtain approved supplies and available parking/entry products through the appropriate providers. | Confirmations and receipts appear within the same outing. |
| Leave | Present the route and what is ready; flag a supply delay or changed travel time that affects departure. | Leave now / Change departure / Skip the delayed item. |
| Arrive | Bring forward the parking details and provider-issued entry pass or QR code when that entrance requires one. | The useful ticket or pass is immediately accessible. |
| Enjoy | Keep the return plan and meal timing available. React to a user change such as "stay another hour." | One concise decision if the change affects an approved commitment. |
| Return | Coordinate the meal with a confirmed return plan, route estimate and kitchen/delivery lead time. | Dinner follows the updated arrival plan; a traffic estimate alone never becomes a claim that food is ready. |
| Finish | Collect completion evidence and let the user save preferences they want reused. | An outing record with receipts and useful next-time choices. |

Parkin belongs inside this journey and similar visits, work trips and appointments. Its own report describes parking availability in the consumer app. The delivery mechanism for a future DubaiIO connection can be selected when implementing the journey. A map pin, a parking payment and a reserved space are different provider outcomes.

Entry and parking arrangements depend on the selected destination and operator. The experience uses the pass that is actually issued; it never manufactures a valid-looking entry QR.

## 6. More high-value journeys

These are outcome proposals. Their rank reflects relevance to the founder's examples, not a claim of implementation or established provider access.

| Priority | User need | Complete useful journey | Research / evidence basis |
|---|---|---|---|
| High | "I paid for care. Help me get the reimbursement paperwork right." | Gather receipts and the applicable claim rules; identify missing documents/signatures; prepare a reviewed claim pack; track the user's submission receipt and follow-up. | Insurer claim forms and the actual member handbook. GIG documents demonstrate this process and that the applicable policy sets the claim deadline. Approval and reimbursement amount remain insurer decisions. |
| High | "My car broke down and I still need to reach work." | Find the policy's assistance route and entitled repair network; prepare the location/call; coordinate transport and any eligible replacement-car process; retain repair and collection updates. | The user's motor policy and insurer's current assistance/claims guide. Policy-specific entitlements and provider confirmations control each promise. |
| High | "I am moving on Saturday. Make sure the essentials join up." | Turn the tenancy and move date into a sequence covering building access, movers, utilities, internet, supplies and first-night food; avoid scheduling work before prerequisites are ready. | DEWA Move To and du relocation guidance establish real dependencies and official handoffs. Building/mover arrangements require their own evidence. |
| High | "Prepare my business trip and my return home." | Use booking-provider itinerary details for flight choices or an existing trip; prepare packing, work tasks, airport travel, parking and documents; revise the return ride and meal when the plan changes. | Booking APIs such as Duffel support offers/orders. Live flight status uses an appropriate status source. Ticket issue, refunds and cancellations are distinct approved provider actions. |
| High | "The school shortlist works. Now get us ready for term." | Use the selected school calendar, actual supply list and fee schedule to prepare uniform/books, transport questions, forms, payment reminders and the first-week plan. | KHDA calendar and fee links plus school-specific published or user-supplied material. Do not assume all schools share dates, supplies or bus routes. |
| Medium | "Can my employer reimburse these school or travel costs?" | Read the employer's policy and relevant receipts; identify applicable conditions and missing evidence; prepare a reviewed request and track the employer's response. | User-supplied employer policy and correspondence; employer approval remains authoritative. No entitlement or amount is invented. |
| Medium | "Help me check this property before I commit." | Assemble DLD broker/project checks, registered-rent comparisons, the relevant service-charge information and a visit checklist; keep unresolved questions together for the user. | DLD publishes official enquiry services. The assistant presents records and routes the user to official checks; a record match is not a guarantee about a deal. |
| Medium | "The AC failed and guests arrive tonight." | Arrange an available fixed-price service visit, check user-supplied landlord/maintenance responsibilities, plan access, and coordinate any chosen temporary alternative and later follow-up. | Existing fixed-price merchant pattern, user documents and provider events. Preserve the prohibition on bidding, quotes and negotiation. |
| Medium | "Plan a useful afternoon near school pickup." | Combine a suitable Dubai library/park/activity, actual published hours, the pickup deadline, travel and a meal plan. | Dubai Culture and Municipality sources plus relevant provider schedules. Use Dubai sources for Dubai facilities; availability and reservations need their own confirmation. |

The common benefit is converting documents, conditions and scattered services into a coordinated plan that persists until the user's chosen outcome is handled.

## 7. Demo design

**Recommended leading demonstration:** school choice that develops into a practical home/visit plan. The founder has explicitly promoted KHDA. A family scenario is illustrative; parenthood is never inferred for a real user.

**Second leading demonstration:** the founder's insurance experience. Let the audience see a complicated network table become matched branches on a map, with the source row available to inspect. Then prepare the next action.

**Coordination demonstration:** the Mamzar outing. Show supplies, travel, parking/entry and dinner changing together after one request such as "we will stay an extra hour."

**Agentic moment:** the user changes a constraint after approving a plan's steps. The assistant preserves completed steps, identifies dependent work, revises the plan and requests only the necessary new decision. Avoid a sequence of unrelated search screens.

**Approval moment:** show stepwise Yes/No for the concrete displayed plan, one explicit tap per side effect (no Yes to all; founder 9 Nov). Track approved, waiting, confirmed and completed states using actual or clearly staged evidence.

**UAE PASS:** an optional identity demonstration if it serves a selected journey. It is not a prerequisite for showing value in KHDA comparison or a user-supplied insurance document workflow.

## 8. Source opportunities and delivery maturity

Sources checked 26 Oct 2026. Published information is evidence of the source content, not proof of a working DubaiIO adapter.

| Source | What is established in this research | What remains to deliver |
|---|---|---|
| KHDA directory, school pages, fee sheets and calendars | Published school facts and linked documents support comparison. Inspection and fee years vary. | Reliable extraction, entity matching, source rights/freshness handling and a verified comparison experience. |
| Neuron FAQ | Eligible provider categories are tabulated Yes/No; clients receive monthly network lists. | The user's exact current network list and any member-specific eligibility confirmation. |
| Nextcare network updates and FAQ | Policy-specific provider access is available through the member app. | Consented data access or user-provided material; the chosen future verification service. |
| Hospital branch insurance pages | Accepted plans and direct-billing information can be branch-specific. | Reconcile against the member's exact plan and current insurer/provider answer. |
| Parkin consumer app and company report | Parking discovery and related consumer services are documented, including availability in its app. | Choose app handoff, a permitted provider connection or a commissioned service when delivering the coordinated journey. |
| DLD | Registered property data and official enquiry tools are published. | Selected samples, methodology, current source dates and appropriately designed official handoffs. |
| Booking providers / flight status | Separate provider categories can supply booking and operational flight facts. | Select coverage, account and suitable production/test mode; preserve the source's actual limitations. |
| Bayanat, Data.Dubai, Municipality and other emirate portals | Source catalogues exist; the value depends on the selected records. | Verify a useful resource and its fields; do not repeat an unverified dataset count or blanket anonymous-access claim. |

**Delivery progression:** a curated sourced demo can establish the experience; reliable document workflows and selected integrations can support a pilot; live member-specific verification and commissioned service connections can follow. APIs, MCP tools and skills are implementation choices beneath the journey.

A reusable skill describes how to handle a task. A connector or service provides access to external facts and actions. Neither by itself supplies a commercial agreement, current entitlement or provider confirmation.

## 9. Original scenario ideas retained

The earlier thirteen ideas remain available as inputs. Their fabricated sample amounts, distances, violation histories and vacancy counts have been removed from the current script.

| Original idea | Revised treatment |
|---|---|
| Taxi lost item | Preserve the implemented receipt/cash intake, official handoff and labelled staged replies. Delivery stays unavailable in the current checkpoint. Future provider recovery services are a separate proposal. |
| Car rental | A travel-journey component with explicit provider inventory, approval and confirmation. |
| Multi-stop trip | Develop as coordinated work across appointments, travel and the return home. |
| Late-night arrival | Use booking/flight-status sources, applicable RTA timings and route estimates; keep airport positions user-confirmed. |
| Restaurant safety | A future sourced decision input if an appropriate record is obtained. No invented restaurant violations or inspection history. |
| Parking | Embed in outings and appointments, with Parkin considered as a provider. |
| Rent versus buy | Use DLD evidence and explicit cost assumptions; a price index alone cannot establish unit-level costs or a personal breakeven. |
| Renovation materials | Supplement an explicit quantities/budget exercise with dated published prices; avoid unsupported whole-project totals. |
| Hospital locator | Promote to the exact-insurance-network journey. |
| School finder | Promote to the leading KHDA school/home journey. |
| Mosque locator | An optional user-requested trip component using appropriate location/time sources; no inferred religion. |
| Library locator | A family/study-day component using Dubai Culture evidence for Dubai locations. |
| Neighbourhood research | Support the school/home decision with available geography-specific records; no invented family, crime or demographic percentages. |

## 10. Next design and delivery work

1. Refine the KHDA, insurance and Mamzar stories as complete conversations and task timelines, ending in the selected concrete execution target above.
2. Choose one pilot with a limited provider set, a named delivery owner and a measurable completion result. Identify which provider-confirmed events are real and which events must be labelled staged in a demo.
3. Design the shared plan card, Yes/No/Change controls, one approval tap per side effect, documents/map/ticket presentation and response to changed timing.
4. Validate the smallest useful evidence package for the selected pilot: a few school pages/fee sheets or one consented insurance network list and benefit document.
5. Deliver the selected read/compare/plan slice within the approved app surfaces, then add the chosen connections in dependency order.
6. Reconcile new execution requirements explicitly before implementation; batch approval is out (founder 9 Nov, one tap per side effect). Government execution, real external sends and purchases are not authorized merely by discussing this design; they run only through a real registered adapter with explicit per-action approval and verified provider evidence (rule 4).
7. Test the pilot against the user's current process and ChatGPT plus ordinary apps. Prioritise successful follow-through and recovery before expanding the service catalogue.

## References

- [KHDA school directory](https://web.khda.gov.ae/en/Education-Directory/schools)
- [KHDA school fee sheets](https://web.khda.gov.ae/en/Guides/Parents/Schools-Fees-Fact-Sheet-FAQs)
- [Neuron network eligibility FAQ](https://www.neuron.ae/faq/)
- [Nextcare member provider search FAQ](https://www.nextcarehealth.com/faqs/)
- [Nextcare network updates](https://www.nextcarehealth.com/network-updates/)
- [Mediclinic Al Qusais insurance information](https://www.mediclinic.ae/en/al-qusais/your-visit/insurance.html)
- [GIG Gulf member/claims FAQ](https://www.giggulf.ae/en/personal/frequently-asked-questions)
- [GIG Gulf policy document selection](https://www.giggulf.ae/en/personal/products/health-insurance/policy-documents)
- [Parkin official site](https://www.parkin.ae/)
- [Parkin 2025 annual report, published 2026](https://feeds.dfm.ae/documents/2026/Mar/16/3730076e-02f7-44ef-95a5-ae46be61436e/Parkin%20Annual%20Report%202025%20ENG%20v2.pdf)
- [DLD real-estate data](https://dubailand.gov.ae/en/open-data/real-estate-data/)
- [DLD official enquiries](https://dubailand.gov.ae/en/how-do-i/)
- [DEWA Move To](https://www.dewa.gov.ae/en/consumer/supply-management/transfer-of-electricity-water-move-to)
- [du home relocation](https://www.du.ae/personal/at-home/moving-to-a-new-home)
- [Sukoon motor claims guide](https://www.sukoon.com/-/media/OIC/OIC%20Media/OIC%20Documents/Other%20System%20Documents/Claims%20-%20Motor%20Comprehensive%20Claims%20Guide)
- [Duffel flight orders](https://duffel.com/docs/api/v2/orders)
- [Duffel test-mode limitations](https://duffel.com/docs/api/overview/test-mode)
- [Dubai Culture public libraries service directory](https://dubaiculture.gov.ae/-/media/DC/E-Services/Guides/Dubai-Culture-and-Arts-Authority-English-Language-Directory-Of-Services.pdf)
- [Data.Dubai description](https://www.digitaldubai.ae/apps-services/details/data.dubai)
- [Dubai Municipality open data](https://www.dm.gov.ae/open-data2/)
- [UAE PASS POC credentials](https://docs.uaepass.ae/quick-start-guide-uae-pass-staging-environment/testing-credentials-for-poc)
- [ChatGPT Work website booking/payment capabilities](https://learn.chatgpt.com/docs/browser)
- [ChatGPT commerce and partner checkout](https://developers.openai.com/commerce/guides/key-concepts)
- [Careem tools for agents](https://builders.careem.com/)
- [Careem production review](https://builders.careem.com/request-access/)
- [Careem scenario sandbox](https://builders.careem.com/docs/sandbox/)
- [GEMS Metropole school tour booking](https://www.gemsmetropoleschool-dubai.com/en/Admissions/Virtual-Admissions-Centre)
- [Medcare booking and branch-specific insurance information](https://medcare.ae/en)
