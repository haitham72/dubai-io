# Common rules for every build agent (included by B-A, B-B, B-C, B-D)

- **Repo:** the Dubai-io repo `G:\Haitham\VsCode\contest`. The memory engine lives in **`apps/memory/`** (package `temporal_memory`) on the **`memory`** branch, which is checked out at `G:\Haitham\VsCode\contest-memory`. Read `apps/memory/README.md` and `apps/memory/CLAUDE.md` first. The root `CLAUDE.md` rules apply too.
- **Plan:** `G:\Haitham\lab-data\memory-bakeoff\planaudit.md`, **v2.1**. The v2.1 box at the top sets the location.
- **Contract:** `apps/memory/src/temporal_memory/models.py`. Implement the signatures exactly. Need a change? List it under "Contract requests" in your report. Don't edit `models.py`.
- **Your own worktree** (agents never share a working tree):
  ```powershell
  git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wp<X> -b mem-wp<X> memory
  cd G:\Haitham\VsCode\contest-mem-wp<X>\apps\memory
  ```
  Commit only on your branch, and only files under `apps/memory/`. The integrator (Claude) merges into **`memory`**. **Never commit to or merge into `main`**: it belongs to the project orchestrator. Never touch `apps/web` or any other app.
  - **Never edit anything in the folder `G:\Haitham\VsCode\contest` itself.** It's the `main` checkout of the project orchestrator. That includes docs: `PLAN.md`, `docs/`, everything. If your task needs a doc change, make it **in your own worktree** and commit it on your branch.
  - **Already mid-task in an old `G:\Haitham\VsCode\temporal-memory-wp*` worktree?** Finish and commit there; the integrator imports your branch into `memory`. Use the new layout only for your next task.
- **Environment:** in `apps\memory` of your worktree, `python -m venv .venv`, then `pip install -e ".[dev,cloud,mcp]"`. Infra: `docker compose up -d postgres rabbitmq redis`, run from `G:\Haitham\VsCode\contest-memory\apps\memory` (one shared stack; ports 5442 / 5682 / 6390).
- **Tests:** `python -m pytest -q`. DB tests use `TM_TEST_DATABASE_URL=postgresql://tm:tm@localhost:5442/tm` and must **create and drop their own schema** per session (e.g. `tm_test_<uuid>`), because other agents run tests at the same time. Every module ships fixtures plus a happy-path and a failure-path test.
- **Data:** synthetic only. Copy small slices of `G:\Haitham\lab-data\memory-bakeoff\gold\` (fictional persona "Karim") into `tests/fixtures/`. No real personal data in the repo, ever.
- **Reuse from the Dubai-io repo (read-only; port, don't import):** `g:\Haitham\VsCode\contest\apps\api\app\lab\` and `G:\Haitham\lab-data\memory-bakeoff\weekbench\`. Note the source path in a comment at the top of each ported module.
- **LLM:** only through `core/extract.py` runners. Tests use canned outputs and never call a real model. Model ids come from env/config. **No Gemini API calls in production extraction.**
- **Truth rules** (repo `CLAUDE.md` §5): provenance + `as_of` everywhere; inferences are hypotheses; family, health and faith are never inferred; third parties are never auto-promoted; Forget is the only delete.
- **Sub-agents:** use them when work splits; roles and rules in `prompts/SUBAGENTS.md`. You remain the only one who commits.
- **Scoring/benchmarking is NOT your job.** It's phase P5, last.
- **Report back (short):** your branch name, files added, test counts (pass/fail), contract requests, known gaps.
