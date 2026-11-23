# Local Supabase Runbook (Docker First — D12)

Runs local PostgreSQL 17, GoTrue Auth, Kong API Gateway, Studio, and Mailpit using the repository's **unedited** `supabase/config.toml` and `supabase/migrations/`.

**Hard rules:**
- **NEVER edit or commit anything under `supabase/`.** (`supabase/migrations/` stays frozen.)
- If `npx.cmd --yes supabase@2.121.0` creates an untracked `supabase/.temp/` folder, do **not** `git add` or commit it.
- Keep secrets (`SERVICE_ROLE_KEY`, `ANON_KEY`, `JWT_SECRET`, `DB_URL`) in process env or gitignored `.env` files only — never commit them.

---

## 1. Prerequisites & CLI Note

- **Docker Desktop** running (Linux containers).
- **Node.js / `npx.cmd`** so we run the exact pinned CLI **`supabase@2.121.0`** (`supabase/config.toml:1`).
  - *Note:* An older global Scoop `supabase.exe` (for example `v2.33.9`) rejects `auto_expose_new_tables`, `health_timeout`, and `[local_smtp]` in `supabase/config.toml`. Always use `npx.cmd --yes supabase@2.121.0` (or the helper scripts here).

## 2. Local Ports (`supabase/config.toml`)

| Service | Local URL / Port | Notes |
|---|---|---|
| API Gateway + GoTrue Auth | `http://127.0.0.1:15421` | Auth issuer `http://127.0.0.1:15421/auth/v1`, JWKS `/.well-known/jwks.json` (`ES256`) |
| PostgreSQL 17 | `postgresql://postgres:postgres@127.0.0.1:15422/postgres` | Existing tables live in backend-only schema `dubaiio` |
| Studio | `http://127.0.0.1:15423` | Local DB/Auth inspector |
| Mailpit (local SMTP) | `http://127.0.0.1:15424` | Captures local auth emails |

---

## 3. Start / Status / Stop

From the repo root (`D:\Vscode\dubai-io-shared` or entry worktree):

```powershell
# Start local Supabase + apply the 11 frozen base migrations in supabase/migrations/
.\docs\submissions\shared\local-supabase\start.ps1

# Inspect current URLs and keys (in terminal only — never commit output)
npx.cmd --yes supabase@2.121.0 status -o env

# Stop containers (preserves local DB volume by default; pass -NoBackup to discard)
.\docs\submissions\shared\local-supabase\stop.ps1
```

---

## 4. Applying Each Entry's Own SQL into Its Own Schema (D12)

Because `supabase/migrations/` is frozen until mains reconcile, each entry stores its own DDL/RLS SQL under its own folder and applies it into its own schema via `apply-entry-sql.ps1` (executed inside the running `supabase_db_dubai-io` container via `docker exec ... psql`, so no host `psql` install is required):

| Scope | Source SQL location | Target Postgres Schema | Command |
|---|---|---|---|
| **Shared (`cs_*`)** | Created automatically by `IdentityStore` / `ensure_memory_bridge_schema` (`CREATE TABLE IF NOT EXISTS`); optional extra SQL under `docs/submissions/shared/local-supabase/sql/` | `dubaiio` (or custom via `DATABASE_SCHEMA`) | `.\docs\submissions\shared\local-supabase\apply-entry-sql.ps1 -Entry shared -Schema dubaiio` |
| **Community (`societal`)** | `apps/community/supabase/*.sql` | `community` | `.\docs\submissions\shared\local-supabase\apply-entry-sql.ps1 -Entry community` |
| **Messenger (`business`)** | `apps/messenger/supabase/*.sql` | `messenger` | `.\docs\submissions\shared\local-supabase\apply-entry-sql.ps1 -Entry messenger` |

`apply-entry-sql.ps1`:
1. Validates the schema identifier (`^[a-z][a-z0-9_]{0,62}$`) and refuses any path under `supabase/migrations/`.
2. Runs `CREATE SCHEMA IF NOT EXISTS <schema>;`.
3. Executes sorted `*.sql` files wrapped with `SET search_path TO <schema>, extensions, public;` and `-v ON_ERROR_STOP=1`.

---

## 5. Creating Synthetic Adult Test Users (`enable_signup = false`)

Public sign-up is disabled in `supabase/config.toml:42`. Provision synthetic adult test accounts via GoTrue's Admin API using `SERVICE_ROLE_KEY` from `npx.cmd --yes supabase@2.121.0 status -o json`:

```powershell
$cfg = (npx.cmd --yes supabase@2.121.0 status -o json | Out-String) | ConvertFrom-Json
$headers = @{ apikey = $cfg.SERVICE_ROLE_KEY; Authorization = "Bearer $($cfg.SERVICE_ROLE_KEY)"; "Content-Type" = "application/json" }
Invoke-RestMethod -Method Post -Uri "$($cfg.API_URL)/auth/v1/admin/users" -Headers $headers -Body '{"email":"tester1@dubai.test","password":"SynthPass!ChangeMe","email_confirm":true}'
```

---

## 6. Running B0 Contract Tests Against Local Supabase Postgres 17 + Auth

```powershell
$cfg = (npx.cmd --yes supabase@2.121.0 status -o json 2>$null | Out-String) | ConvertFrom-Json
$env:TEST_DATABASE_URL = $cfg.DB_URL
$env:DATABASE_URL = ' '
$env:SUPABASE_LOCAL_URL = $cfg.API_URL
$env:SUPABASE_ANON_KEY = $cfg.ANON_KEY
$env:SUPABASE_SERVICE_ROLE_KEY = $cfg.SERVICE_ROLE_KEY
$env:SUPABASE_JWT_SECRET = $cfg.JWT_SECRET

Set-Location apps\api
$b0Files = @(Get-ChildItem tests\test_identity_*.py, tests\test_memory_bridge_*.py | ForEach-Object { $_.FullName })
D:\Vscode\dubai-io\apps\api\.venv\Scripts\python.exe -m pytest -q @b0Files
```

Each test creates an isolated temporary Postgres schema `t_cs_<hex>`, runs against real Postgres 17 + `JSONB`/`BYTEA`, and drops the temporary schema on teardown; `test_identity_supabase_live.py` provisions and deletes two GoTrue users and verifies real `ES256` JWKS tokens end-to-end.
