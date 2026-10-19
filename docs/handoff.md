# Handoff — 19 Oct 2026

**Branch** `redesign`. Scope and remaining work: `PLAN.md` (§4). Architecture: `ARCHITECTURE.md`. Review checklist: `docs/user-app-review-guide.md`.

## Run

1. `cd apps/api; docker compose --env-file .env up -d` (Postgres 16 + pgvector; without `DATABASE_URL` the API uses SQLite in `data/`).
2. `.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` (also starts the widget origin on `:8001`).
3. Phone: `http://<pc-ip>:8000/#demo.wifi`. Second device: `http://<pc-ip>:8000/merchant.html`, PIN in `apps/api/data/merchant.pin`.
4. One-off after switching to Postgres: `.\.venv\Scripts\python -m app.migrate_sqlite` copies old SQLite data (already done on this PC).

`.env` keys: OpenAI, Google (Places + Routes), Tavily, SerpAPI, Finnhub, Postgres. `LUNA_EFFORT=medium` (bench: high 4.7 s · medium 3.5 s · low 2.3 s per turn, same accuracy). Web assets are `no-cache`, so phones pick up edits on reload.

## State

Working end to end (browser-verified 19 Oct): Luna at `/` · one order path (server catalog prices → one approval → sandbox merchant inbox → live SSE card) · deadline loop (10:00 → ask 08:30 → merchant confirms) · reminders + labelled Demo triggers (dedupe, consent, quiet hours) · taxi memory → prefilled lost-item report · profile learning from real choices (Confirm / Not true / Forget persist) · profile document + bi-temporal facts in Postgres · Luna research tools (Tavily/SerpAPI cited answers, Finnhub quotes, civic questions refused) · product search (live Amazon.ae results via SerpAPI, links only) · live Google Routes ETA · **Maps view on real Google Places** (photos, open now, phone, website, Directions) on a server-proxied Google static map · chat restyled to `02-rows`/`03-approve-events` (flat, AI text unboxed) · rich results survive reload · profile learns from real use only.

Tests: 79 backend passed (also on Postgres with `TEST_DATABASE_URL`), 11 live cases skipped; JS 92 + 8 + 12.

## Known limits (cannot be real yet)

- Partner mini-apps, their prices and the merchant are sandbox (no real merchant joined). Arrival Wi-Fi captive portal is a staged concept (no airport partnership). Guide photos are illustrative (no licensed DXB imagery). Taxi fare range is a fixed estimate (no verified tariff source). RTA lost-item has no API (report is prepared + official handoff only).

- Sandbox merchant (no real shop yet); anonymous cookie sessions; merchant PIN doubles as operator access.
- Places results are a list only (no Google map pins yet); flight "landed" is a Demo trigger until a flight API key exists.
- Research answers take ~6–9 s (search + a second model call).
- Purchasing/payments are not available (`docs/references/api-catalog.md`).

## Review notes

_(Founder: add notes here while following `docs/user-app-review-guide.md`.)_
