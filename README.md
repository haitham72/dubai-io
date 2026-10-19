# Dubai-io

A chat-first AI companion for Dubai visitors and residents, built for the Create AI Agents Championship.

**Current stage:** Phase 0 complete; cyan Home v2 HTML lab + early FastAPI/LangGraph API slice on `redesign`. Luna wiring, shared request preparation, local persistence and the Google OAuth connector are implemented locally. React, separate widget hosting, Postgres and the persistent profiler remain planned.

## Run the current cyan lab

See [`demo/run.md`](demo/run.md) for Python 3.13 setup and troubleshooting. Once the API environment is installed, from the repository root:

```powershell
cd apps/api
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000, or `http://<pc-ip>:8000` on a phone on the same Wi-Fi. The API serves `/lab/home-v2-cyan.html`; `/api/health` reports the configured model and key-presence flags.

The lab has coverflow onboarding, a visible fixture profile, an airport guide, competing service mini-apps and map fixtures. Chat calls Luna on the API origin, with a labelled offline/timeout router fallback. Saved requests use the local action engine and SQLite; plain-text chat history and reports survive browser refresh. Google OAuth code exchange, encrypted grants, refresh and disconnect are prepared but unconfigured. Live Places/map integration remains pending. Merchants, orders and map places shown in the lab are simulated.

Current priorities: configure OAuth, connect a supported live provider adapter, review the separately owned bridge branch, finish remaining reference parity, then the accepted React/Postgres port and persistent profiler. The cyan palette is selected; C1’s reflection is the reference for all stage cards at 70% intensity. Phone review and Artifact republishing are pending.

## Legacy v1 demo

```powershell
cd demo
python -m http.server 8765
```

Open http://localhost:8765. V1 has the scripted visitor → airport → laundry deadline → taxi-memory story and a backstage merchant inbox. It also contains historical community/ticket/other fixtures; these do not expand the current contest scope in `PLAN.md` §2.

## Docs

Agents read `CLAUDE.md` → `PLAN.md` → `ARCHITECTURE.md` → handoff.

| File | Role |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Agent rules and current repository map |
| [PLAN.md](PLAN.md) | Single plan: scope, priorities, phases and gates |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Target architecture; current slice distinguished from planned gates |
| [Handoff](demo/_ref/handoff.md) | Current implementation status, remaining work and review prompts |
| [Run guide](demo/run.md) | Local setup, API and test commands |
| [Cases](demo/_ref/services/cases.md) / [Intake](demo/_ref/services/intake.md) | Case review loop and service intake |
| [Screen references](demo/_ref/redesign.md) / [Effects](demo/_ref/visuals-libraries.md) | Visual references; current plan overrides historical prompts |
| `main` branch | Paper trail: `docs/`, `archive/` |
