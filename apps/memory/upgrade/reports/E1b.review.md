# E1b review (verifier, 2026-11-24)
Verdict: MERGED into main 7fc38fb (e92c872). No blocking findings.
Scope: scripts/dev/* (start-all, stop-all, health, README, proof_extraction.py), apps/memory (core/extract.py envelope fix, privacy/sensitive.py agent-cli classifier, tests/test_run_cli_fenced_envelope.py), apps/desktop/renderer/package-lock.json, .gitignore exception. Nothing else. apps/web untouched. Secrets grep on added lines: clean.

## Checklist
- A.a PRIVACY OK. privacy/sensitive.py:261-291 `_agent_cli_classifier`; opt-in only via TM_CLASSIFIER_RUNNER=agent-cli (sensitive.py:303-305; library default stays LM Studio; start-all sets it only when TM_CLASSIFIER_MODEL is unset). Layer-1 filter_statement still runs after layer 2 (sensitive.py ~320). Sends only SCREEN_SYSTEM + short extracted labels (not record text), a strict subset of what extraction sent to the same Haiku CLI. Fail-closed: timeout/CLI error/empty or unparseable stdout/is_error -> ScreenUnavailable (sensitive.py:288-289); skipped or unknown label -> "unscreened" (blocking, :291). Text never logged (exception strings carry only json/CLI messages). Tests: test_agent_cli_classifier_fail_closed, _outage_raises.
- A.b OK. extract.py:566-570 parses the whole stdout as the envelope first, then the inner `result` goes through the fence stripper (:586). Fenced covered by test_fenced_result_inside_envelope_parses_and_records_cost; unfenced covered by the pre-existing runner tests via the same `_extract_json_dict` path (no dedicated new unfenced test: non-blocking).
- A.c OK. start-all.ps1:250-260 starts only `api` in Docker then `docker compose stop worker-p0 worker-p1 beat`; host workers p0 (solo), p1 (threads) + exactly one beat (:315-317). health shows no-docker rows green, host beat count 1. stop-all.ps1:28-36 kills only PIDs from .pids.json; 8766/8767/8768 PIDs identical before/after.
- A.d CLI flags: `claude -p --model <model> --effort medium --output-format json --tools "" --disable-slash-commands`, prompt via stdin (subprocess input=), no --bare, cwd = apps/memory (Start-Process -WorkingDirectory $MemDir; classifier inherits the worker's cwd). MISSING (non-blocking): `--strict-mcp-config --mcp-config <empty json>`. Defined in config.py:19-22 and start-all.ps1 TM_AGENT_CLI_CMD. cwd inside the repo means the repo CLAUDE.md is auto-loaded by claude -p: consider running from a neutral dir.

## Tests (throwaway worktree, main + A)
apps/memory 432 passed / 8 skipped; apps/api 644 passed / 16 skipped; renderer npm ci + 7 passed. Stack cycle (start-all -> health -AllowStoppedDesktop -> stop-all -KeepInfra): 20/20 rows GREEN incl. desktop; ports 8766/8767/8768 unchanged; postgres/rabbitmq/redis running afterwards. Live extraction proof not re-run (evidence reviewed in E1b.md).

## Non-blocking notes
- stop-all kills any alive PID in .pids.json (PID reuse after reboot could hit an unrelated process).
- Classifier treats an item with a number but no `category` as "none" (parity with the LM Studio classifier; layer 1 still screens it).
- start-all itself keeps running (does not exit) after printing "Done" when launched hidden via Start-Process; use health.ps1 to detect completion.
