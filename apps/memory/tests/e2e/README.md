# Memory Docker tests

Run from `apps/memory` with Python 3.12+, Docker Compose v2.24.4+, and the synthetic `memory-bakeoff/gold` corpus. The tests create a separate Compose project, publish ephemeral loopback ports, and remove the project volumes after the run. They leave the shared development stack available for the unit suite.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev,cloud,mcp]'
$env:TM_E2E_GOLD_DIR = 'G:\Haitham\lab-data\memory-bakeoff\gold'
$env:TM_RUN_E2E = '1'
.\.venv\Scripts\python.exe -m pytest -q -m e2e
```

The gold test loads all five sources via `tm import --no-split` and enqueues one `import.split` job. The oracle runs in the Celery containers and uses each packet's evidence IDs to find the corresponding ledger entries. The assertions account for the CLI's triage and the validator's privacy holds. They check the primary subject, evidence available within the day, and ledger roles with fact evidence. The test projects the ledger's facts as dated inserts.

The separate live test makes one Claude CLI call on one synthetic day. It uses the installed CLI's sign-in and logs the validation verdict, model, input and output tokens, and the CLI-reported cost.

```powershell
$env:TM_RUN_LIVE_LLM = '1'
.\.venv\Scripts\python.exe -m pytest -q -s -m live_llm
Remove-Item Env:TM_RUN_LIVE_LLM
```
