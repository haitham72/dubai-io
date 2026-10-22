# External review prompt

Copy the following into the reviewing LLM. Supply the repository or referenced documents if available; otherwise the context below is self-contained.

---

Act as an independent senior product architect and UX lead reviewing **DubaiIO**. Critique the proposed plan; do not implement code or simply endorse it. Be candid about weak assumptions, excessive scope and missing dependencies.

**Product direction**

DubaiIO is a personal assistant for everyday life and work in Dubai. It is not defined by tourism, airport arrivals, maps or merchant discovery. The first pilot cohort and two recurring jobs are still open; individual residents across personal/work life are the working assumption.

We are learning from OpenAI Dots, Grok Bot and Claude Duet: ongoing responsibilities, continuity, background preparation, reusable routines, useful results and decisions that need the user. If you research competitors, verify claims with current official sources and distinguish documented behavior from marketing or assumptions. If browsing is unavailable, state that limit.

**Proposed experience**

1. Home/Today shows Needs you, In progress, Waiting and Recently completed. Tasks expose an outcome, constraints, progress, sources, artifacts and blockers. Users can correct, redirect, pause, resume or cancel them.
2. Swiping up from a dedicated Home region opens a personalized briefing, with a tap alternative. Topics include arts, media, regional news, politics and UAE regulation updates. Published articles come first; connected email newsletters are a later option. Cards have attribution, dates, concise permitted summaries, relevance explanations and source links. Reading can lead to a user-requested task or plan.
3. General interests can adapt from reviewed interactions and explicit choices. Politics is explicitly selected; political beliefs and sensitive traits must not be inferred. Regulatory claims need authoritative sources, jurisdiction, publication/effective dates where known and visible uncertainty; they are informational, not government execution or legal advice.
4. Useful work includes sourced comparisons, meeting briefs, draft messages, checklists, plans and local service follow-through. Gmail/Calendar and Slack are possible later connectors/contact channels. All channels share identity/task/approval state while preserving private/public boundaries.
5. Routines require a reviewed trigger, sources, steps, scope, notification policy and expiry. Background work must survive restarts, respect cancellation and avoid duplicate effects. Notifications should be useful and bounded rather than a constant feed.

**Existing foundations and constraints**

The current prototype has web chat, visible memory/profile controls, a moderate temporal recommender, Google place discovery and a fixed-price sandbox merchant approval/status loop. The new task system, Today, briefing and communication connectors are proposals, not implemented features.

Keep the approved cyan/gradients, restrained glass, no shadows, single composer and dock-to-chat transition. A targeted Home/task UX redesign is proposed. Maps and Services remain available. Native iOS work is parked.

Stack: FastAPI/Python, LangGraph, Supabase Postgres, an existing deterministic action/approval engine, outbox and SSE. Local database write health remains an unresolved deployment gate. External side effects need exact approvals and authoritative outcomes; no bidding, government execution, purchasing/payments or invented confirmations. Do not assume unrestricted news reuse, free APIs, mailbox access or real merchant partnerships.

With repository access, read PLAN.md, docs/references/personal-assistant-direction.md, docs/references/assistant-experience-plan.md, docs/implementation-plan.md and ARCHITECTURE.md. Treat the latest founder direction as overriding historical visitor-first prompts. Compare code when assessing what is already built.

**Review questions**

- Is this a coherent, useful product? Which specific jobs would make someone return weekly, and what would differentiate it from general agents and news apps?
- Does Today plus a swipe-up briefing create a clear hierarchy or split the product into unrelated experiences? Propose a better Home flow if needed, including gesture/accessibility and empty/error states.
- What should be built first, removed or deferred? Identify the smallest complete pilot, rather than a large feature checklist.
- Are task state, memory, source context, approvals and background execution separated correctly? Where could stale context, cancellation races, duplicate effects or channel leakage occur?
- Are news relevance, political-topic boundaries, regulatory provenance, source rights and newsletter privacy handled credibly?
- Are the proposed integrations, operating costs and reliability expectations realistic? Identify concrete unknowns and lighter alternatives without inventing access or pricing.

**Return**

1. A clear verdict and the five most serious problems, ranked by impact.
2. Specific changes: keep, change, remove and defer, with reasons.
3. A recommended Home/user journey and two concrete pilot jobs.
4. A revised delivery sequence with dependencies and measurable acceptance gates.
5. At most five questions whose answers would materially change the plan.

Separate facts, inferences and open decisions. Challenge the plan without replacing it with an equally broad wishlist.
