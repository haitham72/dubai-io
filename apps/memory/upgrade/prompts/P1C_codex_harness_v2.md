# P1C — Codex: harness v2 + baselines B0/B1 + scorer

Paste everything below the line into Codex. Run it with working directory `G:\Haitham\lab-data\memory-bakeoff\`.

---

Build **harness v2** for a memory-library bake-off. Read `PLAN.md` in this folder first (§1 goal, §3 contestants, §4 MemoryInsight contract, §5 decision rule). The previous harness is `G:\Haitham\lab-data\bench-4tools-30d\`. Reuse what's good there: `embeddings.py`, and the extraction and 4-way verdict prompts in `tool_hindsight.py`. Three audits list its flaws; fix all of them:
- `G:\Haitham\lab-data\bench-4tools-30d\claude_auditRview.md` §1;
- `muse_spark_auditRview.md` §J;
- `gpt62_auditRview.md` §1.

## Build under `harness/`

1. **`adapter.py`** with this interface. Every contestant implements it.
   ```python
   class MemoryAdapter:
       name: str
       def reset(self) -> None
       def ingest(self, records: list[Record]) -> IngestStats      # backfill; Record = {record_id, source, source_id, ts, author, text}
       def live_turn(self, text: str, ts: str) -> MemoryInsight     # blocking part only; async work may continue
       def drain(self) -> None                                      # wait until async work is searchable
       def recall(self, query: str, k: int = 8) -> list[Hit]        # Hit carries record_ids for gold mapping
       def forget_source(self, source_id: str) -> None
   ```
2. **`hookproxy/` + `llm.py`**: the founder's rule is **subscription CLI hooks, medium effort, no API keys.**

   **The hook proxy** is a local OpenAI-compatible server (`http://127.0.0.1:8787/v1/chat/completions`, FastAPI or similar) that forwards each request to a CLI:
   - **Startup probe:** try `codex exec -m gpt-6.2-luna -c model_reasoning_effort="medium" --ephemeral -s read-only --skip-git-repo-check`. On 23 Nov it fails with "not supported when using Codex with a ChatGPT account". If it fails, use **`claude -p --model haiku --effort medium --output-format json --system-prompt <system message>`** with the user/assistant messages as the prompt. Log which backend is active.
   - **Don't use `--bare`.** It skips the subscription login and fails with "Not logged in".
   - **Cut per-call overhead (measured 23 Nov, mandatory):** the default call carries about 46k tokens of Claude Code tools and MCP, about $0.0035 per call at API rates. Trimmed, it's about 1k tokens and $0.0004. Use exactly:
     `claude -p --model haiku --effort medium --output-format json --system-prompt "<system>" --strict-mcp-config --mcp-config empty_mcp.json --tools "" --disable-slash-commands`
     with `empty_mcp.json` = `{"mcpServers":{}}`.
     - Send the prompt **via stdin**, not as an argument: `--tools ""` swallows a positional prompt.
     - stdout can start with warning lines, so parse the first `{` … last `}`.
     - Log `total_cost_usd` from every response (the API-equivalent cost) and sum it in the scoreboard.
   - **Structured output:** when a request has `response_format` (`json_object` or `json_schema`, which Graphiti and Mem0 use), inject the schema into the system prompt, extract JSON from `result`, validate against the schema, and retry once with the validation error. Return a proper OpenAI response shape with `usage` mapped from the CLI JSON.
   - **Concurrency:** `MAX_PARALLEL` env, default 4 parallel CLI processes. Queue the rest and back off on rate-limit errors.
   - **Per-call log** (`results/calls.jsonl`): backend, model, wall ms, `duration_api_ms` (model time), tokens (input / cache read / cache create / output), ok or fail, retries.

   **`llm.py`** is the harness's own OpenAI client, pointed at the proxy by default (`BASE_URL`, `MODEL` env). LM Studio (`http://127.0.0.1:1234/v1`) stays selectable for the later fast-extractor sweep and is always used for embeddings.
3. **`gate.py`**: a `pre_write(fact) -> allow | quarantine(category)` hook. Wrap `g:\Haitham\VsCode\contest\apps\api\app\lab\sensitive.py` layer 1 **read-only**: import it, don't edit the repo. Add, in the harness only:
   - a `family_third_party` category (a fact whose subject is a person other than the user, carrying health, faith, relationship, money or legal content);
   - word boundaries on the Arabic patterns;
   - allowlists for "Sheikh <Name>", "Golden/Green Visa", "government entity", "Dubai Police" (as a provider).

   Quarantined facts store category + count + `record_id` only, never the text.
4. **`b0_raw.py`** (B0): chunk records (one email, or a WhatsApp window of about 20 messages), embed, BM25 + vector RRF. `live_turn` uses the shared composer (item 6).
5. **`b1_custom.py`** (B1, "Hybrid-1P"): SQLite stand-in for the Postgres schema (`sources`, `memories`, `entities`, `entity_aliases`, `links`, `milestones`, `forget_rules`, `outbox`).
   - **Backfill:** per-source triage rules (drop promos/OTP/newsletters by sender and header heuristics), then **one** extraction call per batch (≤ 8 emails, or a WhatsApp day-window ≤ 1,500 tokens). The call gets the **top-5 RRF neighbours per batch** (not the oldest rows) and returns facts + entities + edges + `effect` + `target_id`.
   - **Live:** blocking = retrieval + one call returning the MemoryInsight; extraction writes go to the outbox and `drain()` processes them.
   - Alias resolution: Arabic folding + lowercase + a known-alias table, with an LLM merge proposal only on a miss.
   - Late-arriving older facts must never overwrite a newer `valid_from`.
6. **`composer.py`**: a shared single LLM call that turns any adapter's raw outputs (nodes, edges, events, recall hits) into a MemoryInsight. Mark each field `native` or `composed`.
7. **`score.py`**: reads `gold/probes.json` and `gold/ledger.json` (Muse is building these in parallel; until then use a 5-probe fixture you write in `harness/fixture/`, clearly labelled as a fixture). Map each adapter's memories to ledger fact IDs through `record_ids`. Compute the §5 metrics exactly:
   - contradiction F1 (target + verdict);
   - person + relation accuracy;
   - subject-link accuracy;
   - context recall@8;
   - `must_not_contain` violations;
   - gated-count correctness;
   - live blocking p50/p95;
   - time-to-searchable;
   - backfill seconds and tokens per 1,000 records;
   - the Forget test (forget one source, then assert zero recall hits from it).

   Arabic probes are scored separately. Output `results/<adapter>_<run>.json` + `results/scoreboard.md`.
8. **`run.py --adapter b0|b1 --runs 3`.**

## Constraints

- Work only inside `G:\Haitham\lab-data\memory-bakeoff\`. Read the contest repo, but never write to it. Never touch `apps/web/` or any `design/references/quest/` or `_archive/quest-*` file.
- No mocks reported as results. Fixture runs are labelled `fixture` in every output.
- Don't add L1–L3 library adapters yet. That's P2, after the library research lands.

## Done when

- The hook proxy passes a smoke test: one plain call and one `json_schema` call return valid OpenAI-shaped responses. Report the per-call overhead tokens before and after disabling tools.
- `python harness/run.py --adapter b1 --runs 1` and `--adapter b0` complete on the fixture **through the proxy (Haiku, medium)**.
- `scoreboard.md` shows every §5 metric, with latency as both model time and wall time.

Report the commands you ran and the scoreboard, plus anything that failed.
