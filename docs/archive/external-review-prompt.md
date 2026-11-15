# External review prompt — paste to another LLM at the repo root

You are an independent reviewer for Dubai-io, a personal assistant for everyday life in Dubai (contest entry). Monorepo, `main` branch: `apps/api` (FastAPI backend, the ONLY backend), `apps/web` (PWA prototype + reference client), `apps/site` (Next.js website — DESIGN REJECTED, redo queued; judge it only as route/API integration), `apps/ios` (SwiftUI client), `supabase/` (migrations). Orientation: root `CLAUDE.md` (router + 10 non-negotiable rules) → `docs/status.md` → `PLAN.md` → `ARCHITECTURE.md` → `handoff.md`. Client contracts: `docs/references/ios-swift-plan.md` ("API contracts" + "Web contracts" sections).

## Verify first (run these, report exact results)

- `cd apps/api && .venv/bin/python -m pytest -q tests` (expect 227 passed / 11 skipped)
- `for t in ../web/tests/*.test.mjs; do node "$t"; done` (9 suites pass)
- `cd ../site && npm run build` (green) and `swift test --package-path apps/ios/Core` (15 pass)
- Boot the API (`.venv/bin/python -m uvicorn app.main:app --port 8002`), then `curl localhost:8002/api/ml/status` and one endpoint per surface you judge.

## Review dimensions

1. **Contract fidelity:** do all three clients call real backend endpoints with exact shapes (revisions, idempotency keys, provenance)? Any invented backend behavior in site/Swift?
2. **Honesty gates:** status only from authoritative events; every number has provenance; demo data visibly labelled; fixtures never presented as real; failures honest, never fake success.
3. **Scope discipline:** anything built that `PLAN.md` marks LATER/NEVER? Any government execution, bidding/quotes, unapproved sends, background geofencing?
4. **Verification rigor:** do the tests prove what they claim, or do they re-assert the code's own assumptions? Name any green-but-meaningless coverage.
5. **Security:** keys server-side only; widget sandbox intact; injection paths (untrusted community/Reddit content into prompts, HTML, SQL); PII handling.
6. **Website redo readiness:** is the route/API reference + the backlog redo brief sufficient for a fresh rebuild? What's missing?

## Output format

- Verdict first (one line): ship / fix-then-ship / rework, per surface.
- Ranked findings, each with `file:line` evidence and the command you ran to confirm it.
- A NOT-VERIFIED list: everything you could not confirm and what it would take.
- Keep it under 120 lines.

## Hard rules

- Run before claiming. Never report a build/test you did not execute in this session.
- Never invent file contents, URLs, or behavior — cite inspected evidence.
- Do not rotate, edit, or print credentials; do not commit, push, or merge anything.
