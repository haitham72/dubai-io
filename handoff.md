# Handoff - 21 Oct 2026

The primary continuity artifact is **PLAN.md**, with nested tasks and acceptance gates in **docs/implementation-plan.md**. The request ledger is docs/request-backlog.md. **Next task: REC-02, finish recommender controls and explainability.** Do not restart Supabase setup or resume native features.

## Running now

- Branch redesign: local API at port 8000 and isolated widget origin 8001 use the dedicated Supabase project dubai-io. Existing anonymous tester cookies own data; Google OAuth is explicitly last.
- Supabase API 15421, Postgres 15422, Studio 15423, test mail 15424, Edge inspector 15428. Windows reserves the earlier 554xx range. All active Dubai-io containers were healthy/running at verification; CLI status returned success.
- Backend-only schema dubaiio is excluded from the Data API. Anonymous/authenticated/service-role SQL access was denied. FastAPI still performs owner checks; this is not production Supabase Auth integration.
- The review SQLite records (sessions/actions/approvals/profile/recommender records) were backed up and imported. API session creation was verified in Supabase. Ignored apps/api/.env now selects that target and keeps existing provider keys. Active local file directory remains output/review-data (including merchant.pin).
- Original dubaiio-db remains unhealthy and its volume untouched. This migration is not recovery of its records. Old review SQLite LangGraph checkpoints are archived, not imported; new model thread context starts on Postgres. Browser-local chat remains on its device.

## Resume the app

1. From repository root: tools/start-supabase.ps1 -UseCachedImages on this Windows workstation. See supabase/README.md for pinned versions, standard CLI startup and hosted setup boundaries.
2. cd apps/api; .venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
3. Open http://<pc-ip>:8000/#demo.wifi for Wi-Fi/gradients; #maps/#services bypass onboarding. Merchant: /merchant.html with the PIN from output/review-data/merchant.pin. Never print or commit that PIN or .env values.
4. Stop only the app's owning PID if restarting; do not kill all Python or restart other projects' containers.

## Implemented checkpoint

- Moderate server recommender first slice: reviewed topics, owner-bound events, dedupe/per-kind repetition cap, session/long-term decay, organic-only projections, stable home-card boosts/reasons and live-map click ingestion. Me -> You, over time exposes Confirm/Not true/Forget/Resume. Edit, richer evidence, wider eligibility/surfaces and measurement remain REC-02/03/04.
- Whole-place chat focus with visible Clear, 30-minute expiry and ephemeral LangGraph runtime context. Recent stored history is bounded to 24 messages; understanding reads the last 12. Research answer text supports follow-ups. Selected fragments and server-validated plan context remain CTX-02.
- Forget removes owner checkpoints as well as canonical facts/evidence so old model history cannot recreate a forgotten detail. Other owners survive. Multi-worker turn/forget coordination remains a release task.
- Pet-specific queries and captured category/subcategory metadata fix the map review findings. Existing single category row, cyan, explicit 2D/3D and single-composer chat remain intact.
- Native handoff was pushed on ios-swift (eba81b7). Build cfb65a4 passed seven Swift contract tests and unsigned Simulator build, run 39585052919. Mac/device UI testing and substantial parity remain parked; see handoff-ios.md.

## Verification

- Backend: **97 passed, 11 live cases skipped on SQLite; 97 passed, 11 skipped on Supabase Postgres**. Two known FastAPI startup deprecation warnings remain.
- Existing JavaScript: profile 92, recovery 8, Luna client 12 passed.
- Five browser acceptance checks passed for pet-query context, place-to-chat focus/single composer, real profiler ingestion, Clear and visible Forget/Resume. Google/Luna responses were controlled test data, not a new live-provider claim. Artifact: output/playwright/live-interests.png.
- Import tests verify backup, identical replay, conflict rejection and unmapped-table refusal. Private schema access checks and real API-to-Supabase session persistence passed.

## Still pending

Follow the detailed plan in order: REC-02/03/04 -> CTX-02/PLAN-01 -> SUG-01/EVT-01 -> ADS-01 -> REV-01/02/03. Draft itineraries, event/occasion feeds and sponsored placements are not implemented. Public proxy quotas and merchant throttling/roles, physical-device review, original-data recovery, hosted deployment and production identity remain visible. Google OAuth is last; no provider outreach/application was submitted.

Backups, status logs and screenshots live under ignored output/. They contain local/private state and must not be committed. Relevant implementation files are named in the detailed plan; compare them before marking any task complete.
