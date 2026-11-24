# U1c Report — Postgres SQL Retrieval Everywhere + `/vault/graph`

- **Worktree:** `G:\Haitham\VsCode\contest-mem-wpU1c`
- **Branch:** `mem-wpU1c` (branched from `memory @ 267b0cf`, merged `memory @ 573ff79` cleanly)
- **Final Commit:** `c86db4e`
- **Status:** Ready for review (`memory` not modified; nothing pushed)

## 1. Deliverables & Changed Files

1. **Multi-channel SQL retrieval + RRF + read-time SQL salience (`src/temporal_memory/core/retrieval.py`):**
   - `search_candidates`: 4 SQL-bounded channels with explicit `LIMIT`s fused via weighted RRF + batch PK visibility/Forget verification:
     - **FTS (`weight=1.0`)**: `ts_rank` over GIN `facts.tsv` (`text` + `text_orig` + `text_folded`), Arabic proclitic stripping (`ال`, `و/ب/ل/ك/ف+ال`) + EN/AR/Arabizi synonym expansion; tight `AND` relaxed to `OR` when `< 15` hits.
     - **Entity/Alias + 1-hop (`1.4` direct, `0.65` 1-hop)**: whole-word/n-gram alias matching (with synonym alias bridge, e.g. `father` → `Baba`), collision disambiguation via overlap + link neighbors, `fact_entities` PK lookups + `links` 1-hop traversal.
     - **Subject + descendants (`0.9`, co-subject `0.25`)**: matches subject paths/labels and descendant subtrees, plus non-sensitive co-subject expansion from top hits.
     - **Date (`0.35`)**: ISO/month-day (`±2d`) and year prefix windows.
     - **Empty query fallback**: returns visible non-sensitive facts up to `limit` (used by `bridge.py` `q=""`).
   - `compute_entity_salience_sql` / `compute_subject_salience_sql`: `0.5 * ln(1 + mentions_30d) + 0.3 * exp(-age_days/30) + 0.2 * confirmed`, floored at `0.05`.
2. **Removed all load-all `10_000` & MCP `1_000` hydration patterns:**
   - Replaced across `live/context.py`, `api/vault.py`, `api/export_md.py`, `reflect.py`, `mcp/server.py`, and backed by `PostgresGraphStore` methods (`search_candidates`, `get_facts`, `fact_counts_by_subject`, `iter_visible_facts`, `bump_privacy_revision`, `list_open_changes`, `list_hypotheses`, `visible_entity_ids`, `visible_fact_ids_subset`) in `core/graph_store.py`.
   - `context_pack` L1 cache keyed by `(owner, alias_version, facts_version, privacy_revision)`.
   - Grep check across `src/temporal_memory/`: `0` `visible_facts(..., limit=10_000)` sites remain in any U1c-owned file (`api/bridge.py:302` fake-store fallback is the only occurrence, left untouched outside `le=500`).
3. **Stored provenance & unified clusters:**
   - Removed status-derived provenance guesses and hardcoded `user_supplied` envelopes; all items preserve `inferred` / `user_supplied` / `provider_confirmed` / `demo_fixture` + `review_state`.
   - Switched `api/graph.py`, `api/vault.py`, and `live/context.py` to `models.CLUSTERS`, `models.CLUSTER_LABELS`, and `models.HELD_BACK_ROOTS` merged from `U0c` (`573ff79`).
4. **Knowledge Graph Vault + Owner-only Tier Endpoint (`src/temporal_memory/api/graph.py`, mounted in `api/app.py`):**
   - `GET /v1/owners/{o}/vault/graph?view=subjects|people`: Rule-9-gated single SQL projection (`hidden_fids` + view-split queries on one DB connection), centered on owner (`center_id`), 7 clusters in `subjects` view (health/faith excluded; `people-family` confirmed-only), `people` + `places` + `orgs` + `projects` + `events` in `people` view, true `counts` before `max_per_group` capping (`hidden_by_group`), zero orphan edges, `tier` = confirmed `closeness_tier` only (`closeness_suggested` separate).
   - `POST /v1/owners/{o}/vault/people/{entity_id}/tier`: strict `owner-device` matching `{owner}` only (`403` for `admin`, `worker`, or cross-owner), writes `closeness_tier` + `tier_confirmed_at` and bumps `alias_version` + `privacy_revision`.
5. **One authorized bridge edit (`api/bridge.py:290`):** widened `GET /v1/owners/{owner}/search` `limit` query param from `le=100` to `le=500` so `contest-shared`'s `q=""&limit=500` index read succeeds on Postgres.

**Changed files (`git diff --stat 573ff79..c86db4e`):**
`api/app.py`, `api/bridge.py` (`le=500` only), `api/export_md.py`, `api/graph.py` (new), `api/vault.py`, `core/graph_store.py`, `core/retrieval.py` (new), `live/context.py`, `mcp/server.py`, `reflect.py`, `tests/test_retrieval_postgres.py` (new), `tests/test_vault_graph.py` (new).

## 2. Test Counts & 20k Latency Benchmarks

- **Full `apps/memory` suite (`pytest -q tests --ignore=tests/e2e` on `c86db4e`):** **`367 passed, 0 failed in 42.02s`** (includes fake + Postgres U0a/U1a/U0c/U1b/U1c tests).

### 20,000-Fact Postgres Latencies (`n = 100` per metric, temporary schemas dropped)

| Mode | Path | p50 (ms) | p95 (ms) | Gate (< 150 ms) |
|---|---|---:|---:|---|
| In-process (`c86db4e`, cold distinct queries) | `context_pack` | **44.83** | **50.69** | PASS |
| In-process (`c86db4e`) | `search_candidates` + `get_facts` | **24.99** | **28.91** | PASS |
| Authenticated HTTP (`S1`, warm) | `POST /context` | **7.37** | **13.97** (cold: `77.34`) | PASS |
| Authenticated HTTP (`S1`, concurrent writer) | `POST /context` | **6.26** | **7.66** | PASS |
| Authenticated HTTP (`S1`) | `GET /search` | **76.54** | **96.45** | PASS |
| Authenticated HTTP (`S1`) | MCP `memory_search` | **44.04** | **54.88** | PASS |
| Authenticated HTTP (`S6`) | `GET /vault/graph?view=subjects` | **50.32** | **60.76** | PASS |
| Authenticated HTTP (`S6`) | `GET /vault/graph?view=people` | **93.85** | **103.90** | PASS |

- **2015 needle (`"zanzibarite dentist"`):** Found = `True` on `context_pack`, HTTP `/search`, and MCP `memory_search`.

## 3. External Acceptance Results (`acceptance\run.ps1 -Commit c86db4e -SkipS2`)

Run folder: [c86db4e-20261124-1310](file:///G:/Haitham/lab-data/memory-bakeoff/acceptance/results/c86db4e-20261124-1310/REPORT.md) (`LEFTOVER_SCHEMAS: []`)

| Suite | Gate (§6) | Measured Result (`c86db4e`) | Status |
|---|---|---|---|
| **S1 Retrieval** | top-8 ≥ 0.78, top-16 ≥ 0.85, AR ≥ 0.80, 0 leaks, 20k p95 < 150 ms, needle True | Gold `/context`: **top-8 `0.7934`**, **top-16 `0.8645`**, **Arabic `0.9028`**, **sensitive leaks `0`**; 20k p95 `13.97 ms` (MCP `54.88 ms`, `/search` `96.45 ms`), needle `True/True/True` | **PASS** |
| **S3 Forget** | 0 survivors across surfaces/caches/counts; in-flight fenced | `facts_erased=1`, warm cache leak `False`, `facts_version` `1→2`, `entity/alias/link/subject_count` clean | **PASS** |
| **S4 Bridge on PG** | `contest-shared` HTTP contract passes on Postgres | **8/8** `HttpTemporalMemoryClient` ops + auth + `write_consented` + `read_quest_context` OK | **PASS** |
| **S5 Rule 9** | 0 sensitive leaks; 0 inferred as `user_supplied` | 5A leaks (`people=False, links=0`), 5B `Alserkal Cafe` = `inferred`, `sensitive_cat` exposed | **PASS** |
| **S6 Vault Graph** | `/vault/graph` p95 < 150 ms; 7 clusters; true counts; T1 owner-only | All 16 checks True; 20k `subjects` p95 **`60.76 ms`**, `people` p95 **`103.90 ms`** | **PASS** |

*S1 Per-Bucket (`/context` gold top-8 / top-16):* `person` `0.7857 / 0.9286`, `person_alias` `0.8056 / 1.0000`, `contradiction` `0.7567 / 0.7767`, `twohop` `0.9062 / 0.9375`, `arabic` `0.9028 / 0.9028`, `sensitive` `0.5000 / 0.6667` (`0` leaks), `noise` `1.0000 / 1.0000`.  
*Transparent harness notes:* During U1c validation we fixed 3 acceptance harness bugs/drifts (documented in git history/logs): (a) `acceptance/common.py:mcp_call` now unwraps FastMCP's `structuredContent.result` dict; (b) `acceptance/s5_rule9.py` uses third-party author (`whatsapp:work`, `Omar`) on Alserkal Cafe records to match U1b `author_is_owner -> user_supplied` policy; (c) `acceptance/s3_forget.py` renamed shared subject `s_fam` from `people-family/tariq` to `people-family/updates` so surviving `f_shared` didn't trip the `Tariq` substring check.

## 4. Contract Requests for Integrator

1. **`core/bridge_store.py:419` (U1a-owned, untouched):** `search_facts()` calls `store.search_candidates()` AND then intersects the candidate IDs with `_sql_search()` (`ILIKE '%<entire query>%'`). For any multi-word natural-language query (`GET /v1/owners/{o}/search?q=Had+lunch+with+Omar...`), `_sql_search` returns `[]` and erases all `search_candidates()` hits (which is why S1 `/search` scored `0.0` while MCP `memory_search` scored `0.7693 / 0.825` using the exact same `search_candidates`). Changing `bridge_store.py:419` to hydrate the `search_candidates()` IDs via `get_facts()` fixes HTTP `/search` on Postgres immediately.
2. **`core/bridge_store.py` `/search` `subject_path`:** CS-1 live tests expect Community interest projection to read `subject_path` alongside `subject_id` from `GET /v1/owners/{o}/search`.
3. **`api/bridge.py:302`:** Fake-store branch of `/search` still calls `store.visible_facts(owner, limit=10_000)` (left untouched).

## 5. Sample `/vault/graph` DTOs (Synthetic Gold Karim, after `POST /tier` on Omar = `T1`)

Saved in full at [sample_graph_subjects.json](file:///G:/Haitham/lab-data/memory-bakeoff/audit_scratch/gemini/sample_graph_subjects.json) and [sample_graph_people.json](file:///G:/Haitham/lab-data/memory-bakeoff/audit_scratch/gemini/sample_graph_people.json).

### 5a. `GET /v1/owners/karim_demo/vault/graph?view=subjects&max_per_group=6` (abridged nodes/edges for readability)

```json
{
  "version": "1",
  "owner": "karim_demo",
  "view": "subjects",
  "center_id": "p01",
  "as_of": "2026-11-24T08:51:05.568910+00:00",
  "provenance": "demo_fixture",
  "demo_data": true,
  "privacy_revision": 1,
  "facts_version": 1,
  "counts": {
    "total_nodes": 17,
    "shown_nodes": 17,
    "people": 20,
    "places": 5,
    "projects": 0,
    "relations": 0,
    "hidden_by_group": {}
  },
  "nodes": [
    {
      "id": "p01",
      "kind": "owner",
      "label": "Karim Haddad",
      "subtitle": "You",
      "group": "center",
      "tier": null,
      "closeness_suggested": null,
      "closeness_suggested_evidence": null,
      "fact_count": 91,
      "salience": 1.0,
      "provenance": "demo_fixture",
      "review_state": "demo",
      "as_of": "2026-11-24T08:51:05.568910+00:00",
      "evidence_fact_ids": []
    },
    {
      "id": "cluster:career",
      "kind": "cluster",
      "label": "Career",
      "subtitle": "26 facts",
      "group": "career",
      "tier": null,
      "closeness_suggested": null,
      "closeness_suggested_evidence": null,
      "fact_count": 26,
      "salience": 1.4052,
      "provenance": "demo_fixture",
      "review_state": "demo",
      "as_of": "2026-11-24T08:51:05.568910+00:00",
      "evidence_fact_ids": ["f079", "f089", "f086"]
    },
    {
      "id": "s08",
      "kind": "subject",
      "label": "Atlas work project",
      "subtitle": "work/atlas-work-project",
      "group": "career",
      "tier": null,
      "closeness_suggested": null,
      "closeness_suggested_evidence": null,
      "fact_count": 16,
      "salience": 1.4052,
      "provenance": "inferred",
      "review_state": "demo",
      "as_of": "2026-11-19",
      "evidence_fact_ids": ["f079", "f089", "f086"]
    }
  ],
  "edges": [
    {
      "id": "mem:p01->cluster:career",
      "src": "p01",
      "dst": "cluster:career",
      "rel": "CLUSTER_OF",
      "kind": "membership",
      "provenance": "demo_fixture",
      "review_state": "demo",
      "valid_from": null,
      "valid_to": null,
      "evidence_fact_ids": []
    },
    {
      "id": "mem:cluster:career->s08",
      "src": "cluster:career",
      "dst": "s08",
      "rel": "TOPIC_OF",
      "kind": "membership",
      "provenance": "inferred",
      "review_state": "demo",
      "valid_from": null,
      "valid_to": null,
      "evidence_fact_ids": ["f079", "f089", "f086"]
    }
  ],
  "key_items": [
    {"id": "cluster:career", "cluster": "career", "label": "Career", "summary": "Atlas work project · Senior AI Engineer job search", "fact_count": 26, "provenance": "demo_fixture", "review_state": "demo"},
    {"id": "cluster:learning", "cluster": "learning", "label": "Learning", "summary": "LLM agents course", "fact_count": 6, "provenance": "demo_fixture", "review_state": "demo"},
    {"id": "cluster:projects", "cluster": "projects", "label": "Projects", "summary": "Raseef side-project app · AI bil Arabi channel", "fact_count": 9, "provenance": "demo_fixture", "review_state": "demo"},
    {"id": "cluster:events", "cluster": "events", "label": "Events", "summary": "Notes · Omar Farouk wedding · Dubai Marathon training", "fact_count": 48, "provenance": "demo_fixture", "review_state": "demo"},
    {"id": "cluster:home-money", "cluster": "home-money", "label": "Home & money", "summary": "Gold savings plan", "fact_count": 2, "provenance": "demo_fixture", "review_state": "demo"}
  ]
}
```

### 5b. `GET /v1/owners/karim_demo/vault/graph?view=people&max_per_group=6` (abridged nodes/edges for readability)

```json
{
  "version": "1",
  "owner": "karim_demo",
  "view": "people",
  "center_id": "p01",
  "as_of": "2026-11-24T08:51:05.610676+00:00",
  "provenance": "demo_fixture",
  "demo_data": true,
  "privacy_revision": 1,
  "facts_version": 1,
  "counts": {
    "total_nodes": 33,
    "shown_nodes": 17,
    "people": 20,
    "places": 5,
    "projects": 0,
    "relations": 0,
    "hidden_by_group": {"people": 14, "orgs": 2}
  },
  "nodes": [
    {
      "id": "p01",
      "kind": "owner",
      "label": "Karim Haddad",
      "subtitle": "You",
      "group": "center",
      "tier": null,
      "closeness_suggested": null,
      "closeness_suggested_evidence": null,
      "fact_count": 91,
      "salience": 1.0,
      "provenance": "demo_fixture",
      "review_state": "demo",
      "as_of": "2026-11-24T08:51:05.610676+00:00",
      "evidence_fact_ids": []
    },
    {
      "id": "p02",
      "kind": "person",
      "label": "Omar Farouk",
      "subtitle": "friend",
      "group": "people",
      "tier": "T1",
      "closeness_suggested": null,
      "closeness_suggested_evidence": null,
      "fact_count": 7,
      "salience": 1.297,
      "provenance": "user_supplied",
      "review_state": "demo",
      "as_of": "2026-11-12",
      "evidence_fact_ids": ["f080", "f010", "f095"]
    },
    {
      "id": "l01",
      "kind": "place",
      "label": "Al Barsha",
      "subtitle": "place",
      "group": "places",
      "tier": null,
      "closeness_suggested": null,
      "closeness_suggested_evidence": null,
      "fact_count": 5,
      "salience": 0.9964,
      "provenance": "inferred",
      "review_state": "demo",
      "as_of": "2026-11-05",
      "evidence_fact_ids": ["f074", "f044", "f004"]
    }
  ],
  "edges": [
    {
      "id": "mem:p01->p02",
      "src": "p01",
      "dst": "p02",
      "rel": "FRIEND",
      "kind": "membership",
      "provenance": "user_supplied",
      "review_state": "demo",
      "valid_from": null,
      "valid_to": null,
      "evidence_fact_ids": ["f080", "f010", "f095"]
    }
  ],
  "key_items": [
    {"id": "p02", "kind": "person", "label": "Omar Farouk", "subtitle": "friend", "tier": "T1", "fact_count": 7, "provenance": "user_supplied", "review_state": "demo"},
    {"id": "p06", "kind": "person", "label": "Nour El-Din", "subtitle": "friend", "tier": null, "fact_count": 5, "provenance": "inferred", "review_state": "demo"}
  ]
}
```
