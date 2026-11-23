# Mirsal POC

An investor demo of Mirsal: private messaging with an AI assistant, agentic tasks and utility workspaces. Clickable and polished — not a production product.

Two layouts from one codebase:

- **Desktop** (1920×1080) — nav · sidebar · workspace shell.
- **iPhone 17 Pro Max** (any phone-width screen) — iOS 26 Liquid Glass look, 4 tabs, Mirsal stories, Dynamic Island, voice mode, UAE PASS e-sign (mock). Opens full-screen from the Home Screen.

Visual references live in `Mirsal-redesign.md`, `Slides/output_grid/` and `screens/`.
Run it locally: [run.md](run.md) · how the AI agents work, data map and connector contracts: [ARCHITECTURE.md](ARCHITECTURE.md).

**Stack:** React · TypeScript · Vite · Vercel Functions (`api/`) · Python agents · Lucide

## Current state (2026-10-08)

Offline checks pass: 169 tests, 1 Redis test skipped; voice dev 113/113 and holdout 32/32; typecheck and production
build. Voice has 14 actions, including reviewable meeting drafts separate from paid trip planning. Streamed
speech supports 120 seconds, with 4 seconds of reply silence and 1.4 seconds for other commands. The voice island
keeps the chat visible; event pictures and images shared in chat expand in the same viewer.

Current cloud decision connectivity, long audio and actual browser interaction still need verification after
restarting the agents service and refreshing the browser. Recent traces showed classifier connection failures;
o paid live calls were started for these repairs. Local models remain deferred. Changes are uncommitted; the
pushed checkpoint `8d43c23` predates them. See [agents/README.md](agents/README.md) for behavior and remaining checks.

The `app-ai-removal` line adds **Clean AI Detection** (2026-10-14): a local-GPU image-cleaning job backend
(`agents/mirsal_agents/ai_cleaner.py` wrapping the battle-tested `ai_cleaner_engine.py`), an Apps screen
(`src/screens/ai-cleaner/`), an `@mirsal clean` chat skill and a key-gated OpenAI provenance check —
commits `998aef4` (script + plans), `80ec042` (app, skill, engine service) and `f443d6f` (docs). Details:
[docs/ai-image-cleaner.md](docs/ai-image-cleaner.md). The cleaner backend has 10 socket-free tests
(`agents/tests/test_ai_cleaner.py`, passing); the 169-test figure below predates them.

Six event assets are bundled in `public/diwan/rashid-bin-saeed-anniversary/`: three primary pictures and three
versions under `03/`. The source Events folder remains in place. Image previews now sit above the Dynamic Island blur.

---

## Run

```sh
npm install
cp .env.example .env   # set OPENAI_API_KEY; the rest are optional
npm run dev            # → http://localhost:5173 (the dev server also runs api/*.ts — no separate backend)
npm run typecheck      # app + API
npm run agents         # optional, second terminal: the Python agents service on :8787 (see run.md)
```

- Phone layout on a desktop browser: **http://localhost:5173/?device** (draws an iPhone 17 Pro Max frame).
- On your phone (same Wi-Fi): `npm run dev -- --host`, open the Network URL, then Share → **Add to Home Screen**.

| Variable | Role |
|---|---|
| `OPENAI_API_KEY` | AI chat, contact replies, research briefs, voice (speech-to-text + text-to-speech) |
| `OPENAI_MODEL` / `OPENAI_REPLY_MODEL` | Default `gpt-4o-mini` |
| `SERPAPI_KEY` | Live flights; empty → deterministic mock |
| `FINNHUB_API_KEY` | Live stock quotes; empty → demo prices |
| `TVLY_API_KEY` | Live research (Tavily); empty → demo brief |
| `MIRSAL_FAKE_IMAGES` | `1` = stock fakes (no credits). Real Nano Banana 2 needs `HF_CREDENTIALS` + `HIGGS_IMAGE_ENDPOINT` |
| `MIRSAL_FAKE_VIDEOS` | `1` = the bundled Kling clips in `media/videos/`. Real Kling needs `HF_CREDENTIALS` |
| `PHOTOS_TOKEN` | Worker/admin token for `/api/photos` (seed/claim/complete/embed/import/export) |
| `DATABASE_URL` | Postgres for `/api/photos`: local Docker (`mirsal-pg`) in dev, Supabase pooler in production |
| `DEMO_KEY` | Production only: private link gate (`/?key=…`, remembered 30 days) |

Every Higgs generation costs credits — keep the fake flags on while iterating.

---

## Deploy (Vercel)

Project `mirsal-demo` → **https://mirsal-demo.vercel.app** (private: share `https://mirsal-demo.vercel.app/?key=<DEMO_KEY>`).

```sh
vercel deploy --prod
```

Env vars live in the Vercel project (Production). `vercel.json` rewrites `/api/:name/:id` → `/api/:name?id=:id` (keeps the Hobby plan under 12 functions) and everything else to the SPA. `middleware.ts` is the private-link gate.

---

## What's inside

| Area | Path | Notes |
|---|---|---|
| Shell + nav | `src/App.tsx`, `src/shell/` | Screen registry in `src/screens.ts`; phones get `src/mobile/` |
| iPhone layout | `src/mobile/` | Tabs, chat list + Mirsal stories, Dynamic Island, sheets, `?device` preview |
| Design system | `src/tokens.css`, `src/ui/` | Shared primitives; Lucide icons only; phone tweaks are `@media (max-width: 820px)` in each module |
| State / API | `src/store.ts` (+ `storeFactory.ts`), `src/api.ts` (barrel over `src/apiclient/`), `src/types.ts` | Cross-screen via `actions`; network only through `api.ts` |
| Chats | `src/chats/` | Golden screen / geometry reference |
| Mirsal Updates | `src/updates/` | Desktop tray + detail cards (also used in the phone sheet) |
| AI Chat | `src/ai/` | Intent routing into image / video / flight / weather |
| Voice | `src/voice/` | Listen → transcribe → Mirsal AI → speak (Siri-style island on phones) |
| E-sign | `src/esign/` | e& renewal contract (EN/AR), typed signature, UAE PASS confirm (mock) |
| Clean AI Detection | `src/screens/ai-cleaner/` | Remove-AI-fingerprints jobs on the local GPU engine (Apps tile, nav "Clean AI"); `@mirsal clean` skill in chats |
| Workspaces | `src/screens/*` | Flights, weather, calendar, stocks, files, mail, research, history |
| Profile | `src/profile/` | Profile + Settings modals |
| Photos | `public/photos/`, `api/photos.ts` | 97 annotated images on the CDN (Vercel) + metadata/embeddings in Postgres (local Docker in dev, Supabase in prod). Never bytea, never base64 |
| API | `api/*.ts`, `lib/http.ts` | Web-standard handlers (Vercel + dev server). `server/` is the retired Python version |

---

## Real vs mock

| Real | Mock |
|---|---|
| OpenAI chat + intent routing, contact replies | Image generation (fake mode until Higgs API keys) |
| Voice mode (OpenAI transcribe + TTS) | Video generation (bundled Kling 3.0 clips) |
| Flights (SerpAPI) · Stocks (Finnhub) · Research (Tavily + OpenAI) | UAE PASS e-sign, mail, history |
| Files photo search (hybrid keyword + pgvector, Supabase in prod) | Booking / share affordances |
| Weather (Open-Meteo) | |
| AI image cleaning (local GPU `ai_cleaner_engine` + key-gated OpenAI provenance check) | Instagram AI labels (no integration of any kind) |
| Calendar CRUD (localStorage) | |

**API:** `POST /api/chat` · `POST /api/reply` · `GET /api/flights` · `POST/GET /api/images` · `POST/GET /api/videos` · `GET /api/stocks` · `POST /api/research` · `POST /api/transcribe` · `POST /api/speak` · `GET /api/health` · `/api/photos` (search/list/image + annotation queue) · agents: `POST /agents/ai-cleaner/jobs` · `GET /agents/ai-cleaner/jobs/{id}` + `/file` · `GET /agents/ai-cleaner/capabilities` · `POST /agents/ai-cleaner/verify` (key-gated)

Event photos: three primary images plus three versions under `public/diwan/rashid-bin-saeed-anniversary/03/`. Event and chat photos open a full-size viewer. See [agents/README.md](agents/README.md).

**Photos pipeline** (`node scripts/photos.mjs …`): `setup` (table + pgvector, drops legacy bytea cols) · `seed <folder>` (metadata only — copy the JPGs to `public/photos/` yourself) · `work` (annotate via any OpenAI-compatible vision endpoint; queue carries URLs) · `status` · `migrate --to <prod>` (metadata only, then `embed` there) · `search "<q>"` · `embed`. Annotation happens locally; only `migrate` writes to Supabase.

---

## Demo flows (phone)

1. **Stories** — tap a Mirsal circle → its card scales up; swipe left/right between tasks, scroll for details, swipe down to close.
2. **Voice** — waveform button (or "Ask Mirsal" circle) → speak → island shows what you said → Mirsal answers aloud.
3. **AI → flights** — "Find flights Jeddah to Dubai next Friday" → Dynamic Island Live Activity (JED ✈ DXB) → tap to enlarge.
4. **AI → video** — "Make a Dubai sunset video" → island tick-bar progress → plays in the story card.
5. **E-sign** — e-Sign story → type *Haitham Mohamed* or *هيثم محمد* → UAE PASS sheet in the island → Signed.
