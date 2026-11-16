# Status — 9 Nov 2026

Single current-state file. Scope: `PLAN.md`. Open requests: [request-backlog.md](request-backlog.md).

## Direction

UI paused. The Know / Notice / Do pipeline is built headless in `apps/api/app/lab/` (steps: `apps/api/app/lab/CLAUDE.md`). Order (from docs/Researches/CLAUDE.md, 9 Nov): import (Gmail + Calendar; exported WhatsApp chats) → consolidate into `mem_*` and the life themes → reveal → people map → daily matched cards via the outbox; plus one task thread to an honest terminal state.

## Connectors (merged 16 Nov from `cursor/universal-connectors-395e`)

Framework in `apps/api/app/connectors`; docs in `docs/connectors/`. Records stay in `connector_records` and never write profile memory. Sync is explicit; outbound is denied until the owner approves the exact payload. Tested with mocks only, no live provider run. Build order is unchanged: Gmail + Calendar first. **WhatsApp Evolution (unofficial) is off and not approved**; it conflicts with the manual-export rule in `ARCHITECTURE.md` §14, so it needs a founder decision. Other sources (Slack, Telegram, Notion, etc.) are registered capabilities, not product claims. Per-provider live / file-import / not-callable breakdown: `docs/connectors/capability-matrix.md`.

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
