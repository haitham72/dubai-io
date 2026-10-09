# Visitors: what they actually face

**Purpose:** ground the demo and plan in real visitor problems. **Everything here is a hypothesis until the Phase 0 interviews confirm it.**

Tags: `[T03]` / `[S11]` = from the archived case studies (`archive/handoff/06` Part II, `03`) · `[verify]` = general knowledge, not yet checked · `[interview]` = only interviews can answer.

---

## 1. Journey stages and pain points

| Stage | What goes wrong | Source |
|---|---|---|
| **Before the trip** | Unsure about entry/visa rules for their passport; which terminal; what to pack for the heat; dress norms | [T02] [T08] [verify] |
| **Landing (often late at night)** | Exhausted; long walk/train between concourse and immigration; Smart Gate vs counters unclear; belt not known; no data yet | [T02] |
| **Getting connected** | Roaming bill shock; tourist SIM vs eSIM vs airport Wi-Fi; cash vs card | [T02] [verify] |
| **Airport → hotel** | Taxi vs ride-hailing vs Metro; Nol card needed; luggage limits on Metro; child seats; fares unclear at 2 AM | [T02] [T03] |
| **Hotel check-in** | Deposit holds on cards; tourism fee per night surprises; early arrival before check-in time | [verify] |
| **First 24 hours** | Shirt or suit creased for a meeting; forgotten charger/adaptor; pharmacy for jet lag, sun or stomach; food nearby that is open late | [T01] [S16] [verify] |
| **Getting around** | The city isn't walkable in the heat; Metro women-and-children and Gold cabins; Salik tolls and parking in rental cars; ride surge pricing | [T03] [verify] |
| **Activities** | Desert safari packages hard to compare, inclusions hidden, scam worry; booking skydiving/attractions; weather cancellations | [T01] [T09] |
| **Culture & rules** | Ramadan etiquette; dress codes in malls and mosques; photography of people; alcohol licensing; public behaviour norms | [T06] [T08] [verify] |
| **Things go wrong** | Item left in a taxi; lost car in a giant mall; heat illness; disputes with a merchant; flight delay breaks the plan | [T04] [T05] [T07] [S10] [Journey D] |
| **Departure** | VAT refund: which receipts qualify, where to validate, timing; check-in at the right terminal; liquids and duty-free | [T10] |

## 2. European visitors: specific frictions

| Friction | Note | Source |
|---|---|---|
| **Roaming:** EU "roam like at home" does not cover the UAE | High data costs → a strong reason to want a local SIM/eSIM on arrival | [verify] |
| **Power plugs:** UAE uses UK-style Type G | Continental Europeans need an adaptor; a classic forgotten item | [verify] |
| **Weekend and working days** differ from what many expect | Affects business meetings, government offices, some shops | [verify] |
| **Medication rules:** some common European prescription or codeine medicines are controlled | Travellers may need documentation; high anxiety, high stakes | [verify] |
| **VAT refund:** the UAE system is separate; **UK and EU refund systems differ** | Don't build one global refund engine | [T10] |
| **Tipping and haggling norms** unclear | Small but constant uncertainty | [verify] |
| **Heat:** summer walking distances are unrealistic for Europeans used to walkable cities | Changes route and activity advice | [T01] [verify] |
| **Visiting family:** "my parents arrive from London on Friday" | Residents preparing for European visitors is a bridge between visitor and resident modes | [archived 08 pitch] |

## 3. Personas

| Persona | Trip | Top jobs | Fit with our demo |
|---|---|---|---|
| **A. European business traveller** (proposed hero) | 2–3 nights, meetings | Arrive late, get to the hotel, shirt pressed by 9 AM, don't lose anything, minimal effort | **Strong**: arrival + laundry deadline + lost bag |
| **B. Family on holiday** | 5–7 nights | Kids, heat, attractions, tickets, car seats, pharmacy | Medium: airport + ride; tickets and activities are LATER |
| **C. Transit / long layover** | 8–24 h | Can I leave the airport? What can I do in X hours? Getting back in time | Weak now; a good post-contest wedge |
| **D. Relatives of residents** | 1–2 weeks | The resident host prepares; the visitor needs local help without the host | Bridge to resident mode |
| **E. Solo young traveller** | 3–5 nights, budget | Metro, nightlife, safe return, cheap food | Medium: Metro path exists |

**Recommendation:** make **Persona A** the hero for the contest story. The external review independently suggested "visitors arriving for work". It's the persona where *memory + deadline + follow-through* matters most and a pressed shirt by 09:00 is believable.

## 4. Mapping to the plan

| Pain point | Status |
|---|---|
| Landing at night, step guide, "I'm lost" | **In demo** |
| Airport → hotel choice | **In demo** |
| Shirt pressed by a deadline (independent laundry) | **In demo (v2)** |
| Lost item in taxi | **In demo** (memory payoff) |
| SIM/eSIM, adaptor, pharmacy after arrival | Candidate: a "first 24 hours" checklist card after hotel arrival (cheap to add) |
| Flight delay → replan transfer | Candidate stretch beat [Journey D] |
| VAT refund on departure | LATER (fits a "Hello again, departing?" flow + the departure maps we have) |
| Safari comparison, tickets, mosque trip | LATER |
| Medication rules, heat illness | LATER, and only with official sources |
| Parking memory, rental car tolls | LATER (needs native app) |

## 5. Phase 0 interview script (6–8 visitors, ~15 min each)

Target: people who visited Dubai in the last 12 months, ideally from Europe and at least half on business.

1. Walk me through your last arrival in Dubai, from the plane to the hotel. What was annoying or confusing?
2. What did you need in the first 24 hours that you didn't have or couldn't easily get?
3. Which apps did you use during the trip? Which did you install just for Dubai, and did you keep them?
4. Did anything go wrong (lost item, wrong booking, sick, scammed, delayed)? What did you do?
5. Did you use any small local shop (laundry, tailor, repair)? How did you find and contact it?
6. *[Show the 4-min demo.]* In one sentence, what does it do? What did it remember about you? Who confirmed the laundry request?
7. Would you install it before your next trip? What would make you delete it?

Record answers in a short table. Promote a `[verify]` / `[interview]` row above to "confirmed" only when at least 3 of 8 people mention it unprompted.

## 6. Sources in the archive

- `archive/handoff/06-DETAILED-USE-CASES.md`: Part II **T01–T10** (tourist case studies), Part IV **Journeys A–F** (36-hour family day, arrival delay replanning), S01–S25 expansions
- `archive/handoff/03-SCENARIO-LIBRARY.md`: scenario index and the tourist case table
- `archive/handoff/07-AI-NATIVE-SERVICE-ECOSYSTEM.md` §6: the visitor journey (pre-arrival → departure)
