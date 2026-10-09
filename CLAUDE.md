# CLAUDE.md — Dubai-io (contest build)

Instructions for any coding agent working in this repo. Read this first, then `PLAN.md`, then `ARCHITECTURE.md`.

## What this is

Dubai-io is a chat-first AI companion for people living in or visiting Dubai, built as an entry for the Create AI Agents Championship (Best Personal AI Agent). One conversation does three things:

1. **Companion (the "Jarvis" part):** greets visitors on arrival, guides them through DXB step by step, remembers what they tell it, and sends proactive in-chat messages that they've opted into.
2. **Services (the "WeChat" part):** an aggregator card lists merchants, and each opens its **own sandboxed HTML mini-app**. Requests go to a real merchant, and the merchant's real reply updates the chat.
3. **Platform:** a new shop joins from a photo of its price list, and the AI generates its mini-app for operator approval.

Civic guidance (official sources, citations) is LATER, not in the contest build.

**Stage: sketch (Phase 0).** The only code is the clickable HTML prototype in `demo/`.

## Docs (highest authority first)

| File | Role |
|---|---|
| `CLAUDE.md` (this) | Hard rules for agents |
| `PLAN.md` | **The single plan**: scope (IN / LATER / NEVER), demo arc, phases, gates |
| `ARCHITECTURE.md` | Build architecture, contracts, state machine |
| `docs/DESIGN.md` | Style tokens, layout, trust labels, screen status |
| `docs/DECISIONS.md` | Decision log, newest first |
| `docs/VISITORS.md` | Visitor needs as hypotheses to test + interview script. Not evidence |
| `docs/VISION.md` | Long-term vision. **Adds no scope** |
| `archive/` | Original handoff 01–08, old implementation plan, past reviews. Reference only, never build from it |

If a request needs something that `PLAN.md` lists as **LATER** or **NEVER**, stop and ask. Do not build a "small version" of it.

## Non-negotiable rules

1. **Truth in status.** Never show `Confirmed`, `Booked`, `Paid`, `Filed`, `Verified` or `Delivered` without an authoritative event: a merchant action in the inbox or a verified adapter response. LLM text never changes status. Use `UNKNOWN_STATUS` before you would invent a success.
2. **Every number has provenance.** Prices, balances, ratings, dates and counts carry `provenance` (`official | provider_confirmed | merchant_submitted | user_supplied | estimate | demo_fixture`) and `as_of`. Fixture data renders a visible `Demo data` pill.
3. **No invented positions or facts.** The arrival guide never claims an indoor position, belt, gate or queue time the user didn't confirm. Map pins mark only user-confirmed places. Prices and times are labelled estimates.
4. **No government execution.** Salik, DEWA, RTA, Tasjeel and fines are display-only or `Open official portal` links. No top-ups, no bookings, no wait times.
5. **No official branding.** Do not use the DubaiNow layout, government emblems or ministry logos. `screens/archive/` holds the rejected DubaiNow-clone montage; don't reuse it.
6. **Approval before side effects.** Sharing data with a merchant, sending a request and accepting a quote each need an explicit user tap on an approval card that lists exactly which fields get shared.
7. **Only registered actions execute.** A card action's `id` must match a capability ID in the registry. The agent fills in *data*. It never writes executable payloads, HTML, SQL or URLs to call.
8. **Proactive = deterministic.** Reminders and triggers come from the scheduler/outbox, not from LLM polling. Every one is deduplicated (`dedupe_key`), consented, respects quiet hours, and is stored as a normal chat message. A trigger the user did not cause is labelled `Demo trigger` on stage. The PWA does **not** do background geofencing.
9. **Memory is user-given.** Belt, taxi number, hotel area and similar facts are stored as `user_supplied` and shown with a "You told me" label. Nothing is inferred silently.
10. **Widget sandbox:** provider HTML runs only from the separate widget origin, inside `<iframe sandbox="allow-scripts">`, with `connect-src 'none'`. It reaches the host only through the allowlisted `postMessage` bridge. See `ARCHITECTURE.md §6`.

## Stack (for Phase 1+, pin versions at scaffold)

- `apps/web`: Next.js (App Router, TypeScript), mobile-first PWA. Routes `/` (user), `/merchant` (inbox), `/ops` (onboarding review).
- `apps/api`: Python 3.12, FastAPI, Pydantic v2, LangGraph, SQLAlchemy 2 + Alembic.
- `apps/widgets`: static widget bundles served from a **different origin**.
- `packages/contracts`: Pydantic models are the source of truth. A script exports JSON Schema, and TS types are generated from it. Never hand-edit generated TS.
- PostgreSQL 16 + pgvector. No Redis, no PostGIS, no microservices.
- LLM: Anthropic Claude through config (`LLM_MODEL`). Never hard-code model IDs outside config.

## Commands

- Demo: `cd demo && python -m http.server 8765`, then open http://localhost:8765
- App: not yet scaffolded (Phase 1 fills in install, dev, test, lint, migrate, seed).

## Working conventions

- Repo: `github.com/haitham72/dubai-io` (private), branch `main`.
- Contracts change first (`packages/contracts`), then the generated types, then the code. A card or state change without a contract change is a bug.
- Every workflow ships with fixtures, a happy-path test and a failure-path test (provider timeout, merchant decline, empty retrieval, duplicate submit).
- Design tokens come from `docs/DESIGN.md` (iOS light mode, cyan tint). Do not invent new palettes.
- Keep the docs short. Tick `PLAN.md` checkboxes, log decisions in `docs/DECISIONS.md`, and don't create new planning docs.
