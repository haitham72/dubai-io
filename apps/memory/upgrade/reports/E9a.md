# E9a - stack fixes (branch e9a/stack-fixes, from origin/main 4e8d531)

Fixes U7_final FAILs 2, 3, 5, 7, 8, 9. No secrets printed or committed. Synthetic data only.

| FAIL | Fix | Where |
|---|---|---|
| 2 | start-all passes `TM_ADMIN_TOKEN` (memory `.env`, generated there if missing) to apps/api, Community and Messenger by process env only. Health row `owner-provisioning-ready` (empty-body POST /v1/owners with the token: 422 = accepted, nothing created; plus apps/api started by start-all) | scripts/dev/start-all.ps1, health.ps1 |
| 3 | start-all always runs `docker compose up -d --build api` (cached; `-Rebuild` = no-cache). Marker `.memory-image.json` (hash of Dockerfile + pyproject + README + src, running image id); health row `memory-image-current` | scripts/dev/memory-image.ps1, start-all, health |
| 5 | CORSMiddleware, explicit allowlist: localhost:8081, 127.0.0.1:8081, plus `PUBLIC_WEB_ORIGINS` (start-all adds http://LAN:8081). Methods GET/POST/PUT/PATCH/DELETE/OPTIONS; headers Content-Type, Authorization, X-App-Session, X-App-Id; no credentials, no wildcard | apps/api/app/cors.py, main.py, .env.example |
| 7 | Cause: the engine `context_pack` is word-overlap retrieval ("sport" shares no word with "joined the surf school"); live it returned 0 facts. REVISED per founder design (chat gets only retrieved, relevant facts): no fallback. An empty pack means chat answers without memory, 0 citations, response field `memory_used: false` (true when facts were retrieved). Engine fix owned by the engine builder: `core/retrieval.py` `search_candidates` / `live/context.py:351` (use the hybrid semantic channel) | apps/api/app/chat_memory.py |
| 8 | GET /api/community/profiles/me answers 200 `{"profile": null}` when none; client returns null (one call, was two); page shows "No profile yet" | community/routes.py, apps/community/src |
| 9 | Main window loads the Dubai-io app (`DUBAI_APP_URL`, default http://localhost:8081) with no preload; same guard as Community/Messenger (will-navigate, window.open deny, webview deny); honest offline page on load failure; menu "Dubai-io > Settings and Sign in..." (Ctrl+,) opens a Settings window (built renderer, allowlisted preload, all navigation denied). Found and fixed: the sandboxed preload `require`d ../main, which cannot work in a sandbox, so channel names are inlined (test asserts equality with IPC). start-all builds the renderer if missing/stale and passes env | apps/desktop/electron |

Choice for 9: main window = web app, Settings = second window, so remote web content never gets the IPC bridge.

## Tests
- apps/api full pytest from the e9a tree: 670 passed, 16 skipped (was 664): +4 CORS, +2 chat, community core test updated.
- apps/desktop main: 28 passed (18 + 10 new) + tsc; renderer 7 passed + build.
- apps/community: vitest 19 passed (+3), tsc clean, next build OK.
- `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web`: clean.

## Live check (start-all from the e9a worktree; waited ~1 h on E9b's DOCKER_LOCK, as designed)
- health: all rows GREEN incl. `memory-image-current` and `owner-provisioning-ready`.
- first ingest for fresh synthetic owner (WhatsApp, 3 records): HTTP 200 (no 503). Backfill 1 job applied, 2 facts.
- chat "What sport am I doing lately and where?": 2 citations (engine context alone: 0 facts).
- Forget WhatsApp: raw SQL scan of all owner tables before = records 2, aliases 2, attempts 1, visible_facts 2, entities 1, facts 2; after = {}. Leftover chat turn record forgotten via /api/vault/forget; 0 live records, 0 facts.
- Website :8081 at 1440x900 in Playwright: /, /memory, /connect load; 0 console errors; cross-origin fetch :8081 -> :8000 returns 200.
- Desktop via CDP: main window title "Dubai-io", shows the app (Quest, Today, Chat; no bridge); Settings window loads the renderer with `window.dubaiDesktop` (13 methods) and the Settings tab.
- Real claude CLI calls: about 3 (1 extraction + chat answer + possible chat-turn extraction).
- stop-all done; postgres/rabbitmq/redis restarted and running; no app, worker, browser or Electron processes left.

## Not done / notes
- Engine paraphrase recall (FAIL 7 root cause) left to the engine owner; FAIL 1, 4, 6 untouched (not in scope).
- stop-all also stops infra; restarted by hand.
