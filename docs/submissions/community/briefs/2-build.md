# Brief B — Build · Dubai-io Community (Entry 2) · branch `societal`

Suggested lead: **Antigravity** (any of Cursor / Muse / Codex / Antigravity works). Paste everything below the line into the lead agent **only after** the founder has approved `docs/submissions/community/DELIVERY_ROADMAP.md` (its status line reads `approved — <date>`).

---

You are the **build lead** for *Dubai-io Community*, our **Best Societal AI Agent** entry, on branch **`societal`** of `github.com/haitham72/dubai-io` (private). You build the approved roadmap with subagents and merge every slice yourself after its gates pass.

## 0. Preconditions and setup

- Local: `D:\Vscode\dubai-io-societal`. Cloud: `git fetch origin && git switch societal && git pull --ff-only`.
- **Stop** unless `DELIVERY_ROADMAP.md` reads `approved — <date>`. Also stop if `open-questions.md` still has an unanswered question marked as blocking the slice you are about to start.
- Slices that depend on shared identity or memory wait until Gate S has passed and `contest-shared` has been merged into `societal` (check `docs/submissions/shared/log.md`). Social-core slices may start before that.
- **Never** commit to or push `main`; never force-push. Lane branches are `cm/<slice-id>`, cut from the latest `societal`.
- Run the API suite once before any change and record the pass count in `community/log.md` as your baseline.

## 1. Read

Root `CLAUDE.md` · `docs/submissions/CLAUDE.md` (paths §2, gates §4, rules §5) · `shared/founder-inputs/02_DUBAI_IO_COMMUNITY_PLAN.md` (the spec) · `community/DELIVERY_ROADMAP.md`, `IMPLEMENTATION_GAP_MATRIX.md`, `open-questions.md` (with the founder's answers), `demo-script.md` · `shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md` · `ARCHITECTURE.md` §7, §9 · `apps/api/CLAUDE.md`.

## 2. Hard rules (paste this block into every subagent prompt)

```
- Work only on your lane branch cm/<slice-id>, cut from societal. Never touch main.
- Write only your slice's files, all inside: apps/community/**, apps/api/app/community/**,
  apps/api/app/communities.py, apps/api/app/social_generation.py, apps/api/tests/test_community_*.py,
  apps/api/tests/test_communities.py, apps/api/tests/test_social_generation.py,
  apps/api/tests/fixtures/community/**, docs/submissions/community/**.
  Everything else is read-only: apps/web/** (frozen), apps/site/**, apps/memory/**, PLAN.md, ARCHITECTURE.md,
  supabase/**, packages/**, docs/submissions/shared/**, apps/api/app/identity/**, apps/api/app/memory_bridge/**,
  and every other module in apps/api/app/.
- Memory only through apps/api/app/memory_bridge (never a new facts table); identity only through apps/api/app/identity.
- Feed ranking reads consented interest features only. Never raw Quest chat, Gmail, Outlook or Mirsal text,
  sensitive facts, family details or third parties' data.
- AI drafts publish only after the user approves the exact revision and destination (a registered capability
  plus an approval card). Moderation flags only; a human resolves.
- Seeded posts are labelled Demo data; never present them as real community activity.
- No Meta, Facebook or government branding. Light mode first; no shadows.
- Synthetic fixtures only. Every workflow: a happy-path AND a failure-path test. Keys from env only.
- Report back: files changed, the exact test commands you ran WITH their output, anything left open.
```

## 3. Use subagents

At most 4 lanes in parallel, following `DELIVERY_ROADMAP.md`; parallel slices never share a file. Typical lanes:
- **Social core API:** profiles, follows, posts, comments, reactions, groups, notifications, moderation events, built on `communities.py`.
- **Media and storage:** signed URLs and quotas.
- **Agents** in `apps/api/app/community/`:
  - Discovery with "Why this?"
  - Community Answer with citations → approve → post
  - Group Organizer (summaries and proposed checklists only)
  - Moderation Copilot
- **Web app** `apps/community/`: Next.js + Vitest + Playwright like `apps/site`; iPhone-first PWA; API on :8060, web on :3060.
- **Demo and packaging:** scenes A–D, deck, video, multi-user test.

You merge each lane into `societal` after **re-running** gates 1–4 (`docs/submissions/CLAUDE.md` §4) yourself. A subagent's report is not evidence. A lane needs a read-only file changed? Use the shared-change exception (its own `shared(<area>):` commit, a test, `community/shared-changes.md`). If the file is a shared-contract file, send it to the B0 lead on `contest-shared` instead.

Run commands (Windows; for Mac/Linux see `apps/api/CLAUDE.md`):

```powershell
cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.community.server:app --port 8060
cd apps/api; .\.venv\Scripts\python.exe -m pytest -q tests
cd apps/community; npm install; npm run dev -- -p 3060
```

## 4. Done means

- The spec's §7 acceptance gates pass in tests, as far as the roadmap's slices reach.
- Gates 1–4 are green in your own run.
- UI slices have a recorded founder visual review of a staged preview.
- The demo script runs end to end three times without a manual fix.
- Packaging for **Fri 18 Dec 2026** is done: deck (10 slides, English), video (≤ 4 min), hosting or tunnel, and a multi-user test written up in `community/log.md`.

A partial slice is never "done".

## 5. Final report (to the founder, ≤ 20 lines)

Slices merged with commit hashes · API test count vs the baseline · which of the spec's §7 gates are green (with test names) · what is `Demo data` on stage · shared changes · open risks · what is needed from the founder.
