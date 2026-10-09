# Decisions

One line per decision, newest first. If a decision changes scope, update `PLAN.md` in the same commit.

| Date | Decision | Why |
|---|---|---|
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

- Hero merchant category: pharmacy vs unlisted long tail (laundry, tailor)?
- Lock the demo arc after external review (`PLAN.md §3`)
- Contest deadline, artifacts and IP terms
