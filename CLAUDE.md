# CLAUDE.md — Dubai-io (contest build)

Instructions for any coding agent in this repo. Read order: this file → `PLAN.md` → `ARCHITECTURE.md` → `handoff.md`.

## Latest navigation correction - read first (22 Oct)

The founder specified permanent adaptive Tasks Home: current source-backed task cards, otherwise 3-5 usage/preference/recommendation starters; normal vertical scrolling through complete task history then News. Services starts new tasks. The Wi-Fi/gradient intro stays full screen without navigation. Today-as-modal and custom handle swipe takeover are superseded. Ask has standard chat history top left, profile top right, and the four tabs collapse **left** into a stacked icon which re-expands them (Apple TV). Flat Try asking rows. This is implemented/SQLite/browser verified at 175 passed/11 skipped; real headline retrieval and source-card behavior were separately checked. Chat history is local to the device. Projects workspaces are implemented and owner/revision-bound, grouping persistent task links, device-local chat references and explicit shared context. Project context never automatically becomes global profile memory; current workspace ownership is checked before model turns. Projects/browser and one synthetic live scope check passed; PostgreSQL/device acceptance remains unverified. Decisions/check-backs/cron/other queue remain pending. Read newest plan/handoff status before acting on historical pass descriptions below. Both independent reviews remain unchanged. Native stays parked.

## What this is

A personal assistant for everyday life and work in Dubai, entered in the Create AI Agents Championship (Best Personal AI Agent). On 22 Oct the founder explicitly superseded visitor-first framing and requested a mature feature proposal informed by Dots, Grok Bot and Duet:

1. **Assistant:** proposed persistent responsibilities, Today/decisions, inspectable context and controlled follow-through. Existing memory/actions/outbox/discovery are foundations; new proposed features are not implemented claims. Airport guidance is an optional existing scenario.
2. **Services (Talabat-normal):** a list sorted closest + ★ + price-from + turnaround; each row opens its **own sandboxed modal HTML mini-app**. Fixed published prices only. **Bidding / quote / negotiation is FORBIDDEN in any form.** A real merchant tap updates the chat.
3. **Platform:** a shop joins from a photo of its price list (deferred past the January submission).

Civic guidance is LATER. **Status:** source checkpoint `6470ad4` has documented verification/runtime limits; product reframing/feature selection is active (`docs/references/personal-assistant-direction.md`). Native `ios-swift` remains parked. Source/build/device validation are separate statuses.

## Docs

| File | Role |
|---|---|
| `CLAUDE.md` | Hard rules for agents |
| `PLAN.md` | The single plan: locks, scope (IN / LATER / NEVER), demo arc, remaining |
| `ARCHITECTURE.md` | Architecture, contracts, state machine |
| `handoff.md` | How to run, current state, open notes; cannot override the canon |
| `docs/request-backlog.md` | Ordered requests, clarifications and outstanding work |
| `docs/implementation-plan.md` | Nested implementation tasks and acceptance gates under PLAN.md |
| `docs/references/personal-assistant-direction.md` | Researched everyday-assistant proposal, pilot decisions and dependencies; not implemented scope |
| `docs/references/assistant-experience-plan.md` | Expanded Today/task/briefing UX, source contracts, delivery slices and gates; external review prompt is beside it |
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

## Latest execution direction (22 Oct)

Work on `redesign`; native stays parked. The latest founder instruction supersedes the visitor persona and pauses automatic REC-03C progression for product reframing/feature selection. Read the personal-assistant direction proposal; keep its proposed features distinct from implemented work and preserve all prior backlog. REC-03A/B remain SQLite/browser verified with a Supabase write-health/PostgreSQL adoption gate. Cookie ownership and the single-tester OAuth-last instruction remain; connector-based pilots need a deliberate dependency reorder. No database reset or native resumption.

**Subsequent 22 Oct authorization:** founder requested building from the reconciled review. Follow `docs/references/assistant-review-decisions.md` and CORE-01A in the implementation plan: persistent manual tasks + Today first; later gates/backlog preserved. Source-only implementation and SQLite preview are distinct from Supabase adoption. Native remains parked.

**Latest founder-selected correction:** both independent reviews are delivered and must remain unchanged. Read `design/CLAUDE.md` before all 12 Duet frames. Preserve full visual/photo Home, recommendation reasons and Wi-Fi/gradient onboarding; Today opens from a dedicated handle, never the system edge/tab bar. DX-14's hide-deck premise is superseded. Manual tasks go On your list by due date, paused stays visible, zero/empty decision/running counts stay hidden; focus/announcements, inline Cancel, retained refresh, title-only capture and human status wording are implemented. SQLite 145 passed/11 skipped (17 task checks); 390x844 and 428x926 normal/reduced-motion browser checks passed. Physical phone gestures, actual screen-reader output and PostgreSQL adoption remain unverified. **Keep-track bridge, taxi staged replies, Reading, cron/worker and Gmail are explicitly outside this pass.** See implementation plan/handoff for exact acceptance and preserved queue. Native stays parked; image/provenance audit remains pending.

**Newest full-build instruction supersedes that pass's exclusions:** founder requested "do everything full throttle" for the assistant experience. DX-C connected sources/tasks/chat is active, followed by actual decisions, staged taxi, durable check-backs, optional Reading, a scoped read-only connector and reviewed routines. Continue dependency-ordered preserved work; verify and document each slice, commit/push/sync. Native remains parked. No new purchases, government execution, unapproved external sends, paid hosting or destructive database reset is authorized. Provider/OAuth/device blocks must stay explicit; avoid declaring the full experience done after a partial slice. Read the newest section in the implementation plan before continuing.

**Clarification/current checkpoint:** "full throttle" means finish the existing app, **not redesign**. Preserve approved surfaces and all existing intent IDs/flows. DX-C source/task/chat connections and reviewed revision-bound chat edits are implemented; current SQLite suite 154 passed/11 skipped, both sizes/motion settings browser-verified and two synthetic live model checks passed. Task suggestions/links never approve or dispatch, and task dates never become unrelated global profile facts. Genuine service Decisions are next; wider completion remains in progress. Source/task bridge checkpoint `d44bf51` is pushed. Keep current exact status in the plan/handoff.
