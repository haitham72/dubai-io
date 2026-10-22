# Handoff - 22 Oct 2026

**Newest authorization supersedes the bounded scope below:** founder requested sustained full implementation of the assistant experience. Start with DX-C source links/task chat, then real decisions, staged taxi recovery, durable checks, Reading, one scoped connector and routines; preserve the earlier queue. Detailed active acceptance is at the top of `docs/implementation-plan.md`. Baseline `443c248` is pushed/synced. Previous exclusions describe that finished pass, not the new scope. Native stays parked; execution/privacy/approval/no-government/no-purchasing/database-preservation locks continue. No new slice is verified merely by this scope update.

**Current additive completion checkpoint:** founder clarified "finish it", not redesign. Preserve approved UI/navigation and every existing intent/flow. Source/task/chat connections were pushed as `d44bf51`; reviewed chat edits are now implemented too. A suggested change shows server-normalized before/after and needs explicit Apply with current revision/one retry key. Not now applies nothing; stale proposals fail; a lost response retried to one edit event. Task-scoped dates never overwrite global profile memory. Tracking/task edits never approve/file/send or change source state. Full SQLite **154 passed/11 skipped (23 task checks)**. Four phone-size/motion variants passed connected journeys and reviewed edits/keyboard focus/stale reload; screenshots visually inspected. Two synthetic live Luna checks passed task-date proposal and the original taxi lost-item intent. This is limited live coverage; PG/device/other golden cases remain unverified. **Next active slice: genuine service decisions**, then staged recovery/check-backs/Reading/connector/routines and preserved queue. The full app is still in progress.

The primary continuity artifact is PLAN.md, with nested work in docs/implementation-plan.md. **Latest scope: the bounded preserved-Home/swipe-up-Today correction is implemented and preview-verified; founder/device acceptance remains.** Read `docs/references/assistant-review-decisions.md` for the DX-14 override, accepted/amended recommendations, future gates and preserved backlog. Both independent critiques remain unchanged. Permanent no-credentials/no-purchases, publisher-only politics and tap-only reading recommendations were not adopted wholesale; everyday life/work identity and the requested reading/connector roadmap remain.

Work stays on `redesign`; native `ios-swift` stays parked. **Latest founder correction: preserve Wi-Fi/gradient onboarding and the full visual/photo Home carousel; open Today in a sheet from its own swipe/tap handle.** Gate A manual tasks and the bounded DX-A/DX-B correction are source-implemented. Full SQLite suite: 145 passed, 11 live-model skips; 17 task checks. Both 390x844 and 428x926 Home/Today checks pass with normal and reduced motion. PostgreSQL adoption is unverified. No scheduler/always-on promise or task-to-service execution bridge is claimed. Cookie-owned manual tasks do not depend on OAuth. Pilot pain/newsletter interpretation/hosted budget remain open.

**Live review preview:** http://localhost:8010/index.html#home (Maps: #maps; Wi-Fi/gradients: #demo.wifi). API reloads backend edits; refresh for web edits. Separate widget port 8011 and ignored SQLite directory `output/assistant-preview`; this is not the configured Supabase runtime. Preview needed network-enabled execution for provider calls; static map returned 200 and Places 17 results after restart. Do not change `.env` to disguise the Supabase write issue.

Latest local preview restart: identified/stopped only the stalled 8010 reloader/child and preserved its SQLite files; root PID 63212, initial worker 57516, exec session 79938. Health returned 200. Launch now includes `--timeout-graceful-shutdown 2` with `--reload --reload-dir app`; do not infer a proven root cause from the reload stall. Original DB containers/.env were untouched. Re-identify PIDs before stopping anything; workers change on reload.

## Claude review handoff

The second report is delivered at `docs/references/assistant-design-interaction-review.md`; both independent reviews remain untouched. Read `design/CLAUDE.md` before the 12 Duet frames. The current correction implements Today semantics/due ordering/paused/focus/cancel/title-first and restores the visual Home, recommendation reasons and everyday wording. Founder explicitly superseded DX-14's hide-the-deck premise; do not turn Home back into a task list. DX-C reference-only links and TAXI-02 remain queued, **outside this pass**. Compare the working tree and the latest reconciliation; source verification does not mean the whole review is resolved.

Latest founder choices: staged airport/RTA/driver replies first; Gmail later. Taxi receipt/cash -> confirmed route/time -> official handoff -> reply/evidence -> collection/delivery choice is planned, not implemented. Freely licensed content-image replacement is requested, not implemented. TAXI-02/VIS-02 nested requirements are in the reconciliation. No native work or real external contact occurred.

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

## Gate A source checkpoint

`apps/api/app/tasks.py` adds cookie-owned Task/Event storage, idempotent create/commands, DB-level concurrency/revision guards, atomic event appends, list/detail/activity/Today routes and explicit user-reported completion. `apps/web/tasks.js`/`tasks.css` provide Today plus forms/detail/activity/All tasks; the page host refreshes restored pages. No Decision table exists yet because this slice has no approval workflow; add it with a real decision use. A versioned private-schema migration is present but not deployed/verified on Supabase.

No worker, scheduled check-back, task-to-action bridge, Gmail monitoring or new provider status is claimed. Automatic checks explicitly show inactive. Preserve all earlier regression coverage.

## Home + Today correction checkpoint

- Home keeps its existing carousel/photo cards, cyan/purple gradients and visible qualified recommendation reasons. Wi-Fi and gradient onboarding/replay remain; normal Home/chat/Services copy describes everyday life/work. Airport-specific wording remains confined to the scripted airport flow.
- Handle uses owner-scoped saved-task totals, independent of the three-row preview cap; zero counts disappear. Currently Needs you is zero because no Decision workflow exists. Manual tasks never become decisions. Tap, Enter, ArrowUp and upward pointer motion on the handle open Today; bottom edge/tab bar do not. Reduced motion removes sheet/handle animation.
- On your list sorts due dates ascending, undated last, with overdue/within-24h flags and Dubai display time. Paused tasks remain available; empty Needs you and Running lanes stay hidden. Completed results retain user-reported provenance.
- Pause/Resume/Edit/Done return focus to the state chip and update a mounted polite announcement region. Cancel has an inline confirm; Escape keeps the task. Today keeps cached content/scroll/focus during refresh. Title-only capture saves an empty next step; the example remains a placeholder.
- Order/request/recovery components display human status labels and retain raw codes in `data-status`. Unknown order outcomes do not claim an order was sent. No provider/recovery behavior was added.
- Verified browser matrix: 390x844 and 428x926, normal/reduced motion; real isolated SQLite API; true uncapped counts, due lanes, paused visibility, Enter/ArrowUp/tap/handle pointer swipe, edge exclusions, keyboard-only task create/pause/resume/edit/complete/cancel, focus/live-region DOM updates and held refresh. Visible computed box-shadow checks passed. Screenshots `output/playwright/home-today-*-home.png` / `*-tasks.png`; representative 390 Home and 428 reduced-motion Today were visually inspected.
- Wi-Fi -> captive -> install -> gradient intro plus keyboard Next passed at both sizes/motion settings, with no visible computed shadows. The 390 gradient screenshot was visually inspected. Actual order/report renderers passed human-label/data-code fixture checks; Services/chat everyday copy and no-shadow checks passed. Fixtures sent no action/provider request.
- Physical iPhone gestures and actual screen-reader announcements are **unverified**. SQLite results do not verify Supabase/PostgreSQL, multi-worker deployment or hosted availability.
- **Explicitly excluded:** Keep-track bridge, taxi staged replies, Reading, cron/worker and Gmail. Chat's Keep track entry only opens a manual form; it does not link reports/orders or execute anything. Do not begin excluded work automatically after this pass.

## Implemented checkpoint

- Moderate server recommender first slice: reviewed topics, owner-bound events, dedupe/aggregate per-option repetition cap, session/long-term decay, organic-only projections, stable home-card boosts/reasons and live-map click ingestion. Me -> You, over time exposes Confirm/Edit/Not true/Forget/Resume, separate visit/long-term influence and dated evidence. REC-02 is verified complete, including atomic edits, capped upgrades, stale-cache invalidation and corrected timeline labels. Wider eligibility/surfaces and measurements remain REC-03/04.
- Whole-place chat focus with visible Clear, 30-minute expiry and ephemeral LangGraph runtime context. Recent stored history is bounded to 24 messages; understanding reads the last 12. Research answer text supports follow-ups. Selected fragments and server-validated plan context remain CTX-02.
- Forget removes owner checkpoints as well as canonical facts/evidence so old model history cannot recreate a forgotten detail. Other owners survive. Multi-worker turn/forget coordination remains a release task.
- Pet-specific queries and captured category/subcategory metadata fix the map review findings. Existing single category row, cyan, explicit 2D/3D and single-composer chat remain intact.
- Native handoff was pushed on ios-swift (eba81b7). Build cfb65a4 passed seven Swift contract tests and unsigned Simulator build, run 39585052919. Mac/device UI testing and substantial parity remain parked; see handoff-ios.md.

## Verification

- Current checkpoint: **145 backend tests passed on SQLite (17 task checks), 11 live cases skipped**. The task-only final rerun also passed 17 checks. PostgreSQL runs stalled before verification and were stopped. The earlier REC-02 result was 109 passed per database; it does not verify A/B. Two known startup deprecation warnings remain; a task rerun also reported an inaccessible pytest cache directory.
- JavaScript: profile 92, recovery 8, Luna client 12, recommendation-cache 5, browsing-visit 3 and discovery-cache 5 passed.
- Five browser acceptance checks passed for pet-query context, place-to-chat focus/single composer, real profiler ingestion, Clear and visible Forget/Resume. Google/Luna responses were controlled test data, not a new live-provider claim. Artifact: output/playwright/live-interests.png.
- Import tests verify backup, identical replay, conflict rejection and unmapped-table refusal. Private schema access checks and real API-to-Supabase session persistence passed.

## Gate A browser verification

Historical first-slice checks: nine 390x844 scenarios passed on isolated SQLite (empty, CRUD, user-reported completion, reload, stale cancellation/edit, refreshed Back, controlled 503, composer and layout). `output/playwright/core01a-today.png` depicts the superseded full-list Home. Use the current Home + Today matrix above for this correction. The new keyboard checks found and fixed Home's global Enter shortcut activating the carousel behind a focused control. Existing six JS suites passed: 92/8/12/5/3/5 checks. No new live-provider guarantee follows from UI checks.

## Still pending

Next acceptance is the founder's walkthrough of the bounded correction and physical-device/accessibility checks; Supabase adoption remains gated. DX-C/Keep-track bridge, TAXI-02, Reading, B check-back/worker, E connector/Gmail and F routine remain queued and excluded from this pass. Gates B-F describe future sequencing, not active implementation. REC-03C/04, CTX-02/PLAN-01, SUG-01/EVT-01, ADS-01, REV-01/02/03 and DB-02/03 remain preserved. Draft itineraries, event/occasion feeds and sponsored placements are not implemented. Public proxy quotas/merchant throttling/roles, original-data recovery, hosting and production identity remain pending. OAuth is last; no provider outreach was submitted.

Backups, status logs and screenshots live under ignored output/. They contain local/private state and must not be committed. Relevant implementation files are named in the detailed plan; compare them before marking any task complete.

## REC-02 completion checkpoint

Edit requires explicit Save, clears old evidence, pauses the corrected old topic and confirms the replacement. Facts/projections commit together; owner isolation and rollback are tested. The UI exposes dated recent evidence, session/long-term influence and expiry. Aggregate weights reconcile from retained events, with strongest-signal caps per option/visit. Existing local projections were backed up and reconciled to temporal-v2 before restarting the API; no schema change was needed.

Eight browser acceptance checks passed for evidence/scopes, timeline labels, Cancel, failed-save retry and stale reason clearing, edit/reload, Not true/Resume, Forget/reload and outage/recovery. These used seeded profiler observations and deliberate 503 responses, not new live-provider data. Screenshot: output/playwright/rec02-evidence.png.

## REC-03A/B completion checkpoint

`temporal-v3` separates this-visit influence from inferred preferences supported by two visits at least six hours apart. Category taps do not count as distinct options; negative feedback reduces influence. Browser visits rotate after 30 minutes idle / 24 hours maximum. Confirmed preferences and paused learning remain separate.

Cookie-owned `POST /api/discovery/places` fetches one Google batch, applies type/radius/open-now eligibility and ranks its actual places. The UI has Recommended/Closest/Open now/radius/Refresh, stable result snapshots, visible reasons and seven-day item hiding. Profile corrections and visit rotation invalidate saved/in-flight snapshots. Natural-language budgets/dates, future availability, service/product eligibility and measured relevance remain pending.

Seven phone-size browser scenarios passed against isolated SQLite sessions and controlled Places/static-map responses: real detail-click learning, stable order, filters, item hiding, new explicit context, Forget with a held stale response, and provider failure/retry. Artifact: ignored `output/playwright/rec03-discovery.png` (visually inspected). A separate live request returned eight places with types; it is not a live end-to-end recommendation claim. QA used port 8010 and separate ignored data; its server/browser were closed after verification. It must not be presented as the Supabase runtime.
