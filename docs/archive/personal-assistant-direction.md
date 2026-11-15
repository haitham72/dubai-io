# DubaiIO personal assistant direction — 22 Oct 2026

Status: **product direction and feature proposal, not implemented capabilities**. The founder explicitly changed the visitor-first framing. PLAN.md remains authoritative; this document develops the proposed product and pilot. Current source checkpoint: `6470ad4` on `redesign`. Native work stays parked.

Expanded screen/state, task/source and phased delivery detail is in [assistant-experience-plan.md](assistant-experience-plan.md), including the founder's swipe-up personalized briefing addition. The [external review prompt](assistant-plan-review-prompt.md) requests critique before implementation. The targeted redesign preserves the approved visual language and existing discovery/action foundations.

## 1. Founder instruction and audience

> no, change of plans, learn from openai dots/grok dots/claude due and suggest features in a mature way, it is for dubai but it is not a companion for visitios

**Confirmed change:** build a personal assistant for everyday life and work in Dubai. Arriving at an airport is one possible situation. It must not define the persona, onboarding or product promise. The previous short-stay business visitor/hotel-concierge framing is superseded.

**Working pilot assumption, awaiting the founder's preference:** an individual living and working in Dubai, with optional home/work contexts. Household collaboration and business/team operations are possible later expansions, not automatically the first audience. Do not assume a family, employer, school enrollment or business ownership from browsing. A pilot-audience question was asked; an unanswered question is not approval of a narrowed pilot.

**Proposed promise:** “Tell DubaiIO what you need handled. It keeps the context, prepares the next steps, follows progress and brings you decisions that need you.” Dubai supplies relevant places, routes, services, events and official handoffs. The assistant remains useful when the task is an email, a work commitment or a personal follow-up without a map.

## 2. What to learn from the reviewed products

Official sources reviewed 22 Oct; descriptions are vendor-documented behavior, not independent reliability tests. The relevant Grok product is **Grok Bot**.

| Product | Documented pattern | Design lesson for DubaiIO |
|---|---|---|
| OpenAI Dots | Ongoing responsibilities, work between conversations, shared context across contact methods, activity review and boundaries on sharing. | Persist the responsibility and its progress. A channel is a doorway to the same assistant. Keep pause, review and redirection accessible. |
| Grok Bot | Delegation, reusable routines, background execution, team interaction and concrete approval/failure handling. | Let users teach an approved process and inspect its results. A useful handoff includes a finished artifact or an honest blocker. Multiple visible bots are not required for an initial pilot. |
| Claude Duet | Briefings, background preparation, connected-app context and requests for user judgment. | Prioritize attention: present what changed and which decision is needed. Avoid sending every piece of progress as a notification. |

Sources: [official OpenAI documentation](https://learn.chatgpt.com/docs/dots), [Grok Bot introduction](https://x.ai/news/introducing-grok-bot), [Grok Bot changelog](https://x.ai/changelog/bot), [Claude Duet announcement](https://claude.com/resources/articles/claude-duet).

The common lesson is continuity, useful preparation and controllable follow-through. Copying an avatar, an unrestricted cloud browser or a large connector catalog would not establish those qualities. This proposal does not select a new model vendor or replace the existing LangGraph/action architecture.

## 3. Proposed core: responsibilities the user can delegate

### PA-01. Persistent responsibilities and task progress — proposed first core slice

- A responsibility captures an outcome, owner, scope (personal/work or a user-named context), deadline, constraints, allowed sources, update preference and stop/expiry condition.
- Start with one-off tasks and simple recurring responsibilities. Suggested prompts are editable examples, not a mandatory automation builder.
- Separate task progress from individual action status. A task may be Working, Waiting for you, Waiting externally, Paused, Completed or Blocked. An order may be SUBMITTED/ACCEPTED/etc. under the existing action engine. A drafted email is not a sent email; a prepared plan is not a reservation.
- Persist the accepted plan, proposed changes, current step, artifacts, blockers, next check and linked action evidence. “Actually, make it tomorrow” edits the existing responsibility and shows affected work rather than silently spawning a duplicate.
- Let the user inspect, pause, resume or cancel future work. Explain when an already-sent external action cannot be undone. Prevent a stopped job from later sending a queued message.
- Acceptance: resume after restart, changed deadline, duplicate instruction/event, cancelled pending work, a provider timeout, cross-owner denial and an intelligible activity record.

### PA-02. Today and a decision inbox — proposed first core slice

- Home prioritizes **Needs you / In progress / Waiting / Recently completed**. Keep chat immediately available; Maps and Services remain useful destinations.
- Show a small number of useful items, each stating what changed, the evidence/time, the consequence and the next decision. An empty day is valid; do not invent urgency or fill it with promotions.
- A briefing is optional with user-selected timing and delivery. Interruptions require an explicit task/watch rule, an actionable change and the existing consent/dedupe/quiet-hours rules.
- A decision card previews exact recipients, content, changed times, fixed prices or fields before a side effect. Choices include edit, approve, defer and dismiss as applicable.
- Acceptance: every urgent item has a source and next step; dismissed/unchanged updates do not repeatedly return; the user can understand current work without reading the full chat.

### PA-03. Context the user can inspect — extend existing memory work

- Keep four separate concepts: confirmed facts/preferences; fading inferred interests; task-specific working context; and completed-action evidence. Do not turn an inference or a summary into a confirmed fact.
- Organize explicitly saved areas, availability, important dates, recurring responsibilities and related people without requiring an exhaustive profile upfront. Record who a preference belongs to; shopping for someone else must not train the user's own taste.
- Preserve corrections, validity windows, evidence and Forget across checkpoints, projections and caches. Explain deletion scope. Shared channels receive only the context the user authorized for that audience.
- Use bounded relevant retrieval rather than one unlimited transcript. A new task should not inherit an unrelated selected place, recipient or date.
- Acceptance: two concurrent tasks keep their constraints separate; changed facts supersede old ones; a correction survives restart and prevents old context from resurfacing.

### PA-04. Procedures and background execution — proposed after task foundation

- “Every Thursday, prepare three weekend options within my saved constraints” becomes a reviewed routine: trigger, sources, steps, output, notification rule, permissions and expiry. Show one preview run before enabling it.
- An inferred habit can suggest a routine; only an explicit user decision activates it. No silent monitoring or scheduling from recommendation clicks.
- Use persisted jobs and bounded source checks, with execution budgets, leases, idempotency, observable failures and safe retries. The product can continue after a user closes the app; it does not require continuous model polling.
- A routine may research and prepare within its approved scope. External messages, merchant sharing and other side effects retain the existing explicit approval gate.
- Acceptance: missed schedule/restart recovery, overlapping jobs, stale input, revoked connector, repeated upstream event, pause/cancel and honest uncertainty after an ambiguous send.

## 4. Practical capabilities that make the assistant useful

### PC-01. Communications and calendar follow-through — proposed connector pilot

- Turn a selected message, forwarded text or user-provided appointment into a task before requiring access to an entire inbox. Manual input keeps a useful first slice independent of Google OAuth.
- With a deliberately connected source: summarize what needs a response, prepare a reply using the relevant context, detect an explicit date conflict and propose changes. Calendar entries and emails are information, not commands granting authority.
- Outbound messages show the destination, sender account, exact body and attachments. Record provider evidence of sending; a timeout produces an unresolved outcome rather than an automatic resend.
- A reminder may help the user follow up after an agreed interval. Contacting the other person again is a separate approved side effect; avoid autonomous outreach loops.
- Google identity scopes do not grant Gmail/Calendar access. Production connector permissions, account ownership, revocation and native callbacks must be implemented before claiming these capabilities. The existing single-tester OAuth-last instruction is not silently lifted; a connector-based pilot would require a deliberate dependency reorder.
- Acceptance: manual-input happy path, wrong recipient/account, ambiguous date, revoked permissions, duplicate event and unknown send outcome.

### PC-02. Plans and relevant opportunities — reuse REC / CTX / PLAN / SUG / EVT

- Support useful outcomes: arrange a day, compare places for an occasion, prepare a weekend, fit a service around commitments or investigate an event. Ask only for missing information that changes the decision.
- Eligibility comes first: dates, places, party size, explicit preferences, fixed budgets where verifiable, availability evidence and travel estimates. Then apply qualified temporal preferences and relevant variety.
- Keep locked commitments fixed. Show a revision-bound before/after change with assumptions and source timestamps. Planning does not imply booking, paying or sharing.
- Occasion and event suggestions adapt to explicit context and changing interests; they do not repeat the same static cards. An event must still be upcoming and relevant even if the user likes its artist.
- Acceptance remains in CTX-02/PLAN-01/SUG-01/EVT-01; a recommendation's relevance, a plan's validity and a provider's stock are separate claims.

### PC-03. Local follow-through — preserve the strongest existing engine

- Keep service comparisons, published fixed prices, isolated merchant mini-apps, exact approvals, merchant-confirmed updates and reminders.
- Apply them to ordinary life and work without hotel/arrival assumptions. A provider missing a requested deadline becomes a decision the user can act on.
- Start with one genuinely supported vertical. Broader city coverage should distinguish live discovery, sandbox execution, real adapters and official handoffs.
- Saved renewal dates and documents may support reminders/checklists and official links. Government execution, legal/medical advice, payments and purchasing do not become authorized merely because the audience broadens.
- Acceptance: one complete existing service flow, visible deadline risk, a useful next step and no invented provider outcome.

### PC-04. Multiple ways to reach the same assistant — proposed later connector slice

- The app supports richer planning, comparisons and controls. Slack DM/mention is another possible entrance for users who work there. Voice and native sharing can follow device validation; native implementation stays parked now.
- Map external workspace/user IDs to a proven account and explicit permissions. Keep private memory and team/channel visibility separate. Do not create a public `tester` identity bridge.
- Separate messaging adapters, source connectors and execution adapters. MCP can expose tools; incoming Slack messages still need a channel integration. A Gmail notification is a source event, not permission to act.
- Return progress and decisions to the chosen channel, with a link to richer app views where useful. All channels use the same task IDs, approvals, idempotency and audit trail.
- Acceptance: duplicate delivery, private/public boundary, conflicting channel instructions, source revocation and approval bound to the exact user and action snapshot.

### PC-05. Useful finished work — proposed with the first task pilot

- A delegated task should return something useful: a sourced comparison, meeting brief, draft reply, checklist, organized set of references or a revised plan. It need not involve a local merchant.
- Example: “Compare these internet plans for how I work” produces a dated comparison against user-supplied requirements, source links and unknowns. It does not purchase a plan or invent a current offer.
- Reuse existing research and structured response capabilities first. Keep versions and source references attached to the responsibility so the user can revise it next week without reconstructing the brief.
- Start with readable in-app outputs and links; a complete document/spreadsheet editor or arbitrary cloud desktop is not a prerequisite. Downloadable artifacts require their own ownership, retention and format checks.
- Acceptance: a comparison answers the actual criteria, missing facts stay explicit, corrections update the same result, and cross-owner artifact access is denied.

## 5. Recommended delivery sequence, awaiting pilot choice

| Phase | Outcome | Reused work / dependencies | Completion evidence |
|---|---|---|---|
| 0. Product validation | Choose a first audience and two recurring jobs; revise the demonstration around their ordinary week. | This proposal, existing app walkthrough, founder input. | The user can describe when to hand work over and what result to expect. This is the active planning task. |
| 1. Responsibility + Today | Hand over a task, leave, return, review progress/decision and correct it. | PA-01/02/03 + a bounded PC-05 output; existing actions/outbox/profile/research; database write health and ownership. | Restart/resume, exact approval, clear blocker and a complete useful result using manual inputs. |
| 2. Useful connected loop | One communications/calendar source plus a planning/service outcome. | PC-01/02/03; trusted eligibility, CTX/PLAN, explicit connector/Auth decision. | A real permitted source change produces a relevant reviewable result without leakage or duplicate action. |
| 3. Repeatable delegation | One reviewed routine and an optional second contact channel. | PA-04/PC-04; scheduler, cancellation, budgets, identity mapping. | The routine is useful over several cycles and can be stopped reliably. |
| 4. Expansion | Broader events, household/team collaboration and monetization. | Measured usage and source/merchant access; existing SUG/EVT/ADS backlog. | User value and reliability justify each added surface/connector. |

The sequence is a proposal, not permission to implement every listed capability. Original REC-03C/REC-04/CTX/PLAN/SUG/EVT/ADS/REV/DB tasks remain preserved. Some should become dependencies of these outcomes rather than a reason to spend all effort expanding a discovery feed first. No deadlines or provider access are invented.

## 6. Interface and onboarding direction

- Preserve the approved cyan/gradients, restrained glass, no shadows, single composer, explicit map modes and in-app browser requirement. Wi-Fi/arrival graphics can remain replayable or contextual; they should not force every new user through an airport story.
- Onboard by asking what the user wants help keeping on top of and how they want updates. Gather only needed context; request a connector when it helps a concrete task. Display claims must match available integrations.
- Main interaction verbs: ask, delegate, review, redirect and stop. Chat history is an interaction record; Today and task views expose what is actually underway.
- A future demo should follow a resident's ordinary week: an existing service deadline, a plan/commitment change and a useful reviewable next action. The old arrival/laundry/taxi script remains a historical working scenario until a new demo is selected. Label any seeded data, time jumps or sandbox merchant activity.

## 7. How to judge quality before adding more

- Outcome completion: did the user get the promised artifact or evidenced action, rather than merely an answer?
- Constraint adherence: correct date, recipient, account, fixed price, location and permissions; measure violations separately from recommendation engagement.
- Continuity: can work resume after interruption, across threads and eventually channels without rebriefing or context leakage?
- Attention: how many brief/notification items were useful, deferred or dismissed? Measure false urgency and repeated interruptions; a quiet day can be successful.
- Control: can users inspect provenance, correct memory, pause a routine and understand what cannot be undone?
- Reliability/cost: duplicate/unknown outcomes, recovery success, latency and bounded background/provider usage. Do not claim 24/7 operational reliability from a browser mock.

Pilot gates should exercise those dimensions with two real recurring jobs. Exact numeric targets need a baseline; new usage metrics should not be invented as achieved results.

## 8. Features to defer deliberately

Multiple visible specialist bots; a general cloud computer that logs into arbitrary websites; broad autonomous purchasing; public/private team collaboration; a large connector catalog; passive routine detection; always-on location; and sponsored placement in the decision inbox. These may increase engineering and trust costs before proving everyday usefulness.

Previously requested food sponsorship remains in the ledger. It should follow organic value, stay clearly labelled in relevant discovery contexts, and never influence an urgent task/approval or use restricted private-source evidence.

## 9. Open product decisions

1. First pilot audience: individual across life/work, household, or business operator/team. Asked asynchronously; not yet resolved.
2. Which two recurring responsibilities matter enough to test over multiple weeks? Select after the audience choice rather than use a generic feature checklist.
3. Should the first connected loop use calendar context, inbox follow-up or a real service partner? Depends on access and the chosen job. No connector is required just to understand or try manual task delegation.
4. The revised contest demo and commercial model need to follow observed value; the old visitor pitch and merchant-commission-first assumption should not silently determine them.

## 10. Subsequent authorization / review continuity

Founder authorized building from the reconciled review; Gate A manual tasks/Today is now source-implemented and SQLite verified, with later worker/connector/briefing gates still pending. Read `assistant-review-decisions.md` and current handoff before treating earlier proposed sequence/objects as authoritative. Native remains parked. Staged taxi replies first, Gmail later, freely licensed imagery and all 12 Duet design references are logged. New design/interaction/use-case report must be separate from the first critique; use `assistant-design-interaction-review-prompt.md`.
