# E2b review (pairing polish) - Claude verifier, 2026-11-24

Verdict: MERGED into main 86f0457 (tip reviewed 4fbb019). No BLOCKING issues.

Scope: only apps/api (identity router/service/store, tests, .env.example), apps/mobile, apps/desktop. apps/web identical to baseline tag. No secrets/personal emails in added lines.

Checklist
1. QR carries API URL - OK. service.py `_public_api_base_url` (env PUBLIC_API_BASE_URL, http/https only, no userinfo) + start_pairing payload `&api=` (code-only fallback). Mobile lib/auth.tsx `validatePairingApiBase` / `isLocalOrPrivateHost`: https anywhere, http only localhost/127/10/172.16-31/192.168; ScanQrModal (QrPairingModals.tsx submit) refuses others; manual entry kept. .env.example has name only.
2. Desktop sign in/out control - OK. SettingsPanel.tsx (authStatus/authSignIn/authSignOut, "Not signed in" or email), bridge.ts stub for browser preview.
3. Rate limit - OK. service.py `_pair_throttle_check` / `_pair_record_failure`: 5 failures per IP per 300 s -> 429; code invalidated after 5 wrong guesses (store.invalidate_pairing_code). Keyed on request.client.host (router.py complete), not a client header.
4. Paired phone cannot start pairing - OK. service.py start_pairing checks store.is_pairing_session -> 403.
5. Loopback nonce - OK. desktop auth.ts: crypto.randomBytes(24) per attempt, embedded in callback URL, checked with timingSafeEqual before any auth_code handling, 403 otherwise; API append_auth_code preserves existing query.

Tests (clean tree at 4fbb019): api 644 passed, 16 skipped, 0 failed (incl. test_ops and test_e3_ingest). mobile: npm ci OK with no lockfile change, jest 50 passed, tsc clean. desktop: npm ci OK, main tests 18 passed, typecheck:main clean; renderer 7 passed, tsc clean.

Non-blocking notes
- Rate-limit store is in-memory and unbounded: `_pair_ip_failures` keeps empty lists per IP, `_pair_code_failures` grows per distinct guessed code (never pruned). Needs pruning/TTL eventually; bounded in practice by the 5/IP/5min limit. Also per-process (not shared across workers) and resets on restart.
- Limiter trusts request.client.host; behind a reverse proxy all clients share one IP unless proxy headers are configured.
- apps/desktop/renderer has no package-lock.json (pre-existing on main), so `npm ci` fails there; I used `npm install` in the throwaway tree.
