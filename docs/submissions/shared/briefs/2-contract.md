# Brief P2 — Shared contract + cross-check · branch `contest-shared`

Suggested lead: **Antigravity** (any of Cursor / Muse / Codex / Antigravity works). Run this **after** both P1 planners have pushed (`societal` and `business` each contain `docs/submissions/<slug>/DELIVERY_ROADMAP.md`). Paste everything below the line into the lead agent.

---

You are the **shared-contract lead** for three Dubai Chambers contest entries that share one verified `user_id` and one memory service:
- Entry 1, Quest / Dubai-io, on `main` (another team);
- Entry 2, Dubai-io Community, on branch `societal`;
- Entry 3, Mirsal messenger, on branch `business`.

Two planning agents have each planned one entry. You **check both plans against each other and against the canon**, then write the **one contract** all three apps follow. You write docs only, no code.

## 0. Setup

- Local: `D:\Vscode\dubai-io-shared` (branch `contest-shared`). Cloud: `git fetch origin && git switch contest-shared`.
- Read the other branches **without switching to them**: `git show origin/societal:docs/submissions/community/<file>` and `git show origin/business:docs/submissions/mirsal/<file>`.
- Read the memory engine's contract the same way: `git show origin/memory:apps/memory/src/temporal_memory/models.py` and `git show origin/memory:apps/memory/CLAUDE.md`.
- **Never** commit to or push `main`. Never force-push. Commit only to `contest-shared`, and only under `docs/submissions/shared/` (never `founder-inputs/`).

## 1. Read

1. Root `CLAUDE.md` (rules 1–10 and the *Contest submissions* section), then `docs/submissions/CLAUDE.md`.
2. `docs/submissions/shared/founder-inputs/`: all three founder documents, verbatim.
3. Both P1 outputs: `audit.md`, `IMPLEMENTATION_GAP_MATRIX.md`, `DELIVERY_ROADMAP.md`, `identity-memory-needs.md` and `open-questions.md` from each branch, plus `ip-and-baseline.md` from `business`.
4. `PLAN.md` §1–§5 and `ARCHITECTURE.md` §7 (memory), §9 (security), §11–§14.
5. `apps/api/CLAUDE.md`; then `apps/api/app/auth.py`, the session and cookie code in `apps/api/app/actions.py`, `apps/api/app/memory/`, `apps/api/app/profile.py`, and the auth work on `origin/desktop` and `origin/ios` if any exists (`git grep -n -i "supabase\|jwt\|auth" origin/desktop -- apps/desktop`, and the same for `origin/ios` under `apps/mobile`).

## 2. Use subagents (read-only; each returns findings with `file:line`, commit or URL evidence)

- **Lane A: Identity.** What exists today: Google OAuth connections in `auth.py`, cookie sessions in `actions.py`. Bearer-token verification of Supabase Auth in FastAPI is *planned, absent* according to `apps/api/CLAUDE.md`. Does the desktop or iOS team already have an auth design? Propose one verified `user_id` for three apps (web, PWA and later desktop/iOS): token verification in FastAPI, session-to-`user_id` mapping, per-app sessions and capabilities, no account merge by display name, and the test list (two users, token expiry, a revoked session).
- **Lane B: Memory and consent.** Map the founder's "`MemoryBackend` + `ScopeGuard`" onto the real `GraphStore` protocol in `origin/memory` (`scoped_context`, `visible_facts`, …) and onto today's `apps/api/app/memory/` `mem_*` tables. Define:
  - the **write** path each app may use (source, actor, host, time, scope, trust tier, supersession, correction, Forget);
  - the **read** path each app may use (Community reads consented *interest features* only; Quest reads owner-scoped memories; Mirsal reads chat-scoped memories);
  - consent objects (per source, per app, per conversation: Off / Session only / Save approved memories);
  - revoke and Forget propagation, and the audit trail.
  Mark what depends on `memory` landing on `main` and what the bridge must fake until then.
- **Lane C: Cross-check the two plans.** Find contradictions between the Community and Mirsal plans: two inbox or messaging stacks (Community's founder spec says not to build two), duplicated tables, an identity assumed in different ways, overlapping agents. Then check each against canon rules 1–10, NEVER, D14, D15, the frozen `apps/web`, and the founder's "sequential, gated" delivery. Check that the Quest acceptance gates AC-1–AC-3 are preserved and not claimed as passed. For each finding: the conflict, the evidence, a recommended resolution, and who decides.
- **Lane D: Canon patch proposals.** Draft, *as proposals only*, the edits that `PLAN.md` (§1, §2 founder-decision log, §3 scope), `ARCHITECTURE.md` (identity, cross-app memory, messaging boundary) and `docs/status.md` need once the mains are merged. Each is a unified-diff-style snippet with its reason. Earlier decisions are kept as superseded history, never deleted. Do **not** apply them, and do not create `HANDOFF.md` (top-level `.md` rule).

## 3. Write (all under `docs/submissions/shared/`)

| File | Contents |
|---|---|
| `THREE_ENTRIES_OVERVIEW.md` | For each entry: identity, track fit, differentiator, agentic workflow, dependencies, demo criteria, and what is real vs fixture today |
| `SHARED_MEMORY_CROSS_APP_CONTRACT.md` | Identity contract; owner-scoped read/write policy per app; the message vs memory distinction; schemas and API signatures (Python types for `apps/api/app/identity/` and `apps/api/app/memory_bridge/`); consent and scope model; revoke, Forget and audit; and the contract tests that B0 must make pass |
| `shared-slices.md` | B0 build slices `CS-B1 … CS-Bn`. Each gives: goal; owned files (only `contest-shared` paths); depends-on; happy- and failure-path tests; which entry slices it unblocks |
| `cross-check.md` | Lane C's findings table, with the decision each finding needs |
| `canon-patches/PLAN.md.patch.md`, `canon-patches/ARCHITECTURE.md.patch.md`, `canon-patches/status.md.patch.md` | Lane D's proposals |
| `log.md` | `## <date> — P2 (<tool>)`: what you checked, what changed, top risks |

## 4. Finish

1. Commit on `contest-shared`: `docs(shared): P2 cross-app contract, cross-check and canon patch proposals`, then `git push origin contest-shared`.
2. Merge `contest-shared` into both entry branches (they never touch shared paths, so this should be clean). For `societal`: `git switch societal && git pull --ff-only && git merge --no-ff contest-shared && git push origin societal`. Do the same for `business`. On a conflict, stop and report it. In local worktrees, run these commands from `D:\Vscode\dubai-io-societal` and `D:\Vscode\dubai-io-business` instead of switching.
3. Final message to the founder (≤ 20 lines): commit hashes · the 5 most important cross-check findings · the decisions the founder must make now (each entry's blocking open questions, plus **M0** for Mirsal), each with your recommendation · what B0 builds first.
