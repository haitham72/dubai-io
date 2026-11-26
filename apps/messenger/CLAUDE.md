# CLAUDE.md — Messenger POC

**What this is:** a good-looking investor demo of Messenger — a private chat app with an AI assistant, agentic tasks and utility workspaces. A clickable demo ("Figma you can tap"), not a product. Light theme. Two layouts from one codebase: **desktop** (1920×1080 shell) and **iPhone 17 Pro Max** (`src/mobile/`, used at ≤820px).

**Sources of truth:** `README.md` (app overview, deploy), `README.md` "Run details" (run locally), `ARCHITECTURE.md` (agents, data map, connector contracts), `Messenger-redesign.md` (desktop UI spec), `Slides/output_grid/output_grid_1..4.jpg` (desktop R01–R15, mapped in spec §31), `screens/` (iOS references incl. `screens/dynamic island/`).

## Run

```bash
npm install                      # once
cp .env.example .env             # fill OPENAI_API_KEY (others optional)
npm run dev                      # → http://localhost:5173 — also runs api/*.ts (no separate backend)
npm run typecheck                # app + API
npm run agents                   # optional agents service on :8787 (agents/README.md); npm run agents:test
vercel deploy --prod             # → https://messenger-demo.vercel.app (private: ?key=<DEMO_KEY>)
```

Phone layout on desktop: `http://localhost:5173/?device` (iPhone 17 Pro Max frame).

## Current verification (2026-10-08)

Offline: 169 tests passed, 1 Redis test skipped; voice dev 113/113, holdout 32/32; typecheck/build pass.
Current voice has 14 actions and reviewable meeting drafts. Cloud connectivity, long audio and browser interaction
remain unverified; local models are deferred. Changes remain uncommitted. Runtime details and outstanding checks:
[ARCHITECTURE.md](ARCHITECTURE.md) and [agents/README.md](agents/README.md).

## Checks (run before and after a change)

```sh
npm run typecheck          # app + API
npm run agents:test        # agents service, offline (169 pass, 1 skipped without Redis)
npm run agents:eval        # voice eval, offline; add --set holdout for the held-out set
npx vite build
```

## Read, in order

1. `README.md` (Run + Run details) — how to run it locally (two terminals, from the repo root).
2. `ARCHITECTURE.md` — how the AI works, the data map (demo vs live), connector contracts, what each needs to go live.
3. `agents/README.md` — the Python agents service (voice, research, chat skills, stickers, verified vs not verified).
4. `agents/eval/REPORT.md` — the voice eval: what is measured, held-out first runs, timing choices.

## Branches (historical POC record, 2026-10-14; superseded: Messenger work now starts on feature branches from `main`, Claude merges gated work into `main`, the demo runs from the founder's PC, and the sticker Builder service is excluded; stickers use founder-made packs and local background removal within D7)

| Branch | What | Pushed? |
|---|---|---|
| `master` | Vercel production. A push deploys `messenger-demo.vercel.app`; only finished, tested work lands here. | yes — the only branch pushed |
| `messenger-agents` | Main working line: everything up to 2026-10-13 (incl. photo search index, particle lab). | no, local only |
| `app-ai-removal` | Clean AI Detection app (2026-10-14): engine `ai_cleaner_engine.py` (renamed, unchanged) + `ai_cleaner.py` job backend (5 endpoints), `src/screens/ai-cleaner/`, `@messenger clean` skill, key-gated OpenAI verify, `python-multipart`, model-weight gitignore rules. | yes — `origin/app-ai-removal` (confirm with `git status -sb` in your terminal) |

- Never merge `messenger-agents` ↔ `app-ai-removal`, and never merge either into `master` unless the owner says so.
- Work only on the branch you were given; commit before switching (uncommitted files follow you across branches).
- `.git/hooks/pre-push` blocks pushing anything except `master`.
- Push only when the owner says so. Commit messages and PR text never name an AI model.

## Layout

Desktop — one shell for every screen:

```
┌──────────────┬────────────────────┬──────────────────────────────┐
│ Nav 208px    │ Sidebar 380px      │ Main workspace (rest)        │
│ always       │ changes per screen │                              │
│ expanded     │ (optional)         │                              │
└──────────────┴────────────────────┴──────────────────────────────┘
```

The nav shows labels and collapses to a solid-white icon rail (toggle beside the logo). AI Chat is not in the nav: **Messenger AI** opens from its row at the top of the Chats list. Profile and Settings open as frosted modals over the current screen. On desktop the whole shell runs inside a macOS-style window (`src/shell/MacDesktop.tsx`: wallpaper, menu bar, Dock; red closes, yellow minimizes, green zooms to fullscreen).

iPhone — tabs **Chats · Messenger AI · Apps · Settings**; workspaces open from Apps (sidebar → sheet). Messenger is never a contact: it's the **stories row** (task circles → swipeable scale-up cards) and the **Dynamic Island** (compact / Live Activity / enlarged / Siri-style voice / Apple-Pay-style UAE PASS confirm). Native light status bar; the island drops from just under the hardware one.

## Code map

| Path | What |
|---|---|
| `src/App.tsx`, `src/shell/`, `src/screens.ts` | desktop shell, nav, screen registry (phones render `src/mobile/MobileApp`) |
| `src/mobile/` | iPhone layout: tabs, chat list, stories, Dynamic Island, sheets, `?device` preview |
| `src/tokens.css`, `src/ui/` | design tokens + shared primitives |
| `src/types.ts`, `src/store.ts` (+ `storeFactory.ts`), `src/api.ts` (barrel over `src/apiclient/`) | shared types, global store, API client |
| `src/chats/` | Chats — the **golden screen** (geometry reference); media panel (Emoji · Stickers · GIFs), @messenger skills (incl. `clean`), research report viewer |
| `src/screens/ai-cleaner/` | Clean AI Detection screen (Apps tile, nav "Clean AI"); renders the job stage payload verbatim |
| `src/updates/` | Messenger AI row in Chats (orb + live status), result detail views (shown in the Messenger AI workspace and the phone sheet) |
| `src/ai/`, `src/voice/`, `src/esign/` | Messenger AI workspace (sidebar: Agents · Ready card stack · Chats; a result opens full size in main), voice mode, e-sign (UAE PASS mock) |
| `src/screens/{flights,weather,calendar,stocks,files,mail,research,history}/` | workspaces |
| `src/profile/` | Profile/Settings modals |
| `api/*.ts`, `lib/http.ts` | Web-standard API handlers (Vercel functions; the Vite dev server runs the same files). `server/` = retired Python |
| `agents/` | Phase-two agents service (Python + Docker + Redis, local first, approved 2026-10-08): streaming voice commands (14 actions, fast path, meeting drafts), @messenger chat skills (fact check on text and photos, stickers, image choices, trip plan with leave email draft, `clean`), Messenger Builder Library stickers (read in place), deep research + weekly watch, Gmail, memory, spend cap, single-GPU Clean AI Detection backend (`ai_cleaner.py` + `ai_cleaner_engine.py`, needs the sibling CUDA env). Run: `npm run agents`. Browser reaches it only via `src/api.ts` at `/agents/*` (Vite proxy); everything falls back when it is off. See `agents/README.md` and `docs/ai-image-cleaner.md`; current verification is offline, cloud connectivity remains unverified |
| `media/videos/` | Bundled clips, played in place of live video generation |

No new npm dependencies without asking first.

Current checks (2026-10-08): 169 tests passed, 1 skipped; offline voice dev 113/113 and holdout 32/32; typecheck/build pass. Local models are deferred. The `app-ai-removal` line adds 10 passing cleaner tests (`agents/tests/test_ai_cleaner.py`); current details and limits are in `ARCHITECTURE.md` and `agents/README.md`.

## Rules

1. **One look.** Use `src/ui` primitives and `tokens.css` variables. No hard-coded colors, fonts, radii or shadows; no global CSS. Styles go in a CSS module in your folder.
2. **Icons:** Lucide only, `size 20, strokeWidth 1.75` (`ICON` from `src/ui`). Brand logos are the only exception.
3. **Slot contract:** each screen folder's `index.tsx` exports `<name>Screen = { Sidebar?, Main }` (see `src/screens.ts`). Keep the export name; split the folder into as many files as you like.
4. **Cross-screen actions go through `actions` in `src/store.ts`:** `navigate`, `openChat`, `sendToChat` ("Use in chat"), `addTask`/`updateTask` (Messenger Updates), `addEvent`/`updateEvent`/`deleteEvent` (calendar), `openModal`.
5. **Network only through `src/api.ts`.** Never `fetch` inside a component (the barrel re-exports `src/apiclient/`; put new calls in the matching domain module).
6. **Fake data lives in a `data.ts` inside the owner's folder.** Photos: `img(unsplashId, width)`; people: `avatar(1..70)` (both from `src/ui`). Only use Unsplash photo ids you have verified load (`curl -o /dev/null -w "%{http_code}" ">?w=100"` → 200).
7. **Images keep their natural aspect ratio** — no stretched strips. Rounded 14–20px.
8. **Minimal AI.** Status lines like `Searched 8 sources · 12s`, never step-by-step reasoning.
9. **Overlays never resize the chat.** Sheets and the island float over the conversation.
10. **Phone layout:** each module adapts with `@media (max-width: 820px)`; iOS rule — glass only on controls/navigation, never on content cards.
11. **Real things:** AI chat + voice (OpenAI), weather (Open-Meteo), flights (SerpAPI), stocks (Finnhub), research (Tavily + OpenAI). Image and video generation are not part of this app. Everything else is fake but clickable (UAE PASS is a mock).
12. **Secrets** only in `.env` / Vercel env (never committed).
13. **Vercel Hobby = max 12 functions:** add routes as methods/`?id=` on an existing `api/*.ts` (see the rewrite in `vercel.json`), not new files, when near the limit.
14. **Agents service env:** `.env` may have `AGENTS_LIVE=1`: live OpenAI/Tavily calls cost money, metered against `AGENTS_BUDGET_USD` (default $1). Tests and evals never spend. Ask the owner before any live run you start yourself.
15. **Files:** read and write text files as UTF-8 explicitly (Windows defaults to cp1252).

## Agents service state (2026-10-08, branch `messenger-agents`; historical POC state, old integrations and hosting are not current)

- Built provider integrations: voice (realtime transcription + Decisions model + fast path), research, fact check (text and photos), GIPHY. Current cloud decision connectivity is unverified; recent traces fell back to rules. Demo (labelled): Diwan events, Nadi leave, Supabase pictures, Builder MCP, Gmail.
- Stickers come from the sibling `Messenger-Builder` checkout's Library (read only) plus 4 bundled demo packs.
- Offline voice: dev 113/113, holdout 32/32; 14 actions. Meeting drafts, final-only recovery, stale-decision rejection and recipient clarification are covered by tests.
- Voice limits: 120 s active speech, 4 s reply silence, 1.5 s other-command silence (3-frame 0.12 arming, 0.06 release); no screen-wide voice blur.
- Local models are deferred until the owner requests them again.
- The cleaner feature is committed on `app-ai-removal` (`998aef4`, `80ec042`); model weights and job uploads are git-ignored, never committed. Cleaner tests: `agents/tests/test_ai_cleaner.py` (10, socket-free, passing).

## Open work

- Run the Decisions model on the eval sets once (`--live --name model`; estimate current cost and obtain owner approval first) and report it in `agents/eval/REPORT.md`.
- Verify current model connectivity, long audio, recipient clarification, meeting draft save and image previews after restarting the service.
- Judge transcription quality live after the resampler fix and the `medium` delay; if still poor, try `AGENTS_STT_MODEL=gpt-live-transcribe` (keywords + Arabic; confirm its price first).
- Voice search inside Chats / Mail (not built). Noto Animated emoji (not downloaded; system emoji in use).
- Hosting: the agents service needs a container host (WebSockets), not Vercel functions — `ARCHITECTURE.md` §6.

## Gotchas

- Windows: with a voice WebSocket open, uvicorn `--reload` can stall and keep serving old code — restart `npm run agents` after Python changes. Stop processes only by exact PID.
