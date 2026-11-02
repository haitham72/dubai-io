# Demo journey scripts — best 5 + appendix (2 Nov 2026)

Status: **ready for founder review** (Phase A2). Card-by-card; fixtures from `2026-11-02-demo-resident.md`.  
Honest statuses only. **Demo data** / **Sandbox** pills where fixtures/sandbox apply.

Shared grammar: ack → cards → detail/plan → Approve or Yes-to-all → evidence or Blocked/portal.

---

## Demo 1 — School + home (KHDA)

| | |
|---|---|
| **Utterance** | “We need Year 5 British curriculum — shortlist schools we can afford and a home with a sane school run.” |
| **UI bot** | Household |
| **Ontology** | `kids_family/school_khda/*`, `household/property_search/*`, `home.jlt_apt` |

**Cards**

1. Constraints confirm (from pack): Year 5 · British · area JLT/work Marina · budget chips — **Edit** / **Looks right**  
2. School shortlist: GEMS candidate A · Nord Anglia candidate B (fees + KHDA-year labels, `as_of`, Demo)  
3. Trade-off: shorter run vs lower fees vs inspection year  
4. Area/rent compare (registered-rent style fixture — historical, not “available flat”)  
5. Plan: request tours for selected schools  

**Approve:** “Send tour enquiries for {schools}” — fields listed.  
**Terminal:** `WAITING_PROVIDER` / Blocked + “Open school portal” if no adapter. Never “seat confirmed.”

---

## Demo 2 — Insurance clinic near me

| | |
|---|---|
| **Utterance** | “Ear pain — which nearby clinic does my insurance cover?” |
| **UI bot** | Money (insurance admin) |
| **Ontology** | `health/insurance_network/*`, `ins.network_bp`, clinics |

**Cards**

1. “Using your **B+** network list (Demo · as_of Sep 2026)” — **Not my list** / **Continue**  
2. Matched branches: Medcare JLT · Aster Marina (why matched + distance estimate)  
3. Detail: outpatient note — network ≠ treatment guarantee  
4. Next: Book / Call / Directions handoff  

**Approve:** share name + member id (fixture) with clinic booking channel if any.  
**Terminal:** appointment `WAITING` or handoff; never invent coverage approval.

---

## Demo 3 — Mamzar day

| | |
|---|---|
| **Utterance** | “Saturday Mamzar with the kids — toys + hot meal when we get back.” |
| **UI bot** | Lifestyle |
| **Ontology** | `fun_out/beach_parks/*`, parking-as-step, food delivery |

**Plan card (Yes / step / Yes-to-all)**

| Step | Content |
|---|---|
| Prepare | Beach toys basket (Noon Now–class fixture prices) |
| Travel | Route + departure aligned with delivery ETA |
| Parking/entry | Parkin-style step — issued pass only if fixture says so |
| Return meal | Hot meal timed to return |

**Disruption chip:** “Stay another hour” → recalculate meal + parking; ask only if outside approved limits.  
**Terminal:** each step Demo / Confirmed only with staged provider events labelled Demo.

---

## Demo 4 — Lost bag — track your ride

| | |
|---|---|
| **Utterance** | “I left my bag in a taxi last night.” |
| **UI bot** | Travel |
| **Ontology** | `travel/taxi_recovery/*`, `trip.careem_marina_dxb` |

**Flow**

1. Ack: **“Let’s track your ride.”**  
2. Cards: **Ride-share / card** · **Cash**  
3a. **Ride-share (B+A):** Demo trip card (Marina → DXB, 22:40, Paid in app) + **Paste receipt/link**  
3b. **Cash:** area chips + time window (evening / after 10) — **no plate**  
4. Next: contact driver / in-app lost item **or** RTA draft + Open official portal  
5. Optional later: “Anything else you remember?” (roof/company) — never required  

**Terminal:** draft / Waiting / Blocked. Never Filed/Paid/Recovered without evidence. Staged replies = Demo.

---

## Demo 5 — Guests tonight

| | |
|---|---|
| **Utterance** | “Guests at 8 — flat ready and light dinner.” |
| **UI bot** | Household |
| **Ontology** | `household/guests_ready`, cleaning, food |

**Plan (Yes-to-all)**

| Step | Provider pattern |
|---|---|
| Clean 2BR | Fixed-price sandbox / Demo |
| Light dinner | Delivery or cook options |
| Access | Building known from `home.jlt_apt` |

**Terminal:** Running / Needs you / Blocked per step; no fake “chef confirmed” without evidence.

---

## Appendix F — Pay bills + UAE Pass (not blocking E)

| | |
|---|---|
| **Utterance** | “Pay this month’s bills.” |
| **UI bot** | Money |
| **Ontology** | `money/pay_all_bills`, `uae_pass/sandbox_demo`, DEWA/Salik fixtures |

1. UAE Pass **Sandbox** connect → Connected (sandbox) or Blocked  
2. Bill list Demo: DEWA · Salik (amounts + as_of)  
3. Approve exact totals + fields shared  
4. Lines stay **Waiting / Blocked** — never Paid without provider evidence  

---

## Micro (not top-5): Gym renew

Utterance: “Update my gym membership.”  
Uses `gym.ff_marina` — cards renew / freeze / change / cancel. **Never ask gym name.**
