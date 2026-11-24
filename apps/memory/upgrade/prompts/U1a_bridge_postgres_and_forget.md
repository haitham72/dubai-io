# U1a — Bridge on Postgres + Forget that really forgets (after U0a is merged)

Suggested agent: **Cursor** (it built the B-M bridge, which only works on the fake store). Any agent may take it.

Paste below the line.

---

Read first:
- `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md`. The integrator is **Gemini**.
- `TN_UPGRADE_PLAN.md` v1: §2b **B1** and **B3**, §6 (Forget and bridge gates).
- Codex audit findings **02** and **03**.
- The hand-off spec: `git -C G:\Haitham\VsCode\contest show contest-shared:docs/submissions/shared/handoff-temporal-note.md`.

**Sub-agents:** at most 2, cheap tier only: Cursor → its fast model, Codex → gpt-6.2 sol, Muse → Muse 1.3 Contributor, Gemini → a lower tier.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpU1a -b mem-wpU1a memory   # memory must already contain U0a
cd G:\Haitham\VsCode\contest-mem-wpU1a\apps\memory
```

## The problems (reproduced by the audits)

- **The bridge breaks on Postgres.** `POST /records` and `/facts/{id}/resolve` return **HTTP 500** (`AttributeError: PostgresGraphStore has no attribute records`), because `api/bridge.py` mutates `FakeGraphStore` attributes (`:111,141,152,174,199,241,278`). Source-prefix search returns 0 of 2 valid facts.
- **Forget by fact ID** returns 200/ok with `facts_erased=0`, and the fact stays.
- **`forget_source()`** never bumps `facts_version`, so a **warm `context_pack` keeps returning the erased fact**. It doesn't recompute counts, and its idempotency is process-local (`api/bridge.py:63`).

Community and Messenger depend on these routes.

## Owned files (only these)

- `src/temporal_memory/api/bridge.py`
- `src/temporal_memory/privacy/forget.py`
- new `src/temporal_memory/core/bridge_store.py` (the Postgres implementations of the bridge writes; keep them out of `graph_store.py` so U1c can edit that file)
- `tests/test_crtm_handoff.py`, `tests/test_forget.py`
- new `tests/test_bridge_postgres.py`

You may add **one** line to `api/app.py` only if store wiring requires it. Say so in your report.

## Deliverables

1. **All CR-TM routes work on `PostgresGraphStore`:** `/records` (batch, dedupe by hash, enqueue `extract.live | extract.day | none`), `/forget`, `/facts/{id}/resolve`, `/context`, `/search`. Response shapes stay identical; owner auth is unchanged.
   - `/search` calls the contract method `store.search_candidates(...)` (U1c implements it on Postgres; until then test against the fake) and applies `source_prefix` **in SQL, before the limit**.
   - A fact matches a prefix when every one of its surviving evidence records starts with it, and it has at least one.
2. **Forget is transactional.** In the same transaction:
   - erase the facts, and their entities, aliases and links that are left without surviving evidence;
   - bump `facts_version` **and** `privacy_revision`;
   - recompute `subjects.fact_count`;
   - record the request in `forget_requests` (durable idempotency).

   Forget by fact ID really erases. Survivor requeue still works, including the `extract.session` job kind.
3. **Tests on Postgres (not the fake), happy + failure paths:**
   - each route;
   - Forget then a warm `context_pack` → the fact is gone;
   - Forget with a job leased in flight → its result is rejected by the generation fence;
   - the same idempotency key twice → one effect, even across a new process;
   - cross-owner → 403.
4. **The cross-repo contract.** Start the API on Postgres and run `contest-shared`'s `apps/api/tests/test_memory_bridge_*.py` against it with the real `HttpTemporalMemoryClient` (worktree `G:\Haitham\VsCode\contest-sub-contest-shared`; read-only, don't edit it). Report the pass count. If its interface differs from yours, **report the difference; don't bend either side.**

**Done when:**
- the full suite is green;
- `test_bridge_postgres.py` and the Forget tests pass on the compose Postgres;
- the contest-shared contract suite passes against your server.

Commit on `mem-wpU1a`. Report the branch, files, test counts (fake and Postgres separately), the contract-suite result, and any contract requests.
