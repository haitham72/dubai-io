# Claude review prompt — design, interaction, UI/UX and use cases

Copy the block below into Claude with access to this repository. This is the second review. The first product/architecture critique stays intact.

---

Act as an independent senior product designer, interaction designer and product architect reviewing **DubaiIO**. Assess whether the current app and planned experience are useful, coherent and beautiful. Inspect actual screens, interactions, code and references; do not simply endorse the plan or invent a larger feature list. **Review first; do not implement, change scope, commit or push.**

Write a **new** report at `docs/references/assistant-design-interaction-review.md`. Preserve `assistant-experience-review.md` as the earlier independent critique. Explicitly identify recommendations you retain, amend or supersede, with reasons. A new recommendation does not silently override a founder decision.

## Read and inspect

Read `design/CLAUDE.md` before interpreting visual references. It distinguishes AI-generated app explorations from founder-supplied files and unknown-purpose material. Preserve founder files, the flagged Wi-Fi-image uncertainty and the missing 01b/02b PNGs. Never recreate the deleted quote mockup or civic montage.

1. `PLAN.md`, `docs/references/assistant-review-decisions.md`, `docs/implementation-plan.md`, `ARCHITECTURE.md`, `handoff.md`, `docs/request-backlog.md`.
2. `docs/references/assistant-experience-plan.md`, `personal-assistant-direction.md` and the earlier `assistant-experience-review.md` in the same directory. Read reconciliation before treating the earlier review's proposals as requirements.
3. **All 12 images in `design/references/claude duet/`**, in timestamp order. `README.md` there indexes the frames. Cite exact filenames in visual findings. They are founder-supplied video frames illustrating interactions, not proof of implemented competitor internals. Learn from hierarchy, pacing, artifacts and approval placement; do not clone branding, palette or unsupported capabilities.
4. Current code: `apps/web/tasks.js`, `tasks.css`, `app.js`, `chat.js`, `page-host.js`, `recovery.js`, `offers.js`, `orders.js`, map/navigation files; `apps/api/app/tasks.py`, `actions.py`, `proactive.py`, and relevant tests. Check the uncommitted working tree as well as HEAD. Preserve other work.
5. If runtime is available, inspect `http://localhost:8010/index.html#today`, Maps `#maps`, and onboarding `#demo.wifi` (reload after a hash-only URL change). Preview widgets use 8011. Read handoff first: the preview uses separate SQLite records, not adopted Supabase state. If you cannot run/view something, label it unverified; do not invent observations. Do not contact providers, send messages, enter credentials, or mutate real user data.

## Product direction and current boundaries

- DubaiIO is a personal assistant for everyday life and work in Dubai. It is not a visitor companion, a maps encyclopedia, a merchant-only tool or a regulation-only tool. Test whether the chosen jobs create repeat usefulness beyond a general chatbot.
- Gate A is a newly implemented **manual** task/Today slice (143 SQLite backend tests pass, 11 live cases skipped; nine phone-size browser checks pass; PostgreSQL/physical-device adoption remains unverified): task create/list/detail/edit/pause/resume/cancel, user-reported completion, revisions/idempotency and activity. Task commands/reads do not call an LLM. Saving does not activate a worker, monitor email or send anything. Check handoff for latest test evidence.
- Later gates: delayed check-back → one existing service vertical linked through the Action engine → optional public-source briefing → one connector → one reviewed routine. Earlier recommender/context/plans/events/ads/database tasks remain logged. Native `ios-swift` is parked.
- Existing external actions require exact user approval, registered capabilities and authoritative evidence. No bidding, invented confirmations or government transactions. Purchasing/payments are absent from this release and remain LATER, not a permanent brand prohibition. Identity OAuth code exists; Gmail monitoring is not implemented.
- Preserve the approved cyan/purple identity, beautiful Wi-Fi/gradient onboarding, no shadows, single category row with Back, explicit 2D/3D selection, and one composer as browsing collapses into chat. Challenge execution and usability while preserving these decisions.

## Review these journeys end to end

1. **Today → manual responsibility → detail → update → pause/resume/cancel → return later.** Can people distinguish saved, waiting, actually running, blocked and completed? Are needs/next steps obvious? Check empty, overflow, stale edit, failure/retry, persistence, Back and keyboard/focus behavior. Does this feel like useful assistance or administrative work?
2. **Chat ↔ browsing/maps/services ↔ task/result.** One composer, context focus/Clear, return position, card density, no search stacked over the browse menu, stable 2D/3D, and truthful unavailable states. Avoid showing infrastructure jargon to ordinary users.
3. **Taxi lost-item recovery, receipt and cash branches.** Founder wants: ask whether there is a receipt; if cash/no receipt, confirm the previous route and time rather than guessing; prepare the airport/RTA handoff; keep a persistent recovery task; show checks and replies; when an authoritative reply identifies the item, ask collection from a stated place versus supported delivery. Founder confirmed **clearly labelled staged airport/RTA/driver replies first; real Gmail response monitoring later**. Do not mistake this request for a built recovery/authority/delivery integration. Current government execution remains excluded. Show exactly where user confirmation, approved sharing, real versus staged evidence, wait/unknown/not-found, and a new delivery approval belong. A found item is not yet delivered; a sent request is not a recovery.
4. **Home → personalized reading → article → question/task proposal.** Relevant arts/media/region/UAE updates, explicitly selected politics, public/newsletter distinctions, a safe swipe-up entrance plus tap. Reading stays separate from urgent decisions. Adaptation must evolve from visible first-party evidence with correction/forget, not fixed suggestions or inferred beliefs. Evaluate hierarchy without making briefing the task-release dependency.
5. **Service-with-evidence.** Fixed published catalog price, sandbox mini-app, exact approval, provider event, deadline conflict and an honest unknown result. Existing merchant proof supports the broader assistant. A Google listing is not a fulfillment partner or ticket stock.

## Visual and interaction assessment

- Cover composition, hierarchy, typography, spacing, cyan/gradient balance, card vocabulary, photo treatment, motion, gesture conflicts, touch targets, contrast, accessibility, keyboard/safe areas and consistency across Today/chat/tasks/maps/services/onboarding.
- Compare Duet's notification → compact summary → decision card → result artifact → draft/send → refreshed artifact → follow-up flow with DubaiIO. Identify useful principles and places that require a different solution. Static frames cannot prove animation quality or backend safeguards.
- Founder requested **beautiful, freely licensed images for content placeholders**, stored locally with source/licence records. Audit actual placeholders and broken/missing assets; distinguish intentional gradients from missing photos and editorial category imagery from real venue photos. The Duet screenshots are reference material, not replacement product assets. Image replacement is pending unless the working tree proves otherwise.
- Test phone sizes around 390×844 and 428×926 if possible, plus reduced motion and keyboard access. Label physical-device claims separately. No superficial score without concrete evidence.

## Required report structure

1. **Verdict and five highest-impact problems:** what works, what prevents usefulness, and what should change before the founder's thorough review.
2. **Reference analysis:** all 12 frames mapped to observed interaction/design principles; distinguish observation, inference and undocumented behavior.
3. **Journey matrix:** for every journey above, record entry/context → user action → assistant response → decision/evidence → next step → interruption/failure → return. Mark implemented, partial, staged-demo, planned or unverified per step.
4. **Screen-by-screen recommendations:** concrete annotated proposals or text wireframes for Home/Today, task detail, chat/composer, recovery, reading and service handoff. Preserve the visual locks. Tie each recommendation to a demonstrated problem.
5. **Findings table:** stable ID (DX-01…), severity, journey/screen/state, evidence (file/line and screenshot filename where applicable), consequence, proposed fix, verification criterion and dependency. Separate usability defects, visual defects, missing capability and unvalidated product assumptions.
6. **Reconciliation with the earlier review:** prior RV/C/gate → retain/amend/supersede/defer → reason and scope consequence. In particular scrutinize the receipts-only thesis, tap-only briefing, permanent credential/payment bans, politics publisher-only gate, and worker/idempotency assumptions.
7. **Prioritized build plan:** fixes before founder review, smallest complete demo, later work, dependencies and measurable acceptance. No architecture rewrite or new feature family without evidence it is necessary. Identify the next three concrete changes.
8. **At most five material questions**, plus a verification log listing what you inspected, ran, could not verify, and any primary sources consulted.

Be candid and specific. Distinguish facts, hypotheses, preferences and open decisions. Screenshots alone do not prove product reliability; code alone does not prove a good experience. Keep the report reviewable and actionable, not long for its own sake.

---

Output is a new critique, not an implemented redesign or an instruction to overwrite the plan. After the founder chooses changes, reconcile accepted findings back into PLAN.md and the implementation plan.
