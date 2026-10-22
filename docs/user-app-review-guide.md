# User app review guide

One pass, about 20 minutes. Tick each box; write anything off in `handoff.md` → Review notes. Read its runtime checkpoint first: the 21 Oct preview used local Supabase with imported SQLite review records; the 22 Oct write stall must be resolved before adopting the latest checkpoint. Original Postgres recovery remains separate and unresolved.

**Setup:** server running (`handoff.md` → Run). Phone: `http://<pc-ip>:8000/#demo.wifi`. Second device (or tab): `http://<pc-ip>:8000/merchant.html`, sign in as **Marina Express Laundry** with the PIN in the active data directory's `merchant.pin` (`output/review-data` for the current preview).

## Current 22 Oct preview and task checks

Open `http://localhost:8010/index.html#home` and refresh for new modules. Home keeps its photo carousel; swipe up on the Today handle, tap it, or focus it and press Enter/ArrowUp. The bottom edge/tab bar never opens Today. Wi-Fi/gradient replay: `#demo.wifi`; direct sheet: `#today`. Separate widgets use 8011; ignored SQLite data is `output/assistant-preview`, not Supabase. Port 8000 instructions below describe the historical baseline. Google map/Places and a LangGraph greeting were separately verified; OAuth/Gmail are not connected.

- Create a manual task, edit its next step, pause/resume, report a result, cancel another task and reload. Check All tasks and activity; returned results must say you reported them.
- Check saved-task counts against All tasks, due ordering/overdue/within-24h cues in Dubai time, paused disclosure, and hidden empty Needs you/Running. Manual tasks belong On your list; no real decision/worker exists yet.
- Saving must not imply an automatic check, email contact, authority response or booking. Task capture/detail explicitly says automatic checks and sending are inactive. Next step starts empty; the example must not become saved text.
- Pause/Resume/Edit/Done should focus the state chip and announce the update; Cancel asks inline and Escape keeps the task. Refresh must keep the current Today content. Human labels replace technical status codes.
- Stale edits should require reloading, without restoring a cancelled task. Review empty/error/retry, keyboard/Back and long content at phone size.
- Browser verification passed at 390x844 and 428x926, normal/reduced motion, including keyboard, gesture scope and visible computed no-shadow checks. **Physical iPhone gestures and screen-reader announcements remain unverified**; check these on the founder's phone before device acceptance.
- Keep-track bridge, taxi staged responses, Reading, cron/worker and Gmail are outside this pass. The image/provenance audit remains pending despite restoring existing photos.
- New external review: use `docs/references/assistant-design-interaction-review-prompt.md` and all Duet frames; preserve the earlier critique and write a separate report.

## A. Stage script (follows `PLAN.md` §3)

- [ ] **Arrival:** Wi-Fi sign-in → install → card intro. "Scripted demo" label visible at the top.
- [ ] **Guide:** *Guide me to arrivals* → Terminal 3 → steps advance only when you tap; "I'm lost" offers landmarks; belt saved only if you type it.
- [ ] **Ride:** tap *Try it at 00:40* → "Metro has stopped, so a taxi"; ETA says `Estimate · Google`.
- [ ] **Taxi memory:** choose taxi → type plate, roof colour, hotel area → chat shows "You told me".
- [ ] **Ask:** "I need a shirt pressed by 9 tomorrow" → badge says `LangGraph` (not `Lab router`); laundries listed closest first, prices marked `(demo)`.
- [ ] **Mini-app:** open Marina Express → it loads (separate origin) → *Send order request*.
- [ ] **Approval:** one card: shop, items, total, area and deadline as "You told me", plus "Never shared". Approve once.
- [ ] **Waiting:** chat card says "Waiting for the shop" (technical `SUBMITTED` stays in data) and nothing changes on its own.
- [ ] **Merchant:** order appears on the second device → accept with ready time **Tomorrow 10:00**.
- [ ] **Deadline:** phone shows "misses your Tomorrow 09:00 deadline" → *Ask for Tomorrow 08:30, same price* → merchant confirms 08:30 → phone: "meets your deadline. Confirmed by the shop, not by me." Price unchanged.
- [ ] **Proactive:** tap *Remind me before it's ready* → merchant page → *fast forward reminders* → phone gets one message labelled **Demo trigger**. Press it again: no second message.
- [ ] **Payoff:** "I left my bag in the taxi!" → saved plate/roof/route shown → *Prepare RTA report* asks only for the bag description → ends "Prepared, not filed".
- [ ] **Timing:** whole run under 4:00.

## B. Honesty checks

- [ ] No screen says Confirmed / Booked / Paid / Filed without a merchant tap behind it.
- [ ] Every price and rating shows `(demo)`, `Estimate · Google` or a source.
- [ ] Reload the phone mid-order: the order card comes back with the same status.
- [ ] Merchant page shows the approved fields only (no name, phone or profile).
- [ ] Decline an order on the merchant page → phone shows "Merchant declined".

## C. Luna

- [ ] "Is my shirt ready?" → shows the real order card (status from the shop, not from Luna).
- [ ] "Is the Dubai Frame open on Mondays?" → short answer with numbered, clickable sources.
- [ ] "Coffee near me" → real Google places with photos on a Google map; tap one → Directions / Call / Website work.
- [ ] "Find me shampoo" → 10 Amazon.ae cards with images, AED prices, ratings; tapping one opens Amazon.
- [ ] "Apple stock price?" → price with a time and "Finnhub".
- [ ] "How much is a Salik fine?" → refuses and points to the official portal.
- [ ] Repeat a fact you already gave → no duplicate "You told me" line.

## D. Profile (Me → You, over time)

- [ ] After an order, a matching "I noticed" item shows its evidence ("on this device"); demo items say "demo history".
- [ ] *Forget* one → reload → it stays gone. *Confirm* one → it moves to "You told me / You confirmed".

## E. Look and feel (iPhone, 390 px)

- [ ] No shadows anywhere; AI text plain, your messages in a tinted box, choices in white rounded boxes.
- [ ] Onboarding cards move slowly and smoothly; nothing overlaps the notch or home bar.
- [ ] Screens match `design/references/` closely enough (note gaps per screen).

## F. After the review

- [ ] Notes written in `handoff.md`.
- [ ] Decide: purchasing/payments (`PLAN.md` §5), keys for flight status / Google Maps JS (`docs/references/api-catalog.md`).

## Current recommender/context checks

- [ ] Explore two distinct live food places; re-enter Home and inspect any explained category ranking. Current maps keep closest ordering. Do not mistake broad category adaptation for complete restaurant-item personalization.
- [ ] Me -> You, over time -> Live interests: Confirm, Edit, Not true, Forget and Resume persist. Edit requires explicit Save and removes old evidence. This visit / Across visits show dated evidence, decay and expiry; failed saves remain retryable.
- [ ] Open a place -> Ask about this place -> chat shows the selected place and one composer; Clear removes the context. A selected listing is not a confirmed fact or live ticket inventory.
- [ ] Forget a saved detail, then ask again in the old thread: old server model checkpoints must not restore the detail. Old browser chat display is separate from model memory.

Detailed future acceptance tasks are in implementation-plan.md; native device testing stays on the Mac under ios-swift. Google OAuth is deferred for the single tester.

- [ ] REC-02: Edit a learned topic to another reviewed topic, Cancel once, then Save. Reload: old topic stays paused; replacement says You confirmed and has no transplanted evidence. Not true/Forget remove the saved preference; Resume starts clean. Repeated taps/reclassifications on one option do not inflate distinct-option counts or resurrect an old Home reason.

## 22 Oct recommender checkpoint

This checkpoint is on `redesign`; native `ios-swift` remains parked. REC-03A/B code is SQLite/browser verified, with local Supabase write health and PostgreSQL verification/reconciliation still outstanding. Do not describe the isolated browser QA server as a deployed Supabase app.

- In Maps, select Food -> Seafood and open two different places. Return to All food or refresh: seafood places in the returned provider batch can rise with a visible "this visit" reason. A batch with no seafood candidates cannot invent them.
- Open/back should preserve the current list. Closest must preserve distance ordering; Open now must exclude closed and unknown opening hours. Radius uses labelled straight-line distance.
- Hide one place for seven days without implying a dislike of every restaurant. In Me -> You, over time, distinguish this-visit evidence from across-visit qualification, and verify Forget removes the corresponding reasons.
- One visit must not establish a lasting inferred preference. Long-term influence requires two distinct options across visits at least six hours apart. Confirmed preferences remain explicit and editable.
- Exact restaurant spend, arbitrary typed dates/budgets, future ticket stock, service/product eligibility and actual recommendation usefulness are not proven by this checkpoint. These remain in the nested plan.


## Second design review findings to recheck after fixes

The first nine browser scenarios are not a complete UX sign-off. Recheck due ordering/overdue cues, paused visibility, decision-versus-note labels, focus retention, refresh flash, accidental cancellation, default next-step text, photo/gradient/recommendation continuity, visitor copy, report/order task links and receipt/cash trip confirmation. All are findings or proposed corrections in `docs/references/assistant-design-interaction-review.md`; none is marked fixed by the review assessment. Duet is interaction reference material, not proof of implementation.
