# Handoff 2: integrator session ended on quota, 25 Nov 2026 (11:30 Dubai)

Continues `HANDOFF_integrator_2026-11-25.md`. Read that, root `CLAUDE.md`, `docs/submissions/shared/founder-decisions.md` (D16–D22 + D19b) first. Hard rules are unchanged: `apps/web` frozen (`git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web`), no force-push, no deletions without the founder, never stage the 3 founder untracked files, no new top-level `*.md`, never print `.env` values.

## State of `main`: 55878ab (pushed)

Merged this session, all gated and independently verified: E11a, E11b (PR #7), E10, E12 (PR #8). Full 5-lane E6 rerun is in `reports/U7_post_E11.md` (Lane 1 9/10 PASS, S2 fails on cost $0.00514/day and changes 6/8 sup, 1/4 late; Lane 2 all green; Lane 3 89/89 E2E; Lane 4 20/22; Lane 5 3/3). Decisions D19 (Lower, floor 0.01, surface 0.10, Delete-my-data), D19b (lowered memories stay 100% callable on explicit user trigger and the call adds back weight), D20 (canon patches finalized + archived), D21, D22 are recorded. Prompts E13a, E13b, E14a, E14b are in this folder.

## In-flight work (nothing below is merged)

| Item | Where | State |
|---|---|---|
| **E14 Community replica + two-tower + context** (me, 4 sub-agents) | worktree `G:\Haitham\VsCode\contest-e14-community`, branch `e14/community-replica-recommender`, pushed WIP `1275b25` | **UNVERIFIED snapshot.** Sub-agents 2 and 4 died on quota mid-run, so their own gates never ran. See breakdown below. |
| **E13a Lower + Delete-my-data** (Codex) | worktree `G:\Haitham\VsCode\contest-e13a`, branch `e13a/lower-and-delete` | ~55 uncommitted modified files, no commit, not reviewed. Do not touch; Codex owns it. When it lands, verify D19 + D19b. |
| **PR #9 cleanups** (Devin) | branch `chore/e11b-e12-cleanups`, `ab6ca8c` | Open, not reviewed. Touches `core/embed.py`, `stop-all.ps1`, community `layout.tsx`/`FeedScreen.tsx`. **Will conflict with E14** on `FeedScreen.tsx`, `layout.tsx` (E14 also moved `feed.css`). Merge PR #9 first, then rebase E14. Devin says semantic-hybrid tests can't run in its venv (numpy) and the 20k p95 test (graph_subjects 155–182 ms) fails on unmodified main in that venv. Re-run in `contest-memory` venv before trusting. |
| **E13b similar-query agent** | prompt only | Not started. |

### E14 breakdown (what each sub-agent reported or left)
1. **Backend social core** (agent 008ef79e): finished. `store.py`, `routes.py`, `memory_routes.py`, `test_community_social_parity.py`. Reported 65 pre-existing + 6 new community tests passing (71). Endpoints: vote (post/comment), hashtags + `tags/trending`, 5 feed sorts + `tag` filter, repost, block/mute/safety, split memory consent, `memory/lower`, moderation-removed filter.
2. **Two-tower + context** (13ff77a0): **died on quota.** Files exist: `context_profile.py`, `recommender.py`, `scripts/train_community_two_tower.py`, 2 test files. The backend agent saw **2 failing tests**: `test_community_context_profile.py::test_rule9_zero_health_facts_from_user_state_and_sensitive_topics` and `test_community_two_tower.py::test_benchmark_2000_posts_under_150ms_and_trained_weights`. **Not wired:** `context_profile.router` is not included in `app/community/server.py`, and `recommender.rank_discovery` is not called from `agents.py` `GET /api/community/discovery`. The trainer smoke was not confirmed.
3. **Mobile sensors** (e1be35c8): finished. `apps/community/mobile` 18/18 tests, `tsc` clean. Foreground-only, opt-in, no coordinates stored.
4. **Web UI** (ce19606f): **died on quota.** Large diff exists (`api.ts` +619, `RealPostCard.tsx` +753, `FeedScreen.tsx` +583, new `SafetyPanel`, `UsageProfilePanel`, `t/[tag]` page). `npm test`, `tsc`, `next build` and the Playwright e2e were **not confirmed**. Assume nothing works until run.

### E14 next steps (in order)
1. Merge PR #9 into main (after review), then `git rebase main` on the E14 branch; resolve conflicts in `FeedScreen.tsx`, `layout.tsx`, `feed.css`.
2. Wire the two missing seams: include `context_profile.router` in `server.py`; call `recommender.rank_discovery` from `agents.py` discovery while keeping the existing response keys (`items, candidates, reason, empty, features_used, source, why_chip`). Make the two failing tests pass without weakening them (Rule 9: `user_state` must never reach temporal_memory; benchmark < 150 ms at 2,000 posts).
3. Run gates in the E14 worktree: `apps/api` full pytest with `DATABASE_URL` unset and `PYTHONPATH` on the worktree; `apps/community` `npm test`, `npx tsc --noEmit`, `npm run build`; Playwright `tests/e2e/test_community_web_e2e.py`; `apps/community/mobile` and `desktop` tests; `python scripts/train_community_two_tower.py --synthetic-smoke`; `apps/memory` full pytest in the `contest-memory` venv on Postgres :5442; apps/web diff.
4. Independent verifier sub-agent (not the builder) against D3 (no P2P messaging), D11 (18+), D14 (light, no shadows), D19/D19b, D22 (no background geofencing, no health inference). Write `reports/E14.md` and `E14.review.md`, merge `--no-ff`, add STATUS lines, push.
5. Do not stage `apps/community/tsconfig.tsbuildinfo`.

## Founder readiness answer (what remains before testing 3 apps x 3 platforms on localhost + Expo)

Observed on this PC, not assumed:
- **Blocker 1: DB.** `apps/api/.env` `DATABASE_URL` points to port **15422**, which is offline. Either start that Postgres or blank `DATABASE_URL` for SQLite. A clean worktree with no `.env` starts fine (that is how E6 ran).
- **Blocker 2: Google sign-in.** `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `OAUTH_TOKEN_KEY` are **not set** in `apps/api/.env`. Real login needs them plus the 2 redirect URIs and test users (MORNING.md §B step 2). Synthetic sessions work without them.
- **Firewall:** inbound TCP rules exist for 8000, 8060, 8070, 8081, 8082, 8083, 3060, 5173. Nothing to add.
- **Launcher covers 5 of 9 client targets.** `scripts/dev/start-all.ps1` starts the three websites (:8081 Dubai-io Expo web, :3060 Community, :5173 Messenger), the Dubai-io Expo server and the Dubai-io Electron app. **Not started by it:** Community and Messenger Expo Go shells and Community/Messenger Electron shells. Run by hand: `apps/community/mobile` `npm start`, `apps/messenger/mobile` `npm start`, `apps/community/desktop` `npm start`, `apps/messenger/desktop` `npm start`. Adding them to `start-all.ps1` is a small open task.
- **iPhone caveat:** Community web `API_BASE` is `http://localhost:8060`, which points at the phone itself on a LAN. The E14 web agent was fixing this (use `window.location.hostname`) but it is unverified. Messenger similarly uses `VITE_MESSENGER_API_URL` / `http://localhost:8000`. Test iPhone with the LAN IP printed by `start-all.ps1`, and set the shells' Server URL to `http://<LAN-IP>:3060` / `:5173`.
- **Electron gotcha:** an agent shell with `ELECTRON_RUN_AS_NODE=1` makes Electron fail to launch ("Cannot find module 'electron'"). Unset it. A normal PowerShell is fine.
- **Still owed from real use:** Today shows 0 live cards on synthetic data (E4 target >= 5); the real Google, real iPhone QR scan and real-data walkthrough have never been run.
- **Not yet true on main:** E13a (Lower/Delete-my-data) and E14 are not merged, so the current build still shows the old Forget button and the old Community UI. Founder testing can start now on the E12 Community; the Facebook/Reddit parity arrives with E14.

## Open items for the founder
None blocking. D19 through D22 and D19b are answered. Pending only: whether to also add the 4 shell apps to `start-all.ps1`.
