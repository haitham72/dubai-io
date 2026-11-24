# B-M — Cursor: Implement `handoff-temporal-note.md` (`CR-TM-1` … `CR-TM-4` + 2 Fixes) on `memory`

Paste below the line into **Cursor** to satisfy the founder's `docs/submissions/shared/handoff-temporal-note.md` requirement (`CR-TM-1` … `CR-TM-4` + 2 upstream fixes for the shared memory bridge across Quest, Community, and Messenger).

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and run `git -C G:\Haitham\VsCode\contest-memory show contest-shared:docs/submissions/shared/handoff-temporal-note.md` first. **Sub-agents: Composer 2 Fast only.**

Create or switch to worktree `G:\Haitham\VsCode\contest-mem-wpM` on branch `mem-wpM` branched from `memory` (`03e8fa3`):

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpM -b mem-wpM memory
cd G:\Haitham\VsCode\contest-mem-wpM
```

### Owned Files (Strict Ownership inside `apps/memory/`)
- `apps/memory/src/temporal_memory/api/vault.py` (or a new router module `apps/memory/src/temporal_memory/api/bridge.py` included in `api/app.py` + `vault.py`)
- `apps/memory/src/temporal_memory/api/app.py`
- `apps/memory/src/temporal_memory/store/postgres.py` (if helper methods are needed)
- `apps/memory/src/temporal_memory/privacy/forget.py`
- `apps/memory/tests/fixtures/fake_store.py`
- `apps/memory/tests/test_crtm_handoff.py`

### Deliverables (Exact Spec from `handoff-temporal-note.md`)
1. **Upstream Fix 1 — Block `worker` tokens on Vault & CR-TM routes (`api/vault.py:55-58`):**
   - In `require_owner_access`, allow ONLY `auth.role == "admin"` OR `(auth.role == "owner-device" and auth.owner == owner)`. Return `HTTP 403` for `worker` and any other role. Apply the exact same guard to `CR-TM-1..4`.
2. **Upstream Fix 2 — Include `extract.live` in Forget job requeue (`privacy/forget.py:147`):**
   - Change the job requeue filter from `AND kind = 'extract.day'` to `AND kind IN ('extract.day', 'extract.live')` (and mirror in `FakeGraphStore.forget_source` if applicable).
3. **`CR-TM-1` — Upsert Records & Direct Confirmed Facts (`POST /v1/owners/{owner}/records`):**
   - Request JSON:
     ```json
     {
       "records": [{"id": "mgmsg:m-101", "source": "messenger:conv-42", "at": "2026-11-23T14:00:00+04:00", "author": "<user_id>", "text": "..."}],
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
   - `enqueue` is `"extract.live" | "extract.day" | "none"` (default `"extract.live"`).
   - Reject any record whose `id` or `content_hash` matches `forget_rules` for `owner`.
   - `direct_fact` is optional; when present:
     - `evidence` MUST be non-empty (`422` if empty) and reference records in the batch or store (`422` if unknown);
     - Must pass `privacy/sensitive.py` (`classify_sensitive` / `contains_credential` — reject credentials fail-closed with `400` or quarantine and increment `quarantined` without storing raw sensitive text);
     - Writes the confirmed `Fact(status="active", provenance=direct_fact.provenance or "user_supplied", ...)` and bumps `owners.facts_version`.
   - Response JSON: `{"ok": true, "record_ids": [...], "job_id": "..." | null, "fact_ids": [...], "quarantined": 0}`.
4. **`CR-TM-2` — HTTP Forget Endpoint (`POST /v1/owners/{owner}/forget`):**
   - Request JSON: `{"record_ids": ["..."], "fact_id": "..." | null, "idempotency_key": "..."}`
   - Calls `forget_source(owner, record_ids)` and/or `forget_fact(owner, fact_id)` on the store/DB, invalidates `live/context.py` L1 cache for `owner`, and populates `forget_rules` so re-importing forgotten `record_ids` is blocked.
   - Response JSON: `{"ok": true, "generation": 2, "records": 1, "facts_erased": 1, "facts_trimmed": 0, "entity_subjects_recomputed": 1, "jobs_requeued": 0, "jobs_enqueued": 0}`.
5. **`CR-TM-3` — Fact & Hypothesis Resolution (`POST /v1/owners/{owner}/facts/{fact_id}/resolve`):**
   - Request JSON: `{"action": "confirm" | "edit" | "reject" | "supersede", "new_text": "..." | null, "valid_from": "..." | null, "evidence_record_id": "..." | null}`
   - `confirm`: promotes `status="hypothesis"` → `"active"`, `provenance="user_supplied"`, bumps `facts_version`.
   - `edit` / `supersede`: requires non-empty `new_text` (and passes sensitive check); sets old fact `valid_to=valid_from or now`, `status="superseded"`, `superseded_by=new_fact_id`, inserts new evidence-linked active fact (inheriting old fact's evidence + optional `evidence_record_id`), bumps `facts_version`.
   - `reject`: erases/hides fact immediately, unlinks evidence, bumps `facts_version`.
   - Response JSON: `{"ok": true, "fact_id": "...", "new_fact_id": "..." | null, "status": "...", "facts_version": 42}`.
6. **`CR-TM-4` — HTTP L1 Context & Source-Scoped Search:**
   - `POST /v1/owners/{owner}/context` — body `{"text": "...", "max_tokens": 1500}` → returns the L1 context pack (`live/context.py:context_pack` or store-backed context pack matching MCP `memory_context`).
   - `GET /v1/owners/{owner}/search?q=...&limit=20&source_prefix=...` — searches visible facts for `owner` matching `q`; when `source_prefix` is supplied, returns **only** facts whose evidence records have `record.source.startswith(source_prefix)` (so `messenger:c1` never leaks `messenger:c2` or `quest:` facts).
7. **Acceptance Tests (`apps/memory/tests/test_crtm_handoff.py`):**
   - Implement all 6 acceptance tests from §4 of `handoff-temporal-note.md`:
     1. `test_vault_and_crtm_reject_worker_and_cross_owner`
     2. `test_crtm1_records_upsert_and_direct_fact`
     3. `test_crtm2_forget_erases_trims_and_requeues_live_jobs`
     4. `test_crtm3_resolve_confirm_edit_reject`
     5. `test_crtm4_http_context_and_source_prefix_search`
     6. `test_crtm2_forget_blocks_reimport`

**Done when** `pytest -q` in `apps/memory` passes all existing + new tests and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes. Commit on `mem-wpM` with a clear commit message and report branch + SHA + test counts.
