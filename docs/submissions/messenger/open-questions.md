# Messenger — founder questions

**Status:** planned (revised to D1–D6) — awaiting founder approval (23 Nov 2026, Cursor).

P2 cross-checks what is still open. The import does not run until the keep/exclude list is signed. Chat that needs a verified `user_id` waits for Gate S.

## Answered (23 Nov)

### M0 — D1

The office owns the old product and its brand. The redesign repo is the founder’s own app. Every feature the founder added there is the founder’s, and the office app never implemented those features. M0 is **reuse that code as a rebranded snapshot**, not clean-room and not a history-keeping subtree. The list is `ip-and-baseline.md`: keep 12, exclude 8, rebuild 16. The logo, the Diwan pictures, the 97 photos, the four sticker packs, and the Builder generator are excluded.

Import still waits on the signed sentence in that file. That signature is the rest of D1, not a new question.

### Updates tray — D4

The 19 Nov AI workspace (commit `6b45ba4`) is current. `openUpdates()` sets `screen: "ai"` (`src/store.ts:147-148`). The spec’s compact-tray line is outdated. `MG-B2` keeps the workspace and renames the visible product string.

### Messaging boundary — D3

Messenger owns all person-to-person messaging: 1:1, groups, media, and stickers, plus the chat-to-action business agents. Community builds no messenger. Its Inbox is notifications only. A “message this person” action deep-links here once shared identity exists. The parked `chat_*` tables in `communities.py` are not extended, and this branch does not edit that file.

### Old name, logo, and the Builder — D1 and D6

The old product name is retired. The working name is Messenger. The orb logo is excluded. The Builder service is excluded entirely: no code, prompts, design, emoji-bank data, or MCP adapter. Built-in packs are finished files the founder supplies. User stickers are a photo plus background removal (D7).

## Open

### Transport — for P2

The spec allows Supabase Realtime plus Postgres RLS, or a justified WebSocket. Schema `dubaiio` is revoked from `anon`, `authenticated`, and `service_role`. There is no verified JWT yet.

**Recommendation:** a cookie-authenticated FastAPI WebSocket until B0 identity exists. Durable rows are `mg_*` in `dubaiio`. RLS SQL is written under `apps/messenger/supabase/` and is not called live until it is applied. The API membership check is the fence until then.

**Blocks:** the live two-user claim in `MG-B3`. Local UI work in `MG-B2` does not wait on this.  
**Deadline:** P2, so the shared contract does not assume browser Realtime.

### O2 — the product name

Messenger is the working name. The final name is not chosen.

**Recommendation:** ship the working name in the UI and the deck until you pick one. Do not put the retired name or the excluded logo on either.  
**Blocks:** the chrome and `MG-B8` only in the sense that the title string is still provisional. It does not block the snapshot.  
**Deadline:** before the deck is recorded.

## Not blocking

- Group size cap of 8. Change it when a pilot needs a different number.
- Voice and video calling stays P1. The business demo does not use it.
- Stage 1 (family and friends) is a usability test. Family content is not inferred into memory (rule 9).
- `workspace.task.create` is not in `CAPABILITIES` today. `MG-B6` registers it from `apps/api/app/messenger/capabilities.py` at import time and does not edit `actions.py`.
- How `apps/messenger/supabase/` SQL is applied waits until the two `main`s merge. Until then the API checks membership.
- Concept sheets, Kling clips, and fonts without notices stay on the rebuild rows until the signed list says keep or drop.
