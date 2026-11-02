# Cursor plan — residence companion (this session, 2 Nov 2026)

**This file is the new plan from the 2 Nov planning session.**  
It is **not** a rewrite of `handoff.md` or `PLAN.md`. Those stay the **old / parallel** track (29 Oct domains, desktop full load, Plans 2–8). Do not merge or delete them into this file.

Detailed agent tasks: `docs/superpowers/plans/2026-11-02-residence-companion-mcp.md`  
Brief / ontology: `docs/superpowers/specs/2026-11-02-residence-companion-design.md`, `docs/superpowers/specs/2026-11-02-residence-ontology-tree.md`

---

## Product (locked this session)

- **Dubai-io** = Grok-style **residence companion** (life/work in Dubai).  
- **Not** DEWA Jarvis, not a shop, not a DubaiNow clone.  
- **Services** = a feature (cards → detail → approve → honest proof).  
- **Memory B:** Me + rare “Because…” chips; temporal_note **engine** (cloud-slim), not the personal vault.  
- **UI bots (coarse, app-owned):** Lifestyle · Career · Social · Household · Money · Travel · Me.  
- **Ontology (fine):** tree in memory only — user never browses folders.  
- **Taxi / UAE Pass:** demo appendix rules unchanged (no fake Paid / Filed).

---

## Contest spine — DONE (2 Nov, review-ready)

Shipped on `apps/site` + `apps/api` for founder review at **http://localhost:3000/**:

| Axis | Shipped |
|---|---|
| **Real API** | Google Places in chat (`Gyms near Marina`); Google Shopping AE (`I need a green shirt`) → up to **5 stores**, `provider_confirmed`, as_of |
| **Memory (MCP-lite)** | `clothing_size` + `area` facts; Me “You told me”; **Because size XL / in Marina** chips on shopping |
| **Design (money shot)** | Live place cards + **clothes photo grid** (Try it on / Open store) — shell polish deferred |
| **Clothes try-on** | Still-photo fitting sheet (18+ + approval) → Vertex VTO when configured, else OpenAI image, else honest blocker. Live AR stays LATER |
| **Full demos** | Sidebar Demo threads are interactive journeys (taxi / KHDA / insurance / Mamzar / guests / gym / laundry / AC) — not empty Approve stubs |
| **Maps + Dashboard** | Interactive in-app Google Map + place photos near **device location**; Dashboard “Near you” map strip; weather uses the same pin |

**Try demos:** sidebar → Lost bag / School + home / Clinic / Mamzar / Guests (tap through).  
**Try live:** `I live in Dubai Marina` → `I wear size XL` → `I need a green shirt` → **Try it on** · or **Gyms near Marina** · Maps / Dashboard rails.  
If demos were dismissed: **Restore demos** under the thread list.

```powershell
cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030
cd apps/site; npm run dev
```

### Open agent queue on this file

**Active (2 Nov evening):** Grok result template + bigger Maps (shipping) · temporal memory schema/API · mail profiler (OAuth-gated / `DEMO_MAIL=1`).  
Founder still supplies Google OAuth + Gmail API for live inbox.

### Parked (not agent-active until founder chooses)

- Full product memory engine / Builder MCP (Phases C–D of companion MCP plan)
- Five demo journey polish (Phase E) / UAE Pass appendix (F)
- Broad visual redesign; Plan 2 phone / Plan 4 Services (old `handoff` / `PLAN` track)

---

## MCP tracks (reference)

| Track | What | Status |
|---|---|---|
| **Product memory** | Schema, Me, context pack | Lite: area + clothing_size live; full engine parked |
| **Builder MCP** | Dev agent tools | Parked |

---

## Execution phases (companion plan)

| Phase | Status |
|---|---|
| A Demo resident docs | Scripts exist — polish parked |
| B UI domain bots | Done on website |
| C Product memory engine | Lite done; full parked |
| D Builder MCP | Parked |
| E Wire 5 demos | Parked (live Places/Shopping supersedes for review) |
| F UAE Pass appendix | Parked |
| G Optional browser-agent | Parked |
