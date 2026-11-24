# Dubai-io dev stack (E1)

One command starts the real-data stack on the founder's Windows PC: memory engine (Docker), `apps/api`, Expo (website + iPhone dev server) and the desktop app. Rules 1-10 of `CLAUDE.md` apply; nothing here prints or commits a secret.

| Piece | Where | Port |
|---|---|---|
| Memory API + infra (Docker `apps/memory`: postgres 5442, rabbitmq 5682, redis 6390, api) | `http://localhost:8040` | 8040 |
| Memory **workers + one beat on the HOST** (Celery, `-P solo` for `mem.p0`, `-P threads -c 2` for `mem.p1,mem.p3`) | no port | - |
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

Options: `start-all.ps1 -NoDesktop`, `-Rebuild` (rebuild the memory image without Docker's cache; a plain run already does `docker compose up -d --build api`, cached and a no-op when `apps/memory` is unchanged); `stop-all.ps1 -KeepInfra` (leave postgres/rabbitmq/redis up). `health.ps1 -AllowStoppedDesktop` shows the desktop row as SKIP.

What `start-all` does, in order: prints the active LLM runner; starts postgres/rabbitmq/redis + the memory api from `apps/memory/docker-compose.yml` (never `down -v`) and **stops** the Docker `worker-p0`/`worker-p1`/`beat` containers (no `claude` CLI inside, and no double consumers); then starts the memory Celery workers (`p0@w`, `p1@w`) and ONE beat on the host with `TM_WORKER_RUNNER=agent-cli` (or `lmstudio` when :1234 answers; override with env `DUBAI_WORKER_RUNNER`), the host `claude` CLI on PATH (Haiku, medium effort) and `TM_CLASSIFIER_RUNNER=agent-cli` for the Rule-9 layer-2 screen (unless `TM_CLASSIFIER_MODEL` is set for a local classifier). Python for the workers: `apps/memory/.venv` if present, else the sibling `contest-memory\apps\memory\.venv`, else the apps/api venv; `PYTHONPATH` is always this checkout's `apps/memory/src`. PID files in `.pids.json` (`worker_p0`, `worker_p1`, `beat`); logs `logs/worker_p*.err.log`, `logs/beat.err.log`; creates a memory service token **only if `TM_SERVICE_TOKEN` is missing** from `apps/api/.env` (admin flow, appended, never printed, no other line of that file is touched; delete that one line to re-mint after a database reset); starts `apps/api` with process-environment `MEMORY_BRIDGE_BACKEND=http`, `TM_BASE_URL=http://localhost:8040`, `PUBLIC_API_BASE_URL=http://<LAN IP>:8000` (the pairing QR carries this address to the phone); starts Expo on :8081 and prints the website URL, `exp://<LAN IP>:8081` and the Expo QR; starts the desktop app. Logs go to `scripts/dev/logs/` (git-ignored).

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

## Proof that real extraction runs (synthetic owner)

`python scripts\dev\proof_extraction.py` (stack up): creates a synthetic owner, posts one small record through the engine's normal `/v1/owners/{id}/records` path (the one apps/api uses), waits for the host worker to apply the job, prints the job state transitions, the `job_attempts` row (worker kind, model, tokens, cost) and the fact count, then Forgets the record and prints the unerased counts. One real `claude -p` Haiku call (about 2 min, about 0.08 USD).

## Community and Messenger (E5)

`start-all` also starts the Community API (`:8060`) + website (`:3060`) and the Messenger API (`:8070`) + website (`:5173`). Both APIs run with `MEMORY_BRIDGE_BACKEND=http`, `TM_BASE_URL` and `TM_SERVICE_TOKEN` (process environment, never printed) and `DUBAI_SHARED_IDENTITY_DB` = the same identity database apps/api uses, so one Google sign-in is one `user_id` in all three apps (`app_id` = quest | community | messenger on `/api/identity/google/exchange` and `/api/identity/pair/complete`). The Google redirect URIs do not change: sign-in always starts on apps/api (`http://localhost:8000/api/identity/google/start?return_to=http://localhost:3060/signin`). `health.ps1` shows `community-*` / `messenger-*` rows (API, memory backend must be `http`, website). Their Expo shells load the website, so they use the website sign-in or the same QR pairing.

## E9a additions

- **Owner provisioning:** `start-all` passes the memory admin token (`TM_ADMIN_TOKEN`, generated into the git-ignored `apps/memory/.env` when missing, never printed) to apps/api, Community and Messenger by process environment only. Health row `owner-provisioning-ready` posts an empty body to `/v1/owners` with that token (422 = accepted, nothing is created) and checks apps/api was started by `start-all`.
- **Image freshness:** the memory image is always built (cached). `start-all` records a hash of everything the Dockerfile copies plus the running image id in `scripts/dev/.memory-image.json`; health row `memory-image-current` is red if `apps/memory` changed afterwards or another container is running.
- **Website CORS:** apps/api allows only `http://localhost:8081`, `http://127.0.0.1:8081` and the origins in `PUBLIC_WEB_ORIGINS` (`start-all` adds `http://<LAN IP>:8081`). No wildcard.
- **Desktop:** the main window loads the Dubai-io app (`DUBAI_APP_URL`, default `http://localhost:8081`) with no bridge and the same navigation guard as the Community and Messenger shells. Menu `Dubai-io > Settings and Sign in...` (Ctrl+,) opens the Settings window (the built `renderer/dist`, with the allowlisted preload). `start-all` builds the renderer when missing or stale.

## Semantic model first run (E9d)

The memory API embeds with BAAI/bge-m3 (int8 ONNX, ~570 MB). It is stored in the named Docker volume `tm-hf-cache` (`HF_HOME` in the container), so it downloads once and survives rebuilds and recreates (never `down -v`). The very first `start-all` downloads it during the "Loading semantic model" step (minutes); later starts load it from the volume in seconds. Offline, `start-all` prints an amber line and chat uses lexical recall (honest `retrieval.semantic` flag); health row `memory-semantic-model` is red until the model loads.
