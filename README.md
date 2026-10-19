# Dubai-io

A chat-first AI companion for Dubai visitors and residents, built for the Create AI Agents Championship.

## Architecture

The repository is structured as a standard monorepo:

```
dubai-io/
├── apps/
│   ├── web/                    # Frontend UI (Wi-Fi captive sign-in, onboarding, guide, services, chat)
│   └── api/                    # Backend API (FastAPI, LangGraph Luna agent, Places/Routes)
├── design/                     # Design mockups, flow references, UI assets
├── docs/                       # Specifications, architecture reviews, handoff, service cases
├── CLAUDE.md                   # Agent rules and repository layout
├── PLAN.md                     # Contest plan, scope boundaries, and phases
├── ARCHITECTURE.md             # Target architecture and contracts
└── README.md
```

## Running the Application

### 1. Start the API Backend & Web Host

From the repository root:

```powershell
cd apps/api
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` (or `http://<your-ip>:8000` on mobile on the same Wi-Fi).

- The backend serves `apps/web` directly at `/` (and `/index.html`).
- To jump straight to specific stage flows, use hash flags:
  - `http://localhost:8000/#wifi` — Replays the full airport arrival & Wi-Fi captive portal sign-in flow.
  - `http://localhost:8000/#intro` — Replays the card onboarding intro.
  - `http://localhost:8000/#services` — Opens the services catalog directly.
  - `http://localhost:8000/#guide` — Opens the airport guide.

### 2. Testing

```powershell
# Backend tests (Python / pytest)
cd apps/api
.\.venv\Scripts\python -m pytest -q tests

# Frontend tests (Node.js) — 107 checks across 3 files
node apps/web/tests/profile.test.mjs
node apps/web/tests/recovery.test.mjs
node apps/web/tests/luna-client.test.mjs
```

The 11 skipped backend tests are the live Luna golden cases. Run them before a rehearsal:

```powershell
$env:RUN_LIVE=1
.\.venv\Scripts\python -m pytest -q tests
```

## Documentation Map

Agents and contributors should read: `CLAUDE.md` → `PLAN.md` → `ARCHITECTURE.md` → `docs/handoff.md`.

| Document | Purpose |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Agent non-negotiables, engineering rules, repo map |
| [PLAN.md](PLAN.md) | Single plan: scope (IN / LATER / NEVER), demo arc, phases |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Target architecture, state machine, trust boundary |
| [Handoff](docs/handoff.md) | Current implementation status and active review prompts |
| [Product Review](docs/DUBAI-IO_Product_Enhancement_Review.md) | Strategic & technical product evaluation |
| [Gemini Review](docs/gemini-review.md) | Architectural critique, roadmap, and alignment notes (see its correction banner — repo paths reconciled 19 Oct) |
| [Independent Review](docs/space-bunny_review.md) | Third peer review: scope arbitration, live-proof gap analysis, sprint plan |
| [Cases](docs/services/cases.md) / [Intake](docs/services/intake.md) | Service catalog cases and intake rules |
