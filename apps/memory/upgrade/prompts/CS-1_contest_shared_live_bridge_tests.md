# CS-1 — contest-shared: run the memory-bridge suite against the REAL temporal_note server

For the **shared-code lead on the founder's other PC** (branch `contest-shared`). Paste below the line.

---

Read `docs/submissions/CLAUDE.md` on `contest-shared` first (lane branches `cs/<slice>`, owned paths §2, gates §4).

**Lane:** `cs/live-bridge-tests` from `contest-shared`. Owned paths only: `apps/api/tests/test_memory_bridge_*.py`, `apps/api/tests/conftest.py` (memory-bridge fixtures only), and `docs/submissions/shared/handoff-temporal-note.md`.

## Why

The hand-off's acceptance gate is "the bridge contract suite passes against the rebuilt temporal_note". But every `test_memory_bridge_*.py` file builds `FakeTemporalMemoryClient()` directly (for example `test_memory_bridge_writes.py:47`, `_reads.py:45`, `_consent.py:47`, `_forget.py:174`, `_e2e.py:52`). The 89 passing tests therefore **never reach the real server**.

The real server is now fixed. temporal_note branch **`memory` @ `267b0cf`** (on GitHub) runs `/records`, `/forget`, `/facts/{id}/resolve`, `/context` and `/search` on Postgres. A manual run with `HttpTemporalMemoryClient` against it succeeded for owner setup, record upsert, prefixed search, context, forget-by-fact, forget-by-record, the 409 on re-import, and resolve.

## Deliverables

1. **A live mode.** One fixture that returns `FakeTemporalMemoryClient()` by default and, when `MEMORY_BRIDGE_LIVE=1`, returns the client from your existing `memory_bridge/config.py` builder (`MEMORY_BRIDGE_BACKEND=http`, `TM_BASE_URL`, `TM_SERVICE_TOKEN`).
   - Switch the contract tests to that fixture.
   - Tests that only make sense with the fake (for example, ones that inspect its internals) stay fake-only and are marked as such.
   - Live mode uses a fresh owner per test run, and cleans it up through Forget.
2. **How to run it.** A short section in `handoff-temporal-note.md`:
   - check out `memory` (`git worktree add ..\tm-live origin/memory`);
   - in `apps/memory`: `copy .env.example .env`, set `TM_ADMIN_TOKEN`, then `docker compose up -d postgres rabbitmq redis api`;
   - create an owner (`POST /v1/owners`) and a service token (`POST /v1/tokens`) with the admin token;
   - export `TM_BASE_URL=http://localhost:8040` and `TM_SERVICE_TOKEN=…`;
   - `MEMORY_BRIDGE_LIVE=1 pytest -q apps/api/tests/test_memory_bridge_*.py`.
3. **Align the field name.** The hand-off doc's examples send `subject_id` (around line 50), but `HttpTemporalMemoryClient` sends `subject_path`. The server accepts both today. Make the doc match the client (`subject_path`, saying that `subject_id` is accepted too). Don't change the client.
4. **Report back:** the pass/fail counts in **fake** and **live** mode separately. For every live failure, give the request, the response and which side you believe is wrong. **Don't change temporal_note** (another team owns it); report mismatches instead.

**Done when:** the fake mode is unchanged (89 passed or more), the live mode has been run once against `memory@267b0cf` with results reported, and §4 gates pass. Merge `--no-ff` into `contest-shared` (the lead merges), then `git merge contest-shared` into `societal` and `business` when no agent is working there.
