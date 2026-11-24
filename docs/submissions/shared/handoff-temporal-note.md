# Handoff to `temporal_note` Team (`apps/memory/`, package `temporal_memory`)

**From:** `contest-shared` (`apps/api/app/identity/`, `apps/api/app/memory_bridge/`)
**To:** PC2 `memory` / `main` team (`apps/memory/`, package `temporal_memory`)
**Baseline inspected:** `origin/memory` @ `fc2e24a` (latest `apps/memory` commit `602c8c3`)
**Date:** 2026-11-23 (Founder decision **D10**)

---

## 0. Expectation (founder, 24 Nov 2026)

The rebuilt **temporal_note** is the Dubai-io companion's new memory, replacing Hindsight, Honcho, mem0 and GraphRAG. It **is expected to implement this hand-off**: `CR-TM-1` … `CR-TM-4` and the two fixes below, or an equivalent that the bridge can map one to one.

- It is the **single memory service for all three entries**: Quest (the companion) uses it as its memory, and Community and the Messenger reach it only through `apps/api/app/memory_bridge/`. Nothing builds a second engine.
- **Acceptance:** the bridge's contract suite (`apps/api/tests/test_memory_bridge_*.py` on `contest-shared`) passes with `HttpTemporalMemoryClient` against the rebuilt service. It is the same suite that passes today against `FakeTemporalMemoryClient`.
- **If the rebuild's interface differs, the memory team replies with it.** The bridge adapts to the engine, not the other way round. Until the routes land on `main`, the entries keep running on the fake.

---

## 1. Purpose & Auth Model

All three Dubai Chambers entries (Quest, Community, Messenger) call `temporal_memory` strictly through `apps/api/app/memory_bridge/` using HTTP REST as primary transport.

- Every user-scoped call carries **`Authorization: Bearer <owner-device-token>`**, where `temporal_memory.owners.id == cs_users.user_id` (1:1 immutable owner mapping).
- `TM_ADMIN_TOKEN` stays server-side for `POST /v1/owners` and `POST /v1/tokens` / `DELETE /v1/tokens/{id}` provisioning only.
- Until the 4 HTTP endpoints and 2 fixes below land on `main` alongside `apps/memory/`, our B0/entry builds run against a clearly named `FakeTemporalMemoryClient` implementing the exact same protocol.

---

## 2. Change Requests (`CR-TM-1` … `CR-TM-4`)

### `CR-TM-1` — Upsert Records & Direct Confirmed Facts
- **Route:** `POST /v1/owners/{owner}/records`
- **Auth:** `admin` OR `owner-device` where `auth.owner == owner` (`403` otherwise)
- **Request JSON:**
  ```json
  {
    "records": [
      {
        "id": "mgmsg:m-101",
        "source": "messenger:conv-42",
        "at": "2026-11-23T14:00:00+04:00",
        "author": "<user_id>",
        "text": "..."
      }
    ],
    "enqueue": "extract.live",
    "direct_fact": {
      "text": "...",
      "subject_path": "projects/dubai-io",
      "valid_from": "2026-11-23T14:00:00+04:00",
      "evidence": ["mgmsg:m-101"],
      "provenance": "user_supplied"
    }
  }
  ```
  `enqueue` is `"extract.live" | "extract.day" | "none"` (default `"extract.live"`). `direct_fact` is optional (`"subject_id"` is also accepted as an alias for `"subject_path"`); when present, `evidence` MUST be non-empty and reference records in the batch or DB, must pass `privacy/sensitive.py` + `forget_rules` (reject credentials fail-closed), and writes via the same validator/applier invariants as `PostgresGraphStore`.
- **Response JSON:** `{"ok": true, "record_ids": [...], "job_id": "..." | null, "fact_ids": [...], "quarantined": 0}`

### `CR-TM-2` — HTTP Forget Endpoint
- **Route:** `POST /v1/owners/{owner}/forget`
- **Auth:** `admin` OR `owner-device` where `auth.owner == owner` (`403` otherwise)
- **Behavior:** Wraps `privacy/forget.py:forget_source(owner, record_ids)` and/or `forget_fact(owner, fact_id)` (bumping `records.generation`, erasing only-evidence facts, trimming `fact_evidence` on multi-source facts, recomputing `entity_subjects`, writing `forget_rules`, requeuing survivor jobs, and invalidating `live/context.py` caches).
- **Request JSON:** `{"record_ids": ["..."], "fact_id": "..." | null, "idempotency_key": "..."}`
- **Response JSON:**
  `{"ok": true, "generation": 2, "records": 1, "facts_erased": 1, "facts_trimmed": 0, "entity_subjects_recomputed": 1, "jobs_requeued": 0, "jobs_enqueued": 0}`

### `CR-TM-3` — Fact & Hypothesis Resolution / Correction
- **Route:** `POST /v1/owners/{owner}/facts/{fact_id}/resolve`
- **Auth:** `admin` OR `owner-device` where `auth.owner == owner` (`403` otherwise)
- **Behavior:** Wires the `["Confirm", "Edit", "Not true", "Forget"]` actions already returned by `api/vault.py:273`.
- **Request JSON:**
  `{"action": "confirm" | "edit" | "reject" | "supersede", "new_text": "..." | null, "valid_from": "..." | null, "evidence_record_id": "..." | null}`
  - `confirm`: promotes `status="hypothesis"` → `"active"`, `provenance="user_supplied"`.
  - `edit` / `supersede`: sets old fact `valid_to=now`, `status="superseded"`, `superseded_by=new_fact_id`, inserts new evidence-linked fact.
  - `reject`: erases/hides fact immediately (same effect as `"Not true"`), unlinks evidence, bumps `owners.facts_version`.
- **Response JSON:** `{"ok": true, "fact_id": "...", "new_fact_id": "..." | null, "status": "...", "facts_version": 42}`

### `CR-TM-4` — HTTP L1 Context & Source-Scoped Search
- **Routes:**
  1. `POST /v1/owners/{owner}/context` — body `{"text": "...", "max_tokens": 1500}` → wraps `live/context.py:context_pack` (same payload as MCP `memory_context`).
  2. `GET /v1/owners/{owner}/search?q=...&limit=20&source_prefix=...` — wraps `visible_facts` FTS (`mcp/server.py:449-503`). When `source_prefix` is supplied, joins `fact_evidence` → `records` and returns **only** facts where **all** (or strictly matching) evidence records have `records.source LIKE '<source_prefix>%'` (so Messenger `messenger:<conversation_id>` and Community `community:` reads never leak across sources).
- **Auth:** `admin` OR `owner-device` where `auth.owner == owner` (`403` otherwise)

---

## 3. Two Upstream Fixes Required

1. **Block `worker` tokens on Vault routes (`apps/memory/src/temporal_memory/api/vault.py:55-58`):**
   - Current code:
     ```python
     if auth.role == "owner-device" and auth.owner != owner:
         raise HTTPException(status_code=403, ...)
     return auth
     ```
     This allows a `worker` token (where `auth.owner` is `None` or unrelated) to read `/v1/owners/{owner}/vault/*`.
   - **Fix:** Allow ONLY `auth.role == "admin"` OR `(auth.role == "owner-device" and auth.owner == owner)`. Return `HTTP 403` for `worker` and any other role. Apply the exact same guard to `CR-TM-1..4`.
2. **Include `extract.live` in Forget job requeue (`apps/memory/src/temporal_memory/privacy/forget.py:147`):**
   - Current query filters `WHERE owner = %(owner)s AND kind = 'extract.day' AND input_ref && %(rids)s`, omitting requeueable `extract.live` jobs referencing forgotten records.
   - **Fix:** Change filter to `AND kind IN ('extract.day', 'extract.live')`.

---

## 4. Acceptance Pytest Checklist (for `apps/memory/tests/`)

1. `test_vault_and_crtm_reject_worker_and_cross_owner`: `worker` token → `403` on `/vault/*` & `CR-TM-1..4`; User A `owner-device` → `403` on User B `{owner}`.
2. `test_crtm1_records_upsert_and_direct_fact`: upserts record + creates `user_supplied` fact with evidence; rejects missing evidence (`422`) and credential text (`400`/quarantined).
3. `test_crtm2_forget_erases_trims_and_requeues_live_jobs`: only-evidence fact erased; multi-source fact trimmed and still visible; `extract.live` job requeued or marked `dead`; stale-generation worker submit rejected (`fence_stale`).
4. `test_crtm3_resolve_confirm_edit_reject`: `confirm` promotes hypothesis; `edit`/`supersede` links `superseded_by` + sets `valid_to`; `reject` hides immediately; `facts_version` increments on each.
5. `test_crtm4_http_context_and_source_prefix_search`: `POST /context` matches MCP `memory_context`; `GET /search?source_prefix=messenger:c1` never returns `messenger:c2` or `quest:` facts.
6. `test_crtm2_forget_blocks_reimport`: `forget_rules` populated so re-upserting a forgotten `record_id` is blocked.

---

## 5. How to run live mode

To run the bridge contract suite (`apps/api/tests/test_memory_bridge_*.py`) against a live `temporal_memory` HTTP server (`origin/memory` on port `8040`):

1. Create a worktree for `origin/memory` and configure `.env` with `TM_ADMIN_TOKEN`:
   ```bat
   git worktree add ..\tm-live origin/memory
   cd ..\tm-live\apps\memory
   copy .env.example .env
   rem Set TM_ADMIN_TOKEN=<your-admin-token> in .env
   docker compose up -d postgres rabbitmq redis api
   ```
2. Provision an owner (`POST /v1/owners`) and an `owner-device` token (`POST /v1/tokens`) using `TM_ADMIN_TOKEN`:
   ```sh
   curl -X POST http://localhost:8040/v1/owners \
     -H "Authorization: Bearer $TM_ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"id":"cs_live_default","label":"cs_live_default","kind":"demo"}'

   curl -X POST http://localhost:8040/v1/tokens \
     -H "Authorization: Bearer $TM_ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"role":"owner-device","owner":"cs_live_default","label":"cs-live"}'
   ```
3. Export the live bridge environment variables and run `pytest` with `MEMORY_BRIDGE_LIVE=1`:
   ```sh
   export TM_BASE_URL=http://localhost:8040
   export TM_SERVICE_TOKEN=<owner-device-or-service-token>
   export TM_ADMIN_TOKEN=<your-admin-token>
   MEMORY_BRIDGE_LIVE=1 pytest -q apps/api/tests/test_memory_bridge_*.py
   ```
