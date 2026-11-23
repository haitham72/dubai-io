# docs/submissions/ — Entries 2 and 3, and what they share

**Founder decision, 23 Nov 2026:** we enter three submissions. All three share **one verified `user_id`** and **one authorised long-term memory service**. Each still has its own app, its own agentic workflow and its own honest evidence (multiple applications are allowed: `docs/Researches/contest.md`, FAQ).

| # | Track | Entry | Branch | Folder |
|---|---|---|---|---|
| 1 | Best Personal AI Agent | Quest / Dubai-io: the ChatGPT-like memory companion; keep its plan and working code | `main` (the other PC's team) | repo root canon |
| 2 | **Best Societal AI Agent** | **Dubai-io Community**: the Facebook-like social network with community agents (replaces Persocial) | `societal` | `docs/submissions/community/` |
| 3 | **Best Business AI Agent** | **Messenger** (working name; final name pending): the WhatsApp-like AI messenger, built from the founder's own redesign features, with chat-to-action business agents | `business` | `docs/submissions/messenger/` |
| — | Shared base | Cross-app identity, memory bridge, consent scopes, the shared contract | `contest-shared` | `docs/submissions/shared/` |

**Read first: `shared/founder-decisions.md`** (the founder's answers of 23 Nov: the Messenger's IP and name, Persocial, the messaging boundary, the current design). It overrides anything below and anything in the founder inputs.

**Product specs (the founder's, filed unchanged; never edit them):** `shared/founder-inputs/02_DUBAI_IO_COMMUNITY_PLAN.md`, `shared/founder-inputs/03_MIRSAL_AI_MESSENGER_PLAN.md`, and `shared/founder-inputs/IDE_INGEST_TWO_SUBMISSIONS_PROMPT.md`. Those inputs still use the Messenger's old product name; that name is **retired** (`founder-decisions.md` D1) and must not be carried into anything new. The last is the founder's original single-agent ingest prompt; the briefs on these branches split its tasks between agents.

**What this supersedes, on these branches only** (`PLAN.md` itself is not edited here; proposed canon edits go to `shared/canon-patches/`):
- `PLAN.md` §1 "not a social network (community parked 9 Nov) … Persocial is a separate project": community is **unparked for Entry 2**, and Community **replaces Persocial**.
- `PLAN.md` §2 19 Nov, the "Entry 2 Business" line: the Business entry is now the **Messenger**, built from the founder's own redesign repo. The sticker *Builder service* (`D:\Vscode\mirsal-builder-io`) is **excluded**: its ownership is contested, so no code, prompts, design or data come from it (`founder-decisions.md` D6). ide-companio is superseded *for the contest portfolio only*; the project is kept.
- `PLAN.md` §2 19 Nov "single active focus on Entry 1": now three entries, delivered **sequentially and gated**, not all started at once (§3).

## 1. Branches and merge protocol (read before any git command)

```
origin/main @ f016856 (23 Nov) ── contest-shared ──┬── societal   (Entry 2: Community)
                                                   └── business   (Entry 3: Messenger)
```

- The other PC's `main` (the team building Dubai-io's iOS and desktop apps) is **far ahead of `origin/main` and not pushed yet**. It uses the rewritten **temporal_note** memory engine (D5). Its pushed branches (`desktop`, `ios`, `memory`) edit `CLAUDE.md`'s repo-layout block, `PLAN.md`, `docs/plan/`, `docs/request-backlog.md`, `apps/memory/`, `apps/desktop/`, `apps/mobile/` and `packages/design-tokens/`.
- **Zero-conflict rule:** these branches only **add new files in new folders**. The single edit to an existing file is the *Contest submissions* section appended at the very end of root `CLAUDE.md`; if that ever conflicts, keep both sides. Once the founder pushes a snapshot of the other PC's `main` to a non-`main` branch (for example `pc2-main`), gate 5 (§4) checks every merge against it.
- **Never** commit to `main`, push `main`, open a PR into `main`, or merge anything into `main`. Merging into `main` is a founder decision, made after the two `main`s are reconciled.
- **Never** force-push `contest-shared`, `societal` or `business`.
- **Shared work happens only on `contest-shared`.** Lane branches there are `cs/<slice>`. Entry branches take shared work with `git merge contest-shared`, and they **never edit shared paths** (§2). Entry branches are never merged into `contest-shared` or into each other.
- **Entry lane branches:** `cm/<slice>` (Community, from `societal`) and `mg/<slice>` (Messenger, from `business`). Don't name them `societal/...` or `business/...`: git cannot hold a branch `societal` and a branch `societal/x` at the same time.
- **Lane → its branch:** `--no-ff` merge (or a PR into that branch) only after the §4 gates pass. The lead agent merges; subagents never merge.
- **Taking `main` in, once the other PC pushes it:** first the shared lead runs `git fetch origin && git merge origin/main` into `contest-shared`; then each entry lead runs `git merge contest-shared`. If a conflict falls outside your own paths, **stop and report it to the founder**. Never resolve it by bending a shared file toward your entry.
- **Local worktrees (founder's PC):** `D:\Vscode\dubai-io-shared` (`contest-shared`), `D:\Vscode\dubai-io-societal` (`societal`), `D:\Vscode\dubai-io-business` (`business`). Cloud agents check out the branch from GitHub.
- **The founder's redesign repo** (`github.com/haitham72/Mirsal-redesign`, branch `master`; local clone `D:\Vscode\Mirsal-redesign`) is **read-only** for every agent. Never commit or push there without the founder's say-so. Its founder-authored code enters `apps/messenger/` only as a **rebranded snapshot**, after the founder confirms the M0 file list (`founder-decisions.md` D1). The URL and local path are the only places the old name may still appear.

## 2. Paths

**Own (write freely; nobody else writes there):**

| Branch | Code | Tests | Docs |
|---|---|---|---|
| `contest-shared` | `apps/api/app/identity/`, `apps/api/app/memory_bridge/` | `apps/api/tests/test_identity_*.py`, `test_memory_bridge_*.py`, `fixtures/contest_shared/` | `docs/submissions/CLAUDE.md`, `docs/submissions/shared/**` (except `founder-inputs/`), the *Contest submissions* section at the end of root `CLAUDE.md` |
| `societal` | `apps/community/` (web), `apps/api/app/community/` (all new backend code: agents, services, `cm_` tables) | `apps/api/tests/test_community_*.py`, `fixtures/community/` | `docs/submissions/community/**` |
| `business` | `apps/messenger/**` (only after the M0 list is confirmed), `apps/api/app/messenger/` (registered capabilities and approvals bridge into the Dubai-io action layer) | tests inside `apps/messenger/`, `apps/api/tests/test_messenger_*.py`, `fixtures/messenger/` | `docs/submissions/messenger/**` |

**Read-only (import, never edit):** `PLAN.md`, `ARCHITECTURE.md`, `README.md`, the rest of `CLAUDE.md`, `docs/status.md`, `docs/request-backlog.md`, `docs/plan/**`, `docs/services/**`, `docs/submissions/shared/founder-inputs/**`, `apps/web/**` (frozen, the reference), `apps/site/**`, `apps/dash/**`, `apps/ios/**`, `apps/memory/**`, `apps/desktop/**`, `apps/mobile/**`, `packages/**`, `supabase/**`, `scripts/**`, `design/**` (the Quest references are permanent), every existing module in `apps/api/app/`, including the parked `communities.py` and `social_generation.py` (import or read them, never edit them: the other PC's apps may still use them), and `main.py`, `config.py`, `actions.py`, `auth.py`, `merchant.py`, `tasks.py`, `proactive.py`, `profile.py`, `recommendations.py`, `luna/`, `connectors/`, `lab/`, `memory/` …), every existing test, and the other entry's paths.

- **DB:** new tables are prefixed `cs_` / `cm_` / `mg_`, created in code with `CREATE TABLE IF NOT EXISTS` (the pattern of `apps/api/app/tasks.py`). The parked tables in `communities.py` are never altered; Community creates its own `cm_` tables. **No new files in `supabase/migrations/`**: their timestamps collide with the other team's. RLS or Realtime SQL goes under the entry's own folder (for example `apps/messenger/supabase/`) and is listed in `open-questions.md` until the mains are merged.
- **No edits to existing files, not even one line.** Read new settings from env inside your own package. Register capability IDs into `actions.CAPABILITIES` from your own package at import time, and run your own FastAPI entrypoint (`app.community.server:app` on :8060, `app.messenger.server:app` on :8070) that includes the shared routers, so `main.py` is never edited. If something truly cannot work without changing an existing file, stop and put it in `open-questions.md`: only the founder can allow it.
- **Never build a second memory engine.** Memory is the rewritten **temporal_note** engine (D5): the other team's `apps/memory/`, package `temporal_memory`, with its HTTP API, MCP server and the `models.py` contract. It is on the pushed branch `memory`; the other PC's `main` may hold a newer rewrite. **Hindsight and Honcho are not used.** Where the founder specs say `MemoryBackend` or `ScopeGuard`, read temporal_note. Entries reach memory **only** through `apps/api/app/memory_bridge/`, a client of temporal_note.

## 3. Phases: sequential and gated

| Phase | Branch · brief | Output | Gate to the next phase |
|---|---|---|---|
| **P1 — Plan each entry** (2 agents in parallel) | `societal` · `community/briefs/1-plan.md`; `business` · `messenger/briefs/1-plan.md` | Per entry: `audit.md`, `IMPLEMENTATION_GAP_MATRIX.md`, `DELIVERY_ROADMAP.md`, `identity-memory-needs.md`, `demo-script.md`, `sources.md`, `open-questions.md`, `log.md`; plus `ip-and-baseline.md` for the Messenger | Both entry plans committed and pushed |
| **P2 — Shared contract + cross-check** (1 agent) | `contest-shared` · `shared/briefs/2-contract.md` | `shared/THREE_ENTRIES_OVERVIEW.md`, `shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md`, `shared/shared-slices.md`, `shared/cross-check.md`, `shared/canon-patches/*.md`; then merged into both entry branches | **Founder gate:** answers each entry's `open-questions.md` (≤ 5 blocking each), confirms the Messenger's **M0 file list** (founder-authored → keep; office-origin → exclude or rebuild) and picks its new name, and sets the status line of both roadmaps to `approved — <date>` |
| **B0 — Shared build** | `contest-shared` · `shared/briefs/3-build-shared.md` | Verified identity, memory bridge, consent scopes, forget propagation, contract tests | **Gate S:** contract tests green; merged into both entry branches |
| **B — Entry builds** | `societal` · `community/briefs/2-build.md`; `business` · `messenger/briefs/2-build.md` | Working apps, demos, packaging | Per slice: §4 gates. After the founder gate, each entry may start the slices that need neither shared identity nor memory; **slices that need them wait for Gate S**. The Messenger also needs its M0 file list confirmed. |

**Suggested roster** (swap freely; every brief runs in any of the four tools):

| Phase | Lead |
|---|---|
| P1 Community (`societal`) | **Muse** (taken over from Codex, 23 Nov) |
| P1 Messenger (`business`) | **Cursor**: done; then revised to D1–D6 (`messenger/briefs/1b-revise.md`) |
| P2 Shared contract + cross-check | **Antigravity** (Part A now, Part B after Community's plan) |
| B0 Shared build | **Antigravity** |
| B Community | **Muse** |
| B Messenger | **Cursor** |
| Reserve | **Codex**: slow and low quota, so only small tasks, and only when needed |

Cursor, Muse and Antigravity may all run long tasks and use subagents.

**Subagents are expected.** The lead keeps the plan and does every merge, fanning out to subagents (parallel agents, background agents, agent-manager tasks: whatever the tool offers; with none, run the lanes one after another):
- One lane per subagent, an explicit list of files it may write, and its own lane branch or worktree. Paste the §2 must-not-touch list into its prompt in full; "read the repo rules" is not enough.
- Planning subagents are **read-only**. They return findings with `file:line`, commit or URL evidence, and the lead writes the docs.
- Build subagents return the files they changed, the exact test commands they ran **with their output**, and anything left open. The lead **re-runs the tests itself** before merging; a report is not evidence.
- At most 4 lanes in parallel per branch, and two lanes never own the same file.

## 4. Gates (every merge into `contest-shared` / `societal` / `business`)

```sh
cd apps/api && .venv/Scripts/python -m pytest -q tests                # 1. whole API suite (Mac/Linux: .venv/bin/python)
git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web && echo "apps/web untouched"   # 2. frozen reference
git diff --name-only $(git merge-base HEAD origin/main) HEAD            # 3. only own paths
git merge-tree --write-tree HEAD origin/pc2-main >/dev/null && echo clean   # 5. once the other PC's main is pushed as pc2-main
# 4. the entry's app: its own test + build commands (apps/community: npm test && npm run build; apps/messenger: per its README)
```

- **Gate 3:** every printed path must be in your branch's *Own* row or a path inherited from `contest-shared`. Anything else fails, with no exceptions.
- **Gate 5:** when `origin/pc2-main` exists, a merge that conflicts with it stops; report it to the founder.
- Every workflow ships synthetic fixtures plus a happy-path **and** a failure-path test. No real personal data in the repo; real runs read from outside it (for example `G:\Haitham\lab-data\`).
- Hindsight's `AC-1` and `MEM-01` (`PLAN.md` §2) are not gates for these entries (D5). Never claim any memory test passed unless you ran it.

## 5. Rules for every entry

- Root `CLAUDE.md` rules 1–10 and `PLAN.md` §3 NEVER apply unchanged:
  - truthful statuses only; provenance and `as_of` on every number;
  - `Demo data` on seeded posts and messages;
  - approval of the exact payload before every external effect;
  - only registered actions execute;
  - no sensitive inference;
  - no official or third-party branding: no Meta, Facebook or WhatsApp marks, and no government emblems.
- `PLAN.md` §4 D14: no unsolicited or bulk messaging. D15: one explicit approval per side effect.
- **Messages are not memories.** A chat or post is a record of its own app; it becomes memory only through consented, source-linked extraction. Other people's messages are third-party content, never facts about the user. Feed ranking may read consented *interest features* only: never raw chats, mail, sensitive facts or family details.
- **Connectors:** WhatsApp by manual `Export chat` only; the Evolution/Baileys plugin stays off. No covert scraping. No Gemini API calls. No end-to-end-encryption claim unless it is implemented and independently assessed.
- **Messenger IP and name (D1):** the office owns the old product and its brand. Reuse only what the founder authored. No office code, logo, icon, graphics, copy or the old name goes into a submission. The old name must never appear in the UI, code identifiers, packages, routes, `@`-skills, deck, video or new docs. Docs may cite the redesign repo's own file paths so builders can find code, but never use the old name as the product's name. Gate for every Messenger merge: `git grep -n -i -e "m[i]rsal" -- apps/messenger apps/api/app/messenger` prints nothing. Nothing from the sticker Builder service is used (D6).
- **UI:** "UI paused 9 Nov" is about Dubai-io's `apps/site`; these entries need demo UIs. The founder's gate still applies: **no UI slice is done without founder visual review of a staged preview**. The Messenger keeps the founder's redesign visual language (the redesign repo's design spec and its 15 references; the 19 Nov **AI workspace** is current, D4), with original brand marks in place of the old ones. Community uses an original Dubai-io aesthetic and copies token values from `apps/site/app/globals.css` (noting the source) until `packages/design-tokens` is on `main`.
- Contest facts (read-only): `PLAN.md` §5. Internal target **Fri 18 Dec 2026** (deck, demo video, hosting or tunnel, small user test); the official submission is in January 2027, in English. Each deck stands alone.
- Progress goes into `docs/submissions/<slug>/log.md` (date, agent and tool, what changed, test summary, open items). Do not edit `docs/status.md` or `docs/request-backlog.md`, and do not create `HANDOFF.md`: root `CLAUDE.md` allows only four top-level `.md` files. Proposed canon edits go to `shared/canon-patches/`.
