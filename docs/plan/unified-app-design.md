# Unified Dubai-io app — design (23 Oct 2026, v2: Dubai-io-led)

Status: design, founder-steered; awaiting final approval after the white/dark design set. Supersedes `docs/plan/website-rebuild.md` and the decision to keep `apps/web` as the mobile app. Self-contained: a new session should be able to continue from this file alone.

## 0. How we got here (23 Oct, one session)

- Founder rejected the rebuilt marketing site ("super awful") and stopped Swift ("slowing us down").
- Founder wants Dubai-io to *be* an app on the web, like ChatGPT / Gemini / Claude, with a Reddit-style community one switch away (Higgsfield image/video-style switch), connectors, and a visible task queue.
- Founder's own **Mirsal-redesign** (`~/VsCode/Mirsal-redesign`, many iterations) supplies the visual craft and the desktop/iPhone presentations.
- v1 of this doc leaned ~90% Mirsal; founder corrected: **Dubai-io is the product; Mirsal is the craft.** Mirsal's connector workspaces are only a dashboard for tasks/connectors, not the app.
- Founder's reference run (Grok Bot, "why didn't my Puffy job application pay off"): searched 5–7 repos for "puffy", found a notes `.md` about the email, searched Gmail/Outlook, found 12 emails, fanned out a small LLM to read them into minimal JSON summaries, the main model reviewed → advice → drafted the reply in **Outlook** (the account the thread lived in) → proposed a LinkedIn title change, after noticing in `CLAUDE.md` that the founder had recently changed title. This is the assistant behaviour Dubai-io must reach.
- Visual references: `.superpowers/brainstorm/94241-1792742190/content/img/` (GPT Image 2.5 concepts: `concept1–3`, `v2/s1–s9`, **v3 = current reference set: `v3/l01–l10` light desktop/web, `v3/m01–m06` phone (guided by the real `apps/web` screens + `chat.jpg`), `v3/d01` graphite / `v3/d02` true-black dark candidates**), `design/references/chat/chat.jpg` (WhatsApp Chats/Calls), `design/references/chat/grok-bot.jpeg` (Grok Bot task threads), `design/references/claude duet/` (Duet frames), Mirsal `Slides/output_grid/*.jpg`.

## 1. Product: Dubai-io first

A personal assistant for everyday life and work in Dubai (not a visitor/tourist app). Its surfaces, in priority order:

| Surface | What it is | Origin |
|---|---|---|
| **Assistant** (home) | Greeting + composer + briefing strip (direction C). Agentic: investigates across sources, drafts, proposes, asks approval. | Dubai-io (Luna), behaviour from Grok Bot / Dots / Duet |
| **Task threads + Today** | Every task is a thread (Grok Bot style) with live status; Today lanes: Needs you, Running, Scheduled, On list, Paused, Done. | Dubai-io tasks engine |
| **Community** | Reddit-style feed, communities, AI personas (labelled), behind the Assistant ⇄ Community switch. | Dubai-io community |
| **Chats ⇄ Calls** | WhatsApp-style (built 23 Oct in `apps/web`): search/Ask bar, chips, Archived, swipe-archive, Calls with favorites carousel, Favorites panel. | Dubai-io + founder ref |
| **Services** | Providers, fixed-price orders, approval card listing exact shared fields, sandbox merchant. 3.1 thumbnail rows. | Dubai-io |
| **Maps** | Places, user-confirmed pins only, directions handoff (Google Places/static maps exist in backend). | Dubai-io |
| **Me / memory** | "You told me" (editable/forgettable), "I noticed" (hypotheses with Confirm/Edit/Not true/Forget), "You, over time" timeline, Settings. | Dubai-io rule 9 + temporal_note |
| **Onboarding** | Orb wakes up → setup is the chat (area, household, services, connectors). | new |
| **Dashboard** | Tasks + connectors overview, with Mirsal-style workspace views: Weather (Open-Meteo, real), Prayer (Aladhan, real), News (Tavily, real if key), Mail/Calendar later. | Mirsal craft |

**Cases that must survive** (founder, 23 Oct):
1. **Airport arrival guide** — DXB guide that never claims an indoor position, belt, gate or queue the user didn't confirm; "I'm lost" resumes from a confirmed landmark; late-night constraints (Metro stops ~midnight, T2 has no station). Today in `apps/web/arrival.js` / `guide.js`. In the new app: an Assistant flow + task thread + Maps pins of user-confirmed places only.
2. **Lost item in a taxi** — recovery from what the assistant remembers (time, pickup, plate/roof colour if told), prefilled official report + RTA handoff, honest "not recovered" outcome; staged replies are labelled demo; RTA adapter is BLOCKED (no fake send). Today: TAXI-02 commands in `apps/api/app/tasks.py`, C6 in `PLAN.md`. In the new app: a task thread with the staged progress + approval card.

## 2. Assistant behaviour (Grok Bot + ChatGPT Dots + Claude Duet)

Founder: these three are "extremely close" to what Dubai-io should be. Reference summary in `docs/references/personal-assistant-direction.md`.

- **Grok Bot → delegation + task threads + routines.** A request becomes a task thread in the sidebar (icon, title, live one-line status, blue unread dot). Inside: acknowledgement → what it's doing and how long → structured result with source chips → approval card when anything would be shared/sent. Routines = an approved process the user can rerun.
- **ChatGPT Dots → ongoing responsibilities.** "Keeping track" items persist between conversations (bill due, renewal, follow-up) and report progress; activity is reviewable.
- **Claude Duet → briefings + decisions.** The briefing strip / Updates tray shows what changed and which decision is needed; connected-app context informs it; never floods.
- **Investigation loop (the Puffy run):** fan out across every connected source (mail accounts, notes/vault, files/repos, tasks, chats, memory) → small fast model (`FAST_MODEL`) reads each hit into a minimal JSON summary → main model (Luna) reviews with memory context → advice + draft in the *originating* app (Outlook vs Gmail) + proposals → approval card before any send/change. Progress lines in the thread come only from real steps actually run (truth rules).
- Model routing exists: chat = Luna first (agnes fallback); feed personas = agnes first (Luna fallback) — `AI_main` / `fallback_model` / `FEED_*` in `apps/api/.env`.

### 2.1 Feasibility of the founder's Puffy run in Dubai-io

| Step | Doable? | Needs |
|---|---|---|
| Search notes/files/repos for "puffy" | Yes, via connectors | GitHub connector (repos) and a notes/vault connector; a browser app cannot read local folders — local files need a desktop/agent bridge (vault-control style) |
| Search Gmail + Outlook | Yes | Google OAuth Gmail read scope + Microsoft Graph (Outlook) app registration; both new backend slices |
| Small LLM reads each email → JSON | Yes | `FAST_MODEL` fan-out in the backend (exists as config) |
| Main model reviews + advice | Yes | Luna + memory context pack |
| Draft reply in Outlook (the right account) | Yes, with approval | Graph "create draft" (draft only; sending needs the approval card) |
| "You recently changed your title" | Yes | temporal_note-style memory events from connected sources |
| Change LinkedIn title | Suggest only | LinkedIn has no general profile-edit API; Dubai-io drafts the text, user applies it |

## 3. Memory: temporal_note as the engine

The founder's `temporal_note` (`~/VsCode/Claude---Cowork/temporal_note`; Python, Postgres 16 + pgvector, BM25 + vector RRF hybrid search, 36 MCP tools, ~317 tests) becomes the model for Dubai-io's memory — **engine and schema, not the founder's personal data**:

- Port into Dubai-io's Supabase Postgres (`dubaiio` schema): events (+ embedding), entities with `valid_from`/`valid_to`, relationships, threads, patterns, advice entries; memory ops extract / consolidate / conflicts / salience / context pack.
- Feeds: short-term (conversation/task context) and long-term memory, recommendations ("advice due/stale" → Keeping track + briefing, fired by the scheduler — rule 8), profiler ("I noticed").
- Rule 9 holds: everything visible and editable in Me; inferred items are hypotheses with Confirm/Forget; **never infer health, religion, ethnicity, nationality-as-trait, gender, sexuality, politics** (temporal_note's extractor needs this filter); unconfirmed hypotheses only re-rank, with a "Because…" chip.
- Existing Dubai-io pieces to connect: `user_profile.py`, `recommendations.py`, `profile.py` (episodes/overrides), session facts (`area`, `household`, `services`, …).
- Separately: temporal_note can serve as an MCP for the agents building this repo; its plugin launcher is Windows-only (`run.ps1`) — point it at `mcp_server/run.sh` on the Mac.
- **Founder permission (23 Oct): copy/learn freely from temporal_note.**
- **Vault control** (founder's "Claude control" extension UI; same family as temporal_note): indexes code/files, has an LLM summarise and document tasks for later sessions, and mainly **guides and controls what local info agents see and how it's shown**. In Dubai-io this becomes:
  1. **"What Dubai-io can see" control page** (Me/Settings): every source (connectors, notes/vault, files, memory) with what is indexed, the summaries made from it, and per-source on/off + scope. Rule 9 as a real panel; bounds the investigation loop.
  2. **Persistent task write-ups:** when a task thread finishes, a short summary (what was done, sources, outcome) is stored as a memory event so later chats and the briefing build on it — same engine as §3.

## 4. Shell, presentations, look

- **One React codebase in `apps/site`** (Next.js 16 / React 19); replaces the marketing site and, after parity, `apps/web`. iOS/Swift stopped (`docs/plan/ios-upgrade.md` = history).
- **Three presentations of the same screens** (from Mirsal): **Website** (real; desktop >820 px, phone ≤820 px), **Desktop app** (`?desktop`, Mirsal `MacDesktop` window + menu bar + Dock), **iPhone view** (`?device`, Mirsal iPhone frame + Dynamic Island). Plain URL is the deliverable; demo modes use the same live API.
- **Navigation (desktop):** slim rail ≤6 items — Assistant, Chats, Services, Maps, Dashboard, Me — + task-thread sidebar + main; Assistant ⇄ Community pill top-center. **Phone:** tabs Home, Chat, Services, Feed + Ask; Dynamic Island = live task.
- **Palette (founder, 23 Oct): more white, accent toward grey.** Accent `#357F92` (muted steel-teal; replaces aqua `#0A9CC2`), backgrounds `#FFFFFF`, secondary `#F6F7F8`, neutral untinted glass. **Light mode is not flat (founder, 23 Oct):** a soft Gemini-style gradient haze behind the home greeting/composer and onboarding — steel-teal `#357F92` at ~8% blending into a faint warm sand/lavender at ~5% on white, fading to pure white below the fold; never behind dense content (lists, threads, forms). **Dark mode = Graphite** (`#141618` / `#1B1E21` / `#202428`, accent `#6FA9B8`) — Claude's call since the founder didn't pick; a user on/off toggle plus system setting; true black stays a possible later option.
- Copy from Mirsal: tokens (recolored), `ui/` primitives, shell, `MacDesktop`, mobile shell + frame + Dynamic Island, Updates tray, weather view. Not ported: stocks, flights, files, history, Mirsal `server/`, AI action layer, e-sign, voice, Postgres photos.
- Root UI rules: no shadows, plain AI text, tinted user box, white rounded action boxes.

## 5. Decisions (founder, 23 Oct)

1. One React app; three presentations; Mirsal = craft, Dubai-io = product.
2. Home = direction C (composer + slim briefing strip).
3. Assistant ⇄ Community switch, one view at a time.
4. Connectors drive which dashboard workspaces appear.
5. Notifications = task queue (task threads + Updates tray + Dynamic Island, same data).
6. Fresh session: 3 labelled demo tasks (AC repair, laundry, DEWA) + composer creates real tasks.
7. This design supersedes the 22 Oct `PLAN.md` locks on Home, onboarding and Reading/connector scope (recorded in `PLAN.md`). Worker/cron stays out.
8. Approved deps: `lucide-react`, Playwright, Vitest.
9. Palette: white + `#357F92`; dark mode from the white design.
10. Airport arrival guide and lost-in-taxi recovery survive.
11. Behaviour target: Grok Bot + Dots + Duet; memory engine modelled on temporal_note.

## 6. Calls made by Claude (founder to check)

- First visit lands in the app (chatgpt.com style); About page carries the pitch.
- Onboarding: orb wakes up → setup is the chat.
- Next.js kept; Mirsal mounts as one client-only app.
- Connectors without a backend show "Not available yet" with a reason; never in the nav until really connected.
- Mic hidden until voice is real.
- Desktop rail order as in §4.

## 7. Data mapping (what is real today)

| Surface | Source | State |
|---|---|---|
| Composer | `POST /api/luna/turn` | real (503 → honest "Assistant unavailable") |
| Task threads / Today / tray / island | `/api/today`, `/api/tasks*`, `/api/tasks/{id}/activity`, `/api/messages` | real; refresh on read (poll while visible) |
| Chats/Calls/archive/favorites | `/api/chats*`, `/api/calls`, `/api/contacts`; favorites device-local | real + labelled demo |
| Community | `/api/feed`, `/api/communities*`, `/api/posts*` (replies queued in background) | seeded demo + real user content |
| Services | `/api/catalog`, actions/orders | demo catalog, sandbox merchant |
| Maps | Google Places / static maps (`google_maps.py`) | real with key |
| Weather / Prayer / News | Open-Meteo (browser) / `/api/prayer-times` / `/api/reading` | real / real / real if key |
| Memory | session facts, profile episodes/overrides, recommendations | real; temporal_note engine = new slice |
| Connectors | `/api/auth/*` (Google identity only) | Gmail/Outlook/Calendar = new slice |
| Airport guide / taxi recovery | `apps/web` arrival/guide, TAXI-02 commands | real logic; RTA adapter BLOCKED |

## 8. Pending founder picks (design set in progress)

- Dark mode: Graphite chosen by Claude (founder may switch to true black).
- Any further visual options shown in the brainstorm gallery.

## 9. Build order

1. Mirsal foundation in `apps/site` (tokens recolored white/`#357F92`, primitives, shell, presentations, client-only mount).
2. Assistant home + switch + onboarding + task threads/tray/island wired to real tasks; 3 demo tasks; composer → real tasks.
3. Community, Chats ⇄ Calls, Services, Maps — ported from `apps/web` behaviour.
4. Airport guide + lost-in-taxi as assistant flows/task threads.
5. Dashboard workspaces: Weather, Prayer, News; connector gallery.
6. Memory engine (temporal_note port) + Me timeline + "I noticed".
7. Investigation loop: connectors (Gmail/Outlook/Calendar, vault/notes) + small-model fan-out.
8. Parity check, then retire `apps/web` (separate go-ahead).

Each slice: build green, API tests green, Playwright happy/failure path, screenshots at 1440 / 390 / `?device` / `?desktop`, light + dark, main-session review before merge.
