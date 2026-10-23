# API — `apps/api`

Python 3.13, FastAPI, Pydantic v2, LangGraph, OpenAI SDK. Serves `apps/web` at `/`; widget origin on `WIDGET_PORT`. Venv: `apps/api/.venv`.

## Run / test (from `apps/api`)

```sh
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
.venv/bin/python -m pytest -q tests
TEST_DATABASE_URL=$DATABASE_URL .venv/bin/python -m pytest -q tests   # same suite on Postgres
RUN_LIVE=1 .venv/bin/python -m pytest -q tests                        # + live Luna golden cases
```

Stop the dev server by its PID only.

## Map

`main` wiring · `actions` engine/registry · `communities` + `social_generation` (persona replies) · `recommendations`/`discovery` (temporal ranker) · `tasks`/`projects`/`reading`/`proactive`/`merchant`/`profile`/`user_profile` · `luna/{graph,schema,research}` · `db` store · `config` settings · `auth`/`oauth` · `widgets`/`google_maps` · `migrate_sqlite`/`migrate_supabase`.

## Rules

- Luna contract changes start in `app/luna/schema.py`.
- Model IDs live only in `app/config.py` (`LUNA_MODEL`, `SOCIAL_MODEL`, …); never hard-code elsewhere. Keys stay server-side, from env.
- DB: Supabase PostgreSQL 17 + pgvector via `DATABASE_URL`, backend-only `DATABASE_SCHEMA=dubaiio`. SQLite is the test/offline fallback. No PostGIS/microservices. Redis (Celery results/cache) + RabbitMQ (broker) adopted 23 Oct for the ML pipeline — see ML section. See `supabase/CLAUDE.md`.
- Only registered action IDs execute; the agent fills data, never code/SQL/URLs.
- Fixtures under `app/fixtures/` are large: validate via loader/counts/tests, never `cat` them into context.

## ML pipeline (23 Oct)

- Broker RabbitMQ, results/cache Redis (`docker-compose.infra.yml`: rabbitmq, redis, api, worker). Dev/tests run `CELERY_EAGER=1` (inline, no broker).
- Models (Faz3 reference, overridable in config): sentiment `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`, embeddings `sentence-transformers/all-MiniLM-L6-v2`.
- `harsh` is sentiment-derived, never a moderation verdict; nothing auto-hides. Missing models/deps → analysis null, search keyword-only, status honest.
- Heavy deps live in `requirements-ml.txt` (Docker worker only); dev venv stays light.
