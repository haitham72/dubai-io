# `temporal_memory` Acceptance Harness (`S1`–`S10`)

Self-contained acceptance suite for `apps/memory` running against live Postgres (isolated temporary `acc_*` schemas that self-drop on exit) and an in-process FastAPI `LiveApiServer`.

## Prerequisites

1. **Postgres on `:5442`** with `pgvector` enabled (`TM_TEST_DATABASE_URL`, default `postgresql://tm:tm@localhost:5442/tm`).
2. **Python `.venv`** in `apps/memory/.venv` (with `apps/memory` + `[cloud,semantic]` dependencies installed). Override with `-Py <path>` if needed.
3. **Claude CLI** (required for **S2** extraction/judge and **S8** extraction probe): `claude` on `PATH` or `CLAUDE_EXE` env var (defaults to `~/.local/bin/claude.exe`).
4. **Optional (`S4` cross-repo bridge contract):** set `CS_API_DIR` and `CS_PY` if `contest-shared` (`apps/api` with `app/memory_bridge`) is not at a sibling worktree path; otherwise `S4` records a clean `SKIPPED` result after running auth-isolation checks.

## Running

From `apps/memory/acceptance/`:

```powershell
# Full suite (S1..S10) against HEAD
.\run.ps1

# Specific suites (comma-separated)
.\run.ps1 -Only S1,S9
.\run.ps1 -Only S9,S10

# Skip LLM-backed extraction suite S2
.\run.ps1 -SkipS2

# Validate gold dataset integrity
..\.venv\Scripts\python.exe .\gold\validate.py
```

## Suites

- **S1** (`s1_retrieval.py`): 40-probe retrieval quality (gold + extracted graph) across `/context`, `/search`, and MCP `memory_search` + 1k/5k/20k latency & concurrent-writer check.
- **S2** (`s2_extract_cost.py`): Full 31-day + late-packet extraction via `PostgresJobs` + Haiku judge (cost, recall/precision, changes, Rule 9 privacy).
- **S3** (`s3_forget.py`): Forget completeness across `/forget`, `forget_source()`, warm `context_pack` cache, in-flight job fencing, `entities`/`aliases`/`links`/`subjects.fact_count`, and export.
- **S4** (`s4_bridge_pg.py`): `HttpTemporalMemoryClient` and `MemoryBridge` contract on live Postgres.
- **S5** (`s5_rule9.py`): Rule 9 quarantine isolation, auto-promoted entity provenance, and sensitive-category export/subject gating.
- **S6** (`s6_graph.py`): `/vault/graph?view=subjects|people`, 7-cluster mapping, T1 tier confirmation, and 20k graph latency.
- **S7** (`s7_traps.py`): 84-item EN/AR/ARZ live-triple trap dataset validation (`TRAPS.md`, `traps_dataset.json`).
- **S8** (`s8_places_topics.py`): R6 place retrieval and 2-session topic hypothesis probe.
- **S9** (`s9_why_story.py`): U5 `/why/{fact_id}` evidence/reason spans and `/story` deterministic/narrated grounding, Postgres `story_cache`, Forget invalidation, and auth isolation.
- **S10** (`s10_hybrid_ablation.py`): U4 hybrid search ablation (keyword-only vs hybrid on gold + 20 `paraphrase_probes.json`) and 20k HNSW vs exact vector benchmark.

## Data Policy & Outputs

- **Synthetic-only guarantee:** `gold/`, `traps_dataset.json`, and `paraphrase_probes.json` contain strictly synthetic personas and fixtures (Karim Haddad), with zero real names or personal paths.
- **Results gitignored:** `run.ps1` writes JSON artifacts and `REPORT.md` to `apps/memory/acceptance/results/<timestamp>/`, which is ignored via `apps/memory/.gitignore`.
