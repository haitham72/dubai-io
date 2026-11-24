# Dubai-io

Dubai-io is a personal AI agent for people who live and work in Dubai.

Contest entries: Create AI Agents Championship (Dubai Chambers) — 3 award tracks ($150k grant each):
Three entries live on `main`: **Dubai-io** (Best Personal AI Agent), **Community** (Best Societal AI Agent) and **Messenger** (Best Business AI Agent).

Identity, scope and dates: `PLAN.md`.

```
apps/api/          FastAPI + LangGraph backend, tests/
apps/api/app/lab/  Headless Know / Notice / Do pipeline (active, 9 Nov)
apps/mobile/       Dubai-io: iPhone via Expo Go + website via Expo web
apps/desktop/      Dubai-io: Electron desktop
apps/memory/       temporal_note memory engine
apps/community/    Community entry (mobile/ + desktop/ shells)
apps/messenger/    Messenger entry (mobile/ + desktop/ shells)
apps/api/app/identity, apps/api/app/memory_bridge   shared per-user layer
apps/site/         Paused Next.js client (UI paused 9 Nov)
apps/web/          Original mobile app PWA — FROZEN reference (tag mobile-pwa-baseline-2026-10-23)
apps/ios/          Native SwiftUI client — STOPPED 23 Oct (history only)
scripts/           Local ingestion pipelines (Gmail 50k tokens cap, YouTube 4-feed, local browser history, dev sessions)
supabase/          Migrations, local project config
docs/              Status, backlog, specs, services/ (docs/archive/ is history)
design/            Screen references
```

## Run (this Windows machine, PowerShell)

```powershell
cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030
# API + original mobile app: http://localhost:8030/index.html · merchant sandbox: /merchant.html
```

Current local setup and verification: start with `apps/memory/upgrade/prompts/E0_real_data_round.md` and E1. For Dubai-io web development run `npm run web` from `apps/mobile`. See the app READMEs for individual clients and `docs/status.md` for current runtime state. (`apps/site` is paused.)

`DATABASE_URL` set to a single space selects SQLite; a real value uses Supabase Postgres (`supabase/CLAUDE.md`). Keys live in `apps/api/.env`, never committed; key names are in `docs/status.md`.

## Test

```powershell
cd apps/api; .\.venv\Scripts\python.exe -m pytest -q tests   # $env:RUN_LIVE='1' adds the live Luna cases
cd apps/api; .\.venv\Scripts\python.exe -m app.lab <step> --data <dir>   # headless Know/Notice/Do lab CLI
```

## Docs

Read in order: `CLAUDE.md` (rules, router) → `PLAN.md` (identity, decisions, scope) → `ARCHITECTURE.md` (contracts) → `docs/status.md` (current state) → `apps/memory/upgrade/` (current E0–E4 round); `apps/api/app/lab/CLAUDE.md` (legacy headless lab). Connector framework (not live-enabled): `docs/connectors/README.md`. Open requests: `docs/request-backlog.md`. History: `docs/archive/` and git.
