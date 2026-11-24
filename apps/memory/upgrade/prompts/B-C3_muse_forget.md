# B-C3 — Muse: make Forget real now that the schema has landed

Paste below the line into **Muse**.

---

Your WP-C and WP-C2 are merged. The core engine (WP-A, Gemini) is merged too, so `db/schema.sql`, the graph store, the validator fence and the job queue now exist. **Your 5 Forget tests are still `xfail`.** Make them real.

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` (**new location:** the Dubai-io repo, `apps/memory/`, branch `memory`) and `prompts/SUBAGENTS.md` (use a red-team sub-agent for the Forget races and a verifier before committing).

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpC3 -b mem-wpC3 memory
cd G:\Haitham\VsCode\contest-mem-wpC3\apps\memory
```

Own only `src/temporal_memory/privacy/` and `tests/test_{privacy,forget}.py`.

1. **Remove the 5 `xfail` marks** in `tests/test_forget.py` and make the tests pass against the real schema (Postgres on `localhost:5442`). Issues Gemini flagged:
   - `privacy/forget.py:93`: `RETURNING max(generation)` isn't valid (no aggregates in `RETURNING`). Use a CTE or a follow-up `SELECT`.
   - `tests/test_forget.py:66-81`: fixtures must insert the parent `owners` row (`o1`) first (FK).
   - `tests/test_forget.py:178`: use the store's `visible_facts` (`core/graph_store.py` exports it at module level and on `PostgresGraphStore`).
2. **CR-1:** use `temporal_memory.db` (`db.connect()` / the pool) instead of your local DB seam.
3. **CR-3:** re-queue affected days through `temporal_memory.queue.jobs` (`enqueue(owner, "extract.day", record_ids, priority=1, day=…)`), and re-check the generation fence end to end: forget while a job is leased → the late submit is rejected → **0 resurrected facts**.
4. Keep `pre_write`, the credential and wedding behaviour, and all 98 privacy tests green.

**Done when** the full suite (`python -m pytest -q` in `apps/memory`) shows **0 xfail and 0 fail**. Commit on `mem-wpC3` and report: branch, counts, and any contract request.
