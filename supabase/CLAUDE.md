# Supabase — `supabase`

Local project `dubai-io`, PostgreSQL 17. Heavy lifting: `README.md` (setup, ports, checkpoints, adoption limits).

## Rules

- Migrations are versioned, additive, reviewable in `migrations/`. Never `db reset --linked`.
- App data lives in backend-only schema `dubaiio`, excluded from the Data API; browser roles get no grants.
- RLS on versioned tables does not replace owner checks in FastAPI.
- Old Postgres volumes stay untouched; SQLite review data is separate data.
