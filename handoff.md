# Handoff — 21 Oct 2026

**Branches:** `redesign` (web snapshot `feb4163`, pushed), `ios-swift` (native first slice handed off; backend work resumes on `redesign`). Scope and remaining work: `PLAN.md` (§4). Architecture: `ARCHITECTURE.md`. Review checklist: `docs/user-app-review-guide.md`.

## Current status before founder review

The web demo is ready for a founder walkthrough, with documented limits; it is not declared production ready or physically verified on iPhone. Start at `http://<pc-ip>:8000/#demo.wifi` to see Wi-Fi and gradient onboarding. Browse/chat transitions, fixed-price sandbox merchant approval/status loop, live discovery and explicit 2D/3D Maps with one cyan category row have browser coverage.

The original Postgres database remains unresolved. Port 8000 currently uses separate SQLite review data under `output/review-data`, not a recovered copy of the original records. Supabase migration/Auth, the broad temporal recommender, selected-card/itinerary context and event/sponsorship features are planned, not implemented. Full findings: `docs/review-findings-2026-10-21.md`; access/demo assessment: `docs/references/api-catalog.md`.

Native first-slice source is handed off in `handoff-ios.md`. The founder will test on a Mac and iPhone 13 Pro Max; further native features are parked while Supabase/recommender work resumes. Google OAuth is deferred until last; the existing tester cookie session remains the development identity.

## Native first-slice status

`ios-swift` is published from the pushed web baseline. `apps/ios` now contains a checked-in Xcode project/shared scheme, a local Swift package with API DTOs/URL validation/session handling and contract tests, and SwiftUI source for arrival/gradients, browse/chat, catalog, Google 2D discovery/separate MapKit 3D preview, saved details and Safari browsing sheets. No external Swift dependencies or project generator are required to open it on the Mac.

macOS CI run 39585052919 passed seven package tests and the unsigned Simulator build at `cfb65a4`. No Simulator UI or device run is claimed. Setup: `apps/ios/README.md`. Merchant approval/mini-app/SSE parity, production Auth and APNs/Live Activity remain pending. This is a native first slice, not a completed conversion.

## Run

1. `cd apps/api; docker compose --env-file .env up -d` (Postgres 16 + pgvector; without `DATABASE_URL` the API uses SQLite in `data/`).
2. `.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` (also starts the widget origin on `:8001`).
3. Phone: `http://<pc-ip>:8000/#demo.wifi`. Second device: `http://<pc-ip>:8000/merchant.html`, PIN in `apps/api/data/merchant.pin`.
4. One-off after switching to Postgres: `.\.venv\Scripts\python -m app.migrate_sqlite` copies old SQLite data (already done on this PC).

`.env` keys: OpenAI, Google (Places + Routes), Tavily, SerpAPI, Finnhub, Postgres. `LUNA_EFFORT=medium` (bench: high 4.7 s · medium 3.5 s · low 2.3 s per turn, same accuracy). Web assets are `no-cache`, so phones pick up edits on reload.

## State

Working end to end (browser-verified 19 Oct): Luna at `/` · one order path (server catalog prices → one approval → sandbox merchant inbox → live SSE card) · deadline loop (10:00 → ask 08:30 → merchant confirms) · reminders + labelled Demo triggers (dedupe, consent, quiet hours) · taxi memory → prefilled lost-item report · profile learning from real choices (Confirm / Not true / Forget persist) · profile document + bi-temporal facts in Postgres · Luna research tools (Tavily/SerpAPI cited answers, Finnhub quotes, civic questions refused) · product search (live Amazon.ae results via SerpAPI, links only) · live Google Routes ETA · **Maps view on real Google Places** (photos, open now, phone, website, Directions) on a server-proxied Google static map · chat restyled to `02-rows`/`03-approve-events` (flat, AI text unboxed) · rich results survive reload · profile learns from real use only.

Latest web baseline: 81 backend passed on SQLite, 11 live cases skipped; earlier PostgreSQL coverage predates the local runtime failure; JS 92 + 8 + 12.

## Known limits (cannot be real yet)

- Partner mini-apps, their prices and the merchant are sandbox (no real merchant joined). Arrival Wi-Fi captive portal is a staged concept (no airport partnership). Guide photos are illustrative (no licensed DXB imagery). Taxi fare range is a fixed estimate (no verified tariff source). RTA lost-item has no API (report is prepared + official handoff only).

- Sandbox merchant (no real shop yet); anonymous cookie sessions; merchant PIN doubles as operator access.
- Google 2D map pins are implemented; flight "landed" is a Demo trigger until a flight API key exists.
- Research answers take ~6–9 s (search + a second model call).
- Purchasing/payments are not available (`docs/references/api-catalog.md`).

## Review notes

- **Request order:** `docs/request-backlog.md` tracks every open request. Founder lifted the native hold: docs/status → commit/push redesign → ios-swift branch → first native slice. Recommender/Supabase/memory implementation remains pending.
- **Reviewer assessment:** `docs/review-findings-2026-10-21.md` lists the reliability/privacy/deployment gaps, map query/async metadata issues, remaining visual differences and physical-phone validation limits. Assessment is delivered; fixes are not implied by that status.
- **API/demo review:** `docs/references/api-catalog.md` now distinguishes no-key/developer/OAuth/affiliate/partner/business-verification gates and recommends live discovery + labelled sandbox merchant + official handoffs. Careem MCP is a newly documented reviewed-access option (company/team optional on its access form); no access request or integration was performed.
- **Maps, 21 Oct:** live Google 2D and illustrative 3D are explicit modes. Loading/errors/late responses do not switch engines. One category row drills into category options; Back returns to categories. Selected chips use cyan tokens. Browser checks cover drill-down, theme, retries, late responses and hidden-camera stability. Screenshot: `output/playwright/maps-single-row-cyan.png`.
- **21 Oct:** Browse has a floating category dock plus Ask. Ask enters chat with one composer; the dock is hidden and inert. Back/Escape restore browsing, scroll and the unsent draft. Services use horizontal category rows. Keyboard viewport handling and reduced-motion/transparency fallbacks added. Desktop browser checks at 320–430 px passed; physical iPhone keyboard validation is still needed.
- **Database:** original Postgres container stalled after a server-process crash; its normal restart also stalled. No volume reset. Port 8000 currently uses separate SQLite review data under `output/review-data`, not the original database. See `docs/references/backend-options.md` for evidence and the Supabase proposal.
- Founder: add review notes here.
