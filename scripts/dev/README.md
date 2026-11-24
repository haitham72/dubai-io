# Dubai-io Dev Stack (E1)

One-command local startup for the real-data stack on Windows (`apps/memory`, `apps/api`, Expo Web, iPhone Expo Go, and Desktop).

## Prerequisites

1. **Docker Desktop** running with Linux containers (`pgvector/pg17`, `rabbitmq:3.13-management`, `redis:7-alpine`).
2. **Python virtualenvs** ready:
   - `apps/api/.venv` (`pip install -r apps/api/requirements.txt`)
   - `apps/memory/.venv` (`pip install -e "apps/memory[cloud,mcp]"`) — optional for host scripts
3. **Node.js 20+** and `npm install` run inside `apps/mobile` and `apps/desktop`.
4. **`claude` CLI signed in** (founder subscription: Haiku, medium effort) on `PATH` or at `%USERPROFILE%\.local\bin\claude.exe`.
5. **Optional local Qwen (LM Studio):** start LM Studio server on `http://127.0.0.1:1234` with `qwen/qwen3-4b-2507` loaded; owner-device jobs use LM Studio first when reachable.

## Usage

```powershell
# Start / converge all services (idempotent; safe to rerun)
powershell -ExecutionPolicy Bypass -File scripts\dev\start-all.ps1

# Check green / red status of all containers, APIs, queues, LLM runner, and LAN URLs
powershell -ExecutionPolicy Bypass -File scripts\dev\health.ps1

# Stop host processes + memory containers cleanly (keeps Postgres volume)
powershell -ExecutionPolicy Bypass -File scripts\dev\stop-all.ps1
```

Options:
- `start-all.ps1 -NoDesktop`: skip launching Electron desktop window.
- `start-all.ps1 -Rebuild`: rebuild `apps/memory` Docker images before starting.
- `start-all.ps1 -AddFirewall`: prompt/add Windows Firewall rules for inbound TCP `8000`, `8081`, `8082`.
- `stop-all.ps1 -KeepInfra`: keep `postgres`, `rabbitmq`, `redis` containers running while stopping app services.

## One-Time Windows Firewall Rules (for iPhone Expo Go on LAN)

Allow inbound LAN TCP traffic to `apps/api` (`8000`), Expo Go Metro (`8081`), and Expo Web (`8082`) in an **elevated PowerShell**:

```powershell
netsh advfirewall firewall add rule name="Dubai-io API 8000" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="Dubai-io Expo 8081" dir=in action=allow protocol=TCP localport=8081
netsh advfirewall firewall add rule name="Dubai-io Web 8082" dir=in action=allow protocol=TCP localport=8082
```

## One-Time Google Cloud Console Setup (Founder OAuth)

1. Open Google Cloud Console → **APIs & Services → Library** and enable:
   - **Gmail API**
   - **Google Calendar API**
   - **YouTube Data API v3**
2. Configure **OAuth consent screen**:
   - User Type: **External**, Publishing status: **Testing**.
   - Under **Test users**, add the founder's primary Gmail and tester Gmail.
3. Under **Credentials → OAuth 2.0 Client ID (Web application)**, add these **Authorized redirect URIs**:
   - `http://localhost:8000/api/identity/google/callback` (E2 Website + Desktop sign-in loopback)
   - `http://127.0.0.1:8000/api/identity/google/callback` (loopback alias)
   - `http://localhost:8000/api/auth/google/callback` (connector OAuth callback on `:8000`)
4. Put `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `OAUTH_TOKEN_KEY` in `apps/api/.env` (never commit `.env`; secrets stay on the PC only).
