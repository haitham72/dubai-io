# Brief P1 — Plan · Mirsal AI Messenger (Entry 3, Best Business AI Agent) · branch `business`

Suggested lead: **Cursor** (any of Cursor / Muse / Codex / Antigravity works). It runs in parallel with the Community planner on `societal`. Paste everything below the line into the lead agent.

---

You are the **planning lead** for *Mirsal*, our **Best Business AI Agent** entry. Mirsal is a WhatsApp-style AI messenger whose business agents turn team chat into confirmed decisions, tracked tasks and cited briefs. It lives on git branch **`business`** of `github.com/haitham72/dubai-io` (private). The founder's product spec exists, and an existing visual/agent proof of concept lives in a **separate repo**. **Audit both, settle the IP question's evidence, then expand the spec into a build-ready plan.** You write docs only: no code, no import, no build.

## 0. Setup

- Local: `D:\Vscode\dubai-io-business` (already on `business`). Cloud: `git fetch origin && git switch business`.
- **The Mirsal POC:** `github.com/haitham72/Mirsal-redesign`, branch `master`, **read-only**. Locally it is already cloned at `D:\Vscode\Mirsal-redesign` (last commit `6b45ba4`, 19 Nov). To run its tests, use a **separate throwaway clone** (`git clone https://github.com/haitham72/Mirsal-redesign <scratch dir>`). Never commit, push or open PRs there, and never copy its files into `dubai-io`.
- **Mirsal Builder:** `D:\Vscode\mirsal-builder-io` is the sticker/emoji *Builder service* that Mirsal calls. It is a dependency, **not** the chat app. Read-only.
- **Never** switch to, commit to, or push `main`. Never force-push. Commit only to `business`, and only under `docs/submissions/mirsal/`.

## 1. Read (in this order)

1. Root `CLAUDE.md` (rules 1–10 and the *Contest submissions* section) → `docs/submissions/CLAUDE.md` (branches, paths, phases, the **M0** IP gate)
2. **The spec:** `docs/submissions/shared/founder-inputs/03_MIRSAL_AI_MESSENGER_PLAN.md`. Never edit it; your files expand it.
3. The founder's ingest prompt `shared/founder-inputs/IDE_INGEST_TWO_SUBMISSIONS_PROMPT.md`. Do audit tasks **A–F for Mirsal only**. The Community planner does Community; P2 writes the shared files.
4. The Community spec `shared/founder-inputs/02_DUBAI_IO_COMMUNITY_PLAN.md`, §2 *Inbox* and §4–5 only (the boundary between the two apps' messaging, and the shared memory)
5. In the Mirsal repo: `README.md`, `ARCHITECTURE.md`, `Mirsal-redesign.md`, `CLAUDE.md`, `src/screens.ts`, `src/chats/data.ts`, `src/store.ts`, `src/mobile/`, `src/updates/`, `src/voice/`, `agents/mirsal_agents/`, `api/`, `server/`, `Slides/output_grid/`, `screens/`
6. In `dubai-io`: `PLAN.md` §1–§5, §7 · `ARCHITECTURE.md` §2, §3, §7, §9, §11, §14 · `apps/api/CLAUDE.md` · `apps/api/app/actions.py` (the approval and capability layer Mirsal's external actions must pass through)

## 2. Facts already checked (23 Nov, Claude Code). Re-verify.

- The spec itself says the POC is **a clickable investor demo, not a multi-user messenger**:
  - seeded chats in `src/chats/data.ts`, and `src/store.ts` starts from `seedMessages`;
  - `/agents/memory/*` is a Redis/in-process facts store, **not** Hindsight;
  - pgvector is used for *photo search only*;
  - its reported tests (169 offline passes + 1 Redis skip, plus 10 cleaner tests) were **not** rerun.
- **Possible conflict:** the spec says to *preserve the compact Mirsal Updates tray*, but the POC's latest commit (`6b45ba4`, 19 Nov) is titled "Mirsal AI workspace replaces Updates tray". Find out which is current and raise it if they disagree.
- No verified-JWT `user_id` exists in `dubai-io` yet (`auth.py` = Google OAuth connections; cookie sessions in `actions.py`). Shared identity and memory are **B0 work on `contest-shared`**: you only state Mirsal's needs.
- The memory engine is the other team's `apps/memory/` on branch `memory` (`git show origin/memory:apps/memory/src/temporal_memory/models.py`). Do not plan a second facts bank; Mirsal's Redis facts must *bridge* to it.
- `apps/api/app/communities.py` (owned by `societal`) already has `chat_*` tables, and the Community spec says not to build two full messaging stacks. Recommend the boundary (for example: Mirsal owns person-to-person messaging; Community's Inbox hands off or stays minimal).

## 3. Use subagents (read-only; each returns findings with `file:line`, commit or URL evidence; the lead writes)

Paste into each: its lane text, the *Read-only* list from `docs/submissions/CLAUDE.md` §2, and "do not edit any file in any repo; do not switch branches in dubai-io; never push to Mirsal-redesign".

- **Lane A: IP and provenance (gate M0; ingest task B, spec §1).** Using only evidence (git history, author names and emails, dates, licence files, asset sources, brand files, any office references in docs), state per area what is demonstrably the founder's own and what may be office- or client-owned: UI code, agents, images and graphics, the brand name and logo, Slides and screens. The areas are `src/`, `api/`, `agents/`, `server/`, `design/`, `media/`, `Slides/`, `screens/`, `public/`. List exactly what the founder must confirm in writing. Recommend one of: **reuse** (import the repo into `apps/mirsal/` with `git subtree add --prefix=apps/mirsal https://github.com/haitham72/Mirsal-redesign master`, keeping history), **clean-room** (a new `apps/mirsal/` with original design and brand, built by agents who never open the office-owned parts), or **no-go**. The founder decides; you never copy anything.
- **Lane B: Baseline audit (ingest task A).** Rerun the POC's offline tests in the throwaway clone and cite the output. Classify every row of the spec's §0 table and every module in §6 as `working/tested`, `implemented but unverified`, `mock/fixture`, `planned` or `not found`. Do not infer completion from filenames. Note the stack: React 18 + TS + Vite, Vercel `api/*.ts`, Python FastAPI agents + Redis. It is not Electron.
- **Lane C: Chat core, privacy and trust (ingest tasks C, D, F).** Design the real messaging path:
  - transport: Supabase Realtime + Postgres RLS, or a justified WebSocket service;
  - tables: users, contact requests, memberships, messages, receipts, attachments metadata, tasks, approvals, audit;
  - media in object storage with signed access; idempotent sends, offline retry, reconnect;
  - per-conversation AI controls *Off / Session only / Save approved memories*;
  - group-consent policy; **no E2EE claim**; the message-vs-memory boundary.
  Red-team it: a third user querying a private chat or its embeddings; an AI send, post or task without approval; a joke treated as an obligation; a third party's reminder created without consent; prompt injection inside a message; D14. For each case: the expected behaviour, the rule, and the test.
- **Lane D: Business case, live test and pitch (ingest task E, spec §2 business agents and §7).** Make the five business agents concrete as one demo chain: **Summarise → Decision Keeper → draft task → approval → task created → evidence-backed progress brief**, with the access-denied case. Also cover:
  - Stage 1 (the family/friends beta) vs Stage 2 (an opt-in team pilot), keeping the two apart;
  - before/after measures to *observe* (never invented percentages);
  - official, quotable numbers on SME or team productivity where they exist (URL + as-of; anything else labelled "reported");
  - a ≤ 4-minute demo script with `Demo data` and `Demo trigger` labels;
  - a 10-slide deck outline.
  The spec's own caveat ("a family chat app with AI stickers is not, by itself, a strong Business case") must be answered by the demo.

## 4. Write (all under `docs/submissions/mirsal/`)

| File | Contents |
|---|---|
| `ip-and-baseline.md` | Lane A: evidence per area, what the founder must confirm, and the **M0 recommendation** (reuse / clean-room / no-go) |
| `audit.md` | Lane B: what actually exists, with test output and status labels |
| `IMPLEMENTATION_GAP_MATRIX.md` | For each spec feature: source evidence · reuse candidate · missing work · S/M/L · dependency · acceptance test |
| `DELIVERY_ROADMAP.md` | Build slices `MS-B1 … MS-Bn` in the spec's §9 order (A audit + IP → B real chat core → C creative/voice agents on real chats → D scoped memory → E business agent → F verification + package). Each gives: owned files (only `business` paths), depends-on (mark the slices that wait on **M0** or on B0 identity or memory), happy- and failure-path tests, and the demo beat it unlocks. The last slices are packaging: deck, video, hosting or tunnel, and the Stage 2 pilot. Status line: `planned — awaiting founder approval (<date>, <tool>)` |
| `identity-memory-needs.md` | Exactly what Mirsal needs from shared identity and memory: chat-scoped reads, consented writes with source, actor and time, the Redis-facts bridge plan, consent toggles per conversation, Forget behaviour |
| `demo-script.md`, `sources.md` | Lane D's output |
| `open-questions.md` | At most **5 blocking** founder questions: **M0 first**, then the Updates-tray conflict, the messaging boundary with Community, … Each has a recommended answer, what it blocks and a deadline; non-blocking ones are listed after |
| `log.md` | `## <date> — P1 (<tool>)`: what you checked, what changed, top risks |

## 5. Finish

- Commit on `business`: `docs(mirsal): P1 IP evidence, audit, gap matrix and delivery roadmap`, then `git push origin business`. Never push `main`, and never push to `Mirsal-redesign`.
- Final message (≤ 15 lines): commit hash · what exists vs what is missing · the M0 recommendation and the evidence behind it · top 5 risks · blocking questions, each with your recommendation.
- Then stop. P2 (`shared/briefs/2-contract.md`) cross-checks your plan against Community's and writes the shared contract; the founder decides M0 and approves before any build.
