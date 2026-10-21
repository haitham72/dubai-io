# Dubai-io Supabase

Dedicated local project `dubai-io`, CLI **2.121.0**, PostgreSQL 17. It does not reuse or reset `dubaiio-db` or other projects. Docker is required. Ports: API 15421, Postgres 15422, Studio 15423, test mail 15424, Edge inspector 15428. Analytics is disabled for this development stack.

From the repository root:

```powershell
npx.cmd --yes supabase@2.121.0 start
npx.cmd --yes supabase@2.121.0 migration up --local
```

Copy the settings in `apps/api/.env.supabase.example` into the ignored API `.env`, keeping existing provider keys. Restart FastAPI. The existing cookie session supports the single tester; Google OAuth, production Auth/owner transfer and public signup are deferred. Supabase Auth/Storage/Edge services are available locally but are not claimed as completed app integrations.

Application data and LangGraph checkpoints use backend-only schema `dubaiio`. It is excluded from the Data API and browser roles have no schema/table grants. RLS is enabled on versioned application tables without client policies. FastAPI still checks the cookie owner on every private endpoint; connecting as Postgres does not implement `auth.uid()` automatically. Do not expose database credentials to clients.

For hosted deployment, create a separate development project, review migrations, link it explicitly and apply migrations with `db push`. Use the dashboard's direct connection or session pooler for this persistent Python service, with TLS. Keep the same `DATABASE_SCHEMA`. [Connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres), [local workflow](https://supabase.com/docs/guides/local-development/cli-workflows).

The old database volume remains untouched. The isolated SQLite review database is separate data. Copying it requires an explicit source, a backup and row-count verification; starting Supabase is not recovery of the original records. Never run `db reset --linked` as a migration step.

## Verified workstation checkpoint

The API on port 8000 now uses this target. 97 backend tests passed on Supabase Postgres and 97 on SQLite (11 live cases skipped each). The SQLite review records were backed up and imported with app.migrate_supabase; the old Postgres volume is untouched and SQLite checkpoints were archived rather than imported. Current ignored .env keeps existing provider keys and selects DATABASE_SCHEMA=dubaiio.

Registry downloads stalled, so this workstation uses CLI-supported version files for already-cached official images. Reproduce with tools/start-supabase.ps1 -UseCachedImages: Postgres 17.11.0.002, GoTrue v2.197.0, PostgREST v16.4, Storage v1.79.28, Realtime v2.140.3, Edge Runtime v1.77.1, Studio 2026.09.28-sha-5e59b60, pg-meta v0.99.0. These are explicit development pins, not renamed images. Normal CLI startup on a new machine can download the configured CLI defaults. Windows reserves 55335-55434 on this host; dedicated ports 15421-15429 avoid it.
