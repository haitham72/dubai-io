# Dubai-io

Current web preview: Home scrolls from adaptive task cards through complete inline task history into attributed News. Ask has chat history/profile and a left stacked navigation toggle; Services starts new tasks and its Try asking rows are flat. SQLite/browser checkpoint: 165 passed/11 skipped; Projects workspaces, genuine Decisions and scheduled checks remain pending. Exact status and run details: [handoff.md](handoff.md).

A personal assistant for everyday life and work in Dubai, built for the Create AI Agents Championship (Best Personal AI Agent).

**22 Oct completion work:** preserve the approved visual/photo Home, Wi-Fi/gradient onboarding and navigation. Manual Today now connects saved reports/orders -> tasks -> current source -> task chat, with clearable context and reviewed revision-bound chat edits. Suggestions/tracking do not approve/send/file or change provider state. Open `http://localhost:8010/index.html#home` and refresh for web changes; widgets use 8011 with separate SQLite data. SQLite: 154 passed/11 skipped; both phone sizes/motion settings browser-verified, plus two synthetic live model checks. Genuine service decisions and the remaining recovery/check-back/Reading/connector work are next under the finish-the-app authorization; this is not a redesign or a finished-app claim. [PLAN.md](PLAN.md) and [handoff.md](handoff.md) record exact scope/gates. Physical iPhone/screen-reader/PostgreSQL adoption remains unverified; both review reports stay unchanged and native remains parked.

```
apps/web/   frontend (HTML/CSS/ES modules), served by the API
apps/api/   FastAPI + LangGraph (Luna), action engine, merchant inbox, outbox, profile; Postgres via Docker
design/     reference screens
docs/       handoff, review guide, references, service cases
```

## Run

```powershell
cd apps/api
docker compose --env-file .env up -d                                   # Postgres 16 + pgvector (once)
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

| Open | What |
|---|---|
| `http://<pc-ip>:8000/#demo.wifi` | The app from the arrival flow, with the "Scripted demo" label (`#intro`, `#services`, `#guide`, `#profile` also work) |
| `http://<pc-ip>:8000/merchant.html` | Sandbox merchant inbox + operator Demo triggers (PIN in `apps/api/data/merchant.pin` or `MERCHANT_PIN`) |

`apps/api/.env` (not committed): `OPENAI_API_KEY`, `GOOGLE_PLACES_KEY`, `TVLY_API_KEY`, `SERPAPI_KEY`, `FINNHUB_API_KEY`, `PG_PASSWORD`, `DATABASE_URL`, optional `LUNA_EFFORT`, `MERCHANT_PIN`, `WIDGET_PORT` (default 8001).

## Test

```powershell
cd apps/api
.\.venv\Scripts\python -m pytest -q tests          # 79 passed, 11 live cases skipped ($env:RUN_LIVE=1 to run)
node ../web/tests/profile.test.mjs; node ../web/tests/recovery.test.mjs; node ../web/tests/luna-client.test.mjs
```

## Docs

[CLAUDE.md](CLAUDE.md) (agent rules) → [PLAN.md](PLAN.md) (scope, demo arc, remaining) → [ARCHITECTURE.md](ARCHITECTURE.md) → [docs/handoff.md](handoff.md) (run + state) · [Review guide](docs/user-app-review-guide.md) · [API catalog](docs/references/api-catalog.md) · [Cases](docs/services/cases.md)
