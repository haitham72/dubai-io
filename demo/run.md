# Run Dubai-io

Current frontend: the cyan HTML lab. The API can serve it on your PC and phone, but **chat still uses the lab keyword router**; wiring `/api/luna/turn` into chat is pending. Running the API does not complete that wiring.

## A. Just look (no install)

Open the cyan Artifact: https://claude.ai/artifact/YZgGtUTmXuarcz97FvGH1w

The Artifact cannot reach your PC API. Local edits are not automatically republished. Cyan is selected; the old chromatic link is a retired comparison, not the current entry point.

## B. Serve the lab and API locally (PowerShell)

### First time only

Use Python 3.13. If your terminal shows `(base)`, run `conda deactivate` first. The current local `.venv/pyvenv.cfg` identifies CPython 3.13.16 in `C:\Program Files\Python313`.

```powershell
cd G:\Haitham\VsCode\contest\apps\api
py -3.13 -m venv .venv
$env:REQUESTS_CA_BUNDLE = ""          # clears this PC’s stale bundle path for this terminal
.\.venv\Scripts\python -m pip install -r requirements.txt
```

If the Python launcher cannot find 3.13, replace the venv command with:

```powershell
& "C:\Program Files\Python313\python.exe" -m venv .venv
```

Keys belong in `apps/api/.env` or the existing gitignored `demo/.env`; `config.py` loads them in that order without overriding environment variables. Never commit keys.

```text
OPENAI_API_KEY=...
GOOGLE_PLACES_KEY=...
```

`LUNA_MODEL`, `LUNA_EFFORT` and `LUNA_TIMEOUT_S` configure the backend. Defaults: `gpt-6-luna`, `high`, 20 seconds. To try the configured alternative, set `LUNA_MODEL=gpt-6.1-sol` and `LUNA_EFFORT=medium`. This is a manual configuration choice; an automatic fast pass is not implemented.

### Every time

```powershell
cd G:\Haitham\VsCode\contest\apps\api
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- PC: http://localhost:8000 → cyan lab.
- iPhone (same Wi-Fi): `http://<your PC IP>:8000`; find IPv4 using `ipconfig`. Allow the expected Windows firewall prompt.
- Health: http://localhost:8000/api/health (model/effort and whether keys are set, never the keys themselves).
- API schema: http://localhost:8000/docs. These demo endpoints have no auth; use the local demo environment.
- API paths: `POST /api/luna/turn`, `GET /api/memory/{user_id}`, `DELETE /api/memory/{user_id}/{key}`, `POST /api/places/search`, `POST /api/route`. Luna/Google calls are external and may incur charges.

Stop with `Ctrl+C`. Phone microphone/compass permissions require HTTPS; typed input remains available.

## Restart the demo from the start

Tap **Dubai-io**, use Me → "Replay landing and Wi-Fi sign-in", or add `#wifi`. For card onboarding alone, use Me → "Replay the intro" or `#intro`. Refresh skips first-run onboarding after it has been seen.

## Tests

Offline checks:

```powershell
node G:\Haitham\VsCode\contest\demo\lab\tests\profile.test.mjs
cd G:\Haitham\VsCode\contest\apps\api
Remove-Item Env:RUN_LIVE -ErrorAction SilentlyContinue
.\.venv\Scripts\python -m pytest -q
```

The profile suite has 92 checks. Pytest defines 6 offline checks and 11 live golden cases (skipped by default). Live cases are optional model calls and can write test-user facts to the JSON memory store:

```powershell
$env:RUN_LIVE = "1"
try { .\.venv\Scripts\python -m pytest -q -k golden }
finally { Remove-Item Env:RUN_LIVE -ErrorAction SilentlyContinue }
```

## Old v1 demo

```powershell
cd G:\Haitham\VsCode\contest\demo
python -m http.server 8765
```

Open http://localhost:8765. This is the legacy scripted demo, separate from the current lab.

## Conda / pydantic_core issue

Previous startup error: `cannot import name ArgsKwargs` from `pydantic_core`, with Anaconda paths in the traceback. The current API health endpoint responds, and the local venv is Python 3.13.16; a clean rebuild itself was not rerun during step 00.

If the error recurs, deactivate Conda and check `.venv/pyvenv.cfg` before rebuilding. Preserve the old environment rather than deleting it; the backup name must be unused:

```powershell
conda deactivate
cd G:\Haitham\VsCode\contest\apps\api
if (Test-Path -LiteralPath .venv.previous) { throw "Rename the existing backup before continuing." }
Rename-Item -LiteralPath .venv -NewName .venv.previous
py -3.13 -m venv .venv
$env:REQUESTS_CA_BUNDLE = ""
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Use the quoted executable command above if `py -3.13` is unavailable.

## Phone access / firewall

- The API binds `0.0.0.0:8000`. Find your PC’s IPv4 with `ipconfig`, then open `http://<pc-ip>:8000` on the same trusted Wi-Fi.
- If Windows Firewall blocks access, run this once in an Administrator PowerShell on a private LAN: `New-NetFirewallRule -DisplayName "Dubai-io API 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private`.

## Connected accounts and saved requests

Me → Connected accounts stays unconfigured until GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_REDIRECT_URI are set in apps/api/.env and the API is restarted. The callback must be the exact approved origin plus /api/auth/google/callback. Secrets stay server-side. The connector implements state/PKCE, code exchange, encrypted grants, refresh and disconnect. Optional OAUTH_TOKEN_KEY supplies a managed Fernet key; the local lab otherwise creates ignored data/oauth.key when configured. Never delete that key while keeping encrypted grants.

Me → Saved requests loads the private local action store. SQLite files (data/actions.sqlite3*) and local OAuth key are ignored. Chat/report snapshots stay in this browser. No live provider adapter is connected; saving a draft never sends or files it. Google OAuth does not supply merchant/RTA execution access.

Offline checks from the repository root:

```powershell
node --test demo/lab/tests/luna-client.test.mjs demo/lab/tests/recovery.test.mjs
node demo/lab/tests/profile.test.mjs
.\apps\api\.venv\Scripts\python.exe -m pytest apps/api/tests -q -k "not golden" -p no:cacheprovider
```

Browser checks use offline Luna fixtures; no paid call is needed to review the UI. Actual iPhone/Google consent and private Artifact publication remain pending.
