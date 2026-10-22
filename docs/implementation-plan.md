# Detailed implementation plan

Execution detail for the authoritative [PLAN.md](../PLAN.md). This is the durable task breakdown, not a second scope document. Updated 22 Oct 2026 after temporal qualification/trusted discovery and the founder's product-direction change. The active planning proposal is [personal-assistant-direction.md](references/personal-assistant-direction.md). Consult code to establish progress; never infer that a proposal or service case is implemented.

## 0. Decisions that survive a session change

1. Build a **personal assistant for everyday life and work in Dubai**. The 22 Oct founder instruction supersedes the short-stay visitor/hotel-concierge persona. Ongoing responsibilities, communication, plans and local follow-through are the proposed product; Maps is one surface and arrival is one optional situation.
2. Finish an active task before moving to another. New messages refine it or enter the request ledger. Record any logical reordering in the same session. Answer questions before treating them as implementation instructions.
3. **Current order, revised 22 Oct:** first complete product reframing and feature/pilot selection informed by Dots, Grok Bot and Duet. PA-01/02/03 (responsibilities, Today/decisions, context) plus bounded PC-05 deliverables are the proposed foundation; PC-01/02/03 and PA-04/PC-04 stage connected outcomes, routines and optional channels. These are proposals, not automatic implementation authorization. All earlier REC/CTX/PLAN/SUG/EVT/ADS/REV/DB tasks remain preserved and should be mapped as dependencies after selection. Do not resume the older recommender-first order silently.
4. **Google OAuth is last.** There is one tester. Existing server-owned cookie sessions remain valid; never introduce a public `tester` owner override. Missing Google sign-in credentials must not block profiling, planning or discovery. Google API keys are separate from OAuth.
5. **Native features are parked.** The founder will test on a Mac and iPhone 13 Pro Max. Do not install Windows Swift, force Expo, or divert back to native work. `ios-swift` contains the first client; `handoff-ios.md` records its remaining parity work.
6. Preserve Wi-Fi concept onboarding, slow gradients, cyan and approved purple fringe, no shadows, one category row with Back, explicit 2D/3D selection, and the browse dock that collapses into one chat composer.
7. Keep FastAPI/LangGraph, the deterministic action engine, fixed published prices, approval snapshots, idempotency, outbox and SSE. Supabase supplies Postgres and later Auth/Storage/Edge integrations. Do not rewrite orchestration into Edge Functions just to use another service.
8. No bidding, purchasing/payments, government execution, invented locations/statuses or fake provider integrations. Provider access limits produce a truthful draft/handoff, not a fake Send or a dead TBD button. No provider applications/outreach without an explicit request.

## 1. Database foundation — local checkpoint reached

### DB-01. Local Supabase [implemented and verified]

- Dedicated project `dubai-io`; API 15421, Postgres 15422, Studio 15423, mail 15424, Edge inspector 15428. Original `dubaiio-db` and other projects are separate.
- Versioned migrations in `supabase/migrations`; backend-only `dubaiio` schema excluded from the Data API. Browser roles cannot read it. RLS is enabled on the versioned business tables; checkpoint tables remain protected by private schema permissions.
- `app/db.py` applies `DATABASE_SCHEMA`, preserves explicit connection options, includes `extensions` on the Supabase path, and bounds connection establishment. LangGraph uses the same backend schema.
- Local API at port 8000 uses this database. SQLite review records, including owner sessions and approvals, were backed up and imported. A new API session was verified in Supabase itself.
- Cached official images were pinned through CLI version files after registry downloads stalled. Reproduction: `tools/start-supabase.ps1 -UseCachedImages`; service versions and normal startup are documented in `supabase/README.md`.
- Verification: 97 backend tests passed on SQLite and 97 on Supabase Postgres; 11 live-model tests skipped in each run. Import tests verify backup, identical replay, conflict rejection and unmapped-table rejection. Anonymous/authenticated/service-role database reads of the private schema were denied.

### DB-02. Preserve and distinguish old data [outstanding, independent of current development]

- The original Postgres container is still unhealthy; its volume has not been reset or deleted. Recovery cause is unresolved. Supabase is a new target, not recovery of those original records.
- Review-data SQLite files and backups remain under ignored `output/`. Its records were imported; old SQLite LangGraph checkpoints were **archived, not imported**. New model conversation context starts on Postgres. Browser chat snapshots remain on their original device.
- Next recovery work: obtain a consistent export if the old server can recover, inventory owners/actions/facts/outbox/checkpoints, compare with the new target, and design a conflict report before any import. Never overwrite new records or merge owners by a display name.
- Acceptance: recoverable source is backed up; source/target counts and conflicts are reported; owner/order/approval evidence remains intact. If the old source cannot be read, document the limit without destructive repair.

### DB-03. Hosted Supabase and production identity [deferred, no credentials assumed]

- Hosted development project, reviewed migrations and TLS database connection. Use direct connection or a session pooler for persistent Python/LangGraph; do not blindly use transaction pooling.
- Keep database passwords/service keys out of clients. Preserve private schema boundaries; add deliberate RLS only for tables intentionally exposed later.
- Then Supabase Auth, proof-based anonymous-owner transfer, separate visitor/merchant/operator roles, cross-device state and native bearer verification.
- Google sign-in and optional Calendar/People scopes come last. Local OAuth is supported but phones/webhooks need reachable URLs. Existing OAuth connector scopes are only `openid email profile`; no Google Ads private-interest export exists.
- Edge Functions: add an authenticated function only for a concrete webhook/provider need, with signature verification, replay protection and idempotency. Running the Edge service is not an implemented function.

## 2. Moderate temporal recommender — implemented foundation and preserved pending work

Design rationale and intended scoring: [recommender-plan.md](references/recommender-plan.md). Current code: `apps/api/app/recommendations.py`, `apps/web/recommendation-client.js`; migrations `20261021000200_recommender.sql`.

### REC-01. Current behavior [implemented and verified]

- Reviewed app-owned topic taxonomy; client cannot supply weights, owners, sensitive topics or a completed-order event.
- Server timestamps, owner-scoped dedupe, aggregate per-option/visit repetition caps and cross-process Postgres advisory locking for ingestion. REC-02 reconciles earlier per-kind weights from retained evidence.
- Session projection: 30-minute half-life, 24-hour expiry; long-term projection: 30-day half-life, 90-day inferred expiry. Events retain at most 90 days; ranking runs at most 24 hours. Expired rows are removed during subsequent activity; no scheduled cleanup job exists yet.
- Explicit current intent has the strongest score. Closest/price modes preserve input order. Inferred boosts require distinct evidence and a displayed reason. No LLM call per click.
- Client observations are **all organic-only**. They do not feed sponsorship. No Google listing names/photos/reviews/attributes or full transcripts are retained in recommender events; permitted provider IDs and app-owned selection topics are used.
- Real live-map category/detail clicks are ingested. Food has a Seafood drill-down. Cached home-card ranking/reasons are applied when entering Home again; cards do not reshuffle under a finger. Existing distance sorting remains intact.
- Me -> You, over time has live interests and Confirm / Edit / Not true / Forget / Resume learning. Confirmation or explicitly saving an edit creates a `user_supplied` preference. Forget removes observations/projections/runs, clears model checkpoints and leaves a visible learning pause until Resume.
- Existing six legacy hypotheses/JS math coexist. Their scripted fixture episodes must never be uploaded as real observations.
- Tests cover two distinct choices, explicit intent precedence, repetition, decay, expiry, owner isolation, sensitive-topic rejection, concurrent replay, confirmation and forgetting. Browser acceptance used controlled provider responses and actual profiler endpoints.

### REC-02. Finish controls and explainability [implemented and verified]

1. **Edit:** a reviewed replacement selector and explicit Save/Cancel. Saving removes old evidence, leaves the corrected old topic paused, and confirms the replacement. Projection/control changes and canonical facts commit together; injected storage failures roll them back together. No old inference is transplanted into the new interest.
2. **Evidence:** the five recent contributing observations expose action kinds, timestamps and permitted place-ID handoff links. No provider listing snapshots are persisted. Session evidence is restricted to that visit; long-term evidence spans retained visits. Cross-owner access remains isolated.
3. **Influence:** separate This visit / Across visits panels show inferred confidence, distinct-option counts, learning state, decay and expiry. Confirmed preferences and paused learning are labelled explicitly. Live interests remain separate from the legacy timeline.
4. **Repetition:** one option/topic/visit contributes at most its strongest positive signal (currently save = 1.5), with an independent bounded negative signal. Category/detail/choose/save reclassification and replay cannot add four positive weights or inflate the distinct-option count. Upgrades contribute only the difference. A deterministic replay reconciles existing v1 weights while preserving retained observation records and confirmed/paused controls.
5. **Caches/timeline:** corrections clear applied Home reasons and cached/in-flight ranking responses. Loads pause during mutations; late responses cannot restore forgotten inferences. Ranking reads/writes share owner serialization with controls. Timeline end labels derive from the actual range, preserving the existing visual design.
6. **Acceptance passed:** 109 backend tests on SQLite and 109 on Supabase Postgres, with 11 live-model cases skipped per run; five JS cache tests cover stale/in-flight/overlapping/failure behavior. Eight browser checks cover scopes/evidence, timeline labels, Cancel, a failed-save retry with reason invalidation, edit/reload/canonical facts, Not true/Resume, Forget/reload and a visible profile outage/recovery. Browser observations were seeded test inputs; injected 503s were expected failure checks. Artifact: `output/playwright/rec02-evidence.png`.
7. **Deployment checkpoint:** existing local recommender data was backed up under ignored `output/backups`, reconciled to `temporal-v2`, and the API restarted. No schema change or original-database reset was needed. Maintenance command when required: `python -m app.recommendations` from `apps/api`, using the configured database. The current API already runs this version.

### REC-03. Candidate eligibility and more surfaces [ACTIVE, expanded 22 Oct]

1. Move candidate retrieval/eligibility into trusted server paths where provider attributes matter. The current general rank endpoint accepts bounded caller candidate IDs/topics; it does **not** verify prices, stock, dates or opening hours and must not authorize actions.
2. Apply explicit area/date/budget/service/open-now constraints before scoring. Missing information is unknown, not fabricated. New explicit intent must immediately override old interests.
3. Extend to service/product/place candidates with permitted tags. Broad home-category adaptation is implemented; individualized restaurant/item ranking across all surfaces is not complete.
4. Respect user-selected closest/price sorting; add controlled variety within constraints and stable ranking snapshots. Never reorder during a pending tap.
5. Wire verified server completion signals only from authoritative action-engine events; never accept client `completed` claims. Do not learn sensitive pharmacy/medical traits.
6. Acceptance: a small repeatable seafood sequence improves the next relevant list; an unrelated request wins immediately; event replays do not inflate weights; provider failures preserve browsing and status truth.

#### REC-03A. Temporal behavior, not permanent click labels [implemented; SQLite/browser verified 22 Oct]

- Preserve the existing evidence ledger and controls. Distinguish session influence from across-visit qualification: at least two distinct options and two visits separated by at least six hours for inferred long-term ranking. Two tabs opened together do not establish a lasting preference. These are conservative tuning defaults, not learned or measured thresholds.
- Read-time decay remains 30 minutes for session signals and 30 days for long-term signals; inferred expiry remains 24 hours / 90 days. Confirmed preferences persist until corrected/forgotten and do not become booking facts.
- Rotate the browser visit after 30 minutes of inactivity or 24 hours maximum duration, including an already-open tab. Never rotate in the middle of one event request. Server timestamps govern evidence; browser visit IDs alone cannot prove long-term qualification.
- New explicit context overrides old context immediately. Negative feedback must reduce influence; dismissal hides one item for a bounded time without inventing a category dislike. Fresh contradictory evidence can change an inferred preference. Paused topics stay paused.
- Acceptance: same-visit learning, no long-term boost from one visit/multiple simultaneous tabs, separated-visit qualification, fading/expiry, changing interests, negative feedback and explicit intent precedence. Profile UI describes these rules plainly.

#### REC-03B. Trusted live-place discovery [implemented; SQLite/browser verified 22 Oct]

- Add an owner-bound structured discovery endpoint. The server maps reviewed category/subcategory choices to provider queries, fetches the actual candidates and computes distance and transient topic matches. Do not accept caller-provided provider prices, availability, types or scores.
- One provider request per list refresh initially; no extra paid query on every interaction. Rank the returned pool rather than promise exhaustive personalized retrieval. Unknown category tags stay unknown; broad-food observations do not magically prove a seafood preference.
- Filter explicit radius and open-now requirements before ranking; missing opening information fails an explicit open-now filter. Date/ticket availability and exact restaurant budgets are unsupported unless a suitable authoritative source is introduced: reject unsupported structured claims rather than silently ignore them.
- Add Recommended / Closest, Open now and explicit refresh in the existing result sheet, preserving the single category row and separate 2D/3D modes. Show a concrete reason only when profile evidence actually influences the result. Straight-line distance remains labelled as an estimate.
- Reserve a bounded variety position in larger personalized lists, subject to all constraints. No random shuffle or mid-tap reranking. Profile controls invalidate place snapshots and late in-flight results as well as Home reasons.
- Persist only permitted IDs, ranking metadata and app-owned interests. Provider listing names/types/hours/photos remain transient request/display data, never recommendation-history payloads.
- Acceptance: actual candidate ordering changes after meaningful seafood interactions; explicit cafe/pet request and closest sort win; closed/unknown/out-of-radius candidates cannot enter a constrained result; provider timeouts produce retry rather than fictional places; stale profile responses cannot restore old reasons.

**22 Oct implementation checkpoint for A/B:** `app/discovery.py` adds cookie-owned `POST /api/discovery/places`; provider candidates are fetched once per refresh, type/radius/open-now checked, then scored using current profile state. The existing generic rank endpoint also treats explicit topic intent as eligibility. Unknown provider tags do not receive invented specific preferences. Ranking runs retain IDs/scores/app-owned explanations only. The web preserves server ordering, offers Recommended/Closest/Open now/radius/Refresh, displays explanations and supports seven-day per-item hiding even when topic learning is paused. Transient display snapshots are bounded to 16 contexts and invalidated on visit rotation/profile correction. Visits rotate after 30 minutes idle / 24 hours maximum. `temporal-v3` requires separated visits for inferred long-term influence, excludes category taps from distinct-option counts and supports negative influence. Existing confirmed facts, organic-only classification and paused learning are preserved.

**Exact coverage limits:** only category/subcategory and the structured radius/open-now controls reach this discovery contract. Natural-language budget/date/party-size extraction is not implemented; do not claim an arbitrary typed request has been fully constrained. Exact restaurant spend, future hours, ticket stock and authoritative service/product eligibility remain adapter/context work. Food, coffee and veterinary type checks use provider types; other service text-search matches are not verified fulfillment capabilities. The existing generic rank endpoint remains non-authoritative for provider attributes and actions.

**Validation/deployment gate:** seven phone-size browser acceptance scenarios passed using the real app/session/profile endpoints and controlled provider/static-map responses. One separate live Google request returned eight places with types, validating the field mask; it was not an end-to-end live recommendation evaluation. PostgreSQL reads succeeded, but local test-schema creation stalled on `WALWrite`/object locks while Docker returned HTTP 500. The isolated runs were stopped; no PostgreSQL pass or production deployment is claimed. Before running this checkpoint against existing Supabase data: restore database write health, back up recommendation tables, run `python -m app.recommendations` to reconcile old category counts to v3, rerun both database suites, then restart the app. Do not reset volumes, replace `.env` with test settings or merge this write stall with the older Postgres recovery issue. No schema migration is required for A/B.

**Latest regression evidence:** 128 backend tests passed on SQLite, 11 live-model cases skipped; JavaScript profile 92/recovery 8/Luna 12/recommendation-cache 5/browsing-visit 3/discovery-cache 5 passed. Browser artifact: ignored `output/playwright/rec03-discovery.png`. The earlier 109-per-database result belongs to REC-02 and does not verify the new PostgreSQL checkpoint.

#### REC-03C. Trusted services/products and verified completions [preserved pending task; ordering follows product selection]

- Use host catalog/provider adapters for item IDs, exact fixed prices, service compatibility and fulfillment evidence. Do not trust web fixture prices or use a restaurant price category as a guaranteed meal budget.
- Preserve existing explicit service sorts. Personalize only when there are meaningful differing permitted tags; do not manufacture differences between identically tagged laundries.
- Add authoritative completion observations from the engine only, with action-based idempotency and explicit sandbox exclusion. A sandbox completion must not train a real user's taste. Client `completed` events remain rejected. Pharmacy/medical activity never trains a health profile.
- Product feeds require a source adapter and trustworthy currency/stock/date fields; existing search results alone do not prove current stock or eligibility. Keep unsupported sources visibly pending.
- Acceptance: tampered prices rejected/ignored, exact budget filters use host values, fixture exclusions, verified completion replay, sensitive service exclusion, existing order/approval regression checks.

### REC-04. Measurement and lifecycle [pending]

- Measure cached-batch ranking p50/p95, with the proposed <150 ms p95 treated as a target until measured. Compare useful selections, dismissals, constraint adherence and variety with the distance/category baseline; do not optimize clicks alone.
- Add scheduled retention cleanup, bounded run/event storage, concurrency/failure tests across processes and source-permission review before public use.
- Keep canonical confirmed facts in `profile_facts`; do not duplicate them in a second LangGraph Store. Semantic embeddings are optional, not a prerequisite.

## 3. Assistant context, short/long memory and draft plans

### CTX-01. Current context/memory [implemented, bounded scope]

- `luna/schema.py:FocusContext` accepts a selected entity, source, card/fragment, timestamp and optional draft-plan identifiers. Place detail -> Ask shows a removable chip and sends the selected place without requiring the user to repeat its name.
- Focus expires after 30 minutes and is passed through LangGraph runtime context rather than checkpointing the focus object. It is untrusted reference data, never an instruction or a stated fact.
- Recent checkpointed history is bounded to 24 messages; understanding reads the last 12; research answer text is retained for follow-up understanding. Confirmed facts remain the cross-thread source of truth. This is bounded recent history, not a semantic long-term transcript search or implemented summary system.
- Forget deletes all old checkpoint versions for that owner so earlier conversation text cannot reintroduce a deleted fact. Other owners are preserved. Current turn/forget serialization is a single-tester process lock; production multi-worker coordination still needs work.
- Pet 24h/Boarding queries retain their category meaning; responses normalize with the original category/subcategory rather than mutable UI state.

### CTX-02. Complete selected-card follow-ups [pending]

1. Resolve entity/card IDs and plan ownership/revision on the server; current focus strings and plan fields are bounded caller context, not authoritative provider or saved-plan records.
2. Wire selected **fragments**, not just whole-place detail. Museum example: the user tapped fact 3, which reports tickets sell out quickly. Preserve the exact fragment and its provenance/as-of in request context without promoting it to a fact about the user.
3. Include the current Dubai date/time, explicit dates, party size, budget and task constraints. Keep data minimal and mark unknowns. Do not infer birthday, school enrollment or other milestones from casual browsing.
4. Resolve ambiguous entities such as “green house in Deira” before planning travel. Do not merge a similarly named venue automatically.
5. **Ticket-availability guard:** comments/news/search snippets are not live ticket inventory. If no authoritative inventory adapter exists, say availability is unverified and offer a sourced booking-page handoff. Do not claim tickets are available from a review saying they sell out.
6. Acceptance: “Are tickets available?” resolves to the selected Museum of the Future; stale/cleared focus does not leak into a new thread; injected fragment instructions cannot write memory, invoke a capability or set status.

### PLAN-01. Versioned itinerary drafts [pending]

1. Create owner-scoped draft-plan storage with plan ID/revision, user-confirmed constraints, selected place IDs, explicit visit durations, locked items and source/as-of for estimates. A plan is not a booking.
2. Separate proposed edits from the accepted draft. Generate a deterministic before/after diff bound to the base revision; reject a stale revision.
3. Museum example: propose a two-hour visit, a route estimate to the resolved greenhouse, and the resulting lunch change. Mark the visit duration/travel time as assumptions or estimates. Keep a locked lunch unchanged; ask about a conflict rather than silently moving it.
4. Show the changed times and assumptions before accepting the draft edit. Accepting a local plan edit must not share data, purchase tickets, book restaurants or mark an external action confirmed.
5. Obtain fresh permitted route estimates/opening information where possible; missing provider coverage stays visible. Define time zone, midnight crossings, travel buffer and unavailable-source behavior.
6. Acceptance: revision conflict, ambiguous destination, locked lunch, uncertain duration, route failure and cross-owner access tests; one reviewable browser itinerary diff. External execution stays behind the existing explicit approval/capability engine.

## 4. Temporal suggestions and nearby events

Detailed product requirements: [assistant-context.md](references/assistant-context.md); service cases C9/C13/C15 in `docs/services/cases.md`. These features are **not implemented at this checkpoint**.

### SUG-01. Confirmed occasion context

- Add visible, editable occasion records: birthday/celebration, school start, visiting family, conference, departure or an explicit date the user saved. Store date, recurrence/time zone, provenance, validity and consent separately from inferred interests.
- Suggest useful choices: cakes/dinner/gifts for a birthday; books/uniform supplies for a confirmed school occasion; family activities for a saved visit; chargers/printing/laundry around a conference; packing/laundry around departure.
- Avoid sensitive inferences, presumed children or milestones, and notifications based only on a hypothesis. An in-app suggestion and a proactive outbox notification are different permissions.
- Test date boundaries, recurring dates, forgotten occasions, explicit opt-out and unavailable providers. Reuse existing dedupe, quiet hours and consent for any proactive message.

#### SUG-01A. Eligibility and expiry

- Resolve the explicit occasion/date/timezone first. Define the lead window per occasion and stop surfacing expired or cancelled occasions. A birthday example is a user-saved occasion, never a conclusion from shopping clicks.
- Separate recipient preferences from the user's own tastes: buying a cake for a friend does not establish the user's permanent food preference. Initially keep gift/occasion exploration inside that task; do not train long-term recipient traits.
- Suppress dismissed suggestions and respect budget/area/dietary constraints only where supplied and verifiable. Unknown constraints stay unknown.

#### SUG-01B. Adaptive choices, rather than fixed occasion cards

- Retrieve eligible candidates, then apply relevant confirmed and qualified temporal interests using the shared ranker. Example: a birthday may suggest dinner, cake or an activity; repeated interest in live music can favor an eligible music experience over a generic dinner.
- The occasion provides relevance and timing; it does not force the same suggestions for everyone or override a new request. Keep a relevant variety option, explain the actual reason and expire the recommendation after its useful window.
- Test two owners with the same occasion but different preferences, a changed explicit request, conflicting/expired dates, recipient-context isolation and no unwanted notification. Feed retrieval/verification must be implemented before marking this complete.

### EVT-01. Source-backed future events

- Reuse configured search tools first; NewsAPI is optional and its developer tier is not a production feed. Do not add a key dependency when existing sources suffice.
- Retrieve festivals, performances/exhibitions and artist visits relevant to an explicit area/date/topic. For a specific singer, store a preference only when confirmed or keep it as a visible organic hypothesis.
- Normalize event identity, venue, local start/end, timezone, source URL, publication date, event date, verification state and checked-at. Confirm dates with organizer/venue/ticketing sources before presenting a scheduled event as verified.
- Examples are queries, not fixture facts: Global Village opening, a singer touring Dubai next week, a nearby festival. Do not assume this year's opening date or treat a past news item as upcoming.
- Separate relevance from eligibility, duplicate news reports, stale/cancelled events, unverified announcements and ticket stock. A news report is not booking availability.
- Render a clean carousel with reason/date/source, dismiss and handoff; no fake ticket purchase or external confirmation. Test timezone/date changes, duplicates, cancellation and empty results.

#### EVT-01A. Freshness before personalization

- Query for the explicit Dubai date window, verify identity/venue/date against the organizer, and exclude past/cancelled/out-of-area events before scoring. Never let a favorite artist's high score revive an expired event.
- Rank eligible events by the current request, explicitly saved artist/topic preferences and qualified temporal interests. A short festival-browsing session can affect the next festival list without becoming a lasting artist preference.
- Store permitted source/provenance/verification metadata and define refresh/expiry per source adapter. News is discovery evidence, not ticket inventory. No source means an honest empty/error state.

#### EVT-01B. Timing patterns are a later, separate inference

- Recency-based decay is implemented; learned habits such as Friday lunch, school routine or preferred outing time are not. Do not describe the six legacy demo hypotheses as measured habits of the real tester.
- Any future time-of-day/day-of-week inference needs repeated evidence on separate days, a visible explanation/control, enough data to evaluate it and a reviewed retention policy. No LLM transcript mining or hidden routine detection.

## 5. Sponsored restaurant discovery

### ADS-01. Controlled, labelled placement [pending]

- Show only within a relevant restaurant/food thread or surface. Match explicit current cuisine/area/budget and **eligible first-party** preferences. Keep organic choices visible.
- Sponsored card must identify the sponsor, display a clear Sponsored label and an intelligible “Why this ad” reason, and offer dismiss/less-like-this controls. Do not silently mix paid placement into organic relevance scores.
- Separate eligibility, targeting evidence, budget/frequency caps, impression/click audit and organic ranking. Empty sponsor inventory means no sponsored card; do not invent an advertiser.
- The current recommender marks all observations organic-only. Define separate consented sponsored-eligible evidence before using behavioral personalization for ads. Never use Google Workspace data, sensitive traits, raw transcripts or restricted Google-derived profiling.
- Google sign-in offers basic identity and separately granted scopes; it does not export Google's private ad-interest profile. Google Ads audience selection is not permission to read those user profiles.
- Acceptance: no sponsorship outside food context, visible label and organic alternatives, no ineligible evidence crossing the boundary, caps/dismissal/privacy isolation. Merchant-side campaign management, billing and external ad operations need their own future scope.

## 6. Remaining review and release work

### REV-01. Security/reliability

- Paid Places/Routes/static map/photo proxies still need deployment-appropriate owner checks, quotas/rate limits, bounded validation and honest upstream timeout/failure handling. An API key working does not settle public abuse controls.
- Sandbox merchant PIN needs attempt throttling before public exposure; production merchant and operator roles are separate work. Do not weaken ownership checks because there is one tester.
- Keep route/price/stock facts authoritative and dated; keep provider errors distinguishable from sandbox/mocked failure tests.
- Improve connection lifecycle and multi-worker turn/forget coordination before claiming production readiness. Backend startup still uses deprecated FastAPI startup hooks; migration to lifespan is maintenance, not a feature gate for the single tester.

### REV-02. Code/UI and device review

- Remaining visual references: Home/Services arrival composition, guide, lost-item surfaces and Me. Preserve the approved current navigation, cyan, no shadows, Wi-Fi and gradients; do not restore excluded features just to copy an old reference.
- Recheck map drill-down, 2D/3D mode stability, late responses and pet query context after subsequent changes.
- Physical iPhone Safari/native keyboard, safe areas, VoiceOver, Dynamic Type, reduced motion and frame pacing remain unverified. Founder has a Mac/iPhone; the native unsigned build is not device acceptance.
- The native in-app browser uses a Safari sheet; production OAuth callbacks, isolated merchant bridge, approval/order cards, SSE, guide/recovery parity, APNs/Live Activity and voice remain parked on `ios-swift`.

### REV-03. Demo and provider access

- Keep live configured discovery/search APIs, clearly labelled sandbox merchant execution and official/in-app-browser handoffs for unsupported transactions. No blanket assumption that every API requires a company.
- API catalog preserves Careem MCP reviewed-access path, Uber privileged approval, affiliate/marketplace tiers and provider-specific unknowns. Registering/applying/production grants are external work, not implemented adapters.
- Founder walkthrough, ten clean <=4-minute rehearsals, fallback video, deck/hosting/small user test remain pending. Submission target remains January 2027, with the internal package target recorded in `PLAN.md`.

## 7. How the next LLM should execute

1. Read `CLAUDE.md`, `PLAN.md`, this document and `docs/request-backlog.md`; use `handoff.md` only for current runtime/checkpoint details.
2. Read the 22 Oct **personal-assistant-direction.md** proposal before picking implementation work. Current task is mature feature/pilot selection, not automatic REC-03C execution. The first pilot audience was asked asynchronously and remains open unless a later founder answer resolves it. Preserve code checkpoint `6470ad4`, its Supabase adoption gate and all unfinished tasks; do not rebuild REC-02, restart setup, re-research settled OAuth answers or resume native features.
3. Mark each task implemented and verified separately. Record changed contracts, migrations, test evidence and remaining limits before committing. Update the plan if the founder changes scope/order.
4. Keep tests proportional: deterministic/profile/privacy/action changes need meaningful tests; browser acceptance must distinguish mocked provider data from live provider verification.
5. Commit and push to `redesign` at coherent checkpoints; native branch remains `ios-swift`. Never commit `.env`, database contents, backups, provider keys or local signing state.
