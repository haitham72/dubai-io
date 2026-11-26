# Integrator handoff + founder test plan — 2026-11-26 (b)

**From:** Claude (integrator since 26 Nov 10:01 Dubai). **For:** the next integrator session and builder agents, plus the founder's test run.
**Supersedes:** `HANDOFF_integrator_2026-11-26_to_claude.md` (that file's queue §4 items 1–2 are now done).

## 1. State of `main` — ready to test

`main` = `7d51577` (pushed; PRs #11 and #12 show MERGED).

| Commit | What |
|---|---|
| `72acfa2` | merge **E14** (PR #11): Community replica, two-tower recommender, context profile (opt-in, TTL-only context), real Lower/recall, Community purge hook |
| `7d51577` | merge **E13a** (PR #12): D19 Lower/Restore, D19b explicit recall + boost, account "Delete my data" (Redis + caches + sessions + Community purge), de-identified backup without Google data |

Verified on merged `main` (by the integrator's merge subagent; Claude re-checked the frozen check and conflict markers):
- `apps/web` frozen check exit 0.
- `apps/memory` Postgres `:5442` suite 559 passed, 8 skipped, 0 failed.
- `apps/api` full suite exit 0 (summary line cut off; no failures in the output).
- Community tests 85 passed, 1 skipped; Messenger `tsc` 0.
- No conflict markers.

Gate reports: `apps/memory/upgrade/reports/E14.review.md`, `E13a.review.md` (committed). Founder decision (26 Nov): Community UI quality is "mediocre", so it merged as-is; polish waits until after testing.

## 2. Open queue (strict order, integrator gates each)

| # | Item | Owner | State | Gate file |
|---|---|---|---|---|
| 1 | **E13b** shared vocab agent (PR #13, `e13b/shared-vocab-agent`, worktree `contest-e13b`) | Cursor (took over from Muse) | **BLOCKERS F1–F3** sent: full-query storage (Rule 9), purge/deleted-owner exclusion (D19), `record_query_signal` has no caller (D21). Must merge `main` (now has E13a) and re-run the Postgres suite. | `apps/memory/upgrade/reports/E13b.review.md` (untracked in `G:\Haitham\VsCode\contest`; commit it with the E13b merge) |
| 2 | **Test bench** — one plain page at `/testbench` on apps/api, only when `DEV_TESTBENCH=1` | Codex | Was blocked waiting for E14/E13a. **Unblocked now.** Branch `testbench/plain-page` from `origin/main` (`7d51577`). Health paths: Messenger `/api/messenger/health`, memory `/health`. | `TESTBENCH.review.md` (to write) |
| 3 | **N3 cleanup** — `apps/api/app/identity/router.py` wraps the Community purge import in `except ImportError: pass`; make it a hard import now that E14 is on main | Codex (fold into #2) | open | in TESTBENCH review |
| 4 | **02A Community 10-user demo population** (`docs/plan/02A_COMMUNITY_10_USER_AGENT_ORCHESTRATION.md`, untracked) | Cursor, after E13b | proposed. Its two cited companion docs don't exist, and it assumes Supabase while we run local SQLite/Postgres. Seeded data must be `demo_fixture` and excluded from training/memory. | — |
| 5 | Docs stale-file archive pass (`docs/plan` has 17 files; likely stale: `two-tower-recommender.md` (removed 26 Nov; see git history) (merged into references/recommender-plan.md 26 Nov; removed, see git history), `dubai_io_knowledge_connector.md` (removed 26 Nov; see git history) (merged into connectors/README.md 26 Nov; removed, see git history), `domain-agents.md`, `journeys.md`) | integrator → Sonnet subagent | **needs founder OK of the list**; move to `docs/archive/` with a note, never delete | — |
| 6 | GrepMem WhatsApp pilot (`docs/submissions/shared/research/grepmem-whatsapp-pilot-plan.md`, untracked) | — | deferred post-wave | — |

Contest pre-submission (non-agent unless noted): register on the portal now (free; registration closes Jan 2027); email organisers to ask whether one person may enter 3 categories, plus the existing pre-contest-code question; per entry, a deck and demo video (English); internal target **Fri 18 Dec**; hosting or tunnel (D13); 5+ adult user test; Messenger final name and mark; dated rules screenshot; backlog: S2 extraction cost, S2 7/8 supersession gate, Account B chat `cited=0`.

## 3. Founder test plan (closed network: PC + iPhone on the same Wi-Fi, no tunnel)

### 3.1 Start
1. `git pull` on `main` in `G:\Haitham\VsCode\contest` (expect `7d51577` or later).
2. `scripts\dev\stop-all.ps1` (old processes don't have the new Redis setting).
3. Start Docker Desktop.
4. Google Cloud Console: Gmail, Calendar and YouTube APIs on, and your test users listed.
5. `powershell -ExecutionPolicy Bypass -File scripts\dev\start-all.ps1 -Shells`
6. `powershell -ExecutionPolicy Bypass -File scripts\dev\health.ps1`: every row OK (shell rows say SKIP if `-Shells` wasn't used). If the iPhone can't connect, run the firewall command the start script prints (ports 8000, 8081, 8060, 3060, 8070, 5173, 8082, 8083).

### 3.2 Where things are
| App | PC web | PC desktop | iPhone |
|---|---|---|---|
| Dubai-io | `http://localhost:8081` (Connect at `/connect`) | Electron window (start-all step 6) | Expo Go → `exp://<LAN-IP>:8081` (QR in the terminal) |
| Community | `http://localhost:3060` | Electron (`-Shells`) | Expo Go, port 8082 |
| Messenger | `http://localhost:5173` | Electron (`-Shells`) | Expo Go, port 8083 |

APIs: apps/api `:8000`, Community API `:8060`, Messenger API `:8070`, memory `:8040`.

### 3.3 Accounts
- **Desktop (PC Chrome profile #1):** the tester account. Gmail/Calendar/YouTube connect and Chrome-history sharing happen **only here**.
- **iPhone user:** in **PC Chrome profile #2**, sign in to Dubai-io as the iPhone's own user and choose **Pair iPhone**. On the phone, use *Scan QR to Pair iPhone* in Dubai-io, or *Pair with PC code* (6 characters) in Community sign-in and Messenger Settings.
- Use a **throwaway account** for "Delete my data".

### 3.4 Checks (write ✅/❌ + a note; ❌ goes back to the integrator with app, device, step and what you saw)
| # | Flow | Expected |
|---|---|---|
| 1 | Sign in on each of the 3 PC web apps | Same signed-in user across apps; 18+ gate on Community |
| 2 | Pair iPhone (all 3 apps) | Phone signs in as **its own** user, not the desktop tester |
| 3 | Connect Gmail / Calendar / YouTube (desktop) | Connection status shown; nothing claims "done" without a server response |
| 4 | Ask Dubai-io something about your connected data | Answer cites sources; estimates/fixtures carry a "Demo data" pill |
| 5 | Vault → **Lower** a memory | Disappears from chat context and Today, still listed in Vault as "Lowered" |
| 6 | Search explicitly for the lowered memory / open it | Found 100% of the time; its weight goes back up (it's active again) |
| 7 | Vault → **Restore** | Back to normal |
| 8 | Community feed: For you / Following, post, comment, vote, join a group | Works; no direct messages inside Community |
| 9 | Community context toggle | **Off by default**; turning it on uses foreground-only area/state; nothing location-based is stored |
| 10 | Community "Lower Community memory" | Shows the real number of items lowered |
| 11 | Messenger: send a message phone ↔ PC; memory Lower/Restore | Messages arrive; status line reads "Lowered N item(s), as of …" |
| 12 | Desktop Electron windows (3) | Each opens its app; Dubai-io desktop Settings shows memory controls |
| 13 | **Delete my data** (throwaway account, identity settings) | Returns success; you're signed out everywhere; signing back in shows no old memory, Community context or usage profile |

## 4. Guardrails for the next session
- `apps/web` frozen (`git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` = 0).
- No force-push; no branch, worktree or folder deletion without founder OK.
- Never stage the untracked founder or build files: `apps/community/tsconfig.tsbuildinfo`, `apps/desktop/renderer/dist/`, `design/20-11-2026/Dubai-io Quest Milestones Showcase.jpg`, `docs/Researches/new tools research.md`, `docs/plan/Memory/deepseek_markdown_20261124_fbeb70.md`, `docs/submissions/shared/research/grepmem-whatsapp-pilot-plan.md`, `docs/plan/02A_COMMUNITY_10_USER_AGENT_ORCHESTRATION.md`, `env (2)`. Stage explicit paths only.
- Never print `.env` values.
- Merge order rule: builders push + open a PR + STOP; the integrator writes `<item>.review.md` with PASS, then merges `--no-ff`. `STATUS.md` conflicts: keep both sides' rows.
- Running tests from a worktree: put that worktree's `apps/memory/src` (and `apps/api`) on `PYTHONPATH`. The contest-memory venv otherwise imports the old `temporal_memory`.
- Founder prefers very short, plain updates.
