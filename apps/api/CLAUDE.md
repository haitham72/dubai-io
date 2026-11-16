# API — `apps/api`

Python 3.13, FastAPI, Pydantic v2, LangGraph, OpenAI SDK. Serves the frozen `apps/web` at `/` (also `/lab`, a static alias unrelated to `app/lab/`) and `apps/dash` at `/dash`; widget origin on `WIDGET_PORT` (8001). Venv: `apps/api/.venv`. Contracts: root `ARCHITECTURE.md`.

## Run / test (from `apps/api`)

```powershell
# Windows (this machine). DATABASE_URL=' ' forces the SQLite fallback.
$env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030
.\.venv\Scripts\python.exe -m pytest -q tests
$env:TEST_DATABASE_URL='<postgres url>'; .\.venv\Scripts\python.exe -m pytest -q tests   # same suite on Postgres
$env:RUN_LIVE='1'; .\.venv\Scripts\python.exe -m pytest -q tests                        # + live Luna golden cases
```
```sh
# Mac/Linux
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
.venv/bin/python -m pytest -q tests
```

Stop the dev server by its PID only.

## Map

- `main`: wiring; Luna turn, session memory, places/maps/route, shopping search, try-on routes
- `luna/{graph,schema,research}`: LangGraph turn · `actions`: capability registry, approvals, idempotency, evidence gate, order state machine · `merchant`: sandbox inbox
- `tasks` / `projects`: task threads, Today lanes, check-backs · workspaces
- `proactive`: outbox, consent, quiet hours, reminders, assist mode, morning brief, Demo triggers
- `memory/{schema,store,api}`: temporal_note-slim `mem_*` tables + `/api/memory/*`
- `profile` / `user_profile`: hypotheses · profile document + bi-temporal facts
- `recommendations` / `discovery`: temporal ranker · owner-bound live places
- `mail_profile`, `oauth`, `auth`: Gmail read-only needs-reply · Google grants · connections
- `reading` (pull-only headlines) · `catalog` (fixed prices) · `widgets` · `google_maps` · `tryon` (Vertex → OpenAI → honest failure) · `prayer` (Aladhan)
- `communities`, `social_generation`: PARKED 9 Nov (code stays, not in the contest build)
- `ml_api`, `ml_models`, `ml_rag`, `ml_tasks`: ML pipeline (below) · `ops`: `/api/ops/*`, `X-Ops-Token` = `OPS_TOKEN` (unset → 404)
- `db` (`?` SQL, Postgres translation) · `config` · `migrate_sqlite` / `migrate_supabase`
- `lab/`: headless Know/Notice/Do pipeline; see `app/lab/CLAUDE.md` (being built 9 Nov)

## Endpoints (from route decorators, 9 Nov)

- **main:** `GET /api/health`, `/api/catalog` · `POST /api/luna/turn` · `GET /api/session/memory`, `PUT|DELETE /api/session/memory/{key}` · `GET /api/memory/{user_id}`, `DELETE /api/memory/{user_id}/{key}` · `POST /api/places/search`, `GET /api/places/photo`, `/api/maps/config`, `/api/staticmap`, `POST /api/route` · `POST /api/shopping/search` · `GET /api/tryon/status`, `POST /api/tryon`
- **actions:** `GET /api/session`, `/api/actions/capabilities`, `/api/actions`, `/api/actions/{id}`, `/api/actions/{id}/stream` (SSE) · `POST /api/actions/prepare`, `/api/actions/{id}/approve|cancel|request-earlier`
- **merchant:** `GET /api/merchant/providers`, `/orders`, `/stream` (SSE) · `POST /api/merchant/login`, `/orders/{id}/{command}`
- **tasks:** `POST|GET /api/tasks` · `GET /api/tasks/{id}`, `/{id}/activity` · `POST /api/tasks/{id}/commands`, `/{id}/prepare-change`, `/from-action`, `/from-report` · `GET /api/today`, `/api/today/lanes/{lane}`
- **projects:** `POST|GET /api/projects` · `GET /api/projects/{id}`, `/for-chat/{thread_id}` · `POST /api/projects/{id}/commands`
- **proactive:** `POST /api/reminders`, `/api/proactive/consent` · `GET|PUT /api/routines/brief`, `/api/assist` · `GET /api/messages`, `/api/messages/stream` (SSE) · `GET|POST /api/demo/triggers`
- **profile / recommender:** `GET /api/profile`, `/api/profile/me`, `/api/profile/interests` · `POST /api/profile/episodes`, `/api/recommendation-events`, `/api/recommendations`, `/api/discovery/places` · `PUT|DELETE /api/profile/overrides/{hypothesis}` · `PUT /api/profile/interests/{topic}`
- **memory** (`/api/memory`): `GET /timeline`, `/search`, `/hypotheses`, `/context` · `PUT /hypotheses/{id}` · `DELETE /items/{id}`. The router is included before main's `/api/memory/{user_id}`; keep that order.
- **connectors:** `GET /api/auth/connections`, `/api/auth/{provider}/start`, `/api/auth/google/callback` · `POST /api/auth/{provider}/disconnect` · `GET /api/mail/status`, `/api/mail/needs-reply`
- **other:** `GET /api/reading`, `/api/reading/thumbnails/{id}`, `/api/prayer-times`, `/api/ops/health`, `/api/ops/ml`, `/api/ml/status`, `/api/community/search`
- **community (parked):** `/api/communities` (+`/{id}/join|leave|stories|posts`), `/api/feed`, `/api/posts/{id}` (+`/comments`, `/hide`), `/api/votes`, `/api/me/posts`, `/api/chats` (+`/{id}/messages|read|archive`), `/api/contacts`, `/api/calls`

**vs `docs/archive/references/ios-swift-plan.md` (23 Oct inventory):** every endpoint it names exists. **Planned** (named there, absent in code): Supabase Auth bearer-token verification in FastAPI; outbox → APNs push. Also planned elsewhere: a Calendar connector and a WhatsApp export importer (`ARCHITECTURE.md` §14).

## Contracts (FIN-08)

Full table: `ARCHITECTURE.md` §12.1. Essentials: approve sends `Idempotency-Key` + `snapshot_hash` + `revision`, and 409 means reload; every task command carries `expected_revision` + `command_key`; Needs you holds only crucial stops (`approve | check | deadline`); the brief is deterministic, never model text; no assist mode sends, shares or pays. Task engine rules (write guard, RUN-01, no transaction across a provider/LLM call): §11.

## Hosting (recommended, not deployed)

- **Supabase** (Postgres + pgvector, Auth, Storage); migrations in `supabase/migrations`; only the API reaches the DB, with the backend role.
- **Keep FastAPI + LangGraph** as a container (Fly.io, Railway, Render or Cloud Run) in the Supabase region. **No Edge Functions rewrite:** they host neither Python nor long SSE well; use them only as small glue (auth hooks, signed, replay-safe, idempotent provider webhooks).
- **Vercel** for the website (`apps/site`), calling the same API; CORS allowlists the Vercel domain.
- DB connection: direct or session pooler for persistent Python/LangGraph, never transaction pooling blindly.
- No paid deployment or budget assumed. Healthy durable writes precede runtime adoption; a hosted worker, health visibility and an agreed budget precede any always-on promise.

(from `docs/archive/references/ios-swift-plan.md` "Architecture and hosting"; `docs/archive/root/handoff.md`; `docs/archive/implementation-plan.md` §0.7, DB-03; `docs/archive/references/assistant-review-decisions.md` #6)

## Rules

- Luna contract changes start in `app/luna/schema.py`.
- Model IDs live only in `app/config.py` (`LUNA_MODEL`, `SOCIAL_MODEL`, …); never hard-code elsewhere. Keys stay server-side, from env.
- DB: Supabase PostgreSQL 17 + pgvector via `DATABASE_URL` (verified: `supabase/config.toml` `major_version = 17`; the `app/db.py` docstring's "16" is stale), backend-only `DATABASE_SCHEMA=dubaiio`. SQLite is the test/offline fallback. No PostGIS/microservices. Redis (Celery results/cache) + RabbitMQ (broker) adopted 23 Oct for the ML pipeline only. See `supabase/CLAUDE.md`.
- Only registered action IDs execute; the agent fills data, never code/SQL/URLs.
- Owner always comes from the server session; callers never set owner, status or provenance; no public `tester` override.
- Fixtures under `app/fixtures/` are large: validate via loader/counts/tests, never `cat` them into context.

## ML pipeline (23 Oct)

- Broker RabbitMQ, results/cache Redis (`docker-compose.infra.yml`: rabbitmq, redis, api, worker). Dev/tests run `CELERY_EAGER=1` (inline, no broker).
- Models (Faz3 reference, overridable in config): sentiment `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`, embeddings `sentence-transformers/all-MiniLM-L6-v2`.
- `harsh` is sentiment-derived, never a moderation verdict; nothing auto-hides. Missing models/deps → analysis null, search keyword-only, status honest.
- Heavy deps live in `requirements-ml.txt` (Docker worker only); dev venv stays light.
