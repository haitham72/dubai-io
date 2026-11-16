# Dubai-io

Dubai-io is a personal AI agent for people who live and work in Dubai.

Contest entry: Create AI Agents Championship (Dubai Chambers), Best Personal AI Agent. Identity, scope and dates: `PLAN.md`.

```
apps/api/          FastAPI + LangGraph backend, tests/
apps/api/app/lab/  Headless Know / Notice / Do pipeline (active, 9 Nov)
apps/site/         THE app: one React codebase (Next.js) → website, desktop, iOS/Android; UI paused 9 Nov
apps/web/          Original mobile app PWA — FROZEN reference (tag mobile-pwa-baseline-2026-10-23)
apps/ios/          Native SwiftUI client — STOPPED 23 Oct (history only)
supabase/          Migrations, local project config
docs/              Status, backlog, specs, services/ (docs/archive/ is history)
design/            Screen references
```

## Run (this Windows machine, PowerShell)

```powershell
cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030
# API + original mobile app: http://localhost:8030/index.html · merchant sandbox: /merchant.html

cd apps/site; npm run dev
# THE app: http://localhost:3000/ — proxies the API at DUBAIIO_API_ORIGIN (default http://127.0.0.1:8030)
```

`DATABASE_URL` set to a single space selects SQLite; a real value uses Supabase Postgres (`supabase/CLAUDE.md`). Keys live in `apps/api/.env`, never committed; key names are in `docs/status.md`.

## Test

```powershell
cd apps/api; .\.venv\Scripts\python.exe -m pytest -q tests   # $env:RUN_LIVE='1' adds the live Luna cases
cd apps/site; npm test                                       # Vitest; npm run e2e = Playwright (builds and serves on :3041)
```

## Docs

Read in order: `CLAUDE.md` (rules, router) → `PLAN.md` (identity, decisions, scope) → `ARCHITECTURE.md` (contracts) → `docs/status.md` (current state) → `apps/api/app/lab/CLAUDE.md` (headless build). Open requests: `docs/request-backlog.md`. History: `docs/archive/` and git.
