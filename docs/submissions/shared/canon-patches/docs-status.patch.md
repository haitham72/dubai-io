# Canon Patch Proposal: `docs/status.md`

- **Target file:** `docs/status.md` (currently 57 lines at `origin/main` `f016856` / `contest-shared` `206b9ff`)
- **Affected line ranges:** lines `1-16`, `35-49`, `55-57`
- **Status:** **PROPOSAL ONLY — DO NOT APPLY ON `contest-shared`.**
- **D16 (24 Nov):** all branches merge into `main` after their gates; describe the paths as `main` folders once merged.
- **When to apply:** Only after the founder reconciles the other PC's unpushed `main` with `origin/main` and approves merging the three-entry portfolio into `main`.
- **Merge-conflict notes:**
  - `origin/memory` (`fc2e24a`), `origin/desktop` (`d07ee53`), and `origin/ios` (`3b12997`) have **zero diffs** against `origin/main` in `docs/status.md`.
  - Check `main` after `memory`, `desktop` and `ios` are merged into it for updated `apps/memory/` test counts and desktop/mobile run commands before applying.

---

## Hunk 1 — Direction & Memory Engine Status (`docs/status.md:1-16`)

**Rationale:** Updates active direction to the three-entry portfolio + `temporal_note` (`apps/memory/`) per D5 while keeping the 18 Nov Hindsight `MEM-01` / `AC-1` record as explicitly superseded history and preserving Entry 1's `154 passed` offline CI record and `AC-2`/`AC-3` items.

```diff
--- a/docs/status.md
+++ b/docs/status.md
@@ -1,17 +1,19 @@
-# Status — 18 Nov 2026
+# Status — <post-merge date>
 
 Single current-state file. Scope: `PLAN.md`. Open requests: [request-backlog.md](request-backlog.md).
 
 ## Direction
 
-UI paused. Active work is closing **AC-1 through AC-3** (`apps/api/tests/test_live_hindsight_llm.py`) before any new feature work, alongside the Know / Notice / Do pipeline (`apps/api/app/lab/CLAUDE.md`) and the memory plan (`docs/plan/Memory/memory.md`; locked rulings still in `PLAN.md` §2).
+Legacy `apps/site` UI remains paused for Entry 1 (desktop/mobile shells live in `apps/desktop/` and `apps/mobile/`). Active portfolio (23 Nov 2026, `docs/submissions/shared/founder-decisions.md` D1–D7) runs sequentially and gated across three entries sharing one verified `user_id` (`apps/api/app/identity/`) and one **`temporal_note`** memory engine (`apps/memory/`, reached via `apps/api/app/memory_bridge/`). Hindsight `AC-1` is **superseded** by D5; Entry 1 `AC-2` and `AC-3` plus shared **Gate S** govern next feature gates.
 
-## MEM-01 & Acceptance Gates Status (18 Nov 2026)
+## Memory Engine (`temporal_note` / Gate S) & Superseded `MEM-01` Status
+
+- **Active memory engine (23 Nov 2026, D5):** Rewritten `temporal_note` (`apps/memory/`, package `temporal_memory`) + shared client `apps/api/app/memory_bridge/` (contract: `docs/submissions/shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md`). Entry 1's `apps/api/app/memory/` (`mem_*`) remains read-only for legacy routes.
+- **MEM-01 status *[Superseded 23 Nov 2026 by D5 (`temporal_note`) — Hindsight `AC-1` is not a gate]*:** **Unproven at the Hindsight LLM-extraction layer** (previously gated on **SRE AC-1** `apps/api/tests/test_live_hindsight_llm.py::test_ac1_live_hindsight_llm_extraction` with `HINDSIGHT_URL` + `HINDSIGHT_LLM_ENABLED=1`).
+- **Entry 1 offline CI baseline (18 Nov 2026, `154 passed`):** `pytest -q tests/test_live_hindsight_llm.py tests/test_lab_*.py tests/test_memory_schema.py tests/test_connectors.py tests/test_connectors_api.py`.
 
-- **MEM-01 status:** **Unproven at the Hindsight LLM-extraction layer** (gated on **SRE AC-1** `apps/api/tests/test_live_hindsight_llm.py::test_ac1_live_hindsight_llm_extraction` with `HINDSIGHT_URL` + `HINDSIGHT_LLM_ENABLED=1`).
   - **Architectural decision (`PLAN.md` §2, AC-5):** Hindsight swappable backend retained; fix Dubai-io rule violations only (`§R-ND` decay-with-floor, Amazon.ae/AED, `"I noticed"` phrasing with two-visit qualification, sensitive-category confirmation gate); full Postgres/markdown-tree re-fit deferred until card contract and AC-1 pass.
   - **Single memory plan (18 Nov):** `docs/plan/Memory/memory.md` (research dumps in `docs/plan/Memory/_archive/` only). FTS-first hybrid; topics = spine + dynamic subtopics + aliases; typed `links` ≠ GraphRAG; Mnemosyne-like live session + Hindsight weekly backfill.
   - **Lab evidence — `mamty-hindsight` prompt-level retain lab run (`G:\Haitham\lab-data\mamty-hindsight\`, AC-L1 / AC-L5):** Offline multi-agent retain (~57 ISO weeks, ~444 facts; playbook in `apps/api/app/lab/CLAUDE.md`). **Not** live `hindsight-api` (no embeddings bank, no `reflect`, no cross-week consolidate). Does not close SRE AC-1 (`MEM-01` remains **unproven**). Blocked from `mem_*` until AC-L3/L4 + confirm. **vs cards UI (`design/17-11-2026/`):** medium fuel for Family/Mom person scope only; **low** as shippable morning-brief feed; Mermaid `graph-from-weeks.md` is diagnostic only (not product). Next useful slice for that design: Gmail + Calendar + one card generator — not more week files.
-  - **Verified offline in CI (`154 passed` across lab/memory/connector/AC-1–5/AC-L1–5 suites):** `pytest -q tests/test_live_hindsight_llm.py tests/test_lab_*.py tests/test_memory_schema.py tests/test_connectors.py tests/test_connectors_api.py`.
```

---

## Hunk 2 — Runtime, Keys, Parked & Branches (`docs/status.md:35-57`)

**Rationale:** Documents ports for `temporal_memory` (`:8040`), Community (`:8060`), and Messenger (`:8070`); adds env-var names (names only, zero secrets) for `identity` and `memory_bridge`; updates Parked (Community unparked for Entry 2 while parked `communities.py` stays frozen; Builder MCP permanently excluded per D6) and branch topology.

```diff
--- a/docs/status.md
+++ b/docs/status.md
@@ -35,23 +35,25 @@
 ## Runtime
 
 - `DATABASE_URL` blank (a single space) → SQLite fallback. Local Supabase optional (`supabase/CLAUDE.md`); PostgreSQL apply of recent migrations unverified.
-- Run: `cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030` · `cd apps/site; npm run dev` (http://localhost:3000/).
+- Run: Entry 1 API `cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030` · `temporal_memory` (`apps/memory/`, `:8040`) · Entry 2 Community API `app.community.server:app` (`:8060`) · Entry 3 Messenger API `app.messenger.server:app` (`:8070`) · `cd apps/site; npm run dev` (http://localhost:3000/).
 
 ## Keys (names only)
 
 - In use (2 Nov): `OPENAI_API_KEY`, `GOOGLE_PLACES_KEY`, `SERPAPI_KEY`, `TVLY_API_KEY`. Optional: `GOOGLE_MAPS_BROWSER_KEY`, `VERTEX_PROJECT` + ADC / `VERTEX_ACCESS_TOKEN`; flags `TRYON_FIXTURE=1`, `DEMO_MAIL=1`.
+- Shared Identity & Memory Bridge (`apps/api/app/identity/`, `apps/api/app/memory_bridge/`): `IDENTITY_JWT_ISSUER`, `IDENTITY_JWT_AUDIENCE`, `IDENTITY_JWT_JWKS_URL`, `IDENTITY_JWT_HS256_SECRET`, `IDENTITY_TOKEN_KEY`, `MEMORY_BRIDGE_BACKEND` (`fake|http`), `TM_BASE_URL`, `TM_SERVICE_TOKEN`, `TM_ADMIN_TOKEN`.
 - Founder to supply (from docs/archive/root/handoff.md, 2 Nov): `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` / `_REDIRECT_URI` + `OAUTH_TOKEN_KEY`, Gmail API enabled — **needed first**; Microsoft Graph app; GitHub token; `GOOGLE_MAPS_BROWSER_KEY` before public hosting; `DATABASE_URL` (Supabase); Apple/Google developer accounts + desktop signing.
 
 ## Parked (not claimed)
 
-- Community/social track (9 Nov; code stays). UI work (9 Nov), incl. the proposed Today / Goals / Memory shell (needs founder approval).
-- Plan 2 device switch / phone core; Plan 4 Services; Plan 6 full temporal memory (the lab builds on existing `mem_*` instead); Builder MCP; UAE Pass sandbox; browser Maps key for a public host; Postgres/Auth hosting; companion Phases C–F beyond the above.
+- Legacy `apps/api/app/communities.py` (9 Nov; frozen read-only — Entry 2 Dubai-io Community builds on `apps/community/` + `app/community/` with `cm_*` tables and no P2P chat per D2/D3). Legacy `apps/site` UI work (9 Nov; Entries 2 & 3 ship dedicated demo UIs under founder visual review).
+- Plan 2 device switch / phone core; Plan 4 Services; UAE Pass sandbox; browser Maps key for a public host; Postgres/Auth hosting; companion Phases C–F beyond the above.
+- **Permanently excluded (23 Nov, D6/D7):** Contested sticker Builder service / Builder MCP (`D:\Vscode\mirsal-builder-io`) and AI image/sticker generation in Messenger.
 - Native iOS STOPPED (23 Oct).
 
-Recommended, not set up (23 Oct, from docs/archive/root/handoff.md): Supabase (Postgres/Auth/Storage) + FastAPI as a container (Fly/Railway/Render/Cloud Run) + Vercel for the site; no Edge Functions rewrite. See `apps/api/CLAUDE.md`.
+Recommended, not set up for production (23 Oct); **contest staging (23 Nov, D10):** separate staging Supabase project for Entries 2 & 3 (sign-up disabled, test users only; Auth/RLS scripted from `apps/community/supabase/` and `apps/messenger/supabase/`, keeping `supabase/migrations/` frozen), plus secure tunnel from founder's PC for 18 Dec demo & adult tester runs. See `apps/api/CLAUDE.md`.
 
 ## Branches
 
-`main` for product work; `apps/web` frozen at `mobile-pwa-baseline-2026-10-23`. Docs cleanup on `docs-cleanup-2026-11-09`, pending founder review.
+`main` (reconciled Entry 1); `contest-shared` (shared identity & memory bridge); `societal` (Entry 2: Community); `business` (Entry 3: Messenger); `apps/web` frozen at `mobile-pwa-baseline-2026-10-23`.
```
