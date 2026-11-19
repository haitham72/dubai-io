# Status — 18 Nov 2026

Single current-state file. Scope: `PLAN.md`. Open requests: [request-backlog.md](request-backlog.md).

## Direction

UI paused. Active work is closing **AC-1 through AC-3** (`apps/api/tests/test_live_hindsight_llm.py`) before any new feature work, alongside the Know / Notice / Do pipeline (`apps/api/app/lab/CLAUDE.md`) and the memory plan (`docs/plan/Memory/memory.md`; locked rulings still in `PLAN.md` §2).

## MEM-01 & Acceptance Gates Status (18 Nov 2026)

- **MEM-01 status:** **Unproven at the Hindsight LLM-extraction layer** (gated on **SRE AC-1** `apps/api/tests/test_live_hindsight_llm.py::test_ac1_live_hindsight_llm_extraction` with `HINDSIGHT_URL` + `HINDSIGHT_LLM_ENABLED=1`).
  - **Architectural decision (`PLAN.md` §2, AC-5):** Hindsight swappable backend retained; fix Dubai-io rule violations only (`§R-ND` decay-with-floor, Amazon.ae/AED, `"I noticed"` phrasing with two-visit qualification, sensitive-category confirmation gate); full Postgres/markdown-tree re-fit deferred until card contract and AC-1 pass.
  - **Single memory plan (18 Nov):** `docs/plan/Memory/memory.md` (research dumps in `docs/plan/Memory/_archive/` only). FTS-first hybrid; topics = spine + dynamic subtopics + aliases; typed `links` ≠ GraphRAG; Mnemosyne-like live session + Hindsight weekly backfill.
  - **Lab evidence — `mamty-hindsight` prompt-level retain lab run (`G:\Haitham\lab-data\mamty-hindsight\`, AC-L1 / AC-L5):** Offline multi-agent retain (~57 ISO weeks, ~444 facts; playbook in `apps/api/app/lab/CLAUDE.md`). **Not** live `hindsight-api` (no embeddings bank, no `reflect`, no cross-week consolidate). Does not close SRE AC-1 (`MEM-01` remains **unproven**). Blocked from `mem_*` until AC-L3/L4 + confirm. **vs cards UI (`design/17-11-2026/`):** medium fuel for Family/Mom person scope only; **low** as shippable morning-brief feed; Mermaid `graph-from-weeks.md` is diagnostic only (not product). Next useful slice for that design: Gmail + Calendar + one card generator — not more week files.
  - **Verified offline in CI (`154 passed` across lab/memory/connector/AC-1–5/AC-L1–5 suites):** `pytest -q tests/test_live_hindsight_llm.py tests/test_lab_*.py tests/test_memory_schema.py tests/test_connectors.py tests/test_connectors_api.py`.

## Headless Lab Pipeline (built 16 Nov, `apps/api/app/lab/`)

- **Built & tested (`apps/api/tests/test_lab_parse.py`, `test_lab_rows.py`, `test_lab_skills.py`, `test_lab_chunking.py`, `test_lab_compact.py`, `test_lab_pipeline.py`, `test_lab_eval.py`):** WhatsApp `.txt` parser (`parse.py`: iOS, Android, copy-paste) and email `.mbox`/`.eml` parser (`parse_email.py`); generic skill-based extraction (`engine.py`, `skills/chat.py`, `skills/email.py`) with user-supplied `circle.json` relations/nicknames and Arabic/Latin typo-alias detection (`circle.py`); two-layer fail-closed sensitive filter (`sensitive.py` + `audit`); local sentiment & emotion classifier worker (`scoring.py` / `scorer_worker.py`); multi-space embeddings + hybrid BM25/dense/RRF search with Arabic-to-English query translation (`index.py`, `searchlib.py`); cited-evidence follow-up resolver (`followups.py`); two-step life-theme assignment + Mermaid mindmap & co-occurrence graph (`tree.py`, `tree_assign.py`); and S0–S5 evaluation harness (`evaluate.py`).
- **Execution queue (`PLAN.md` §2, 17 Nov — do not reorder 1–3):** (1) **AC-1:** Live Hindsight LLM-provider extraction test (`tests/test_live_hindsight_llm.py`) · (2) **AC-2:** Card lifecycle (`new → seen → actioned → dismissed → resolved` + `reminder saved — delivery not yet enabled` label, `docs/plan/morning-brief.md` §8.3) · (3) **AC-3:** Orchestrator query rewriter (`docs/plan/morning-brief.md` §8.1.1) · (4) **AC-4:** Sensitive rule in canon (`CLAUDE.md`, `ARCHITECTURE.md` §7) · (5) **AC-5:** `MEM-01` decision text (`PLAN.md` §2) · (6) Backfill agent spec (`docs/plan/backfill-agent.md`) · (7) Reading list appendix (`docs/plan/Memory/_archive/memory-research-2026-11.md` §8) · (8) Local Qwen 1.5B–3B classifier integration (only after AC-1–AC-3 are green).

## Connectors (merged 16 Nov from `cursor/universal-connectors-395e`)

Framework in `apps/api/app/connectors`; consolidated docs in `docs/connectors/README.md`. Records stay in `connector_records` and never write profile memory. Sync is explicit; outbound is denied until the owner approves the exact payload. Tested with mocks only, no live provider run. Build order is unchanged: Gmail + Calendar first. **WhatsApp Evolution (unofficial) is off and not approved**; it conflicts with the manual-export rule in `ARCHITECTURE.md` §14, so it needs a founder decision. Other sources (Slack, Telegram, Notion, etc.) are registered capabilities, not product claims. Per-provider live / file-import / not-callable breakdown and priority scores: `docs/connectors/README.md`.

## Shipped contest spine (2 Nov, `apps/site` + `apps/api`)

- Live **Google Places** in website chat (device location, Marina fallback); starter **Gyms near Marina**.
- Live **Google Shopping AE** via SerpAPI — photo grid, up to 5 stores; **Try it on** still-photo sheet (Vertex VTO / OpenAI / honest blocker).
- Memory lite: `clothing_size` + `area` → Me "You told me" + **Because…** chips on shopping.
- **Maps + Dashboard:** in-app map + photos near you; weather uses the same pin.
- UI bots on the sidebar (superseded by the 9 Nov life themes); demo threads.
- Built 2 Nov, review pending: Grok-style result cards; `mem_*` + `/api/memory/*` + Me timeline; mail profiler `/api/mail/needs-reply` (live Gmail needs OAuth; `DEMO_MAIL=1` = fixture).

## Runtime

- `DATABASE_URL` blank (a single space) → SQLite fallback. Local Supabase optional (`supabase/CLAUDE.md`); PostgreSQL apply of recent migrations unverified.
- Run: `cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030` · `cd apps/site; npm run dev` (http://localhost:3000/).

## Keys (names only)

- In use (2 Nov): `OPENAI_API_KEY`, `GOOGLE_PLACES_KEY`, `SERPAPI_KEY`, `TVLY_API_KEY`. Optional: `GOOGLE_MAPS_BROWSER_KEY`, `VERTEX_PROJECT` + ADC / `VERTEX_ACCESS_TOKEN`; flags `TRYON_FIXTURE=1`, `DEMO_MAIL=1`.
- Founder to supply (from docs/archive/root/handoff.md, 2 Nov): `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` / `_REDIRECT_URI` + `OAUTH_TOKEN_KEY`, Gmail API enabled — **needed first**; Microsoft Graph app; GitHub token; `GOOGLE_MAPS_BROWSER_KEY` before public hosting; `DATABASE_URL` (Supabase); Apple/Google developer accounts + desktop signing.

## Parked (not claimed)

- Community/social track (9 Nov; code stays). UI work (9 Nov), incl. the proposed Today / Goals / Memory shell (needs founder approval).
- Plan 2 device switch / phone core; Plan 4 Services; Plan 6 full temporal memory (the lab builds on existing `mem_*` instead); Builder MCP; UAE Pass sandbox; browser Maps key for a public host; Postgres/Auth hosting; companion Phases C–F beyond the above.
- Native iOS STOPPED (23 Oct).

## Hosting

Recommended, not set up (23 Oct, from docs/archive/root/handoff.md): Supabase (Postgres/Auth/Storage) + FastAPI as a container (Fly/Railway/Render/Cloud Run) + Vercel for the site; no Edge Functions rewrite. See `apps/api/CLAUDE.md`.

## Branches

`main` for product work; `apps/web` frozen at `mobile-pwa-baseline-2026-10-23`. Docs cleanup on `docs-cleanup-2026-11-09`, pending founder review.
