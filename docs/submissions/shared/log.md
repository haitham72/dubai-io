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
