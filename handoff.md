# Handoff - 22 Oct 2026

The primary continuity artifact is **PLAN.md**, with nested tasks and acceptance gates in **docs/implementation-plan.md**. The request ledger is docs/request-backlog.md. **Latest task: product reframing and mature feature selection**, per the 22 Oct founder instruction that this is an assistant for everyday life/work in Dubai, not a visitor companion. Read `docs/references/personal-assistant-direction.md`: competitor research, proposed core, acceptance gates and open pilot decisions. No new assistant/connector features are implemented by that proposal. Previous unfinished tasks remain preserved; do not automatically resume REC-03C ahead of product selection.

Source checkpoint `6470ad4` was committed/pushed on `redesign`. REC-03A/B are SQLite/browser verified; restore local Supabase write health and complete PostgreSQL verification/reconciliation before runtime adoption. Work stays on `redesign`; do not switch/merge `ios-swift` or start native work. A pilot-audience question was asked; check later founder replies rather than treating the working individual-resident assumption as approval.

## Runtime checkpoint

- The 21 Oct baseline used API 8000/widget 8001 with dedicated Supabase `dubai-io`. No new Supabase runtime deployment is claimed on 22 Oct. Existing anonymous tester cookies own data; Google OAuth remains last.
- Supabase API 15421, Postgres 15422, Studio 15423, test mail 15424, Edge inspector 15428. The 21 Oct healthy-container result is historical: on 22 Oct reads succeeded, but test-schema creation stalled on `WALWrite`/object locks while Docker returned HTTP 500. Only isolated test processes were stopped; no shared Docker restart or volume reset occurred.
- Backend-only schema dubaiio is excluded from the Data API. Anonymous/authenticated/service-role SQL access was denied. FastAPI still performs owner checks; this is not production Supabase Auth integration.
- The review SQLite records (sessions/actions/approvals/profile/recommender records) were backed up and imported. API session creation was verified in Supabase. Ignored apps/api/.env now selects that target and keeps existing provider keys. Active local file directory remains output/review-data (including merchant.pin).
- Original dubaiio-db remains unhealthy and its volume untouched. This migration is not recovery of its records. Old review SQLite LangGraph checkpoints are archived, not imported; new model thread context starts on Postgres. Browser-local chat remains on its device.

## Resume the app

1. From repository root: tools/start-supabase.ps1 -UseCachedImages on this Windows workstation. See supabase/README.md for pinned versions, standard CLI startup and hosted setup boundaries.
2. Confirm database writes work, back up recommendation tables, run `python -m app.recommendations` from apps/api to reconcile old category counts to `temporal-v3`, and rerun the PostgreSQL suite. Then start `.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`. No new schema migration is needed for A/B. Do not replace the configured database with test data to hide a runtime failure.
3. Open http://<pc-ip>:8000/#demo.wifi for Wi-Fi/gradients; #maps/#services bypass onboarding. Merchant: /merchant.html with the PIN from output/review-data/merchant.pin. Never print or commit that PIN or .env values.
4. Stop only the app's owning PID if restarting; do not kill all Python or restart other projects' containers.

## Implemented checkpoint

- Moderate server recommender first slice: reviewed topics, owner-bound events, dedupe/aggregate per-option repetition cap, session/long-term decay, organic-only projections, stable home-card boosts/reasons and live-map click ingestion. Me -> You, over time exposes Confirm/Edit/Not true/Forget/Resume, separate visit/long-term influence and dated evidence. REC-02 is verified complete, including atomic edits, capped upgrades, stale-cache invalidation and corrected timeline labels. Wider eligibility/surfaces and measurements remain REC-03/04.
- Whole-place chat focus with visible Clear, 30-minute expiry and ephemeral LangGraph runtime context. Recent stored history is bounded to 24 messages; understanding reads the last 12. Research answer text supports follow-ups. Selected fragments and server-validated plan context remain CTX-02.
- Forget removes owner checkpoints as well as canonical facts/evidence so old model history cannot recreate a forgotten detail. Other owners survive. Multi-worker turn/forget coordination remains a release task.
- Pet-specific queries and captured category/subcategory metadata fix the map review findings. Existing single category row, cyan, explicit 2D/3D and single-composer chat remain intact.
- Native handoff was pushed on ios-swift (eba81b7). Build cfb65a4 passed seven Swift contract tests and unsigned Simulator build, run 39585052919. Mac/device UI testing and substantial parity remain parked; see handoff-ios.md.

## Verification

- Current checkpoint: **128 backend tests passed on SQLite, 11 live cases skipped**. PostgreSQL runs stalled before verification and were stopped. The earlier REC-02 result was 109 passed per database; it does not verify A/B. Two known startup deprecation warnings remain.
- JavaScript: profile 92, recovery 8, Luna client 12, recommendation-cache 5, browsing-visit 3 and discovery-cache 5 passed.
- Five browser acceptance checks passed for pet-query context, place-to-chat focus/single composer, real profiler ingestion, Clear and visible Forget/Resume. Google/Luna responses were controlled test data, not a new live-provider claim. Artifact: output/playwright/live-interests.png.
- Import tests verify backup, identical replay, conflict rejection and unmapped-table refusal. Private schema access checks and real API-to-Supabase session persistence passed.

## Still pending

Follow the detailed plan in order: A/B PostgreSQL adoption gate + REC-03C -> REC-04 -> CTX-02/PLAN-01 -> SUG-01/EVT-01 -> ADS-01 -> REV-01/02/03. Draft itineraries, event/occasion feeds and sponsored placements are not implemented. Public proxy quotas and merchant throttling/roles, physical-device review, original-data recovery, hosted deployment and production identity remain visible. Google OAuth is last; no provider outreach/application was submitted.

Backups, status logs and screenshots live under ignored output/. They contain local/private state and must not be committed. Relevant implementation files are named in the detailed plan; compare them before marking any task complete.

## REC-02 completion checkpoint

Edit requires explicit Save, clears old evidence, pauses the corrected old topic and confirms the replacement. Facts/projections commit together; owner isolation and rollback are tested. The UI exposes dated recent evidence, session/long-term influence and expiry. Aggregate weights reconcile from retained events, with strongest-signal caps per option/visit. Existing local projections were backed up and reconciled to temporal-v2 before restarting the API; no schema change was needed.

Eight browser acceptance checks passed for evidence/scopes, timeline labels, Cancel, failed-save retry and stale reason clearing, edit/reload, Not true/Resume, Forget/reload and outage/recovery. These used seeded profiler observations and deliberate 503 responses, not new live-provider data. Screenshot: output/playwright/rec02-evidence.png.

## REC-03A/B completion checkpoint

`temporal-v3` separates this-visit influence from inferred preferences supported by two visits at least six hours apart. Category taps do not count as distinct options; negative feedback reduces influence. Browser visits rotate after 30 minutes idle / 24 hours maximum. Confirmed preferences and paused learning remain separate.

Cookie-owned `POST /api/discovery/places` fetches one Google batch, applies type/radius/open-now eligibility and ranks its actual places. The UI has Recommended/Closest/Open now/radius/Refresh, stable result snapshots, visible reasons and seven-day item hiding. Profile corrections and visit rotation invalidate saved/in-flight snapshots. Natural-language budgets/dates, future availability, service/product eligibility and measured relevance remain pending.

Seven phone-size browser scenarios passed against isolated SQLite sessions and controlled Places/static-map responses: real detail-click learning, stable order, filters, item hiding, new explicit context, Forget with a held stale response, and provider failure/retry. Artifact: ignored `output/playwright/rec03-discovery.png` (visually inspected). A separate live request returned eight places with types; it is not a live end-to-end recommendation claim. QA used port 8010 and separate ignored data; its server/browser were closed after verification. It must not be presented as the Supabase runtime.
