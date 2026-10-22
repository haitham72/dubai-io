# Status — 23 Oct 2026

Single current-state file. Detail lives in `handoff.md`, `docs/request-backlog.md`, git history.

## Branches

- `main` @ `834a185`: verified baseline (community redesign + AI persona replies merged in).
- `dubai-io-web` @ `834a185`: website track, fresh from main.
- `ios-swift` @ `c9efee2`: native track; main merged in, `apps/ios` preserved.
- `redesign-community` @ `834a185`: merged; no further work planned here.
- `redesign`: historical, not a target.

## Verified on the baseline

- Backend: 210 passed / 11 live skipped (SQLite). Web suites: all pass.
- Community: chat hub, contacts/call log, feed + stories, nested replies, 100 personas / 15 communities / 15 chat threads, backend-orchestrated Agnes replies with dedupe and honest failures. Fixtures are `demo_fixture`/`ai_demo`, never real people.
- Docs: `docs/references/community-data-storage-plan.md` is a plan, not a deployed backend.
- ML pipeline: Celery/RabbitMQ/Redis (eager default), Faz3 sentiment + embedding models (lazy), hybrid comment search + `/api/ml/status`; 8 tests green. Heavy deps in `requirements-ml.txt` (Docker worker only).

## Next

Web (`dubai-io-web`) and iOS (`ios-swift`) tracks from this baseline. One track at a time, tight briefs, review gates; see `docs/references/ios-web-agent-prompt.md` and `docs/references/ios-swift-plan.md`.

## Still pending (not claimed)

- REC-03C/REC-04 (service/product eligibility, measurement, scheduled cleanup); no community-feed ranker.
- PostgreSQL migration application, hosted Auth/Storage, live Agnes connectivity.
- Missing keys: `NEWSDATA_API_KEY`, `TVLY_API_KEY`, `SERPAPI_KEY`, `GOOGLE_MAPS_BROWSER_KEY`.
