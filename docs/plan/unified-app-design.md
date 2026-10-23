# Unified Dubai-io app — design (locked 23 Oct 2026)

Status: design for founder approval. Supersedes `docs/plan/website-rebuild.md` (landing-page brief) and the decision to keep `apps/web` as the mobile app. Visual references: `.superpowers/brainstorm/*/content/img/v2/s1–s9.jpg` (GPT Image 2.5 concepts, illustrative data), `design/references/chat/chat.jpg` (WhatsApp-style Chats/Calls), `design/references/chat/grok-bot.jpeg` (Grok Bot task threads), and the founder's own Mirsal-redesign project (`~/VsCode/Mirsal-redesign`, `Slides/output_grid/*.jpg`).

## 1. Intent

The founder rejected the rebuilt marketing site ("super awful") and wants Dubai-io to *be* an app on the web, like ChatGPT / Gemini / Claude: an assistant you talk to, with a Reddit-style community one switch away, connectors that bring your apps in, and a visible queue of the tasks it is working on. The same app is shown three ways — a real website, a desktop-app demo, and an iPhone demo — the way Mirsal-redesign already does after many rounds of visual and logic work. Mirsal is the source; Dubai-io evolves it and keeps its minimal ease of use and its truth rules.

## 2. Decisions (founder, 23 Oct)

1. **One React codebase** in `apps/site` (Next.js 16 / React 19) replaces both the marketing site and `apps/web`. `apps/web` stays running as the feature reference until the React app reaches parity, then retires. iOS/Swift is stopped.
2. **Three presentations of the same screens** (copied from Mirsal):
   - **Website** — the real product in the browser, connected to `apps/api`. Desktop layout above 820 px, phone layout at ≤820 px.
   - **Desktop app** — the same app inside Mirsal's macOS window (`MacDesktop`: menu bar, draggable window, Dock, wallpaper). Demo presentation.
   - **iPhone view** — the phone layout inside Mirsal's iPhone 17 frame with the Dynamic Island (`?device`). Demo presentation.
3. **Copy Mirsal's shell, design system, workspaces and Updates tray**; evolve rather than redesign. Recolor Mirsal's blue to Dubai-io cyan (`#0A9CC2` family).
4. **Home = direction C (hybrid):** big greeting + composer ("Ask Dubai-io anything", + / connectors / mic) with a slim strip of briefing cards under it (Needs you · Changed · Due). Reference: s1.
5. **Assistant | Community switch** at the top center, Higgsfield-style (one view at a time, not split). Community = Reddit-style feed with a "Communities to join" rail. Reference: s3.
6. **Apps come from connectors, not hard-coding.** A workspace appears in the nav when its connector is connected; built-in Dubai workspaces are always present. Connectors gallery like ChatGPT/Claude. Reference: s6.
7. **Notifications are the task queue.** Every in-flight task is visible:
   - **Task threads (Grok Bot style):** the Chats sidebar lists tasks as conversations — icon, title, live one-line status, blue unread dot. Opening one shows staged assistant messages (ack → what it's doing and how long → structured result with source chips → approval card when anything would be shared). Reference: s2, grok-bot.jpeg.
   - **Updates tray (Mirsal):** at-a-glance overview at the top of Chats on desktop; Updates sheet + Dynamic Island + task "stories" row on the phone. Reference: s8.
   - Both read the same real task data.
8. **Mobile parity** keeps everything approved today in `apps/web`: WhatsApp-style Chats ⇄ Calls with Favorites and archive, slide-in panels (threads, posts, Settings), services 3.1 grid, feed with AI-persona replies.
9. **First workspaces (v1):** Assistant, Chats (people + task threads), Community, Services, **Weather**, **Prayer + News**. Later: Mail and Calendar (need Google scopes), Bills/Money (demo until a real provider).

10. **Task queue on a fresh session:** seed 3 labelled demo tasks (AC repair, laundry pickup, DEWA bill; `Demo` pill, dismissible) AND make the composer create real tasks from requests (backend slice: Luna turn → `POST /api/tasks` / `from-action`). Thread stages render from the real activity log; where the log has no entry for a stage, that stage is not shown.
11. **This design supersedes the 22 Oct locks in `PLAN.md`** on Home (carousel/Today handle → direction C), onboarding (Wi-Fi/gradient → orb + chat setup), and scope (News/Reading in; Connectors gallery in, with Gmail/Calendar shown as "not available yet" until built). Worker/cron stays out.
12. **New dependencies approved:** `lucide-react` (icons), Playwright (browser tests), Vitest (unit tests).

## 3. Calls made by Claude (founder to check)

- **First visit lands in the app, not a marketing page** (chatgpt.com style): onboarding plays once, then the composer. A short "About" page stays reachable from the footer/menu for people who want the pitch. (Founder did not answer this; flagged.)
- **Onboarding animation = "Orb wakes up" then "setup is the chat"**: the cyan glass orb breathes, the greeting types, the orb stretches into the composer, then the assistant asks area → household → services → connectors as chat bubbles with tap-chips (saved via `PUT /api/session/memory/{area,household,services}`). Reduce Motion = static frames. Reference: s9.
- **Keep Next.js** rather than Mirsal's Vite. The Mirsal app mounts as one client component (`dynamic(..., { ssr: false })`) because nearly every Mirsal module touches `window`/`localStorage` at import.
- **Presentation switch:** `?device` (iPhone frame) as in Mirsal, `?desktop` (macOS window); plain URL = website.
- **Stocks, flights, files, history workspaces are not ported** (no Dubai-io data); their code can be copied later if wanted.
- **Connectors with no backend** appear in the gallery with a visible "Not available yet" blocker and reason (root rule: blocker, never a fake connect); their workspaces never appear in the nav until a real connection exists.
- **Mic/voice hidden in v1** (no real voice backend; a dead control would break the truth rules).
- **Not ported from Mirsal:** `server/`, the AI action layer (`ai/runAction`), `esign`, `voice`, Postgres photos. Everything calls `apps/api` instead.
- **Plain URL is the deliverable**; `?desktop` / `?device` run the same live API. Missing key/server → honest unavailable states (e.g. `luna/turn` 503 shows "Assistant unavailable"), never fixtures pretending to be live.
- **Current `apps/site` routes:** the landing/funnel/demo pages are retired; their pitch copy moves to the About page; the API rewrite stays.

## 4. Data mapping (what is real)

| Surface | Source | State |
|---|---|---|
| Composer / assistant | `POST /api/luna/turn` (existing Luna chat) | real |
| Task threads, briefing strip, Updates tray, Dynamic Island | `GET /api/today` (lanes: needs_you, running, scheduled, on_list, paused, completed), `GET /api/tasks/{id}`, `GET /api/tasks/{id}/activity`, `GET /api/messages` | real; refreshes on read (no background worker) — poll while visible |
| Thread progress lines | task activity log only | real; never invented ("Checking your inbox" appears only if a connector actually ran) |
| Progress rings | only where an event gives progress | otherwise an indeterminate state, never a fake % |
| People chats, Calls, Favorites, archive | `/api/chats*`, `/api/calls`, `/api/contacts` | real + labelled demo personas |
| Community | `/api/feed`, `/api/communities*`, `/api/posts*` | seeded = Demo; user content real; replies queued |
| Services | `/api/catalog`, actions/orders | demo catalog; sandbox merchant |
| Weather | Open-Meteo from the browser (Mirsal's `getWeather`, 1 h cache) | real, no key |
| Prayer | `GET /api/prayer-times` | real |
| News | `/api/reading` (Tavily) | real if key set, else honest "unavailable" |
| Connectors | `/api/auth/connections`, `/{provider}/start` | Google identity only today; Gmail/Calendar scopes + fetch code are a later backend slice |
| Onboarding facts | `PUT /api/session/memory/*` | real |

Truth rules unchanged (root `CLAUDE.md`): status words only from provider evidence, provenance + `Demo data` pills, approval card listing exact fields before any share/send, no fake calls, no official branding.

## 5. Goals / non-goals / anti-goals

- **Goals:** feels like a first-party 2026 assistant app; one codebase for every device; the task queue always visible; minimal (≤6 nav items, one primary action per screen); everything shown is real or labelled demo.
- **Non-goals (this design):** native iOS/Android builds, real accounts (anonymous session stays), Gmail/Calendar reading, bill payment, background worker/scheduler, websockets.
- **Anti-goals (failure even if it works):** a marketing site with no app; a Mirsal clone that ignores Dubai-io's truth rules (fake "Flight found", fake progress); clutter that loses the ChatGPT-like calm; a third parallel codebase.

## 6. Build order (for the plan)

1. Port Mirsal foundation into `apps/site`: tokens (cyan), `ui/` primitives, shell (nav rail + sidebar + main), `MacDesktop`, mobile shell + `?device` frame + Dynamic Island, client-only mount.
2. Assistant home (direction C) + Assistant|Community switch + onboarding (orb → chat setup).
3. Task threads + Updates tray + Dynamic Island wired to `/api/today` and task activity.
4. Community (feed, post panel, AI replies polling) — port from `apps/web`.
5. Chats ⇄ Calls, Favorites, archive, Settings — port from `apps/web`.
6. Workspaces: Weather, Prayer + News, Services (3.1 grid), Connectors gallery.
7. Parity check vs `apps/web`, then retire it (separate founder go-ahead).

Each slice: `npm run build` green, API tests green, screenshots at 1440 desktop / 390 phone / `?device` / `?desktop`, light + dark, reviewed by the main session before merge.

## 7. Left to the builder

Component structure inside the port, CSS module organisation, polling intervals (suggest 15–30 s while visible), animation timing, exact copy (within the truth rules), how Mirsal's seeded data is replaced endpoint by endpoint.
