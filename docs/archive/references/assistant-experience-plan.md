# Extended assistant experience and delivery plan — 22 Oct 2026

Status: **original expanded proposal, partially superseded by the reconciled build. Gate A manual tasks/Today is implemented with SQLite checks; later features remain proposals.** Subordinate to PLAN.md and docs/implementation-plan.md. Product rationale: [personal-assistant-direction.md](personal-assistant-direction.md). Founder requested the expansion, an explanation of redesign needs, and a swipe-up personalized news/newsletter briefing. The founder subsequently authorized implementation from the [reconciled review](assistant-review-decisions.md). Gate A (manual tasks + Today) is active; later features below remain proposals. `ios-swift` stays parked.

## 1. Product and scope decisions

- Confirmed: a personal assistant for everyday life and work in Dubai. Visitor/arrival is an optional situation. Do not require hotel, flight or visitor information at onboarding.
- Proposed first audience: an individual living/working in Dubai, with optional personal/work contexts. The earlier pilot question remains unresolved. Household/team collaboration is a separate expansion.
- Core outcomes: hand over work, understand progress, review decisions, receive a usable result and redirect or stop work. Relevant discovery and a personal briefing support those outcomes.
- First bounded task proposals: prepare a sourced comparison from supplied requirements; track an existing service deadline and bring back a useful decision. These reuse current research/actions and can start with manual input. Choose the actual two pilot jobs before implementation scope is locked.
- Preserve existing fixed-price/approval/provider-evidence safeguards, source/privacy boundaries and outbox consent. Payments, government execution, sensitive inference and unapproved outreach do not become permitted through this expansion.

## 2. Does it need a redesign?

**Yes: a targeted redesign of information hierarchy and a few key screens.** The current Home coverflow introduces ideas; the proposed Home must show the user's responsibilities, decisions and relevant briefing. The visual identity and working discovery/action flows remain reusable.

| Surface | Proposed change | Reuse / boundary |
|---|---|---|
| Home / Today | Prioritize Needs you, In progress, Waiting and Recently completed; open All tasks from here. | Preserve cyan/gradients, restrained glass and no shadows. No giant analytics dashboard. |
| Swipe-up briefing | A separate expandable reading layer for relevant published news and, later, explicitly connected newsletters. | Distinct from task urgency and approvals; tap alternative to the gesture. |
| Task detail | New persistent view of outcome, constraints, next step, result, activity and decisions. | Reuse registered page/sheet host and action cards where suitable. |
| Chat | Relate a conversation to a selected task/source, show proposed changes and let the user correct them. | One composer; existing browse dock collapses for chat. Preserve return position/context. |
| Maps / Services | Link a selected place/service to a task or plan. | Preserve explicit 2D/3D modes, one category row and existing approved merchant mini-app boundary. |
| Me | Organize saved facts, inferred interests, update preferences and connected accounts. | Extend existing visible evidence and correction controls. |
| Routines / outputs | Add routine preview/control and versioned results as later task-related views. | No new top-level destination until use warrants it. |

**Initial navigation proposal:** Today (renamed io/Home), Maps, Services, Me, with the existing Ask entry. Tasks open within Today. Do not add several bottom tabs or consolidate Maps/Services into Explore without a demonstrated navigation need. Horizontal carousels remain suitable for a small set of discovery options, rather than being the only way to inspect ongoing work.

Wi-Fi/gradient onboarding remains available, with copy reflecting everyday assistance. Airport replay is contextual or optional. Keep the admired visual treatment; do not force a first-run airport story. Historical prompts in redesign.md are references, not current navigation authority.

## 3. Screen specifications and state coverage

### UX-01. Today

- Header: simple greeting/date and optional user-confirmed context. No location claim inferred from the map or browsing.
- Needs you: a small ordered list of actionable decisions. Each gives the change, consequence, source/time and next action. Unknown evidence cannot manufacture urgency.
- In progress / Waiting: concise task rows showing outcome and next expected step. Distinguish waiting on the user, a provider and a failed source.
- Recently completed: usable results with relevant evidence, not a count of generated answers.
- All tasks: initial bounded list/detail with pagination; full search/filter is deferred. Later open/completed/paused views may follow evidence of need. New users get one clear delegation prompt, not a mandatory profile wizard.
- Briefing handle: “Your briefing” preview above the browse dock, with a tap and swipe-up entrance. Keep urgent decisions visible before optional reading.
- Required states: empty, loading, stale/offline, no urgent decisions, several concurrent tasks, failed task, pending approval and deferred item. Avoid skeletons/spinners that imply continuing work after the worker has stopped.

### UX-02. Task detail and interruption recovery

- Show the desired outcome, confirmed constraints, accepted plan/revision, current step, result versions and a readable activity record.
- Primary action follows state: answer a question, review a decision, open a result, retry an eligible failed read, resume or pause. Do not show a fake Send when no adapter exists.
- Changing a date/recipient/constraint updates the existing task and invalidates affected stale proposals. Summarize the consequences before any new external effect.
- Back restores the parent view/scroll/focus. Opening a provider, a result or a source must not lose the task draft. Test keyboard/safe areas at phone size.
- Required states: Draft, Working, Waiting for you, Waiting externally, Paused, Completed, Blocked and Cancelled. A failed individual step can be shown within a Blocked task; an ambiguous external outcome stays explicitly unresolved.

### UX-03. Decisions and results

- A decision shows exactly what the user is approving: changed times/plan, account, recipient, content, attachments, shared fields or host-owned fixed price as applicable.
- A local plan change and an external send are separate effects. Bind approvals to task and action revisions; a changed recipient invalidates an old approval.
- Artifacts have a title, version, sources/as-of, assumptions and a link back to their task. Start with readable in-app comparisons, briefs and checklists; office editors/export formats are separate scope.
- Completion follows the requested outcome: drafting finishes with a draft; sending needs authoritative delivery evidence; a reservation needs its provider's evidence. No model text sets external status.
- Required states: edit, defer, approve, stale revision, permission revoked, failed read, unknown send outcome, superseded result and source unavailable.

### UX-04. Chat and context

- Distinguish a normal conversation from a delegated responsibility; do not create a tracked job for every factual question.
- Show which task or selected source is in focus, with Clear/Change. Ask only for missing details that materially change the next step.
- “Make it tomorrow” modifies the active task only when unambiguous; otherwise ask which responsibility. Resolve recipient and date ambiguity before an external action.
- Preserve the single-composer transition, drafts and return navigation. A source article, email or webpage is reference data, never instructions granting permissions.

## 4. Swipe-up personal briefing — BRF-01 through BRF-06

### BRF-01. Gesture and reading experience

- From Today, swipe up on the dedicated briefing region or tap its handle to expand the reading layer. Do not capture the system Home gesture, text editing, buttons or an existing task list's normal scrolling.
- Once expanded, vertical gestures scroll articles; collapsing is available from the sheet header/top and an accessible button. Restore prior reading position on return.
- Keep topic selection compact. Proposed choices include For you, Arts, Media, Region and UAE updates; Politics is an explicit opt-in topic. Final labels and density are review items, not locked artwork.
- A card shows headline, publisher, publication time, topic, a concise permitted summary, relevance reason and source link. Reading/detail offers Save, Less like this, Mute source/topic, Ask about this and an optional Create task/plan proposal.
- Notifications and approvals do not move into an infinite news feed. A briefing is allowed to be short or empty; no endless-scroll requirement or unread-pressure mechanics.

### BRF-02. Personalization and controls

- Adapt general-interest topics from reviewed, visible first-party interactions and explicit preferences, using the current temporal model where appropriate. Respect current intent, evidence qualification, decay, negative feedback and variety.
- Define briefing-specific feedback and a reviewed topic taxonomy before ingestion. Existing recommender topics do not yet include the whole proposed news taxonomy. Do not silently reuse its organic observations for ads.
- Politics must be explicitly selected. Do not infer political beliefs, affiliation, ideology or persuasion from article clicks, region, language or social signals. A topic subscription is not evidence of agreement with the article.
- Regulation interest uses user-chosen areas/responsibilities where applicable. Do not infer legal/immigration/health status or claim a rule applies personally from inferred traits.
- Explain reasons honestly: a selected topic, an explicitly saved area, or qualifying general-interest evidence. Do not claim Google supplied a private interest profile.
- Acceptance: correction/forget invalidates briefing caches; a saved/dismissed article does not imply a belief; no sensitive trait or sponsorship evidence is learned; cold start uses chosen topics with a visible generic fallback.

### BRF-03. Source selection and publishing rights

- Start with published sources whose retrieval/display rights and access are verified. No assumed free news API, unrestricted scraping, full-article republication or subscription bypass.
- Build source adapters with clear permissions, attribution, retrieval method, allowed excerpt/summary policy, latency, rate/cost limits and failure behavior. Save only allowed metadata/content.
- Rank only after source eligibility, freshness, duplicate clustering and topic/date checks. Separate article publication time, the date of the reported event and checked-at; a newly published retrospective is not a new event.
- Preserve publisher attribution, links, corrections and story provenance. A similar headline or copied report is not an independent confirming source. Do not optimize only clicks or promote sensational material to create activity.
- Required states: no results, provider failure, stale source, duplicate story, corrected/retracted article, paywall and source removed. A broken feed must not silently become a fictional demo feed.

### BRF-04. UAE/Dubai regulation updates

- Use authoritative issuer material for regulatory claims. Treat media coverage as discovery/context until the official source is resolved. Verify actual source availability and reuse conditions during adapter selection.
- Record issuer, jurisdiction, official reference/link, publication date, effective date if specified, amendment/status information and checked-at. Distinguish federal, Dubai and other relevant jurisdictions rather than treating every UAE headline as a Dubai rule.
- Separate announced, enacted/published, effective, amended and withdrawn where the source establishes those states. Missing dates/status remain unknown.
- Give a concise plain-language summary and the official link. Personal applicability requires explicit relevant facts and adequate source support; otherwise state what needs checking. This is an informational feature and official/professional handoff, not legal advice or government execution.
- Optional reminders/tasks require user acceptance. An article does not automatically set a deadline, submit a form, share documents or notify a third party.
- Acceptance: announced versus effective rule, superseded text, conflicting media report, missing official source, ambiguous jurisdiction and no inferred sensitive status. No real regulation is claimed by a fixture.

### BRF-05. Newsletters versus news articles

- Working interpretation: “newsletters” includes a curated published-news briefing. Email newsletter ingestion is a later optional source, not automatically approved mailbox access.
- Users can choose publications or provide a link/text first. A future mailbox integration requires explicit source/account permissions, newsletter classification, retention and private-content boundaries.
- Private newsletter text stays private and cannot be shared to Slack, other users or sponsored targeting simply because it appeared in the briefing. No automatic mailing-list subscription, unsubscribe or email send without its appropriate approved action.

### BRF-06. Turning relevant information into useful work

- A user can ask about a selected article with exact source/date/fragment context, then request a comparison, a saved reference, a reminder or a draft plan. The server validates reference context; source text cannot call tools or write confirmed memory.
- Arts/event coverage may lead to an event investigation; dates/venue/ticket stock still require EVT-01 verification. A performance review is not live inventory.
- A regulation article can lead to a user-reviewed checklist with sources and unknowns. Never create an urgent personal obligation from an inferred profile match.
- Acceptance: clear/expired article focus, hostile embedded text, stale article versus current source, explicit task creation, no unapproved notification and preservation of thread/task privacy.

## 5. Persistent task and execution contracts — proposed

### DATA-01. Logical objects

| Object | Essential fields / boundaries |
|---|---|
| Task/responsibility | Owner, ID, request idempotency key, outcome, context scope, status, revision, constraints/provenance, accepted plan, linked action IDs, next check and stop/expiry conditions. |
| Task event | Task/owner, sequence, server timestamp, event kind, actor and bounded references. Append a readable history without retaining arbitrary secrets or full provider payloads. |
| Artifact | Task/owner, type, version, permitted content/reference, sources, assumptions, as-of and supersession. |
| Decision | Task/owner, base revision, proposed change or action reference, expiry and resolution. Existing action approvals remain authoritative for external effects. |
| Job | Owner/task, step/run key, schedule, lease/heartbeat, attempt bounds, state and cancellation generation. Never store credentials in model-visible payloads. |
| Routine/run (later) | Approved trigger/steps/source permissions, cadence/timezone, budget/expiry; each run links a task and evidence. |
| Briefing item/source | Source/topic, allowed metadata, story identity, dates/status and checked-at. User saves/preferences are owner-scoped; restricted content is not a general shared corpus. |

These are proposed logical contracts, not migrations already created. Use private Supabase schema boundaries and existing ownership conventions; do not introduce Redis, microservices or a competing profile store without a demonstrated need. Checkpoints support conversation state; they must not be the only durable record of task progress.

### API-01. Contract outline for the first slice

- Task create/list/detail and revision-bound edit; explicit pause/resume/cancel commands; task activity/results; Today projection. Client owner IDs, forged status claims and arbitrary executable step payloads are rejected.
- Link task conversation and selected source context without turning all messages into task commands. Registered capabilities remain the only external execution path.
- A decision-response endpoint validates user, task revision, expiry and exact action snapshot, then delegates to the existing action engine where appropriate. Do not duplicate execution in a new chat route.
- Briefing retrieval/feedback/source controls use an explicit reviewed taxonomy and permitted source adapters. Pagination/refresh cannot bypass filtering, source eligibility or user corrections.
- Final endpoint names/schema/migrations are an implementation deliverable after the first pilot slice is chosen. Record contract changes and client compatibility before native parity work resumes.

### RUN-01. Worker, cancellation and recovery

- Persist each task/job transition before telling the user work is underway. Use bounded leases, duplicate-event keys and safe retries for read-only operations.
- Recheck task revision/cancellation and permissions after network waits. A late worker must not restore old plans, publish a stale result as current or send after cancellation.
- Do not hold a database transaction across a provider/LLM call. Commit intent/state and provider outcome deliberately; ambiguous side effects retain UNKNOWN_STATUS and are reconciled rather than automatically repeated.
- Proposed routines use approved structured steps, not model-authored executable code. Apply per-run provider/model/time budgets and backoff; show exhaustion/blockers honestly.
- Deployment requires a running backend/worker and healthy durable writes. A local host being off means no background work; do not promise always-on operation from an unsigned app build or a browser mock.

### ATTN-01. Briefings and notifications

- Reuse outbox consent, dedupe and Dubai quiet hours. A source watcher runs within an explicit responsibility/routine, with cadence, scope, expiry and revocation.
- Model-generated candidate insights may be reviewed/validated, but deterministic policy decides delivery eligibility. Inferred interests alone cannot start proactive notifications.
- Bundle routine progress into the task/optional digest; interrupt only for a permitted actionable change. Define deferral, dismissal, expiry and suppression of repeated unchanged updates.
- News reading is in-app by default. News push alerts require separately chosen topics/rules. Sponsored discovery stays separate from Today urgency, regulation updates and approval cards.

## 6. Delivery slices and gates

| Slice | Planned result | Dependencies | Gate before proceeding |
|---|---|---|---|
| EXP-00 | Review Today, task detail, decision and swipe-up briefing wireframes/states using representative inputs. | This plan, approved visual references, pilot assumptions. | Clear task-versus-reading hierarchy; one composer; accessible gesture alternative; no lost context. |
| CORE-01 | Manual-input responsibility -> useful research/comparison result -> Today/detail -> correction/pause/restart. | Task/events/artifact contracts, bounded research, memory, ownership and database write health. | One real useful artifact, restart/resume, revision conflict, cancellation and cross-owner checks. |
| CORE-02 | Existing service deadline becomes a task/decision with provider evidence. | Existing catalog/action/merchant/outbox path; sandbox label until real provider access. | No duplicate order or invented completion; exact approval; understandable deadline risk and blocker. |
| BRIEF-01 | Swipe-up briefing from a small reviewed published-source set and explicit topics. | Source/rights review, permitted metadata, BRF feedback taxonomy and relevance rules. | Freshness/duplicates/failures, politics opt-in, official-source handling for regulations and clear reading/task separation. |
| CONNECT-01 | One deliberately chosen Gmail/Calendar source improves an actual pilot job. | Production ownership/Auth/scopes, revocation, account mapping and source-event handling. | Recipient/account correctness, no channel leakage, duplicate events, revoked access and unknown-send recovery. Google OAuth dependency must be explicitly reordered for this slice. |
| ROUTINE-01 | One user-reviewed recurring preparation/monitoring procedure. | CORE tasks, scheduler/leases, budgets, consent and cancellation. | Useful across repeated cycles, no silent activation or post-cancel action. |
| CHANNEL-01 | Optional Slack entrance and replies using the same task/approval state. | Proven channel identity, scoped accounts, event verification/dedupe. | Private/public separation, conflicting instructions and exact-user approval. |
| EXPAND-01 | More sources, events, household/team capabilities and sponsored discovery. | Measured relevance/task usefulness, permissions and real provider access. | Value and reliability justify each addition; existing REC/CTX/PLAN/SUG/EVT/ADS/REV gates remain. |

This order is a proposed delivery sequence, not a promise to implement every row immediately. BRIEF-01 can be designed alongside CORE work, but source-backed news aggregation should not hide unfinished task completion/recovery. No iOS implementation starts through this plan.

## 7. Mapping the existing backlog

- REC-03A/B: preserve temporal/correction foundations and existing structured place filtering. News needs its own reviewed taxonomy/signal rules; do not pretend arts/politics/regulation topics already exist in code.
- REC-03C/04: trusted service/product constraints, authoritative completion signals, relevance measurement and lifecycle remain pending. Use them where a selected task requires them.
- CTX-02/PLAN-01: selected article/place fragment validation, trusted entity/plan ownership and versioned plan diffs support chat-to-task and briefing-to-task flows.
- SUG-01/EVT-01: explicit occasions and sourced future events support useful opportunities; they are not inferred milestones or news-based ticket confirmations.
- ADS-01: preserved, deferred until organic utility is established; no sponsored slot in the decision inbox or regulatory alerts.
- REV/DB: retain public quotas/roles/device review, healthy database writes, original-data preservation and hosted production identity. Old Postgres recovery and the newer Supabase write stall are distinct unresolved work.
- Native: parked; later mirror stable task/briefing contracts on the founder's Mac/iPhone. Do not convert this planning task into a new Swift effort.

## 8. Validation and review deliverables

- Before coding: screen/state map, two selected pilot jobs, task/source/action boundaries, initial data/API contracts and a reviewed source shortlist with access/rights unknowns recorded.
- Core tests: owner isolation, idempotency, revision conflicts, restart/resume, pause/cancel race, revoked credentials, stale workers and ambiguous external outcome. Reuse existing action/profile checks.
- Briefing tests: explicit topic choice, sensitive inference exclusion, source rights/freshness, date/jurisdiction distinctions, corrections/duplicates, empty/error states, malicious source content and privacy on sharing.
- UI acceptance: task creation and correction, visible blocker, inspectable decision/result, return navigation, swipe-up/tap/collapse reading behavior, one composer, keyboard/safe areas, reduced motion and accessibility. Physical-device review remains separate from browser screenshots.
- Quality: useful completed outcomes, constraint adherence, understandable progress, false urgency, notification dismissals, recommendation/source diversity and bounded latency/cost. Establish baselines before numeric targets; clicks alone are insufficient.
- Demo proposal: an ordinary day with a task outcome, one evidenced change/decision and a relevant briefing item that can lead to a user-requested next step. Preserve the historical visitor demo as a scenario, not the product's identity. Label fixture/time-jump/sandbox evidence.

## 9. Remaining choices for review

First pilot cohort/two jobs; exact Today density; whether Tasks later merits a tab; initial licensed/public source set; published briefing versus optional email newsletters; first connected source; retention choices and hosting budget. These are open decisions, not reasons to abandon the plan or invent access. The requested external LLM review should challenge them before implementation.

## 10. Current delivery and design-review update

The [reconciliation](assistant-review-decisions.md) and latest founder decision take precedence over older navigation/full-platform assumptions above. Gate A implements manual task CRUD, user-reported completion, revisions/idempotency and activity. **Preserve full visual Home and Wi-Fi/gradient onboarding; Today opens as a sheet from its own handle** with tap/keyboard alternatives, actual saved-task counts, due-sorted On your list and paused visibility. Empty Needs you/Running stay hidden; DX-14's hide-deck premise is superseded. SQLite: 145 passed/11 skipped (17 task checks); both requested phone sizes/motion settings and keyboard/browser checks passed. Physical iPhone gestures, screen-reader output and PostgreSQL adoption remain unverified. Keep-track bridge, taxi staged replies, Reading, cron/worker and Gmail are explicitly excluded from this pass. No scheduler, monitoring, decision/execution bridge or briefing is built; their specifications above remain future proposals.

Founder confirmed staged taxi-recovery replies first and Gmail later; requested freely licensed content-photo replacements; supplied 12 Duet frames for visual/interaction/use-case review. TAXI-02/VIS-02 are nested in the reconciliation. Use [the new Claude prompt](assistant-design-interaction-review-prompt.md); output a new `assistant-design-interaction-review.md`, preserving the prior critique.


## 11. Second review quality correction

The new design/interaction/use-case critique is delivered, with detailed DX findings and a verified distinction between implemented contract quality and weak Home/task integration. Read the review and reconciliation assessment. Proposed amendments: On your list for manual tasks, Needs you for decisions, paused visibility/due prioritization, restored compact photo/gradient Home and visible recommendation reasons, reference-only task links, and the receipt-first staged recovery journey. These corrections are pending, not an implemented redesign. The first critique and founder-supplied design references remain preserved.
