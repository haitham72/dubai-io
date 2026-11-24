# E2b report - pairing polish (builder, 2026-11-24)
Branch e2b/pairing-polish, tip 4fbb019 (from origin/main d485571), pushed, NOT merged. Worktree G:/Haitham/VsCode/contest-e2b.

## What
1. QR carries API base: /pair/start adds `&api=<urlencoded PUBLIC_API_BASE_URL>` to qr_payload (+ `api_base_url` field) when env is set and is http(s); unset/invalid -> old code-only payload. Mobile `parsePairingScan` + `validatePairingApiBase` (https anywhere; http only localhost/127/8, 10/8, 172.16/12, 192.168/16); invalid -> honest error, nothing submitted. On success the base is saved (SecureStore via saveSettings) and used. Manual code entry unchanged. `PUBLIC_API_BASE_URL=` added to apps/api/.env.example.
2. Desktop Settings panel: Sign in / Sign out button + "Signed in as <email>" / "Not signed in" via allowlisted authStatus/authSignIn/authSignOut IPC (bridge types added; demo bridge says sign-in needs the desktop app). Existing styles only.
3. /pair/complete: per-IP lockout after 5 failures in 5 min (429 too_many_attempts); a code that collects 5 failed attempts is invalidated (429 code_invalidated). Counters are in-memory in IdentityService (reset on API restart; single-process). Note: wrong guesses of non-existent codes are counted per submitted string, so the per-IP lockout is the real brute-force guard.
4. start_pairing refuses sessions minted by pairing (cs_pairing_codes.consumed_by_session_id) -> 403 pairing_from_paired_device. No schema change.
5. Desktop loopback callback URL carries a random 24-byte nonce (?nonce=); requests without a matching nonce get 403 (timing-safe compare) and do not settle the sign-in.

## Tests
- apps/api full: 637 passed, 17 skipped, 6 failed (test_ops redis + 5 env-only test_e3_ingest) - was 631 passed; +6 new in test_e2_signin_pairing.py (14 there).
- mobile: npm ci ok, jest 50 passed (10 suites; +6 new e2b-pairing), tsc clean.
- desktop main: npm ci ok, vitest 18 passed (+1 nonce), tsc -p tsconfig.main.json clean. Renderer: no lockfile exists (pre-existing); installed with `npm install --no-package-lock`, vitest 7 passed (+2 new), tsc renderer clean.
- apps/web identical to baseline tag. package.json/lock untouched (npm ci succeeds).

## Remaining
- Real phone scan of the QR is untested on device (camera path is Expo-only); logic is unit-tested.
- Desktop renderer lacks a package-lock.json (pre-existing).
