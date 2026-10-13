# CLAUDE.md — Dubai-io (contest build)

Instructions for any coding agent working in this repo. Read this first, then `PLAN.md`, then `ARCHITECTURE.md`.

## What this is

Dubai-io is a chat-first AI companion for people living in or visiting Dubai, built as an entry for the Create AI Agents Championship (Best Personal AI Agent). One conversation does three things:

1. **Companion (the "Jarvis" part):** greets visitors on arrival, guides them through DXB step by step, remembers what they tell it, and sends proactive in-chat messages that they've opted into.
2. **Services (the "WeChat" part, Talabat-normal):** a list sorted closest + ★ + price-from + turnaround, and each row opens its **own modal sandboxed HTML mini-app** (services / shops / stores / rides — same pattern). Fixed published prices only. **Bidding / quote / negotiation is FORBIDDEN in any form.** Requests go to a real merchant, and the merchant's real reply updates the chat.
3. **Platform:** a new shop joins from a photo of its price list, and the AI generates its mini-app for operator approval.

Civic guidance (official sources, citations) is LATER, not in the contest build.

**Stage: sketch (Phase 0).** The only code is the clickable HTML prototype in `demo/`.

## Research status (build branch — code-only)

* Paper trail (research, reviews, decisions, visitor evidence, handoff archive) lives on `main`. This branch keeps the 4 canon files + `demo/` only.
* Do NOT re-run forum research. Remaining task: verify contest facts on the official portal only (`dubaichamberdigital.com`, Dubai Media Office / WAM): submission deadline (Dec 2026 vs Jan 2027 conflict), final (first week May 2027), artifacts, judging criteria (no rubric published), IP terms. Then re-anchor `PLAN.md §4` dates.

## Docs (highest authority first)

| File | Role |
|---|---|
| `CLAUDE.md` (this) | Hard rules for agents |
| `PLAN.md` | **The single plan**: scope (IN / LATER / NEVER), demo arc, phases, gates |
| `ARCHITECTURE.md` | Build architecture, contracts, state machine |
| `demo/` | Clickable prototype (static, no build): chat, journey, Talabat list → modal, fixed-order machine; `demo/lab/` = Home v2 visual lab |
| `demo/_ref/services/` | **Services list (`cases.md`) + intake guide (`intake.md`).** New ideas go here, never into `PLAN.md` |
| `main` branch | Paper trail: `docs/` (decisions, design, visitors, vision, research, reviews) + `archive/` (handoff, old reviews) |

If a request needs something that `PLAN.md` lists as **LATER** or **NEVER**, stop and ask. Do not build a "small version" of it.

## Repo layout (schema — where things go, don't invent new top-level docs)

```
dubai-io/  (branch: build — code-only; paper trail lives on main)
├── CLAUDE.md / PLAN.md / ARCHITECTURE.md / README.md  # canon, this order
├── demo/                        # clickable prototype (static, no build)
│   ├── index.html               # phone + backstage shell, modal sheets
│   ├── app.js                   # chat, journey, Talabat list → modal, fixed-order machine
│   ├── data.js                  # fixtures only (merchants, bridge_scopes=[order.request])
│   ├── styles.css               # iOS light + cyan tokens (single source for Phase 1)
│   ├── miniapps/*.html          # one modal HTML mini-app per merchant (own branding)
│   └── maps/*                   # PLACEHOLDERS — replace with arrival-side maps
└── (Phase 1 scaffolds) apps/web + apps/api + apps/widgets, packages/contracts
```

Rules: never add top-level `*.md` beyond the four canon files (paper trail lives on `main`); never write code outside `demo/` until Phase 1 scaffold exists.

## Non-negotiable rules

1. **Truth in status.** Never show `Confirmed`, `Booked`, `Paid`, `Filed`, `Verified` or `Delivered` without an authoritative event: a merchant action in the inbox or a verified adapter response. LLM text never changes status. Use `UNKNOWN_STATUS` before you would invent a success.
2. **Every number has provenance.** Prices, balances, ratings, dates and counts carry `provenance` (`official | provider_confirmed | merchant_submitted | user_supplied | inferred | estimate | demo_fixture`) and `as_of`. Fixture data renders a visible `Demo data` pill.
3. **No invented positions or facts.** The arrival guide never claims an indoor position, belt, gate or queue time the user didn't confirm. Map pins mark only user-confirmed places. Prices and times are labelled estimates.
4. **No government execution.** Salik, DEWA, RTA, Tasjeel and fines are display-only or `Open official portal` links. No top-ups, no bookings, no wait times.
5. **No official branding.** Do not use the DubaiNow layout, government emblems or ministry logos. `screens/archive/` holds the rejected DubaiNow-clone montage; don't reuse it.
6. **Approval before side effects.** Sharing data with a merchant and sending a fixed-price order each need an explicit user tap on an approval card that lists exactly which fields get shared. Single approval only — there is no second quote approval because quotes do not exist.
7. **Only registered actions execute.** A card action's `id` must match a capability ID in the registry. The agent fills in *data*. It never writes executable payloads, HTML, SQL or URLs to call.
8. **Proactive = deterministic.** Reminders and triggers come from the scheduler/outbox, not from LLM polling. Every one is deduplicated (`dedupe_key`), consented, respects quiet hours, and is stored as a normal chat message. A trigger the user did not cause is labelled `Demo trigger` on stage. The PWA does **not** do background geofencing.
9. **Memory is user-given or visibly inferred.** Facts the user states are `user_supplied` and shown as "You told me". The temporal profiler may store inferences only as **hypotheses** (`provenance: inferred`, confidence, evidence, valid time). Each one is listed under "I noticed" with Confirm / Edit / Not true / Forget. An unconfirmed hypothesis may re-rank options only, with a visible "Because…" chip. It never pre-fills a field, appears on an approval card, triggers a proactive message or sets a status. Nothing about the user is stored where they can't see it. Health, religion, ethnicity, nationality-as-trait, gender, sexuality and politics are never inferred. See `ARCHITECTURE.md §12`.
10. **Widget sandbox:** provider HTML runs only from the separate widget origin, inside `<iframe sandbox="allow-scripts">`, with `connect-src 'none'`. It reaches the host only through the allowlisted `postMessage` bridge. See `ARCHITECTURE.md §6`.

## Service intake

**New ideas and services.** When the user adds an idea, a service or a reference image, follow [`demo/_ref/services/intake.md`](demo/_ref/services/intake.md).
- File it under `demo/_ref/services/<shops|service>/<category>/`.
- The default outcome is a category-registry row: filed cases are ~1% of the app, and the generic engine covers the rest. Add or extend a case in `demo/_ref/services/cases.md` (status `idea`) only when the idea needs a new pattern, rule or data source, or is a demo moment.
- Never write a case into `PLAN.md`.
- If the idea is unclear (category, the user's ask, what is sold or done, who confirms), ask before filing.
- If it touches a NEVER item, stop and say so.

## Stack (for Phase 1+, pin versions at scaffold)

- `apps/web`: **Vite + React + TypeScript** (founder decision 12 Oct, replaces Next.js), mobile-first PWA viewed in iPhone Safari, no native iOS build. Routes `/` (user), `/merchant` (inbox), `/ops` (onboarding review). Mini-apps stay sandboxed HTML (`<iframe sandbox="allow-scripts">`) served from `public/miniapps/`.
- `apps/api`: Python 3.12, FastAPI, Pydantic v2, LangGraph, SQLAlchemy 2 + Alembic.
- `apps/widgets`: static widget bundles served from a **different origin**.
- `packages/contracts`: Pydantic models are the source of truth. A script exports JSON Schema, and TS types are generated from it. Never hand-edit generated TS.
- PostgreSQL 16 + pgvector. No Redis, no PostGIS, no microservices.
- LLM: Anthropic Claude through config (`LLM_MODEL`). Never hard-code model IDs outside config.

## Commands

- Demo: `cd demo && python -m http.server 8765`, then open http://localhost:8765
- App (`apps/web`, once scaffolded): `cd apps/web && npm install && npm run dev -- --host`, then open `http://<pc-ip>:5173` on the iPhone (same Wi-Fi) and Add to Home Screen. HTTPS (tunnel or deploy) is needed for the live compass.
- API / tests / migrate / seed: Phase 1 fills in.

## Working conventions

- Repo: `github.com/haitham72/dubai-io` (private), branch `main`.
- Contracts change first (`packages/contracts`), then the generated types, then the code. A card or state change without a contract change is a bug.
- Every workflow ships with fixtures, a happy-path test and a failure-path test (provider timeout, merchant decline, empty retrieval, duplicate submit).
- Design tokens live in `demo/styles.css` on this branch (iOS light mode, cyan tint; `docs/DESIGN.md` on `main`). Do not invent new palettes.
- Keep the docs short. Tick `PLAN.md` checkboxes, and don't create new planning docs.
