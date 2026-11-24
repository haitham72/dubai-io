# E1b report - host workers run real extraction (builder, 2026-11-24)
Branch e1b/host-workers, tip e92c872 (from origin/main 1ed8759). Pushed, NOT merged. Worktree G:/Haitham/VsCode/contest-e1b. apps/web untouched.

## What changed
- start-all: Docker now runs only postgres/rabbitmq/redis + memory api; it STOPS the worker-p0/worker-p1/beat containers. Host Celery: worker p0@w (`-Q mem.p0 -P solo`), p1@w (`-Q mem.p1,mem.p3 -P threads -c 2`) and ONE beat. Python = apps/memory/.venv if present, else the sibling contest-memory venv (the one used today), else the apps/api venv; PYTHONPATH = this checkout's apps/memory/src. TM_WORKER_RUNNER=agent-cli (lmstudio when :1234 answers; env DUBAI_WORKER_RUNNER overrides), TM_WORKER_MODEL=claude-haiku-4-5-20251001, host claude dir on PATH. PID entries worker_p0/worker_p1/beat in .pids.json; stop-all kills them (process tree) like the other entries; logs in scripts/dev/logs/.
- health.ps1: host claude CLI + version, ping per queue (celery inspect ping -d p0@w / p1@w), exactly one beat process, Docker worker/beat must be absent, per-queue depth from RabbitMQ.
- scripts/dev/proof_extraction.py, README section, apps/desktop/renderer/package-lock.json (+ .gitignore exception); npm ci then works, renderer tests 7 passed.

## Two engine bugs the proof exposed (fixed in apps/memory, tests in tests/test_run_cli_fenced_envelope.py)
1. core/extract.py _run_cli: `claude -p --output-format json` prints one JSON envelope whose `result` is usually a ```json fenced string; the fence stripper ran over the WHOLE stdout and cut inside the envelope -> "model JSON output is not an object". agent-cli extraction with the claude CLI could never have worked. The envelope is now parsed first.
2. privacy/sensitive.py: for agent-cli workers the Rule-9 layer-2 screen needs a local LM Studio classifier model (TM_CLASSIFIER_MODEL) and fails closed (ScreenUnavailable) without it. Added an OPT-IN backend TM_CLASSIFIER_RUNNER=agent-cli (same prompt, same fail-closed contract: any failure raises, an unclassified or mislabelled label comes back "unscreened" = blocking). start-all sets it for the workers unless TM_CLASSIFIER_MODEL is set. PLEASE REVIEW: this is a privacy-path change.

## Proof (synthetic owner, never the founder's account)
Owner synthetic-e1b-708731 (kind simulated), one note record through POST /v1/owners/{id}/records (enqueue extract.day, the path apps/api uses):
- ingest: job_id=job_f63cf3a051eb4e42
- states: t+0s queued -> t+16s leased (host worker p1@w) -> t+156s applied
- attempt row: worker_kind=agent-cli, model=claude-haiku-4-5-20251001, model_observed=claude-haiku-5-5, tokens_in=23562, tokens_out=12801, cost_usd=0.08285, verdict=applied
- facts written: 3 (provenance inferred)
- Forget (record): facts_erased=3, records=1; afterwards 0 unerased facts, record erased_at set

LLM calls made in total: 1 failed (before fix 1), 1 failed at the screen (before fix 2), 2 successful (this run and an earlier leftover synthetic owner with 4 facts, also forgotten). Notes: (a) a call takes about 2 min (claude -p loads a large context, ~24k input tokens); (b) model_observed differs from the requested Haiku 4.5 (the CLI also bills a haiku-5-5 sub-call): validator flags model_mismatch, non-blocking; (c) ENGINE ISSUE, not fixed: Forget soft-erases (erased_at, embedding NULL) but the text columns of records/facts stay in the rows.

## Tests
apps/memory full pytest (memory venv, PYTHONPATH=worktree src): 432 passed, 8 skipped. apps/api full pytest from the worktree: 644 passed, 16 skipped, 0 failed. Desktop renderer: npm ci OK, 7 passed. health after start-all: all rows green (desktop SKIP).

## Not done / caveats
Desktop window not started in this cycle. LM Studio path not exercised (:1234 down). Workers use the contest-memory venv unless apps/memory/.venv exists. Live CS-1 style tests enqueue real extraction jobs: with host workers running they spend subscription calls (I marked 4 leftover test jobs dead).
