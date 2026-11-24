# CS-1 Report — Live `memory-bridge` Contract Suite Verification

- **Worktree:** `G:\Haitham\VsCode\contest-cs-live-bridge`
- **Branch:** `cs/live-bridge-tests` (base: `contest-shared @ fbcdf97`)
- **Commit:** `f4922b9` (*"CS-1: live MEMORY_BRIDGE_LIVE=1 fixture, contract test wiring, and handoff alignment"*)
- **Merge state:** **Not merged** into `contest-shared`, `societal`, or `business`, and not pushed (per user instruction).

## 1. Owned Files Changed

- New [memory_bridge_fixtures.py](file:///G:/Haitham/VsCode/contest-cs-live-bridge/apps/api/tests/fixtures/contest_shared/memory_bridge_fixtures.py) (shared fake/live `memory_bridge_env` + `tm_client` fixture and `@fake_only` marker; kept out of `apps/api/tests/conftest.py` to satisfy Gate 3)
- [test_memory_bridge_client.py](file:///G:/Haitham/VsCode/contest-cs-live-bridge/apps/api/tests/test_memory_bridge_client.py)
- [test_memory_bridge_consent.py](file:///G:/Haitham/VsCode/contest-cs-live-bridge/apps/api/tests/test_memory_bridge_consent.py)
- [test_memory_bridge_e2e.py](file:///G:/Haitham/VsCode/contest-cs-live-bridge/apps/api/tests/test_memory_bridge_e2e.py)
- [test_memory_bridge_forget.py](file:///G:/Haitham/VsCode/contest-cs-live-bridge/apps/api/tests/test_memory_bridge_forget.py)
- [test_memory_bridge_reads.py](file:///G:/Haitham/VsCode/contest-cs-live-bridge/apps/api/tests/test_memory_bridge_reads.py)
- [test_memory_bridge_writes.py](file:///G:/Haitham/VsCode/contest-cs-live-bridge/apps/api/tests/test_memory_bridge_writes.py)
- [handoff-temporal-note.md](file:///G:/Haitham/VsCode/contest-cs-live-bridge/docs/submissions/shared/handoff-temporal-note.md) (`subject_path` canonical field with `subject_id` alias note, plus `§5. How to run live mode`)
- [log.md](file:///G:/Haitham/VsCode/contest-cs-live-bridge/docs/submissions/shared/log.md)

## 2. Verification Results (Fake vs Live)

| Run mode | Target server | Passed | Failed | Skipped | Notes |
|---|---|---:|---:|---:|---|
| **Fake (bridge suite)** | `FakeTemporalMemoryClient` | **92** | 0 | 0 | `test_memory_bridge_*.py` (`2.85s`) |
| **Fake (Gate 1 full API)** | `FakeTemporalMemoryClient` | **520** | 1 | 14 | Only failure is pre-existing missing `redis` module in `tests/test_ops.py:130` (matches `contest-shared` log baseline) |
| **Live (baseline `memory`)** | `origin/memory @ 267b0cf` (Postgres 17 `:5442`, temp schema dropped) | **78** | 8 | 6 | 6 skipped (`@fake_only`); all 8 failed on `GET /v1/owners/{owner}/search?q=&limit=500` → `422` (`le=100`) |
| **Live (after U1c `le=500`)** | `mem-wpU1c @ 30929bb` (merged w/ `573ff79`, Postgres 17 `:5442`, temp schema dropped) | **81** | **5** | **6** | 6 skipped (`@fake_only`); all 8 prior `422` errors fixed, surfacing 5 remaining contract mismatches below |

## 3. §4 Gates on `cs/live-bridge-tests` (`f4922b9`)

- **Gate 1 (bridge contract suite):** `92 passed in 2.85s`; full API suite: `520 passed, 14 skipped, 1 failed` (`test_ops.py` missing `redis`, pre-existing).
- **Gate 2 (`apps/web` untouched):** `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` → exit `0`.
- **Gate 3 (owned paths only):** `git diff --name-only $(git merge-base HEAD origin/main) HEAD` → strictly `CLAUDE.md` Contest submissions + `apps/api/app/{identity,memory_bridge}/` + `apps/api/tests/test_{identity,memory_bridge}_*.py` + `apps/api/tests/fixtures/contest_shared/` + `docs/submissions/{CLAUDE.md,shared/**}`.
- **Gate 5 (`merge-tree` vs PC2 branches):**
  - vs `origin/memory`: exit `0`
  - vs `origin/ios`: exit `0`
  - vs `origin/desktop`: exit `0`

## 4. Remaining Live Mode Mismatches (vs `mem-wpU1c @ 30929bb`)

All 5 failures occurred under `MEMORY_BRIDGE_LIVE=1` in clean isolated Postgres temp schemas (`cs1_live_*`, dropped in `finally`):

1. **`test_mb_default_off_consent`** (`test_memory_bridge_consent.py:120`)
   - **Request:** `POST /v1/owners/{owner}/context` with `{"text": "padel", "max_tokens": 1500}` after `POST /v1/owners` (`kind="demo"`).
   - **Response:** `200 OK` with `facts[0]["display_prefix"] = "Demo data"`.
   - **Expected / Faulty side:** Test asserts `"You told me"`. **Fixture issue (`contest-shared` test fixture):** `memory_bridge_fixtures.py:105,123` provisions live owners with `kind="demo"`, causing `temporal_memory/live/context.py` to tag every fact `"Demo data"` (`kind="real"` should be used unless testing demo mode).

2. **`test_gate_s_full_cross_app_e2e`** (`test_memory_bridge_e2e.py:274`)
   - **Request:** `POST /v1/owners/{owner}/records` with `direct_fact.subject_path = "hobbies/specialty-coffee"`, followed by `GET /v1/owners/{owner}/search?q=&limit=500`.
   - **Response:** `GET /search` returns `subject_id: "subj_..."` (internal UUID/ID) without `subject_path`; `bridge.py` falls back to `topic_slug = "general"`.
   - **Expected / Faulty side:** Test asserts `features[0]["topic_slug"] == "specialty-coffee"`. **`temporal_memory` server contract gap (or bridge mapping):** `CR-TM-4` `GET /search` (in `core/bridge_store.py`) does not return `subject_path` alongside `subject_id` (unlike `FakeTemporalMemoryClient`, where `subject_id` stored `"hobbies/specialty-coffee"`).

3. **`test_mb_community_strict_allowlist_and_d11_minor_gate`** (`test_memory_bridge_reads.py:279`)
   - **Request:** Two confirmed facts written (`"hobbies/padel"`, `"travel/salalah"`), then `GET /v1/owners/{owner}/search?q=&limit=500`.
   - **Response:** Both facts return internal `subject_id` without `subject_path`, colliding into one `"general"` `InterestFeature`.
   - **Expected / Faulty side:** Test asserts `len(features) == 2` (`"padel"` and `"salalah"`). **Same root cause as #2** (`subject_id` vs `subject_path` in `/search` response).

4. **`test_mb_two_visit_qualification`** (`test_memory_bridge_writes.py:445`)
   - **Request:** 3 behavioral signals for `topic_slug="desert-cycling"` promote via `direct_fact.subject_path="interests/desert-cycling"`, then Community reads `GET /search?q=&limit=500`.
   - **Response:** Returned `topic_slug = "general"`.
   - **Expected / Faulty side:** Test asserts `topic_slug == "desert-cycling"`. **Same root cause as #2.**

5. **`test_mb_supersession_and_correction`** (`test_memory_bridge_writes.py:508`)
   - **Request:** `POST /v1/owners/{owner}/facts/{fid}/resolve` with `{"action": "edit", "new_text": "Plays padel twice a week in Al Quoz", "valid_from": "2026-11-23T12:00:00+00:00"}`.
   - **Response:** `200 OK`, `{"ok": true, "fact_id": fid, "new_fact_id": "rf-...", "status": "active", "facts_version": ...}`.
   - **Expected / Faulty side:** Test asserts `res_edit["status"] == "superseded"`. **Spec vs test mismatch (`contest-shared` side):** `handoff-temporal-note.md:77` shows the response `status` describes the resulting active state (matching `temporal_memory/api/bridge.py:264` setting `status = "active"` for the new replacement fact), whereas the unit test + `FakeTemporalMemoryClient` returned `"superseded"` (the old fact's status).
