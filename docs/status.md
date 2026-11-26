# Status — 26 Nov 2026

Single current-state file. Scope: `PLAN.md`. Open requests: [request-backlog.md](request-backlog.md).

## Direction (26 Nov 2026)

All 3 products and 9 client targets (Expo Go iPhone, website, Electron desktop for Dubai-io, Community, and Messenger) are on `main` (`0360773`) with **PRs #11–#15 merged and 0 open PRs**:
- **PR #11 (`E14`):** Community Facebook/Reddit social parity + two-tower recommender + opt-in TTL context profile + real Lower/recall + Community purge hook.
- **PR #12 (`E13a`):** D19 Lower/Restore (`0.01` floor / `0.10` active surface cutoff), D19b 100% explicit recall + weight boost, immediate account `"Delete my data"` (Redis + caches + sessions + Community purge + de-identified non-Google training backup).
- **PR #13 (`E13b`):** Shared vocabulary agent + `0009` migration + E10 cleanups.
- **PR #14:** Dev Test Bench (`/testbench/`, gated by `DEV_TESTBENCH=1`) + Community purge hard import.
- **PR #15:** Guarded Community 10-user / 7-group demo seed (`scripts/seed_community_10_users.py --apply` with `DEMO_SEED_ENABLED=true`).
- **Docs cleanup (`baf70a6`):** tracked markdown reduced from 330 to 175 files.

- **GrepMem pilot (`G:\Haitham\lab-data\grepmem-pilot\`, outside git):** standalone harness verified (8/8 synthetic). Per-export 7-day snapshot rebuilt on isolated owner `grepmem-pilot-2611` across 2 scoped chats (271 messages imported, 4 skipped; Chrome history: no; founder written OK for `claude -p` Haiku medium for this pilot only). Currently **blocked** on 8 extraction jobs stuck leased by Docker workers (`temporal-memory-worker-p0-1`, `worker-p1-1`, `beat-1`), which lack host `claude` CLI (`FileNotFoundError: 'claude'`). Fix: stop Docker worker/beat containers and run host Celery workers (`scripts/dev/start-all.ps1` does this automatically), requeue the 8 jobs until `facts > 0` + idle, redraft 24 prompts, then founder approval -> benchmark -> Lower pilot owner -> aggregate report to Claude.
- **Waiting on founder:** 13-check closed-Wi-Fi 3×3 test run (`apps/memory/upgrade/prompts/HANDOFF_integrator_2026-11-26b_testing.md` §3), GrepMem prompt approval after redraft, contest portal registration + prayer widget wording, and OpenAI model selection (`gpt-6-luna` is latest `luna`; `gpt-6.2-sol` / `gpt-6.2-astra` available).
- **Next queue (post-testing):** `dev/dubai-io` desktop screen-time widget then Google Drive + memory; `dev/community` fail-closed `demo_fixture` guard follow-up from PR #15; `dev/messenger` idle.

Engine: `temporal_note` (`docs/plan/Memory/memory.md` §18). Delivery matrix: `PLAN.md` §0. Treat the 16–18 Nov lab results below as historical.

## Historical: MEM-01 & Acceptance Gates Status (18 Nov 2026; superseded by temporal_note)

- **MEM-01 status:** **Unproven at the Hindsight LLM-extraction layer** (gated on **SRE AC-1** `apps/api/tests/test_live_hindsight_llm.py::test_ac1_live_hindsight_llm_extraction` with `HINDSIGHT_URL` + `HINDSIGHT_LLM_ENABLED=1`).
  - **Architectural decision (`PLAN.md` §2, AC-5):** Hindsight swappable backend retained; fix Dubai-io rule violations only (`§R-ND` decay-with-floor, Amazon.ae/AED, `"I noticed"` phrasing with two-visit qualification, sensitive-category confirmation gate); full Postgres/markdown-tree re-fit deferred until card contract and AC-1 pass.
  - **Single memory plan (18 Nov):** `docs/plan/Memory/memory.md` (research dumps in `docs/plan/Memory/_archive/` only). FTS-first hybrid; topics = spine + dynamic subtopics + aliases; typed `links` ≠ GraphRAG; Mnemosyne-like live session + Hindsight weekly backfill.
  - **Lab evidence — `mamty-hindsight` prompt-level retain lab run (`G:\Haitham\lab-data\mamty-hindsight\`, AC-L1 / AC-L5):** Offline multi-agent retain (~57 ISO weeks, ~444 facts; playbook in `apps/api/app/lab/CLAUDE.md`). **Not** live `hindsight-api` (no embeddings bank, no `reflect`, no cross-week consolidate). Does not close SRE AC-1 (`MEM-01` remains **unproven**). Blocked from `mem_*` until AC-L3/L4 + confirm. **vs cards UI (`design/17-11-2026/`):** medium fuel for Family/Mom person scope only; **low** as shippable morning-brief feed; Mermaid `graph-from-weeks.md` is diagnostic only (not product). Next useful slice for that design: Gmail + Calendar + one card generator — not more week files.
  - **Verified offline in CI (`154 passed` across lab/memory/connector/AC-1–5/AC-L1–5 suites):** `pytest -q tests/test_live_hindsight_llm.py tests/test_lab_*.py tests/test_memory_schema.py tests/test_connectors.py tests/test_connectors_api.py`.

## Historical: Headless Lab Pipeline (built 16 Nov, `apps/api/app/lab/`)

- **Built & tested (`apps/api/tests/test_lab_parse.py`, `test_lab_rows.py`, `test_lab_skills.py`, `test_lab_chunking.py`, `test_lab_compact.py`, `test_lab_pipeline.py`, `test_lab_eval.py`):** WhatsApp `.txt` parser (`parse.py`: iOS, Android, copy-paste) and email `.mbox`/`.eml` parser (`parse_email.py`); generic skill-based extraction (`engine.py`, `skills/chat.py`, `skills/email.py`) with user-supplied `circle.json` relations/nicknames and Arabic/Latin typo-alias detection (`circle.py`); two-layer fail-closed sensitive filter (`sensitive.py` + `audit`); local sentiment & emotion classifier worker (`scoring.py` / `scorer_worker.py`); multi-space embeddings + hybrid BM25/dense/RRF search with Arabic-to-English query translation (`index.py`, `searchlib.py`); cited-evidence follow-up resolver (`followups.py`); two-step life-theme assignment + Mermaid mindmap & co-occurrence graph (`tree.py`, `tree_assign.py`); and S0–S5 evaluation harness (`evaluate.py`).
- **Execution queue (`PLAN.md` §2, 17 Nov — do not reorder 1–3):** (1) **AC-1:** Live Hindsight LLM-provider extraction test (`tests/test_live_hindsight_llm.py`) · (2) **AC-2:** Card lifecycle (`new → seen → actioned → dismissed → resolved` + `reminder saved — delivery not yet enabled` label, `docs/plan/morning-brief.md` §8.3) · (3) **AC-3:** Orchestrator query rewriter (`docs/plan/morning-brief.md` §8.1.1) · (4) **AC-4:** Sensitive rule in canon (`CLAUDE.md`, `ARCHITECTURE.md` §7) · (5) **AC-5:** `MEM-01` decision text (`PLAN.md` §2) · (6) Backfill agent spec (`docs/plan/Memory/memory.md` §20) · (7) Reading list appendix (`docs/plan/Memory/_archive/memory-research-2026-11.md` §8) · (8) Local Qwen 1.5B–3B classifier integration (only after AC-1–AC-3 are green).

## Connectors (merged 16 Nov from `cursor/universal-connectors-395e`)

Framework in `apps/api/app/connectors`; consolidated docs in `docs/connectors/README.md`. Records stay in `connector_records` and never write profile memory. Sync is explicit; outbound is denied until the owner approves the exact payload. Tested with mocks only, no live provider run. Build order is unchanged: Gmail + Calendar first. **WhatsApp Evolution (unofficial) is off and not approved**; it conflicts with the manual-export rule in `ARCHITECTURE.md` §14, so it needs a founder decision. Other sources (Slack, Telegram, Notion, etc.) are registered capabilities, not product claims. Per-provider live / file-import / not-callable breakdown and priority scores: `docs/connectors/README.md`.

## Shipped contest spine (2 Nov, `apps/site` + `apps/api`; historical)

- Live **Google Places** in website chat (device location, Marina fallback); starter **Gyms near Marina**.
- Live **Google Shopping AE** via SerpAPI — photo grid, up to 5 stores; **Try it on** still-photo sheet (Vertex VTO / OpenAI / honest blocker).
- Memory lite: `clothing_size` + `area` → Me "You told me" + **Because…** chips on shopping.
- **Maps + Dashboard:** in-app map + photos near you; weather uses the same pin.
- UI bots on the sidebar (superseded by the 9 Nov life themes); demo threads.
- Built 2 Nov, review pending: Grok-style result cards; `mem_*` + `/api/memory/*` + Me timeline; mail profiler `/api/mail/needs-reply` (live Gmail needs OAuth; `DEMO_MAIL=1` = fixture).

## Runtime

- `apps/api/.env` is populated for local SQLite (`DATABASE_URL=` blank; offline `:15422` preserved as `#` comment) + Google OAuth (`installed` client) + Fernet keys + `TM_ADMIN_TOKEN`. (Local Supabase optional: `supabase/CLAUDE.md`; PostgreSQL apply of recent migrations unverified.)
- Launch all 3×3 targets with `scripts\dev\start-all.ps1 -Shells` (controlled same-network Wi-Fi, no tunnel for this phase; physical iPhone uses 6-character PC pairing code on Community & Messenger and QR pairing on Dubai-io). API only: `cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030`. Keep OAuth keys server-side.
- Community 10-user demo seed: `$env:DEMO_SEED_ENABLED="true"; apps\api\.venv\Scripts\python.exe scripts\seed_community_10_users.py --apply`. Dev Test Bench at `http://localhost:8000/testbench/` (gated by `DEV_TESTBENCH=1`).

## Keys (names only)

- Populated in gitignored `apps/api/.env`: `OPENAI_API_KEY`, `GOOGLE_PLACES_KEY`, `SERPAPI_KEY`, `TVLY_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, redirect URIs, `OAUTH_TOKEN_KEY`, `IDENTITY_TOKEN_KEY`, `TM_SERVICE_TOKEN`, `TM_ADMIN_TOKEN` (flags `TRYON_FIXTURE=1`, `DEMO_MAIL=1` optional).
- Optional keys still unset: `GOOGLE_MAPS_BROWSER_KEY`, `NARAROUTER_API_KEY`, `WHATSAPP_EVOLUTION_*`, `VERTEX_*`. (Before public hosting / later phases: `GOOGLE_MAPS_BROWSER_KEY`, `DATABASE_URL` Supabase, Microsoft Graph app, GitHub token, Apple/Google developer accounts + desktop signing.)

## Parked (not claimed)

- UI work (9 Nov; `apps/site` and native Swift paused; design polish follows E0–E4), incl. the proposed Today / Goals / Memory shell (needs founder approval).
- Plan 2 device switch / phone core; Plan 4 Services; Plan 6 full temporal memory (the lab builds on existing `mem_*` instead); Builder MCP; UAE Pass sandbox; browser Maps key for a public host; Postgres/Auth hosting; companion Phases C–F beyond the above.
- Native iOS STOPPED (23 Oct).

## Hosting

The current demo runs on the founder's PC with local Postgres (E1). Cloudflare Tunnel is planned under D13. Azure's $200 demo credit is reserved for later deployment. (The 23 Oct Fly/Railway/Vercel recommendation is superseded.) See `apps/api/CLAUDE.md`.

## Branches

3-dev-branch rule: `main` + `dev/dubai-io`, `dev/community`, `dev/messenger`, all synced with `main` (one agent per dev branch; integrator gates PRs into `main`). `apps/web` is frozen at `mobile-pwa-baseline-2026-10-23`.
