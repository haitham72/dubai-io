# Calls + services + panels plan — DRAFT, awaiting founder sign-off (23 Oct 2026)

Status: plan only. Covers the founder's WhatsApp-style calls feedback, services 3.1 thumbnails, panels-not-popups, and services directory expansion. Do not implement until signed off. Source log: `docs/request-backlog.md` ("Calls WhatsApp-style + services 3.1 thumbnails").

## 1. Calls screen — WhatsApp style

Target surface: `apps/web` calls destination (planned touch points: hub/contacts/calls JS + `community.css`; verify exact files at implementation — no unrelated refactoring).

- Header reads "Call". Directly under it a subheader carousel with tabs: call | keypad | favorites.
- A search row sits on top (filter contacts/calls).
- Contacts list fixed on the right side of the calls surface.
- Keypad stays inside Calls (not a separate destination).
- Calling semantics unchanged: in-app call log + explicit device-dialer handoff (`tel:`). No fake in-app calling; the handoff must read as a handoff, not a simulated call screen.
- Thumbnails: real open-licensed contact images where available, consistent with the existing attribution rules; no placeholders presented as people.

Acceptance: side-by-side visual check against the WhatsApp reference at 390x844 and 428x926, normal + reduced motion; existing contacts/calls tests stay green; call-log entries still record keypad-dialed numbers via `POST /api/calls`.

## 2. Services — 3.1 thumbnails per row

- Exactly 3 full thumbnails per row plus ~10% of the next (3.1) to signal horizontal scroll; snap alignment so a swipe lands cleanly.
- The 1.5-per-row state must be gone at 390/428 widths. If a category has too few entries to scroll, the row renders left-aligned full tiles with no phony peek.
- Thumbnails: real imagery; every tile keeps its provenance label behavior (no invented ratings/prices).

Acceptance: measured tile widths at both phone sizes (screenshot + computed-style check); snap verified by scroll test; reduced motion removes scroll animation but keeps position.

## 3. Panels, not popups

DMs, the Reddit-style feed thread view, and settings stop using centered modal overlays. They slide in/out full-height, WhatsApp-style.

- Planned touch point: the page/panel host (`apps/web/page-host.js` + hub/feed/settings surfaces; verify at implementation).
- Back gesture/button parity: system back and the in-panel back control both dismiss to the exact previous scroll position.
- Deep-linkable: an open panel has a route/hash so reload restores it (or lands on its parent honestly — never a blank panel).
- Reduced motion: instant swap, no slide animation. Focus moves into the panel on open and returns on close (keyboard path).
- Approval cards, dialer handoff sheets, and destructive confirms are NOT panels — they stay explicit interruptive UI per the approval rules.

Acceptance: open/close/scroll-restore journey per surface at both sizes, normal + reduced motion; no centered overlay remains on these three surfaces; back-button journey passes in the browser.

## 4. Services directory expansion

Goal: full DubaiNow-equivalent COVERAGE as browsable entries in our own design — never the DubaiNow look (still NEVER), never invented availability.

Coverage areas (non-exhaustive; intake decides order): police info/contacts + reporting where a real channel exists; DEWA + other utilities info/displays + top-ups; Salik/parking/RTA info + displays + top-ups; licensed-charity directory + donations; visa/health/government info + booking links.

Rules per entry (no exceptions):

- Filed per category via `docs/services/intake.md`; default outcome is a registry row, not a bespoke mini-app.
- Every entry carries provenance; info-only entries link "Open official portal".
- Execution (top-up, filing, donation, booking) only via a real registered adapter with explicit per-action approval and verified provider evidence — rule 1 intact (no authoritative event, no success status).
- Without an adapter the entry shows the blocker + portal link and keeps the draft; never a fake Send.
- Donations: licensed charities only; license/provenance shown; same approval + evidence path as payments.
- Grid density follows §2 (3.1 rows); categories group entries so the grid stays scannable as it grows past dozens of entries.

Acceptance: each shipped entry names its adapter or shows its blocker; a blocked entry demonstrably keeps its draft and links the portal; no entry shows a success status without provider evidence; intake files exist per category.

## 5. Slices (in order, each reviewed separately)

- S1: Calls screen restyle (§1). Gate: WhatsApp side-by-side passes.
- S2: Services 3.1 grid (§2). Gate: measured widths + snap pass.
- S3: Panels for DMs, thread view, settings (§3). Gate: back/scroll-restore journeys pass.
- S4: Services expansion batches (§4), intake-ordered, a few categories per batch. Gate per batch: adapter-or-blocker holds for every entry.

## 6. Open questions for sign-off

1. Proceed S1→S4 in order, or reprioritize (e.g. panels before calls)?
2. Services expansion: which categories first (utilities? police? donations?)?
3. Any category explicitly excluded from expansion?
