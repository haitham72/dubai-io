# E9a review (Claude verifier, 2026-11-25)

Verdict: MERGED into main a17f5b5 (from f077a72). No blocking issues.

Scope (three-dot vs origin/main): 22 files, all expected: scripts/dev/*, apps/api (cors.py, main.py, chat_memory.py, community/routes.py, .env.example, tests), apps/community (profile page, api.ts, test), apps/desktop (window/menu/security/preload + tests). No apps/memory, no apps/web (diff vs mobile-pwa-baseline-2026-10-23 empty). Secrets grep on added lines: clean.

Checklist
- a (B) CORS OK: api/app/cors.py:8-27. Explicit list (two localhost defaults + PUBLIC_WEB_ORIGINS split/trimmed/empties and "*" dropped), allow_credentials=False, no regex, methods/headers limited. Wired main.py:146.
- b (B) Admin token OK: start-all.ps1:237 reads TM_ADMIN_TOKEN from apps/memory/.env (gitignored: apps/memory/.gitignore:4), sets it via process env only (:365, :408), removed after spawn (:377); never echoed. Note: start-all does not generate it when missing (existing behaviour, not changed here); the builder spec said "only if missing" - token must pre-exist in .env. health.ps1:155-178 owner-provisioning-ready posts "{}" -> expects 422, creates nothing, prints no token.
- c OK: start-all.ps1:255-271 always `up -d --build api` (cache), `-Rebuild` = build --no-cache; marker src hash + image id; health.ps1:133-149 compares both. No `down -v`.
- d (B) Chat OK: chat_memory.py:379-461 only context-pack facts (sensitive filtered), no recent-facts padding anywhere, memory_used=bool(safe_facts); citations at :473-488 only from safe_facts_by_id (pack fetched for the verified principal's own owner, :412/:442). Tests in test_e4_chat_today.py.
- e OK: community/routes.py:300-305 still goes through scope(request) (session required) and profile_by_owner(store, owner) = own row only; returns {profile: null}. Test updated.
- f (B) Desktop OK: window.ts main window has webPreferencesBase only, no preload; attachNavigationGuards (security.ts:70-100) blocks off-origin will-navigate, denies window.open, blocks webview; settings window has preload + contextIsolation/sandbox on, nodeIntegration off (security.ts:2-9), allowedOrigin about:blank. Preload channel table inlined (preload/index.ts:3-17); security.test.ts:145-150 asserts it equals IPC allowlist. Note (non-blocking): resolveAppUrl (security.ts:22) accepts any http(s) URL, including remote http, with no warning.

Tests (clean tree, no .env): apps/api 670 passed, 16 skipped; desktop main 28 passed + typecheck ok; desktop renderer 7 passed + build ok; community 19 passed + build ok.
(desktop e2Account test needs the electron binary: npm ci --ignore-scripts then node node_modules/electron/install.js.)

Stack cycle: SKIPPED - DOCKER_LOCK present (E9b holding it). Cite builder's live check in E9a.md.

Non-blocking notes: the above DUBAI_APP_URL and token-generation notes; contest-e9a worktree and local branch e9a/stack-fixes retained (worktree has untracked .env files and untracked AGENTS.md/tsbuildinfo/renderer dist). Remote branch deleted. Main checkout fast-forwarded to a17f5b5.
