# Dubai-io

Personal assistant for everyday life and work in Dubai. Contest entry (Best Personal AI Agent). Monorepo: one FastAPI backend serves the PWA prototype, the Next.js website, and the native iOS app.

```
apps/api/   Backend: FastAPI + LangGraph, community/ML/Reddit APIs, tests/
apps/web/   PWA prototype + reference client (vanilla HTML/CSS/ES modules)
apps/site/  Next.js website — DESIGN REJECTED, full redo queued for another LLM
apps/ios/   SwiftUI client (needs device/Simulator-UI passes)
supabase/   Migrations, local project config
docs/       Status, backlog, plans, references, services/
```

## Run (this Mac; ports 8000/8010/8020 belong to other apps)

```sh
cd apps/api && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
# Prototype + API:      http://localhost:8002
# Merchant sandbox:     http://localhost:8002/merchant.html

cd apps/site && NEXT_PUBLIC_API_BASE=http://localhost:8002 npm run dev -- --port 3000
# Website:              http://localhost:3000

# iOS: open apps/ios/DubaiIO.xcodeproj in Xcode, pick a Simulator, Run.
# API base in-app: http://<mac-ip>:8002 (localhost on-device means the phone)

cd apps/api && docker compose -f docker-compose.infra.yml up -d redis   # ML cache (6380; 6379 is the Mac's system redis)
```

## Test

```sh
cd apps/api && .venv/bin/python -m pytest -q tests        # 227 passed, 11 live skipped
for t in ../web/tests/*.test.mjs; do node "$t"; done     # 9 web suites
cd ../site && npm run build                               # website build
swift test --package-path apps/ios/Core                   # 15 iOS contract tests
```

## State

Backend verified (227 tests); clients build. Website design was founder-rejected — see `docs/request-backlog.md` (redo brief, left for another LLM). Missing provider keys keep some paths honestly unavailable; device/PostgreSQL/hosted checks remain open.

## Docs

`CLAUDE.md` (router) → `docs/status.md` (current state) → `PLAN.md` (scope) → `ARCHITECTURE.md` → `handoff.md` (run-book) · Backlog: `docs/request-backlog.md` · Client contracts: `docs/references/ios-swift-plan.md` · External review prompt: `docs/references/external-review-prompt.md`
