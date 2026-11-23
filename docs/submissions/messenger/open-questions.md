# Messenger — founder questions

**Status:** M0 and transport answered — 23 Nov 2026 (founder, D11). O2 stays open. Gate S is on `business`. UI slices stop for a staged visual review.

## Answered (23 Nov)

### M0 — answered 23 Nov 2026

The founder confirmed the list. The confirmation block at the top of `ip-and-baseline.md` is the decision. Concept sheets, the named screen frames, the video clips, and the motion-graphics audio and photos are kept, except any image that shows the old name or logo, and except the dynamic-island scrapes. The Diwan connector, the Nadi connector, and the watermark-removal cleaner are dropped. Fonts without notices, Google Fonts links, and Unsplash or Pravatar hotlinks are fixed in the rebrand. `MG-B1` and `MG-B2` are approved. Every later slice waits.

### Updates tray — D4

The 19 Nov AI workspace (commit `6b45ba4`) is current. `openUpdates()` sets `screen: "ai"` (`src/store.ts:147-148`). The spec’s compact-tray line is outdated. `MG-B2` keeps the workspace and renames the visible product string.

### Messaging boundary — D3

Messenger owns all person-to-person messaging: 1:1, groups, media, and stickers, plus the chat-to-action business agents. Community builds no messenger. Its Inbox is notifications only. A “message this person” action deep-links here once shared identity exists. The parked `chat_*` tables in `communities.py` are not extended, and this branch does not edit that file.

### Old name, logo, and the Builder — D1 and D6

The old product name is retired. The working name is Messenger. The orb logo is excluded. The Builder service is excluded entirely: no code, prompts, design, emoji-bank data, or MCP adapter. Built-in packs are finished files the founder supplies. User stickers are a photo plus background removal (D7).

## Open

### Transport — answered 23 Nov 2026 (shared contract, D11)

Messenger uses a FastAPI WebSocket on `app.messenger.server:app` (`:8070`), bound to the B0 verified `user_id`. The client exchanges `POST /api/identity/sessions` with `app_id="messenger"` for an HttpOnly `cs_session_messenger` cookie, or `POST /api/identity/ws-ticket` for a single-use, 60-second Origin-bound ticket. An anonymous `dubaiio_lab_session` is prohibited for live multi-user chat. Browser Supabase Realtime against `dubaiio` is prohibited.

**Blocks:** nothing further on transport. Gate S is on `business` (`720d0a4`). Live Supabase still waits for local Docker (D12).

### O2 — the product name

Messenger is the working name. The final name is not chosen.

**Recommendation:** ship the working name in the UI and the deck until you pick one. Do not put the retired name or the excluded logo on either.  
**Blocks:** the chrome and `MG-B7` / `MG-B8`. It does not block slices before the deck and video.  
**Deadline:** before MG-B7.

## Not blocking

- Group size cap of 8. Change it when a pilot needs a different number.
- Voice and video calling stays P1. The business demo does not use it.
- Stage 1 (family and friends) is a usability test. Family content is not inferred into memory (rule 9).
- `workspace.task.create` is not in `CAPABILITIES` today. `MG-B6` registers it from `apps/api/app/messenger/capabilities.py` at import time and does not edit `actions.py`.
- How `apps/messenger/supabase/` SQL is applied waits until the two `main`s merge. Until then the API checks membership.
- Concept sheets, Kling clips, and fonts without notices stay on the rebuild rows until the signed list says keep or drop.
