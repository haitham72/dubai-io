# Status — 23 Oct 2026

Single current-state file. Detail lives in `handoff.md`, `docs/request-backlog.md`, git history.

## Branches (monorepo — all tracks merged into main)

- `main` @ `b3130d4`: backend (`apps/api`) + prototype (`apps/web`) + website (`apps/site`) + iOS (`apps/ios`).
- `dubai-io-web`, `ios-swift`: merged into main; kept as history. New work goes on main.
- `redesign-community`: merged; `redesign`: historical.

## Verified on the baseline

- Backend: 227 passed / 11 live skipped (SQLite). Web suites: all pass.
- Community: chat hub, contacts/call log, feed + stories, nested replies, 100 personas / 15 communities / 15 chat threads, backend-orchestrated Agnes replies with dedupe and honest failures. Fixtures are `demo_fixture`/`ai_demo`, never real people.
- Docs: `docs/references/community-data-storage-plan.md` is a plan, not a deployed backend.
- ML pipeline: Celery/RabbitMQ/Redis (eager default), Faz3 sentiment + embedding models (lazy), hybrid comment search + `/api/ml/status`; 8 tests green. Heavy deps in `requirements-ml.txt` (Docker worker only).
- Reddit section: votes (toggle), feed sort (new/top/hot), comment top-sort, my-posts, mark-read, keypad call logging, prayer-times (Aladhan), prototype UI wired; 9 tests green.

## Next

- Website: FOUNDER REJECTED (absolute trash) — full redo as state-of-the-art SaaS onboarding, LEFT FOR ANOTHER LLM (see backlog). Current `apps/site` stays only as a route/API-integration reference, not shippable design.
- iOS: stands; device/Simulator-UI passes still required.
- Next phase: real APIs + real users + daily-driver dogfooding; API authorization outreach; unified dashboard plan pending scope answer.

## Still pending (not claimed)

- REC-03C/REC-04 (service/product eligibility, measurement, scheduled cleanup); no community-feed ranker.
- PostgreSQL migration application, hosted Auth/Storage, live Agnes connectivity.
- Missing keys: `NEWSDATA_API_KEY`, `TVLY_API_KEY`, `SERPAPI_KEY`, `GOOGLE_MAPS_BROWSER_KEY`.
