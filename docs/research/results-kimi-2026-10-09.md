# Research results: Dubai visitor needs
**Tool:** Kimi (web search, Oct 9 2026 session) — replaces the planned Gemini/DeepSeek run
**Date:** 2026-10-09
**Prompt source:** `docs/research/research-prompt.md` (sections A–H followed)
**Note:** Reddit/TripAdvisor content was reachable only via search snippets, not full-thread browsing. FlyerTalk returned nothing. Frequencies are "independent reports found in this search," not population rates.

---

## 1. Executive summary (most decision-relevant first)

1. **The hotel-concierge gap is real and is the product's core opportunity.** Hotel laundry runs ~US$5–10 per item (a bag = $100–150) with typically next-day turnaround, while Dubai laundries charge AED 3–7 to press a shirt with 24h or same-day express and WhatsApp booking. Guests in serviced apartments / mid-range / Airbnb have no concierge at all and self-serve via Google Maps + WhatsApp. Concierge "solves" deadline tasks only for luxury guests, only at 5–10x price, and rarely same-night.
2. **DubaiNow — the government's flagship AI-assisted app — does essentially nothing for visitors.** It is built on UAE Pass/Emirates ID, targets residents (370 services, 2.2m users), and has no arrival guidance, laundry, or lost-item flows for tourists. Big whitespace for a visitor companion.
3. **Lost items in taxis are extremely common (104,162 items in 2025, per RTA) and Dubai's recovery system is genuinely good** (RTA claims "99.9%"; S'hail app + 800 9090; many returns in hours). The visitor pain is not the recovery rate — it is knowing the process at 1am, having the required trip details (plate/roof colour/time/route), the official 3–10 day follow-up window vs a 2–4 night stay, and paying the driver's return meter fare.
4. **Late-night arrival friction is structural:** the Metro stops at midnight (1am Fri), there is no Metro at Terminal 2 (Bus 43 / shuttle needed), taxi ranks surge when multiple long-hauls land together, and the recurring failure modes are a dead phone, hotel booked from the wrong date, and walking out of the wrong terminal.
5. **The "one app" illusion breaks at the lost-item step:** Careem handles lost items for its own rides in-app but redirects Hala/RTA-taxi items to the RTA call centre; Uber only covers its own trips. No single actor follows a visitor through the whole incident.
6. **Car-rental deposits are the highest-cost recurring complaint** — withheld deposits, hidden charges, and ghosted support (multiple Trustpilot reports; even Sixt reviews cite a 6,000 AED deposit taking 2 months). Official recourse: DED complaint.
7. **Medication rules are the highest-consequence surprise:** controlled medicines (codeine, tramadol, benzodiazepines, ADHD stimulants) need prescription + attested report, ≤3 months; CBD/THC is flatly prohibited with prison sentences; a free e-permit (ede.gov.ae, ~1 working day) exists but most travellers don't know about it.
8. **Competitor check (F): no competitor can execute a deadline task end-to-end.** Careem/Uber/talabat/hotel apps each cover fragments (booking, delivery); none orchestrates "shirt pressed by 8am from a local shop + confirm + chase." ChatGPT/Gemini give guidance but can't act, book, verify, or follow through.
9. **Chasing replies / repeating details (D) is real but evidenced indirectly:** non-responsive merchants, ghosted rental support, and "charged, no service, no support" reports (e.g., Careem home cleaning thread). No first-hand study quantifies it; treat as directional.
10. **The contest (H) was announced 7 Oct 2026 — days ago.** Registration closes December 2026; required artifacts = AI-agent prototype + pitch deck + demo video; AED 550k per category (Best Personal AI Agent is one of four) + AED 1m AI Agent of the Year. **Fully commercialised solutions are ineligible** — keep the agent pre-commercial. Detailed judging rubric, IP terms, and final-stage format are not yet published.

---

## 2. Evidence tables

### A. Arrival at DXB (esp. late night)

| Finding | Frequency signal | Consequence | Current workaround | Source (date) |
|---|---|---|---|---|
| Metro stops ~midnight (1am Fri); useless for most after-midnight arrivals | Official fact; echoed in every late-night guide | Taxi rank queues at peak banked landings; no cheap option | Pre-booked chauffeur; taxi queue | dubaiairports.ae (2024); emirateslimo.com (2026-09-30) |
| No Metro at Terminal 2; Bus 43 (~15–18 min) to Airport Free Zone / Al Qiyadah (1.7km) / Abu Hail (2.3km); T2→T1/T3 shuttle ~every 20 min | Multiple forum/social threads asking "is there metro at T2?" | Confusion, unexpected taxi cost, missed connections | Bus 43, shuttle, taxi | reddit r/emirates; tripadvisor; instagram reel (web_search:6#0–8) |
| Metro luggage: max 2 suitcases (large ≤81×58×30cm, small ≤55×38×20cm), dedicated cabin area | Official (RTA via Gulf News) | Families with bags can't realistically use Metro | Taxi/van | gulfnews.com (2025-08-13) |
| Taxis 24/7 at ranks in every terminal; night queues spike when long-hauls bank together | Recurring in guides + Reddit | 20–40 min wait at 1am; surge on ride-hail apps | Pre-booked transfer | emirateslimo.com (2026-09-30) |
| Immigration mostly fast (Smart Gates ~12–15 sec/traveller); queues at peaks | Several Reddit reports | Occasional 30–60 min at peak banks | Smart Gate eligibility | reddit r/dubai; facebook anjanamedia |
| Recurring late-night mistakes: hotel booked from wrong date, wrong terminal exit, dead phone, no child seat at rank | One structured guide listing the same set | Check-in denied at 2am; missed pickup | None (planning gap) | emirateslimo.com (2026-09-30) |
| Terminal 3 has 3 concourses; kerb walk can be long | Official/guide | Confusion at pickup | — | dubaiairports.ae |

### B. Lost items in taxis / ride-hails

| Finding | Frequency signal | Consequence | Current workaround | Source (date) |
|---|---|---|---|---|
| 104,162 items left in Dubai taxis in 2025; >AED 2m cash, ~35,000 electronics, ~3,000 passports/IDs | Official RTA figures | Very high frequency | RTA Lost & Found | timesofindia (2026-01-20) |
| RTA claims "99.9%" recovery; official follow-up window 3–10 days, many returns in hours | Official + several Reddit success reports | High, but window can exceed a short stay | S'hail app / 800 9090 | gulfnews (2024-07-15); reddit r/dubai |
| Required details: trip time, pickup/dropoff route, roof colour, plate number; receipt is best | Official (RTA/Dubai Taxi FAQ) | Visitor rarely has these → report stalls | Hala booking history in Careem shows details | dubaitaxi.ae FAQ; gulfnews (2024-07-15) |
| If found, driver returns item with meter running; finder pays the fare | Official | AED 30–100 unexpected cost | Pay driver | gulfnews (2024-07-15) |
| Careem: own rides → in-app lost item, captain's contact <5 min, delivery AED 59 in UAE; but Hala/RTA taxis → redirected to RTA 800 9090 | Official Careem help | Two different processes in one app | Call RTA | help.careem.com |
| Uber: in-app "Find lost item" → masked call to driver; no liability; return fee varies | Official Uber help | Works only for Uber trips | — | help.uber.com |
| Reddit success stories: item back in ~1 hour when pickup/drop known; AirPods recovered after rider got taxi number from the taxi's Wi-Fi network | ≥3 independent Reddit threads | Relief pattern: details → fast recovery | Taxi Wi-Fi trick | reddit r/dubai (web_search:7#2,#4,#5) |
| Failures exist (item not found / driver unreachable), especially without trip details | ≥2 threads | Lost phone + no local SIM = hardest case | RTA report anyway | reddit r/dubai |

### C. Deadline tasks + hotel concierge

| Finding | Frequency signal | Consequence | Current workaround | Source (date) |
|---|---|---|---|---|
| Hotel laundry ~$5–10/item; a bag ≈ $100–150; dry cleaning $6–8/item | Multiple Reddit/HN threads (general + Dubai) | 5–10x local price | Local laundry | reddit r/travel; HN (web_search:12#0,#3) |
| Local laundry: shirt press AED 3–7, wash+press AED 7–12, suit dry-clean AED 25–60; 24h standard; same-day/express widely offered | 6+ Dubai laundry price lists (2025–26) | Price gap vs hotel | Walk-in / WhatsApp | halagreen, washhouse, swabilaundry, imagelaundry, laundry.ae (2025–26) |
| WhatsApp is the dominant booking channel for independent laundries (booking, updates, payment) | Repeated across provider sites + Reddit | Visitor must find + vet a shop on Google Maps, no aggregation of trust | Laundry apps (WashOn, Laundryheap, Washmen, justclean marketplace) | swabilaundry.ae; lavanderialaundry.com; reddit r/UAE |
| Careem Home Services: laundry daily 9:00–23:30, cleaning, salon; partnered with Justlife | Official Careem | Fragment: booking only, no deadline orchestration | Careem app | careem.com; blog.careem (2025-08-22) |
| Same-day tailors exist (1-hour express +50% at Tailor & Tweak; same-day hemming/zip at Swabi if booked before 10am; The Draper multiple branches) | ≥4 providers + Reddit request threads | Visitor discovery problem | Google Maps / hotel referral | tailorandtweak.com; swabilaundry.ae; thedraper... (web_search:16) |
| Pharmacies: 24/7 outlets with delivery; Aster free same-day delivery; delivery after midnight via Deliveroo/talabat | ≥3 sources | Solved if you know the app | Delivery apps | asterpharmacy.ae; instagram; kindcare |
| Concierge capability concentrated in luxury segment; business travellers under-use it ("I never know what I can ask for") | 1 Reddit luxury thread (Mandarin Oriental Dubai) | Under-use even where it exists | — | reddit r/FATTravel (2026-01-28) |
| Serviced apartments / Airbnb: 24/7 host or property manager sometimes (GuestReady), but no concierge task desk | The Times serviced-apartment guide | No task help at all | Self-serve | thetimes.co.uk (2024) |

### D. Repeating information / chasing replies

| Finding | Frequency signal | Consequence | Current workaround | Source (date) |
|---|---|---|---|---|
| Merchants/providers go silent after payment — car rental deposits, cleaning services | ≥6 Trustpilot reviews + 1 Reddit thread | Money held; time chasing via WhatsApp/calls | DED complaint; Dubai Police e-Crime | trustpilot (2025-11–2026-02); reddit r/dubai |
| Careem home cleaning: "Getting Charged, No Cleaner, No Support!" | 1 detailed Reddit thread | Paid, no service, no reply | Public complaint / chargeback | reddit r/dubai (web_search:11#4) |
| Rental deposit refunds take weeks even with legit brands (Sixt: 2 months for 6,000 AED) | 1 detailed review + sector pattern | Card funds frozen post-trip | None | sixt.com reviews |
| Direct evidence of "repeating details across hotel, apps, merchants" as a named pain | **Not found** — treat as hypothesis | — | — | — |

### E. Top recurring complaints (ranked by frequency × cost)

| Rank | Complaint | Frequency signal | Cost | Source |
|---|---|---|---|---|
| 1 | Car rental deposits / hidden charges / scams | Very high (Trustpilot clusters; DED complaints cited) | AED 1,000–8,000 held or lost | trustpilot; saadatrent (2023) |
| 2 | Items left in taxis | Very high (104k/yr official) | Moderate; mostly recovered | RTA via timesofindia (2026-01) |
| 3 | Late-night arrival transport friction | High in forums/guides | Time/stress | section A sources |
| 4 | Medication rules / controlled meds / CBD | Moderate frequency, **severe** consequence | Arrest, fines AED 20k–100k+, prison | uaeinform (2026-09); UAE embassy; Aetna (2025-12) |
| 5 | Hotel laundry pricing | High (global + Dubai) | 5–10x markup | section C |
| 6 | Taxi fare complexity (new Nov 2025 peak structure; airport vs street flagfall; Salik) | Moderate | Confusion, overpaying | khaleejtimes (2025-11-05) |
| 7 | Legal/etiquette surprises (swearing incl. WhatsApp, gestures, PDA, alcohol licences) | Moderate | Fines/deportation in extremes | pixidia honest guide (2026-04) |
| 8 | VAT refund process friction (validate before check-in, 85% net, fees) | Moderate | Money left on table | u.ae; irglobal (2026-07) |
| 9 | Heat / outdoor discomfort | Seasonal | Comfort | — |

### F. Competitor check (can / partly / no)

| Competitor | DXB arrival guidance | Shirt pressed by deadline from local shop | Recover item left in taxi | Notes + source |
|---|---|---|---|---|
| DubaiNow (incl. AI assistant) | **No** | **No** | **No** (taxi lost-item flow is in S'hail/RTA, not DubaiNow) | Resident-first (UAE Pass/Emirates ID); 370 services, AI assistant added 2025–26; 2.2m users. gulfnews (2026-02-20); digitaldubai guide (2026-09) |
| S'hail (RTA) | **Partly** (metro/taxi info, journey planner) | **No** | **Partly/Yes** for RTA taxis (Lost & Found feedback flow, SMS tracking) | rta.ae; gulfnews (2024-07) |
| Careem | **Partly** (book Hala from airport; no arrival guidance) | **Partly** (Home Services laundry 9:00–23:30; no deadline orchestration/escalation) | **Partly** (own rides in-app, captain contact <5 min, AED 59 delivery; Hala taxis → redirected to RTA) | help.careem.com; careem.com/homeservices |
| Uber | **Partly** (rides) | **No** | **Partly** (own trips only; masked driver call; no liability) | help.uber.com |
| talabat | **No** | **No** | **No** | Food/grocery/pharmacy delivery only |
| Hotel apps / concierge | **Partly** (arrange transfers) | **Partly** (laundry bag, next-day, $5–10/item) | **Partly** (may call RTA for you; no follow-through guarantee) | section C |
| ChatGPT / Gemini | **Partly** (generic guidance) | **No** (can't book/verify/chase) | **Partly** (explains RTA process; no action, no trip data) | capability assessment |
| **Gap** | No visitor-first arrival copilot | **No one orchestrates deadline tasks end-to-end** | No cross-operator (taxi + ride-hail) single flow | — |

### G. Fact checks (official sources only)

| Item | Verified fact | Source (checked 2026-10-09) |
|---|---|---|
| Metro hours at DXB (T1/T3, Red Line) | Mon–Thu 5:00–24:00; Fri 5:00–01:00 (next day); Sat 5:00–24:00; Sun 8:00–24:00 (may extend on holidays/events) | dubaiairports.ae/transport/metro; gulfnews (2025-08-13) |
| T2 Metro access | **None.** Nearest stations Al Qiyadah (~1.7km) / Abu Hail (~2.3km); Bus 43 ~15–18 min; free inter-terminal shuttle ~every 20 min | rome2rio; tripadvisor; dubai-airport.com |
| Metro luggage rules | Max 2 suitcases incl. hand luggage: large ≤81×58×30cm, small ≤55×38×20cm; dedicated luggage area | RTA via gulfnews (2025-08-13) |
| DXB taxi starting fare | DTC airport taxi: AED 20 (normal) / AED 25 (van) flagfall, AED 2.62/km, AED 0.50/min waiting; Dubai Airports quotes "from AED 25". Street-hail flagfall AED 5 (day) / 5.5 (night); **new Nov 2025 structure**: minimum fare AED 13, peak surcharges by day/time | dubaitaxi.ae; khaleejtimes (2025-11-05) |
| RTA lost-item channels | S'hail app → More → Feedback → Taxi Lost & Found; RTA call centre 800 9090; ask@rta.ae; Mahboub chatbot. Details needed: trip date/time, pickup/dropoff, roof colour, plate number, receipt. Status via SMS. Return delivery on meter, paid by finder | rta.ae; dubaitaxi.ae FAQ; gulfnews (2024-07-15) |
| Tourism Dirham | AED 7–20 per room per night by hotel class (5★=20, 4★=15, 3★=10), max 30 consecutive nights, separate invoice line | u.ae; DET Resolution 2 of 2020. **⚠ 2026 support packages deferred (from Apr) then waived the fee (from ~Jun) — status is time-limited; confirm before quoting in-app** |
| EU "roam like at home" → UAE | **No.** RLAH covers EU/EEA only; UAE is outside. Some EU operators sell UAE add-ons; local eSIM/tourist SIM is the norm | EU roaming regulations; eand.ae packs |
| UAE plug type | Type G (UK-style, dominant); legacy C and D sockets exist; 220V / 50Hz | power-plugs-sockets.com; wise.com |
| UAE working week | Mon–Fri (federal government 4.5 days: Mon–Thu + Fri morning); weekend Sat–Sun since 1 Jan 2022; Sharjah public sector Mon–Thu | NPR (2021-12); CNBC (2022-03); Lockton |
| Controlled medicines | Narcotic/controlled: max = shorter of stay or 3 months, needs prescription + attested medical report; free e-permit via ede.gov.ae (~1 working day, UAE PASS, visitor account OK); if no permit, declare at red channel. Ordinary Rx meds: up to 6 months with prescription. **CBD/THC/cannabis: prohibited, no permit route; prison risk** | uaeinform (2026-09-29); UAE embassy; Aetna (2025-12); Federal Decree-Law 30/2021 |
| Tourist VAT refund | Planet is exclusive operator; min spend AED 250/store; 18+; export within 90 days; validate goods + passport + boarding pass before check-in; refund = 85% of VAT minus fees (fixed fee **AED 3.60/claim from 12 Jul 2026**, FTA Decision 11/2026; 13% admin fee remains); cash capped AED 35,000/24h | u.ae; tax.gov.ae; irglobal (2026-07-21) |

### H. Create AI Agents Championship — official rules

| Item | Finding |
|---|---|
| Announcement | Launched **7 Oct 2026** by Sheikh Hamdan at the 3rd Create Apps Championship awards; replaces Create Apps; run by Dubai Chamber of Digital Economy |
| Categories | Best Societal / **Best Personal** / Best Business / Best Youth (youth = lead applicant under 21) |
| Prizes | AED 550,000 per category winner + one winner named **AI Agent of the Year** (+ AED 1,000,000). Total > AED 2.5m |
| Eligibility | Open worldwide, technical & non-technical, **no minimum age**, individuals or teams; entry = idea, prototype, or early-stage MVP. Existing businesses may submit a *new* AI-agent capability. **Fully commercialised solutions are NOT eligible** |
| Timeline | Registration opened 7 Oct 2026, **closes December 2026**. Three intro Agentic-AI workshops; Digital Academy opens November (4 courses, 4 workshops, mentoring) |
| Required submission artifacts | **AI-agent prototype + pitch deck + demo video** (per launch coverage) |
| Judging criteria | Stated qualitatively: identify priority problems, design agents, **test impact**, demonstrate potential to become viable/scalable products. Detailed rubric/weightings: **not published** as of 2026-10-09 |
| IP ownership terms | **Not found** in launch coverage |
| Final-stage format | **Not published**. (The predecessor format — semi-final pitch day → on-stage grand finale — is on createapps.ae but is the old competition's format; do not assume it carries over) |
| Portal | dubaichamberdigital.com/en/create-ai-agents |

Sources: businesswire (2026-10-09); bignewsnetwork/WAM (2026-10-07); khaleejtimes (2026-10-07); renascence (2026-10-08).

---

## 3. First-hand quotes (verbatim, ≤15)

1. "Hotel service is about 5-10 usd per item, so likely $100-$150." — reddit r/travel, hotel laundry thread — https://www.reddit.com/r/travel/comments/10nhhjq/
2. "Laundry is one of the biggest hassles of travel, IMHO. Hotels charge extortionate prices to launder your clothes." — Hacker News — https://news.ycombinator.com/item?id=29812878
3. "they were quite responsive on WhatsApp. I tried WashOn laundry app. They provided good service, They delivered in 24 hour." — reddit r/UAE laundry recommendation — https://www.reddit.com/r/UAE/comments/1njeby2/
4. "Hi, I landed last night in Dubai, took a taxi to my apartment, and unfortunately left my mobile in the back seat. I couldn't memorize the plate number..." — reddit r/dubai — https://www.reddit.com/r/dubai/comments/1847y2c/
5. "Left my airpods in a taxi (fell out of my pocket). Luckily I connected to the taxi's wifi on the journey and got its number on my previously..." — reddit r/dubai — https://www.reddit.com/r/dubai/comments/1gtfgm1/
6. "RTA customer care managed to track the can down based on the pick-up and drop locations. I had my lost item back in an hour." — comment, reddit r/dubai lost & found thread — https://www.reddit.com/r/dubai/comments/192wcmv/
7. "If you have given a deposit please forget about it, as you will not get it back." — Trustpilot review, Dubai car rental (Dec 2025) — https://www.trustpilot.com/review/alzameerrentacar.com
8. "to all those who did not get their security deposit, file a complaint to DED to assist with your deposit. That's what i did and only get my deposit back although they gave me less than 50% of my deposit" — Trustpilot (Jan 2026) — same page
9. "Hopefully this time my deposit will be back as quick as the second time, within 2 weeks. coz very first time I was waiting for the deposit of 6 thousand aed coming back to my card for 2 months." — Sixt Dubai review — https://www.sixt.com/car-rental/united-arab-emirates/dubai/
10. "Home Cleaning Service Is a Mess — Getting Charged, No Cleaner, No Support!" — reddit r/dubai (Careem) — https://www.reddit.com/r/dubai/comments/1lhgl2m/
11. "Thank you DTC I lost my original apple AirPods Pro and my office and House keys thank to DTC lost and found team that found the itme and give to me safe and sound..." — testimonial, dubaitaxi.ae — https://www.dubaitaxi.ae/en/faqs
12. "Landing at DXB after midnight? The metro has stopped, taxi queues build..." — emirateslimo late-night guide (commercial, but accurately summarises the failure modes) — https://www.emirateslimo.com/blog/late-night-arrivals-dxb-hotel-after-midnight
13. "Any recommendations for a good laundry for ironing that's doesn't charge a fortune, I was paying 2dhs and not the guy is asking for 7" — Dubai Facebook community group — https://www.facebook.com/groups/363539461713155/
14. "I'm looking for a budget-friendly tailor in Dubai who can do same-day alterations." — reddit r/dubai — https://www.reddit.com/r/dubai/comments/1pageiu/
15. "It has come to my attention that I clearly do not take full advantage of the services at five star hotels... I'm so used to doing everything myself." — reddit r/FATTravel (Mandarin Oriental Dubai) — https://www.reddit.com/r/FATTravel/comments/197t220/

---

## 4. Hotel-concierge verdict

**Does hotel help already solve deadline tasks and lost-item problems for business visitors? No — it solves them only partially, only in the luxury segment, and only on the hotel's terms.**

Where it works:
- 5-star concierge desks will take a laundry bag, book a restaurant, arrange a transfer, and sometimes call RTA about a lost item. For guests with a flexible schedule and an expense account, this is adequate for non-urgent tasks.

Where it fails:
- **Price:** hotel laundry $5–10/item vs AED 3–7 pressing at local shops — a 5–10x markup that budget-conscious business travellers and anyone on per-diem actively avoid.
- **Speed:** hotel standard turnaround is next-day; a "pressed by 8am tomorrow" or "tonight" request is not reliably executable, especially after evening drop-off. Local laundries offer 24h standard and same-day express; tailors offer 1-hour express alterations.
- **Availability:** mid-range hotels, serviced apartments and Airbnbs — where much of the 2–4 night business-travel segment stays — have no concierge at all, just a front desk or a property manager.
- **Scope/follow-through:** concierge acts as a messenger, not an executor with status tracking; there is no escalation loop when a vendor goes silent (the exact "chasing replies" pain in section D).
- **Lost items:** a concierge can phone RTA on a guest's behalf but cannot supply the trip details the guest didn't capture, and no hotel owns the outcome.
- **Under-use:** even where concierge exists, travellers report not knowing what they can ask for (quote 15) — an information/UX gap, not a staffing gap.

Conclusion: the concierge is a fragmented, premium-priced, daytime-oriented service. A visitor companion that (a) captures trip details passively, (b) books vetted local vendors against a stated deadline with escalation, and (c) owns follow-through, fills the gap the concierge leaves — for every hotel tier.

---

## 5. Surprises (problems we didn't ask about that appear frequently)

1. **The RTA lost-item system is a strength, not a gap** — 104k items/year and claimed 99.9% recovery. The product opportunity is the *visitor's side of the process*: capturing plate/roof-colour/time automatically, filing correctly at 1am, and beating the 3–10 day window before a 3-night visitor flies out.
2. **The taxi Wi-Fi trick** — riders recover taxi numbers by checking which Wi-Fi network their phone joined in the cab (quote 5). This is a folk workaround for a data-capture failure an app could eliminate.
3. **Return delivery is on the meter, paid by the finder** — an unadvertised cost that annoys people even after successful recovery.
4. **Medication/CBD severity** — multi-year prison sentences over CBD vape liquid; codeine and ADHD stimulants are controlled; free e-permit exists but awareness is near zero among visitors.
5. **Nov 2025 taxi fare restructuring** (peak-hour flagfalls/surcharges, AED 13 minimum) makes fare explanation a fresh support burden — visitors comparing 2024 blog posts will be wrong.
6. **Tourism Dirham in flux in 2026** — deferred then waived under support packages; any app hard-coding it should flag the effective date.
7. **Careem redirects Hala-taxi lost items to the RTA** — the super-app boundary is visible exactly in a high-stress moment.
8. **Hotel guests under-use concierge** even at 5-star (quote 15) — the barrier is knowledge/comfort, suggesting a conversational "what can I ask for" layer has value even in luxury.
9. **T2-no-Metro confusion is chronic** across years of forums — small but permanent arrival friction.
10. **Contest eligibility bars fully commercialised products** — the build must stay at prototype/early-MVP stage through December 2026 submission.

---

## 6. Confidence and gaps

**High confidence (official sources, dated 2024–2026):** all of section G; RTA lost-item process and 2025 volumes; Careem/Uber lost-item flows; contest structure/eligibility/timeline; laundry price ranges (6+ independent 2025–26 price lists).

**Medium confidence:**
- Hotel laundry markup ($5–10/item) — robust globally, but few Dubai-specific 2026 hotel price sheets; one 2014 TripAdvisor Dubai thread plus global threads. Range is directionally safe.
- Car-rental deposit complaints — strongly evidenced on Trustpilot clusters, but these skew to one scam-heavy segment; major-brand experience varies.
- Late-night arrival stressors — from one structured commercial guide + forum echo; plausible, not quantified.

**Thin / not found:**
- **Section D direct evidence** — no first-hand reports explicitly about "repeating details across hotel/apps/merchants"; inferred from silence/ghosting complaints. Recommend a small interview round (5–8 business travellers) before hard-scoping.
- **FlyerTalk** — no usable results.
- **TripAdvisor Dubai forum** — surfaced only in search snippets (T2 metro, dry-cleaning cost); could not open threads.
- **SIM/eSIM arrival confusion** — search returned nothing usable; anecdotal importance unknown.
- **Concierge after-hours availability and follow-through** — no quantified data.
- **Contest judging rubric, IP terms, final-stage format — not published** as of 2026-10-09 (contest is 2 days old). Re-check dubaichamberdigital.com/en/create-ai-agents in November when the Digital Academy opens.
- **Reddit full threads** — accessed via search snippets only; some quotes (esp. #6, whose thread title is sarcastic/"USELESS") should be re-verified against the live thread before publication.

**Method note:** frequencies above count independent reports surfaced by web search in one session; they are not prevalence estimates.
