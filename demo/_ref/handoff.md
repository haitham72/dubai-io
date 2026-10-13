# Handoff: 13 Oct 2026 session (branch `redesign`)

Read `CLAUDE.md` → `PLAN.md` (§7) → `demo/_ref/services/cases.md` + `intake.md` → this file.
(Kept under `demo/_ref/` because CLAUDE.md allows only four top-level .md files.)

## Done

**Docs (committed)**
- CLAUDE.md:
  - rule 9 = visible hypotheses
  - `inferred` provenance
  - "Service intake" rule → `demo/_ref/services/intake.md`
- ARCHITECTURE.md:
  - §12 temporal profiler (honesty tiers, tables, decay math, LangGraph hot/cold path, eval gate)
  - `categories` registry
  - tabs io · Maps · Services · Me
- PLAN.md v1.5:
  - floor items 12–13
  - step 0 = Home v2, step P = profiler
  - §7 loop (pick shell → pick case → build → review → rebuild)
  - Ask Maps jury objection
- `demo/_ref/services/cases.md`: C1–C14 + pattern library. Cases are ~1% of the app; the engine (registry + patterns + surfaces + profiler) does the rest.

**Lab (`demo/lab/`, static, published as two private Artifacts)**
- Links: cyan https://claude.ai/artifact/YZgGtUTmXuarcz97FvGH1w · chromatic https://claude.ai/artifact/DukxEKh196BPzRaREFuKqe (v3 published; the two edits below are not yet republished)
- **Home stage:** WebGL2 coverflow (silk / mesh / foil / alu / photo bands), top aura + bottom glow, soft card-by-card intro, profile-ranked "Try" cards with a "Because…" chip.
- **Arrival (C14):** iPhone Wi-Fi settings → captive sign-in (sponsor strip) → install sheet GET → progress → OPEN → icon expands. Unbranded.
- **io chat** (`chat.js`), currently a labelled keyword router:
  - lost item → RTA report pre-filled from "you told me", prepared · not filed · not recovered (C6)
  - airport → guide
  - service → offers
  - place → map
  - unclear → clarify chips
- **Airport guide (C5)** (`guide.js`):
  - signage-based steps; "I'm lost" by landmark
  - belt the user types
  - ride step reasons from Dubai time and terminal (no Metro at T2)
  - taxi plate/roof saved and reused by C6
- **Services** (`offers.js`), separate from Maps:
  - competing partner / merchant mini-apps, websites and marketplaces; published offers; Best price / Fastest holo badges
  - mini-apps in `iframe sandbox="allow-scripts"` via srcdoc; scoped bridge; the host rebuilds prices
  - single approval → merchant events (simulated) in chat
- **Maps** (`map.js`):
  - MapLibre on a bundled OpenStreetMap extract (`fixtures/dubai-map.json`, ODbL, 3D buildings), 27 fictional geolocated places
  - glass chips, draggable sheet (carousel → "Picked up from" → Good spots grid → detail)
- **Profile:** `profile.js` + `fixtures/profile-vectors.json`; `node demo/lab/tests/profile.test.mjs` → 92/92.
- **Media:** all sources and licences in `demo/lab/media.json` (Unsplash + OSM).

**Backend slice (`apps/api`, committed)**
- FastAPI app; serves the lab at `/lab` (same origin, so the phone needs no extra setup).
- **Luna** = LangGraph `normalize → understand (OpenAI responses.parse, Pydantic schema) → validate → remember`.
  - Short-term memory: LangGraph `InMemorySaver` per thread.
  - Long-term memory: stated facts only (`data/memory.json`, user_supplied, supersede + forget).
- `/api/places/search` and `/api/route` (Google Places New / Routes, server-side key, no caching).
- **Tests:**
  - 6 offline pass.
  - Live golden set (11 cases, incl. Arabic + typos) passes on both `gpt-6-luna` (high) and `gpt-6.1-sol` (medium).
- **Latency:**
  - luna-high: 6–9 s per turn.
  - sol-medium: 3–11 s per turn (most 4–8 s).
  - Both too slow for chat without streaming or a cheaper first pass. Decide.
- **Run:** `cd apps/api && .venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`, then open `http://<pc-ip>:8000/lab/home-v2-cyan.html`.

**Keys and models (verified 13 Oct)**
- `demo/.env` (gitignored) holds `OPENAI_API_KEY` and `GOOGLE_PLACES_KEY`; `config.py` reads `apps/api/.env`, then `demo/.env`.
- Real model IDs: `gpt-6-luna`, `gpt-6.1-sol` (also `gpt-6-sol`, `gpt-6-astra`). "luna-6" / "sol-6.1" are not IDs.
- Google key works for Places (New) and Routes (DXB T3 → Marina: 37.6 min, 40.9 km).
- This machine has a stale `REQUESTS_CA_BUNDLE` (points at a deleted file in another project). It breaks pip; `config.py` ignores it at runtime. To fix it permanently, remove that environment variable.

## Pending / not finished

1. ~~Republish~~ done (v4 has the flat bubbles and the logo restart).
2. **Wire `chat.js` to `/api/luna/turn`:**
   - Call it when served from `/lab` on the API host, with a ~15 s timeout and the lab router as fallback.
   - Show "Luna · gpt-6-luna (high) · intent · ms".
   - Show stated facts from the response as "You told me".
   - The published Artifacts cannot reach the API (sandbox CSP); live AI runs only when served locally.
3. **Latency decision** (founder):
   - option A: stream the reply
   - option B: Sol medium per turn + Luna high only for plans/bundles (e.g. C1)
   - option C: keep the lab router as an instant first guess, then Luna confirms

   Also consider prompt caching for the static instructions.
4. **Live Places on a map:** the Places policy requires a Google map. Do this in the Vite app with the Maps JS key; the lab keeps OSM + fixtures. A second browser key (Maps JavaScript API only, website-restricted to `localhost:5173` and the LAN IP) is still to be created. The current key is effectively the server key: restrict it to Places (New) + Routes.
5. **Founder to pick the shell palette** (cyan vs chromatic) on the iPhone. Not yet verified on device: whether the MapLibre worker and the srcdoc mini-apps run inside the Artifact sandbox. If either is blank, add a fallback.
6. **Step P (profiler on Postgres + pgvector)** is not started. Luna's FactStore JSON is a stand-in for told facts only.
7. **Google Agent Platform / Agent Registry** (GA 18 Jun 2026): not adopted. Our agents are LangGraph in `apps/api`, and Google APIs are tools. Revisit only if we need A2A interop. The extra APIs enabled by its setup wizard (Compute Engine, Notebooks, Model Armor, …) are unused; the founder may disable them.
8. **Vite + React port (`apps/web`)** of the picked shell and accepted cases: not started.
9. **CLAUDE.md stack line still says Anthropic Claude.** The founder switched to OpenAI models on 13 Oct; the PLAN.md §6.9 note records it. Update the CLAUDE.md line when the founder confirms that is permanent.
10. **WaveSpeed images:** the founder will provide the API later. Every slot in `demo/lab/media.json` has a `wavespeed_prompt` field (several still empty); swap images under the same slot ids and set `provenance: generated`. C1 candidate portraits go first.
11. **How to start the demo:**
    - tap the Dubai-io logo (top-left on Home, or in the chat header), or
    - Me → "Replay landing and Wi-Fi sign-in", or
    - add `#wifi` to the link.

    A refresh skips the intro once it has been seen (stored per browser).
12. **Untracked:** `demo/_ref/01 - Visitor onboarding/` (founder ref). Commit it with the next commit.
