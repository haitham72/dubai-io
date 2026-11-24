# B-A — Codex: core engine (schema · graph store · validator · applier · job ledger + Celery + claim API · extract runners · API app)

Paste below the line into **Codex**.

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and follow it (worktree `..\temporal-memory-wpA`, branch `wpA`). Then build **WP-A** of `planaudit.md` v2.1 (v2.1 box, §3.2, §6, §7, §10, §12).

**Build order (commit after each step; tests green each time):**

1. **`config.py` + `db/`.**
   - `db/schema.sql`: Postgres 17, idempotent. Tables per §3.2 without the `mem_` prefix: `owners`, `records` (+ `generation`), `entities`, `entity_aliases`, `subjects`, `facts` (+ GIN `tsv` over `text` + `text_orig`, using a folded `simple` config), `fact_entities` (role), `fact_evidence`, `links`, `entity_subjects`, `milestones`, `quarantine`, `forget_rules`, `jobs`, `job_attempts`, `workers`, `tokens`, `outbox`. Plus views `visible_facts` and `hypotheses`, and `(owner, …)` indexes.
   - `db/db.py`: a psycopg3 pool and a `migrate()` function.
2. **`core/graph_store.py`:** `GraphStore`. Scoped context ≤ 3k tokens = entities matched in the records (alias index) + 1-hop links + their top visible facts + subject paths. `visible_facts`.
3. **`core/validator.py`:** all 8 checks in §6.4, in order, each failure a named reason. Call the gate through `temporal_memory.privacy.policy.gate_fact` (WP-C). Until that exists, use a local shim marked `# TODO WP-C` that ports layer 1 from `contest/apps/api/app/lab/sensitive.py`.
4. **`core/applier.py`:**
   - `pg_advisory_xact_lock(hashtext(owner))`;
   - generation fence;
   - resolve-or-create entities and aliases (port `Memory.apply` + `_resolve` from `weekbench/configs/tn_update.py`);
   - ops new/update/end, with **older evidence never overwriting newer**;
   - write `fact_entities` (role) and `fact_evidence`; recompute `entity_subjects` for the touched entities;
   - quarantine sensitive facts (category + record ids only);
   - third-party entities stay `candidate` (promotion is `policy.may_promote`, WP-C).
5. **`queue/jobs.py` + `queue/outbox.py`:**
   - **enqueue:** job + outbox row in one transaction, plus an idempotency key;
   - **claim:** the SQL in §6.1, extended with optional `owner`, `day_from`/`day_to` and `limit`, so **one worker can claim one owner's week** (up to 7 `extract.day` jobs, same fence semantics);
   - heartbeat; submit (validate → apply → attempt row with model name + verdict);
   - **reconciler:** republish unpublished jobs, requeue expired leases, dead after 3 attempts.
6. **`queue/celery_app.py` + `queue/worker.py`:**
   - Celery on RabbitMQ (`TM_BROKER_URL`), result backend ignored for memory tasks;
   - tasks `memory.run_job(job_id)` (claim-by-id → `extract.run` → submit; a duplicate delivery exits without a model call) and `memory.reconcile` (beat, 60 s);
   - queues `mem.p0` / `mem.p1` / `mem.p3`, matching `docker-compose.yml` (P0 has its own worker).
7. **`core/extract.py`:**
   - system prompt and schema ported from `weekbench/configs/tn_update.py`, generalised per `Owner` (`display_name`, `self_aliases`), plus `role` per fact entity and `text_orig`;
   - records wrapped as inert data (injection guard);
   - **runners:**
     - `anthropic` (Messages API, structured JSON, `TM_CLOUD_MODEL`; check the current id in Anthropic docs);
     - `lmstudio` (port `chat_json` from `contest/apps/api/app/lab/llm.py:88-114`: strict json_schema, thinking off);
     - `agent-cli`: a generic subprocess runner that pipes the bundle to a command template from env, e.g. `claude -p --model haiku --effort medium --output-format json …` (trimmed flags from `weekbench/hook.py`), and reports the model name it was given.
8. **`api/app.py`:** `create_app()` with token auth (admin / worker / owner-device; sha256-stored tokens), a health endpoint, and the worker endpoints `POST /v1/workers/online`, `POST /v1/jobs/claim`, `/v1/jobs/{id}/heartbeat`, `/v1/jobs/{id}/result`. These let agent-cli workers on the host claim without Celery. Mount the routers from WP-B and WP-D if present (`include_router` behind `try/except ImportError`).

**Tests** (`tests/test_{schema,validator,applier,jobs,api}.py`):
- happy path: a gold day goes in, and facts, entities, aliases, role and entity_subjects come out; a week claim returns 7 jobs for one owner;
- failures: duplicate delivery, expired lease, fence-stale after a generation bump, late (older) evidence vs newer, evidence outside input, target outside context, a record id as an entity name, injected instruction text, a credential in a fact, malformed JSON, a worker token claiming the owner-device pool.
