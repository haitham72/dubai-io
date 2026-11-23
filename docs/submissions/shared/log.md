# Shared Contract Log (`contest-shared`)

## 2026-11-23 — P2 Part A (Antigravity)

### What was checked
- **Branches & commits audited (read-only):**
  - `contest-shared` (`206b9ff`, forked from `origin/main` `f016856`): `CLAUDE.md`, `PLAN.md`, `ARCHITECTURE.md`, `docs/status.md`, `docs/submissions/CLAUDE.md`, `docs/submissions/shared/founder-decisions.md` (D1–D7), all three `founder-inputs/`, `apps/api/app/auth.py`, `apps/api/app/actions.py`, `apps/api/app/main.py`, `apps/api/app/lab/sensitive.py`, `apps/api/app/memory/` (`mem_*`, confirmed read-only), `supabase/config.toml`, `supabase/migrations/20261021000100_backend.sql`, `apps/api/requirements.txt`.
  - `origin/memory` (`fc2e24a`, newest `apps/memory` commit `602c8c3` on `origin`): `apps/memory/README.md`, `CLAUDE.md`, `models.py`, `db/schema.sql`, `api/app.py`, `api/vault.py`, `api/export_md.py`, `api/ops.py`, `mcp/server.py`, `mcp/tokens.py`, `core/validator.py`, `core/applier.py`, `privacy/forget.py`, `privacy/policy.py`, `privacy/sensitive.py`, `live/context.py`, `tests/fixtures/fake_store.py`.
  - `origin/desktop` (`d07ee53`) & `origin/ios` (`3b12997`): verified auth state (`electron/main/ownerHook.ts`, `index.ts`, `localReader.ts`; `apps/mobile/src/features/{connect,vault,quests}/*`) and canon diffs vs `origin/main`.
  - `business` (`fc18129`): all 9 docs under `docs/submissions/messenger/` plus `briefs/1b-revise.md`.
  - `societal` (`cccf09f`): confirmed only `briefs/1-plan.md` and `2-build.md` exist today (`DELIVERY_ROADMAP.md` not yet landed; Part B runs later).
- **Four read-only subagent lanes executed:** Lane A (Identity), Lane B (Memory & Consent against `temporal_note`), Lane C (Cross-check), Lane D (Canon patch proposals).
- **Gates verified:** frozen `apps/web` (`mobile-pwa-baseline-2026-10-23`) clean; `contest-shared` owned-paths only; zero `HANDOFF.md`.

### What changed (all under `docs/submissions/shared/`)
- Added `THREE_ENTRIES_OVERVIEW.md` (`draft — awaiting Community needs (P2 Part B)`)
- Added `SHARED_MEMORY_CROSS_APP_CONTRACT.md` (`draft — awaiting Community needs (P2 Part B)`)
- Added `shared-slices.md` (`draft — awaiting Community needs (P2 Part B)`, slices `CS-B1`..`CS-B5`)
- Added `cross-check.md` (Messenger P1 plan + Community founder spec cross-check, transport decision, open-questions triage)
- Added `canon-patches/PLAN.patch.md`, `ARCHITECTURE.patch.md`, `docs-status.patch.md`, `CLAUDE.patch.md` (proposals only; never applied)
- Created `log.md` (this file)

### Top risks & open blockers
1. **Messenger P1b not yet applied on `business`:** `business:docs/submissions/messenger/` (`fc18129`) still carries the retired product name, clean-room M0 recommendation, outdated Updates tray, Builder MCP / Higgsfield AI sticker generation, and Hindsight `AC-1` gate references (`XC-M01`..`XC-M11`). Cursor must run `briefs/1b-revise.md` before M0 / `B`.
2. **`temporal_memory` HTTP contract gaps (`origin/memory` @ `fc2e24a`):** `CR-TM-1..4` (`/records`, `/forget`, `/facts/{id}/resolve`, HTTP `/context` + `/search?source_prefix=`) exist in Python modules only and are not yet HTTP endpoints; `api/vault.py:55-58` does not block `worker` tokens on vault routes; `privacy/forget.py:147` filters job requeues on `extract.day` only (not `extract.live`). B0 uses clearly named `FakeTemporalMemoryClient` until `memory` + `CR-TM-1..4` land.
3. **Desktop & iOS have no JWT auth:** Both `origin/desktop` (`d07ee53`) and `origin/ios` (`3b12997`) hardcode/default owner `"karim"` without `Authorization` headers; unpushed PC2 `main` may add further drift when reconciled.
4. **Live Postgres / Supabase Auth readiness:** `supabase/config.toml:42` sets `enable_signup = false`, `dubaiio` schema is backend-only (`supabase/migrations/` frozen), and staging RLS SQL apply for `apps/messenger/supabase/` and `apps/community/supabase/` needs an explicit founder ops step before live pilot traffic.
5. **Founder gate items pending:** O2 (Messenger new product name), M0 keep/exclude/rebuild file list confirmation + organizer prototype-reuse check (`PLAN.md:174`), and Community P1 plan (`societal`) before P2 Part B + B0.

## 2026-11-23 — P2 Part B (Antigravity)

### What was checked
- **Branches & commits audited:**
  - `contest-shared` (`f03d15f`): read new Founder Decisions **D8** (Messenger M0 confirmed + U²-Net any-subject cut-out stickers + drop Diwan/Nadi/watermark-cleaner/Higgsfield + `MG-B1`/`MG-B2` approved), **D9** (Community `v3-higgsfield` layout + `design/20-11-2026/` style, all-ages self-declared age gate with under-18 protections + pre-`CM-B3` UAE child-safety check, invisible private groups, Scene C allowlisted public-info + non-civic fallback), and **D10** (18 Dec secure tunnel + `>= 5` adult testers, separate staging Supabase project with entry-folder RLS scripts, `handoff-temporal-note.md`, founder prototype-reuse inquiry).
  - `business` (`4f7c675`, including P1b `2523d3d`, `faeaff7`, `e7638e4`): re-checked all 11 Part A `XC-M` findings — 9 resolved (including `XC-M01`..`M07`, `M10`, `M11`), 2 still open for build slices (`XC-M08` WS auth waiting on Gate S; `XC-M09` `demo-script.md` list/provenance payload shape for `MG-B6`), plus minor doc sync `XC-M12` (`DELIVERY_ROADMAP.md:117` Diwan basename note). Noted active `MG-B2` worktree edits in `D:\Vscode\dubai-io-business`.
  - `societal` (`317de4d`): audited full Community P1 pack (`identity-memory-needs.md`, `open-questions.md`, `DELIVERY_ROADMAP.md`, `audit.md`, `IMPLEMENTATION_GAP_MATRIX.md`, `demo-script.md`, `sources.md`, `log.md`, and `28 passed in 11.17s` parked baseline).
  - `origin/memory` (`fc2e24a`): verified exact `api/vault.py:55-58` and `privacy/forget.py:147` lines for the D10 hand-off doc.

### What changed (under `docs/submissions/shared/`)
- Created `handoff-temporal-note.md` (`CR-TM-1..4` + 2 upstream fixes for PC2 `temporal_memory` team, D10).
- Updated `SHARED_MEMORY_CROSS_APP_CONTRACT.md`: set status to `ready for founder approval`; folded Community `identity-memory-needs.md` (canonical `community:post:*`/`group:*` writes, `read_community_own_activity`, separate Forget-memory vs Delete-post controls, `adopt_session_owner`) + D9 self-declared `age_band` (`cs_users.age_band`, `is_minor_protected`, `MinorProtectionError` blocking writes & cross-app personalisation) + tests `ID-10`, `ID-11`, `MB-11`, `MB-12`.
- Updated `shared-slices.md`: set status to `ready for founder approval`; added D9 age gate, `adopt_session_owner`, and Community needs across `CS-B1`, `CS-B3`, `CS-B4`, `CS-B5`.
- Updated `cross-check.md`: marked Part B status on `XC-M01`..`XC-M12` and added Community P1 rows `XC-CP01`..`XC-CP07`.
- Updated `THREE_ENTRIES_OVERVIEW.md`, `canon-patches/{PLAN,ARCHITECTURE,docs-status}.patch.md` for D8–D10.

### Remaining risks & founder gate items
- **D9 UAE child-safety / under-13 policy:** Community must source official UAE child digital-safety & child-data rules before `CM-B3` (stop and ask founder if unmet by 18 Dec).
- **O2 & prototype-reuse inquiry:** Founder still to pick Messenger's final name/mark (**O2**) before `MG-B8` and email `createaiagents@dubaichamber.com` on prototype reuse (D10).
- **Upstream `temporal_memory` handoff:** `CR-TM-1..4` + 2 fixes await PC2 memory team delivery (`FakeTemporalMemoryClient` covers B0 until landed).
- **Cursor `MG-B2` active in `D:\Vscode\dubai-io-business`:** Dirty worktree cannot be merged into automatically in Part B; Messenger lead merges `contest-shared` after `MG-B2` commits/cleanliness.

## 2026-11-23 — B0 Shared Build / Gate S (Antigravity)

### Baseline (at `f19db5c`, before B0 changes)
- Command (`D:\Vscode\dubai-io-shared\apps\api`, `$env:DATABASE_URL=' '`):
  `D:\Vscode\dubai-io\apps\api\.venv\Scripts\python.exe -m pytest -q tests`
- Result: **`409 passed, 3 failed, 12 skipped`** (the 3 failures are pre-existing Windows `.venv` env issues: `test_connectors.py::test_filesystem_is_scoped` [WinError 1314 symlink privilege] and `test_tryon.py::{test_tryon_requires_adult_confirm,test_tryon_fixture_preview}` [`python-multipart` absent]).

### Slices merged into `contest-shared`
- **`CS-B1`** (`126b8ca` → merge `330c058`): `apps/api/app/identity/{__init__,config,models,jwt,store,service,deps,router}.py`, `tests/fixtures/contest_shared/{__init__,identity_fixtures}.py`, `tests/test_identity_{jwt,sessions,isolation}.py` — canonical `(issuer, subject)` verified `user_id`, RFC 7519 HS256/RS256/ES256/EdDSA verifier, D11 fail-closed `is_minor_protected`, one-time `adopt_session_owner`, per-app sessions + capabilities, single-use `Origin`-bound WS tickets, anti-spoof guards, anonymous cookie boundary (`14 passed`).
- **`CS-B2`** (`8b81e37` → merge `94982b0`): `apps/api/app/memory_bridge/{__init__,config,models,schema,sensitive,client,fake_client}.py`, `tests/fixtures/contest_shared/memory_fixtures.py`, `tests/test_memory_bridge_{client,sensitive}.py` — `TemporalMemoryClient(Protocol)`, `HttpTemporalMemoryClient` (+ `/mcp` fallback), clearly named `FakeTemporalMemoryClient` (generation-fenced Forget, erase-vs-trim, `forget_rules`, `source_prefix`, token guards), `cs_*` schema, Rule 9 fail-closed sensitive filter (`55 passed`).
- **`CS-B3`** (`558b097` → merge `45a760a`): `apps/api/app/memory_bridge/{consent,bridge}.py`, `tests/test_memory_bridge_{consent,writes,reads}.py` — default-off `ConsentStore`, D11 minor fence (`MinorProtectionError`), consented/third-party write paths, two-visit behavioral signal qualification, Quest/Community(`InterestFeature` + `read_community_own_activity`)/Messenger(`read_messenger_chat_scope` + opt-in recall) read projections (`20 passed`).
- **`CS-B4`** (`6efcf4b` → merge `7bbfb24`): `apps/api/app/memory_bridge/{audit,forget}.py`, `tests/test_memory_bridge_{forget,audit}.py` — immutable Rule-9-clean `AuditStore`, synchronous 4-step `ForgetCoordinator` cascade, generation fence, idempotent `ForgetReceipt` + `pending_reconciliation` (`9 passed`).
- **`CS-B5`** (`39e2252` → merge `641fef2`): `apps/api/app/identity/memory_tokens.py`, `apps/api/app/memory_bridge/router.py`, router/bridge wiring, `tests/test_identity_tm_tokens.py`, `tests/test_memory_bridge_e2e.py` — Fernet-encrypted `owner-device` `temporal_memory` token binding/revocation, `/api/v1/memory-bridge/*` FastAPI router, cross-app Gate S E2E (`9 passed`).

### Gate S Verification (lead's own runs at `641fef2`)
- **Contract suite (`test_identity_*.py` + `test_memory_bridge_*.py`):** **`107 passed in 6.36s`** (`0 failed`).
- **Whole API suite (`pytest -q tests`):** **`516 passed, 3 failed, 12 skipped in 191.31s`** (`+107` new passing tests over the `409` baseline; only the exact 3 pre-existing Windows/multipart env failures).
- **Gate 2 (`apps/web`):** `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` → exit `0` (untouched).
- **Gate 3 (owned paths):** `git diff --name-only $(git merge-base HEAD origin/main) HEAD` → `contest-shared` owned paths only.
- **D1 name check:** `git grep -n -i -e "m[i]rsal" -- apps/api/app/identity apps/api/app/memory_bridge` → `0` matches.

### What is real vs faked
- **Real:** JWT HS256/RS256/ES256/EdDSA verification, `(issuer, subject)` user provisioning, D11 `is_minor_protected`, `adopt_session_owner`, per-app sessions/capabilities, `Origin`-bound WS tickets, default-off `ConsentStore`, Rule 9 sensitive filter, two-visit tracker, Community `InterestFeature` projection, Messenger chat-scope + `GroupConsentSnapshot` gate, immutable `AuditStore`, `ForgetCoordinator` local cascade, Fernet `cs_memory_tokens`, FastAPI routers (`/api/identity/*`, `/api/v1/memory-bridge/*`), and `HttpTemporalMemoryClient` (tested over mock HTTP transport).
- **Faked until `temporal_note` rebuild (`CR-TM-1..4`) lands:** `FakeTemporalMemoryClient` in `apps/api/app/memory_bridge/fake_client.py` (selected when `MEMORY_BRIDGE_BACKEND=fake`, default while `TM_BASE_URL` is unset). Tests ran on SQLite (`DATABASE_URL=' '`); Postgres (`TEST_DATABASE_URL`) & live `temporal_memory` integration remain pending.
