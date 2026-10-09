# Research prompt: Dubai visitor needs (for Gemini Deep Research / DeepSeek)

**Status: ⏳ NOT RUN YET.** Paste the prompt below into Gemini Deep Research or DeepSeek (with search on). Save each answer as `docs/research/results-<tool>-<YYYY-MM-DD>.md` and change this status line to ✅ with the date.

**Why:** our own tools can't read Reddit or forums. The plan (`PLAN.md` v1.0) rests on desk research that's strong for lost items in taxis, medium for late-night arrival, and **weak for the laundry deadline and the hotel-concierge question**. This research fills those gaps before the build.

---

## Prompt (copy everything below this line)

You are a meticulous user researcher. Research what **short-stay visitors to Dubai** (especially business travellers on 2–4 night trips) actually report as problems, using real first-hand sources. I'm building a personal AI companion app, and I need evidence, not opinions.

### Sources to search (prioritize first-hand reports)
- Reddit: r/dubai, r/DubaiTravel, r/UAE, r/travel, r/solotravel, r/BusinessTravel, r/onebag, r/delta / r/emirates (airline subs for DXB arrivals)
- TripAdvisor Dubai forum, FlyerTalk (Emirates and DXB threads), Google Maps reviews of DXB and laundries, Trustpilot
- Official: RTA, Dubai Airports, Dubai Economy and Tourism (DET), consumerrights.ae, UAE government portals
- Reputable news: Gulf News, Khaleej Times, The National

### Questions to answer

**A. Arrival at DXB (especially late at night)**
1. What do first-time and business visitors report as confusing or stressful from the plane to the hotel? (immigration, baggage, connectivity/SIM/eSIM, cash, transport choice, taxi queues, terminal differences T1/T2/T3)
2. Real experiences with Metro vs taxi vs Careem/Uber after midnight and from T2.

**B. Lost items**
3. First-hand stories of leaving items (bags, phones, passports) in Dubai taxis or ride-hails: what they did, how long it took, what details were needed, and whether they got the item back. Note any failures.

**C. Getting things done by a deadline during a short stay**
4. Reports of needing something done before a fixed time (shirt/suit pressed, tailoring, repairs, pharmacy, documents printed) and how it went.
5. **Hotel concierge vs alternatives:** where does hotel help fall short (price, speed, availability at night, follow-through, budget hotels/serviced apartments without a concierge)? Quote examples of hotel laundry prices or delays if reported.
6. Do visitors use small independent shops (laundry, tailor, repair)? How do they find and contact them (WhatsApp, walk-in, apps)? What goes wrong?

**D. Repeated information and chasing replies**
7. Reports of having to repeat details or chase replies across hotel, apps and merchants during a trip.

**E. Other high-frequency, high-consequence problems**
8. Top recurring visitor complaints (e.g. car rental deposits, scams, refunds, heat, etiquette surprises, medication rules). Rank them by how often they appear and how costly they are.

**F. Competitors (be fair, don't assume they're weak)**
9. What can visitors do today with DubaiNow (incl. its AI assistant), Careem, talabat, Uber, hotel apps, and ChatGPT/Gemini for: DXB arrival guidance; a shirt pressed by a deadline from a local shop; recovering an item left in a taxi? Mark each can / partly / no, with sources.

**G. Fact checks (official sources only)**
10. Verify, with links and dates: Dubai Metro hours at DXB stations; whether T2 has Metro access; Metro luggage rules; DXB taxi starting fare; RTA lost-item reporting channels and required details; the Tourism Dirham fee; whether EU "roam like at home" covers the UAE; UAE plug type; the UAE working week; travelling with controlled medicines into the UAE; the UAE tourist VAT refund process.

**H. Contest**
11. Official rules for the **Create AI Agents Championship (Dubai)**: deadlines, required submission artifacts, judging criteria for "Best Personal AI Agent", eligibility, IP ownership terms and the final-stage format. Say "not published" if not found.

### Output format (follow exactly)
1. **Executive summary:** 10 bullets, the most decision-relevant findings first.
2. **Evidence table per section A–H:** `Finding | Frequency signal (how many independent reports) | Consequence (time/money/stress) | Current workaround | Source links (with dates)`.
3. **Quotes:** up to 15 short, verbatim first-hand quotes (with links) that best capture real pain.
4. **Hotel-concierge verdict:** does hotel help already solve deadline tasks and lost-item problems for business visitors? Where exactly does it fail?
5. **Surprises:** problems we didn't ask about that appear frequently.
6. **Confidence and gaps:** what you couldn't verify, and which sources were thin or old.

### Rules
- Prefer first-hand reports from the **last 3 years**; label anything older with its year.
- **Never invent quotes, numbers or links.** If you can't find something, say "not found".
- Separate **facts** (from official sources) from **experiences** (forums/reviews).
- Count independent reports; don't present one viral post as a trend.

---

## After running it

1. Save the output to `docs/research/results-<tool>-<date>.md`
2. Update the status line at the top of this file
3. Ask Claude to merge the findings into `docs/VISITORS.md §0`, `PLAN.md` §3 and `docs/DECISIONS.md`
