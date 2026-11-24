# E3 — The founder's real data into memory, with consent (Codex)

Read `E0_real_data_round.md` first. Branch `e3/ingest` from `main`. Keep it tight: Codex gets half the volume of the others.

## What exists (reuse it)

- **Memory engine importers** (`apps/memory/src/temporal_memory/ingest/`): `gmail_json`, `email`, `youtube`, `takeout`, `whatsapp`, `ai_exports`, desktop `browser` + `agent_sessions`. Triage, dedupe, Forget rules and day-packet jobs are all built in.
- **The bridge** `POST /v1/owners/{o}/records` (on Postgres, U1a) and **`onboarding-status`** (progress %).
- **`apps/api`:** Google OAuth helpers (`oauth.py`, `connectors/`, encrypted token storage), identity (`/memory-device-token`). The 17 Nov reference script `scripts/sync_google.py` (Gmail with a 50k-token cap, YouTube 4 feeds) is **read-only: port the logic, don't run it against the repo**.

## Owned files

- `apps/api/app/connectors/**` (Google sources)
- new `apps/api/app/ingest_routes.py` (+ one `include_router`)
- `apps/memory/src/temporal_memory/ingest/**` only for small fixes the real formats need
- tests

## Deliverables

0. **Verify the merged Forget regression (fix merged in `4e2646d`; originally FIX FIRST):** a topic hypothesis retracts when fewer than two supporting sessions survive. Original issue: Forget could leave an existing topic hypothesis ("I noticed you're into X") visible after erasing one of its two supporting sessions. You may edit `apps/memory/src/temporal_memory/privacy/forget.py` and `live/topics.py` for this.
   - On any Forget, drop the `topic_mentions` rows tied to the erased records.
   - Re-check every affected hypothesis, and erase or retract it if fewer than 2 distinct surviving sessions remain.
   - Bump `privacy_revision`.
   - Postgres tests: forget 1 of 2 sessions → the hypothesis is gone from `/hypotheses`, `/vault/graph` and context; forget unrelated data → the hypothesis stays.

   Commit this first, on its own branch `e3/topic-forget-fix` from `main`, with a report line in `STATUS.md`. Then continue below on `e3/ingest`.
1. **Per-source consent**, default **off**, stored per owner:
   - Gmail (primary category, last 90 days, token cap, no spam / promotions);
   - Calendar (next + last 90 days);
   - YouTube (likes, subscriptions, playlists, uploads);
   - Takeout upload; WhatsApp `.txt` upload;
   - desktop browser + agent sessions.

   Turning a source off stops pulls. "Forget this source" calls the memory Forget (U1a).
2. **Google pull on the server** for the signed-in owner: OAuth scopes requested **only when that source is enabled** (incremental auth). Tokens are encrypted at rest. Records go into memory through the bridge as day packets. Re-pulls are idempotent: no duplicates.
3. **Uploads:** `POST /api/ingest/takeout` (zip) and `/api/ingest/whatsapp` (`.txt`) → the existing importers, with zip-bomb and path checks (already in `takeout.py`). The Connect screen calls these (Cursor wires the buttons in E2; you provide the endpoints + a DTO sample in the report).
4. **The desktop sources** post to the same owner through `memory-device-token` (verify the continuous sync in `apps/desktop/electron/main/continuousSync.ts` uses it; if not, report the exact change for Cursor).
5. **Backfill progress:**
   - `GET /api/ingest/status`: per-source counts, last pull, queued / done jobs, the onboarding %, the LLM runner and model in use, a cost estimate;
   - the backfill uses the founder's `claude -p` subscription runner (no API spend); local Qwen when LM Studio is up.
6. **Tests (synthetic fixtures only, Postgres):**
   - consent off → no pull;
   - consent on → records + jobs;
   - re-pull → no duplicates;
   - Forget source → gone everywhere;
   - an upload with a bad zip → rejected;
   - two owners are isolated.

   **Never commit real exports.**

**Report** → `reports\E3.md`, with the endpoint DTO samples, the scopes list (for the founder's Google console), and the manual run sheet: connect Gmail → status shows records → memory shows facts.
