# Services list (cases)

Menu for picking the next case **after the January submission** (cases are frozen until then, `PLAN.md`). New ideas: follow [`intake.md`](intake.md). Cases are ~1% of the app; the generic engine (category registry, Services surface, profile) covers the rest. A case earns an entry only for a new pattern, rule, data source or demo moment.

**Status flow:** `idea → picked → built → in review → accepted`

**Shared rules:** fixed published prices only (no quotes, bids or negotiation) · one approval before anything leaves the phone · status words only on a merchant/provider event · fixture prices say `(demo)`; live data (real shops, products, prices) shows its source and time · generated images say "AI preview"; try-on only with the user's own photo, 18+ · Google attribution on Places data · hypotheses only re-rank, with a "Because…" chip.

## Index

| ID | Case | Status |
|---|---|---|
| C1 | Maid hire with visa (bundle) | idea |
| C2 | Clothing: facet browse + Try It On | idea |
| C3 | Barber | idea |
| C4 | Laundry with a deadline | built (live loop: approval → merchant inbox → deadline) |
| C5 | DXB arrival guide + ride | built (reference-image parity pending) |
| C6 | Lost item in a taxi | built (contest form: prefilled report + official handoff, not recovered) |
| C7 | Car licence renewal (Resident arc) | idea · LATER for January |
| C8 | Fix it / AC / renovation | idea |
| C9 | Community + shopping rows; interest-based event discovery | v1 only (old `build` branch); event discovery idea · needs plan change |
| C10 | Merchant joins from a price-list photo | deferred (May-final candidate) |
| C11 | Share a video → map | idea |
| C12 | Pets | idea |
| C13 | Food: share or ask → the right kind of answer | idea · needs plan change |
| C14 | Visitor arrival via sponsored airport Wi-Fi | built |
| C15 | Temporal shopping and celebrations | idea · needs plan change |

## Pattern library

Cases are composed from these. A new pattern gets a name in its case. If it needs backend work, the case is flagged **needs plan change**.

| Pattern | What it is |
|---|---|
| `lanes` | Parallel agent lanes → merged total |
| `facets` | Browse by attributes; the shop is only a badge |
| `nearby-rows` | Closest + ★ + price-from + turnaround |
| `map-browse` | Category menu + glyph pins + bottom sheet (the Services surface) |
| `tryon` | Photo → AI preview (Nano Banana via WaveSpeed) |
| `holo-choice` | Holographic finishes: best price (Foil) / fastest (Polished Aluminum) |
| `deadline-check` | Ready-date vs the user's deadline, misses flagged |
| `add-ons` | Fixed-price extras that roll the total |
| `published-offer` | A merchant-published promotion, auto-applied |
| `book-slot` | Slot request → merchant confirms → Booked |
| `route` | Map card + "Open in Maps" handoff, ETA as an estimate |
| `rate-after` | Rating prompt after the "Completed" event (outbox, once) |
| `video-ingest` | Link / upload / iOS Shortcut → frames + transcript → structured extraction |
| `approval` | Single approval card listing exactly what is shared |
| `events` | Provider-confirmed status updates |
| `order` | `order.request` at the published price via the merchant's mini-app |
| `sign-in` | Partner sign-in inside the mini-app |
| `bundle` | One ask spanning several cases/categories, sequenced against one deadline/route |
| `intent-mix` | One input → several answer *types*, ordered by profile hypotheses, each with a "Because…" chip |
| `context-focus` | Selected entity/card/fragment + active task/plan + relevant user context accompany a turn; never treated as execution authority |
| `sponsored-result` | Explicitly labelled paid placement matched to the current task and confirmed preferences, alongside organic choices |
| `temporal-suggestion` | Date-relevant suggestions from user-given milestones; proactive delivery only with consent through the outbox |
| `event-discovery` | Interest + area + future date → sourced event options; ticket availability checked separately |
| `handoff` | Open a third-party app/site at the right screen; nothing submitted on the user's behalf |
| `guide`, `recovery`, `onboarding` | Legacy one-offs (C5, C6, C10) |

---

## C1 · Maid hire with visa
status: idea · refs `service/maid/` · scene `?scene=C1`

**Ask:** "I need a new maid with visa, before 1 Nov."
Lanes Maid · Office · Visa fan out (ThinkingOrb, BorderBeam, pipeline sheet). The lane pills gooey-merge into the odometer total, and every delta shows its reason ("published Filipina fee").

| Step | Choice (published fixed prices, AED, demo) | Total | vs 1 Nov |
|---|---|---|---|
| 0 | Auto cheapest: Maid Match (demo) any nationality 3,950 + Palm Typing (demo) visa pack 3,150 + insurance 343 | **7,443** | ~8 Nov, misses |
| 1 | Indian / Filipina / Ethiopian / Kenyan → **Filipina** at Maid Match 5,900 (+1,950). **Approve** (shares household size, area, start date, preferences) | 9,393 | misses |
| 2 | Offices: Home Ally 5,600 · 30 d · Maid Match 5,900 · 21 d · **Nest Helpers 6,400 · 9 d** (Polished Aluminum "fastest") | 9,893 | 27 Oct ✓ |
| 3 | Visa offices: Quick Visa Hub 3,600 · 3 d · Palm Typing 3,150 · 5 d · **Marina Typing 2,890 · 6 d** (Foil "best price") | 9,633 | 28 Oct ✓ |
| 4… | Insurance (Shield Motor / Gulf Assure / Palm Cover, demo), medical slot, start date → per-provider approval → events → calendar | | |

- Status only from events ("Office accepted", "Entry permit issued"). Dubai-io never submits to GDRFA/MOHRE; the official portal is a handoff link.
- Salary: "set by contract, not in this total".
- Candidate portraits: stock, labelled "Demo profile · stock photo". These are the first slots to swap for WaveSpeed-generated fictional faces.
- **Profile:** reads household, area, budget band. Teaches the hypothesis "minimise price subject to deadline" (steps 2–3), raised as an "I noticed" chip after step 3.
- **Checks:** totals 7,443 → 9,393 → 9,893 → 9,633; deadline flags correct; no status word without an event.

## C2 · Clothing: facet browse + Try It On
status: idea · refs `shops/cloth/` (`try it on - lens.jpg`) · scene `?scene=C2`

**Ask:** "I need a summer outfit."
- Marketplace lanes. Real marketplaces and products are fine on screen with source and time (e.g. Amazon.ae via SerpAPI).
- Facets **Gender · Age · Item** over one merged photo-tile set (cut-out on a shader swatch, price (demo), ★, delivery time, shop badge). "By shop" toggle. Fitting-tray pill (gooey merge). Gender is never inferred: asked once, then confirmed.
- Try It On sheet per the ref, restyled to our tokens: photo centred, items as bobbing stickers, hints "Full body · Front facing · Bright", **Try It On** / "Choose a different photo".
- Approval first: "Your photo + N item images → Nano Banana via WaveSpeed. Not shared with shops. Deleted after the preview unless you keep it."
- `img-fx` `pixels-organic` reveal, captioned "AI preview · results may be unexpected · not a size guide". Share / Add to bag → that shop's mini-app `order.request`.
- Own photo only, 18+ confirm; kids' items browse-only. "Keep my photo?" → stored only on Yes.
- Lab: scripted before/after pair (founder supplies the real pair). Live: `/tryon` mode `outfit` (server-side key); a failure shows "Couldn't make a preview".
- **Profile:** reads confirmed sizes and style. Teaches style/colour hypotheses from views and choices.

## C3 · Barber
status: idea · refs `service/barber/` · scene `?scene=C3`

**Ask:** "I need a haircut."

| Step | On screen | Rule |
|---|---|---|
| 1 Near you | Fade Factory (demo) ★ 4.8 (312) · 0.6 km · Al Barsha Gents ★ 4.6 · 1.1 km · Marina Blade ★ 4.7 · 2.0 km, "· Google (demo)" | Places rating with attribution; distance is an estimate |
| 2 Style | App catalogue: Skin fade 70 · Classic taper 60 · Textured crop 80 (this shop's prices) | Images "Illustrative" |
| 3 See it on you | `/tryon` mode `hair`, still photo, same approval | **No live AR** (LATER) |
| 4 Add-ons | Hair dye 90 · Beard trim & shape 40 · Beard dye 50 | Fixed published prices |
| 5 Offer | Published "Cut + beard bundle" 110 → **90 (demo)** | No "ask for discount" button |
| 6 Book | Slot → single approval (name, phone, services, slot) → merchant confirms → **Booked** → calendar | Booked only on the merchant event |
| 7 Route | Shop pin, consented approximate user dot, "Open in Maps", ETA estimate | No in-app navigation |
| 8 Rate | After "Completed": outbox prompt, once, quiet hours | Stored in Dubai-io; not posted to Google |

- **Profile:** reads distance tolerance, min ★. Teaches the haircut routine. After ≥ 3 visits: "I noticed you go about every 4 weeks — remind you?" A reminder exists only after Yes.
- **Checks:** total 70 → +40 → bundle 90; Booked only after the event; rating prompt fires once.

## C7 · Car licence renewal
status: idea · spec `../redesign.md` R2–R5

## C8 · Fix it / AC / renovation
status: idea · spec `../redesign.md` R6

## C11 · Share a video → map
status: idea · refs `shops/coffee/` (`coffee.jpg`) + `Pulled data services for agents - app.jpg` (logic only; its colour scheme is rejected) · scene `?scene=C11`

- **Input** (iOS PWAs have no share target): paste a link into the AI search · upload from the camera roll · iOS Shortcut "Send to Dubai-io" in the share sheet → `/share?url=…`. Native share extension later (Swift).
- **Pipeline sheet**, hh:mm:ss per step: Fetching video → Reading frames → Listening → Finding places → Building map.
  - `POST /ingest/video`: a link → oEmbed caption + thumbnail only (no TikTok/Instagram media download). An upload → ffmpeg keyframes (8–12) + faster-whisper (EN/AR) → Claude (frames + transcript + caption) → `{items_sold[], place_names[], area_hints[], prices_mentioned[] (estimate), category}` → Places Text Search (New).
- **Map:** Google Maps JS styled to our tokens. Pins say "From your video"; the user dot only if consented and approximate. A pin opens a photo tile: ★ · Google, area, "seen at 0:14" with the frame. Actions: shop mini-app (partners) · Navigate handoff · Save. Weak matches show 2–3 candidates with "may not match".
- Lab: scripted coffee clip → scripted extraction → stylised map with pins. Live keys server-side in 1b.
- **Profile:** teaches interest and area hypotheses (e.g. "into specialty coffee, Al Quoz"), raised after 2 related shares.

## C12 · Pets
status: idea · refs `service/pets.jpg` (logic only; the ref's real clinic name is not reused) · scene `?scene=C12`

The pets ref also defines the universal **Services surface** (already built). This case is the pets-specific part.
- **Ask** (a bundle): "My dog needs grooming and a check-up this week."
- **Map-first browse:** glass category menu All · Vet · 24h · Pet shop · Boarding · Grooming · Photo (one SVG icon set). Pins distinguished by glyph, colours from tokens. Places (attribution) + partner merchants.
- **Bottom sheet:** name, category chip, address, distance (estimate), **"Partner (demo)" chip, never a verified tick**. Directions (handoff) · Call (`tel:`) · **Book** (partners only → mini-app; e.g. "Bath + trim, medium dog · AED 180 (demo)", "Wellness check · AED 250 (demo)").
- **Bundle:** two slot requests sequenced within "this week" with a travel-time estimate between them; one approval per provider; each confirms separately; the calendar shows both.
- **Urgency:** 24h is display-and-call only. No AI medical or triage advice: "If it's urgent, call a 24h vet now."
- **Profile:** pet facts (name, species, breed, age band, vaccination due) stored only when told. Teaches a grooming-cadence routine, raised after ≥ 3 visits.

## C13 · Food: share or ask → the right kind of answer
status: idea · **needs plan change** · refs `shops/restaurants/` (`food.jpg`; logic only) · scene `?scene=C13`

- **Input:** a dish photo · a food video (same routes as C11) · a typed ask ("craving koshari").
- **Understanding:** frames/transcript or image → Claude → `{dish, cuisine, key_ingredients[], place_hint?}`, shown as "Looks like **koshari**" with *Not this* (a guess, never asserted).
- **Answer types**, one coverflow card each:
  1. **Make it:** recipe with source link, time, difficulty ("AI-adapted" when adapted).
  2. **Watch it:** cooking videos → handoff to the video site.
  3. **Go there:** nearby restaurants (★ · Google, distance estimate, open now, price-from), map toggle.
  4. **Get it delivered:** delivery apps (real names fine, opened as a handoff), ETA estimate, **published** offer only ("15% off first order · as of 13 Oct (demo)") → handoff. Partner restaurants open their own mini-app.
- **`intent-mix`, the counter-intuitive part:** the same photo is ordered differently by the temporal profile, with a "Because…" chip on each card.
  - Fri 13:00 → **Go there** first ("Because: you eat out on Friday lunch").
  - Tue 22:40 → **Get it delivered** first ("Because: late on weeknights you order in").
  - After 3 saved recipes → **Make it** first.
- **Profile:** reads area, cuisine likes, and the conditional fact "cook / order / eat out by time-of-week". Diet, allergies and halal only if told. Teaches cuisine preference and the time-conditioned policy.
- **Rules touched:** offers merchant-published with `as_of`; no health advice in recipes beyond what the user told (e.g. allergy filter); videos and apps are handoffs.
- **Needs plan change:** recipe/video search in 1b (Claude `web_search` server tool with citations + a video-search API key, server-side). Founder to agree before it enters `PLAN.md`.
- **Open questions:** (1) order in-app for partner restaurants only? Default yes, others hand off. (2) Creator rail from the ref? Default out.
- Lab: scripted photo → "Looks like koshari" → 4 cards, with a time toggle (Fri 13:00 / Tue 22:40) that reorders them live.

### C13 extension — relevant sponsored restaurants (21 Oct)

Founder request, verbatim:
> sponsered restaurants if user is in 'restaurant' thread as he clicked on food in the maps, based on user recommendations, for example seafood if google analytics about that user signed in with his g account mentioned he is more interested in {location:restaurant, dish:fish}

- **Status:** idea · needs plan change; extends `shops/restaurants/`, not a separate case. Patterns: `context-focus`, `sponsored-result`, `intent-mix`.
- Entering Food/restaurant context makes restaurant suggestions eligible. If the user told/confirmed “I like seafood”, rank relevant seafood places within the requested area/budget. Paid placement always says **Sponsored** and explains its relevance; it must not masquerade as an organic recommendation or suppress all organic results. No invented live sponsors: fixture placements say **Sponsored demo**.
- **Data correction:** Google sign-in/Analytics cannot supply a private per-user dish-interest record. Use confirmed Dubai-io preferences and explicitly connected data. Do not send profile, calendar or browsing history to advertisers. Dismiss and mute options persist; commercial placement cannot override a stated requirement.
- **Ask/actions:** “Find seafood for dinner near my hotel.” Discovery only until a real adapter exists; provider confirms availability, fixed prices and any booking. Only the fields on an approval card are shared. These are the default assumptions.
- **Profile reads/teaches:** reads confirmed cuisine/dish preferences; choices may teach a visible hypothesis. Dietary/health/religious restrictions are supplied by the user, never inferred.
- **Checks:** sponsor label and reason visible; irrelevant sponsor excluded; organic choices remain; dismiss persists; no provider action without the approved path.

### C9 extension — events matched to interests (21 Oct)

Founder request, verbatim:
> events happening near me: user like festivals? show global village opening, likes parties? show a tour by singer. like a specific singer? show he is visiting dubai next week from news api

- **Status:** idea · needs plan change; extends the existing C9 event/community direction. Discovery and planning are separate from community posting, ticket wallets and ticket purchasing. Patterns: `event-discovery`, `context-focus`, `temporal-suggestion`, `handoff`.
- **Ask:** “What is happening near me next week that I would enjoy?” Match a confirmed festival/music/artist interest against an explicit area (or consented location), dates, schedule and budget. Examples: Global Village's next officially announced season opening; an artist's announced Dubai show; a food festival during a visitor's stay. These are examples, not assertions of current events.
- **Sources:** existing Tavily/SerpAPI can discover news and official event pages without a new NewsAPI dependency. Verify venue, future event date and cancellation status with the organizer/venue where available. Show source + checked time; distinguish an article's publication date from the event date. Ticket stock and prices require ticket-provider evidence, otherwise official handoff.
- **Profile reads/teaches:** reads confirmed artists, genres and festival preferences. Ordinary browsing can suggest a visible hypothesis, not cause unsolicited reminders. Avoid inferring sensitive affiliations from event choices.
- **Sharing/status:** discovery shares no personal data with the venue; a later booking uses its own approval. Only the provider can confirm a booking or ticket. Remind/follow-artist notifications require consent, dedupe and quiet hours.
- **Checks:** past/cancelled events excluded; two events with similar names not merged; relevant dates/area shown; no “tickets available” from news alone; no unconsented proactive messages.

## C15 · Temporal shopping and celebrations
status: idea · **needs plan change** · refs `shops/gifts/`, `shops/books/`, existing `shops/restaurants/` (proposed locations; no media folders created) · scene `?scene=C15` · patterns `context-focus`, `temporal-suggestion`, `intent-mix`, `handoff`

Founder request, verbatim:
> temporal suggestions, for example user has birthday? show birthday cake shops or places to celebrate. school? show book shops. be creative

**Ask:** “Help me prepare for what is coming up.” Default: in-session suggestions; proactive delivery is a separate opt-in. Dates/occasions come from what the user tells us or an explicitly authorized calendar. Never infer parenthood, a child's school, age or a birthday from unrelated browsing.

| Trigger supplied by user | Useful suggestion | Timing/context |
|---|---|---|
| Birthday coming up | Cake pickup/delivery, dinner, activity, a gift within the stated budget | Account for the cake shop's published lead time and the party date |
| School term starts | Bookshops, required supplies, uniform services, transport planning | Use a user-supplied list and term date; ask for missing details |
| Friends/family visiting | Airport pickup reminder, rooms, meals and interests-based outings | Fit around confirmed arrival/departure and existing commitments |
| Anniversary | Restaurant, flowers, a shared activity | Preserve existing bookings; use stated preferences and budget |
| Conference or important meeting | Shirt pressing, charger/adapter, route, breakfast | Work backwards from the stated deadline using the existing laundry flow |
| Returning from travel | Laundry, groceries and a home service if requested | Suggest a convenient window; no order until approval |

- **Profile reads/teaches:** confirmed milestones/dates and preferences; editable, forgettable facts. An occasion is not a licence to infer sensitive traits. Explain “Your birthday is next week—you told me” or “From the calendar you connected”.
- **Flow:** relevant occasion → 2–4 useful cards → source/lead time shown → fit into the draft plan → provider handoff or an approved registered action. Fixed published amounts only; prices and promotional fixtures say `(demo)`.
- **Media:** reuse existing food, book/product and service imagery where relevant; event/occasion art is illustrative, never proof of availability.
- **Sharing/status:** no milestone/profile shared with a shop during discovery; only explicit order fields after approval. Provider confirms stock/slot/order. No fake reservation or purchase.
- **Checks:** incorrect date can be edited; no sensitive inference; local Dubai dates; lead times respected; duplicates suppressed; paid options labelled; reminders withdrawn when consent is revoked.
- **Assumptions:** discovery and draft planning first; payments/ticket purchases remain deferred. Calendar OAuth, structured plan state, sponsorship inventory and temporal suggestion rules are new work, not completed features. Technical context requirements: `../references/assistant-context.md`.

| Review date | Entry | Outcome |
|---|---|---|
| 21 Oct 2026 | C13 sponsorship, C9 event discovery, C15 temporal suggestions | Founder ideas captured; current contest implementation scope unchanged; context contract and data-source constraints documented |
