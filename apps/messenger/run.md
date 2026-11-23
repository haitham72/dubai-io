# Run Messenger locally

Every command runs from the **repo root** (`G:\Haitham\VsCode\Messenger-redesign`), in PowerShell or any terminal.
No `cd` into sub-folders. There is no `npm run server` any more: the old Python server was retired.

## Once

```sh
npm install                 # app dependencies
cp .env.example .env        # PowerShell: Copy-Item .env.example .env   — then fill OPENAI_API_KEY (the rest are optional)
```

Windows PowerShell: use `npm.cmd` / `npx.cmd` if execution policy blocks the `.ps1` wrappers.

Needs Node 18+ and Python 3.11+ (only for the agents service).

## Every session — two terminals

| Terminal | Command | What it is |
|---|---|---|
| 1 | `npm run dev` | The app → <http://localhost:5173>. Also serves the `api/*.ts` routes (chat, weather, flights, stocks…). |
| 2 | `npm run agents` | The agents service → `:8787` (voice commands, research, @messenger skills, Diwan events, stickers, GIFs). First run creates `agents/.venv` and installs its packages (a minute). Clean AI Detection needs the GPU env instead — see Optional below. |

The app works without terminal 2: features that need the agents service fall back to demo data.

Open:

- Desktop: <http://localhost:5173>
- iPhone layout on the desktop: <http://localhost:5173/?device>
- Your phone (same Wi-Fi): `npm run dev -- --host`, open the Network URL it prints

## Check it works

```sh
npm run typecheck                                  # app + API, should print nothing
npm run agents:test                                # offline: 169 passed, 1 skipped without Redis (+10 socket-free cleaner tests)
npm run agents:eval                                # offline development set: 113/113
npm run agents:eval -- --set holdout                  # holdout: 32/32
npx vite build                                     # production app build
curl http://localhost:5173/agents/connectors       # each connector: demo or live, and what it waits for
curl http://localhost:8787/agents/ai-cleaner/capabilities  # cleaner modes + engine (needs the GPU env below)
```

## Optional

- **Redis** (memory survives restarts): `docker compose -f agents/docker-compose.yml up -d redis`. The service finds
  it at `localhost:6379` on its own; without it, memory is kept in-process.
- **Live AI in the agents service** costs money and is off by default. Turn it on with `AGENTS_LIVE=1` in `.env`;
  the hard cap is `AGENTS_BUDGET_USD` (default `1.00`).
- **Images/video** stay fake while `MESSENGER_FAKE_IMAGES=1` / `MESSENGER_FAKE_VIDEOS=1` (real generation costs credits).
- **Clean AI Detection (local GPU):** run terminal 2 from the sibling env instead of `agents/.venv` — from `agents/`:
  `G:\Haitham\VsCode\remove-ai-watermarks\venv\Scripts\python.exe -m uvicorn messenger_agents.app:app --port 8787`
  (or pip-install CUDA torch + Pillow + `remove-ai-watermarks==0.45.1` into `agents/.venv`, several GB).
  Needs ~6 GiB free VRAM. The OpenAI provenance check needs only `OPENAI_API_KEY` — no new env keys.

## When something goes wrong

| Symptom | Fix |
|---|---|
| `Missing script: "server"` | Old instructions. Use `npm run dev` (+ `npm run agents`). |
| `npm run agents` fails installing packages with a TLS / CA bundle error | A shell variable `SSL_CERT_FILE` or `REQUESTS_CA_BUNDLE` points at a deleted file. The runner now ignores a missing file; if it still fails, clear them: `Remove-Item Env:SSL_CERT_FILE, Env:REQUESTS_CA_BUNDLE` |
| `Python was not found` | Install Python 3.11+ from python.org (tick "Add to PATH"), or turn off the Microsoft Store alias in *Settings → Apps → App execution aliases*. |
| Port 5173 or 8787 already in use | Another copy is running. Inspect `Get-NetTCPConnection -LocalPort 8787` and verify the owning process; stop only the exact confirmed PID with `Stop-Process -Id <PID>`, then restart that terminal. |
| The app shows old agents data after a code change | Restart terminal 2 (`Ctrl+C`, then `npm run agents`). |
| Cleaner job fails "remove-ai-watermarks CLI missing" | The service runs from an env without the package — use the GPU env above. |
| Cleaner job fails "GPU unavailable" / CUDA OOM | Close GPU-heavy apps (needs ~6 GiB free VRAM). |
| `agents:test` socket errors in a locked-down shell | Pre-existing: some tests need loopback sockets. `tests/test_ai_cleaner.py` is socket-free and runs anywhere. |

Before the long-audio test, restart terminal 2 and hard-refresh the browser. Active streamed speech can last 120 s; reply dictation ends after 4 s quiet, other commands after 1.4 s. Meetings open a prefilled draft and require Save to calendar. No current paid/live verification was started for the latest repairs; local models remain deferred.

More: [README.md](README.md) (deploy, env vars) · [ARCHITECTURE.md](ARCHITECTURE.md) (how the AI works, connectors) ·
[agents/README.md](agents/README.md) (agents service).
