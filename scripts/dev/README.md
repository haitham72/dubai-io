# Dubai-io dev stack (E1)

One command starts the real-data stack on the founder's Windows PC: memory engine (Docker), `apps/api`, Expo (website + iPhone dev server) and the desktop app. Rules 1-10 of `CLAUDE.md` apply; nothing here prints or commits a secret.

| Piece | Where | Port |
|---|---|---|
| Memory API (Docker `apps/memory`: postgres 5442, rabbitmq 5682, redis 6390, api, worker-p0, worker-p1, beat) | `http://localhost:8040` | 8040 |
| `apps/api` (FastAPI, own venv) | `http://localhost:8000` (LAN `http://<LAN IP>:8000`) | 8000 |
| Expo: website (web bundle) **and** the LAN dev server the iPhone uses, one process | `http://localhost:8081` | 8081 |
| Desktop app (Electron, dev start) | window | - |

Ports 8766, 8767, 8768 belong to other tools: this stack never uses them. 8081 is fixed because E2's sign-in `return_to` is `http://localhost:8081/connect`.

## Prerequisites

1. **Docker Desktop** running (Linux containers).
2. **Python venv for `apps/api`** at `apps/api/.venv` (`pip install -r apps/api/requirements.txt`). Setup installs the memory engine into it automatically (`pip install -e apps/memory`, adds `temporal_memory`, `json-repair`, `celery`, `redis`), then runs `pip check`. Do it by hand with `apps\api\.venv\Scripts\python.exe -m pip install -e apps\memory`. Without it the E3 ingest tests (and the in-process memory bridge) fail with 404/502.
3. **Node 20+**. Setup runs `npm ci` (never `npm install`, so lock files are not rewritten) in `apps/mobile` and `apps/desktop`.
4. **`claude` CLI signed in** with the founder's subscription (Haiku, medium effort) on `PATH` or `%USERPROFILE%\.local\bin\claude.exe`. No Gemini API is used.
5. Optional: **LM Studio** server on `http://127.0.0.1:1234` with the Qwen model loaded; when it answers, local Qwen is used first for owner-device jobs.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\start-all.ps1     # idempotent
powershell -ExecutionPolicy Bypass -File scripts\dev\health.ps1        # exit 1 on any red
powershell -ExecutionPolicy Bypass -File scripts\dev\stop-all.ps1      # keeps the database volume
```

Options: `start-all.ps1 -NoDesktop`, `-Rebuild` (rebuild memory images); `stop-all.ps1 -KeepInfra` (leave postgres/rabbitmq/redis up). `health.ps1 -AllowStoppedDesktop` shows the desktop row as SKIP.

What `start-all` does, in order: prints the active LLM runner; starts postgres/rabbitmq/redis then api + workers + beat from `apps/memory/docker-compose.yml` (never `down -v`); creates a memory service token **only if `TM_SERVICE_TOKEN` is missing** from `apps/api/.env` (admin flow, appended, never printed, no other line of that file is touched; delete that one line to re-mint after a database reset); starts `apps/api` with process-environment `MEMORY_BRIDGE_BACKEND=http`, `TM_BASE_URL=http://localhost:8040`, `PUBLIC_API_BASE_URL=http://<LAN IP>:8000` (the pairing QR carries this address to the phone); starts Expo on :8081 and prints the website URL, `exp://<LAN IP>:8081` and the Expo QR; starts the desktop app. Logs go to `scripts/dev/logs/` (git-ignored).

**Docker coordination.** Before touching containers, both `start-all` and `stop-all` look for `contest-memory\apps\memory\upgrade\reports\DOCKER_LOCK` (override with env `DUBAI_DOCKER_LOCK`). While it exists they wait, checking every 2 minutes for up to 60 minutes; `start-all` then exits with code 3 (skipped), `stop-all` stops only the app processes.

## iPhone on the same Wi-Fi

Open Expo Go and scan the QR (or enter `exp://<LAN IP>:8081`). On the Connect screen, sign in on the PC first, press "Pair iPhone" there, and scan that QR on the phone: it contains the API address and the one-time code.

### Windows firewall (documented, never run by these scripts)

If the phone cannot reach the PC, run once in an **elevated** PowerShell:

```powershell
netsh advfirewall firewall add rule name="Dubai-io Dev TCP 8000" dir=in action=allow protocol=TCP localport=8000 profile=private
netsh advfirewall firewall add rule name="Dubai-io Dev TCP 8081" dir=in action=allow protocol=TCP localport=8081 profile=private
```

## One-time Google Cloud Console setup (founder)

1. **APIs & Services -> Library:** enable **Gmail API**, **Google Calendar API**, **YouTube Data API v3**.
2. **OAuth consent screen:** External, publishing status **Testing**. Under **Test users** add the founder's Gmail **and** the tester Gmail.
3. **Credentials -> OAuth client ID (Web application):** add exactly these **Authorized redirect URIs**:
   - `http://localhost:8000/api/identity/google/callback` (sign-in on PC / website / desktop)
   - `http://localhost:8000/api/ingest/google/callback` (Gmail / Calendar / YouTube connect)
4. Put `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` and the token key in `apps/api/.env` (names in `.env.example`). Never commit it; never paste it into chat or logs.

`http://localhost:8081/connect` and `http://127.0.0.1:<port>/callback` are app `return_to` addresses, not Google redirect URIs; do not add them to Google.
