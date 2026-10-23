# Status — 23 Oct 2026

Single current-state file. Detail lives in `handoff.md`, `docs/request-backlog.md`, git history.

## Branches (monorepo — all tracks merged into main)

- `main` (23 Oct EOD): backend (`apps/api`) + mobile PWA (`apps/web`) + website (`apps/site`) + iOS (`apps/ios`, STOPPED).
- `dubai-io-web`, `ios-swift`: merged into main; kept as history. New work goes on main.
- `redesign-community`: merged; `redesign`: historical.

## Verified on the baseline

- Backend: 227 passed / 11 live skipped (SQLite). Web suites: all pass.
- Community: chat hub, contacts/call log, feed + stories, nested replies, 100 personas / 15 communities / 15 chat threads, backend-orchestrated Agnes replies with dedupe and honest failures. Fixtures are `demo_fixture`/`ai_demo`, never real people.
- Docs: `docs/references/community-data-storage-plan.md` is a plan, not a deployed backend.
- ML pipeline: Celery/RabbitMQ/Redis (eager default), Faz3 sentiment + embedding models (lazy), hybrid comment search + `/api/ml/status`; 8 tests green. Heavy deps in `requirements-ml.txt` (Docker worker only).
- Reddit section: votes (toggle), feed sort (new/top/hot), comment top-sort, my-posts, mark-read, keypad call logging, prayer-times (Aladhan), prototype UI wired; 9 tests green.

## Next (23 Oct, founder)

- **North star: `docs/plan/unified-app-design.md`** — one React app in `apps/site` (website real; `?desktop` macOS frame; `?device` iPhone frame), Dubai-io-led, Mirsal-redesign as visual craft, Grok Bot / ChatGPT Dots / Claude Duet behaviour, temporal_note-style memory, white + `#357F92` palette, dark mode from white. Airport guide + lost-in-taxi survive. Awaiting final approval after the white/dark design set; then writing-plans → subagent slices.
- **Plan 1 DONE (23 Oct, `eb6568f`):** `apps/site` is now the unified app — `/` website shell (floating sidebar card, task threads, greeting + composer + briefing strip, Assistant|Community switch, haze, Graphite dark), `?desktop` macOS window, `?device` iPhone frame + Dynamic Island, onboarding (orb → chat setup → session facts). Old landing at `/about`. 20 unit + 36 e2e pass. Next: Plan 2 (composer → real tasks), Plan 3 (Community + Chats⇄Calls port). Refine later: background skyline silhouette looks blocky. `apps/web` unchanged (tag `mobile-pwa-baseline-2026-10-23`).
- Swift/iOS STOPPED. `apps/web` stays as feature reference until parity, then retires.
- Done 23 Oct: Luna-first chat replies (agnes fallback) / agnes-first feed (Luna fallback, background-queued); signup facts (household, services); chat archive + demo missed calls; dashboard S1–S2 (`/api/ops/*`, `/dash`); `apps/web` services 3.1 grid, WhatsApp-style Chats ⇄ Calls + Favorites, slide-in panels + Settings. Backend 249 passed / 11 skipped; web 12 suites pass.

## Still pending (not claimed)

- REC-03C/REC-04 (service/product eligibility, measurement, scheduled cleanup); no community-feed ranker.
- PostgreSQL migration application, hosted Auth/Storage, live Agnes connectivity.
- Keys (23 Oct): Tavily, NewsData, SerpAPI, Google Places, OpenAI, NaraRouter, Finnhub, ops token set. Missing: Google OAuth trio + `OAUTH_TOKEN_KEY` (founder connects later), `GOOGLE_MAPS_BROWSER_KEY`, `DATABASE_URL` (dev runs SQLite).
- Plans: `docs/superpowers/plans/2026-10-23-unified-app-foundation.md` (Plan 1, in progress), `docs/superpowers/plans/2026-10-23-temporal-memory.md` (Plan 6).
