# Decisions

One line per decision, newest first. If a decision changes scope, update `PLAN.md` in the same commit.

| Date | Decision | Why |
|---|---|---|
| 2026-10-09 | Working persona: **short-stay business visitor**; "European" is optional, not a differentiator | Traits that matter: short stay, deadline, unfamiliarity (review round 2) |
| 2026-10-09 | Rejected for now: "first 24 hours" card and flight-delay beat. Flight delay may *replace* the laundry-conflict beat later, never add to it | Keeps the arc focused; test the current arc first |
| 2026-10-09 | Archive scenarios and LLM reviews are hypotheses, not evidence. Findings are tracked as frequency / consequence / workaround separately; facts are checked against sources, not interviews | Avoid false confidence |
| 2026-10-09 | Hotel concierge treated as the main competitor for this persona | It may already solve shirt pressing and taxi problems |
| 2026-10-09 | Core promise: **"remembers your situation and follows through with local merchants, with you approving what gets shared"**. Companion = product, mini-apps = mechanism, onboarding = growth | External review: the demo read as three competing products |
| 2026-10-09 | Hero merchant: **independent laundry with a deadline**, not pharmacy | Pharmacy looks like talabat/Careem; a deadline creates a real agent decision |
| 2026-10-09 | Add a **deadline-conflict beat** (quote 10:00 vs need 09:00 → ask for earlier) | Turns a merchant reply into an agent decision |
| 2026-10-09 | Close the pitch on the **lost-bag memory payoff**; onboarding goes before it | End with the person being helped |
| 2026-10-09 | Remove the Civic tab from the sketch; the forbidden-payment demo is for Q&A only | Fewer promises on stage |
| 2026-10-09 | Mock fixes: lost-bag intent, explicit hotel arrival, merchant-originated updates | They contradicted the story |
| 2026-10-09 | Docs consolidated: `PLAN.md` is the single plan; handoff 01–08, the old implementation plan and all reviews moved to `archive/` | 17 overlapping files, no clear authority |
| 2026-10-09 | We're in **sketch mode**: no legal/citation or licensing work yet. Airport maps are placeholders | Validate the idea and story first |
| 2026-10-09 | Visual style: **iOS light + cyan** (replaces Editorial Luxury gold) | Founder preference; native feel |
| 2026-10-09 | Demo opens with **"Hello, visitor" → DXB arrival guide → taxi/Metro** | Universal, emotional hook |
| 2026-10-09 | Services open as **per-merchant HTML mini-apps** from an aggregator card (WeChat model) | The core differentiator |
| 2026-10-09 | Civic RAG, vehicles, Salik/DEWA moved to LATER | Keep the contest build focused |
| 2026-10-09 | Mini-app sandbox: `allow-scripts` only, no network, scoped `postMessage` bridge; host executes, widget never does | Security by construction |
| 2026-10-09 | Request states add `DECLINED` and `QUOTE_ACCEPTED` (user approves the price) | Gaps in the original state machine |
| 2026-10-09 | The LLM can read and propose; only user/merchant taps change state | Truth in status by construction |
| 2026-10-09 | Stack: Next.js + FastAPI + LangGraph + Postgres/pgvector; no Redis, PostGIS or microservices | Solo-builder sized |
| 2026-10-09 | Visitor/resident mode is a user setting, not auto-detected | No reliable signal |

## Open

- **Why not the hotel concierge?** Interviews must show where hotel help falls short
- Lock demo arc v2 after the interviews and laundry tabletop (`PLAN.md §3`)
- Contest deadline, artifacts and IP terms
