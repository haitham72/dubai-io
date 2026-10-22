# Review reconciliation — 22 Oct 2026

The founder authorized building from the independent review after the primary agent's assessment. This reconciles the [original critique](assistant-experience-review.md) with PLAN.md. Preserve the critique as an independent opinion; implementation status belongs in docs/implementation-plan.md and handoff.md.

## Decisions

1. **Promise:** personal assistance for everyday life and work in Dubai, with continuity, evidence and exact control. Do not return to a visitor, merchant-only or regulation-only identity.
2. **Reading:** retain personalized briefing, initially optional and pull-only, outside task urgency. Preserve safe-region swipe plus accessible tap; validate on a phone. Visible hypotheses explain general interests. Politics needs explicit selection plus item/content and source controls, never inferred beliefs. Regulation remains one topic.
3. **Pilots:** service-with-evidence and delayed manual check-back. Without a connected source, check-back means a reminder/update request; it cannot detect an office reply or contact someone. Individual resident/worker is a working audience assumption, with the founder as tester; recurring user need still needs validation.
4. **Model:** Task + TaskEvent + Decision, existing Action as the only external executor/evidence. Add artifacts/routines/briefing records in their slices. Durable claims, recovery, fencing and bounded attempts remain required even without a Job table.
5. **Demo:** existing fixed-price service loop is strongest technical proof, within resident life. Label sandbox merchants. Briefing is not a dependency of a complete demo.
6. **Hosting:** healthy durable writes precede runtime adoption. Local contract tests can proceed separately; hosted worker, health visibility and an agreed budget precede always-on promises. No paid deployment/budget is assumed.
7. **Limits:** expose permissions, connected sources/revoke, cadence, ceilings and worker availability as they ship. Never fabricate monetary spend from request counts.
8. **Connectors:** manual-first, OAuth-last for the tester; retain staged connectors. Existing encrypted identity OAuth grants are credential custody; identity-only scopes are not Gmail access. Keep tokens out of chat/model/provider pages. No general browser/password automation in the pilot.
9. **Purchasing:** absent from this release; remains LATER in PLAN.md, not a permanent “never spends” brand promise.
10. **Newsletters:** public-news digest, followed publications and private email newsletters are separate concepts. Public sources are the working first interpretation; email remains deferred. Founder meaning/source shortlist remain open.

## Engineering qualifications

- Today: manual tasks are On your list, due ascending/undated last, with paused disclosure and quiet completed results. Needs you is reserved for real decisions; empty Needs you/Running stay hidden. Three-row previews never cap the handle totals or hide overflow. Waiting is a row state; no reading urgency or invented work. Today is a sheet above the preserved visual Home, not Home's replacement.
- Atomic task/event writes, revision-bound idempotent commands and owner checks. Model text and LangGraph checkpoints never set durable task or external status.
- Revision predicates fence local writes, not external calls already dispatched. Late provider evidence must remain in the action engine without reviving a cancelled task. Ambiguous external outcomes stay UNKNOWN_STATUS; no blind replay.
- Outbox dedupe prevents duplicate messages, not duplicate provider calls. Gate B needs persisted claims/expiry/recovery; Gate C binds decisions to existing action snapshots/idempotency.
- Task constraints are captured per revision. Hypotheses only rerank. Memory edits cannot silently change approved dates/recipients/shared fields; stale workers/caches must not undo Forget.
- Admit reading sources with retrieval/reuse basis, storage/display rules, publication/event/check dates, TTL and failure policy. No confirmed feed does not prove none exists. Begin with URL/title dedupe, not a claim of independent corroboration.
- Public docs do not establish competitor internals or exclusive safeguards. Dots describes separate notes/memory and dot deletion; update-only wording does not prove selective forgetting impossible. Treat comparative advantages as hypotheses.

## Delivery gates and nested pending work

### A — Persistent manual tasks + Today (active first slice)

- Owner-scoped create/list/detail/edit/pause/resume/cancel, idempotent writes, bounded events and zero LLM calls on task reads/commands.
- Manual tasks start Waiting for your update. Next step is optional; an example is a placeholder, never saved boilerplate. Saving does not activate monitoring or send anything. Completion records an explicit user-reported result with provenance, never a provider confirmation.
- Empty/loading/error states; preview caps never hide overflow. Preserve onboarding/gradients/discovery/single composer.
- Verify owner isolation, concurrent/stale edits, restart, duplicate submissions, terminal states, transactional rollback and phone-size UI. Versioned Supabase migration/private access and live PostgreSQL tests are separate adoption gates while writes are unhealthy.

### B — Delayed check-back (pending)

- Explicit check time, Dubai time zone and consent; persisted claims/expiry, retry/call limits, restart recovery and fencing. No LLM polling.
- Manual update request unless a permitted fresh source exists. Reuse outbox/quiet hours. Cancel/reschedule/acknowledgement must suppress obsolete pending messages.
- Test double sweeps, crash boundaries, cancellation/reschedule in flight, quiet hours and owner separation. Hosted availability/budget gates before always-on use.

### C — One service vertical linked to tasks (pending)

- Existing action engine only; task decision/revision binds exact action snapshot. Preserve evidence after task cancellation.
- Fixed catalog price, honest sandbox distinction, provider-only external completion; stale approvals invalidated by price/date changes. Test ambiguous send, timeout, late evidence and duplicate dispatch.

### D — Optional published briefing (pending; not a dependency of A–C)

- Source register, freshness/rights, topic taxonomy, explicit sensitive-content rules before adapters. Measure usefulness/cost; arbitrary open-rate targets are not proof of value.
- Bounded pull-only cards, controls/source links, honest outages/staleness, safe swipe/tap. No news push, private email ingestion or sponsored urgency.

### E — One connector; F — One reviewed routine (pending)

- Choose one connector after a useful manual loop; deliberately reorder OAuth then. Scope/revoke/isolation tests before use.
- Routines require Gate B durability, explicit activation/expiry, bounded cost and cancellation. Slack/channels, teams, general browser automation and native parity stay later.

## Preserved backlog and open inputs

This sequence logically precedes feature expansion under the founder's instruction to build from the review. REC-03C/04, CTX-02/PLAN-01, SUG-01/EVT-01, ADS-01, REV-01/02/03, DB-02/03 and native handoff remain logged. Database health never authorizes resetting volumes or replacing records. Weekly pilot pain, newsletter meaning, admitted sources and hosting ceiling remain open; none blocks Gate A's manual contract.

## Subsequent founder requests ? preserved for design/use-case review

### TAXI-02 / existing C6 recovery evolution [planned, staged-first confirmed]

- Entry: ?I forgot an item.? Ask for a receipt. With a receipt, extract only available identifiers as a proposal; user reviews/corrects them. Receipt upload/OCR remains a separate implementation need, not an existing task capability.
- Cash/no receipt: show the previous route and time as candidates; ask the user to confirm pickup, drop-off, date/time/timezone and any plate/roof/booking clues. Unknown stays unknown; browsing history is not proof of a trip.
- Prepare the minimal airport/RTA handoff with exact shared fields and user confirmation. No direct government execution is authorized by this demo request. Model output cannot claim contact occurred.
- Persistent recovery task shows next check, blockers, unanswered questions and evidence. Founder explicitly confirmed staged airport/RTA/driver replies first, visibly labelled Demo/staged at every result and decision; do not label the item genuinely recovered from a fixture.
- Later Gmail connector: explicit scopes/consent, bounded mailbox selection, sender/thread/reference validation, read-only reply ingestion, untrusted-body protection, dedupe, revoke/stale/unknown handling. A received email is not automatically authoritative proof of ownership or collection. Actual outbound contact remains a separate approved supported capability/handoff.
- A supported verified/staged response can propose pickup at the sourced place versus driver delivery. Confirm the location/time and any host-owned published fee. A new delivery effect needs a supported registered capability and exact approval. Found, collection arranged and delivered are distinct outcomes; never claim physical recovery from a sent request.
- Failure branches: no receipt, ambiguous route, no identifiers, no reply, not found, uncertain sender, conflicting place/time, cancellation while waiting, repeated reply, denied mailbox access and unavailable delivery. User can correct, stop tracking or use the official handoff at any stage.

### VIS-02 ? content image quality [requested, not implemented]

Audit missing/broken/content placeholders across the existing app. Replace them with attractive freely licensed category-appropriate imagery stored locally, with original source/author/licence and download date. Keep intentional cyan/approved-purple gradients and onboarding. Real venue photos must remain tied to the actual provider; editorial imagery must not pretend to depict a named venue. Verify phone cropping, readability/contrast, lazy loading and failure states. The 12 Duet screenshots are interaction references, not image-replacement assets.

### DX-REVIEW - second independent review [delivered; bounded correction reconciled below]

Founder supplied 12 frames in `design/references/claude duet/` and requested a separate design/interaction/UI/UX/use-case review. Read `design/CLAUDE.md`, their README and `assistant-design-interaction-review-prompt.md`. The new `assistant-design-interaction-review.md` is delivered beside the earlier critique; both remain independent and unchanged. Current implementation status and founder overrides belong here and in the plan/handoff.


## Second review assessment - 22 Oct

The independent design/interaction/use-case review is delivered in `assistant-design-interaction-review.md`. Preserve both reports as critiques. The primary agent checked the Today query, deck-hiding stylesheet, copy and recovery branch code and confirms the principal findings. The 143 backend / nine browser checks prove bounded contracts and flows, not full UI/product acceptance. No application changes are made by this assessment.

### Next correction sequence (the existing Gate A, not a new product diversion)

1. **DX-A: Today semantics and usability** (DX-01 through DX-06): due ascending/undated last; overdue/within-24h flags; paused disclosure/overflow; cached refresh; focus/announcements; inline cancel; title-first capture with optional empty next step. Founder subsequently explicitly selected On your list for manual tasks and Needs you for real decisions, with empty Running hidden. These bounded changes are implemented and verified as recorded below.
2. **DX-B: Home identity and copy** (DX-14 through DX-19, DX-08): **founder override supersedes DX-14's hide-the-deck premise** and the assessment's compact-photo-only recommendation. Preserve the full existing photo/gradient carousel and Wi-Fi/gradient onboarding; open Today from its own handle into a sheet. Keep qualified recommendation reasons visible. Everyday wording outside scripted airport, human status labels/data attributes and distinct errors are implemented. Neither review report is rewritten; this reconciliation records the newer instruction.
3. **DX-C: Reference-only task bridge** (DX-07 and start of DX-10): validate owner-bound references to existing actions/prepared reports; Keep track of this creates or reopens a manual task, without dispatching anything or changing source status. Task detail opens its linked item and can focus chat on the task with Clear. Proposals to change due dates still need a revision-bound before/after confirmation; task chat does not grant authority to send.
4. **TAXI-02 corrections before the expanded recovery demo** (DX-09/10/21): receipt-first, explicit confirmation/unknown values for route and time before any staged reply; persistent staged reply events; remove unchosen driver movement. Preserve the founder's collection-versus-delivery choice as a demo requirement. No live delivery is promised: it needs a supported capability/approval; any demo-only choice must remain clearly labelled. Existing prepared-report behavior is not completion of this flow.
5. **DX-11 location truth and DX-13 first-paint investigation:** an unconfirmed map anchor must be labelled as a demo area; no hard-coded personal area passed as fact to a mini-app. The reduced-motion Services first-paint report was observed once, so reproduce it before claiming a cause or fix.
6. **VIS-02 and DX-23:** the reviewer found 30 present image files rather than a blanket missing-assets problem. The remaining audit covers aesthetics/crops, author/photo-page/download/licence records and safe fallbacks. Standard free Unsplash-licensed images are a workable proposed source, subject to per-image verification; Unsplash+ and unknown-origin assets are not assumed covered. Licence checked at https://unsplash.com/license on 22 Oct; no individual asset provenance was verified by that check.

### Recommended answers to the five review questions

- Q1: reserve Needs you for genuine decisions; ordinary tasks go On your list.
- Q2: earlier compact-photo recommendation **superseded by the founder**: preserve full visual Home plus swipe-up/tap Today and recommendation reasons.
- Q3: no live delivery adapter exists. Keep the founder's staged choice visible without implying a real courier, booking or physical movement; real delivery remains conditional on a supported approved path.
- Q4: standard free Unsplash photos may be used as a proposed source with traceable per-photo records. Do not equate that licence with CC0 or assume every CDN image has been checked.
- Q5: the proposed onboarding-entry change is **not implemented**. Founder requested preserving the admired current Wi-Fi/gradient onboarding and replay; first-run entry remains as before. Ordinary assistant copy is everyday life/work. Airport wording remains within the scripted airport flow.

### Verification scope for the wider corrections

The current bounded pass verifies due-order/overdue/paused projections and owner isolation, title-only capture, command focus/live-region DOM updates, cancel/Escape, retained refresh, and both phone sizes/motion settings. Reference ownership/Keep-track bridge and receipt/cash/staged persistence remain unimplemented future checks. Real iPhone gestures, actual screen-reader output, Supabase/PostgreSQL adoption and background reliability remain separate gates. Retain the earlier backlog.

## Latest founder-directed bounded pass - implemented, device acceptance pending

The founder chose the best of both worlds: existing onboarding and visual Home retained, Today behind its own handle. This explicitly **supersedes DX-14's hide-the-deck premise**; no review report was edited. The next checklist is the operative acceptance contract, not a wholesale adoption of either critique.

- **Handle:** actual owner-scoped saved-task totals, zeros hidden, three-row preview cap does not affect totals. Needs you stays absent while no real Decision exists. Swipe starts only on the handle; tap, Enter and ArrowUp also open it. No bottom-edge/tab-bar capture or reduced-motion opening animation.
- **Today:** On your list manual tasks due ascending/undated last; overdue/within-24h cues with Dubai-time entry/display; paused disclosure/overflow; empty Needs you/Running hidden. No scheduled work invented.
- **Detail/capture:** Pause/Resume/Edit/Done restore state-chip focus and update a mounted polite live region; inline Cancel confirm, Escape keeps the task; cached refresh preserves content/scroll/focus. Next step starts empty with a placeholder. Done remains user-reported.
- **Copy:** ordinary Home/chat/Services/onboarding uses everyday assistant wording. Human status labels replace technical codes; `data-status` retains them. Ambiguous order outcomes no longer get a sent headline. Scripted airport copy is preserved.
- **Evidence:** SQLite full suite 145 passed/11 skipped; 17 task checks include due/overdue/paused, uncapped counts and owner isolation. Four Home/Today browser variants (390x844 and 428x926, normal/reduced motion) passed, including keyboard task actions/focus/announcement DOM, cached held refresh, handle gestures/edge exclusions and visible computed box-shadow checks. Wi-Fi/captive/install/gradient intro and keyboard Next passed all four variants. Actual order/report renderers were checked using fixtures; no action/contact sent. Six existing JS suites passed 92/8/12/5/3/5.
- **Still unverified:** physical iPhone gestures, screen-reader announcements, PostgreSQL/Supabase adoption and hosted/multi-worker behavior. Browser pointer movement is not physical-device proof. The broader image/provenance audit and other DX findings are not declared resolved.
- **Excluded by founder:** Keep-track bridge, taxi staged replies, Reading, cron/worker and Gmail. The chat manual capture entry is not a source bridge. Keep these queued; do not automatically implement them at the end of this pass. Native remains parked.

## Subsequent authorization - finish existing app, no redesign

The founder subsequently lifted the bounded feature holds and requested sustained completion, then clarified "finish it", not a redesign. Preserve the approved visual Home/onboarding/navigation and existing flows. DX-C source/report/order/task/chat links are now implemented and verified on isolated SQLite/browser (150 backend passed/11 skipped; both phone sizes/motion settings). Tracking is owner-bound/idempotent, never an approval/send/file, and opens current source state. Task context is resolved by owner/revision and used transiently with Clear/expiry; all original intents remain. Reviewed chat edits are next, followed by genuine Decisions and the existing staged taxi/check-back/Reading/connector/routine sequence. This does not declare the wider review resolved. Native, government/purchasing restrictions, provider/OAuth/device dependencies and database preservation remain unchanged; both independent review reports remain untouched.
