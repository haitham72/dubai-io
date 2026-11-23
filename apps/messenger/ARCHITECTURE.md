# Architecture — Messenger agents

How the app's AI works, where every piece of data comes from, and the contracts of the outside systems it talks to.
Run instructions: [run.md](run.md) · app overview and deploy: [README.md](README.md) · agents service internals:
[agents/README.md](agents/README.md) · voice evaluation: [agents/eval/REPORT.md](agents/eval/REPORT.md).

**Principles**

- **Two parts.** The React app (+ `api/*.ts` Vercel functions) and a Python agents service (`agents/`, FastAPI + Redis).
  The browser reaches the service only through `src/api.ts` at `/agents/*`; with the service off the app still works
  on its own fallbacks.
- **Every outside system is a connector**: an MCP client (or HTTP/OAuth) built and tested against a mock server, and
  switched on by a URL or key. Until then it serves demo data that is labelled "demo" in the UI; it never invents
  real-looking records. `GET /agents/connectors` lists each one, its state and what it waits for.
- **Paid calls are opt-in**: only with `AGENTS_LIVE=1`, priced before each call and stopped at `AGENTS_BUDGET_USD`
  (default $1).

## 1. Where the agent depth is

| Signal of depth | Where it is | Proof |
|---|---|---|
| Streaming voice agent that acts mid-sentence, with a closed action list (14), probability gates, a ~30 ms fast path for nameless in-app commands, and dangling-verb carry ("Open." … "my last chat") | `agents/messenger_agents/engine.py`, `deciders.py`, `session.py` | `agents/eval/REPORT.md` |
| Safety by construction: exact-recipient guard, undo window for sends, confirm for paid actions, corrections withdraw actions | `contacts.py`, `engine.py` | eval: 0 wrong recipients, 0 unconfirmed paid actions; `tests/test_engine.py` |
| Measured before tuned: baseline 80.3 % → held-out first run 83.3 % (1 wrong recipient, found and fixed) → 100 % / 0 | `agents/eval/` (113 dev + 32 holdout items; original first-run figures remain historical) | `tests/test_eval_gate.py` (regression gate) |
| Deep research: plan → parallel search → full pages → cited brief → claim verification → cache; scheduled watch topics | `research.py`, `watch.py`, `watchlist.json` | `tests/test_research.py` |
| Chat skills reading the last 10 messages: fact check with sources (text or photos: the vision model reads the photo, says what to search, then judges with the photo and the sources), stickers, three image choices, a multi-step trip plan (leave optimiser → HR connector → flights → FX → group → calendar) | `skills/` (`factcheck`, `image_ideas`, `stickers`, `planner`, `nadi`, `look`; re-exported by `chat_skills.py`), `src/chats/skills.ts` | `tests/test_chat_skills.py` |
| MCP connectors with written contracts, a real Streamable-HTTP client (JSON and SSE replies, sessions, tool errors) | `mcp_client.py`, `diwan.py`, `sticker_builder.py`, `Nadi` in `skills/nadi.py` | `tests/test_diwan_builder.py` (mock MCP servers) |
| Spend cap priced before every paid call, persisted ledger; per-turn traces with decisions and probabilities | `spend.py`, `trace.py` | `tests/test_spend.py`, `GET /agents/trace` |
| Prompt-injection fencing of chat and web text | `research.py` (`DATA_RULE`), `skills/base.py` (`CHAT_RULE`) | `tests/test_research.py` |
| Clean AI Detection: Apps screen + `@messenger clean` chat skill on one single-GPU FIFO job backend with server-owned stages (checking → resizing → cleaning → faces → presenting), quality counters and a key-gated OpenAI provenance check | `agents/messenger_agents/ai_cleaner.py`, `ai_cleaner_engine.py`, `src/screens/ai-cleaner/`, `src/chats/skills.ts` | `tests/test_ai_cleaner.py` (10, socket-free) |
| Graceful degradation: the app runs with the service off, and the service runs with no keys | every `src/api.ts` caller has a fallback | browser checks |

Run it all: `npm run agents:test` (169 passed, 1 skipped without Redis; offline) · `npm run agents:eval` · `curl localhost:8787/agents/connectors`.

---

## 2. Data map — where every piece of data lives (demo) and where it comes from (live)

| Feature | Demo data lives in | Live source | Connector / env | State today |
|---|---|---|---|---|
| Voice commands | contacts: `src/chats/data.ts` (incl. 3 near-namesakes); eval: `agents/eval/*.jsonl` | OpenAI streaming transcription + Decisions API | `OPENAI_API_KEY`, `AGENTS_LIVE=1` | **built**; recent traces show model connection failures; current cloud connectivity and model accuracy remain unverified |
| @messenger fact check (text and photos) | `DEMO_FACTS` (2 seeded claims) and `DEMO_PHOTO_FACTS` (the seeded Tegalalang photo) in `agents/messenger_agents/skills/factcheck.py` | Tavily search + OpenAI model; photos read by the vision model (`AGENTS_VISION_MODEL`, default the research model, detail "low"), sources cited | `TVLY_API_KEY`, `OPENAI_API_KEY`, `AGENTS_LIVE=1`; fallback `/api/chat` (text only, says the photo wasn't checked) | **built** |
| @messenger trip plan | rules in `skills/planner.py` (`PLACES`, `UAE_HOLIDAYS`, `FX_FALLBACK`); seeded Egypt chat in `src/chats/data.ts` | flights: existing `/api/flights` (SerpAPI); FX: open.er-api.com (free) | `SERPAPI_KEY` | **built** |
| HR leave ("Nadi") | memory store key `nadi:<user>` (30-day balance) | **Nadi MCP** — tools `file_leave`, `list_leave` (§4.3) | `NADI_MCP_URL`, `NADI_MCP_TOKEN` | **connector open**, waiting for URL |
| UAE events ("Diwan") | `agents/messenger_agents/diwan_demo.json` + 3 pictures in `public/diwan/rashid-bin-saeed-anniversary/` | **Diwan MCP** — tool `upcoming_events` (§4.1) | `DIWAN_MCP_URL`, `DIWAN_MCP_TOKEN` | **connector open**, waiting for URL |
| Event pictures | `public/diwan/<image_folder>/01–03.jpg` — the 2026 commemoration posts (two 4:5, one 9:16) in a swipe carousel; the picture showing is the one shared | **Supabase Storage**, public bucket `diwan`, folder per event, **max 3 images** (§4.2) | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `DIWAN_BUCKET` | **connector open**, waiting for keys + folder |
| Research | 6 hand-written reports in `src/screens/research/data.ts` (labelled Demo); offline briefs from `FakeLLM`/`FakeSearch` (labelled Demo); your new reports kept in this browser | Tavily + OpenAI deep research; failure shows Try again, never canned findings | `TVLY_API_KEY`, `OPENAI_API_KEY`, `AGENTS_LIVE=1` | **built**; weekly topics in `agents/watchlist.json` |
| Weekly watch topics | `agents/watchlist.json` (2 topics); results in Redis `watch:<id>` and `agents/.data/watch/` | as research | as research | **done** |
| Stickers (packs) | **The Messenger Builder Library, read in place** (`MESSENGER_BUILDER_LIBRARY`, default the sibling checkout's `messenger/out/library`: approved packs only, `.webm` animated first, re-read when `library.json` changes); then `public/stickers/<pack>/` — 4 demo packs × 8 + `index.json` | **Messenger Builder MCP** — tool `create_sticker_pack` → 3 options (§4.4); exported packs folder via `STICKERS_DIR` | `MESSENGER_BUILDER_MCP_URL`, `MESSENGER_BUILDER_MCP_TOKEN`, `STICKERS_DIR` | **built**: media panel Stickers tab, Builder Library live; Builder MCP waiting for URL |
| Animated stickers | the Builder Library's `.webm` stickers (68 across its approved packs on this machine) | Messenger Builder | `MESSENGER_BUILDER_LIBRARY` | **live** (plays in the panel and in chat) |
| "More from this picture" | `diwan_demo.json` → `more` (3 versions of `03.jpg` in `public/diwan/<folder>/03/03-01…03.jpg`) | **Diwan MCP** — tool `more_from_image` (§4.5); else the picture's Supabase sub-folder | as Diwan / Supabase | **connector open** (mock-server tests), waiting for Diwan |
| GIFs | none without a key (panel says "not connected") | GIPHY search/trending | `GIPHY_API_KEY` → `GET /agents/gifs` | **live** when the key is set |
| Emoji | 9 categories, ~384 curated in `src/chats/data.ts`, system emoji font | — | — | **built** (media panel Emoji tab: search, recents, category strip). Noto Animated set not downloaded yet |
| Mail | fake inbox `src/screens/mail/data.ts` | Gmail API, OAuth (read/search; send only from the compose button) | `agents/.secrets/gmail_client.json`, sign-in at `/agents/mail/oauth/start` | **built, OAuth ready**, waiting for the Gmail test account |
| Images / video | fake jobs + 3 Kling clips in `media/videos/`; 3 demo pictures for "@messenger create image" in `src/chats/data.ts` | Higgs (Nano Banana 2, Kling 3.0) | `HF_CREDENTIALS`, `HIGGS_IMAGE_ENDPOINT`, `MESSENGER_FAKE_*=0` | fakes by default (credits) |
| Memory | in-process when Redis is off | Redis (`docker compose up redis`) | `REDIS_URL` | **built** |
| AI image cleaning | none — jobs live under `agents/.data/ai-cleaner/<job_id>/` (git-ignored) | local GPU: CUDA torch + Pillow in the sibling env, `remove-ai-watermarks==0.45.1`; provenance check via the OpenAI key | `OPENAI_API_KEY` (verify only; no new keys) | **built on `app-ai-removal`**; GPU run and verify call unverified |

---

## 3. Connectors — how they plug in

```
browser ──/agents/* (Vite proxy)──▶ agents service (FastAPI)
                                      ├─ McpClient ──▶ Diwan MCP            upcoming_events
                                      ├─ McpClient ──▶ Messenger Builder MCP   create_sticker_pack
                                      ├─ McpClient ──▶ Nadi MCP             file_leave · list_leave
                                      ├─ Supabase Storage (REST list + public URLs, max 3 per event)
                                      ├─ GIPHY (HTTP) · Gmail (OAuth) · OpenAI · Tavily
                                      ├─ local GPU engine (`ai_cleaner`, not MCP — CUDA torch + Pillow)
                                      └─ Redis (memory, cache, spend ledger, traces)
```

- **Client:** `agents/messenger_agents/mcp_client.py` — Streamable HTTP, JSON-RPC 2.0: `initialize` →
  `notifications/initialized` → `tools/call`; reads JSON or SSE replies; keeps `Mcp-Session-Id`; sends
  `Authorization: Bearer <TOKEN>` when set; `isError` results raise `McpError`. A tool result is read from
  `structuredContent`, else the first text block parsed as JSON.
- **Turning one on:** set its URL (and token) in `.env`, restart `npm run agents`, check `GET /agents/connectors`
  shows `"state": "live"`. Nothing else changes: the same routes now serve live data.
- **When a connector fails** the route answers 502 with the connector's name and the app keeps its demo/fallback
  path; the failure lands in the trace.

## 4. Connector contracts (what each outside project exposes)

### 4.1 Diwan MCP — `upcoming_events`

The whole events backend lives in the separate **Diwan** project (formerly "Diwan Hamdan"). Messenger only asks for
events from yesterday to 7 days ahead and shows them as notifications (Messenger Updates; Dynamic Island on phones).

```jsonc
// tools/call  name: "upcoming_events"
// arguments
{ "from": "2026-10-07", "days": 8 }
// result (structuredContent, or a text block with this JSON)
{ "events": [ {
    "id": "rashid-bin-saeed-anniversary",          // stable id (used to avoid duplicate notifications)
    "title": "Sheikh Rashid bin Saeed Al Maktoum death anniversary",
    "title_ar": "ذكرى رحيل الشيخ راشد بن سعيد آل مكتوم",
    "kind": "commemoration",                        // commemoration | national | religious | royal | other
    "date": "2026-10-07",                           // or annual: "month": 10, "day": 7
    "summary": "One sentence.",
    "image_folder": "rashid-bin-saeed-anniversary"  // Supabase Storage folder (§4.2)
} ] }
```

Messenger filters to `-1 ≤ days from today < 7`, labels "Yesterday / Today / Tomorrow / In N days", caches for an hour.
Code: `agents/messenger_agents/diwan.py`; route `GET /agents/diwan/events`; UI `src/updates/diwan.ts`,
`src/updates/details/EventDetail.tsx`.

### 4.2 Supabase Storage — event pictures

- Bucket `diwan` (public read), one folder per event: `diwan/<image_folder>/01.jpg … 03.jpg`.
- Messenger lists the folder (`POST /storage/v1/object/list/diwan`, anon key) and uses **only the first 3** images
  (`.jpg .jpeg .png .webp`, sorted by name), via public URLs. Nothing else is read from Supabase.
- Demo stand-in: `public/diwan/rashid-bin-saeed-anniversary/01–03.jpg` (the 2026 commemoration posts, same folder layout as the
  bucket, so uploading that folder to Supabase is the whole switch). Shapes differ (4:5 posts, a 9:16 story); each keeps its
  ratio and the person taps the one **Use in chat** shares.

### 4.3 Nadi MCP — leave requests

```jsonc
// file_leave  arguments
{ "user": "demo", "type": "annual", "from": "2027-01-01", "to": "2027-01-12", "leaveDays": 7, "note": "Trip to Egypt" }
// result
{ "ref": "NADI-2027-1401", "status": "Pending manager approval", "balanceBefore": 30, "balanceAfter": 23 }
// list_leave  arguments { "user": "demo" }  →  { "requests": [ …file_leave results… ] }
```

### 4.4 Messenger Builder MCP — new sticker packs (three options)

The separate **messenger-builder** repo generates sticker packs. Messenger asks for one pack and gets **3 options**; the
person swipes between them and keeps the best.

```jsonc
// tools/call  name: "create_sticker_pack"
// arguments
{ "prompt": "create sticker of this", "context": ["…last 10 chat messages…"], "options": 3, "formats": ["webm", "webp"] }
// result
{ "options": [ {
    "id": "nile-days-v2", "title": "Nile Days",
    "stickers": [ { "url": "https://…/01.webm", "format": "webm", "emoji": "🐫" } ]   // 6–12 per option
} ] }
```

Sticker formats (copy Telegram): **static** WebP/PNG, 512 px on the long side, transparent, ≤ 512 KB;
**animated/video** WebM VP9 with alpha, 512 px long side, ≤ 3 s, ≤ 30 fps, no audio, ≤ 256 KB, loops.
(Telegram's Lottie `.tgs` is out of scope: it needs a player dependency.)

Exported packs can also land as folders under `STICKERS_DIR` (one folder per pack, optional `pack.json`
`{ "title", "tags": [] }`); they appear in the picker without code changes.
Code: `agents/messenger_agents/sticker_builder.py`; route `POST /agents/stickers/generate` (demo returns 3 local packs,
best match to the chat first).

### 4.5 Diwan MCP — `more_from_image` ("More from this picture")

Diwan keeps several versions of some pictures. Messenger never makes pictures: it asks Diwan for the ones it already has.

```jsonc
// tools/call  name: "more_from_image"
// arguments — `image` is the picture's file name only (no folders; Messenger rejects anything else)
{ "event_id": "rashid-bin-saeed-anniversary", "image": "03.jpg", "count": 3 }
// result
{ "images": [ { "url": "https://…/03/03-01.jpg", "width": 768, "height": 1363 } ] }   // 0–6; [] = nothing more
```

- Which pictures have more: `upcoming_events` may list them per event as `"more_from": ["03.jpg"]`; with Supabase, a
  sub-folder named after the picture (`diwan/<folder>/03/`) means the same. Messenger adds `more: [urls]` to each event so
  the button only shows where there is something.
- Storage naming (the events team's folder convention): versions of `<stem>.jpg` are `<stem>/<stem>-01.jpg …`.
- Order: Diwan MCP → Supabase sub-folder → demo (`more` in `diwan_demo.json`). Cached an hour; every call traced
  (`kind: diwan, tool: more_from_image`, returned count, or the error).
- Route `GET /agents/diwan/more?event=&image=` → 400 bad name · 404 not this event's picture · 502 Diwan down.
- UI (`src/updates/details/EventPictures.tsx`, used by the Updates detail, the island and the phone story card):
  each picture has a heart (favourites, this browser) and, where Diwan has more, **Generate more** — a spinner while
  Messenger asks Diwan, then the versions nest under that picture: a count on the picture and a strip of thumbnails
  (original first). Picking one makes it the picture's main image, which is what **Use in chat** shares.
  Desktop: pictures left (as tall as the tray allows, neighbours peek in dimmed), versions beside the picture, text
  right. Phone: the event is a story (its picture is the circle), the pictures fill the card, versions below.
- Tests: `tests/test_diwan_builder.py` (mock Diwan MCP with both tools, Supabase sub-folder, bad names, route codes).

## 5. Going live — what each connector needs

| Connector | Set | Unlocks |
|---|---|---|
| Diwan MCP | `DIWAN_MCP_URL` (+ `DIWAN_MCP_TOKEN`); Diwan exposes `upcoming_events` (§4.1) and `more_from_image` (§4.5) | live events and picture versions |
| Supabase Storage | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `DIWAN_BUCKET`; upload `public/diwan/<folder>/` as is | live event pictures |
| Messenger Builder MCP | `MESSENGER_BUILDER_MCP_URL` (+ token) exposing `create_sticker_pack` (§4.4) | generated sticker packs |
| Animated stickers | `.webm` files (spec in §4.4) in `public/stickers/<pack>/` or `STICKERS_DIR` | animated stickers |
| GIPHY | `GIPHY_API_KEY` | GIFs |
| Gmail | `agents/.secrets/gmail_client.json` + sign-in at `/agents/mail/oauth/start` | real inbox |
| Nadi MCP | `NADI_MCP_URL` (+ token) with `file_leave` / `list_leave` (§4.3) | real leave filing |
| OpenAI + Tavily | `OPENAI_API_KEY`, `TVLY_API_KEY`, and `AGENTS_LIVE=1` | live voice decisions, research, fact checks |
| Local GPU engine | sibling env with CUDA torch + Pillow (or several-GB pip install into `agents/.venv`), ~6 GiB free VRAM; `OPENAI_API_KEY` unlocks verify | cleaned images + provenance verdicts |

Earlier live probes measured realtime transcription, voice fast-path events (25-33 ms), Decisions responses
(220-550 ms), research and fact checks. These are historical observations, not current readiness checks. Recent
voice traces show model connection failures and rules fallback. Current cloud connectivity, model accuracy and
transcription quality after the resampler fix remain unverified. Obtain owner approval before a paid live run and
estimate its cost from the current corpus. See [agents/eval/REPORT.md](agents/eval/REPORT.md).

## 6. Hosting

The app and `api/` deploy to Vercel as today. The agents service needs a host that keeps WebSockets open and runs
scheduled jobs, which Vercel functions do not: run its Docker image (`agents/Dockerfile`, `agents/docker-compose.yml`) on a
small container host with managed Redis, and point `/agents/*` at it. Supabase provides storage (event pictures) and,
later, Postgres; `agents/messenger_agents/store.py` is the only storage seam.

## 7. Current voice and media behavior (2026-10-08)

### Current verification

- Offline checks: **169 passed, 1 Redis test skipped**; voice dev **113/113**, holdout **32/32**; typecheck and Vite build pass.
- Voice has **14 actions**, including a meeting draft separate from paid trip planning. Sends wait for final speech and the undo window; calendar drafts require review/save.
- Streaming supports up to **120 seconds of active speech**; reply dictation ends after **4 seconds of quiet**, other commands after **1.4 seconds**. No speech times out after 15 seconds; the batch fallback retains its original limits.
- Current cloud decision connectivity and the latest audio/UI behavior are **not live-verified**. Earlier successful probes do not establish current availability; recent traces included model connection failures.
- Local models and a Cloud/Local setting are deferred. No local adapter was added.
- The 2026-10-08 figures above predate the `app-ai-removal` cleaner work (`998aef4`, `80ec042`). A socket-free `tests/test_ai_cleaner.py` (10 tests, passing) covers the cleaner backend and sits outside the voice figures.

A browser tab has a stable `sid`; each utterance uses one WebSocket. The service preserves pending clarification,
dangling verbs, the last contact and its proposal across turns and contact-list rebuilds. Contacts arrive with the
last-interacted chat first, rather than the last group in the seeded message array.

The classifier receives the whole available utterance plus the clause to decide. Early answers are discarded if
the transcript revision changed during the request (`stale: true` in the trace). Classifier requests use a 3-second
timeout without SDK retries; error notes contain exception types and actual elapsed time, not exception text.
Dictation hold is sent as soon as partials identify a reply, independently of classifier latency. End-of-speech
cancels and awaits early work before classifying the frozen final snapshot. The early-decision cap never blocks
the final pass. Traces retain `clausePlan`, decisions, actions and `dictationHold`.

Streaming and final routing share the bounded command parser. `plan for it` after a meeting proposal and
`then make a plan for this event` produce `plan_meeting`, not `plan_trip`. Proposal text is tied to its recipient;
Sara clarification retains her message and following plan without replaying the earlier Arif message/draft.
Known dates/venues fill the review card; unsupported or missing values stay blank. Save creates a local calendar
entry only, never an invitation. See `meeting.py`, `tests/test_meeting.py` and `src/voice/CommandCard.tsx`.

Voice uses no full-screen backdrop. Event pictures and shared chat photos open the shared full-size viewer.
`open the last message` scrolls to/highlights the latest received message and opens its photo, including when the
same chat is already selected. Diwan's bundled six pictures are three primary images plus three nested versions.

Final recovery depends on the available transcript: it cannot reconstruct audio that transcription never captured.
The parser is not a general semantic planner; ordinary/quoted planning words are preserved under its bounded rules.
