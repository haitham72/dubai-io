# Mirsal POC audit

**Status:** planned — awaiting founder approval (23 Nov 2026, Cursor).  
**Commit audited:** `6b45ba48874a60174c728eecedc6c94c0b818231` (2026-11-19 20:20 +0400), branch `master`, throwaway clone `D:\Vscode\_scratch\mirsal-p1-tests`.  
**What this repo is:** a clickable investor demo plus an offline Python agent suite. It is not a multi-user messenger.

The lead re-ran the agent suite after the lane: `agents\.venv\Scripts\python.exe agents/run.py test -rs` from that clone. Same result.

## Tests

Command, from the clone root: `python agents/run.py test`. It creates `agents/.venv`, installs `requirements-dev.txt`, changes into `agents/`, and runs pytest. Exit code 0.

```
........................................................................ [ 35%]
........................................................................ [ 71%]
..............................................s..........                [100%]
SKIPPED [1] tests\test_store.py:20: no local Redis
200 passed, 1 skipped in 7.97s
```

The first lane run was 200 passed, 1 skipped in 8.64s, before the skip reason was printed. Venv Python 3.13.9.

`README.md` and `agents/README.md` still say 169 offline passes + 1 Redis skip, and 10 cleaner tests. Those figures were not reproduced. `tests/test_ai_cleaner.py` is 13 passes inside the 200 (lane invocation `pytest tests/test_ai_cleaner.py -q`, 13 passed in 0.58s). The eval gate ran inside the 200 and passed its assertions (`wrong_recipient == 0`, `premature_outward_or_paid == 0`, `args_accuracy >= 0.95`). It did not print 113/113 or 32/32.

No agents test opened a live HTTP client. `httpx.AsyncClient` in `test_diwan_builder.py` uses `MockTransport`. The only skip is Redis. Typecheck, the Vite build, `tests/photo-window`, and the retired `server/` tests were not rerun.

## Stack

| Piece | Evidence |
|---|---|
| React 18 | `package.json` `"react": "^18.3.1"` |
| TypeScript | `package.json` `"typescript": "^5.6.3"` |
| Vite | `package.json` `"vite": "^5.4.11"` |
| Vercel functions | `vercel.json` route `api/*.ts` |
| FastAPI | `agents/mirsal_agents/app.py` |
| Redis optional | `agents/mirsal_agents/store.py` — `RedisStore`, else `MemoryStore` |
| Not Electron | `package.json` has no `electron` dependency. The desktop frame is a browser window. |

## Chat, memory, photos

Chat is client state. `src/store.ts:106` sets `messages: seedMessages`. `src/chats/data.ts` exports `seedMessages`. `sendToChat` and `receiveMessage` (`store.ts:162-172`) append to that array. There is no server chat table.

Memory is Redis or process memory. Routes: `agents/mirsal_agents/routes/memory.py` GET/PUT facts and tasks. The in-process contract passed. The Redis parameter skipped. This is not Hindsight.

pgvector is photo search. `api/photos.ts` enables `vector` and searches `photo_jobs`. No message table uses it. This audit did not connect Postgres.

Auth is a demo-link cookie. `middleware.ts:1-2`: “a private-link gate for the investor demo (no OAuth).” The agent user is the header `x-mirsal-user`, or the string `"demo"`.

## Updates tray

The spec and master disagree. Spec §0 and §3: preserve the compact Mirsal Updates tray, and do not reflow or crop chat when it opens.

Commit `6b45ba4` subject: “Mirsal AI workspace replaces Updates tray; collapsible nav; white chat header.”

On master, the desktop Chats row is `MirsalAiRow` (`src/updates/index.tsx:1`, `:22`). Its click calls `actions.openUpdates()` (`index.tsx:46`). `openUpdates()` sets `screen: "ai"` (`src/store.ts:147-148`). The Chats screen is replaced by the Mirsal AI workspace. The comment on `:147` still mentions a phone Updates sheet; the function itself always sets `screen` to `"ai"`.

## Classification

Labels: `working/tested` means this offline run executed it. Live providers, the browser, and a second user were not part of that run.

| Item | Class | Why |
|---|---|---|
| Desktop and phone UI | implemented but unverified | Screens and layouts exist (`src/screens.ts`). No typecheck, build, or browser pass in this audit. |
| Chat experience | mock/fixture | Seeded `seedMessages`. Client-only send. |
| AI voice / in-app actions | working/tested | Fourteen actions and the eval gate passed offline. Live audio and cloud decisions were not run. |
| Chat skills and planning | working/tested | Planner, demo fact-check, image ideas, stickers, and photo-look passed against fakes. |
| Sticker experience | working/tested | Offline pack match and Builder-library read passed. Without `MIRSAL_BUILDER_MCP_URL`, sticker mode is demo. Live pack generation was not run. |
| Images and video | mock/fixture | `api/images.ts` returns a fake job when Higgs is unset. `api/videos.ts` defaults `MIRSAL_FAKE_VIDEOS` to `"1"`. |
| Workspace modules | implemented but unverified | Registered screens. Mail, stocks, flights, history, research, and calendar are fixtures or local storage. Weather’s Open-Meteo call was not made. |
| AI memory | working/tested | In-process facts and tasks round-trip. Redis skipped. Not Hindsight. |
| Connectors | implemented but unverified | Diwan, Nadi, and mail contracts passed against mocks. Live Gmail, Diwan MCP, Builder MCP, and GIPHY were not connected. |
| Test evidence | working/tested | This run: 200 passed, 1 skipped. The README totals are stale. |
| Client (spec §6) | implemented but unverified | Vite app is present. Build was not run. |
| API / agents (spec §6) | working/tested | FastAPI offline surface passed. Vercel `api/*.ts` handlers were not executed. |
| Database (spec §6) | implemented but unverified | Photo pgvector code only. No database was contacted. No chat tables. |
| AI engine (spec §6) | working/tested | Rule decider, fast path, skills, and spend cap passed with no network. |
| Provenance (spec §6) | not found | No message source-id, trust-tier, or confirmation-history model. Image-signal mapping in the cleaner tests is not chat provenance. |
| Operating costs (spec §6) | working/tested | Spend cap refuses the next paid call and the ledger restarts without Redis. No local Qwen extractor was found in this pass. |
| Real multi-user transport | not found | Messages stay in the client store. The WebSocket in the POC is voice. |
| Auth as a verified user | not found | `DEMO_KEY` cookie. Header `x-mirsal-user`. |
| RLS | not found | No row-level security policy in the POC. |
| End-to-end encryption | not found | No protocol implementation. The product must not claim it. |
| Supabase chat | not found | Supabase appears as the photos database URL and Diwan image config. |
| Hindsight | not found | Facts, tasks, and a short thread in `store.py`. |

`Slides/output_grid/` has four JPGs. `screens/` has 21 reference images. Bytes were not read. Ownership is `ip-and-baseline.md`.

## Do not mark these working

- Person-to-person delivery, accounts, RLS, end-to-end encryption, Supabase chat, and Hindsight.
- Redis, and any live OpenAI, Tavily, SerpAPI, Finnhub, Higgs, Gmail, Diwan, Builder, GIPHY, Open-Meteo, or GPU cleaner call.
- The Vercel handlers, typecheck, production build, photo-window tests, and the retired `server/` tests.
- The README totals 169 and 10, and the voice item counts 113 and 32.
- The compact desktop Updates tray. On this commit, opening updates leaves Chats and mounts the Mirsal AI workspace.
- pgvector as message storage.
