# Contest submissions: pointer and hand-off

**For:** the team on the other PC (Dubai-io iOS + desktop, temporal_note) and any agent opening `main`. **Written:** 24 Nov 2026.

`main` is **Entry 1, Best Personal AI Agent** (Quest / Dubai-io). Two more Dubai Chambers entries are built on their own long-lived branches. All three share one verified `user_id` and one memory service.

**Three separate products, one repo (founder, D15, 24 Nov).** Dubai-io (like ChatGPT), Community (like Facebook) and Messenger (like WhatsApp) are three different products, Meta-style. They share **only the per-user layer** (identity + the temporal_note memory engine), and that layer lives in this repo. Each product is developed in its own folders on its own branch, and they are **never merged into one tree**: `societal` and `business` never go into `main` or into each other. **Status:** the builds are done and waiting for tests. Details: `docs/submissions/shared/founder-decisions.md` D15 on `contest-shared`.

| Track | Entry | Branch | Docs (on that branch) |
|---|---|---|---|
| Shared base: identity, memory bridge, cross-app contract | — | `contest-shared` | `docs/submissions/shared/` (start with `founder-decisions.md`) |
| Best Societal AI Agent | Dubai-io Community (Facebook / Reddit-like) | `societal` | `docs/submissions/community/` |
| Best Business AI Agent | Messenger (WhatsApp-like; working name) | `business` | `docs/submissions/messenger/` |

The branch rules are in `docs/submissions/CLAUDE.md` on each of those branches. In short, they **only add new files**: `apps/community/`, `apps/messenger/`, `apps/api/app/{identity,memory_bridge,community,messenger}/`, their tests, and `docs/submissions/**`. The one exception is a section appended at the end of `CLAUDE.md`. They never touch `main`, `apps/web`, `apps/site`, `apps/memory`, `PLAN.md`, `ARCHITECTURE.md` or `supabase/migrations/`.

## For the other PC: merging your `main`

*Done 24 Nov: this PC's `main` had no unpushed work (Dubai-io's iOS, desktop and memory work is on the pushed `ios`, `desktop` and `memory` branches), so it was fast-forwarded to `origin/main`. Those three branches merge cleanly with `contest-shared`, `societal` and `business`.*

1. `origin/main` changed only these files since `f016856` (23 Nov): this file is new, and `CLAUDE.md` is net unchanged (a section was added and then moved here). So the merge is conflict-free whatever you changed:
   ```
   git fetch origin
   git merge origin/main
   git push origin main
   ```
   Never force-push `main`.
2. **Do not merge `contest-shared`, `societal` or `business` into `main`.** `societal` and `business` never go into `main` (D15). Whether the shared layer reaches `main` for Entry 1 is a separate founder decision.
3. **The memory team: the companion's new memory (the temporal_note rebuild) is expected to implement the hand-off.** That is 4 HTTP routes (`CR-TM-1` … `CR-TM-4`) and 2 fixes, in `git show origin/contest-shared:docs/submissions/shared/handoff-temporal-note.md` (§0 Expectation). It is the single memory service for all three entries. Acceptance: the bridge contract suite (`apps/api/tests/test_memory_bridge_*.py` on `contest-shared`) passes against the rebuilt service. If its interface differs, reply with it, and the bridge adapts. Until then the entries run on a fake with the same interface.
4. **Security:** the Community app's Next.js had a known advisory. `apps/site` also uses Next.js; run `npm audit` there.
5. **Old branches** are archived as tags (`archive/*`). To restore one: `git switch -c <name> archive/<tag>`.

## After your `main` is on GitHub (done from the founder's PC)

1. ~~Fast-forward the local `main`.~~ Done 24 Nov.
2. ~~`git merge origin/main` into `contest-shared` and run the full test suite. Then `git merge contest-shared` into `societal` and `business`.~~ Done and pushed 24 Nov; all gates green (results in D15). Repeat this whenever `origin/main` moves.
3. Re-add the contest pointer to `CLAUDE.md`, and apply the drafted canon updates (`docs/submissions/shared/canon-patches/` on `contest-shared`) to `PLAN.md`, `ARCHITECTURE.md` and `docs/status.md` as one reviewed commit. Under D15, `main` describes Entries 2–3 as living on their branches and never lists their folders as `main` folders.
4. Re-check `apps/api/app/memory_bridge/` against the rebuilt temporal_note, and swap the fake client for the real one.
