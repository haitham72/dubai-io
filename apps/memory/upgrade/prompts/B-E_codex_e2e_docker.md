# B-E — Codex: end-to-end through the real queue in Docker + review of the core engine

Paste below the line into **Codex**.

---

You're back. The memory engine is built and merged on branch **`memory`** of the Dubai-io repo (`apps/memory/`): contract, core engine (Gemini), surfaces (Gemini), privacy (Muse). **137 tests pass.** Gemini is building ingest + MCP (WP-D) and Muse is finishing Forget. Your job is to **prove the whole thing works as a system**: real RabbitMQ, real Celery workers, real Postgres, in Docker.

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md`, `prompts\SUBAGENTS.md` (use implementer × 2 + red-team + verifier), and `planaudit.md` v2.1 (§6, §7, §11 P3).

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpE -b mem-wpE memory
cd G:\Haitham\VsCode\contest-mem-wpE\apps\memory
```

**You own:** `Dockerfile`, `docker-compose.yml`, `tests/e2e/`, `scripts/`. You may fix bugs in `core/` and `queue/` if e2e exposes them, in separate commits prefixed `fix(core):`. **Don't touch** `api/app.py`, `ingest/`, `mcp/`, `hooks/` (Gemini, WP-D) or `privacy/` (Muse).

1. **Docker:** `docker compose up -d --build api worker-p0 worker-p1 beat` comes up healthy. The API health endpoint answers, and the workers connect to RabbitMQ and consume `mem.p0` / `mem.p1` / `mem.p3`. Fix the Dockerfile/compose as needed (schema migration on startup, env, host LM Studio via `host.docker.internal`).
2. **Oracle runner (test-only):** `tests/e2e/oracle_runner.py` returns, for each day packet, the extraction output derived from the gold ledger (`G:\Haitham\lab-data\memory-bakeoff\gold\ledger.json`, copied as a small fixture or read from the path given by env). That makes the full pipeline deterministic with $0 model cost. Register it **only in tests** (env-selected runner or monkeypatch), never in production code paths.
3. **E2E** (`pytest -m e2e`, opt-in, Docker running):
   - create an owner, seed the gold month's records (via `tm import` if WP-D has merged, else via DB/API), enqueue `import.split`, let the **real Celery workers** drain the queue;
   - assert: every day `applied`; facts / people / entity↔subject roles match the ledger within stated tolerances; the Vault and md export render; ops shows per-model attempts;
   - **races (red-team):** kill a worker mid-job → the lease expires → requeue, with no duplicate facts; deliver the same job twice → one model call; Forget a source mid-import → 0 resurrected facts; a P1 import flood never starves a P0 job.
4. **Live smoke (opt-in, `-m live_llm`):** run one gold day through the `agent-cli` runner with the founder's hook (`claude -p --model haiku --effort medium` with the trimmed flags from `G:\Haitham\lab-data\memory-bakeoff\weekbench\hook.py`). Log the model name, tokens and cost in the attempt row.
5. **Review of the core engine (WP-A):** use a read-only reviewer sub-agent over `core/`, `queue/`, `db/`. Check the claim SQL, fence/lease handling, outbox transactionality, the idempotency key, applier time rules and SQL injection. Report findings ranked; fix only what your e2e proves broken.

**Report:** branch, counts (unit + e2e), Docker status, a findings list, and commands to reproduce.
