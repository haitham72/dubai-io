# Calls + services + panels plan — DRAFT, awaiting founder sign-off (23 Oct 2026)

Status: plan only. Covers the founder's WhatsApp-style calls feedback, services 3.1 thumbnails, panels-not-popups, and services directory expansion. Do not implement until signed off. Source log: `docs/request-backlog.md` ("Calls WhatsApp-style + services 3.1 thumbnails").

## 1. Calls screen — WhatsApp style

Target surface: `apps/web` calls destination. Touch points: `apps/web/hub.js` (calls/keypad/contacts render, ~lines 75–85), `apps/web/social-ui.js` (`filterCallPeople`), `apps/web/community.css`. No unrelated refactoring.

- Header reads "Call". Directly under it a subheader carousel with tabs: call | keypad | favorites.
- A search row sits on top (filter contacts/calls).
- Contacts list fixed on the right side of the calls surface.
- Keypad stays inside Calls (not a separate destination).
- Calling semantics unchanged: in-app call log + explicit device-dialer handoff (`tel:`). No fake in-app calling; the handoff must read as a handoff, not a simulated call screen.
- Thumbnails: images are open-licensed with attribution recorded; seeded contacts stay Demo per `PLAN.md` ("Seeded people and posts are labelled Demo") and `apps/web/CLAUDE.md`. This slice does not change Demo-pill or provenance behavior; no placeholders presented as people.

Acceptance:
- Visual: the founder supplies the WhatsApp screenshot into `design/screens/`; none is committed today. If it is absent, judge against the five properties above (Call header, tab carousel, search row, right-fixed contacts column, keypad in-surface). Checked at 390x844 and 428x926, normal + reduced motion. The founder's visual approval is still required.
- Tests stay green: `apps/api/tests/test_communities.py::test_contacts_and_call_log_are_private_and_deletable`, `apps/api/tests/test_reddit.py::test_keypad_number_logs_without_contact`, `apps/web/tests/social-ui.test.mjs` (calls search + favorites).
- S1 adds one web regression asserting that call-log writes, including keypad-dialed numbers, go through `POST /api/calls`.

## 2. Services — 3.1 thumbnails per row

- Touch points: `apps/web/navigation.css:133–140` (current rail: `grid-auto-columns: 68%`, about 1.5 tiles visible, `scroll-snap-type: x proximity`) and the duplicate `.service-category-grid` rule at `apps/web/services.css:40` (static 3-column grid). `navigation.css` loads after `services.css` (`index.html` lines 11 vs 8), so its rule wins today. Consolidate into one rule in `navigation.css`, delete the dead one, and size tiles as `calc((100% - 2 * gap) / 3.1)`.
- Exactly 3 full thumbnails per row plus ~10% of the next (3.1) to signal horizontal scroll; snap alignment so a swipe lands cleanly.
- The 1.5-per-row state must be gone at 390/428 widths. If a category has too few entries to scroll, the row renders left-aligned full tiles with no phony peek.
- Thumbnails: real imagery; every tile keeps its provenance label behavior (no invented ratings/prices).

Acceptance: measured tile widths at both phone sizes (screenshot + computed-style check); snap verified by scroll test; reduced motion removes scroll animation but keeps position.

## 3. Panels, not popups

DMs, the Reddit-style feed thread view, and settings stop opening in the bottom sheet. They slide in/out full-height from the side, WhatsApp-style.

Current state (verified on `main`): these are not centered modals. DM threads (`hub.js`) and the feed thread view (`feed.js`) are `page-host` page definitions. `apps/web/page-host.js` opens them inside the shared bottom sheet through `openSheet()` (`apps/web/ui.js:69`, styled by `.sheet` at `apps/web/stage.css:289`: bottom-anchored, `max-height: 88%`, scrim behind). No standalone settings view exists. The closest surface is the profile sheet `openProfile()` (`apps/web/app.js`, "You, over time"); sign-off question 4 confirms what "settings" means.

- Touch points: `apps/web/page-host.js` (add a full-height panel host beside the sheet), `apps/web/ui.js` (sheet API stays for non-panel content), `apps/web/stage.css` (panel styles), plus `hub.js`/`feed.js` page definitions only where their open call changes.
- Back gesture/button parity: system back and the in-panel back control both dismiss to the exact previous scroll position.
- Deep-linkable: an open panel has a route/hash so reload restores it (or lands on its parent honestly — never a blank panel).
- Reduced motion: instant swap, no slide animation. Focus moves into the panel on open and returns on close (keyboard path).
- Approval cards, dialer handoff sheets, and destructive confirms are NOT panels — they stay explicit interruptive UI per the approval rules.

Acceptance: open/close/scroll-restore journey per surface at both sizes, normal + reduced motion; none of these three surfaces opens in the bottom sheet any more; back-button journey passes in the browser.

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
4. ~~"Settings" panel (§3)~~ Decided 23 Oct: a new settings screen, built as a slide-in panel (added scope).
