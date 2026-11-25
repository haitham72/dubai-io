# Contest submissions: pointer and hand-off

**For:** the team on the other PC (Dubai-io iOS + desktop, temporal_note) and any agent opening `main`. **Written:** 24 Nov 2026.

All three products and the shared per-user layer are on `main` (D16, 24 Nov): Dubai-io (Best Personal AI Agent), Community (Best Societal AI Agent) and Messenger (Best Business AI Agent). All three share one verified `user_id` and one memory service (temporal_note).

**Three separate products, one repo (founder, D15, 24 Nov).** Dubai-io (like ChatGPT), Community (like Facebook) and Messenger (like WhatsApp) are three different products, Meta-style. They share **only the per-user layer** (identity + the temporal_note memory engine), and that layer lives in this repo. Each product lives in its own folders; every feature is built on a branch from `main`, and **finished branches merge into `main` after their gates pass (D16)**. Entry branches never merge into each other. **Status:** the builds are done and waiting for tests. Details: `docs/submissions/shared/founder-decisions.md` D15 on `contest-shared`.

| Track | Entry | Folders |
|---|---|---|
| Shared: identity, memory bridge, cross-app contract | — | `apps/api/app/identity`, `apps/api/app/memory_bridge`, `docs/submissions/shared/` (start with `founder-decisions.md`) |
| Best Societal AI Agent | Dubai-io Community | `apps/community`, `docs/submissions/community/` |
| Best Business AI Agent | Messenger | `apps/messenger`, `docs/submissions/messenger/` |

Start with D16 and the shared memory contract on `main`. Read `community/` for the Societal entry, `messenger/` for the Business entry, and `shared/` for identity, memory and founder decisions. Feature branches start at `main`; Claude merges after the relevant gates pass (`docs/submissions/CLAUDE.md`). The branch graph (`contest-shared`, `societal`, `business`) described in earlier versions of this file is integration history.

## Integration history (superseded by D16; kept as a record)

*Done 24 Nov: this PC's `main` had no unpushed work (Dubai-io's iOS, desktop and memory work is on the pushed `ios`, `desktop` and `memory` branches), so it was fast-forwarded to `origin/main`. Those three branches merge cleanly with `contest-shared`, `societal` and `business`.*

1. `origin/main` changed only these files since `f016856` (23 Nov): this file is new, and `CLAUDE.md` is net unchanged (a section was added and then moved here). So the merge is conflict-free whatever you changed:
   ```
   git fetch origin
   git merge origin/main
   git push origin main
   ```
   Never force-push `main`.
2. **Agents don't merge into `main`.** The integrator merges `contest-shared`, `societal` and `business` into `main` after their gates pass (D16).
3. **The memory team: the companion's new memory (the temporal_note rebuild) is expected to implement the hand-off.** That is 4 HTTP routes (`CR-TM-1` … `CR-TM-4`) and 2 fixes, in `git show origin/contest-shared:docs/submissions/shared/handoff-temporal-note.md` (§0 Expectation). It is the single memory service for all three entries. Acceptance: the bridge contract suite (`apps/api/tests/test_memory_bridge_*.py` on `contest-shared`) passes against the rebuilt service. If its interface differs, reply with it, and the bridge adapts. Until then the entries run on a fake with the same interface.
4. **Security:** the Community app's Next.js had a known advisory. `apps/site` also uses Next.js; run `npm audit` there.
5. **Old branches** are archived as tags (`archive/*`). To restore one: `git switch -c <name> archive/<tag>`.

## After your `main` is on GitHub (done from the founder's PC)

1. ~~Fast-forward the local `main`.~~ Done 24 Nov.
2. ~~`git merge origin/main` into `contest-shared` and run the full test suite. Then `git merge contest-shared` into `societal` and `business`.~~ Done and pushed 24 Nov; all gates green (results in D15). Repeat this whenever `origin/main` moves.
3. Re-add the contest pointer to `CLAUDE.md`, and apply the drafted canon updates (`docs/submissions/shared/canon-patches/` on `contest-shared`) to `PLAN.md`, `ARCHITECTURE.md` and `docs/status.md` as one reviewed commit. Under D15, `main` describes Entries 2–3 as living on their branches and never lists their folders as `main` folders. [24 Nov: superseded by D16 — all three products live on `main`.]
4. Re-check `apps/api/app/memory_bridge/` against the rebuilt temporal_note. The temporal_note HTTP bridge exists and CS-1 supports live contract tests; verify real wiring and isolation in the E-round before claiming the demo works. Review the canon drafts (`docs/submissions/shared/canon-patches/`) against current `main` before applying them.
