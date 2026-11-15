# Dubai-io — Plan

**Single source** for direction, scope, current state and what's next. Updated 15 Nov 2026 · Owner: Haitham · Branch: `main`.

Merged into this file on 15 Nov: old `PLAN.md`, `handoff.md`, `cursor-plan.md`, `docs/status.md`, `docs/request-backlog.md`, `docs/implementation-plan.md`. Originals: [docs/archive/](docs/archive/README.md). Done work lives in git history.

## 1. What we're building

Dubai-io is a Grok-style **residence companion** for everyday life and work in Dubai (founder, 2 Nov). It remembers context, prepares next steps and brings decisions that need you. Services is a feature (cards → detail → approve → honest proof), not the product. Not DEWA Jarvis, not a shop, not a DubaiNow clone.

- **Behaviour target:** Grok Bot + ChatGPT Dots + Claude Duet. Reference run: the founder's "why didn't my Puffy job application pay off" (search notes + Gmail/Outlook → small-model fan-out → advice → draft reply in the right account).
- **Memory:** temporal_note engine (cloud-slim), not the personal vault. Me + "Because…" chips.
- **UI bots (coarse, app-owned):** Lifestyle · Career · Social · Household · Money · Travel · Me. Fine ontology lives in memory only.
- **Cases that must survive:** DXB airport guide, lost item in a taxi.
- **Contest:** Create AI Agents Championship, Best Personal AI Agent. Submission **January 2027** (prototype + pitch deck + demo video); Grand Final first week of **May 2027**. Internal target for deck/video/small user test: **18 Dec 2026**.

## 2. Founder priorities and decisions

- **Quality (23 Oct, final word for this stage):** no rush to ship — polished, refined, working, and **easy to change all the time**: a design change is **one edit that echoes everywhere** (website, desktop, iOS/Android). One React codebase (`apps/site`), one design system (tokens + shared components), light mode first, dark (Graphite) after.
- **Final delivery:** iOS/Android + desktop + website from ONE React codebase (`apps/site`; Capacitor mobile, Tauri/Electron desktop). Swift STOPPED 23 Oct.
- **Original mobile app (`apps/web`) is the reference**, not "classic/old". Frozen at tag `mobile-pwa-baseline-2026-10-23`, byte-identical (`git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web`). New phone experience mirrors it with minimal changes. Retire only after parity + founder approval.
- **Quality bar:** Feed is the best screen (benchmark); Services is the weakest → quality uplift when ported.
- **Look:** white + `#357F92`, soft haze on home/onboarding, dark = Graphite. Visual targets: `.superpowers/brainstorm/94241-1792742190/content/img/v3/`.
- **Mirsal-redesign** is visual craft only; Dubai-io is the product.
- **No bidding, quotes or negotiation** — fixed published prices (10 Oct).
- **Unlocked 23 Oct:** government transactions, bill top-ups/payments, in-app donations, third-party purchasing — each through a real adapter with verified evidence, no fake sends.
- **Still locked:** copying the DubaiNow look, fake statuses, invented facts, bidding/negotiation.
- **Hosting (recommended 23 Oct):** Supabase (Postgres/Auth/Storage) + FastAPI container + Vercel for the site. Deployment is a later stage (15 Nov).
- **Connectors (15 Nov):** testers + contest only (no App Review). Founder uploads own WhatsApp export; testers connect automatically via WhatsApp Coexistence. No DM auto-replies (separate app).
- **Docs (15 Nov):** this file is the single plan; feature designs live in `docs/plan/` and `docs/services/`.

Earlier product rulings D01–D18 (19 Oct): [docs/archive/PLAN-2026-11-02.md §3](docs/archive/PLAN-2026-11-02.md).

## 3. Current state (2 Nov, review-ready)

Review at http://localhost:3000/ (API :8030).

| Area | Shipped |
|---|---|
| Live APIs | Google Places in chat (`Gyms near Marina`); Google Shopping AE via SerpAPI → photo grid, up to 5 stores, `provider_confirmed` + as_of |
| Memory (lite) | `clothing_size` + `area` facts → Me "You told me" + "Because…" chips on shopping |
| Try-on | Still-photo sheet (18+ + approval) → Vertex VTO / OpenAI image / honest blocker |
| Maps + Dashboard | Interactive Google Map + photos near device location; Dashboard near-you strip; weather on the same pin |
| UI bots | Sidebar domain bots; interactive demo threads (taxi / KHDA / insurance / Mamzar / guests / gym / laundry / AC) |
| In progress (2 Nov) | Grok-style ResultTemplate (places/shopping/mail) + bigger Maps · temporal memory `/api/memory/*` + Me timeline · mail profiler `/api/mail/needs-reply` (needs Google OAuth; `DEMO_MAIL=1` fixture) |

**Try:** `I live in Dubai Marina` → `I wear size XL` → `I need a green shirt` → Try it on · Maps · Me.

Keys in use: OpenAI, Google Places, SerpAPI, Tavily. Optional: `GOOGLE_MAPS_BROWSER_KEY`, `VERTEX_PROJECT`, `TRYON_FIXTURE=1`.

## 4. Next (planning, 15 Nov)

| Item | Doc | State |
|---|---|---|
| Connectors: Instagram, WhatsApp, Slack, Gmail/Outlook + "know me" profile | [docs/plan/connectors.md](docs/plan/connectors.md) | Planning |
| Agents: candidates list, template, orchestrator | [docs/services/agents/](docs/services/agents/README.md) | Planning |
| Emails agent (job applications first) | [docs/services/agents/emails.md](docs/services/agents/emails.md) | Design draft |
| Contest agent picks (proposed) | Lost item in transport · Documents & expiry + Bills · Job applications | Founder to choose |

## 5. Parked (founder chooses later)

| Item | Doc |
|---|---|
| Domains + website-first (Household / Places & trips / Services / Work & admin / General) | [docs/plan/domains.md](docs/plan/domains.md) |
| Journeys (KHDA, insurance, Mamzar) | [docs/plan/journeys.md](docs/plan/journeys.md) |
| Unified app design (north star, Plans 2–8) | [docs/plan/unified-app-design.md](docs/plan/unified-app-design.md) |
| Plan 2 device switch / phone core | [docs/superpowers/plans/2026-10-23-device-switch-and-phone-core.md](docs/superpowers/plans/2026-10-23-device-switch-and-phone-core.md) |
| Temporal memory (full engine) | [docs/superpowers/plans/2026-10-23-temporal-memory.md](docs/superpowers/plans/2026-10-23-temporal-memory.md) |
| Desktop full load | [docs/superpowers/plans/2026-10-29-desktop-full-load.md](docs/superpowers/plans/2026-10-29-desktop-full-load.md) |
| Residence companion phases C–G (memory engine, Builder MCP, demo journeys, UAE Pass) | [docs/superpowers/plans/2026-11-02-residence-companion-mcp.md](docs/superpowers/plans/2026-11-02-residence-companion-mcp.md) + `docs/superpowers/specs/` |
| Unified dashboard (founder ops + mobile side view) | [docs/plan/dashboard.md](docs/plan/dashboard.md) |
| Calls WhatsApp-style, services 3.1 thumbnails, panels not popups, services directory | [docs/plan/calls-services-panels.md](docs/plan/calls-services-panels.md) |
| Website rebuild brief | [docs/plan/website-rebuild.md](docs/plan/website-rebuild.md) |
| Services uplift to Feed quality (Plan 4) | — |
| Google OAuth + browser Maps key for public host; Postgres/Auth hosting | — |
| SaaS licensing of the approvals engine (idea only) | — |
| iOS Swift app (stopped) | [docs/plan/ios-upgrade.md](docs/plan/ios-upgrade.md), [docs/archive/ios-swift-plan.md](docs/archive/ios-swift-plan.md) |

## 6. Scope

**IN:** persistent chat · proactive reminders from deterministic triggers · memory the user gives · DXB arrival guide · ride recommendation · fixed-price services with sandboxed mini-apps · merchant loop with deadlines · lost-item recovery · temporal profile ("I noticed") · Services surface · tasks + Today · demo-grade community (chat, feed, communities, stories; seeded content labelled Demo) · resident bills/Salik/DEWA displays · connectors (planning).

**LATER:** civic RAG with citations · background geofencing · ticket wallet · media memory · Arabic RTL UI · live AR try-on · affiliate marketplace feeds.

**NEVER:** fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · copying the official DubaiNow look · bidding / quotes / negotiation.

## 7. Not code, but needed

| Track | Needed by | Fallback |
|---|---|---|
| Dated screenshot of the contest portal rules | before submission | — |
| One real merchant on video | May final | Labelled sandbox merchant |
| Hosting + domain | submission | Local + tunnel |

**Founder inputs:** Google OAuth (`GOOGLE_OAUTH_CLIENT_ID/SECRET/REDIRECT_URI`, `OAUTH_TOKEN_KEY`) + Gmail API · Microsoft Graph app · Meta app testers (Instagram, WhatsApp) · Slack app · `GOOGLE_MAPS_BROWSER_KEY` · `DATABASE_URL` (Supabase) · app store / desktop signing accounts.

## 8. Run locally

```powershell
cd apps/api; $env:DATABASE_URL=' '; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8030
cd apps/site; npm run dev
```

macOS: `cd apps/api && .venv/bin/python -m uvicorn app.main:app --port 8030`. Original mobile app: `:8030/index.html`. New app: `/`, `/?desktop`, `/?devices`.
