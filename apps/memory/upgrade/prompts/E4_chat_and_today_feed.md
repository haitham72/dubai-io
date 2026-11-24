# E4 — Chat on real memory + the Today feed from real interests (Gemini, after E1)

Read `E0_real_data_round.md` first. Branch `e4/chat-today` from `main`.

## Owned files

- new `apps/api/app/chat_memory.py`, new `apps/api/app/today_feed.py` (+ `include_router` lines)
- tests for them

**Not** `apps/mobile` (Cursor wires the screens in E2 from your DTO samples).

## Deliverables

1. **Chat endpoint** `POST /api/chat/turn` (session-authenticated owner). The flow:
   - **(a)** save the turn into memory: bridge `POST /records`; the session catch-up from U2 picks it up later;
   - **(b)** `POST /context` for this message (the hybrid search; no LLM);
   - **(c)** the reply through the configured runner (`claude -p` Haiku, medium; local Qwen if configured), with the context pack as data, never as instructions;
   - **(d)** return the reply + **citations** (fact ids, `/why` links) + an "Ingested into memory" flag.

   Rules: plain AI text (root UI rule); no fake actions or statuses (rule 1); sensitive items never surface (rule 9). Replace the old `apps/api` memory chat path the app uses today (`postMemoryChatTurn`): keep its URL working if cheap, or document the new one.
2. **Today feed** `GET /api/today`. Port the 17 Nov logic read-only from `scripts/extract_all_interests.py` + `scripts/run_two_tower_recommender.py`:
   - **interests** = the owner's memory subjects / topics by salience (U1c) + **confirmed** topic interests (U2). Unconfirmed "I noticed" interests may only **re-rank**, with a visible "Because…" chip (rule 9);
   - **live results per interest** through the existing `apps/api` providers (Google Shopping AE / Places / YouTube): each card has `image_url`, `title`, `subtitle`, `source` (the chip), `url`, `provenance`, `as_of`, `because`;
   - cached per owner (TTL) so the app is fast. No result → no card (never invent one).
   - Third-party images are shown only as live, source-labelled results; never saved as static assets.
3. **DTO samples** for both endpoints in the report (Cursor builds against them).
4. **Tests (synthetic owner, provider calls mocked):**
   - a chat turn saves + cites;
   - a sensitive fact is never cited;
   - Today with confirmed interests → cards with source + `as_of`;
   - an unconfirmed interest only re-ranks;
   - provider down → an honest empty state;
   - two owners are isolated.
5. **One real check on the founder's PC** (after E1 / E2 / E3 land): the founder's own Today shows ≥ 5 live cards with images. Record the counts only, never the content, in the report.

**Report** → `reports\E4.md`, with the DTO samples.
