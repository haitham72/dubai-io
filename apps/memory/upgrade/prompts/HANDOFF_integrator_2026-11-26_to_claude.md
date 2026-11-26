# Lead Integrator Handoff — Gemini/Hydrogen to Claude (2026-11-26 10:01 Dubai)

## 1. Role Transfer & Authoritative References
- **Transfer:** Lead integrator role hands off from **Gemini/Hydrogen** to **Claude** as of `2026-11-26 10:01 Dubai`.
- **Canonical references:**
  - Root `CLAUDE.md`
  - `docs/submissions/shared/founder-decisions.md` (`D3`, `D11`, `D14`, `D16`–`D22`, `D19b`)
  - `apps/memory/upgrade/prompts/wave_2026-11-26/WAVE_PLAN_2026-11-26.md`
  - Prior handoffs: `HANDOFF_integrator_2026-11-25.md`, `HANDOFF_integrator_2026-11-25b.md`, `HANDOFF_integrator_2026-11-25c_EOD.md`

---

## 2. State of `main` (at `b3f9e76` + this handoff)
- **`95fca3a`** — `feat(lan): derive LAN API host for iPhone testing + 2026-11-26 multi-agent wave prompts`
  - Removed 22 stale folders (14 worktrees + 8 leftover non-git dirs; kept `contest`, `contest-e13a`, `contest-e13b`, `contest-e14-community`, `contest-memory`, `e6-logs`).
  - Added LAN API URL fallback in Community & Messenger.
  - Committed `apps/memory/upgrade/prompts/wave_2026-11-26/`.
- **`b3f9e76`** — `fix(lan): drop localhost overrides in start-all, add iPhone pairing-code UI, apply Claude Phase A wave fixes`
  - Applied Claude Phase A fixes on `main`:
    - `scripts/dev/start-all.ps1`: dropped `localhost` env overrides for `community_web` and `messenger_web`, and checks all 8 firewall ports (`8000, 8081, 8060, 3060, 8070, 5173, 8082, 8083`).
    - Loopback-on-LAN host rewrite in Community & Messenger.
    - 6-character `"Pair with PC code"` sign-in (`POST /api/identity/pair/complete`) added to `apps/community/src/app/signin/page.tsx` and `apps/messenger/src/profile/settings/tabs.tsx`.
    - Patched all 5 files in `apps/memory/upgrade/prompts/wave_2026-11-26/` for Claude A1/A2/A3.
  - Verified on `b3f9e76`:
    - `apps/community`: 45/45 Vitest + `tsc` + `next build`
    - `apps/messenger`: typecheck + store-wiring 10/10 + photo-window 4/4 + memory UI 10 + 13/13
    - `scripts/dev/start-all.ps1`: parse OK
    - `apps/web` frozen check (`git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web`): exit `0`

---

## 3. Local Sandbox PC Readiness
- **`apps/api/.env` (gitignored, never printed or committed):** Populated and live-verified:
  - `sqlite_mode=True` (with offline `:15422` `DATABASE_URL` preserved as a `#` comment).
  - Google OAuth `installed` client configured from `client_secret_...json` / `.env.gcloud` (`project-07b22836-51d8-4193-9de`).
  - Callback URIs `/api/identity/google/callback` and `/api/ingest/google/callback` configured and verified.
  - Fresh Fernet `OAUTH_TOKEN_KEY` and `IDENTITY_TOKEN_KEY` generated; `TM_ADMIN_TOKEN` synced from `apps/memory/.env`.
  - Existing OpenAI, Places, SerpAPI, Finnhub, Tavily, and `TM_SERVICE_TOKEN` entries preserved.
- **Controlled same-network Wi-Fi testing policy:**
  - No Cloudflare Tunnel / HTTPS for this phase.
  - Physical iPhone pairs via PC Chrome Profile #2 -> **Pair iPhone** -> 6-character code across all 3 apps.
  - **Founder-only remaining steps to start live testing:**
    1. Start Docker Desktop.
    2. Verify Gmail / Calendar / YouTube APIs + Test Users in Google Cloud Console.
    3. Run `powershell -ExecutionPolicy Bypass -File scripts\dev\start-all.ps1 -Shells`.

---

## 4. Active In-Flight Queue & Next Actions for Claude (Strict Merge Order)

### 1) PR #11 — E14 (`e14/community-replica-recommender`, Cursor, `G:\Haitham\VsCode\contest-e14-community`)
- **Current state:** Open PR #11 at remote `e00f978`; local HEAD `d0fe9a0` + 6 dirty files (Cursor actively fixing blockers).
- **Review findings:** Claude's untracked `apps/memory/upgrade/reports/E14.review.md` in `G:\Haitham\VsCode\contest` holds **`BLOCKERS` (B1–B4 + S1–S5)**.
- **Next actions:**
  1. Wait for Cursor to push fixes and rebase onto `b3f9e76` (preserving LAN helpers + `"Pair with PC code"` UI).
  2. Re-verify all gates and update `apps/memory/upgrade/reports/E14.review.md`.
  3. **Get founder visual preview approval (`D11`/`D14`)** before merging.
  4. Commit `E14.review.md` and merge `--no-ff` into `main`.

### 2) E13a (`e13a/lower-and-delete`, Codex, `G:\Haitham\VsCode\contest-e13a`)
- **Current state:** Local `ddee1d8` (merged `origin/main`) + 14 dirty files (remote `b0785c3`). Actively fixing `D19b` + Claude A2 defects `E1`–`E7` + `:5442` `schema_migrations` version `8` check (`0008` vs `0010`).
- **Next actions:**
  1. Verify and write `apps/memory/upgrade/reports/E13a.review.md`:
     - Postgres `:5442` suite via `G:\Haitham\VsCode\contest-memory\apps\memory\.venv`
     - `apps/api` suite with `DATABASE_URL` unset
     - Client memory suites
     - `apps/web` frozen check
  2. Merge `--no-ff` into `main` (after E14).
  3. Verify `delete-my-data` invokes E14's `purge_owner_community_data` hook once both E14 and E13a are on `main`.

### 3) E13b (`e13b/shared-vocab-agent`, Muse, `G:\Haitham\VsCode\contest-e13b`)
- **Current state:** At `95fca3a` + 2 dirty files. Actively building migration `0009_shared_vocab_proposals.sql`, `vocab/similarity.py`, `vocab/shared_proposer.py`, `api/vocab_admin.py`, E10 cleanups, and Claude A1 #4/#5 privacy fixes (HMAC-SHA256 `TM_SIGNAL_HMAC_KEY`, user-typed queries only, Google Limited Use filter on `learned_terms`, deleted-owner exclusion).
- **Next actions:**
  1. Have Muse rebase onto `main` **after E13a merges**.
  2. Verify and write `apps/memory/upgrade/reports/E13b.review.md` + full Postgres `:5442` suite.
  3. Merge `--no-ff` into `main`.

### 4) Post-Wave & Deferred Items
- **Post-merge cross-app smoke:** Run end-to-end verification across all 3 apps once E14, E13a, and E13b are on `main`.
- **GrepMem WhatsApp pilot** (`docs/submissions/shared/research/grepmem-whatsapp-pilot-plan.md`, untracked, deferred post-wave): qualifies **only** if a 24-prompt pilot achieves `>= 3` hits or `>= 25%` latency drop with `0` scope failures, plus `D19`/`D19b`, `Delete my data`, Rule 9, and zero auto-writes.
- **Pre-submission backlog (non-blocking for this wave):**
  - S2 extraction cost (`$0.00514/d` vs `$0.0044` target)
  - Historical S2 `7/8` supersession gate
  - Synthetic Account B chat `cited=0`
  - Cloudflare Tunnel (`D13`) later
  - `5+` adult user test
  - Pitch decks & demo videos

---

## 5. Untracked Items in `G:\Haitham\VsCode\contest` & Hard Guardrails

### Untracked Items to Preserve (Do NOT stage/delete unless explicitly directed)
1. `apps/memory/upgrade/reports/E14.review.md` *(commit only when merging E14)*
2. `docs/submissions/shared/research/grepmem-whatsapp-pilot-plan.md`
3. `env (2)`
4. `apps/community/tsconfig.tsbuildinfo`
5. `apps/desktop/renderer/dist/`
6. `design/20-11-2026/Dubai-io Quest Milestones Showcase.jpg` *(founder file)*
7. `docs/Researches/new tools research.md` *(founder file)*
8. `docs/plan/Memory/deepseek_markdown_20261124_fbeb70.md` *(founder file)*

- **Retained sibling directory:** `G:\Haitham\VsCode\contest-memory` (**KEEP** — holds full `apps/memory\.venv` used for `:5442` Postgres verification).

### Hard Guardrails
- `apps/web` is **frozen** (`git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` must exit `0`).
- **No force-push** on any branch.
- **No worktree, folder, or branch deletions** without explicit founder approval.
- **Never print, log, or commit `.env*` values or secrets.**
- **Never stage founder untracked files or build outputs** (`apps/desktop/renderer/dist/`, `apps/community/tsconfig.tsbuildinfo`).
- **Plain, short founder updates** (`D3`/`D11`/`D14` visual preview approval before merging UI waves).
