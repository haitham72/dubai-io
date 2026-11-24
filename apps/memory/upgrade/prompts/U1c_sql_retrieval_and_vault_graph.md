# U1c — Postgres retrieval everywhere + `/vault/graph` (after U0a is merged)

Assigned to: **Gemini** (queue `Q_gemini.md`, item 1).

Paste below the line.

---

Read first:
- `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md`. The integrator is **Claude** (verifies on Postgres + the U0b harness, then merges).
- `TN_UPGRADE_PLAN.md` v1: §2 row R3 retrieve, §3, §5 **U1(e–g)** and **§5.1 (graph DTO)**, §6 and **§7 (D-a = the engine's 7 clusters; D-c)**.
- Codex audit **06** and **08** plus its "Graph response and UI" section; Gemini audit **F06**, **F07** and §5 U1; Cursor audit **F3** and **F6**.
- The design: `G:\Haitham\VsCode\contest\design\20-11-2026\Dubai-io Knowledge Graph Vault.jpg`.
- The mobile client: `git -C G:\Haitham\VsCode\contest show ios:apps/mobile/src/features/vault/vaultApi.ts`.

**Sub-agents:** at most 3, cheap tier only: Codex → gpt-6.2 sol, Gemini → a lower tier, Muse → Muse 1.3 Contributor, Cursor → its fast model.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpU1c -b mem-wpU1c memory   # memory must already contain U0a
cd G:\Haitham\VsCode\contest-mem-wpU1c\apps\memory
```

## The problem

Twelve call sites load up to 10,000 facts per request:
- `live/context.py:406`
- `api/bridge.py:280`
- `api/vault.py:92,152,215,264,299,430,587`
- `api/export_md.py:50`
- `reflect.py:117`
- `mcp/server.py:517`

On top of that, MCP search hydrates only the newest 1,000 facts (`mcp/server.py:485`). The result: 287 ms at 20k facts, old facts invisible, and Postgres FTS (0.8 ms) unused.

Other gaps:
- `salience` has no writer.
- There's no graph endpoint.
- Provenance is derived from `status` at `api/vault.py:117,177,250` and `live/context.py:504`, plus hard-coded `user_supplied` envelopes (`vault.py:135,200,323,573,615`, `context.py:546`).

## Owned files (only these)

- new `src/temporal_memory/core/retrieval.py`
- new `src/temporal_memory/api/graph.py`
- `src/temporal_memory/core/graph_store.py` (read methods only)
- `src/temporal_memory/live/context.py`
- `src/temporal_memory/api/vault.py`
- `src/temporal_memory/api/export_md.py`
- `src/temporal_memory/reflect.py`
- `src/temporal_memory/mcp/server.py`
- **one** `include_router` line in `api/app.py`
- tests: `test_live.py`, `test_vault.py`, `test_export.py`, `test_mcp.py`, `test_reflect.py`, new `test_retrieval_postgres.py`, new `test_vault_graph.py`

**Don't touch:** `api/bridge.py` (U1a), `core/applier.py` (U1b).

## Deliverables

1. **`search_candidates` on Postgres (`core/retrieval.py`).** Channels, each a SQL query with a LIMIT over `visible_facts`:
   - FTS (`ts_rank` on the existing GIN `tsv`, which covers `text` + `text_orig`);
   - alias match → `fact_entities`, plus **1 hop** over `links` / `link_evidence`;
   - subject and its descendants;
   - date range from the dates in the question.

   Fuse with RRF and return ~50 candidates, hydrated by ID only. Gemini's ablation got 0.772 / 0.863 at top-8 / top-16 in about 3 ms at 20k on the gold graph: use it as a reference, not a promise.
2. **Replace all 12 load-all sites plus MCP's 1k hydration:**
   - search and context → ranked candidate IDs;
   - `/why` → exact `get_facts`;
   - counts → SQL aggregates;
   - timeline / export / reflect → `iter_visible_facts` windows or cursors.

   Context keeps its pack shape and its ≤ 1.5k-token budget. Its cache is keyed by `facts_version` **and** `privacy_revision`.
3. **Provenance from storage.** Read `entities.provenance` / `subjects.provenance` (U0a / U1b) at all 4 sites, and remove the hard-coded envelopes. Inferred items are returned with `review_state` so the app can show "I noticed" + Confirm / Edit / Not true / Forget.
4. **`salience`,** computed in SQL at read time from mentions in the last 30 days, recency and confirms (plan formula `0.5·log(1+mentions_30d) + 0.3·recency + 0.2·taps`), decaying to a floor.
5. **`GET /v1/owners/{o}/vault/graph?view=subjects|people`** per plan §5.1. It is versioned and owner-scoped, centred on the owner, with stable IDs.
   - **Subjects** = the engine's **7 clusters** (`LIFE_SPINES`); health and faith are never clusters.
   - **People & Places** = people, places, orgs and **projects** (today `/vault/people` drops projects and events).
   - `counts` are computed over the same Rule-9-gated projection, before capping; `+N more` is `hidden_by_group`; no orphan edges.
   - The **People & family** cluster and any family edge use only `user_supplied` / confirmed facts.
   - `tier` = `closeness_tier` (confirmed). `closeness_suggested` is returned separately as an "I noticed" suggestion.
   - Add **`POST /v1/owners/{o}/vault/people/{entity_id}/tier`** `{tier: "T1"|"T2"|"T3"|null}`: the user's confirm. It writes `closeness_tier` + `tier_confirmed_at`, owner-auth only.
   - `/vault/subjects` and `/vault/people` stay backward-compatible for `ios:vaultApi.ts`.
6. **Tests on Postgres at 20k synthetic facts (temporary schema), happy + failure paths:**
   - the 2015 needle is found;
   - context and search p95 < 150 ms, graph p95 < 150 ms (n ≥ 100, measured in-process plus one HTTP run; report both);
   - no orphan edges;
   - a hidden sensitive item doesn't affect any count;
   - an auto-promoted place shows as `inferred`;
   - a cross-owner graph request → 403;
   - the tier endpoint writes only on the owner's call.

**Done when:** the full suite is green, the 20k Postgres tests pass with the latency numbers reported, and a sample `/vault/graph` response for both views is saved in your report, so the UI agent can build against it. Commit on `mem-wpU1c`. Report: branch, files, test counts, p50/p95 table, the DTO sample, contract requests.
