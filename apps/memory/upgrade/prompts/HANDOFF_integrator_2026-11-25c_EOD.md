# End-of-Day Handoff — 25 Nov 2026 (Dubai)

Continues `HANDOFF_integrator_2026-11-25.md` (removed 26 Nov; see git history) and `HANDOFF_integrator_2026-11-25b.md`.
Hard rules remain unchanged: `apps/web` frozen (`git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web`), no force-push, no worktree/branch deletion without founder approval, never stage the 3 founder untracked files (`design/20-11-2026/Dubai-io Quest Milestones Showcase.jpg`, `docs/Researches/new tools research.md`, `docs/plan/Memory/deepseek_markdown_20261124_fbeb70.md`) or build outputs (`apps/desktop/renderer/dist/`), never print `.env` values.

---

## 1. Completed & Merged on `main` Today
- **E11a** (`e11a/temporal-fixes` `722aa37`) — merged (`apps/memory` Postgres 524p/8s; historical S2 7/8 superseded gate remains open).
- **E11b PR #7** (`e11b/review-fixes` `61f230d`, independently verified) — merged (full-venv Postgres `apps/memory` 530p/8s, `apps/api` 671p/16s, Messenger 10+13, Desktop 32p).
- **E10** (`e10/topic-tree` `f33242c`, independently verified in `reports/E10.review.md`) — merged (D17 unified topic tree + D18 weight floor 0.05; combined Postgres `apps/memory` 540p/8s).
- **E12 PR #8** (`e12/community-wiring` `bee0aa0`, independently verified) — merged (`apps/community` vitest 40p + build 9 routes, mobile 8p, desktop 11p, `apps/api` community 65p, Playwright 2-user E2E 4/4).
- **U7_post_E11** (`reports/U7_post_E11.md` (removed 26 Nov; see git history)) — 5-lane E6 rerun on `74cbb1b` (Lane 1 9/10 PASS; Lane 2 10/10 PASS; Lane 3 89/89 E2E PASS; Lane 4 20/22 PASS; Lane 5 3/3 Electron PASS).
- **D19–D22 + D19b canon** — recorded in `docs/submissions/shared/founder-decisions.md`, canon patches archived to `docs/archive/canon-patches-2026-11-25/`, Community replica/two-tower plan written (`docs/submissions/community/FACEBOOK_REDDIT_RECOMMENDER_PLAN.md`), prompts `E13a`, `E13b`, `E14a`, `E14b`, `E14c` committed.
- **PR #9** (`chore/e11b-e12-cleanups` `ab6ca8c`) — verified (Postgres `test_embed_lazy_backfill` + `test_semantic_hybrid` 8/8 passed; `stop-all.ps1` parses clean; `apps/community` vitest 40p, `tsc --noEmit` clean, `next build` 9 routes) and **merged into `main`**.
- **PR #10** (`e14c-1/start-shells` `f41494f`) — verified (`start-all.ps1 -Shells`, `health.ps1`, `stop-all.ps1` parse clean) and **merged into `main`**.

Open PRs on GitHub: **0**.

---

## 2. Pushed Unverified WIP Branches (Not Merged to `main`)

### A. `origin/e14/community-replica-recommender` (`1275b25` in `G:\Haitham\VsCode\contest-e14-community`)
- **Done:** Backend social parity (`store.py`, `routes.py`, `memory_routes.py`, 71/71 community tests) and Mobile foreground sensors (`apps/community/mobile`, 18/18 tests + `tsc` clean).
- **Remaining:**
  1. Rebase onto `main` (resolving conflicts with PR #9 in `FeedScreen.tsx`, `layout.tsx`, `feed.css`).
  2. Fix LAN API base URL for Community (`window.location.hostname` fallback when not localhost) + same pattern for Messenger if needed.
  3. Wire `context_profile.router` into `apps/api/app/community/server.py` and `recommender.rank_discovery` into `apps/api/app/community/agents.py`.
  4. Fix the 2 failing tests (`test_rule9_zero_health_facts_from_user_state_and_sensitive_topics` and `test_benchmark_2000_posts_under_150ms_and_trained_weights`) and run `scripts/train_community_two_tower.py --synthetic-smoke`.
  5. Run full `apps/community` Web UI gates (`npm test`, `npx tsc --noEmit`, `npm run build`, Playwright `test_community_web_e2e.py`) and independent verifier review (`E14.md` + `E14.review.md`).

### B. `origin/e13a/lower-and-delete` (`b0785c3` in `G:\Haitham\VsCode\contest-e13a`)
- **Done (unverified snapshot committed & pushed):** 57 files (`apps/api`, `apps/memory`, `apps/desktop`, `apps/messenger`, `apps/mobile`, `0008_memory_controls.sql`, `privacy/controls.py`, `docs/PRIVACY_AND_MEMORY_FAQ.md`) implementing Codex's D19 pass.
- **Remaining:**
  1. Add **D19b** (100% callable on explicit user trigger + weight boost `w_new = min(1.0, max(0.35, w_eff + 0.25))`) — Codex branched before D19b was committed.
  2. Rebase/merge latest `main`, run full Postgres `apps/memory` + `apps/api` + mobile/desktop/messenger suites, independent verifier pass, and merge to `main`.

---

## 3. Queued Unstarted Engineering Work
- **E13b** (`apps/memory/upgrade/prompts/E13b_similar_queries_vocab_agent.md`) — D21 similar-query clustering & logical agent vocabulary proposer + E10 minor review cleanups.
- **Messenger iPhone LAN API URL fix** (`apps/messenger` equivalent of E14c Piece 2).
- **Non-blocking quality/packaging:** S2 extraction cost (`$0.00514/day` vs `$0.0044` target) & 7/8 supersession gate, synthetic Account B chat `cited=0`, minor RN-Web console warnings on `/memory`, Cloudflare Tunnel (`D13`), 5+ user test, pitch decks & demo videos.

---

## 4. Founder Local 3×3 Testing Checklist
1. In `apps/api/.env`: start local Postgres on port `15422` OR leave `DATABASE_URL=` blank for SQLite.
2. Add Google OAuth keys (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `OAUTH_TOKEN_KEY`) + redirect URIs (`/api/identity/google/callback`, `/api/ingest/google/callback`) & test users in Google Cloud Console.
3. Run `powershell -ExecutionPolicy Bypass -File scripts\dev\start-all.ps1 -Shells` (now starts all 3 websites, 3 Expo apps `:8081/:8082/:8083`, and 3 Electron desktops).
4. Run first live real-data walkthrough (Google sign-in across 3 apps, iPhone QR pairing, real ingest `>= 5` Today cards).
