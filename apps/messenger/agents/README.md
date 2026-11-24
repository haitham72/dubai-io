# Messenger agents service

Phase-two proof of concept: the app's AI becomes real, one capability at a time, without changing the Vercel deploy.
Python (FastAPI) in Docker with Redis, **local first**; the browser reaches it only through `src/api.ts` at `/agents/*`
(proxied by the Vite dev server). With the service off, the demo behaves exactly as before.

| Capability | What it does | Live provider | Offline |
|---|---|---|---|
| **Voice commands** | Acts on speech *while the person is still speaking*: opens screens and chats ("my last chat" too) mid-sentence; reads messages and updates aloud; opens a filled-in email; plans a trip after Confirm; short nameless commands take a ~30 ms fast path without the model; sends to a person only after an undo window; paid actions only after Confirm; uncertain recipients and intents ask one short question | OpenAI streaming transcription (`gpt-realtime-whisper`) + Decisions API (`gpt-6-luna`) | Rule decider; transcript from the existing `/api/transcribe` |
| **Deep research** | Plan → 5–6 parallel searches → full pages read → cited brief (sections, ranking for "best of" topics) → every claim checked against its sources, unsupported claims dropped → cached | Tavily + OpenAI (strict JSON schemas) | Labelled demo brief |
| **Weekly watch** | Research topics that refresh on a schedule (`watchlist.json`) so the newest brief is ready first | as above | Demo brief |
| **Gmail** | Real inbox, search, message bodies; send only from the compose button (server refuses unconfirmed sends) | Gmail API, OAuth, dedicated test account | App's demo inbox |
| **@messenger in chats** | Fact check with sources, on text or photos (vision model reads the photo first) · sticker packs · three image choices · trip plan (leave in the HR portal, flights, budget in local currency, group, reminders; a date in the request, e.g. "on 2 january", is kept) — all from the last 10 messages | OpenAI + Tavily (fact check, ideas); free FX API; existing flights route | Demo answers, bundled packs, demo images, rule-based planner |
| **Memory** | Messenger Updates tasks survive a reload; user facts; conversation log; research cache | Redis | In-process memory |
| **Spend cap** | Every paid call is priced before it runs and refused past the cap; ledger survives restarts | — | — |
| **Traces** | Every utterance, decision (with probabilities), action, outcome and research run → `GET /agents/trace` and `.data/trace.jsonl`; no audio stored | — | — |
| **Clean AI Detection** | One single-GPU FIFO job backend (`resize` / `sdxl` / `resize_then_sdxl`, 50 MB jpg/png/webp, per-user jobs, server-owned stages); Apps screen + `@messenger clean` chat skill; OpenAI provenance check only when the key is set | local GPU (CUDA torch + Pillow) + `remove-ai-watermarks==0.45.1`; OpenAI key for verify only | Service-off message in chat, demo in the screen |
| **Look at a photo** | `POST /agents/messenger/look`: the vision model answers a question about a chat photo (pixels, not the caption) | vision model key for live; seeded demo photo described offline | Falls back to the text-only answer |

## Current verification (2026-10-08)

- Offline checks: **169 passed, 1 Redis test skipped**; voice dev **113/113**, holdout **32/32**; typecheck and Vite build pass.
- Voice has **14 actions**, including a meeting draft separate from paid trip planning. Sends wait for final speech and the undo window; calendar drafts require review/save.
- Streaming supports up to **120 seconds of active speech**; reply dictation ends after **4 seconds of quiet**, other commands after **1.4 seconds**. No speech times out after 15 seconds; the batch fallback retains its original limits.
- Current cloud decision connectivity and the latest audio/UI behavior are **not live-verified**. Earlier successful probes do not establish current availability; recent traces included model connection failures.
- Local models and a Cloud/Local setting are deferred. No local adapter was added.
- The 2026-10-08 figures above predate the `app-ai-removal` cleaner work (`998aef4`, `80ec042`): the cleaner
  backend, screen, chat skill and key-gated verify, plus a socket-free `tests/test_ai_cleaner.py` (10 tests, passing).
  A live GPU run and a live verify call are still unverified.

## Try it (5 minutes)

```bash
npm install && npm run dev        # terminal 1 → http://localhost:5173
npm run agents                    # terminal 2 → creates agents/.venv on first run, serves :8787 (Redis optional)
```

Open **Chats → Arif Khan** (the Egypt-in-January conversation is at the bottom) and type:

| Type | What happens |
|---|---|
| `@messenger is this true` | Fact-checks Arif's last message ("Grand Egyptian Museum is fully open"): verdict chip, one-or-two-line answer, sources. Faint dashed frame = Messenger, not a person |
| Hover a message → ↩ Reply (phone: long-press), then `@messenger is this true` | Checks *that* message (e.g. "Flights from DXB are short, under 4 hours") |
| `@messenger create sticker of this` | Picks the pack that matches the chat (Nile Days) from `public/stickers/<pack>/`; tap one to send it; **Another pack** shuffles |
| `@messenger create image about this` | Three images to choose from; tap one to share it |
| `@messenger setup plan for this` | Files leave 1–12 Jan 2027 in the Nadi demo connector (7 leave days thanks to New Year's Day + 2 weekends), mini calendar, top 3 flights for 4 travellers, AED 1,500 → EGP, **Create group** with Arif, Omar and Hana, reminder + leave added to Calendar, typical Cairo weather, documents check |
| `@messenger` anywhere else in a message | As before (images, video, flights, weather, answers), now with the chat as context and a faint Messenger reply |

Also: voice (mic in **AI Chat**) — "open my messages and text Mazen I'm on my way"; **Research** shows the weekly
watch topics; **Mail** shows Gmail once the test account is linked (below).

## Run

```bash
cd agents
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
redis-server --daemonize yes                      # or: docker compose up redis
.venv/bin/uvicorn messenger_agents.app:app --port 8787
# in the repo root: npm run dev → http://localhost:5173 (proxies /agents → :8787)

docker compose up --build                         # alternative: service + Redis in containers
.venv/bin/python -m pytest                        # 169 pass, 1 skipped without Redis; no network (or: npm run agents:test)
.venv/bin/python -m eval.run_eval                 # voice eval (offline) — see eval/REPORT.md
```

Live providers are **opt-in**: a key alone never spends. Set in the repo's `.env`:

```
AGENTS_LIVE=1            # allow paid calls (OpenAI, Tavily)
AGENTS_BUDGET_USD=1.00   # hard cap; the service stops paid calls and reports when it is reached
```

`GET /agents/health` reports configured provider modes (not a successful connectivity check), the store (redis/memory) and spend; `GET /agents/budget` lists each charge. New dep `python-multipart==0.0.32` (multipart cleaner upload). Cleaner run notes (GPU env, VRAM) and full endpoint/stage reference: [docs/ai-image-cleaner.md](../docs/ai-image-cleaner.md).

### Budget for a 5–10 minute investor session ($1 cap)

| Item | Price used | Session estimate |
|---|---|---|
| Streaming transcription | $0.017 / min (approved) | 10 min → $0.17 |
| Decisions | $0.10 / M input (approved); output metered at $0.40 / M (assumption, set `PRICE_DECISION_OUT_PER_M`) | ~100 utterances × 7 decisions × ~1k tokens → ~$0.07 |
| Deep research | Tavily $0.008 / credit (6 per run) + ~16k tokens on the research model | ~$0.05 per brief × 5 → $0.25 |
| Weekly watch | 2 topics | ~$0.10 |
| **Total** | | **≈ $0.60, hard stop at $1.00** |

### Gmail test account (when the account exists)

1. Google Cloud → OAuth client, type *Web application*, redirect URI `http://localhost:5173/agents/mail/oauth/callback`;
   add the test account under *Test users*.
2. Save the client JSON as `agents/.secrets/gmail_client.json` (git-ignored).
3. Open `http://localhost:5173/agents/mail/oauth/start` and sign in. The Mail screen switches to the real inbox.
   Testing-mode sign-ins expire after 7 days; repeat step 3.

## Voice command design

```
mic ─AudioWorklet 24 kHz PCM16─▶ WS /agents/voice ─▶ transcription (deltas) ─▶ partial transcript
                                                                                     │ stable ≥ 0.35 s or clause closed
                                       one Decisions request, 3 closed Choice questions (action · contact · screen)
                                                                                     │
               policy: p ≥ 0.80 and margin ≥ 0.30 · recipient guard (exact name only) · argument rules
                                                                                     │
  browser executor ◀── act (in-app, now) · undo (send, after speech, 3 s) · confirm (paid) · ask · cancel · chat
```

- **Closed action list (14):** `open_screen`, `open_chat`, `send_message`, `read_messages`, `compose_email`,
  `check_notifications`, `get_weather`, `search_flights`, `research_topic`, `plan_trip`, `plan_meeting`, `generate_image`,
  `generate_video`, `none`. **Fast path:** short in-app commands that name nobody and that the rules decide at
  p ≥ 0.95 skip the model (`FastPathDecider`, `AGENTS_FAST_PATH=1`). Choice answers cannot carry free text, so message
  bodies, cities, topics and prompts come from deterministic rules (`text.py`) on the clause that was decided.
- **Multi-step:** a sentence is split into clauses at "and / then / after that" or sentence breaks only when an app
  command head follows ("bread and milk", "and bring chips", ". Bring drinks too" stay in the message). Each clause
  is decided on its own; streaming and final routing share the parser, with `clausePlan` recorded in the trace.
  Pronouns resolve to the contact named
  earlier in the sentence. "And/but also" goes through a router: it splits only when a preset command head follows
  ("…and also plan the trip" → message + plan, the plan taking the reply's recipient as companion); anything else
  stays dictation ("…but also bring chips" is sent whole).
- **Open-then-dictate:** bare "reply (with/saying) …" heads a send to the chat this turn opened or read (carried up
  to 60 s into the next turn); a spoken name always wins and the exact-name guard is unchanged. The opening act
  carries `awaiting: "reply"`; a separate `listening` transport status also covers standalone sends and replies that
  arrive after an earlier opening act. The browser holds for 4 s of quiet / 120 s active-speech limit until the turn ends, including
  after dictation has started. The voice island floats without blurring/dimming or blocking the rest of the screen.
- **Visit clarification:** "plan the visit" asks whether this is a trip; "yes" preserves the original date/contact
  and returns a paid Confirm card. "An appointment" offers to open Calendar for manual entry, never files leave.
- **Split sentences:** a turn that is only a verb ("Open." — a pause ended the turn) asks "Open what?" and carries
  the verb into the next turn (20 s), so "Open." … "my last chat" is one command and never reaches the chat model.
- **Self-corrections:** "Lina, no, Mazen", "mail, actually calendar", "…, actually never mind". An in-app action that
  is revised is withdrawn (`cancel`, recorded in the trace) and replaced.
- **Recipients:** only the parsed recipient field is matched, never names/dates in the dictated body. Exact match
  only. Near-names ask ("Did you mean Hana?"), unknown names ask, and where a
  near-namesake exists only the spoken full name is accepted ("Sara Ali or Sarah Malik?"), because the
  transcriber takes no vocabulary hints. The answer can be the next utterance ("Sarah Malik", "yes", "no").
  A bare "reply him/her …" with no other context means the most recent chat (named on the undo card, still
  cancellable) — never a guess between names.
- **Fallback:** if the model errors, refuses or the budget is spent, the rule decider answers and the trace says so.

## Verified vs. not yet verified

Verified offline: request/response schemas against the `openai` SDK types (`tests/test_decider.py`,
`tests/test_stt_config.py`); the whole path (tests, eval, browser runs through the Vite proxy).

Earlier live probes (2026-10-08, `AGENTS_LIVE=1`; historical, not current readiness): the realtime transcription session connects and streams; the Decisions
model answers in 220–550 ms per clause (fast path 25–33 ms); live research briefs (36 sources searched, claims
verified); the live fact check; spend metered against the $1 cap.

Current traces subsequently showed decision connection failures; reachability probes without authentication returned
401, which does not verify a paid model request. No paid live call was started for the latest repairs.

Not verified: current Decisions connectivity, actual browser interaction with meeting drafts/media previews, and the Decisions model's accuracy and calibration on the eval sets (only a handful of probes — run
`AGENTS_LIVE=1 npm run agents:eval -- --live --name model`); transcription quality after the resampler fix and the
`medium` delay; `gpt-live-transcribe` (supported in code, price unconfirmed); Gmail OAuth end to end; the Docker build.

Windows note: with a voice WebSocket open, uvicorn's `--reload` can stall and keep serving old code. After changing
Python files, restart `npm run agents`.

## Layout

| File | Role |
|---|---|
| `messenger_agents/app.py` + `routes/` | `Services` + lifespan in `app.py`; one route module per area (`health`, `voice`, `research`, `mail`, `messenger`, `stickers`, `diwan`, `nadi`, `memory`, `cleaner`) + shared request models |
| `catalog.py` · `deciders.py` · `engine.py` · `contacts.py` · `text.py` · `router.py` | action list · Decisions API + rule decider · streaming intent engine · recipient guard · language rules · traceable final clause plan |
| `stt.py` · `session.py` | streaming transcription · one voice WebSocket |
| `research.py` · `watch.py` · `watchlist.json` | deep research · scheduled topics |
| `mcp_client.py` · `diwan.py` · `sticker_builder.py` | MCP client (Streamable HTTP) · Diwan events + Supabase images (max 3) + "more from this picture" (`more_from_image`) · Builder sticker packs (3 options) + GIPHY |
| `chat_skills.py` → `skills/` | compat re-exports; real code in `skills/{base,factcheck,image_ideas,stickers,nadi,planner,look}.py` (@messenger: fact check, image ideas, sticker packs, trip planner, Nadi demo connector, `clean`, look-at-photo) |
| `ai_cleaner.py` · `ai_cleaner_engine.py` | single-GPU FIFO jobs, per-user isolation, stage payloads, key-gated OpenAI verify · battle-tested engine (tuning in config.py `Cleaner`, `CLEANER_*` env — do not retune from code) |
| `tools/demo_stickers.py` | writes the demo sticker packs to `public/stickers/` (+ `index.json` fallback manifest) |
| `run.py` | `npm run agents` / `agents:test` / `agents:eval` (creates the venv, installs, runs) |
| `mail.py` · `memory.py` · `store.py` · `spend.py` · `trace.py` | Gmail · memory · Redis/in-memory store · spend cap · traces |
| `eval/` | 113 dev + 32 holdout items, runner, `REPORT.md`; historical first-run figures retained |
| `tests/` | 169 pass, 1 skipped without Redis; all offline (+ `test_ai_cleaner.py`: 10 socket-free cleaner tests) |

Moving to Vercel + Supabase later: the HTTP surface is plain JSON, and `store.py` is the only storage seam.
The voice WebSocket would need a host that keeps sockets open (Vercel functions do not).

## Connectors (Diwan, Messenger Builder, Nadi, GIPHY, Gmail, Supabase)

All built and waiting for a URL or key; `GET /agents/connectors` shows each one's state. Contracts, data locations and
what each one needs to go live: [ARCHITECTURE.md](../ARCHITECTURE.md) §2–§5. Demo Diwan events live in
`diwan_demo.json`; an event with `"pinned": true` (the Rashid anniversary) keeps its notification past its date.

## Stickers: the Messenger Builder Library and other packs

1. **Messenger Builder's approved packs, read in place** (`BuilderLibrary` in `skills/stickers.py`, re-exported by `chat_skills.py`): `MESSENGER_BUILDER_LIBRARY`,
   default the sibling checkout's `Messenger-Builder/messenger/out/library` (`library.json` + `files/<batch>/<file>`). Only
   `packs` are listed (the Builder adds a pack after its review gates; `trash` is skipped), animated `.webm` first, ids
   `mb-<pack id>`, re-read whenever `library.json` changes — approve a pack in the Builder and it shows here. Never
   written; file paths are confined to `files/`.
2. **Folder packs** under `STICKERS_DIR` (default `public/stickers`, the 4 demo packs): one folder per pack, images or
   `.webm` inside, optional `pack.json` `{"title", "tags"}`.

Both are served at `/agents/stickers/file/<pack>/<name>`. With the service off the app uses `public/stickers/index.json`.
The composer's media panel (`src/chats/MediaPanel.tsx`) shows them; tags matched against the chat pick the pack for
"@messenger create sticker of this".

Voice implementation map: `meeting.py` extracts reviewable fields; `tests/test_meeting.py` checks full streaming/final-only recovery and clarification; `tests/test_voice_session.py` checks long dictation and cancellation.

## Nadi (demo HR connector)

`POST /agents/nadi/leave {start, end, leaveDays, note}` files an annual-leave request; `GET /agents/nadi/leave` lists
them (stored in Redis). It behaves like an API but is a demo: no real HR system is called. Replace `Nadi` in
`skills/nadi.py` with a real client when an API exists.

## Meeting drafts and dependent commands (2026-10-08)

Voice can prepare a meeting/calendar draft (`plan_meeting`), distinct from paid trip planning. The immediately
preceding message supplies the proposal and its resolved contact. A draft shows the spoken venue and a date
resolved from today/tomorrow/day-after-tomorrow or YYYY-MM-DD (Dubai time); a spoken `at 7 pm` supplies the start.
Other date/place forms remain blank for review. End time is never guessed. Save to calendar requires title,
date, start/end times and place; it saves a local calendar entry, never an invitation or leave request.

A trailing bare imperative `plan for it`/`plan for this`/`plan this meeting/event` after meeting dictation splits
without needing punctuation. This is a bounded fallback convention, not general semantic understanding:
ordinary `we can plan for it`, negations and quoted words remain dictation. `then make a plan …` also splits.
Plans run only at the final pass. That pass uses the whole available transcript even when nothing ran early.
If Sara is ambiguous, her message and the following draft wait for the recipient answer. The message context
is preserved across contact-list reorderings; Arif's and Sara's proposals cannot silently exchange details.
Standalone `reply to him/her/them` opens the browser's last-interacted chat as soon as dictation begins.

Verified offline: the owner's exact multi-recipient restaurant example, streaming and final-only, recipient
clarification with a reordered list, ordinary/quoted planning words, and draft extraction. Frontend integration
checked draft deduplication, prefilled fields, review/save and cancellation. Live cloud accuracy and actual audio
still need the owner's test. Local models remain deferred.

## Manual voice checks still needed

Restart the agents service and refresh the browser before testing. Check open-then-reply, past-tense
commands, a message containing another contact's name, and ordinary `and bring chips` dictation. For visit
planning, test both the trip confirmation and appointment clarification; declining must only cancel that plan.
For the long restaurant example, verify both proposals, Sara's recipient choice, and the separate calendar drafts.
Repeat open-last-message in the same chat, expand event versions and shared chat images, and verify that the
floating voice island leaves the surrounding chat usable. Offline checks do not establish these browser behaviors.

`model unavailable` describes a failed classifier request, not a failed transcription connection. Error notes
record exception types and elapsed latency without exception text. Default realtime transcription takes no
vocabulary hints; changing to a keyword-capable transcription model requires checking its price and owner
approval for a live test. Traces are available at `GET /agents/trace` (latest 500) and appended to
`agents/.data/trace.jsonl`; the file is not served by the endpoint. Preserve trace and spend records when cleaning
scratch files. Source event originals remain in the sibling Events folder; six bundled assets live under
`public/diwan/rashid-bin-saeed-anniversary/` (three primary pictures and three versions under `03/`).
