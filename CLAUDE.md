# CLAUDE.md — Dubai-io (contest build)

Instructions for any coding agent working in this repo. Read this first, then `PLAN.md`, then `ARCHITECTURE.md`.

## What this is

Dubai-io is a chat-first AI companion for people living in or visiting Dubai, built as an entry for the Create AI Agents Championship (Best Personal AI Agent). One conversation does three things:

1. **Companion (the "Jarvis" part):** greets visitors on arrival, guides them through DXB step by step, remembers what they tell it, and sends proactive in-chat messages that they've opted into.
2. **Services (the "WeChat" part, Talabat-normal):** a list sorted closest + ★ + price-from + turnaround, and each row opens its **own modal sandboxed HTML mini-app** (services / shops / stores / rides — same pattern). Fixed published prices only. **Bidding / quote / negotiation is FORBIDDEN in any form.** Requests go to a real merchant, and the merchant's real reply updates the chat.
3. **Platform:** a new shop joins from a photo of its price list, and the AI generates its mini-app for operator approval.

Civic guidance (official sources, citations) is LATER, not in the contest build.

**Stage: contest loop working (19 Oct).** Current branch: `redesign`. `apps/web/` is the cyan frontend; `apps/api/` serves it and runs Luna (understanding only), the action engine with the `order.request` capability and a **sandbox merchant inbox adapter** (`merchant.py`), host catalog pricing (`catalog.py`), SSE status, the proactive outbox (`proactive.py`), the profile store (`profile.py`), live Google Places/Routes, and a separate widget origin on `WIDGET_PORT`. No real merchant or government adapter exists. Status of record: `docs/handoff.md`.

## Research status

* Paper trail (research, reviews, decisions, visitor evidence, handoff archive) lives on `main` and `docs/`. The current `redesign` branch contains the four canon files, `apps/`, `design/`, and `docs/`.
* Do NOT re-run forum research. Remaining task: verify contest facts on the official portal only (`dubaichamberdigital.com`, Dubai Media Office / WAM): submission deadline (Dec 2026 vs Jan 2027 conflict), final (first week May 2027), artifacts, judging criteria (no rubric published), IP terms. Then re-anchor `PLAN.md §4` dates.

## Docs (highest authority first)

| File | Role |
|---|---|
| `CLAUDE.md` (this) | Hard rules for agents |
| `PLAN.md` | **The single plan**: scope (IN / LATER / NEVER), demo arc, phases, gates |
| `ARCHITECTURE.md` | Build architecture, contracts, state machine |
| `docs/handoff.md` | Current implementation status and remaining work; cannot override the canon |
| `docs/references/redesign.md` | Screen references and historical prompts; current navigation follows `PLAN.md` §§6.4, 7.5 |
| `docs/references/visuals-libraries.md` | Visual effect references; supplied prompts are preserved verbatim |
| `docs/services/` | **Services list (`cases.md`) + intake guide (`intake.md`).** New ideas go here, never into `PLAN.md` |
| `docs/` | Product review, engineering evaluations (`gemini-review.md`), decisions |

Read order: this file → `PLAN.md` → `ARCHITECTURE.md` → `docs/handoff.md`; follow the routed references for the task. Newer explicit founder decisions in `PLAN.md` supersede older reference prompts. Historical fixtures do not promote LATER features into scope.

If a request needs something that `PLAN.md` lists as **LATER** or **NEVER**, stop and ask. Do not build a "small version" of it.

## Repo layout (schema — where things go, don't invent new top-level docs)

```
dubai-io/  (current branch: redesign; paper trail on main)
├── CLAUDE.md / PLAN.md / ARCHITECTURE.md / README.md  # canon
├── apps/
│   ├── web/                                   # active cyan frontend (HTML/CSS/ES modules)
│   │   ├── index.html / app.js / stage*.css
│   │   ├── arrival.js                         # Wi-Fi captive sign-in & app install flow
│   │   ├── chat.js / guide.js / offers.js / map.js / profile.js
│   │   ├── data.js                            # categories, places, profile fixtures
│   │   └── miniapps/ / fixtures/ / media/ / tests/
│   └── api/                                   # FastAPI + LangGraph API backend
│       ├── app/main.py / config.py / google_maps.py / luna/
│       └── data/ / tests/ / requirements.txt
├── design/
│   ├── references/                            # visual reference images & flow specs
│   └── screens/                               # UI design mocks & montage exports
├── docs/
│   ├── handoff.md                             # current status & review prompts
│   ├── DUBAI-IO_Product_Enhancement_Review.md # comprehensive strategic review
│   ├── gemini-review.md                       # architectural review & next steps
│   ├── references/                            # redesign.md, visuals-libraries.md
│   └── services/                              # cases.md, intake.md
└── output/                                    # test logs, screenshots
```

Rules: never add top-level `*.md` beyond the four canon files. Current code lives in `apps/web/` and `apps/api/`.

## Non-negotiable rules

1. **Truth in status.** Never show `Confirmed`, `Booked`, `Paid`, `Filed`, `Verified` or `Delivered` without an authoritative event: a merchant action in the inbox or a verified adapter response. LLM text never changes status. Use `UNKNOWN_STATUS` before you would invent a success.
2. **Every number has provenance.** Prices, balances, ratings, dates and counts carry `provenance` (`official | provider_confirmed | merchant_submitted | user_supplied | inferred | estimate | demo_fixture`) and `as_of`. Fixture data renders a visible `Demo data` pill.
3. **No invented positions or facts.** The arrival guide never claims an indoor position, belt, gate or queue time the user didn't confirm. Map pins mark only user-confirmed places. Prices and times are labelled estimates.
4. **No government execution.** Salik, DEWA, RTA, Tasjeel and fines are display-only or `Open official portal` links. No top-ups, no bookings, no wait times.
5. **No official branding.** Do not use the DubaiNow layout, government emblems or ministry logos. The rejected DubaiNow-clone montage was deleted (19 Oct); never recreate it.
6. **Approval before side effects.** Sharing data with a merchant and sending a fixed-price order each need an explicit user tap on an approval card that lists exactly which fields get shared. Single approval only — there is no second quote approval because quotes do not exist.
7. **Only registered actions execute.** A card action's `id` must match a capability ID in the registry. The agent fills in *data*. It never writes executable payloads, HTML, SQL or URLs to call.
8. **Proactive = deterministic.** Reminders and triggers come from the scheduler/outbox, not from LLM polling. Every one is deduplicated (`dedupe_key`), consented, respects quiet hours, and is stored as a normal chat message. A trigger the user did not cause is labelled `Demo trigger` on stage. The PWA does **not** do background geofencing.
9. **Memory is user-given or visibly inferred.** Facts the user states are `user_supplied` and shown as "You told me". The temporal profiler may store inferences only as **hypotheses** (`provenance: inferred`, confidence, evidence, valid time). Each one is listed under "I noticed" with Confirm / Edit / Not true / Forget. An unconfirmed hypothesis may re-rank options only, with a visible "Because…" chip. It never pre-fills a field, appears on an approval card, triggers a proactive message or sets a status. Nothing about the user is stored where they can't see it. Health, religion, ethnicity, nationality-as-trait, gender, sexuality and politics are never inferred. See `ARCHITECTURE.md §12`.
10. **Widget sandbox:** provider HTML runs only from the separate widget origin, inside `<iframe sandbox="allow-scripts">`, with `connect-src 'none'`. It reaches the host only through the allowlisted `postMessage` bridge. See `ARCHITECTURE.md §6`.

## Shared service execution

Founder correction: all services must use the agentic loop in `PLAN.md` §7.8. A guidance page, copy/paste report or fictional provider preview is not completion. Prepare from confirmed facts, get approval for the exact side effect, execute through a registered supported adapter, and show provider evidence. If the integration is unavailable, state that blocker. The local executor is implemented; live provider adapters are not connected; existing execution and widget-scope rules still apply.

## Service intake

**New ideas and services.** When the user adds an idea, a service or a reference image, follow [`docs/services/intake.md`](docs/services/intake.md).
- File it under `docs/services/<shops|service>/<category>/`.
- The default outcome is a category-registry row: filed cases are ~1% of the app, and the generic engine covers the rest. Add or extend a case in `docs/services/cases.md` (status `idea`) only when the idea needs a new pattern, rule or data source, or is a demo moment.
- Never write a case into `PLAN.md`.
- If the idea is unclear (category, the user's ask, what is sold or done, who confirms), ask before filing.
- If it touches a NEVER item, stop and say so.

## Stack (current slice and planned scaffold)

- Current frontend: `apps/web/`, plain HTML/CSS + ES modules; cyan theme with Wi-Fi arrival flow.
- Current `apps/api`: Python **3.13** (local venv: 3.13.16), FastAPI, Pydantic v2, LangGraph and the OpenAI SDK. Serves `apps/web` directly at `/`.
- Planned `apps/widgets`: static widget bundles served from a **different origin**. The lab currently uses sandboxed `srcdoc`; this is not the completed widget-host gate.
- Planned `packages/contracts`: Pydantic models are the source of truth, exported to JSON Schema and generated TS. Current Luna schema lives in `apps/api/app/luna/schema.py`; never hand-edit generated TS once codegen exists.
- PostgreSQL 16 + pgvector (Docker, `apps/api/docker-compose.yml`) via `DATABASE_URL`; SQLite fallback for tests/offline (`app/db.py`). Profile in `user_profile` + `profile_facts` (JSONB); Luna checkpoints in Postgres. No Redis, no PostGIS, no microservices.
- Current LLM: OpenAI through `apps/api/app/config.py` (`LUNA_MODEL`, `LUNA_EFFORT`, `LUNA_TIMEOUT_S`). `LLM_PROVIDER` exists in config but does not implement provider switching. Defaults are `gpt-6-luna` / `high`; alternate model/effort can be configured. Keys stay server-side. Never hard-code model IDs outside config.

## Commands

From the repository root:

```powershell
node apps/web/tests/profile.test.mjs
node apps/web/tests/recovery.test.mjs
node apps/web/tests/luna-client.test.mjs
cd apps/api
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 (cyan app); health is `/api/health`. Hash flags jump to a flow: `#wifi` (arrival), `#intro` (onboarding), `#services`, `#guide`, `#profile`. In another terminal, from `apps/api`:

```powershell
.\.venv\Scripts\python -m pytest -q tests
```

`tests/` only — a bare `pytest` walks `data/` and fails with a `PermissionError` on Windows. The 11 skipped tests are the live Luna golden cases; run `$env:RUN_LIVE=1` before a rehearsal.

- Planned React app, once scaffolded: from `apps/web`, `npm install`, then `npm run dev -- --host`. HTTPS is needed for phone microphone/compass permissions.
- Migrate / seed / contracts commands are not implemented yet.
- `pytest` requires `python-dotenv`; if `.env` is missing, keys stay unset and `/api/luna/turn` returns 503.


## Working conventions

- Repo: `github.com/haitham72/dubai-io` (private). Current working branch: `redesign`; `main` holds the paper trail.
- Current Luna contract changes start in `apps/api/app/luna/schema.py`. Once scaffolded, shared contracts change in `packages/contracts`, then generated types, then consumers.
- Every workflow ships with fixtures, a happy-path test and a failure-path test (provider timeout, merchant decline, empty retrieval, duplicate submit).
- Palette: cyan with the approved purple fringe. Tokens/styles live in `apps/web/stage.css`, `stage-v3.css` and `data.js`. The chromatic variant has been removed. Do not invent new palettes.
- Keep the docs short. Tick `PLAN.md` checkboxes, and don't create new planning docs.
