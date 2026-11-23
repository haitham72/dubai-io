# Brief B0 — Shared build (identity + memory bridge) · branch `contest-shared`

Suggested lead: **Codex** (any of Cursor / Muse / Codex / Antigravity works). Paste everything below the line into the lead agent **only after** the founder has approved `shared/shared-slices.md` (its status line reads `approved — <date>`).

---

You are the **shared build lead** for three Dubai Chambers contest entries: Quest on `main`, Community on `societal`, the Messenger on `business`. You build the pieces all three share: one **verified `user_id`**, the **memory bridge** to the memory engine, **consent scopes**, and **Forget/revoke propagation**. Build exactly what `docs/submissions/shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md` specifies, and nothing app-specific.

## 0. Preconditions and setup

- Local: `D:\Vscode\dubai-io-shared`. Cloud: `git fetch origin && git switch contest-shared && git pull --ff-only`.
- **Stop** if `shared/shared-slices.md` is not `approved — <date>`.
- **Never** commit to or push `main`; never force-push. Lane branches are `cs/<slice-id>`, cut from `contest-shared`.
- Run the API suite once before any change and record the pass count in `docs/submissions/shared/log.md` as your baseline.

## 1. Read

Root `CLAUDE.md` · `docs/submissions/CLAUDE.md` (paths §2, gates §4) · `shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md` · `shared/shared-slices.md` · `shared/cross-check.md` · `ARCHITECTURE.md` §7, §9, §11 · `apps/api/CLAUDE.md` · the memory contract: `git show origin/memory:apps/memory/src/temporal_memory/models.py`.

## 2. Hard rules (paste this block into every subagent prompt)

```
- Work only on your lane branch cs/<slice-id>, cut from contest-shared. Never touch main.
- Write only: apps/api/app/identity/**, apps/api/app/memory_bridge/**, apps/api/tests/test_identity_*.py,
  apps/api/tests/test_memory_bridge_*.py, apps/api/tests/fixtures/contest_shared/**, docs/submissions/shared/** (not founder-inputs/).
  Everything else is read-only, especially apps/memory/** (another team's engine: never edit it, never fork it),
  apps/web/**, apps/site/**, PLAN.md, ARCHITECTURE.md, supabase/**, and every existing module in apps/api/app/.
- Do not build a second memory engine or a second facts table. The bridge calls the engine through its contract;
  until `memory` is on main, tests use a fake that implements the same protocol, and the fake is clearly named.
- The owner always comes from the verified token or session on the server; a caller can never set owner, scope or provenance.
- Consent is default-off; revoke and Forget take effect immediately and propagate to derived memories.
- Keys come from env only. Synthetic fixtures only. Every function: a happy-path AND a failure-path test.
- Report back: files changed, the exact test commands you ran WITH their output, anything left open.
```

## 3. Use subagents

At most 4 lanes in parallel, following `shared-slices.md`. Typical lanes:
- **Identity:** token verification, `user_id` resolution, per-app sessions, two-user isolation tests.
- **Bridge:** the client for the memory contract, the fake, write and read paths with provenance.
- **Consent and scopes:** per source, per app and per conversation; interest-feature export for Community.
- **Forget and audit:** revoke, Forget, audit log, propagation tests.

You merge each lane into `contest-shared` after **re-running** gates 1–3 (`docs/submissions/CLAUDE.md` §4) yourself.

## 4. Gate S, then hand over

Gate S passes when every contract test in `SHARED_MEMORY_CROSS_APP_CONTRACT.md` is green in your own run, the whole API suite is at or above the baseline, and two-user isolation is proven. Then:
1. Push `contest-shared`.
2. Merge it into `societal` and `business` (`git merge --no-ff contest-shared` in each; stop and report on a conflict).
3. Log the result in `shared/log.md`.

**Final message (≤ 15 lines):** slices merged with commit hashes · test counts vs the baseline · what is real vs faked (for example, the memory engine is faked until `memory` lands on `main`) · what each entry can now call · open risks.
