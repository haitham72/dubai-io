# Muse independent review — Dubai-io contest scope arbitration

**Reviewer:** Muse (independent peer review, 19 Oct 2026).
**Read:** `CLAUDE.md`, `PLAN.md` v1.7, `ARCHITECTURE.md`, `docs/handoff.md`,
`docs/DUBAI-IO_Product_Enhancement_Review.md` v1.0, `docs/gemini-review.md`,
plus the implementation (`apps/api/app/main.py`, `apps/api/app/luna/schema.py`,
`apps/api/app/actions.py`, `apps/web/chat.js`, `apps/web/offers.js`,
`apps/web/service-workflow.js`, `apps/web/recovery.js`).
**Ran:** both frontend suites (pass); backend suite (environment-blocked, see §5).

**One-line verdict:** `PLAN.md` wins every scope conflict; the enhancement review is
a vision/proposal document that says so itself ("NOT APPROVED FOR IMPLEMENTATION",
§0). Adopt its safety doctrines, adopt Gemini's single-proof cut, and ship the
PLAN §3 laundry-deadline arc — not the 7-day film — as the 4-minute contest cut.

---

## 1. Priority and scope reconciliation

### 1.1 Authority order (not a tie)

1. `CLAUDE.md` + `PLAN.md` — canon. Explicit: "The single plan… nowhere else."
2. `ARCHITECTURE.md` — target contracts/state machine; defers to PLAN §2 on scope.
3. Enhancement review — **candidate amendment only** (its own header + §0 rule 2).
4. `docs/handoff.md` — status notes; "cannot override the canon."

So where they conflict, PLAN.md governs by the repo's own rules, not by reviewer
preference. Gemini's verdict (adopt truth-in-status + single proof + compliance
HOLD; defer the enterprise additions) is consistent with this and I endorse it.

### 1.2 Direct conflicts

| # | Enhancement review proposes | PLAN.md / canon says | Ruling |
|---|---|---|---|
| 1 | §4 L3 "Quote" as a normal integration level; §10.2 mission state includes `QUOTED / QUOTE_ACCEPTED` | NEVER: "bidding / quote / negotiation in any form"; ARCHITECTURE §4 drops `QUOTED` entirely | **PLAN wins.** Scrub `QUOTE*` vocabulary from any adopted diagram. The laundry loop is accept-at-fixed-price → ready-time check → earlier-slot ask (PLAN §3, 1:55–2:45), never a re-quote. |
| 2 | §2 seven-day arc with beats 7 (people/community), 8 (tickets/haircut/day-plan), 9–10 (Gmail fine notice + pending appeal + filing) as product direction | §2 LATER: civic RAG, community, ticket wallet, background geofencing, payments; NEVER: government transactions, fake Confirmed/Booked/Filed | **PLAN wins.** Beats 7–10 are at best labelled cinematic concept, never MVP scope. Gmail OAuth + fine filing is the highest-risk item in the file. |
| 3 | §7 human case-coordinator desk with case schema, SLAs, risk tiers | Cut order (§2: cases → Resident/VIP → onboarding go first); floor is items 1–3, 6–8, 12–13 | **Defer.** A CRM desk is post-contest. On stage it collapses to a status pill ("Merchant reviewing your request"). |
| 4 | §5.2 Docling ingestion pipeline as P1 | Phase 4 platform = price-list photo → draft catalog → generated mini-app → operator approval | **Defer generic Docling.** Keep only the narrow photo→menu extraction already scoped for onboarding. |
| 5 | §4 L4/L5 (Amazon/Noon checkout, fulfillment, webhooks) as near-term pathways | No live provider adapter registered; merchant loop is fixed-order via registered capabilities + approval | **Defer to L1–L3 handoff.** Deep links + pilot inbox only. |
| 6 | 4-minute cut ending in a **fine-appeal twist** (handoff §4.3 repeats this) | PLAN §3 ends 3:05–4:00 on the **taxi-memory payoff** ("not recovered", official handoff) | **PLAN wins.** The fine is not in the locked demo arc. See §3 D05 below. |
| 7 | D16 keeps "one-week DXB visitor" vs "real pilot" ambiguous | PLAN §3 + §6: one visitor, one continuous laundry-deadline story; Resident/VIP only after visitor parity | Visitor arc for stage; pilot = one laundry vertical, not a second persona. |

### 1.3 What MUST be cut or deferred to make the deadline

Definite cuts from the contest build (not "small versions" of them):

- Mass AI cold-calling / WhatsApp prospecting (§8.4 phase 4): **HOLD** — agree with
  both reviews. UAE Cabinet Res. 56/2024 + 57/2024 exposure; needs written counsel
  sign-off, not engineering optimism.
- Government filing / fine payment / "appeal submitted" writes: **NEVER-adjacent.**
  Display + draft + official-link handoff only.
- Community matching, ticket wallet, social-video lookup, native geofencing,
  bank transfer: **LATER**, full stop.
- Case-coordinator desk, Docling pipeline, Noon/Amazon L4: **post-contest roadmap.**
- Resident/VIP arc (PLAN items 10–11) and extra service cases (item 11): build
  **after** the visitor redesign hits parity, per the §2 cut order (11 → 10 → 9 → 5 → 4).

The floor that must not be cut (PLAN §2): persistent chat, deterministic
proactive triggers, user-given memory, Talabat-normal list → modal mini-apps,
fixed-order deadline loop, taxi-memory payoff, temporal-profiler honesty tiers,
services surface.

## 2. "Live proof" vs "stage illusion" boundary

### 2.1 I agree with Gemini's single live proof — with one relabelling

Endorse: voice/text intent → Luna structured extraction → user approval card →
pilot merchant inbox dispatch → live chat update. This is the only thing that
proves agency to technical judges.

Correction from code inspection: what exists today is **`live_internal`**, not
`live_authorized`. `apps/api/app/actions.py` implements the deterministic engine
(SQLite drafts, idempotent approval tokens, `UNKNOWN_STATUS` gating) and
`apps/web/service-workflow.js` + `chat.js` wire Luna (`POST /api/luna/turn`,
`luna-client.js` with labelled 15 s fallback to the lab router) — but **no live
provider adapter is registered** and the merchant side is a simulated role.
That is exactly the enhancement review's `live_internal` label, and the stage
script must say so out loud ("Merchant role, simulated — the state machine,
approval binding, and chat update are real"). Claiming a live merchant
integration you do not have is how teams lose technical judges.

### 2.2 How to stage the cinematic moments honestly

- **Taxi lost item:** keep — it is IN scope (PLAN item 8) — but keep PLAN's
  honesty wording: report **prepared, not filed**; item **not recovered**; never a
  recovery probability. `recovery.js` already does this; do not "upgrade" it into
  a fake RTA filing for drama.
- **Geofencing / "landed" triggers:** operator-fired `Demo trigger` with the pill
  visible (CLAUDE.md rule 8; ARCHITECTURE §7). Never claim background PWA
  geofencing.
- **Fine appeal:** do not put it in the 4-minute cut (see D05). If the founder
  insists on the emotional button, it is a clearly labelled 15-second epilogue
  card ("Concept — simulated authority reply"), never a status update, and it
  must not consume rehearsal time owed to the laundry loop.
- **General rule:** one truth label per scene (`live_internal` vs
  `simulated_external` vs `future_concept`, enhancement review §11), stated in
  the pitch and the judge Q&A sheet — not buried in a log.

## 3. Arbitration on D01, D02, D05, D07

- **D01 (core agent proof): A — pilot merchant inbox dispatch.** Agree with both
  reviews. B (recommendations only) proves no agency; C (government outcome)
  depends on access you do not have; D (general browser agent) is fragile on
  stage and collides with the §7.8 agentic-execution gate (registered capability
  + approval + provider evidence, no fake Submit buttons). Concretely: Luna
  `service_offers` → `service_comparison` rows → mini-app → `action_approval`
  (exact fields, fixed total) → `actions.py` dispatch → merchant accept →
  `action_status` in chat. The deadline-conflict branch (ready 10:00 vs 09:00
  deadline → earlier slot → 08:30 confirm) is the agency moment, not the tap.
- **D02 (audio on stage): push-to-talk (B), with C's wake-phrase only as garnish.**
  Agree with Gemini. Auditorium ASR is the top live-demo killer; a prominent mic
  button + instant transcription + typed fallback always works. Rehearse the
  voice variation that proves the loop is not canned (a novel phrasing of the
  laundry ask), but never gate the 4 minutes on wake-word detection.
- **D05 (fine appeal): remove from the contest cut; optional labelled epilogue.**
  This is my one deliberate split from Gemini's "climax only (simulated)". The
  locked PLAN arc already has a climax — the taxi-memory payoff, which is in
  scope, evidenced (RTA 104k+ lost items), and honest. A simulated government
  decision as the emotional peak invites the exact judge question you cannot
  afford ("so your agent appeals fines? show the filing receipt"), and it trains
  the audience to remember the one thing the product must never claim. Keep the
  fine as a static concept card for vision decks, out of the timed rehearsal.
- **D07 (Google budget): A — Places/Routes first.** Agree. It is the only Google
  spend that is visible on stage (real shortlist + ETAs with attribution). Keep
  the enhancement review's cautions as work items: verify the $300 trial's
  actual billing account/expiry/coverage before spending; no permanent Places
  cache (policy); field masks drive the bill; Gemini grounding is a separate
  budget line, not a substitute for discovery.

## 4. Concrete next sprints (from the actual code to a rehearsal-ready 4 minutes)

**Sprint 0 — truth reset (half day).**
1. Fix `docs/handoff.md` §2–3: it still describes `demo/lab/` paths and claims
   "40/40 + 100/100 green." Frontend suites pass here; the backend suite does
   not run green in this sandbox (14 failed on socket `PermissionError`
   `WinError 10013` — TestClient bind blocked, looks environmental, not logic).
   Re-run `pytest -q` outside the sandbox and record the real number; do not
   rehearse on a false green.
2. Re-anchor `PLAN.md` §4's one carried item: verify deadline/artifacts/rubric/IP
   on the official portal only, then set dates. Everything else in Phase 0 is done.

**Sprint 1 — close the live-internal loop (the proof).**
3. Luna → approval: `service_offers` at confidence ≥ 0.6 maps to
   `SERVICE_GROUPS` rows (`offers.js`) and opens the row's own modal mini-app
   (`sandbox="allow-scripts"`, no `allow-same-origin`); the host — never the
   widget — rebuilds items/totals from its price table and emits
   `action_approval` with `shares[]`, fixed total, recipient, effect.
4. Approval → merchant: single tap dispatches through `actions.py` (idempotency
   key; double-tap = one order); the backstage/merchant view shows accept /
   decline / mark-ready; each transition appends to the chat as `action_status`
   in < 1 s with `provider_reference` or `UNKNOWN_STATUS` — never an invented
   success.
5. Failure paths rehearsed, not just happy path: merchant decline, no-ack
   ("Waiting for merchant"), adapter error → `UNKNOWN_STATUS`, duplicate submit.

**Sprint 2 — finish the arc branches (the story).**
6. Deadline-conflict branch: ready-time 10:00 vs 09:00 deadline → flag → ask
   earlier → 08:30 confirm, price unchanged (no quote vocabulary anywhere; audit
   with `rg "quote\.|QUOTED|QUOTE_ACCEPTED"`).
7. Time-aware ride reasoning (00:40 → no Metro → taxi + reason) and taxi-memory
   save (plate/receipt photo, roof colour, route, start time, "You told me").
8. Recovery sheets per PLAN §7.5.3: driver detail + RTA report sheets, card/cash
   paths ending at `READY` or `PREPARED_NOT_FILED`, pre-filled only from
   user-given facts.

**Sprint 3 — reference parity + rehearsal.**
9. Screenshot each `design/references/` screen at 390 px against its §6.3 row
   (Services top from `01-home.png`, approval/events, lost-item, merchant
   onboarding, backstage ≥ 1100 px); fix copy density per §7.5 before calling
   any surface done.
10. Lock the PLAN §3 script to ≤ 4:00, rehearse 10×, record the fallback video,
    keep the compact backstage ("Trip details saved / Sharing approved /
    Merchant accepted / Ready confirmed") + "Scripted demo" label + console log
    for judge Q&A.

**Explicit non-goals for these sprints:** fine filing, Gmail watcher, community,
Docling, case desk, Noon/Amazon checkout, geofencing, Resident/VIP — all stay
out until the cut above is rehearsal-ready.
