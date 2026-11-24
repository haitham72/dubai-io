# P2 — Codex: plug Hindsight, Honcho and edgextract into weekbench

Paste everything below the line into Codex. Working directory: `G:\Haitham\lab-data\memory-bakeoff\` (a git repo; commit after each step).

---

The founder is choosing between four memory options. One is already running on the saved benchmark:

| Config | What it is | Status |
|---|---|---|
| `tn_update` | Own build (updated temporal_note): 1 LLM call per batch → `graph.json` + Quest-style md tree | Done, see `LEADERBOARD.md` |
| `hindsight` | **Real Hindsight server** (Docker) | **You build** |
| `hindsight_honcho` | Hindsight + **real Honcho server** (Docker) as the reflection layer | **You build** |
| `hindsight_honcho_edgex` | The above + edgextract closed Y/N edge verifier | **You build** |

Read first:
- `weekbench/` (≈ 400 lines: `hook.py`, `data.py`, `configs/tn_update.py`, `score.py`, `run.py`);
- `LEADERBOARD.md`;
- `research/libraries.md` §A (Hindsight v1.2.3 facts, verified 23 Nov). Honcho isn't in that file, so read the official Honcho self-hosting docs and repo yourself and cite URLs + version in `weekbench/configs/README.md`;
- edgextract's prompts: `G:\Haitham\lab-data\bench-4tools-30d\tool_edgextract.py`.

## Rules (founder's)

- **Model:** every LLM call goes through the subscription hook: Claude Haiku, medium effort, via `weekbench/hook.py` (already trimmed to about 1k overhead tokens). No API keys. Zero Gemini API calls. Local LM Studio (`http://127.0.0.1:1234/v1`) is allowed for embeddings (`text-embedding-nomic-embed-text-v1.5`) and for edgextract's Y/N verifier (`qwen/qwen3-4b-2507`), because that's how edgextract is designed.
- **Cost is the main criterion.** Every LLM call a library makes must appear in the run's `calls.jsonl` with tokens and `cost_usd`.
- **Simplicity.** Use small adapters. Don't add services beyond what each library needs.
- **Don't edit** `weekbench/score.py`, `weekbench/data.py` or `gold/` (Claude owns scoring; Muse owns gold). Don't touch the contest repo.

## Step 1 — hook proxy (`weekbench/hookproxy.py`)

The libraries call an OpenAI-compatible endpoint, so build a local `/v1/chat/completions` (and `/v1/models`) server on `127.0.0.1:8787` that forwards to `hook.call(...)`:
- system message → system prompt; other messages → the stdin prompt;
- `response_format` json_object / json_schema: put the schema in the system prompt, parse with `hook.extract_json`, and retry once on invalid JSON;
- return an OpenAI-shaped response with `usage`;
- write each call to the **current run's** `calls.jsonl`, tagged with the library name (set via env `BENCH_RUN_DIR`);
- if a library needs native **tool/function calling**, emulate it by asking for a JSON object with the tool arguments and returning a `tool_calls` message. Note which library needed it.
- Bound parallelism with `MAX_PARALLEL` (default 3).

## Step 2 — three config modules in `weekbench/configs/`

Each must expose the same thing `tn_update` does, so `run.py` and `score.py` work unchanged:

```python
def ingest(records: list[dict], batch: str, run_dir: Path) -> tuple[obj, list[dict]]
# obj.graph() -> {"entities":[{id,name,type,aliases,relation_to_user}],
#                 "facts":[{id,text,category,topic,entities,valid_from,valid_to,status,superseded_by,evidence:[record ids]}],
#                 "edges":[{src,rel,dst,valid_from,evidence}],
#                 "quarantine":{"counts":{cat:n},"evidence":[[ids]]}}
# obj.write_md(root) -> int   # Quest-style tree (reuse tn_update.Memory.write_md: move it into weekbench/export.py unchanged)
```

- **`hindsight`:**
  - Real server (pin the image version in `weekbench/docker/hindsight.compose.yml`), LLM = proxy, embeddings = LM Studio.
  - Retain one document per batch (`batch=week` → one doc per source per week; `day` → per source per day). Keep record IDs in the text so facts can cite `evidence`.
  - Map memory units → `facts`; entities → `entities`; entity links → `edges`; Hindsight's changed/ended/observations → `status` / `superseded_by`.
  - The privacy gate is Hindsight's `pre_write` hook (`OperationValidatorExtension.filter_retain_facts`), using the same `SENSITIVE` list and rule as `tn_update` → quarantine.
- **`hindsight_honcho`:**
  - Same as `hindsight`, plus the real Honcho server (Docker; pin the version). Send the same records as peer messages (Karim = user peer, other senders = their own peers).
  - Honcho's role is **reflection**: write `memory/USER.md` (Quest sections: Identity, Personality, Values, Strengths & Tensions, Interests, Drive, Relationships; every claim cites a memory file) and `memory/milestones.json` (`[{title, status: done|in_progress|planned, evidence:[record ids]}]`) from Honcho's representation / dialectic output.
  - Note Honcho's licence in the README as a fact.
- **`hindsight_honcho_edgex`:** same as above, then run edgextract's closed Y/N verifier over the final `edges` (local qwen3-4b). Drop the "no" edges and log the drop count.

## Step 3 — run and commit

```powershell
python weekbench/run.py --config hindsight --batch week --stage week1
python weekbench/run.py --config hindsight --batch day  --stage week1
python weekbench/run.py --config hindsight_honcho --batch day --stage week1
python weekbench/run.py --config hindsight_honcho_edgex --batch day --stage week1
```

Commit after each run (`runs/` is versioned). If a run fails, keep the folder, add `FAILED.txt` with the reason and cost, and continue.

## Report back

1. The `LEADERBOARD.md` rows.
2. Per config: how many LLM calls the **library itself** made per batch, and why (which internal steps).
3. Setup effort: services added, adapter line counts, anything that needed emulation.
4. Failures, verbatim.
