# B-H — Gemini (WP-A owner): fix the pooled-connection commit bug the Docker e2e found

Paste below the line into **Gemini**.

---

Codex's Docker end-to-end suite on branch `memory` fails 6 of 7 tests. The integrator found the cause, and it's in **your** `db/db.py`.

**Bug:** `Database.connection()` puts a connection back into the pool **with an implicit transaction still open** whenever a caller only reads. Example: the API's `/health` with no schema set, which is the API's configuration. The next `Database.transaction()` on that connection then becomes a **SAVEPOINT inside** that open transaction, so its writes are **never committed**. The e2e symptom: `POST /v1/owners` returns 200, but the row isn't visible from another connection. The unit tests miss it because they always use a schema, and the `SET search_path … commit` happens to clear the transaction.

**Fix (reference only, verify it yourself):** `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\ref_db_pool_fix\db_pool_fix.patch`. In the `finally` block, roll back if `conn.info.transaction_status != TransactionStatus.IDLE` before pooling. A regression test is drafted at `…\ref_db_pool_fix\test_db_pool.py`. It writes after a read on a schema-less `Database`, and checks that a failed block doesn't poison the pool.

Rules: `prompts/B0_common_rules.md` (never edit the `G:\Haitham\VsCode\contest` folder). Sub-agents on a **lower Gemini tier** only if you need them; this is a small fix.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpH -b mem-wpH memory
cd G:\Haitham\VsCode\contest-mem-wpH\apps\memory
```

1. Apply the fix and add `tests/test_db_pool.py`. **Prove the test fails without the fix and passes with it.**
2. Audit every `db.connection()` caller that **writes** (`queue/jobs.py`, `queue/outbox.py`, `core/applier.py`, `api/app.py`, `mcp/*`, `privacy/forget.py`). With the fix, a write without an explicit `commit()` now gets rolled back instead of silently lingering. Make each write use `transaction()` or commit explicitly.
3. Run the unit suite **and** the Docker e2e (`tests/e2e/README.md`: `TM_RUN_E2E=1`, `TM_E2E_GOLD_DIR=G:\Haitham\lab-data\memory-bakeoff\gold`, `pytest -m e2e`). **Both must be green.**

**Report:** branch, unit + e2e counts, the list of write paths you changed.
