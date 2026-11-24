# U0a — Contract + versioned migrations for the temporal_note upgrade (goes FIRST; small)

Suggested agent: **Codex** (it reproduced the schema and Forget issues). Any agent may take it.

Paste below the line.

---

Read first:
- `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md`. It applies, except that **the integrator who merges into `memory` is Gemini**.
- `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\TN_UPGRADE_PLAN.md` v1, especially §2b B4, §5 U1 and §7.
- Codex's audit `tn_upgrade_audit_codex.md` §5 (contract notes).

**Sub-agents:** at most 2, cheap tier only: Codex → gpt-6.2 sol, Muse → Muse 1.3 Contributor, Gemini → a lower tier, Cursor → its fast model.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpU0a -b mem-wpU0a memory
cd G:\Haitham\VsCode\contest-mem-wpU0a\apps\memory
```

## Update, 24 Nov: U1a landed first

U1a (`mem-wpU1a` `afcec62`, verified: 343 passed; 21 Postgres tests) creates two of your objects at runtime in `privacy/forget.py::_ensure_upgrade()` (lines 229-245), because U0a didn't exist yet:
- `owners.privacy_revision BIGINT NOT NULL DEFAULT 0`
- `forget_requests(owner, idempotency_key, request JSONB, result JSONB, created_at, PK(owner, idempotency_key))`

If U1a is already in `memory` when you start:
- (a) your migration `0001` must create **exactly these shapes** (with `IF NOT EXISTS`), so databases that U1a already touched still migrate cleanly;
- (b) you **may edit `privacy/forget.py` only to delete `_ensure_upgrade()` and its two calls** (lines ~250 and ~414). Runtime `ALTER TABLE` inside every Forget takes a table lock on `owners`;
- (c) `api/bridge.py` `/search` already calls `store.search_candidates` when it exists, so keep that name and signature.

Add a test that a database where `_ensure_upgrade` already ran migrates without error.

## Why

Three tracks (U1a, U1b, U1c) start in parallel right after you land. They must share one frozen contract and one migration mechanism. Today `db/db.py:migrate()` only runs `CREATE TABLE IF NOT EXISTS`, so new columns never reach an existing database (B4).

## Owned files (only these)

- `src/temporal_memory/models.py`
- `src/temporal_memory/db/db.py`
- `src/temporal_memory/db/schema.sql`
- new `src/temporal_memory/db/migrations/`
- `tests/fixtures/fake_store.py`
- `tests/test_schema.py`
- new `tests/test_migrations.py`
- `src/temporal_memory/privacy/forget.py`, **only** to remove `_ensure_upgrade()` (see the update above)

## Deliverables

1. **Versioned migrations.**
   - Add a `schema_migrations(version, applied_at)` table, and ordered, idempotent `db/migrations/NNNN_*.sql` files that `migrate()` applies once each, inside a transaction, under an advisory lock.
   - It must upgrade a database created from the **current** `schema.sql` (test this: create the old schema, insert rows, migrate, assert the data survived).
   - Fresh installs end up with the same schema.
2. **Migration `0001_upgrade_v1`** (additive and nullable only):
   - `entities`: `provenance TEXT NOT NULL DEFAULT 'inferred'`, `user_confirmed_at TIMESTAMPTZ`, `closeness_suggested TEXT`, `closeness_suggested_evidence JSONB`, `tier_confirmed_at TIMESTAMPTZ`, `salience_updated_at TIMESTAMPTZ`.
   - `subjects`: `provenance TEXT NOT NULL DEFAULT 'inferred'`, `user_confirmed_at TIMESTAMPTZ`.
   - New `link_evidence(owner, link_id, fact_id, PRIMARY KEY(owner, link_id, fact_id))`, with FKs that cascade.
   - New `forget_requests(owner, idempotency_key, request JSONB, result JSONB, created_at, PRIMARY KEY(owner, idempotency_key))`, so Forget idempotency survives restarts.
   - `owners.privacy_revision BIGINT NOT NULL DEFAULT 0`.
   - **Existing rows stay `inferred`:** legacy origin is unknown, so be conservative. Never infer `user_supplied` from `status`.
   - Index `forget_rules(owner, kind, value)`.
3. **Contract (`models.py`).**
   - Add the fields above to `Entity` and `Subject`, all optional.
   - Add to the `GraphStoreFull` protocol (signatures + docstrings only):
     - `search_candidates(owner, query, *, entity_ids=None, subject_ids=None, date_from=None, date_to=None, source_prefix=None, limit=50) -> list[Candidate]`, where `Candidate = (fact_id, score, channel)` and channel ∈ fts | entity | subject | date;
     - `get_facts(owner, fact_ids) -> list[Fact]` (exact; no cap);
     - `fact_counts_by_subject(owner) -> dict[str, int]`;
     - `iter_visible_facts(owner, *, date_from=None, date_to=None, after=None, page_size=500)` (cursor pages for export / reflect / timeline);
     - `bump_privacy_revision(owner) -> int`.
   - Add `JobKind` value `extract.session` now, unused until U2, so the queue and Forget code can be written against it.
   - Keep every existing signature unchanged.
4. **Fake store parity.** `FakeGraphStore` implements the new methods simply (Python), so the existing tests keep running.
5. **Tests.** Migration upgrade from the old schema (happy path); re-running `migrate()` is a no-op; a migration failing mid-way rolls back (failure path); the fake store passes the new protocol checks. Full suite green: today it's `335 passed, 8 skipped`.

## Don't

- Don't implement the Postgres versions of the new methods (U1a, U1b and U1c do that).
- Don't touch the `api/`, `core/`, `privacy/`, `live/` or `mcp/` folders.
- Don't change `PROMPT_VERSION`.

**Done when:** `python -m pytest -q` is green and the upgrade test passes against the compose Postgres (`:5442`) in a temporary schema you drop. Commit on `mem-wpU0a` and report: branch, files, test counts, the exact final signatures, and anything you changed from this list and why.
