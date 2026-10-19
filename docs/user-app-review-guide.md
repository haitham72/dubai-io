# User app review guide

One pass, about 20 minutes. Tick each box; write anything off in `docs/handoff.md` → Review notes.

**Setup:** server running (`docs/handoff.md` → Run). Phone: `http://<pc-ip>:8000/#demo.wifi`. Second device (or tab): `http://<pc-ip>:8000/merchant.html`, sign in as **Marina Express Laundry** with the PIN in `apps/api/data/merchant.pin`.

## A. Stage script (follows `PLAN.md` §3)

- [ ] **Arrival:** Wi-Fi sign-in → install → card intro. "Scripted demo" label visible at the top.
- [ ] **Guide:** *Guide me to arrivals* → Terminal 3 → steps advance only when you tap; "I'm lost" offers landmarks; belt saved only if you type it.
- [ ] **Ride:** tap *Try it at 00:40* → "Metro has stopped, so a taxi"; ETA says `Estimate · Google`.
- [ ] **Taxi memory:** choose taxi → type plate, roof colour, hotel area → chat shows "You told me".
- [ ] **Ask:** "I need a shirt pressed by 9 tomorrow" → badge says `LangGraph` (not `Lab router`); laundries listed closest first, prices marked `(demo)`.
- [ ] **Mini-app:** open Marina Express → it loads (separate origin) → *Send order request*.
- [ ] **Approval:** one card: shop, items, total, area and deadline as "You told me", plus "Never shared". Approve once.
- [ ] **Waiting:** chat card says `SUBMITTED` / "Waiting for the merchant" and nothing changes on its own.
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

- [ ] Notes written in `docs/handoff.md`.
- [ ] Decide: purchasing/payments (`PLAN.md` §5), keys for flight status / Google Maps JS (`docs/references/api-catalog.md`).
