# B-AD — Gemini: core engine (WP-A), then ingest + MCP + owner hooks (WP-D)

Paste below the line into **Gemini**.

---

You built WP-B (merged into the integration branch `memory`). You now own **WP-A, then WP-D**, back to back without waiting. Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and follow it.

## Part 1 — WP-A core engine

Spec: `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B-A_codex_core.md` (all 8 steps and its test list).

```powershell
cd G:\Haitham\VsCode\temporal-memory
git worktree add ..\temporal-memory-wpA -b wpA memory    # memory = 38cf3cb (has WP-B + WP-C + contract v1.1)
```

> **If `temporal-memory-wpA` already exists** (started from the older base `184fae1`), keep working there. Commit your work, then run `git merge memory` inside it to pick up WP-B, WP-C and contract v1.1. The files don't overlap, so it should merge cleanly. **Never commit to or merge into `main`**: it belongs to the project orchestrator.

Changes to that spec, because `memory` moved on:

1. **Privacy is real now.** Call `temporal_memory.privacy.policy.gate_fact` and `may_promote`, and `privacy.forget.forget_source` (Muse, WP-C). No shim.
2. **Contract v1.1:** your Postgres store must implement **`GraphStoreFull`** in `models.py`. Every method listed there has `tests/fixtures/fake_store.py` (your own fake) as its reference. Add a test that runs your WP-B tests (`test_live`, `test_vault`, `test_export`, `test_reflect`) **against the Postgres store too**, parametrised fake vs real.
3. **`api/app.py`** wires your WP-B pieces:
   - `api.vault.configure(store=…, auth_verifier=…)` returning `AuthContext(role, owner, token_id)` from the tokens table (admin / worker / owner-device);
   - `set_default_store` for `live.context`, `reflect` and `api.export_md`;
   - mount the vault/export/ops routers plus the worker endpoints from B-A step 8.
4. **Fix your own `reflect.py`:** it currently checks only regex layer 1 (`_check_sensitive` → `filter_statement`). Plan §6.4 requires **layer 2 on every reflect output**, so route claims and milestones through `policy.gate_fact(…, worker_kind=…)` with layer 2 on, failing closed.
5. **Known red test:** `tests/test_reflect.py::test_reflect_week_enforces_two_days_trivia_and_rule9` fails on `memory` because the gate wrongly treats "wedding" as sensitive. **Muse is fixing the gate (B-C2).** Don't change that test or the gate. Leave it failing in your report.
6. **Don't touch** `privacy/` or `tests/test_privacy.py`: Muse is editing them right now.

**Checkpoint:** commit on `wpA`, then post a short report (files, test counts, contract requests). Then go straight to Part 2.

## Part 2 — WP-D ingest + MCP + owner hooks

Spec: `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B-D_codex_mcp_hooks.md` (all 6 steps and its test list).

```powershell
cd G:\Haitham\VsCode\temporal-memory
git worktree add ..\temporal-memory-wpD -b wpD wpA
```

Changes to that spec:

- Reuse the **tokens table and auth verifier you built in Part 1** (one token system for API and MCP).
- `hooks/agent_worker.py` is what the founder's later "simulated users" run will use: Gemini / Muse / Codex / Qwen each claim **one owner's week** via a worker token and report their **model name**. Make `--model` mandatory and echo it into every attempt.
- `tm import` must accept a real export path outside the repo (e.g. `G:\Haitham\lab-data\…`). **Never copy real data into the repo or into test fixtures.**
- You may call the agent CLIs only in docs/examples. Tests use canned outputs, and there are **no Gemini API calls in extraction code**.

**Final report:** both branch names, test counts per branch, contract requests, and anything you couldn't finish.
