# Brief P1 — Plan · Dubai-io Community (Entry 2, Best Societal AI Agent) · branch `societal`

Suggested lead: **Codex** (any of Cursor / Muse / Codex / Antigravity works). It runs in parallel with the Mirsal planner on `business`. Paste everything below the line into the lead agent.

---

You are the **planning lead** for *Dubai-io Community*, our **Best Societal AI Agent** entry: a Facebook-style social network for Dubai with community agents (discovery, sourced answers, group organiser, moderation copilot). Git branch **`societal`** of `github.com/haitham72/dubai-io` (private). The founder's product spec already exists. **Check it against the real repo, then expand it into a build-ready plan.** You write docs only: no code, no build, no migrations.

## 0. Setup

- Local: `D:\Vscode\dubai-io-societal` (already on `societal`). Cloud: `git fetch origin && git switch societal`.
- Confirm `git branch --show-current` prints `societal`. If not, stop.
- **Never** switch to, commit to, or push `main`. Never force-push. Commit only to `societal`, and only under `docs/submissions/community/`.

## 1. Read (in this order)

1. Root `CLAUDE.md` (rules 1–10 and the *Contest submissions* section) → `docs/submissions/CLAUDE.md` (branches, paths, phases, gates)
2. **The spec:** `docs/submissions/shared/founder-inputs/02_DUBAI_IO_COMMUNITY_PLAN.md`. Never edit it; your files expand it.
3. The founder's ingest prompt `shared/founder-inputs/IDE_INGEST_TWO_SUBMISSIONS_PROMPT.md`. Do audit tasks **A–F for Community only**. The Mirsal planner does Mirsal, and P2 writes the shared files (`THREE_ENTRIES_OVERVIEW.md`, the shared memory contract).
4. The Mirsal spec `shared/founder-inputs/03_MIRSAL_AI_MESSENGER_PLAN.md`, sections 4–5 only (the shared identity and memory you must align with)
5. `PLAN.md` §1–§5, §7 · `ARCHITECTURE.md` §7, §9, §13, §15 · `apps/api/CLAUDE.md`
6. Code, as the lanes need it. Do not read `docs/archive/`.

## 2. Facts already checked (23 Nov, Claude Code). Re-verify; don't trust them blindly.

- **Community code exists, parked since 9 Nov, demo-grade** (decided 23 Oct):
  - `apps/api/app/communities.py` creates tables `personas`, `communities`, `community_members`, `posts`, `comments`, `hidden_posts`, `votes`, `chat_threads`, `chat_messages`, `chat_reads`. Seeded content is `provenance: demo_fixture`, and community text is untrusted and never becomes profile facts.
  - `apps/api/app/social_generation.py` exists.
  - Tests: `apps/api/tests/test_communities.py`, `test_social_generation.py`.
  - Endpoints are listed in `apps/api/CLAUDE.md` (*community (parked)*).
  - The `societal` branch now **owns** these two modules and their tests (`docs/submissions/CLAUDE.md` §2).
- **Reusable neighbours (read-only):**
  - `recommendations.py` / `discovery.py` (temporal ranker, owner-bound places)
  - `profile.py` (hypotheses with the two-visit rule)
  - `ml_*` (sentiment: `harsh` is *never* a moderation verdict)
  - `memory/` (`mem_*`)
  - `lab/sensitive.py` (fail-closed sensitive filter)
  - `actions.py` (approvals, idempotency, registered capabilities)
- **Identity:** there is no verified-JWT `user_id` yet. `auth.py` is Google OAuth connections; sessions are cookies in `actions.py`. Supabase Auth bearer verification is *planned, absent* (`apps/api/CLAUDE.md`). That is shared work (B0 on `contest-shared`): you only state your needs in `identity-memory-needs.md`.
- **Memory:** the engine is the other team's `apps/memory/` on branch `memory` (`git show origin/memory:apps/memory/src/temporal_memory/models.py`), not on `main` yet. `MEM-01` is unproven (AC-1). Community reaches memory only through the future `apps/api/app/memory_bridge/`.
- **Frozen reference:** `apps/web` (tag `mobile-pwa-baseline-2026-10-23`) may contain community screens. Read them, never edit them.

**Conflicts to resolve or raise:**
- (a) `PLAN.md` §1 says "not a social network … Persocial is a separate project". Is Dubai-io Community distinct from Persocial? This is a founder question.
- (b) The spec says don't build two messaging stacks, yet `communities.py` already has `chat_*` tables and Mirsal is the messenger. Recommend an Inbox boundary.
- (c) The spec mentions "the last four social mockups": find them in `design/` or say they're missing.
- (d) Societal-track fit: the spec's outcome is newcomers finding reliable local knowledge. Make that measurable.

## 3. Use subagents (read-only; each returns findings with `file:line` or URL evidence; the lead writes)

Paste into each: its lane text, the *Read-only* list from `docs/submissions/CLAUDE.md` §2, and "do not edit any file; do not switch branches; do not touch `apps/web`".

- **Lane A: Code audit (ingest task A, for Community).** Classify every community, social, recommendation and profile route and table as `working/tested`, `implemented but unverified`, `mock/fixture`, `planned` or `not found`. Run `cd apps/api && .venv/Scripts/python -m pytest -q tests/test_communities.py tests/test_social_generation.py` and cite the result. Map the spec's P0 tables (profiles, memberships, follows, posts, comments/reactions, media, notifications, moderation events, recommendation events) onto the existing schema, with no duplicates.
- **Lane B: Design authority and UX (ingest task B).** Find the approved social screens and mockups (`design/`, `apps/web` community screens, `apps/site`). List what can be reused and what must be original (no Meta look). Tabs per the spec: Feed / Communities / Create / Inbox / Profile. Note where the founder's visual review is needed.
- **Lane C: Trust, safety and privacy red-team (ingest tasks C, F).** Cover:
  - two-user isolation;
  - private groups;
  - AI drafts that publish only after approval of the exact revision and destination;
  - moderation that only flags, with a human resolution path;
  - cross-app leakage (no raw Quest chat, Gmail or Mirsal text in feed payloads);
  - minors, and third parties' details;
  - spam and fraud;
  - D14 (no bulk outreach).
  For each case: the expected behaviour, the rule, and the test that proves it.
- **Lane D: Societal evidence, demo and pitch (ingest task E).** Find official, quotable numbers on Dubai's newcomers and population growth, and on community or isolation challenges (Dubai Statistics Center, government sources), each with a URL and as-of date; anything else is labelled "reported". Write spec scenes A–D as a ≤ 4-minute script, marking `Demo data` and `Demo trigger`. Pick 2–3 outcome metrics. Outline a 10-slide deck with no claims of a Meta affiliation or of civic integrations.

## 4. Write (all under `docs/submissions/community/`)

| File | Contents |
|---|---|
| `audit.md` | What actually exists, with evidence and status labels (Lane A) |
| `IMPLEMENTATION_GAP_MATRIX.md` | For each spec feature: source evidence · reuse candidate · missing work · S/M/L · dependency · acceptance test |
| `DELIVERY_ROADMAP.md` | Build slices `CM-B1 … CM-Bn` in the spec's §8 order (A audit → B social core → C memory integration → D agentic demo → E polish). Each gives: owned files (only `societal` paths), depends-on (mark the slices that wait on B0 identity or memory), happy- and failure-path tests, and the demo beat it unlocks. The last slices are packaging: deck, video, hosting or tunnel, a multi-user test. Status line: `planned — awaiting founder approval (<date>, <tool>)` |
| `identity-memory-needs.md` | Exactly what Community needs from shared identity and memory: reads (consented interest features only), writes (saved discussions, joined groups, authored public posts with provenance), consent toggles, and Forget behaviour. P2 turns both entries' needs into one contract |
| `demo-script.md`, `sources.md` | Lane D's output |
| `open-questions.md` | At most **5 blocking** founder questions (the Persocial distinction, the Inbox boundary, …), each with a recommended answer, what it blocks and a deadline; non-blocking ones listed after |
| `log.md` | `## <date> — P1 (<tool>)`: what you checked, what changed, top risks |

## 5. Finish

- Commit on `societal`: `docs(community): P1 audit, gap matrix and delivery roadmap`, then `git push origin societal`. Never push `main`.
- Final message (≤ 15 lines): commit hash · what exists vs what is missing · top 5 risks · blocking questions, each with your recommendation.
- Then stop. P2 (`shared/briefs/2-contract.md`) cross-checks your plan against Mirsal's and writes the shared contract; the founder approves before any build.
