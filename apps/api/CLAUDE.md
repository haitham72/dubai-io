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
- DB: Supabase PostgreSQL 17 + pgvector via `DATABASE_URL`, backend-only `DATABASE_SCHEMA=dubaiio`. SQLite is the test/offline fallback. No Redis/PostGIS/microservices. See `supabase/CLAUDE.md`.
- Only registered action IDs execute; the agent fills data, never code/SQL/URLs.
- Fixtures under `app/fixtures/` are large: validate via loader/counts/tests, never `cat` them into context.
