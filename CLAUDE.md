# CLAUDE.md — Dubai-io (contest build)

Instructions for any coding agent in this repo. Read order: this file → `PLAN.md` → `ARCHITECTURE.md` → `handoff.md`.

## What this is

A chat-first AI companion for people living in or visiting Dubai, entered in the Create AI Agents Championship (Best Personal AI Agent):

1. **Companion:** greets visitors on arrival, guides them through DXB step by step, remembers what they tell it, sends proactive in-chat messages they opted into.
2. **Services (Talabat-normal):** a list sorted closest + ★ + price-from + turnaround; each row opens its **own sandboxed modal HTML mini-app**. Fixed published prices only. **Bidding / quote / negotiation is FORBIDDEN in any form.** A real merchant tap updates the chat.
3. **Platform:** a shop joins from a photo of its price list (deferred past the January submission).

Civic guidance is LATER. **Status:** web demo is ready for founder walkthrough with documented gaps (`handoff.md`). Native iOS was authorized on 21 Oct and starts on `ios-swift`; source/build/device validation are separate statuses.

## Docs

| File | Role |
|---|---|
| `CLAUDE.md` | Hard rules for agents |
| `PLAN.md` | The single plan: locks, scope (IN / LATER / NEVER), demo arc, remaining |
| `ARCHITECTURE.md` | Architecture, contracts, state machine |
| `handoff.md` | How to run, current state, open notes; cannot override the canon |
| `docs/request-backlog.md` | Ordered requests, clarifications and outstanding work |
| `docs/implementation-plan.md` | Nested implementation tasks and acceptance gates under PLAN.md |
| `docs/user-app-review-guide.md` | Founder review checklist |
| `docs/references/` | `redesign.md` (screen references), `visuals-libraries.md` (supplied prompts, verbatim), `api-catalog.md` |
| `docs/services/` | `cases.md` + `intake.md`. New ideas go here, never into `PLAN.md` |

If a request needs something `PLAN.md` lists as **LATER** or **NEVER**, stop and ask. Don't build a "small version" of it. Never add top-level `*.md` beyond the four canon files; keep docs short and current (done work lives in git).

## Repo layout

```
apps/web/   HTML/CSS/ES modules: app.js, chat.js, orders.js, offers.js, guide.js, recovery.js,
            profile.js + profile-store.js, merchant.html/.js, miniapps/, tests/
apps/api/   FastAPI + LangGraph: app/{main,actions,merchant,proactive,profile,user_profile,catalog,
            db,widgets,google_maps,oauth,auth}.py, app/luna/{graph,schema,research}.py, tests/,
            docker-compose.yml (Postgres 16 + pgvector)
apps/ios/   Native SwiftUI client and checked-in Xcode project (ios-swift branch)
design/     references/ (screen images), screens/
docs/       see above
```

## Non-negotiable rules

1. **Truth in status.** Never show `Confirmed`, `Booked`, `Paid`, `Filed`, `Verified` or `Delivered` without an authoritative event: a merchant action in the inbox or a verified adapter response. LLM text never changes status. Use `UNKNOWN_STATUS` before you would invent a success.
2. **Every number has provenance.** Prices, balances, ratings, dates and counts carry `provenance` (`official | provider_confirmed | merchant_submitted | user_supplied | inferred | estimate | demo_fixture`) and `as_of`. Fixture data renders a visible `Demo data` pill.
3. **No invented positions or facts.** The arrival guide never claims an indoor position, belt, gate or queue time the user didn't confirm. Map pins mark only user-confirmed places. Prices and times are labelled estimates.
4. **No government execution.** Salik, DEWA, RTA, Tasjeel and fines are display-only or `Open official portal` links. No top-ups, no bookings, no wait times.
5. **No official branding.** No DubaiNow layout, government emblems or ministry logos; never recreate the deleted DubaiNow-clone montage.
6. **Approval before side effects.** Sharing data with a merchant and sending a fixed-price order each need an explicit user tap on an approval card that lists exactly which fields get shared. Single approval only — there is no second quote approval because quotes do not exist.
7. **Only registered actions execute.** A card action's `id` must match a capability ID in the registry. The agent fills in *data*. It never writes executable payloads, HTML, SQL or URLs to call.
8. **Proactive = deterministic.** Reminders and triggers come from the scheduler/outbox, not from LLM polling. Every one is deduplicated (`dedupe_key`), consented, respects quiet hours, and is stored as a normal chat message. A trigger the user did not cause is labelled `Demo trigger` on stage. The PWA does **not** do background geofencing.
9. **Memory is user-given or visibly inferred.** Facts the user states are `user_supplied` and shown as "You told me". Inferences are only **hypotheses** (`provenance: inferred`, confidence, evidence, valid time), each listed under "I noticed" with Confirm / Edit / Not true / Forget. An unconfirmed hypothesis may re-rank options only, with a visible "Because…" chip. It never pre-fills a field, appears on an approval card, triggers a proactive message or sets a status. Nothing about the user is stored where they can't see it. Health, religion, ethnicity, nationality-as-trait, gender, sexuality and politics are never inferred. See `ARCHITECTURE.md` §7.
10. **Widget sandbox:** provider HTML runs only from the separate widget origin, inside `<iframe sandbox="allow-scripts">`, with `connect-src 'none'`. It reaches the host only through the allowlisted `postMessage` bridge. See `ARCHITECTURE.md` §5.

**Service execution:** prepare from confirmed facts → approval of the exact side effect → a registered adapter → provider evidence. When no adapter exists, show the blocker and keep the draft; never a fake Send. **UI:** no shadows; plain AI text, tinted user box, white rounded action boxes.

## Service intake

When the user adds an idea, a service or a reference image, follow [`docs/services/intake.md`](docs/services/intake.md): file it under `docs/services/<shops|service>/<category>/`; default outcome is a category-registry row; add a case to `cases.md` (status `idea`) only for a new pattern, rule, data source or demo moment; never write a case into `PLAN.md`; ask if unclear; stop if it touches a NEVER item.

## Stack

- Web: plain HTML/CSS + ES modules, cyan theme (`apps/web/stage.css`, `stage-v3.css`, `data.js`). Don't invent palettes.
- API: Python 3.13, FastAPI, Pydantic v2, LangGraph, OpenAI SDK; serves `apps/web` at `/`; widget origin on `WIDGET_PORT`.
- DB: local Supabase PostgreSQL 17 + pgvector via `DATABASE_URL`, backend-only `DATABASE_SCHEMA=dubaiio` (`supabase/`). Old Postgres 16 compose volume is preserved for recovery. SQLite fallback for tests/offline. No Redis, PostGIS or microservices.
- LLM: `LUNA_MODEL` / `LUNA_EFFORT` / `LUNA_TIMEOUT_S` in `app/config.py`; never hard-code model IDs elsewhere. Keys stay server-side.
- Luna contract changes start in `apps/api/app/luna/schema.py`.

## Commands

```powershell
cd apps/api
docker compose --env-file .env up -d                                   # Postgres (once)
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
.\.venv\Scripts\python -m pytest -q tests                              # tests/ only (data/ is not walkable on Windows)
$env:TEST_DATABASE_URL=$env:DATABASE_URL; .\.venv\Scripts\python -m pytest -q tests   # same suite on Postgres
$env:RUN_LIVE=1; .\.venv\Scripts\python -m pytest -q tests             # + 11 live Luna golden cases
node ../web/tests/profile.test.mjs; node ../web/tests/recovery.test.mjs; node ../web/tests/luna-client.test.mjs
```

## Working conventions

- Keep the founder's requests and execution order in `docs/request-backlog.md`. Finish the active item before moving on. Treat new messages as clarifications or queued requests, not automatic replacement tasks. State and log any logical reordering in the same session. Preserve unfinished work across handoffs. On 21 Oct the founder explicitly lifted the iOS hold: docs/status → commit/push redesign → create ios-swift → start native client.
- Repo `github.com/haitham72/dubai-io` (private); branch `redesign`; `main` holds the old paper trail.
- Every workflow ships with fixtures, a happy-path test and a failure-path test.
- Stop the dev server by its PID only (never kill all `python.exe`).

## Latest execution direction (21 Oct)

Native features are parked for the founder's Mac/iPhone testing. Local Supabase and review-record migration are verified; do not restart that setup. Follow PLAN.md and docs/implementation-plan.md, starting at REC-03 (REC-02 controls/explainability is verified complete). Finish recommender coverage/measurement, then assistant context and draft itineraries, events/occasions, sponsorship and remaining review fixes. Google OAuth is explicitly last for the single tester; retain cookie ownership and cross-user isolation. Never infer a public tester-owner bypass. Keep root handoff short; the detailed plan is the primary continuity artifact.
