# E14a: Community Facebook/Reddit Social Parity + E11b/E12 Cleanups (Devin)

Read `apps/memory/upgrade/prompts/E0_real_data_round.md`, `docs/submissions/community/FACEBOOK_REDDIT_RECOMMENDER_PLAN.md` (§1), and `docs/submissions/shared/founder-decisions.md` (D3, D11, D14, D19, D22). Branch **`e14a/community-social-parity`** from latest **`main`** (`5a5f6bd`+). Open one PR into `main`. Do NOT touch `apps/web` or add P2P messaging inside Community (D3).

## Deliverables

### Part 1 — Community Social Parity (`apps/api/app/community/**`, `apps/community/src/**`, `apps/community/tests/**`)
*(Note: backend paths are now unlocked for you on this E14a slice — extend existing `cm_*` SQLite+Postgres-compatible schema in `app/community/store.py` and routes in `app/community/routes.py` cleanly without touching parked `app/communities.py`.)*

1. **Reddit Voting & Sorting (`cm_votes`):**
   - Table `cm_votes (owner, target_type IN ('post','comment'), target_id, value IN (-1, 1), created_at)` PK `(owner, target_type, target_id)`.
   - `POST /api/community/posts/{id}/vote` and `/api/community/comments/{id}/vote` (`value: 1 | -1 | 0` toggle), returning authoritative `score` (upvotes - downvotes) and `my_vote`.
   - Extend `GET /api/community/feed?sort=hot|top|new|rising|controversial` using time-decayed Hot scoring server-side; wire all sort pills across `For you`, `Following`, and `Communities` lanes.
2. **Hashtags & Flairs (`cm_post_tags`, `cm_posts.flair`):**
   - Extract `#hashtags` on post create/edit into `cm_post_tags (post_id, tag, created_at)` (normalize lowercase), allow optional post flair (`Question | Recommendation | Event | Warning | Housing`).
   - Add `GET /api/community/tags/trending` and tag filter on `GET /api/community/feed?tag=...`.
   - Add clickable `#tag` pills on `RealPostCard`, `/t/[tag]` tag feed page, and flair/tag selector in `/create`.
3. **Reposts & Quote-Posts (`cm_posts.repost_of_id`):**
   - `POST /api/community/posts/{id}/repost` (with optional quote text; **must fail 403/404** if target post is deleted or inside a private group the caller cannot access).
   - Render repost/quote cards cleanly with original author & link.
4. **Block & Mute (`cm_user_blocks`, `cm_user_mutes`) — Server-Enforced:**
   - `POST/DELETE /api/community/blocks/{handle}`, `POST/DELETE /api/community/mutes` (`kind: owner | group | tag`), `GET /api/community/safety`.
   - Blocked owners' posts, comments, search hits, and profile links are filtered server-side everywhere (`feed`, `search`, `discovery`, `comments`, `notifications`). Muted owners/groups/tags are excluded from caller's `feed` and `discovery`.
5. **Reports & Moderation Queue (`cm_reports`):**
   - `POST /api/community/reports` (`target_type`, `target_id`, `reason`, `detail`), `GET /api/community/moderation/queue`, `POST /api/community/moderation/{report_id}/resolve` (`keep | remove | restore`, moderator/group-owner auth only). Safety reports jump queue priority (`priority = 'high'`).
6. **Split Memory Consent Toggles (`MORNING.md` §E #8 + D19):**
   - Split saved-discussions vs public-posts memory consent into two independent server toggles (`remember_saved_discussions`, `remember_public_posts`) in `app/community/memory_routes.py` + `apps/community/src/app/profile/page.tsx`.
   - Per D19, item-level Community memory feedback lowers weight rather than deleting (`POST /api/community/memory/lower` or updated UI label **Lower** instead of item Forget while keeping account Delete-my-data separate).
7. **Collapsible Threaded Comments & UI Polish:**
   - Nested comment collapse/expand in UI (`RealPostCard` / thread view), keeping D14 rules (light mode, zero shadows, plain AI text / tinted user box / white rounded action boxes).

### Part 2 — Non-Blocking Cleanups from E11b & E12 Reviews
Include these 5 small fixes in the same PR:
1. `apps/community/src/`: import `RealPostCard` button/card styles in `RealPostCard.tsx` (or `layout.tsx`) so `/search`, `/t/[tag]`, and `/communities/[id]` render identically to `/`; apply active sort pill (`Hot`/`Top`/`New`/`Rising`) on `For you` lane too.
2. `apps/memory/tests/test_embed_lazy_backfill.py`: stub `onnxruntime` or use `pytest.importorskip` in `test_failed_model_load_is_cached_for_backoff_window` so `apps/api` venv runs cleanly.
3. `apps/memory/src/temporal_memory/core/embed.py`: re-check queued `_PENDING` rows against quarantine before embedding and pop `_PENDING[owner]` when `facts_version` advances.
4. `scripts/dev/stop-all.ps1`: wrap `$p.StartTime.ToString('o')` in a guarded fallback when access to a mismatched PID's `StartTime` throws so remaining PIDs still process.

## Tests & Gates (Run All)

- `apps/api`: `DATABASE_URL=' ' pytest -q tests/test_community_*.py tests` (cover happy & failure paths for voting, hashtags, reposts of private/deleted posts -> 403/404, blocks/mutes hiding content, reports/mod auth 403 for non-mods, split consent).
- `apps/community`: `npm test` (vitest), `npx tsc --noEmit`, `npm run build`, plus Playwright E2E (`apps/community/tests/e2e/test_community_web_e2e.py`) extended to verify upvote, hashtag click, repost, block hiding content, and screenshot capture under `apps/community/tests/e2e/screens/`.
- `apps/community/mobile` & `apps/community/desktop`: `npm test`, typecheck, build.
- `apps/memory`: `pytest -q tests/test_embed_lazy_backfill.py` in full memory venv against Postgres `:5442`.
- `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` must exit `0`.
- Report → `apps/memory/upgrade/reports/E14a.md` + line in `STATUS.md`. Do NOT merge into `main`.
