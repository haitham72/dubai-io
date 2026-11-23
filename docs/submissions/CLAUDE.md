# docs/submissions/ — Entries 2 and 3, and what they share

**Founder decision, 23 Nov 2026:** we enter three submissions. All three share **one verified `user_id`** and **one authorised long-term memory service**. Each still has its own app, its own agentic workflow and its own honest evidence (multiple applications are allowed: `docs/Researches/contest.md`, FAQ).

| # | Track | Entry | Branch | Folder |
|---|---|---|---|---|
| 1 | Best Personal AI Agent | Quest / Dubai-io AI Companion: keep its plan and working code | `main` (the other PC's team) | repo root canon |
| 2 | **Best Societal AI Agent** | **Dubai-io Community**: Facebook-style social network with community agents | `societal` | `docs/submissions/community/` |
| 3 | **Best Business AI Agent** | **Mirsal**: WhatsApp-style AI messenger with chat-to-action business agents | `business` | `docs/submissions/mirsal/` |
| — | Shared base | Cross-app identity, memory bridge, consent scopes, the shared contract | `contest-shared` | `docs/submissions/shared/` |

**Product specs (the founder's, filed unchanged; never edit them):** `shared/founder-inputs/02_DUBAI_IO_COMMUNITY_PLAN.md`, `shared/founder-inputs/03_MIRSAL_AI_MESSENGER_PLAN.md`, and `shared/founder-inputs/IDE_INGEST_TWO_SUBMISSIONS_PROMPT.md`. The last is the founder's original single-agent ingest prompt; the briefs on these branches split its tasks between agents.

**What this supersedes, on these branches only** (`PLAN.md` itself is not edited here; proposed canon edits go to `shared/canon-patches/`):
- `PLAN.md` §1 "not a social network (community parked 9 Nov)": community is **unparked for Entry 2**.
- `PLAN.md` §2 19 Nov "Entry 2 Business = Mirsal Studio (`mirsal-builder-io`)": the Business entry is the **Mirsal messenger** (`haitham72/Mirsal-redesign`). `mirsal-builder-io` remains the sticker *Builder service* that Mirsal calls; it is a dependency, not the chat app. ide-companio is superseded *for the contest portfolio only*; the project is kept.
- `PLAN.md` §2 19 Nov "single active focus on Entry 1": now three entries, delivered **sequentially and gated**, not all started at once (§3).

## 1. Branches and merge protocol (read before any git command)

```
origin/main @ f016856 (23 Nov) ── contest-shared ──┬── societal   (Entry 2: Community)
                                                   └── business   (Entry 3: Mirsal)
```

- The other PC's `main` (the Quest / iOS / Electron team) is **ahead of `origin/main` and not pushed yet**. Its branches (`desktop`, `ios`, `memory`) edit `CLAUDE.md`'s repo-layout block, `PLAN.md`, `docs/plan/`, `docs/request-backlog.md`, `apps/memory/`, `apps/desktop/`, `apps/mobile/` and `packages/design-tokens/`. Everything below keeps these branches mergeable with that work.
- **Never** commit to `main`, push `main`, open a PR into `main`, or merge anything into `main`. Merging into `main` is a founder decision, made after the two `main`s are reconciled.
- **Never** force-push `contest-shared`, `societal` or `business`.
- **Shared work happens only on `contest-shared`.** Lane branches there are `cs/<slice>`. Entry branches take shared work with `git merge contest-shared`, and they **never edit shared paths** (§2). Entry branches are never merged into `contest-shared` or into each other.
- **Entry lane branches:** `cm/<slice>` (Community, from `societal`) and `ms/<slice>` (Mirsal, from `business`). Don't name them `societal/...` or `business/...`: git cannot hold a branch `societal` and a branch `societal/x` at the same time.
- **Lane → its branch:** `--no-ff` merge (or a PR into that branch) only after the §4 gates pass. The lead agent merges; subagents never merge.
- **Taking `main` in, once the other PC pushes it:** first the shared lead runs `git fetch origin && git merge origin/main` into `contest-shared`; then each entry lead runs `git merge contest-shared`. If a conflict falls outside your own paths, **stop and report it to the founder**. Never resolve it by bending a shared file toward your entry.
- **Local worktrees (founder's PC):** `D:\Vscode\dubai-io-shared` (`contest-shared`), `D:\Vscode\dubai-io-societal` (`societal`), `D:\Vscode\dubai-io-business` (`business`). Cloud agents check out the branch from GitHub.
- **The Mirsal source repo** `github.com/haitham72/Mirsal-redesign` (branch `master`; local clone `D:\Vscode\Mirsal-redesign`) is **read-only** for every agent. Never commit or push there without the founder's say-so. Its code enters `apps/mirsal/` only after gate **M0 = go** (§3).

## 2. Paths

**Own (write freely; nobody else writes there):**

| Branch | Code | Tests | Docs |
|---|---|---|---|
| `contest-shared` | `apps/api/app/identity/`, `apps/api/app/memory_bridge/` | `apps/api/tests/test_identity_*.py`, `test_memory_bridge_*.py`, `fixtures/contest_shared/` | `docs/submissions/CLAUDE.md`, `docs/submissions/shared/**` (except `founder-inputs/`), the *Contest submissions* section at the end of root `CLAUDE.md` |
| `societal` | `apps/community/` (web), `apps/api/app/community/` (new agents and services), and the **parked** `apps/api/app/communities.py` + `apps/api/app/social_generation.py` (parked on `main` since 9 Nov; no other branch touches them; commit prefix `community(api):`) | `apps/api/tests/test_community_*.py`, the existing `test_communities.py` + `test_social_generation.py`, `fixtures/community/` | `docs/submissions/community/**` |
| `business` | `apps/mirsal/**` (only after M0), `apps/api/app/mirsal/` (registered capabilities and approvals bridge into the Dubai-io action layer) | tests inside `apps/mirsal/`, `apps/api/tests/test_mirsal_*.py`, `fixtures/mirsal/` | `docs/submissions/mirsal/**` |

**Read-only (import, never edit):** `PLAN.md`, `ARCHITECTURE.md`, `README.md`, the rest of `CLAUDE.md`, `docs/status.md`, `docs/request-backlog.md`, `docs/plan/**`, `docs/services/**`, `docs/submissions/shared/founder-inputs/**`, `apps/web/**` (frozen, the reference), `apps/site/**`, `apps/dash/**`, `apps/ios/**`, `apps/memory/**`, `apps/desktop/**`, `apps/mobile/**`, `packages/**`, `supabase/**`, `scripts/**`, `design/**` (the Quest references are permanent), every other existing module in `apps/api/app/` (`main.py`, `config.py`, `actions.py`, `auth.py`, `merchant.py`, `tasks.py`, `proactive.py`, `profile.py`, `recommendations.py`, `luna/`, `connectors/`, `lab/`, `memory/` …), every existing test not listed above, and the other entry's paths.

- **DB:** new tables are prefixed `cs_` / `cm_` / `ms_`, created in code with `CREATE TABLE IF NOT EXISTS` (the pattern of `apps/api/app/tasks.py`). The existing community tables in `communities.py` may evolve on `societal`. **No new files in `supabase/migrations/`**: their timestamps collide with the other team's. RLS or Realtime SQL goes under the entry's own folder (for example `apps/mirsal/supabase/`) and is listed in `open-questions.md` until the mains are merged.
- **Shared-change exception:** an unavoidable edit to a read-only file is the smallest possible change, alone in a `shared(<area>):` commit, with a test, and logged in `docs/submissions/<slug>/shared-changes.md` with the reason. Prefer extension: register capability IDs into `actions.CAPABILITIES` from your own package, and run your own FastAPI entrypoint (`app.community.server:app` on :8060, `app.mirsal.server:app` on :8070) that includes the shared routers, so `main.py` is never edited.
- **Never build a second memory engine.** The memory engine is the other team's `apps/memory/` (branch `memory`, contract `apps/memory/src/temporal_memory/models.py`, `GraphStore` protocol). The founder specs call its interface "`MemoryBackend` + `ScopeGuard`"; the P2 contract maps those names to it. Entries reach memory **only** through `apps/api/app/memory_bridge/`.

## 3. Phases: sequential and gated

| Phase | Branch · brief | Output | Gate to the next phase |
|---|---|---|---|
| **P1 — Plan each entry** (2 agents in parallel) | `societal` · `community/briefs/1-plan.md`; `business` · `mirsal/briefs/1-plan.md` | Per entry: `audit.md`, `IMPLEMENTATION_GAP_MATRIX.md`, `DELIVERY_ROADMAP.md`, `identity-memory-needs.md`, `demo-script.md`, `sources.md`, `open-questions.md`, `log.md`; plus `ip-and-baseline.md` for Mirsal | Both entry plans committed and pushed |
| **P2 — Shared contract + cross-check** (1 agent) | `contest-shared` · `shared/briefs/2-contract.md` | `shared/THREE_ENTRIES_OVERVIEW.md`, `shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md`, `shared/shared-slices.md`, `shared/cross-check.md`, `shared/canon-patches/*.md`; then merged into both entry branches | **Founder gate:** answers each entry's `open-questions.md` (≤ 5 blocking each), decides **M0** (Mirsal IP: reuse / clean-room / no-go), and sets the status line of both roadmaps to `approved — <date>` |
| **B0 — Shared build** | `contest-shared` · `shared/briefs/3-build-shared.md` | Verified identity, memory bridge, consent scopes, forget propagation, contract tests | **Gate S:** contract tests green; merged into both entry branches |
| **B — Entry builds** | `societal` · `community/briefs/2-build.md`; `business` · `mirsal/briefs/2-build.md` | Working apps, demos, packaging | Per slice: §4 gates. Community's social core may start during B0 (it doesn't need cross-app identity). **Mirsal starts only after M0 is decided and Gate S passes.** |

**Suggested roster** (swap freely; every brief runs in any of the four tools):

| Phase | Lead |
|---|---|
| P1 Community (`societal`) | Codex |
| P1 Mirsal (`business`) | Cursor |
| P2 Shared contract + cross-check | Antigravity |
| B0 Shared build | Codex |
| B Community | Antigravity |
| B Mirsal | Muse |

A tool that isn't the lead can serve as a subagent lane.

**Subagents are expected.** The lead keeps the plan and does every merge, fanning out to subagents (parallel agents, background agents, agent-manager tasks: whatever the tool offers; with none, run the lanes one after another):
- One lane per subagent, an explicit list of files it may write, and its own lane branch or worktree. Paste the §2 must-not-touch list into its prompt in full; "read the repo rules" is not enough.
- Planning subagents are **read-only**. They return findings with `file:line`, commit or URL evidence, and the lead writes the docs.
- Build subagents return the files they changed, the exact test commands they ran **with their output**, and anything left open. The lead **re-runs the tests itself** before merging; a report is not evidence.
- At most 4 lanes in parallel per branch, and two lanes never own the same file.

## 4. Gates (every merge into `contest-shared` / `societal` / `business`)

```sh
cd apps/api && .venv/Scripts/python -m pytest -q tests                # 1. whole API suite (Mac/Linux: .venv/bin/python)
git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web && echo "apps/web untouched"   # 2. frozen reference
git diff --name-only $(git merge-base HEAD origin/main) HEAD            # 3. only own paths (+ logged shared(...) commits)
# 4. the entry's app: its own test + build commands (apps/community: npm test && npm run build; apps/mirsal: per its README)
```

- **Gate 3:** every printed path must be in your branch's *Own* row, in a path inherited from `contest-shared`, or in `shared-changes.md`. Anything else fails.
- Every workflow ships synthetic fixtures plus a happy-path **and** a failure-path test. No real personal data in the repo; real runs read from outside it (for example `G:\Haitham\lab-data\`).
- Do not claim the memory gates `AC-1`, `AC-2` or `AC-3` (`PLAN.md` §2) passed unless you ran them; `MEM-01` is unproven until AC-1 is green.

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
- **Mirsal IP:** no office- or client-owned code, design, graphics or brand goes into a submission without written rights (M0). Public visibility on GitHub does not prove ownership.
- **UI:** "UI paused 9 Nov" is about Dubai-io's `apps/site`; these entries need demo UIs. The founder's gate still applies: **no UI slice is done without founder visual review of a staged preview**. Mirsal keeps its approved visual language (`Mirsal-redesign.md`, its 15 references). Community uses an original Dubai-io aesthetic and copies token values from `apps/site/app/globals.css` (noting the source) until `packages/design-tokens` is on `main`.
- Contest facts (read-only): `PLAN.md` §5. Internal target **Fri 18 Dec 2026** (deck, demo video, hosting or tunnel, small user test); the official submission is in January 2027, in English. Each deck stands alone.
- Progress goes into `docs/submissions/<slug>/log.md` (date, agent and tool, what changed, test summary, open items). Do not edit `docs/status.md` or `docs/request-backlog.md`, and do not create `HANDOFF.md`: root `CLAUDE.md` allows only four top-level `.md` files. Proposed canon edits go to `shared/canon-patches/`.
