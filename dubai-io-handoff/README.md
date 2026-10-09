# Dubai-io — Canonical Project Handoff

**Product:** Dubai-io (`dubai-io.com` is the intended brand/domain; domain ownership/availability is not asserted here)  
**Positioning:** Your Intelligent Dubai Companion  
**Status:** Strategy and technical design; not evidence of deployed integrations  
**Baseline:** 8 October 2026  
**Revision:** v1.2 — added `06-DETAILED-USE-CASES.md` with fully expanded S01–S25 use cases, T01–T10 tourist refinements, X01–X20 new candidates, event contracts, acceptance tests, and Work implementation instructions. Original v1.1 documents remain otherwise unchanged.

## Read these in order

| File | Purpose | Primary audience |
|---|---|---|
| `00-MVP-FREEZE.md` | Contest MVP override — what builders/agents must/must-not build | All builders, coding agents |
| `01-PRODUCT-VISION.md` | What we are building, why, UX identity, feature horizons | Founder, product/design teams, planning LLM |
| `02-SYSTEM-ARCHITECTURE.md` | Modules, state, data, messaging, memory, trust boundaries, technology | Technical architect, core engineers |
| `03-SCENARIO-LIBRARY.md` | 25 indexed scenarios, ten detailed tourist-case refinements, proactive journey examples and evaluation cases | Product, UX, evals, agent teams |
| `04-SERVICE-INTEGRATION-STANDARD.md` | Merchant/provider onboarding, capability contract, action states and schemas | Integration teams, AI coding agents |
| `05-CONTEST-MVP-AND-VALIDATION.md` | What to ship first, milestone gates, demo, measurements, unresolved research | Founder, competition team, QA |
| `06-DETAILED-USE-CASES.md` | Full expanded examples, 10 tourist deep-dives, 20 additional candidate stories, UX/tool states, privacy and acceptance tests | ChatGPT Work, product/UX engineers, integration and QA agents |
| `07-AI-NATIVE-SERVICE-ECOSYSTEM.md` | Living service ecosystem, merchant registry hierarchy, mini-app distribution | Ecosystem architect, marketplace team |
| `08-UNIFIED-VISION-AND-FINAL-SPECIFICATION.md` | Authoritative master specification, 4-pillar synthesis (Dubai Now + WeChat + Jarvis + Dual-Mode), 4-minute contest script, and phased build roadmap | Founder, jury, full engineering team |

## Non-negotiable boundaries

1. **Keep the product identity:** a Dubai companion integrating **WeChat-style communication and services (including sandboxed inner-HTML widgets/mini-apps)**, **Reddit-style community intelligence**, **AI memory and orchestration**, and **verified civic information (DubaiNow-inspired, no affiliation with the official DubaiNow app)**. It is *not* an airport-only, tourist-only, or fine-warning-only app.
2. **Keep the UI simple:** a chat-first, context-aware experience with reusable cards **and three render modes: compact card → expanded inner-HTML widget → full embedded mini-app (sandboxed iframe, versioned manifest, capability-scoped bridge)**. Services can grow without adding new top-level screens for every category.
3. **Keep implementation honest:** do not show *Booked / Paid / Confirmed / Verified* without authoritative confirmation; do not invent fares, fines, quotas, discounts, business licenses or API access.
4. **Keep horizons distinct:** product vision ≠ competition MVP ≠ implemented behavior. Workflows labelled proposed are hypotheses until verified. Background geofencing is not a browser-PWA feature to assume.
5. **Integrate providers safely:** AI can help normalize service specifications and generate adapters, but only approved capabilities execute, with user permission and audit trails.
6. **Proactive messages are real chat messages:** scheduled/provider/device events feed one deduplicated, consented message timeline with trusted dynamic cards; not arbitrary unsolicited promotions.
7. **Venue and parking accuracy matter:** indoor landmark positioning needs verified venue geometry and manual confirmation; parking floor/pillar is saved from user input/photo, not inferred from GPS.

## What this package deliberately does not include

- Raw transcripts, duplicated LLM opinions or unverified 2026 research presented as fact.
- Production-ready legal advice, pricing tables or live-airport/medical/payment connectors.
- The idea that a CSV alone can execute third-party transactions.

## How to delegate

- **Planning LLM:** `01`, `05` → detailed implementation work breakdown.
- **Architect LLM:** `01`, `02`, `04` → architecture decisions and repo contracts.
- **Integration agents:** `03`, `04`, `05`, `06` → implement one verified provider workflow at a time.
- **QA/research agents:** `03`, `05`, `06` → source verification, evaluation cases and failures.

Every proposed feature should cite one of these files and be labelled **vision**, **MVP**, **pilot**, or **verified integration**.

## Revision v1.1 — what changed after the original handoff

- `01-PRODUCT-VISION.md`: proactive companion message journey and product principles.
- `02-SYSTEM-ARCHITECTURE.md`: event-to-message pipeline, device signals, native/PWA limitations, ticket authorization, landmark wayfinding and parking memory data contracts.
- `03-SCENARIO-LIBRARY.md`: retained all existing 20 scenarios, expanded to 25, included all ten additional tourist workflows and explicit snorkeling/delivery/trip/ticket/parking examples.
- `04-SERVICE-INTEGRATION-STANDARD.md`: provider update/webhook and action-card contracts for real, trustworthy notifications.
- `05-CONTEST-MVP-AND-VALIDATION.md`: tightly scoped reminder enhancement and staged roadmap for native geofencing/indoor mapping.

**No verified production API access or commercial partner commitments are implied by this revision.** All live prices, fines, discounts, transport zones, tickets, venue positions and eligibility rules must be verified before use.


## Revision v1.2 — detailed use-case handoff

- Added `06-DETAILED-USE-CASES.md` as a standalone, self-contained, expanded scenario reference.
- Keeps scenario IDs `S01`–`S25` unchanged and extends rather than overwrites the original cases.
- Adds ten detailed `T` tourist overlays and twenty new `X` candidate concepts, cross-scenario stories, test contracts, permissions and failure handling.
- This new file does **not** make unverified partners, prices, regulations or APIs real.

## Revision v1.3 — canonical final specification

- Added `08-UNIFIED-VISION-AND-FINAL-SPECIFICATION.md` as the unified master blueprint.
- Explicitly concatenated **Civic Lifecycle (DubaiNow-inspired, no affiliation)**, **WeChat (merchant onboarding, inner-HTML dynamic cards/mini-apps, marketplace)**, and **Jarvis (proactive context engine, geofencing anticipation, parking OCR, checklist automation)** across both **Visitor** and **Resident** modes.
- Defines the 4-minute live stage demo script and the phased build roadmap for the Create AI Agents Championship.

## Revision v1.4 — WeChat-inner-HTML + Civic + Jarvis thesis (current)

- Central thesis locked: **one conversation → AI-selected inner-HTML widget/mini-app → authorized action → persistent watch/reminder**.
- `00-MVP-FREEZE.md` is now the build override for contest scope.
- `07` header fixed (was mislabelled Document 08); `07` is the mini-app/registry vision authority.
- `08` demoted from "locked build spec" to contest narrative synthesis; dangerous specifics (exact fines, wait times, balances) must be labelled examples/sandbox.
- "Dubai Now" renamed to "Civic Lifecycle (DubaiNow-inspired)" everywhere to avoid implying official integration.

