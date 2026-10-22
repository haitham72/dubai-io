# Dubai-io

A personal assistant for everyday life and work in Dubai, built for the Create AI Agents Championship (Best Personal AI Agent).

**22 Oct working checkpoint:** visual/photo Home and Wi-Fi/gradient onboarding are preserved; Today opens from its own swipe/tap handle. Manual tasks, due/paused semantics, keyboard focus/announcements and everyday/status wording are implemented on `redesign`. Open `http://localhost:8010/index.html#home` and refresh for web changes; widgets use 8011 and separate SQLite data. SQLite: 145 passed/11 skipped, including 17 task checks; both requested phone sizes and motion settings browser-verified. Physical iPhone gestures/screen-reader output and Supabase adoption remain unverified. [PLAN.md](PLAN.md) and [handoff.md](handoff.md) record exact scope. Both independent reviews remain unchanged; native is parked. Keep-track bridge, taxi staged replies, Reading, worker and Gmail are outside this pass.

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
