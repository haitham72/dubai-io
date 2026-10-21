# Backend review — 21 Oct 2026

**Current checkpoint, 21 Oct:** local Supabase is implemented and the API at port 8000 uses it. See supabase/README.md and PLAN.md / docs/implementation-plan.md (DB-01/02/03). Hosted deployment/production Auth remain pending; Google OAuth is explicitly last for the single tester. The diagnosis below describes the preserved original Postgres, not the new healthy target.


Recommendation: use **Supabase Postgres + Auth** when moving to hosted accounts, retaining FastAPI/LangGraph and the deterministic action/outbox engine. This is a proposal, not a completed migration. An Astra review at medium effort agreed with this direction.

Founder direction, 21 Oct: prefer Supabase's integrated platform; assess local-first integration before hosted deployment. Local development is viable. Recommender tables and memory integration are planned in [recommender-plan.md](recommender-plan.md); remaining work/order is tracked in [request-backlog.md](../request-backlog.md).

## Local integration path

- Supabase officially supports local Google sign-in. Configure the Google OAuth client and local provider, register `http://127.0.0.1:54321/auth/v1/callback` in Google, and configure the application's own redirect allowlist/site URL separately. The existing Places/Routes keys do not replace OAuth client credentials. [Google provider setup](https://supabase.com/docs/guides/auth/social-login/auth-google).
- Existing server-to-server Google Places/Routes, search and other outbound API calls do not require the database to be hosted. Retain valid provider credentials, network access and applicable key restrictions. Local Edge Functions are also available for development.
- On a physical iPhone, `localhost` refers to the phone. Use reachable endpoints for both the app and Auth; for full phone OAuth/webhook tests, prefer a hosted development project or a configured HTTPS development tunnel. Google permits HTTP localhost redirects as a development exception; arbitrary LAN-IP HTTP callbacks are not equivalent. [Google redirect rules](https://developers.google.com/identity/protocols/oauth2/web-server#uri-validation).
- Incoming provider webhooks need a publicly reachable endpoint/tunnel. Local schema migrations can later be applied to hosted Supabase; users, existing records, provider credentials and secrets require explicit migration/configuration.
- On this Windows machine the CLI stack needs a working container runtime. The unresolved Docker problem is a prerequisite to local Supabase, not a Google OAuth incompatibility. A hosted development project avoids that local dependency. [Local development requirements](https://supabase.com/docs/guides/local-development).

## What failed locally

The existing `dubaiio-db` container recovered successfully at 03:29 UTC. At 07:50 UTC a PostgreSQL child exited with code 2; the parent terminated other processes and issued SIGKILL to children that did not exit. No completed recovery followed. Docker reported the container unhealthy. Database storage was only 4% used, with ample shared-memory space. The logs do not establish the original crash cause or prove data corruption.

A normal container restart was attempted with the existing volume retained, but the restart and a subsequent inspect command stalled. No database volume was removed or reset. A Docker Desktop/runtime restart is the next diagnostic step; it affects other running containers and has not been performed. Do not reset WAL or recreate the volume to get past this symptom.

The earlier preview used separate SQLite review data in output/review-data. Those review records were backed up and imported into the dedicated local Supabase target; port 8000 now uses Supabase. Old SQLite checkpoints were archived, not imported. No original Postgres records are claimed recovered.

## Proposed division

| Responsibility | Proposed owner |
|---|---|
| Postgres + pgvector, database operations | Supabase |
| Visitor/merchant sign-in and token lifecycle | Supabase Auth, with explicit role mapping |
| User-owned data access | Explicit RLS policies plus API ownership checks |
| Luna/LangGraph, approvals, fixed-price orders, merchant evidence | Existing FastAPI backend |
| Reminders/outbox and SSE | Existing persistent Python service |
| Small provider webhooks | Edge Functions only when a real integration requires them |

Local Supabase on Windows still needs a container runtime. Hosted Supabase removes the dependency on this computer's database container, but the Python service still needs hosting. Local schema migrations can be versioned and deployed to a hosted project; schema deployment does not automatically copy existing data, users or secrets. [Local requirements](https://supabase.com/docs/guides/local-development), [migration workflow](https://supabase.com/docs/guides/local-development/database-migrations).

Before migrating any original Postgres records or introducing hosted identity:

- Recover and verify a backup/export of the existing database.
- Map anonymous owners to authenticated users without losing actions, profile facts, checkpoints, approvals, consent, reminders or OAuth grants. Separate merchant and operator roles.
- Establish database permissions deliberately. The current psycopg connections do not automatically acquire a Supabase user's identity. Keep action-engine tables inaccessible to direct browser writes. RLS does not replace approval snapshots, idempotency or provider evidence. [RLS documentation](https://supabase.com/docs/guides/database/postgres/row-level-security).
- Keep account sign-in separate from access to Google Calendar. Google OAuth still requires client credentials, redirect configuration and scopes. [Google sign-in setup](https://supabase.com/docs/guides/auth/social-login/auth-google).
- Keep long-lived orchestration in Python. Hosted Edge Functions have resource and duration limits and do not run the existing Python application unchanged. [Limits](https://supabase.com/docs/guides/functions/limits).

## Verified local implementation

Project dubai-io runs on ports 15421-15429 with PostgreSQL 17. Cached official image versions are reproducible through tools/start-supabase.ps1 -UseCachedImages; registry pulls stalled and Windows reserved the first proposed port range. No Docker-wide restart or old-volume reset was used. Versioned migrations create backend-only schema dubaiio; 97 tests passed on this database and API session persistence was checked directly. Browser database roles cannot read the private schema.

The explicit app.migrate_supabase tool inventories a named SQLite source, backs it up with SQLite's WAL-safe backup API, refuses unmapped tables, checks identical replays/conflicts and imports records without silently skipping a failed table. The ignored API .env was backed up before changing DATABASE_URL/DATABASE_SCHEMA. Local review backups live under output/backups. This is a single-tester development deployment, not production identity or recovery of the old database.
