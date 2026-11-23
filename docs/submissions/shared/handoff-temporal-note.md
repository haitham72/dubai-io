# Handoff to `temporal_note` Team (`apps/memory/`, package `temporal_memory`)

**From:** `contest-shared` (`apps/api/app/identity/`, `apps/api/app/memory_bridge/`)
**To:** PC2 `memory` / `main` team (`apps/memory/`, package `temporal_memory`)
**Baseline inspected:** `origin/memory` @ `fc2e24a` (latest `apps/memory` commit `602c8c3`)
**Date:** 2026-11-23 (Founder decision **D10**)

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
      "subject_id": "projects/dubai-io",
      "valid_from": "2026-11-23T14:00:00+04:00",
      "evidence": ["mgmsg:m-101"],
      "provenance": "user_supplied"
    }
  }
  ```
  `enqueue` is `"extract.live" | "extract.day" | "none"` (default `"extract.live"`). `direct_fact` is optional; when present, `evidence` MUST be non-empty and reference records in the batch or DB, must pass `privacy/sensitive.py` + `forget_rules` (reject credentials fail-closed), and writes via the same validator/applier invariants as `PostgresGraphStore`.
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
