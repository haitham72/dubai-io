## 1. Section G — fact-check draft from training knowledge

Save this as `docs/research/priors-claude-<date>.md`. **Every row needs link verification before it goes into `DECISIONS.md`.** My knowledge has a cutoff and several of these (fares, Metro hours) change periodically.

| Claim                                                                                                                                                                                                                                | My confidence                             | Verify at                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- | ------------------------- |
| Dubai Metro has **no 24h service**; roughly ~05:00–00:00, Friday nights extended to ~01:00; Sunday morning start may be later. Hours were revised in 2023.                                                                           | High on "no 24h", medium on exact times   | rta.ae                    |
| **T2 has no Metro station.** Only T1 and T3 are on the Red Line. T2 (regional/flydubai flights) is taxi/bus only and much smaller.                                                                                                   | High                                      | rta.ae / dubaiairports.ae |
| Metro luggage: **max two items per passenger** is the commonly cited RTA rule; luggage racks exist on the airport stretch.                                                                                                           | Medium                                    | rta.ae carriage rules     |
| Taxi from DXB: **AED 25 flagfall at airport ranks** (includes airport surcharge); street-hail flagfall lower (~AED 12); ~AED 2/km after; Salik tolls extra. Airport→central Dubai roughly AED 60–100.                                | Medium-high on AED 25; medium on the rest | RTA fare schedule / DTC   |
| RTA lost items: **call centre 8009090**, DTC lost & found via RTA, or ride-hail in-app support. Key details needed: date/time, **plate number** (on your taxi receipt), pickup/drop-off. Return fees/reward norms vary — unverified. | Medium-high on channels                   | rta.ae                    |
| Tourism Dirham: **AED 7–20 per room per night, tiered by star rating** (5★ ≈ AED 20), collected by hotels since 2014, often added at checkout. Exemptions/caps unverified.                                                           | Medium                                    | Dubai Municipality / DET  |
| EU "roam like at home" **does not cover the UAE** (EU/EEA only); roaming is expensive; tourist eSIMs (du, e&) are the fix.                                                                                                           | High                                      | EU roaming rules + du/e&  |
| Plug type: **Type G (UK 3-pin), 230V/50Hz**.                                                                                                                                                                                         | High                                      | any travel adapter guide  |
| Working week: **Mon–Fri with Friday half-day; weekend Sat–Sun** since Jan 2022. Friday and Sunday are working days.                                                                                                                  | High                                      | UAE government portals    |
| Controlled medicines: **prior MoHAP approval required** for controlled/psychotropic meds (incl. some codeine, ADHD, sleep/anxiety meds); carry original prescription + doctor's letter; quantity limits apply.                       | High on mechanism, medium on specifics    | mohap.gov.ae              |
| VAT refund: 5% VAT; tourists reclaim via **Planet** at kiosks in DXB departures, on "Tax-Free" tagged invoices from participating retailers, min spend ~AED 250; validate before checking bags.                                      | Medium-high                               | FTA / Planet portal       |

**One extra fact worth checking that's not in your list:** WhatsApp **text** works fine in the UAE but voice/video calls have historically been restricted — and that status has reportedly been in flux recently. If your product relies on WhatsApp to contact merchants, verify the current state. This is decision-relevant.

---

## 2. Priors for sections A–F and H — hypotheses to test, not findings

Use these to sanity-check the Deep Research output. If it contradicts a high-confidence prior (e.g., claims the Metro runs 24h), be suspicious.

- **A (arrival):** expect complaints about SIM/eSIM queues at 1 AM, e-gate vs. counter confusion, long-but-orderly taxi ranks at T3, and designated (non-obvious) ride-hail pickup zones. T2 arrivals likely feel neglected. Post-midnight landings = no Metro.
- **B (lost items):** the taxi receipt with the plate number is probably the make-or-break detail; ride-hail in-app flows likely recover items better than street taxis; passport loss is a distinct crisis (police report + embassy).
- **C (deadlines):** expect hotel laundry at AED 15–30+/shirt with morning cutoffs for same-day; independent shops at AED 5–10/shirt, ~24h turnaround, express negotiable, found via Google Maps + WhatsApp. Dedicated laundry _apps_ exist (Washmen, Laundryheap) but are scheduled pickup — not "pressed by 7 AM tonight."
- **E:** expect car-rental deposit pre-auths, Salik/fine admin fees, refund chasing, medication scares, heat, and decency-fine surprises ranking high.
- **F:** DubaiNow is government-services oriented (UAE Pass, resident-oriented); Careem/talabat don't do deadline tasks; ChatGPT/Gemini give generic advice with stale specifics and can't execute anything.
- **H (contest):** my information here is stale/unreliable — treat as "not found" until confirmed from official announcements (Dubai Media Office, WAM, Gulf News).

---

## 3. Four patches to make the real run hallucinate less

Paste these into the prompt before running it in Gemini Deep Research:

1. **Add to Rules:** _"For each row in sections A–F, either cite at least one dated first-hand source (permalink) or write 'no first-hand evidence found'. Never generalize from general knowledge."_
2. **Add:** _"Appendix: list every thread, review, and article you used (URL, date, engagement count). Delete any quote that can't be traced to a URL."_
3. **Add to section G:** _"Fact-check these candidate facts: [paste the table above]. Confirm or correct each with an official link and the page's 'last updated' date where available."_ — confirmation tasks hallucinate far less than open-ended generation.
4. **Add to section H:** _"Search Gulf News, Khaleej Times, The National, WAM and the official championship site. If deadlines or required artifacts aren't on an official page, write 'not published'."_

One practical note: Gemini Deep Research actually browses and cites; DeepSeek's search is much weaker on forums like Reddit. If you can, run Perplexity as a third tool — your per-tool file convention already accommodates it.

---

## 4. After the run

Bring the results files back here and I'll do the merge into `VISITORS.md §0`, `PLAN.md §3`, and `DECISIONS.md` — including reconciling the tool's claims against the priors above and flagging anything that contradicts a high-confidence fact or smells invented.

What did the rest of "Please help me:" say?
