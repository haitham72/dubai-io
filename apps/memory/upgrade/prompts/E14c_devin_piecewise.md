# E14c: Devin takes over E14, one small piece at a time

Read `E0_real_data_round.md` and `HANDOFF_integrator_2026-11-25b.md` first. Rules: do not touch `apps/web`; no P2P messaging in Community; Community is 18+ only; light mode, no shadows; never print `.env` values; never merge into `main` (the integrator merges).

**How to work:** do ONE piece, open ONE small PR for it, write 5 lines in `reports/E14c.md` (what changed, exact test output), add a `STATUS.md` line, then STOP and wait. Do not start the next piece until told. Each piece branches from latest `main`. Pieces 2 to 7 take code from the unverified snapshot branch `origin/e14/community-replica-recommender` (commit `1275b25`): use `git checkout origin/e14/community-replica-recommender -- <only the files named in the piece>`. Never copy files a piece does not name. Never stage `tsconfig.tsbuildinfo`.

## Piece 1: start the 4 shells from `start-all.ps1` (easiest, unblocks testing)
Branch `e14c-1/start-shells` from `main`. Edit only `scripts/dev/start-all.ps1`, `scripts/dev/stop-all.ps1`, `scripts/dev/health.ps1`, `scripts/dev/README.md`.
- Add optional switch `-Shells`. When set, also start: `apps/community/mobile` Expo on port 8082, `apps/messenger/mobile` Expo on port 8083 (`npx expo start --host lan --port <port>` with `CI=1`), and the Electron apps `apps/community/desktop` and `apps/messenger/desktop` (`npm start`, with `ELECTRON_RUN_AS_NODE` removed from the child environment).
- Record their PIDs the same way the others are recorded, stop them in `stop-all.ps1`, and add health rows (ports 8082, 8083; the Electron processes) that are SKIP when `-Shells` was not used.
- Do not change default behaviour when `-Shells` is absent.
- Test: `powershell -File start-all.ps1 -Shells`, then `health.ps1`, then `stop-all.ps1`; paste the output. Parse check: `[scriptblock]::Create((Get-Content <file> -Raw))` on each edited script.

## Piece 2: Community web works from the iPhone (LAN address)
Branch `e14c-2/lan-api-base`. Edit only `apps/community/src/lib/api.ts` and `apps/community/tests/unit/api.test.ts`.
- If `NEXT_PUBLIC_CM_API` points at `localhost`/`127.0.0.1` and the page is opened from another host (`window.location.hostname` is not localhost), use `http://<window.location.hostname>:8060`. Keep localhost for server rendering and tests.
- Add a unit test for both cases. Run `npm test`, `npx tsc --noEmit`, `npm run build` in `apps/community`. All must pass.

## Piece 3: Community backend social features (already written, only verify)
Branch `e14c-3/backend-social`. Take only: `apps/api/app/community/store.py`, `routes.py`, `memory_routes.py`, `apps/api/tests/test_community_social_parity.py`.
- Run in a clean worktree with `DATABASE_URL` unset: `pytest -q tests/test_community_*.py --ignore=tests/test_community_supabase_live.py`. Expected: all pass (80 incl. 6 new). Fix any failure inside those 4 files only. Open the PR.

## Piece 4: phone sensors (already written, only verify)
Branch `e14c-4/mobile-context`. Take only `apps/community/mobile/App.tsx`, `apps/community/mobile/src/context/`, `apps/community/mobile/tests/context.test.ts`.
- Run `npm test` and `npx tsc --noEmit` in `apps/community/mobile`. Expected 18 tests pass. Open the PR.

## Piece 5: web UI for votes, hashtags, reposts, block/mute
Branch `e14c-5/web-social`. Needs piece 3 merged. Take only: `apps/community/src/lib/api.ts`, `lib/types.ts`, `lib/feed.ts`, `components/RealPostCard.tsx`, `components/feed/FeedScreen.tsx`, `components/SafetyPanel.tsx`, `app/t/[tag]/page.tsx`, `app/create/page.tsx`, `app/layout.tsx`, `app/page.tsx`, `styles/feed.css`, and the unit tests that match them.
- Remove from these files anything that calls the context or usage endpoints (`/context/`, `/events`, `/profile/usage`): those come in piece 7. Run `npm test`, `npx tsc --noEmit`, `npm run build`, and the Playwright test `tests/e2e/test_community_web_e2e.py`. Fix failures. If PR #9 is merged first, resolve its conflicts in `FeedScreen.tsx`/`layout.tsx`/`feed.css`.

## Piece 6: the two-tower engine, made to pass its own tests
Branch `e14c-6/two-tower-backend`. Take only: `apps/api/app/community/context_profile.py`, `recommender.py`, `scripts/train_community_two_tower.py`, `apps/api/tests/test_community_context_profile.py`, `test_community_two_tower.py`.
- Two tests currently fail: `test_rule9_zero_health_facts_from_user_state_and_sensitive_topics` and `test_benchmark_2000_posts_under_150ms_and_trained_weights`. Fix the code, never the assertions. Rules: `user_state` must never be written to `temporal_memory` or any health record; raw latitude/longitude must never be stored; lowered items stay callable when the user explicitly asks and that call raises their weight (`min(1.0, max(0.35, w + 0.25))`).
- Run the two files plus `python scripts/train_community_two_tower.py --synthetic-smoke`. Paste the output.

## Piece 7: connect it
Branch `e14c-7/wire-two-tower`. Needs pieces 3 and 6 merged.
- In `apps/api/app/community/server.py` include `context_profile.router`. In `apps/api/app/community/agents.py`, make `GET /api/community/discovery` call `recommender.rank_discovery(...)` and keep every existing response key (`items, candidates, reason, empty, features_used, source, why_chip`).
- Add the web pieces that were removed in piece 5: `components/UsageProfilePanel.tsx`, the context bar in `FeedScreen.tsx`, the usage panel in `app/profile/page.tsx`, and their tests.
- Run the whole `apps/api` suite and all `apps/community` checks.

If any piece fails twice for the same reason, stop and write the exact error in `reports/E14c.md` instead of changing scope.
