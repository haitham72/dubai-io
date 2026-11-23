# Brief P2 — Shared contract + cross-check · branch `contest-shared`

Suggested lead: **Antigravity**. P2 runs in two parts:
- **Part A runs now.** It needs only the finished Messenger plan (`business`) and the founder's Community spec.
- **Part B** (§5) is a short follow-up. Paste it when the Community plan has landed on `societal` (`docs/submissions/community/DELIVERY_ROADMAP.md` exists).

Paste everything below the line into the lead agent.

---

You are the **shared-contract lead** for three Dubai Chambers contest entries that share one verified `user_id` and one memory service:
- Entry 1, Quest / Dubai-io (the ChatGPT-like companion), on `main`. Another team builds its iOS and desktop apps on another PC; its `main` is far ahead of `origin/main`.
- Entry 2, Dubai-io Community (Facebook-like), on branch `societal`. Its plan is still being written.
- Entry 3, the Messenger (WhatsApp-like), on branch `business`. Its plan is done.

You write the **one contract** all three apps follow and cross-check the plans against it and against the canon. You write docs only, no code.

## 0. Setup

- Local: `D:\Vscode\dubai-io-shared` (branch `contest-shared`). Cloud: `git fetch origin && git switch contest-shared`.
- Read other branches **without switching to them**: `git show business:docs/submissions/messenger/<file>`. In a cloud checkout, use `origin/business:`.
- **Never** commit to or push `main`, and never force-push. Commit only to `contest-shared`, and only under `docs/submissions/shared/` (never `founder-inputs/`). Do not edit any other file in the repo.

## 1. Read

1. `docs/submissions/shared/founder-decisions.md`. It overrides everything else, especially:
   - **D5:** memory is the rewritten **temporal_note** engine, not Hindsight or Honcho.
   - **D3:** the Messenger owns all person-to-person messaging.
2. Root `CLAUDE.md` (rules 1–10 and the *Contest submissions* section) → `docs/submissions/CLAUDE.md`.
3. `docs/submissions/shared/founder-inputs/`, all three documents. They predate D1–D5: where they say Hindsight, `MemoryBackend` or `ScopeGuard`, read *temporal_note*.
4. The Messenger plan on `business`: `docs/submissions/messenger/` (`identity-memory-needs.md`, `open-questions.md`, `DELIVERY_ROADMAP.md`, `ip-and-baseline.md`, `audit.md`).
5. **The temporal_note engine** (read-only, from branch `memory`):
   - `git show origin/memory:apps/memory/README.md`;
   - then `src/temporal_memory/models.py` (the contract, `GraphStore`), `api/app.py`, `api/vault.py`, `mcp/server.py`, `mcp/tokens.py`, `privacy/forget.py`, `live/context.py` and `apps/memory/CLAUDE.md`. Use the same `git show origin/memory:apps/memory/<path>` form for each.
   
   The other PC's `main` may hold a newer rewrite. If a branch with that work exists on origin (`git branch -r`), prefer it and say which you used.
6. `PLAN.md` §1–§5, `ARCHITECTURE.md` §7, §9, §11–§14, `apps/api/CLAUDE.md`, `apps/api/app/auth.py`, and the session code in `apps/api/app/actions.py`. Check auth on the other team's branches too: `git grep -n -i "supabase\|jwt\|auth" origin/desktop -- apps/desktop`, and the same on `origin/ios` under `apps/mobile`.

## 2. Use subagents (read-only; each returns findings with `file:line`, commit or URL evidence; you write)

- **Lane A: Identity.** Today `auth.py` provides Google OAuth connections and `actions.py` provides anonymous cookie sessions. Bearer-token verification is *planned, absent*. Does the desktop or iOS team already have an auth design? If so, adopt it rather than inventing a second one. Propose one verified `user_id` for three apps:
  - token verification in FastAPI and session-to-`user_id` mapping;
  - per-app sessions and capabilities, with no account merge by display name;
  - how temporal_note's MCP tokens (`mcp/tokens.py`) relate to that `user_id`;
  - the test list: two users, token expiry, a revoked session.
- **Lane B: Memory and consent against temporal_note.** Design `apps/api/app/memory_bridge/` as a **client of temporal_note's HTTP API or MCP**, never a second engine. Define:
  - the **write** path: source, actor, host, time, scope, trust tier, supersession, correction, Forget;
  - the **read** path per app: Community reads consented *interest features* only; Quest reads owner-scoped memories; the Messenger reads chat-scoped memories;
  - consent objects: per source, per app, per conversation (Off / Session only / Save approved memories);
  - Forget and revoke propagation (`privacy/forget.py`, the generation fence) and the audit trail.
  
  Mark what the bridge must fake until temporal_note is on `main`; the fake implements the same interface and is clearly named. `apps/api/app/memory/` (`mem_*`) is Entry 1's existing store: read-only, not a target.
- **Lane C: Cross-check.** Check the Messenger plan, and the Community **spec**, against D1–D5, canon rules 1–10, NEVER, D14, D15, the frozen `apps/web`, and "sequential, gated" delivery. Look especially for:
  - person-to-person messaging in Community;
  - the retired name used as a product name;
  - edits to existing files (forbidden: `docs/submissions/CLAUDE.md` §2);
  - duplicated tables, and identity assumed in different ways;
  - Hindsight-era assumptions, such as treating the Hindsight AC-1 gate as a gate for these entries.
  
  Settle the Messenger's open question on transport (its recommendation: a cookie-authenticated FastAPI WebSocket until B0 identity exists) or pass it to the founder. Record each finding as: conflict · evidence · recommended resolution · who decides.
- **Lane D: Canon patch proposals.** Draft, *as proposals only*, the edits that `PLAN.md` (§1, the §2 decision log, §3 scope), `ARCHITECTURE.md` (identity, cross-app memory via temporal_note, the messaging boundary) and `docs/status.md` will need once the mains are merged. Also draft the one-section `CLAUDE.md` mention. Each is a diff-style snippet with its reason. Earlier decisions stay as superseded history. Never apply them, and never create `HANDOFF.md`.

## 3. Write (all under `docs/submissions/shared/`)

| File | Contents |
|---|---|
| `THREE_ENTRIES_OVERVIEW.md` | For each entry: identity (ChatGPT-like / Facebook-like / WhatsApp-like), track fit, differentiator, agentic workflow, dependencies, demo criteria, and what is real vs fixture today |
| `SHARED_MEMORY_CROSS_APP_CONTRACT.md` | Identity contract; the read/write policy per app; message vs memory; Python signatures for `apps/api/app/identity/` and `apps/api/app/memory_bridge/` (bridge → temporal_note API/MCP); consent and scopes; Forget, revoke and audit; **the contract tests B0 must make pass**. Status line: `draft — awaiting Community needs (P2 Part B)` |
| `shared-slices.md` | B0 slices `CS-B1 … CS-Bn`. Each gives: goal; owned files (only `contest-shared` paths); depends-on; happy- and failure-path tests; which entry slices it unblocks |
| `cross-check.md` | Lane C's findings (the Messenger now; Community added in Part B) |
| `canon-patches/*.patch.md` | Lane D's proposals |
| `log.md` | `## <date> — P2 Part A (<tool>)`: what you checked, what changed, top risks |

## 4. Finish Part A

- Commit on `contest-shared`: `docs(shared): P2 part A — contract draft, Messenger cross-check, canon patch proposals`, then push `contest-shared` (`git push origin contest-shared`; if pushing is not allowed in your tool, say so).
- Final message to the founder (≤ 15 lines): commit hash · top 5 findings · decisions needed now, each with your recommendation · what B0 builds first.
- Do not merge into `societal` yet: another agent is working there. Part B does that.

## 5. Part B (pasted later, when the Community plan has landed)

> Community's plan is now on `societal` (`docs/submissions/community/`). Read its `identity-memory-needs.md`, `open-questions.md` and `DELIVERY_ROADMAP.md`. Fold Community's needs into `SHARED_MEMORY_CROSS_APP_CONTRACT.md` and set its status to `ready for founder approval`. Add the Community rows to `cross-check.md`, and update `shared-slices.md` and `log.md` (`P2 Part B`). Commit with `docs(shared): P2 part B — Community folded into the contract`. Then merge `contest-shared` into both entry branches: in `D:\Vscode\dubai-io-societal` and `D:\Vscode\dubai-io-business` (or after `git switch` in the cloud), run `git merge --no-ff contest-shared`, then push each. On any conflict, stop and report it. Final message (≤ 15 lines): what changed and the founder's decision list for the gate.
