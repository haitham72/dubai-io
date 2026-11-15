# Status — 2 Nov 2026

Single current-state file. Detail lives in `handoff.md`, `cursor-plan.md`, git history.

## Open agent work

- Grok-style **ResultTemplate** for places / shopping / mail / sources; Maps pane enlarged.
- Temporal memory tables + `/api/memory/*` + Me timeline.
- Mail profiler `/api/mail/needs-reply` (live Gmail needs OAuth + `gmail.readonly`; `DEMO_MAIL=1` for fixture).

## Contest spine (shipped 2 Nov)

- Live **Google Places** in website chat (device location, Marina fallback); starter **Gyms near Marina**.
- Live **Google Shopping AE** via SerpAPI — photo **grid**, up to 5 stores; **Try it on** still-photo sheet (Vertex VTO / OpenAI / honest blocker).
- Memory lite: `clothing_size` + `area` → Me “You told me” + **Because…** chips on shopping.
- **Maps + Dashboard:** interactive in-app map + photos near you; weather uses the same pin.
- UI bots on sidebar (Lifestyle / Career / Social / Household / Money / Travel); demo threads still present for taxi/KHDA/etc.
- Keys in use: OpenAI, Google Places, SerpAPI, Tavily. Optional: `GOOGLE_MAPS_BROWSER_KEY`, `VERTEX_PROJECT` + ADC / `VERTEX_ACCESS_TOKEN`, `TRYON_FIXTURE=1` for tests.

## Branches

- `main` only for product work. `apps/web` frozen at `mobile-pwa-baseline-2026-10-23`.

## Parked (not claimed)

- Plan 2 device switch / phone core; Plan 4 Services; Plan 6 full temporal memory; Builder MCP; UAE Pass sandbox; Google OAuth + browser Maps key for public host; Postgres/Auth hosting.
- Companion Phases C–F beyond the lite memory + live APIs above.

## Run locally

```powershell
cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030
cd apps/site; npm run dev
```
