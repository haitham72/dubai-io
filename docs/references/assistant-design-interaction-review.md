# Design, interaction and use-case review — 22 Oct 2026

Status: **second independent critique. Review only: no implementation, scope change, commit or push.** It answers [assistant-design-interaction-review-prompt.md](assistant-design-interaction-review-prompt.md). The first critique, [assistant-experience-review.md](assistant-experience-review.md), is preserved unchanged. The [reconciliation](assistant-review-decisions.md) and PLAN.md founder locks take precedence: where I disagree with a reconciled decision, I raise it as a question (§8) rather than overriding it.

Subject: the **uncommitted working tree** on `redesign` (Gate A: `apps/api/app/tasks.py`, `apps/web/tasks.js`, `tasks.css`, and the `app.js` / `page-host.js` diffs) plus the existing chat, recovery, order, services and maps surfaces, the live preview on `:8010`, and the 12 founder-supplied Duet frames.

Labels: **Observed** = seen in the running preview or read in code this session (file:line or screenshot given). **Inferred** = my reading of what I observed. **Unverified** = not checked; do not rely on it. Preview screenshots are in the git-ignored `output/dx-review/` folder (names `01-…` to `13-…` below).

---

## 1. Verdict

**Gate A is solid engineering behind a weak first screen.** The task contract is careful: idempotent creates and commands, revision-guarded writes, honest "you reported" completion, truthful "automatic checks are not active" copy, a retry message that explicitly avoids duplicates, owner isolation and 15 passing task tests (re-run this session). Contrast and focus rings pass at a glance; I found no computed `box-shadow` anywhere on the onboarding or Today screens.

The experience, however, does not yet feel like assistance. It feels like a to-do list with a form. Here is what stops it being useful today:

### Five highest-impact problems

1. **Today's "Needs you" lane is inverted.** It lists every task the user typed (all `WAITING_USER`), sorted by *last edit*, capped at three (`tasks.py:257-260`). The real decisions the app already produces never appear on Today. A merchant's ready time missing your deadline, an `UNKNOWN_STATUS` order and a prepared lost-item report all live only in the chat scroll (`orders.js:133`, `recovery.js:108`). **Observed** with four seeded tasks (`03-today-four-tasks.png`): the backpack task due tomorrow at 09:00 was pushed behind "See all", while an undated laundry note stayed visible. A task due two days ago showed no overdue cue. Pausing a task removes it from Today entirely; it is reachable only via All tasks (`tasks.py:257`, verified through `/api/today`).
2. **Home lost its visual identity.** After the gradient onboarding (`10-onboarding-gradient.png`), Home becomes a grey list with a half-empty screen (`01-today-first-run.png`, `11-after-onboarding.png`). The reason is that `.home-today.mode-home #stage, #rail, #caption { display: none }` (`tasks.css:2`) hides the whole photo/gradient card deck. Those cards also carried the recommender's visible home-card boosts and "Because…" reasons. The most beautiful in-app screen, the Services landing hero (`13-services-428-later.png`), now outshines Home.
3. **Visible copy still says "visitor".** Examples: "Your Dubai companion" (`app.js:71,77`, `services.js:32`, `arrival.js:44`); "Hello, visitor." / "Where are you staying?" (`services.js:35-37`); "Your companion for a stay in Dubai" (`data.js:20`); and "Guide me to arrivals" as the first chat suggestion (`05-ask-empty.png`). The 22 Oct direction rejected visitor-first framing. A reviewer opening the app meets the old product in every surface except Today.
4. **Tasks are an island.** Nothing connects them to the rest of the app:
   - chat cannot create or refer to a task (no task references in `chat.js`);
   - a task cannot open a conversation ("Ask about this");
   - a prepared lost-item report or a live laundry order cannot be "kept track of" as a task.

   Creating a task means filling a four-field form whose "next step" is pre-filled with the literal value "Add an update when you are ready." (`tasks.js:30`, `tasks.py:39`), which then gets saved as real content. Duet's frames show the opposite pattern: responsibilities, artifacts and approvals appear *inside* one conversation and are also listed under Tasks.
5. **Today's taxi-recovery flow contradicts the founder's TAXI-02 branches.**
   - The cash path runs a simulated trace immediately, without confirming route or time (`recovery.js:58,72`). It alternates match and no-match per run (`recovery-state.js:24`).
   - It asks "How did you pay?" rather than "Do you have a receipt?".
   - A demo match jumps to "Driver en route (simulated) · 12 min to the Terminal 3 rank" with "Message driver (demo)" (`recovery.js:87-95`). That implies a return trip nobody chose, before any collection-versus-delivery decision.
   - Raw codes `UNKNOWN_STATUS` and `PREPARED_NOT_FILED` are shown to users (`recovery.js:77,81,108,118`).
   - The flow is bound to an in-memory epoch ("This flow has changed. Start a new request", `recovery.js:26`), not a persistent responsibility.

**Before the founder's thorough review, change three things** (§7): fix the Today projection and its lanes; restore Home's visual identity and sweep the visitor copy and status-code labels; add a reference-only "Keep track" bridge from a prepared report or order into a task. None of these needs a worker, connector or new execution path.

---

## 2. Reference analysis — all 12 Duet frames

These are video frames from a presentation. They show layout and pacing. They do **not** prove the backend, the connectors, the timing or the safeguards. Frame IDs below are the timestamps in `design/references/claude duet/2026-10-22 10-31-48 (…).jpg`.

| # | Frame | Observed | Principle (inferred) | DubaiIO application | Do not copy |
|---|---|---|---|---|---|
| F1 | `0-00-02-28` | Lock-screen notification: "Morning, Maya. 5 things in progress and 2 that need you." | One sentence separates *in progress* from *needs you*; the count is the hook. | Use the same split as Today's header line ("2 need you · 3 on your list"). The PWA cannot do background push; any notification stays outbox/consent/quiet-hours. | Counting self-written notes as "need you". |
| F2 | `0-00-09-02` | "Morning brief" message: five bullets, each led by an entity chip (Hiring, Northfield, Chicago location…), with one line of state plus what is needed. | The brief is a **projection of responsibilities**, not news. Chips name the responsibility and act as entry points. | Today's summary should read like this. **Naming risk:** Duet's "brief" means tasks, while DubaiIO's planned "briefing" means reading. Call the reading layer "Reading" to avoid confusing both users and jurors. | Invented urgency; summaries without sources. |
| F3 | `0-00-15-15` | A thread scoped to "Chicago location opening" (chip at top). Three short bubbles (context → 33/41 done, 7 watching, 1 needs you → the item), then an approval card: amount, "Expires in 8 min", line item, **Approve** (filled) / **Not now** (outlined). | A compressed narrative first, then exactly one decision at the end. "Not now" is a first-class defer, not a cancel. | The fixed-price order approval and the recovery handoff should follow this rhythm. Show expiry only when a real expiry exists. | Payment (absent this release); an expiry timer for urgency theatre. |
| F4 | `0-00-22-06` | The same card now shows a green **Paid** pill. Next bubble: "Inspection is the next gate." Then an FYI: install slipped to Nov 10, "I'm watching it." | The card **mutates in place**; the next dependency is stated straight away; a low-priority FYI is separated from decisions. | `orders.js` already updates the order card in place via SSE. Add *who* confirmed and *when* ("Confirmed by the shop · 10:42") — the frame shows a status with no evidence source. | "Paid"/"Confirmed" without an authoritative event (rule 1); "I'm watching it" without a real check (Gate B). |
| F5 | `0-00-27-24` | Artifact card: preview, title "Series A deck", "Updated 5:48 AM", pin and chevron. Following content blurred mid-scroll. | Results are **objects**: title, updated-at, pin, open. | The prepared report, the order receipt and later comparisons should share one artifact card with an updated-at and a pin-to-Today. | A "deck builder" scope. |
| F6 | `0-00-39-07` | User: "Pull them." → "Done. 25 of 26." → prep summary → artifact. | Terse replies; **quantified progress with an honest remainder**. | "5 of 8 report details known — pickup time is missing." | Claims of reading external bios/data DubaiIO cannot access. |
| F7 | `0-00-52-28` | Revision in conversation ("Slide 6 is too busy" → split proposal → "Much."), then "Send the deck to Elena" → "Drafted… Send from you?" | Revise freely; moving from **prepare** to **send** is an explicit, separate step. | Same split between "Prepare RTA report" and any outbound handoff. A draft never implies a send. | — |
| F8 | `0-00-56-09` | Email preview card: To, Subject, body, copy/edit icons, **Not now** / **Send**. | **Exact effect preview** at the point of decision. | DubaiIO's approval cards already list shared fields. Where no send adapter exists (RTA), the primary action is "Copy / Open official channel", never "Send". | A send button without a registered adapter. |
| F9 | `0-01-09-29` | "Build me one page I can check every morning…" → "Pulling from your point of sale, Shopify, CRM, support inbox, payroll and bank." → artifact "refreshes at 5:30 every morning". | Reusable artifact with a **stated refresh cadence**. | Only after Gate F routines and a real source. Never imply connectors that do not exist. | The connector list and the cadence. |
| F10 | `0-01-10-20` | Full-screen artifact: date and refresh line, **verdict headline** ("Healthy, with one leak…"), 2-column tiles each with a comparison line, "Where to look" ranked list. | **Verdict first**, then evidence tiles, then a ranked next look. | Pattern for the task detail and a recovery summary: verdict line → evidence → next step. Every number needs provenance and as_of (rule 2); the frame shows none. | Metric dashboards / productivity scores (rejected in review 1 §16). |
| F11 | `0-01-15-17` | Finding: "East Bay churn went from 2.6% to 3.4%… Want me to dig in?" Quick replies: Yes / No / Not now. | A proactive finding is phrased as a **question with quick replies**, not an action. | Use quick replies for recovery branches ("I have a receipt / Paid cash, no receipt / Not sure"). | Unconsented proactive findings (rule 8). |
| F12 | `0-01-23-07` | Yes → explanation → "Want a 2-week test?" → "Set it up." | Commitment escalates in small, reversible steps. | "Set it up" should create a visible **draft task** the user confirms, never an action. | — |

**Cross-frame observations.**
- **Visible across all 12:** one composer with mic; three bottom tabs (Chat / Tasks / Make); a centred orb whose shape changes between frames (inferred: an activity or state indicator); flat cards on warm grey with no visible drop shadows; peach user bubbles and grey AI bubbles.
- **What DubaiIO should take:** responsibility chips, verdict-first artifacts, in-place card mutation, Not now as defer, prepare-before-send, quantified progress.
- **What DubaiIO keeps instead:** its own plain AI text with a tinted user box (lock), cyan/purple, gradients.
- **Not shown and therefore undocumented:** the Tasks tab itself, how an approval expires, failure and unknown states, how "watching" is implemented, and any evidence source for "Paid".

---

## 3. Journey matrix

Status per step: **I** implemented · **P** partial · **S** staged demo · **PL** planned/not built · **U** unverified.

### J1 — Today → manual responsibility → detail → update → pause/resume/cancel → return

| Step | User action → assistant response | Decision / evidence | Interruption / failure | Status |
|---|---|---|---|---|
| Entry | Today tab after onboarding, or `#today` direct. Header, create card, Needs you, Running, Recently completed. | Date in Dubai time. No inferred location. | Server down → "Today is unavailable" + Try again (`tasks.js:211`). | I |
| Create | Tap "One less thing…" → 4-field sheet → Save. | `user_supplied`; boundary copy "Automatic checks and sending are not active yet." | Lost response → "Retry save to avoid creating a duplicate" with the same key (`tasks.js:61-73`). **Good.** Boilerplate next step saved as a value (DX-06). | I |
| See it | Row appears under **Needs you** with "Waiting for your update". | None needed; but every row has the same label. | >3 rows: ordering by `updated_at` hides due-soon work (DX-01). Overdue unmarked. | P |
| Detail | Row → sheet: state chip, title, due, next step, Edit / Pause / Mark done, Cancel, Activity. | Activity entries "Saved by you", Dubai time. | Stale revision → "Your edit was not applied. Reload…" (`tasks.js:144-147`). **Good.** | I |
| Update | Edit → inline form → Save; Mark done → "What happened?" → "Recorded as your update, not a provider confirmation." | Completion `provenance: user_supplied`. | Focus lands on `<body>` after each command (verified) (DX-04). | I |
| Pause/resume | Pause → state "Paused"; disappears from Today. | — | No Today trace of paused work (DX-03). | P |
| Cancel | One tap, terminal; "Tracking stopped. No request was sent." | — | No confirm/undo; cannot reopen (DX-05). | I |
| Return later | Reload → Today recomputed from server; page host restores scroll/focus on Back (`page-host.js:29`). | — | Today re-renders "Loading your day…" on every change (flash/scroll reset) (DX-04). Persistence on PostgreSQL **U**. | I / U |
| Useful assistance? | — | — | Nothing the assistant does *for* the task: no chat, no draft, no check. That is honest for Gate A, but the screen should not present admin as "needs you". | — |

### J2 — Chat ↔ browsing/maps/services ↔ task/result

| Step | User action → response | Decision / evidence | Failure / return | Status |
|---|---|---|---|---|
| Ask | Ask button → one composer, empty state "What's your next step?" with visitor suggestions (`05-ask-empty.png`). | — | Copy contradicts identity (DX-17). | I |
| Browse | Maps tab → single category row, explicit 2D Live / 3D Demo, live Google list "15 pets near Dubai Marina" (`06-maps.png`). | "Live from Google Maps · straight-line distances". | Anchor "Dubai Marina" is a hard-coded `HOME` (`places.js:4`), unlabelled in 2D (DX-11). | I |
| Place → chat | Place focus chip with Clear (CTX-01, per handoff). | 30-min focus expiry. | Re-verified only by handoff's browser checks; not re-run here. | I / U |
| Service → mini-app → approval | Services → provider row → sandboxed mini-app → approval card listing fields → "Approve and send" (`orders.js:70`). | Merchant taps are the only status source; "Confirmed by the shop, not by me" (`orders.js:132`). | Raw status pill "AWAITING APPROVAL"/"UNKNOWN STATUS" (`orders.js:144`) (DX-08). | I |
| Result → task | — | — | No "Keep track" from an order or report into Today (DX-07). | PL |
| Task → chat | — | — | No "Ask about this task". The tab bar no longer returns to an open thread from Today (`app.js:1032-1033`). Today is reachable, but the thread is one extra tap via Ask. | PL |

### J3 — Taxi lost-item recovery (receipt and cash branches)

Founder target (TAXI-02): receipt? → if cash or no receipt, confirm previous route/time → prepare official handoff → persistent recovery task → staged airport/RTA/driver replies, clearly labelled → on an identified item, choose collection at a stated place versus *supported* delivery. Gmail later.

| Step | Today's behaviour (observed in code) | Target behaviour | Status |
|---|---|---|---|
| Entry | Chat "I lost…" → "Where did you last have it?" taxi/Metro/shop/not sure (`recovery.js:39`). | Keep. | I |
| Saved trip | If saved trip facts exist → "You told me" card → Prepare report (`recovery.js:52-53`). | Keep, but present them as **candidates to confirm**, not as settled facts. | I |
| Receipt question | Asks "How did you pay?" card/cash (`recovery.js:58`). | Ask "Do you have the receipt (paper or app)?" first. Payment method is a separate field. | P |
| Receipt branch | Card → last 4 digits + optional photo → simulated trace (`recovery.js:60-70`). The photo is never read. | Upload → OCR **proposal** of available identifiers → user reviews/corrects. OCR is not built. | S / PL |
| Cash / no receipt | **Immediately** runs a simulated "Airport taxi team" trace (`recovery.js:58,72`). | First show the previous route and time as candidates; the user confirms pickup, drop-off, date/time and plate/roof clues; unknown stays unknown. | **Contradicts** |
| Handoff | Report sheet "Not filed yet" → Prepare → "Prepared, not filed" → Continue (saved request), Call RTA 800 9090, Copy (`recovery.js:100,118`). | Keep; add the exact fields shared and "Open official channel" as the explicit handoff. No government execution. | I |
| Persistent task | Recovery state is per-epoch in memory; only the report draft is saved (`recovery.js:16,26,106`). | A recovery task (Gate A record) with next step, blockers, open questions and evidence. | PL |
| Staged replies | Demo "matched" → "Driver en route (simulated)… to T3 rank", "Message driver (demo)" (`recovery.js:87-95`). | Staged *reply events* on the task ("Staged reply · airport lost & found: item matching description logged"), labelled at every result and decision; **no movement implied**. | S (wrong shape) |
| Found → collect/deliver | Not present; the demo skips straight to a driver moving. | Decision card: "Collect at [sourced place, hours]" vs "Delivery". Delivery shows "Not available in this release" unless a registered capability exists; that decision would need its own approval. | PL |
| Failure branches | No-match fixture (`recovery.js:81`), Stop demo trace. | No reply, not found, conflicting place/time, uncertain sender, cancel while waiting, delivery unavailable. | P |
| Gmail replies | — | Later connector; a received email is not proof of collection. | PL |

### J4 — Home → personalized reading → article → question/task proposal

| Step | Status | Notes |
|---|---|---|
| Entry (swipe-up + tap) | PL | No reading code exists. Today's scroll container (`tasks.css:3`) ends above the dock; a bottom-band swipe would compete with the dock and the system Home gesture (review 1, RV-06). |
| Topic choice / politics opt-in | PL | Needs a reviewed taxonomy; existing recommender topics do not cover news. |
| Card → article → "Ask about this" | PL | Must carry source/date/fragment as reference data (CTX-02 dependency). |
| Article → task proposal | PL | Should reuse the "draft task the user confirms" pattern (F12). |
| Adaptation | P (foundations) | The temporal profile with Confirm/Not true/Forget exists (REC-02); news-specific signals do not. |

### J5 — Service with evidence

| Step | Status | Notes |
|---|---|---|
| Fixed-price catalogue list → sandboxed mini-app | I | Mini-app gets `host.context` with `area: 'Dubai Marina'` hard-coded (`offers.js:195`) (DX-11). |
| Exact approval card | I | Lists fields, recipient, fixed total; single approval. |
| Merchant event → in-place card update | I | Deadline check "misses your 09:00" + "Ask for 08:30, same price" (`orders.js:133`). **This is the best "needs you" moment in the app, and Today does not show it.** |
| Honest unknown | I | `UNKNOWN_STATUS` → "Outcome unknown" warning (`orders.js:138`); pill shows raw code. |
| Linked to a task / Today | PL (Gate C) | |
| Google listing ≠ partner | I | Live Places results are separate from sandbox partners ("Sandbox partners" pill on the Services hero). |

---

## 4. Screen-by-screen recommendations

All of these preserve cyan/approved purple, gradients, no shadows, plain AI text with a tinted user box, one category row with Back, explicit 2D/3D and one composer.

### 4.1 Home / Today (DX-01, -02, -03, -14, -15)

```
┌─────────────────────────────────────────┐
│ ░░ approved cyan→purple gradient band ░░ │ ← reuse onboarding shader at low height (~120px),
│ Thursday 22 Oct · Dubai                  │   no photo, no shadow; replaces the double header
│ Today            1 needs you · 3 on list │ ← F1 sentence; counts only real decisions as "needs you"
├─────────────────────────────────────────┤
│ NEEDS YOU   (only rows with a decision)  │ ← empty in Gate A unless an order/report is linked
│  Laundry · ready 10:00 misses your 09:00 │   what changed
│  Confirmed by Foldpress · 21:14 · sandbox│   evidence + time
│  [Ask for 08:30, same price]  [Not now]  │   one decision, Not now = defer
├─────────────────────────────────────────┤
│ ON YOUR LIST            (by due date)    │
│  ● Lost backpack · taxi T3→Business Bay  │
│    Due tomorrow 09:00 · Next: confirm time│ ← next step visible in the row
│  ● Book dentist             Overdue 2 days│ ← overdue in warn token, not cyan
│  ● Renew Ejari                  Due 30 Nov│
│  Paused (1) ▸                             │ ← quiet disclosure; never vanishes
├─────────────────────────────────────────┤
│ + Keep track of something…               │ ← one-line capture (title only); details later
├─────────────────────────────────────────┤
│ For you nearby  [photo][photo][photo] →  │ ← existing stage cards as a compact row,
│                                          │   keeps photos + "Because…" chips visible
│ Reading ▸  (later, D)                    │ ← tap target; never counted above
└─────────────────────────────────────────┘
        [ Today | Maps | Services | Me ]  (Ask)
```

- Hide **Running** until a real check exists (Gate B). A permanently empty lane reading "No automatic checks running" is truthful, but it is dead weight. Put the "automatic checks are not active" boundary in the create sheet and the detail, where it already exists.
- Sort "On your list" by `due_at` ascending (nulls last), then `updated_at`. Mark overdue and "due within 24 h".
- Keep the stale content visible while refreshing (`aria-busy`). Do not replace it with "Loading your day…".

### 4.2 Task detail (DX-04, -05, -07)

```
[Waiting for your update]                         ← human state chip
Lost black backpack · taxi T3 → Business Bay
Due tomorrow 09:00 · you set this
┌ Next step ─────────────────────────────────┐
│ Confirm the pickup time and whether I have │
│ a receipt                                   │
└─────────────────────────────────────────────┘
Linked: Lost item report · prepared, not filed ▸   ← reference link (DX-07), no execution
[Ask about this]  [Edit]  [Pause]  [Mark done]     ← Ask opens chat with task focus chip + Clear
Stop tracking…  → inline: "Stop tracking? Nothing was sent. [Keep] [Stop]"
▸ Activity (3)
```

- After any command, move focus to the state chip (`tabindex=-1`) and announce the change through a polite live region.
- "Mark done" stays secondary to the next step. For a manual task, the primary action is the next step ("Ask about this" / "Edit next step"), not completion.

### 4.3 Chat / composer (DX-07, -17)

- Empty state: replace the "Your Dubai companion" airport suggestions with everyday ones drawn from the user's context ("Keep track of something", "Find a laundry by tomorrow", "I lost something"). Keep "Guide me to arrivals" only when an arrival context is user-confirmed.
- When a task is in focus, show its chip above the composer (the same component as the place focus chip, with Clear). "Make it Friday" edits *that* task only through a confirm card showing the before/after due date (UX-04).
- Offer "Keep track of this" on the prepared report card and the order card. This creates a manual task with a `links` reference (reference only).

### 4.4 Lost-item recovery (DX-09, -10)

```
Did you get a receipt for the ride?          (quick replies, F11 pattern)
[Yes — paper or app]  [No / paid cash]  [Not sure]

— No / cash —
Let's confirm the trip first. Nothing is sent.
  Pickup     DXB Terminal 3          ✓ you told me   [Change]
  Drop-off   Business Bay            ✓ you told me   [Change]
  When       21 Oct · around 23:40   ? please confirm[Confirm]
  Plate/roof Not known                               [Add]
[These are right]  (unknowns stay "Not known" in the report)

Report prepared · not filed                        ← artifact card (F5), updated-at
Shares: description, pickup, drop-off, time  (exact list)
[Open official channel]  [Copy]  [Keep tracking]   ← no "Send": no adapter

Recovery task · Waiting for a reply
┌ Staged reply · airport lost & found · DEMO ┐     ← labelled on every reply/decision
│ "A black backpack was logged at T3 L&F."   │
│ Item reported found — not yet collected     │
└─────────────────────────────────────────────┘
How do you want it back?
[Collect at T3 Lost & Found · hours: Not known]
[Delivery — not available in this release]        ← disabled with reason, unless a registered capability exists
```

- Delete "Driver en route (simulated)" and "Message driver (demo)". A demo should show *reply evidence*, not *physical movement*.
- Replace raw code chips with human states: "Not filed", "Waiting for a reply", "Found — not collected", "Collected (you reported)". Keep the codes in data attributes for tests.

### 4.5 Reading (DX-22) — later, Gate D

- Entry: a "Reading" row at the end of Today's content (tap), plus swipe-up **only on that row** to expand into a full-height sheet. Never in the bottom 34 px band or on the dock. Collapse with a header button and Escape. Restore the reading position.
- Cards: headline, publisher, publication time, topic, permitted summary, "Because you chose Arts" (the chosen-topic reason), link. Politics appears only after explicit selection, plus per-item "Not interested" and per-source mute.
- "Ask about this" → chat with an article focus chip. "Make a task" → the F12 draft-confirm pattern.

### 4.6 Service handoff (DX-08, -11)

- The order card already has the right truth model. Change the pill to human labels ("Waiting for the shop", "Outcome unknown — check with the shop") and add "Confirmed by {shop} · {time}" to each step (F4).
- Send the user-confirmed area (or `null`) in `host.context` instead of a fixed "Dubai Marina". In 2D live results, label the anchor "near Dubai Marina (demo area) · Change".

---

## 5. Findings

Severity: **H** fix before founder review · **M** fix before the demo · **L** polish.

### 5.1 Usability defects

| ID | Sev | Where | Evidence | Consequence → Fix | Verify | Dep |
|---|---|---|---|---|---|---|
| DX-01 | H | J1 Today / Needs you | `tasks.py:258` `ORDER BY updated_at DESC … LIMIT 4`; `03-today-four-tasks.png` (due-tomorrow task hidden, overdue unflagged) | Urgent work hidden behind "See all". → Order by `due_at` ASC nulls last; add overdue / due-soon flags (server-computed in Dubai time). | Seed 4 tasks (overdue, tomorrow, Nov, undated): Today shows overdue, tomorrow, Nov in that order with labels. | none |
| DX-02 | H | J1 Today lanes | `tasks.js:206-207`; `tasks.py:257` maps every `WAITING_USER` task to `needs_you`; Running is a constant | Self-written notes look like decisions; a dead lane. → Gate A: rename to "On your list"; reserve "Needs you" for rows carrying a decision (Gate C/TAXI-02); hide Running until Gate B. | Zero-decision Today shows no "Needs you" header; no permanent empty lane. | Founder Q1 (amends reconciliation wording) |
| DX-03 | H | J1 pause | `tasks.py:257` only `WAITING_USER`/`COMPLETED`; verified a paused task missing from `/api/today` | Paused work silently vanishes. → Add a `paused: {count}` projection and a "Paused (n)" disclosure. | Pause one task → Today shows "Paused (1)". | none |
| DX-04 | M | J1 detail/Today, keyboard & screen reader | `document.activeElement` = `BODY` after Pause (verified); `tasks.js:141,171,199` re-render via `innerHTML` | Keyboard and VoiceOver users lose their place; visible flash. → Focus the state chip after a command; announce through a live region; keep content during refresh. | Keyboard-only: Pause → focus on the state chip; Today doesn't blank on change. | none |
| DX-05 | M | J1 cancel | `tasks.js:117` one-tap Cancel; `tasks.py:185` terminal | Accidental irreversible stop. → Inline confirm ("Stop tracking? Keep / Stop"). | Cancel requires two distinct taps; Escape keeps the task. | none |
| DX-06 | M | J1 create | `tasks.js:30`, `tasks.py:39` default value saved; `02-new-task.png` ("optional" wraps; `mm/dd/yyyy` picker; phone icon in the sheet header) | Admin-heavy capture; boilerplate stored as content. → Title-only capture first; next step as placeholder; inline "optional"; Dubai date format hint (`en-GB`); task icon. | Create with a title only → no "Add an update…" stored. | none |
| DX-07 | H | J2/J3/J5 bridges | No task refs in `chat.js`; `recovery.js:108`, `orders.js` have no "track" action | Tasks feel separate from the assistant. → Reference-only `links` on a task + "Keep track of this" on report/order cards + "Ask about this" from detail (focus chip). No execution. | Prepare report → Keep tracking → task detail shows the linked report; opening it restores the report. | Small API field; CTX focus reuse |
| DX-08 | M | J3/J5 status labels | `recovery.js:77,81,108,118` code chips; `orders.js:144` raw status pill | Infrastructure jargon in user UI. → A single human label map; codes kept in `data-status`. | No `[A-Z]+_[A-Z]+` text visible in the order/recovery cards. | none |
| DX-09 | H | J3 cash/receipt branches | `recovery.js:58,72-95`; `recovery-state.js:24` | Guesses a trace before confirming the trip; implies a driver delivery nobody chose. → Receipt-first question; confirm route/time candidates; remove "Driver en route" / driver chat; staged reply events. | Cash path cannot reach any reply until the user confirms or marks unknown each trip field; no "en route" string exists. | TAXI-02; DX-10 |
| DX-10 | M | J3 persistence | `recovery.js:16,26` epoch/`live()` guard; toast "This flow has changed" | Recovery is not a responsibility; reload/interruption loses progress beyond the draft. → Recovery task + TaskEvents for staged replies (labelled `demo_fixture`). | Reload mid-recovery → the task shows the last step and staged reply. | Gate A tasks; staged-event kind |
| DX-11 | M | J2 Maps / J5 mini-app context | `places.js:4` `HOME.label='Dubai Marina'`; `app.js:777,817`; `offers.js:195` fixed `area:'Dubai Marina'`; `06-maps.png` | An unconfirmed location is presented as the user's anchor and passed to provider HTML (rules 3/9 tension; sandboxed, so no exfiltration). → Use `told.area` or "Choose area"; label the demo anchor in 2D. | Without a confirmed area: list header says "demo area · Change"; `host.context.area` is null. | none |

### 5.2 Visual defects

| ID | Sev | Where | Evidence | Consequence → Fix | Verify | Dep |
|---|---|---|---|---|---|---|
| DX-14 | H | Home after onboarding | `tasks.css:2` hides `#stage/#rail/#caption`; `10-…` vs `11-after-onboarding.png`; `01-today-first-run.png` (half-empty grey) | A visual cliff from gradient to grey list; the recommender's home boosts and "Because…" chips are now invisible. → A low gradient header band + a compact "For you nearby" row reusing the stage cards (§4.1). | 390×844: gradient visible above the fold; ≥1 photo card visible after scrolling; no shadows (computed). | Founder Q2 |
| DX-15 | M | Today header | `01-today-first-run.png`: "Dubai-io / Dubai" bar + date + 36 px "Today" + All tasks ≈ 170 px | Header weight with no information. → Merge into one band (§4.1) with the F1 count sentence. | Header ≤ 110 px at 390×844. | DX-14 |
| DX-16 | M | Services landing as de facto home | `13-services-428-later.png`; `services.js:32-37` | The strongest visual screen sits under a secondary tab and is visitor-framed. → Keep the hero visual vocabulary but retitle for everyday use; move "Try asking" into chat empty state/Today. | Services hero copy has no "visitor"/"staying". | DX-17 |
| DX-18 | L | Task errors | `tasks.css:61` errors use `--tint`/`--tint-soft` (same as info) | Errors read as hints. → Use the existing `.warn` token used by `orders.js`. | Error box is visually distinct from the "Next step" box. | none |
| DX-19 | L | "Scripted demo" pill on real Today | `11-after-onboarding.png` | Real tasks look scripted. → Scope the pill to scripted screens, or change the text to "Demo session". | Pill absent on Today unless a scripted trigger is on screen. | none |
| DX-13 | L | Services direct load, reduced motion, 428×926 | `12-services-428.png` blank; same view painted correctly ~2.5 s later (`13-…`) | Possible blank first paint. **Seen once; not reproduced.** → Investigate the reduced-motion entry path. | Three cold loads paint content < 1 s. | none |

### 5.3 Missing capability (planned; do not present as built)

| ID | Sev | Capability | Evidence | Dependency |
|---|---|---|---|---|
| DX-20 | H for demo | Decisions from orders/reports surfaced on Today | No Decision table (handoff "Gate A source checkpoint"); `orders.js:133` decision exists only in chat | Gate C |
| DX-21 | H for demo | TAXI-02 staged reply model, collection/delivery decision | §3 J3 | Gate A + DX-10; delivery needs a registered capability or a "not available" state |
| DX-22 | M | Reading surface + taxonomy + source register | No code | Gate D; CTX-02 for "Ask about this" |
| DX-23 | M | VIS-02 image records | `media.json`: 30 slots, all files present, none broken in Maps (verified). Fields: `source, licence, provenance, subject` — **no author, photo-page URL or download date**; sources are raw `images.unsplash.com` CDN URLs. No `onerror` fallback on CSS background images. Today has no image slots at all. Airport guide photos are generic and must not read as DXB-specific. | Founder Q4 (does the Unsplash Licence satisfy "freely licensed"?) |

### 5.4 Unvalidated product assumptions

| ID | Assumption | Why it matters | Cheapest test |
|---|---|---|---|
| DX-24 | People will maintain a manual list in DubaiIO rather than in Reminders/Notes. | Without assistant work attached, Gate A competes with built-in apps. Duet's tasks are filled by the assistant (F2, F3). | Founder 7-day diary: which saved tasks got an update, and which needed the assistant. |
| DX-25 | Staged replies will read as a credible demo, not as fakery. | Rule 1 is respected only if every reply/decision is labelled; jurors may still discount it. | Rehearse with one outsider; ask "what actually happened?" afterwards. |
| DX-26 | A swipe-up reading entrance will be discovered and won't fight scrolling. | Gesture conflicts are device-specific. | Physical iPhone test with the row-scoped swipe vs tap only. |
| DX-17 | Visitor-framed copy is harmless while the scripted airport demo remains. | It contradicts the identity in every non-Today surface (H as a usability/identity defect). | String sweep (§7). |

---

## 6. Reconciliation with the earlier review

| Earlier item | Verdict | Reason / scope consequence |
|---|---|---|
| RV-01 / C-1 "receipts thesis" as **the product promise** | **Supersede** as the promise; **retain** as design language | The founder chose everyday life/work (reconciliation §1). Evidence-on-every-row is still what separates DubaiIO from a chatbot. Apply it visually: every Needs-you row and artifact carries "who confirmed · when" (F4 gap). |
| "Never logs in / never spends" as **permanent** brand clauses | **Supersede** | Payments are LATER and connectors are staged (reconciliation §8–9). Say it in release scope: "In this release DubaiIO can't pay or sign in for you." |
| RV-03 / C-4 three lanes (Needs you ≤3, Running, Recently completed) | **Amend** | The lane *shape* is right. Gate A filled "Needs you" with manual notes, and Running with a permanent empty line. Reserve "Needs you" for decisions; add "On your list" by due date; hide Running until Gate B (DX-01/02). Founder Q1. |
| RV-06 / C-5 tap-only briefing, no swipe | **Amend** | The founder explicitly asked for swipe-up. Keep the tap; scope the swipe to the Reading row/sheet, never the bottom band; verify on device (DX-26). |
| RV-09 / C-6 politics as a **publisher/source** gate | **Amend** | A source-only gate is both too broad (a politics-leaning publisher's arts coverage disappears) and too narrow (politics from general publishers leaks through). Use explicit topic selection + item-level classification + per-source mute. **Retain** "no interest signal from political items". |
| RV-04 / C-3 / C-8 Task + TaskEvent + Decision, revision guard | **Retain**; partly delivered | Observed in `tasks.py:209-214` (revision + `cancelled_at` + status predicate) and the client's same-key retry. Decision is correctly deferred until a real decision exists. Worker claims/leases remain Gate B. |
| RV-05 / C-9 / RV-15 cost/limits surface | **Retain, defer** to Gate B | Nothing runs in the background yet; a limits page now would show zeros. |
| RV-11 no search/filter in the first slice | **Retain** | Implemented as list + pagination only. |
| RV-12 / C-12 demo spine = service with evidence | **Retain; amend** | Add TAXI-02 staged recovery as the second scene (founder-confirmed), labelled throughout. Reading is not a demo dependency. |
| C-11 adopt Duet vocabulary | **Amend** | Adopt "Not now", in-place card updates and the "N need you" sentence. Do not adopt "Paid", "Expires in" or "I'm watching it" until backed by events or checks. |
| RV-07 newsletters disambiguation; RV-08 reasons via hypotheses; RV-10 URL/title dedupe; RV-13/14 TTL and provenance vocabulary; RV-02 source register | **Retain** | Already reconciled; unaffected by design findings. |
| §6.2 task detail "Brief / Evidence / History" | **Amend** | Fine for Gate C. In Gate A there is no evidence region to fill; use state → next step → linked artifacts → activity (§4.2). |
| §6.3 explicit delegate intent only | **Retain** | Pairs with DX-07: "Keep track of this" is the explicit intent. |

---

## 7. Prioritized build plan

### Next three concrete changes (before the founder's thorough review)

1. **Correct Today (DX-01/02/03/04/05).**
   - Server: order by due date; add `overdue` / `due_soon` flags and a `paused` count.
   - Client: "On your list" lane; hidden Running; Paused disclosure; focus management; non-blanking refresh; Cancel confirm.
   - *Acceptance:* the four-task seed in DX-01 renders in due order with labels; a paused task stays discoverable; keyboard-only Pause keeps focus on the detail; existing 15 task tests stay green, plus new tests for ordering and the paused count.
2. **Restore Home identity and sweep the copy (DX-14/15/16/17/08/19).**
   - Gradient header band and a compact stage-card row on Today.
   - Replace the visitor strings in `app.js`, `services.js`, `data.js` and `arrival.js` (the airport Wi-Fi scenario keeps its airport copy *inside* the scripted flow only).
   - Human status labels throughout.
   - *Acceptance:* at 390×844 and 428×926, gradient above the fold and no computed shadows; `grep -n "visitor\|stay in Dubai\|Dubai companion"` returns only scripted-arrival files; no raw status codes are visible.
3. **Reference-only "Keep track" bridge (DX-07, start of DX-10).**
   - Add `links: [{kind: 'recovery_report'|'action', id}]` to a task.
   - Add a "Keep track of this" button on the prepared report and on order cards, and "Ask about this" on task detail (task focus chip with Clear).
   - *Acceptance:* report → Keep tracking → Today row → detail → linked report opens; the link never changes action status; owner isolation tests cover links.

### Smallest complete demo after those

Today with one linked laundry order (Gate C-lite display of the existing deadline decision) plus a TAXI-02 cash-branch recovery task with labelled staged replies and a collection-only choice (delivery shown unavailable). This uses only existing engines plus task links and a staged-event kind. Measures:
- zero unlabelled staged items;
- zero "found/collected" claims without an event;
- the founder can tell the story in ≤4 minutes without narrating around a dead lane.

### Later, with dependencies

- **Gate B** check-back (worker claims, limits surface) → real Running lane.
- **Gate C** Decision table and approvals on Today.
- **VIS-02** image records (author, page URL, download date, `onerror` fallback) after Q4.
- **Gate D** Reading (DX-22) after a source register.
- **Gmail** replies for TAXI-02 after the connector gate.

No architecture rewrite and no new feature family are needed for any of the above.

---

## 8. Material questions (five)

1. **May "Needs you" in Gate A be reserved for real decisions, with manual tasks shown as "On your list"?** This amends the reconciliation's Today wording (DX-02).
2. **After onboarding, should Today keep a visual band plus a compact row of the existing photo cards, or be strictly a list?** This decides whether the stage deck and its visible recommender reasons stay on Home (DX-14).
3. **For a found item, is any delivery capability planned for this release** (for example a sandbox courier at a fixed published fee)? If not, should delivery always render "not available — collect at the stated place"?
4. **Is the Unsplash Licence acceptable as "freely licensed",** or must VIS-02 use CC0/CC-BY sources with attribution records?
5. **Should first run stay on the scripted airport Wi-Fi onboarding,** or start with everyday onboarding and keep the airport as an optional replay? Today, `#demo.wifi` and first run both open the visitor scenario (`app.js:1102`).

---

## 9. Verification log

**Read:** PLAN.md, handoff.md, CLAUDE.md, assistant-review-decisions.md, assistant-experience-plan.md, assistant-experience-review.md (all 622 lines), the review prompt, and the Duet README. I also checked `docs/implementation-plan.md` and `request-backlog.md` for CORE-01A/TAXI-02/VIS-02, and `git status` / `git diff` for the working tree. Code read: `tasks.py`, `tasks.js`, `tasks.css`, `test_tasks.py` (test list), the migration, the `app.js`/`page-host.js`/`index.html`/`main.py` diffs, `recovery.js`, `recovery-state.js`, `service-workflow.js` (recovery request), `orders.js` (status/approval excerpts), `offers.js:186-200`, `places.js:4`, `map.js:55-65`, `media.json`, and targeted greps of `services.js`, `data.js`, `arrival.js`, `chat.js`, `ui.js`. **Not fully read:** `ARCHITECTURE.md`, `personal-assistant-direction.md`, `actions.py`, `proactive.py`, `chat.js` beyond greps (I relied on review 1's E-24/E-25 for the engine and outbox).

**Inspected:** all 12 Duet frames, in timestamp order.

**Ran:**
- `pytest tests/test_tasks.py` → 15 passed. The full 143-test suite was **not** re-run; that figure is handoff's claim.
- Playwright (Chromium, not a phone) on `http://localhost:8010` at 390×844, then 428×926 with `prefers-reduced-motion: reduce`. Screens: `#today` (empty), new-task sheet, Today with 4 tasks, task detail, Pause, Ask empty state, `#maps` (2D live), `#demo.wifi` → portal → app sheet → gradient onboarding → Start → Today, and `#services`.
- Computed-style checks: no `box-shadow` on visible onboarding elements; focus outline 2 px cyan; label colours `#076E89` / `#3C4449` on `#F3F6F8` (inferred AA).
- Screenshots `01`–`13` are in git-ignored `output/dx-review/`.

**Mutations:** in a fresh anonymous preview session (separate preview SQLite, not Supabase, not founder data) I created 4 tasks via `/api/tasks` and paused 1. No chat message was sent (no LLM call). No order, approval, merchant, recovery, RTA or provider action was triggered. Opening `#maps` caused the server to fetch live Google Places results (a read).

**Observed but cause not traced:** `#maps` opened on the "All pets" category (likely restored browser state from earlier QA); the blank first paint of `#services` (DX-13, seen once).

**Not verified:**
- physical iPhone, iOS safe areas, the software keyboard with the composer, real gestures/swipe, or animation quality;
- screen-reader output (only DOM focus checked);
- PostgreSQL/Supabase behaviour;
- Today at 428×926 (only Services was captured at that size);
- whether the Unsplash Licence meets the founder's "freely licensed" intent (recalled terms, not fetched);
- any Duet backend behaviour.

No primary external sources were consulted this session.
