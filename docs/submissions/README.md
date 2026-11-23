# Contest submissions: pointer and hand-off

**For:** the team on the other PC (Dubai-io iOS + desktop, temporal_note) and any agent opening `main`. **Written:** 24 Nov 2026.

`main` is **Entry 1, Best Personal AI Agent** (Quest / Dubai-io). Two more Dubai Chambers entries are built on their own long-lived branches. All three share one verified `user_id` and one memory service.

| Track | Entry | Branch | Docs (on that branch) |
|---|---|---|---|
| Shared base: identity, memory bridge, cross-app contract | — | `contest-shared` | `docs/submissions/shared/` (start with `founder-decisions.md`) |
| Best Societal AI Agent | Dubai-io Community (Facebook / Reddit-like) | `societal` | `docs/submissions/community/` |
| Best Business AI Agent | Messenger (WhatsApp-like; working name) | `business` | `docs/submissions/messenger/` |

The branch rules are in `docs/submissions/CLAUDE.md` on each of those branches. In short, they **only add new files**: `apps/community/`, `apps/messenger/`, `apps/api/app/{identity,memory_bridge,community,messenger}/`, their tests, and `docs/submissions/**`. The one exception is a section appended at the end of `CLAUDE.md`. They never touch `main`, `apps/web`, `apps/site`, `apps/memory`, `PLAN.md`, `ARCHITECTURE.md` or `supabase/migrations/`.

## For the other PC: merging your `main`

1. `origin/main` changed only these files since `f016856` (23 Nov): this file is new, and `CLAUDE.md` is net unchanged (a section was added and then moved here). So the merge is conflict-free whatever you changed:
   ```
   git fetch origin
   git merge origin/main
   git push origin main
   ```
   Never force-push `main`.
2. **Do not merge `contest-shared`, `societal` or `business` into `main`.** Once your `main` is on GitHub, they are reconciled deliberately from the founder's PC (see below).
3. **The memory team (temporal_note rebuild):** the shared memory bridge needs 4 small HTTP routes and 2 fixes. See `git show origin/contest-shared:docs/submissions/shared/handoff-temporal-note.md`. Please reply with whether the rebuild exposes them, or what its interface will be. Until then the bridge runs against a fake with the same interface.
4. **Security:** the Community app's Next.js had a known advisory. `apps/site` also uses Next.js; run `npm audit` there.
5. **Old branches** are archived as tags (`archive/*`). To restore one: `git switch -c <name> archive/<tag>`.

## After your `main` is on GitHub (done from the founder's PC)

1. Fast-forward the local `main`.
2. `git merge origin/main` into `contest-shared` and run the full test suite. Then `git merge contest-shared` into `societal` and `business`, each only while no agent is working there.
3. Re-add the contest pointer to `CLAUDE.md`, and apply the drafted canon updates (`docs/submissions/shared/canon-patches/` on `contest-shared`) to `PLAN.md`, `ARCHITECTURE.md` and `docs/status.md` as one reviewed commit.
4. Re-check `apps/api/app/memory_bridge/` against the rebuilt temporal_note, and swap the fake client for the real one.
