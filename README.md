# Dubai-io

A chat-first AI companion for Dubai visitors and residents, built for the Create AI Agents Championship (Best Personal AI Agent).

```
apps/web/   frontend (HTML/CSS/ES modules), served by the API
apps/api/   FastAPI + LangGraph (Luna), action engine, merchant inbox, outbox, profile; Postgres via Docker
design/     reference screens
docs/       handoff, review guide, references, service cases, archive
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
.\.venv\Scripts\python -m pytest -q tests          # 75 passed, 11 live cases skipped ($env:RUN_LIVE=1 to run)
node ../web/tests/profile.test.mjs; node ../web/tests/recovery.test.mjs; node ../web/tests/luna-client.test.mjs
```

## Docs

[CLAUDE.md](CLAUDE.md) (agent rules) → [PLAN.md](PLAN.md) (scope, demo arc, remaining) → [ARCHITECTURE.md](ARCHITECTURE.md) → [docs/handoff.md](docs/handoff.md) (run + state) · [Review guide](docs/user-app-review-guide.md) · [API catalog](docs/references/api-catalog.md) · [Cases](docs/services/cases.md) · [Archive](docs/archive/)
