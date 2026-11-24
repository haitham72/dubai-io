# Morning handover, 25 Nov 2026

Main is at `835db76` (plus this docs commit). Numbers below come from the reports in this folder. Where a report disagrees with the plan, the report wins and the difference is noted.

## A. Summary

Everything planned overnight is merged into main (`835db76`). You can now test, on your own data: the Dubai-io website (`http://localhost:8081`), the iPhone app through Expo Go, and the Electron desktop app. Community (website `:3060`) and Messenger (website `:5173`) also run, with their phone and desktop shells. All of them use one Google sign-in and the real temporal_note memory (the engine on `:8040`). Nothing was tested with a real Google login, a real iPhone or your real data yet. That is your test.

## B. Your steps, in order

1. **Prerequisites.**
   - Docker Desktop is running (Linux containers).
   - `claude` CLI is signed in on this PC. Extraction runs through it on the host, using your subscription (Haiku, medium effort).
   - Node 20+ and the Python venvs are set up as in `scripts\dev\README.md` (`apps\api\.venv`; `start-all` installs the memory engine into it and runs `npm ci` itself).
2. **Google Cloud Console (one time).**
   - Authorized redirect URIs, exactly these two:
     - `http://localhost:8000/api/identity/google/callback`
     - `http://localhost:8000/api/ingest/google/callback`
   - Enable Gmail API, Google Calendar API, YouTube Data API v3.
   - OAuth consent screen: External, status Testing. Add your Gmail and the tester Gmail as test users.
   - Client id and secret stay in `apps/api/.env` (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`). Never paste them in chat.
3. **Start everything.** In PowerShell, from the repo root. Do not pipe the output (it never returns):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\dev\start-all.ps1
   powershell -ExecutionPolicy Bypass -File scripts\dev\health.ps1
   ```
   - First run takes about 3 minutes (162 s measured): the memory image rebuilds and a one-time ~570 MB semantic model (bge-m3) downloads into the Docker volume `tm-hf-cache`. Later runs take about 1 minute (67 s measured).
   - It creates `apps/memory/.env` with the memory admin token if it is missing. It never prints it.
   - `health.ps1` must show every row GREEN. Important rows:

   | Row | Good |
   |---|---|
   | container:postgres / rabbitmq / redis / api | running (healthy) |
   | memory-api:8040, apps/api:8000 | GREEN |
   | memory-semantic-model | GREEN (red = model not loaded yet) |
   | memory-image-current | GREEN |
   | owner-provisioning-ready | GREEN |
   | host workers p0@w, p1@w, exactly one beat | GREEN |
   | llm-runner | `claude -p` (Haiku, medium effort) |
   | website:8081, expo-lan:8081, lan-ip | GREEN |
   | community-api:8060, community-website:3060 | GREEN |
   | messenger-api:8070, messenger-website:5173 | GREEN |
   | community-memory, messenger-memory | backend `http` |
   | desktop | GREEN (SKIP only if you used `-NoDesktop`) |

   Last full stack check: 27/27 GREEN (E5); 26/27 after E8 with the desktop deliberately stopped. A check after E9d showed all GREEN except desktop (run with `-NoDesktop`).
4. **iPhone on the same Wi-Fi.** Only if the phone cannot reach the PC, run once in an elevated PowerShell (copied from `scripts\dev\README.md`):
   ```powershell
   netsh advfirewall firewall add rule name="Dubai-io Dev TCP 8000" dir=in action=allow protocol=TCP localport=8000 profile=private
   netsh advfirewall firewall add rule name="Dubai-io Dev TCP 8081" dir=in action=allow protocol=TCP localport=8081 profile=private
   ```
5. **Sign in on the PC.** Open `http://localhost:8081`, press Sign in with Google (Connect screen: `http://localhost:8081/connect`). You return showing your name and email.
6. **Pair the iPhone.**
   - In Expo Go, scan the `exp://<LAN IP>:8081` QR that `start-all` prints (or type the address).
   - On the PC, Connect > Pair your iPhone. In the phone app scan that QR. It carries the PC's API address and a one-time code (valid 5 minutes, one use). Manual code entry is the fallback.
   - Difference from E2: E2 said the phone's API address must be typed by hand. E2b fixed that (the QR carries it). The scan itself is still unit-tested only, not tried on a real phone.
   - Revoke a phone: Connect > Signed-in devices > Revoke.
7. **Connect sources.**
   - Per-source consent switches are off by default. Turn one on, then connect.
   - Sources: Google (Gmail, Calendar, YouTube), Takeout upload, WhatsApp upload.
   - Start with a small window (a few days).
   - Cost and speed, from the reports: about $0.002 per extraction call (2.8k tokens in, 2.3k out), about 10-12 s model time per call. The verifier measured about 61 s end to end for one record (includes queue pickup). Mean over the 31-day synthetic month: $0.00517 per day. This runs on the PC's host workers through your `claude` subscription.
8. **What to check.**

   | Screen | Good looks like |
   |---|---|
   | Today | Cards, each with a source and an `as_of`. Owed check: E6 saw 0 cards on synthetic data with no provider keys. Tell us how many live cards you get on your real data (the target in E4 was at least 5, with images). |
   | Chat | Answers cite memory facts. When nothing matches it says no memory was used (`memory_used: false`, 0 citations). It does not pad with unrelated facts. |
   | Memory graph | Both views load. Open "why" and "story" on a fact. Export the Quest tree. |
   | Forget | Forgetting a source erases its text everywhere (records, facts, search index, raw model output). Forgetting ONE fact keeps the source email's text. To remove it, forget the source. |
9. **Community and Messenger.**
   - Community `http://localhost:3060` (`/signin`) and Messenger `http://localhost:5173` (Settings > Account). Same Google sign-in, same account as Dubai-io.
   - Community > Profile > Memory: three switches (order Discover by interests, remember my posts and saved discussions, share interest topics) and a Forget button. A switch changes only after the server answers.
   - Messenger: on a text message choose "Save to memory". The approval card lists exactly what is shared (text, written by, sent at, scope). Settings > AI > Memory shows saved items with per-item Forget. Needs real mode with a signed-in session (demo mode shows no Save button).
10. **Desktop.**
    - The Dubai-io desktop window shows the app (it loads `http://localhost:8081`).
    - Settings and Sign in: menu Dubai-io > Settings and Sign in... (Ctrl+,).
    - Community and Messenger desktop shells load their websites.
11. **Tester isolation.** Sign out. Sign in with the tester Gmail in all three apps. You must see none of your data. Save a distinctive word (for example "falconry") as one account and check it never shows for the other (Feed, Inbox, search, Chat). Repeat in reverse. New accounts start with memory off everywhere.
12. **Stop.** `powershell -ExecutionPolicy Bypass -File scripts\dev\stop-all.ps1`. It also stops the infra containers. Data volumes are kept. Add `-KeepInfra` to leave postgres, rabbitmq and redis running.

## C. What merged overnight

| Item | What it does | Main sha | Tests |
|---|---|---|---|
| Doc audit | 31 md files cleaned; rules 1-10 and Gates byte-identical | d4a127a | `apps/web` untouched |
| E2 sign-in + QR pairing | Google sign-in (PKCE) on PC, website and desktop; QR pairing for the phone; source consent and uploads wired | 8c5b547 (+ lockfile d485571) | api 631/637 + 5 env-only proven 16/16; mobile 44; desktop 17 |
| E2b pairing polish | QR carries the API address; pair brute-force limit (5 failures per IP per 5 min); paired phone cannot mint codes; desktop sign-in nonce and button | 86f0457 | api 644 passed / 16 skipped; mobile 50; desktop main 18, renderer 7 |
| E7 receipt pre-pass | Regex reads purchases, devices, bookings from email before the LLM; sensitive records held back | 4202a33 | memory 428 passed / 8 skipped (+15) |
| E1 one-command stack | `start-all` / `stop-all` / `health` for the whole stack | 1ed8759 | health 15/15 GREEN; api 644 passed / 16 skipped |
| E1b host workers | Extraction workers run on the host with the `claude` CLI; two engine bugs fixed (CLI envelope parse, Rule-9 screen through the CLI) | 7fc38fb | memory 432 / 8 skipped; api 644; renderer 7; stack 20/20 |
| E3, E4 (earlier, for reference) | Real-data ingest; chat and Today feed endpoints | 68e2147, 36eb356 | api 623 passed / 17 skipped |
| E5 Community + Messenger on the shared layer | One identity store and the real memory engine for both; `app_id` on sign-in and pairing; bridge fixes | 9233daf | api 653 / 16 skipped; community 11 + build; shells 11 / 8 / 6 / 8; CS-1 live bridge 86 passed / 6 skipped / 0 failed (fake 92); stack 27/27 |
| E5b memory UI | Community consent switches + Forget; Messenger Save-to-memory approval card + Settings memory; pair store bounded | 48f7ce3 | api 664 / 16 skipped; community 16 + build; messenger memory-ui 10 checks + store |
| E8 engine fixes | Trimmed CLI call: 23.6k to 2.8k input tokens, $0.083 to $0.002 per call; user Forget scrubs text; resolve returns old/new fact | 4e8d531 | memory 443 / 8 skipped; api 653; stack 26/27 (desktop stopped); proof 2.8k in / 3.4k out / $0.0025 |
| E6 full system test + harness | 46 checks on 4e8d531: 37 PASS / 9 FAIL; harness merged | 50f8f4a | memory 443 / 8 skipped |
| E9a stack and app fixes | Admin token passed to apps; image always rebuilt; website CORS allowlist; honest chat; Community no-profile state; desktop loads the app | a17f5b5 | api 670 / 16 skipped; desktop 28 + renderer 7; community 19 |
| E9b engine quality | Change tracking (superseded, ended, late), privacy false positives down, live semantic recall in chat, Forget sweeps raw model output | 9d7b9e5 | memory 475 / 8 skipped; S3, S5, S7 PASS |
| E9d model volume + warm-up | Docker volume for the semantic model (downloads once); `start-all` warms it before green; health row | 835db76 | memory 476 / 8 skipped |

E6 FAILs: E9a fixed FAIL 2, 3, 5, 7, 8, 9. E9b fixed FAIL 4 (Forget sweep) and the S2 change tracking. E9a says FAIL 1 and 6 were not in its scope. No report says they were fixed later.

## D. Current numbers

Tests, latest report for each:

| Area | Result | Source |
|---|---|---|
| apps/memory | 476 passed, 8 skipped | E9d |
| apps/api | 670 passed, 16 skipped (clean worktree, no `.env`) | E9a |
| apps/mobile | 50 jest passed, tsc clean | E2b |
| apps/desktop | main 28 passed + renderer 7 passed | E9a |
| apps/community | 19 vitest passed, build OK | E9a |
| apps/messenger | typecheck + build OK, test:store OK, memory-ui 10 checks | E5b |
| Shells | community mobile 8, community desktop 11, messenger mobile 8, messenger desktop 6 | E5 |

S2 extraction quality (31-day synthetic month, plus late packet):

| Measure | U7_main (4e2646d) | E6 baseline (U7_final) | E9b final | Gate |
|---|---|---|---|---|
| Superseded | 4/8 | 5/8 | 7/8 | |
| Ended | 0/5 | 0/5 | 5/5 | |
| Late | 1/4 | 0/4 | 3/4 | |
| Privacy false positives | 3.92% | 3.92% | 1.96% | at most 2% |
| Recall | 76.5% | not in reports | 88.2% (base rerun 91.2%) | |
| Precision | 53.5% | 75.9% | 68% (base rerun 90%; judge-variable) | |
| Cost per day (mean) | $0.006394 | $0.00531 | $0.00517 | $0.0044 |
| Sensitive leaks | 0 | 0 | 0 | 0 |
| Rejected jobs | 0 | 0 | 0 | |

- S1 retrieval at 20k facts: warm p95 12.84 ms (U7_main). Uncached /context p95 149.64 ms and /search 116.40 ms (U4). Cached /context with HNSW 142.79 ms (S10). All under the 150 ms gate.
- Extraction call (E8): 2,821 tokens in, 2,317 out, $0.002045, 10.1 s model time, 12.4 s wall for one record. Verifier run: 2,829 in, 3,411 out, $0.002486, about 61 s end to end.
- Before the trim (E1b): 23,562 in, 12,801 out, $0.08285, about 156 s.
- Semantic recall (E9b): "sport" now finds "joined a surf school". Live first query after start 0.07 s (E9d); a bare container recreate loads the model on the first query in 1.45 s.

## E. Open issues and decisions for you

| # | Item | Where |
|---|---|---|
| 1 | Extraction cost $0.00517 per day vs $0.0044 target: not met. | E9b.md section 4; E7.md |
| 2 | S2 superseded 7/8 and late 3/4. E9b says the remaining misses are judge counting (f003, f041), not extraction. | E9b.md |
| 3 | Today cards on real data: the E4 check (at least 5 live cards with images) is still owed. E6 saw 0 cards (`empty_reason` no_live_results / no_confirmed_interests). | E4.md; E6 e2e JSON |
| 4 | **DECISION:** a hard-coded 22-word synonym group (sport, surf, football, padel, running...) in `apps/memory` `core/retrieval.py` `_SYNONYM_GROUPS`. Added because bge-m3 does not link "sport" and "surf school" (cosine 0.34, same as unrelated pairs). Keep, move into the subject vocabulary, or delete? | E9b.md; E9b.review.md (d) |
| 5 | The end-verb fallback ("cancelled", "quit") can mark a fact ended when the subject is someone else ("Omar quit", "not cancelled"). | E9b.review.md (b) |
| 6 | Forgetting one fact keeps the source record's text. The UI should say so or offer "forget the source too". | E8.review.md |
| 7 | Lazy embedding of older facts is capped at 64 per facts version, no time budget, and marks the version done even if more remain. Model load runs inside the request. | E9b.review.md (e) |
| 8 | Community "saved discussions" and "public posts" share one consent flag. | E5b.md |
| 9 | Messenger memory UI has no browser click-through test (approval card rendered as static markup). | E5b.md |
| 10 | `DUBAI_APP_URL` (desktop) accepts any http(s) URL without a warning. | E9a.review.md |
| 11 | `stop-all` cannot tell if a recorded PID was reused after a reboot. | E1.review.md |
| 12 | `apps/api/requirements.txt` pins celery 5.5.3 / redis 5.2.1; the venv has 5.7.0 / 8.2.0. No conflict reported. | E1.md |
| 13 | Running apps/api pytest in the main checkout picks up your `apps/api/.env` `DATABASE_URL` (about 14 false Postgres timeouts). A permission-denied `pytest-of-h.ibrahim` folder also breaks collection there. Run from a clean worktree. | E1.md, E1.review.md |
| 14 | The CS-1 live bridge suite spends subscription calls when the host workers are up. | E1b.md |
| 15 | Synthetic test owners are left in the local dev database (E6, E9b, and earlier proofs). | E9b.review.md |
| 16 | No fully clean "run end to end on a real phone" evidence: QR scan, Expo Go over the LAN, firewall and real Google sign-in were never run. | E1.md, E2.md |
| 17 | Pair-code and sign-in rate limits are in memory per process and reset on API restart; behind a proxy all clients share one IP. | E2b.review.md |
| 18 | `subject_aliases` and `subjects.label` are not scrubbed by Forget (static vocabulary). Old job output with no link to an erased record cannot be found by any query. | E8.review.md; E9b.md section 1 |
| 19 | "Egyptian Arabic speaker" now passes the privacy filter (weak trait); "Egyptian passport" and "Quran" stay held on purpose. | E9b.review.md |
| 20 | `_late_superseder` could demote an older fact for two different trips on one subject ingested out of order. | E9b.review.md (b) |
| 21 | The agent-CLI classifier treats an item with a number but no `category` as "none" (layer 1 still screens it). | E1b.review.md |
| 22 | The pairing flow issues the session before consuming the code (a failed consume leaves an unreturned session row). | E5.review.md |
| 23 | Desktop Brave import is not supported by sync. | E2.md |
| 24 | Difference between reports: E9a.review says `start-all` does not generate `TM_ADMIN_TOKEN`; the STATUS E9c line and README say it does (since 630ea72). The later STATUS line wins. If owner provisioning fails, check `apps/memory/.env`. | STATUS.md |

## F. Housekeeping for you

Nothing was deleted. `git worktree list` shows these:

| Worktree | Branch | Why kept |
|---|---|---|
| `G:\Haitham\VsCode\contest-e1-run-stack` | e1/run-stack (d707653) | Holds untracked `apps/api/.env` (may hold a service token). Remote branch deleted. |
| `G:\Haitham\VsCode\contest-e1b` | e1b/host-workers (e92c872) | Holds untracked `.env`. |
| `G:\Haitham\VsCode\contest-e5` | e5/shared-layer (6887f23) | Holds untracked `.env`, plus `AGENTS.md` and a tsbuildinfo file. |
| `G:\Haitham\VsCode\contest-e9a` | e9a/stack-fixes (f077a72) | Holds untracked `.env` files, `AGENTS.md`, tsbuildinfo, renderer `dist`. |
| `G:\Haitham\VsCode\contest-e6` | e6/full-test (f5bd595) | 22 web screenshots in `apps\memory\acceptance\results\screens\` for the design pass, plus the E6 result JSON files (not tracked on main). |
| `G:\Haitham\VsCode\contest-memory` | memory (2570117) | The memory branch. Its reports folder was the source of this commit; it has uncommitted reports and a modified STATUS.md. |
| `C:\Users\h.ibrahim\Documents\Claude\Projects\contest-doc-audit-2026-11-24` | docs/audit-2026-11-24 (4e2646d) | Codex's audit worktree. `git merge-base --is-ancestor 4e2646d origin/main` is **true**, so its commit is already in main. It has an untracked `docs/doc-audit-2026-11-24.md`. |

Untracked files in main (you decide; never touched):

1. `design/20-11-2026/Dubai-io Quest Milestones Showcase.jpg`
2. `docs/Researches/new tools research.md`
3. `docs/plan/Memory/deepseek_markdown_20261124_fbeb70.md` (suggested home for the DeepSeek review: `apps/memory/upgrade/reviews/`)

Remote branches left (`git branch -r`): `origin/chore/npm-lockfiles`, `origin/fix/community-next-security`, `origin/mem-wpU6`, `origin/memory`, `origin/main`.

## G. Next

After your real-data test: the design pass against `design/20-11-2026` (the screenshots are ready).
