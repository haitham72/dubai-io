# CLAUDE.md — Dubai-io (contest build)

Instructions for any coding agent working in this repo. Read this first, then `PLAN.md`, then `ARCHITECTURE.md`.

## What this is

Dubai-io is a chat-first AI companion for people living in or visiting Dubai, built as an entry for the Create AI Agents Championship (Best Personal AI Agent). One conversation does three things:

1. **Companion (the "Jarvis" part):** remembers context and sends proactive in-chat messages that the user has opted into.
2. **Services (the "WeChat" part):** finds a local merchant, sends a real quote request, and shows the merchant's real reply. The UI is typed cards, optionally expanded into a sandboxed HTML widget.
3. **Civic trust layer:** official-source answers with citations, plus a complaint draft and a link to the official channel. It is never a government transaction.

## Document authority (highest wins)

| Rank | File | Role |
|---|---|---|
| 1 | `CLAUDE.md` (this) | Hard rules for agents |
| 2 | `PLAN.md` | **MVP freeze**: what is in and out of scope, phases, gates. This replaces the `00-MVP-FREEZE.md` that the handoff docs cite; that file was never written |
| 3 | `ARCHITECTURE.md` | Build architecture, contracts, state machine |
| 4 | `dubai-io-handoff/05`, `02`, `04` | Background detail. Where they conflict with 1–3, 1–3 win |
| 5 | `dubai-io-handoff/01`, `03`, `06`, `07`, `08` | Vision and reference library only. **They add no scope** |
| — | `dubai-io-implementation-plan.md` | **Superseded** by `PLAN.md` and `ARCHITECTURE.md`. Do not build from it |
| — | `REVIEW.md`, `Muse-report.md`, `cursor-plan_review.md` | Reviews. Context only |

If a request needs something that `PLAN.md` lists as **OUT**, stop and ask. Do not build a "small version" of it.

## Non-negotiable rules

1. **Truth in status.** Never show `Confirmed`, `Booked`, `Paid`, `Filed`, `Verified` or `Delivered` without an authoritative event: a merchant action in the inbox or a verified adapter response. LLM text never changes status. Use `UNKNOWN_STATUS` before you would invent a success.
2. **Every number has provenance.** Prices, balances, ratings, dates and counts carry `provenance` (`official | provider_confirmed | merchant_submitted | user_supplied | estimate | demo_fixture`) and `as_of`. Fixture data renders a visible `Demo data` pill.
3. **No invented law.** A civic answer quotes only retrieved chunks and shows issuer, title, article, URL and retrieved date. If retrieval finds nothing, the agent abstains. Never hard-code law names or article numbers in prompts, UI copy or fixtures.
4. **No government execution.** Salik, DEWA, RTA, Tasjeel and fines are display-only or `Open official portal` links. No top-ups, no bookings, no wait times.
5. **No official branding.** Do not use the DubaiNow layout, government emblems or ministry logos. Say "DubaiNow-inspired" only in internal docs. Archive `screens/Dubai-io Civic Services UI Montage-ios minimal screens.jpg`; it is an anti-pattern.
6. **Approval before side effects.** Sharing data with a merchant, sending a request and accepting a quote each need an explicit user tap on an approval card that lists exactly which fields get shared.
7. **Only registered actions execute.** A card action's `id` must match a capability ID in the registry. The agent fills in *data*. It never writes executable payloads, HTML, SQL or URLs to call.
8. **Proactive = deterministic.** Reminders and triggers come from the scheduler/outbox, not from LLM polling. Every one is deduplicated (`dedupe_key`), consented, respects quiet hours, and is stored as a normal chat message. A trigger the user did not cause is labelled `Demo trigger` on stage. The PWA does **not** do background geofencing.
9. **Parking floor/pillar comes from the user** (photo plus typed or confirmed text). It is never inferred from GPS.
10. **Widget sandbox:** provider HTML runs only from the separate widget origin, inside `<iframe sandbox="allow-scripts">`, with `connect-src 'none'`. It reaches the host only through the allowlisted `postMessage` bridge. See `ARCHITECTURE.md §6`.

## Stack (pinned in Phase 0, see PLAN.md)

- `apps/web`: Next.js (App Router, TypeScript), mobile-first PWA. Routes `/` (user), `/merchant` (inbox), `/ops` (onboarding review).
- `apps/api`: Python 3.12, FastAPI, Pydantic v2, LangGraph, SQLAlchemy 2 + Alembic.
- `apps/widgets`: static widget bundles served from a **different origin**.
- `packages/contracts`: Pydantic models are the source of truth. A script exports JSON Schema, and TS types are generated from it. Never hand-edit generated TS.
- PostgreSQL 16 + pgvector. No Redis, no PostGIS, no microservices.
- LLM: Anthropic Claude through config (`LLM_MODEL`). Never hard-code model IDs outside config.

## Commands

_Not yet scaffolded. Phase 0 must fill this section in: install, dev, test, lint, migrate, seed, eval._

## Working conventions

- No git repo exists yet. The first action of Phase 0 is `git init` and committing the docs as they are.
- Contracts change first (`packages/contracts`), then the generated types, then the code. A card or state change without a contract change is a bug.
- Every workflow ships with fixtures, a happy-path test and a failure-path test (provider timeout, merchant decline, empty retrieval, duplicate submit).
- Design tokens come from `ARCHITECTURE.md §9` (Editorial Luxury: cream / ink / gold). Do not invent new palettes.
- Keep the docs short. Update `PLAN.md` gate status; don't create new planning docs.
