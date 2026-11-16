# Dubai-io residence companion — core design (2 Nov 2026)

**Status (9 Nov 2026):** Task-thread (Do) spec. Identity now in `PLAN.md` §1 (9 Nov); shell/UI and memory-UX sections are superseded by the Know/Notice/Do direction; the grammar, context-reuse rules and dogfood matrix remain the Do-pillar eval.

Status: **active brief (2 Nov)** — folded into `PLAN.md` / `docs/archive/root/handoff.md` (now `docs/archive/root/handoff.md`) and execution plan `docs/archive/superpowers/plans/2026-11-02-residence-companion-mcp.md`. Does not replace `docs/archive/plan/unified-app-design.md` for shell/craft — this file is the **product brief + dogfood bar**.

## 1. One-line product

**Dubai-io is a Grok-style residence companion for people who live and work in Dubai** — it remembers what you told it, runs long-horizon task threads across life domains, keeps a Reddit-style community one switch away, and treats **services as a feature** (cards → detail → approve → honest proof), not as the whole app.

Not: a DubaiNow clone, a DEWA Jarvis, a t-shirt shop, or a tourist brochure.

## 2. Behaviour grammar (every domain)

Borrowed from Grok Bot / ChatGPT Dots / Claude Duet — **interaction pattern**, not shopping:

1. User asks in Assistant → **task thread** in the matching life domain.
2. Short ack + **option/result cards** + refine chips.
3. Tap → **designed detail / plan screen** (simple, elegant, light-first).
4. **Approve** listing exact fields/amounts shared: one explicit tap per side effect, also on a multi-step plan (no Yes-to-all; rule 6 strict, founder 9 Nov).
5. Execution only via **registered adapter** + verified evidence; else draft + blocker / Open official portal. Never invent Paid / Booked / Confirmed / Filed.
6. Optional browser-agent **screenshot** as proof (merchant or portal ready-state) — later slice; not required for first dogfood bar.
7. Memory style **B**: Me page (“You told me” / “I noticed”) + rare in-thread chips (“Because…”, “I saved…”).

Demo / sandbox / fixtures always show a visible **Demo data** or **Sandbox** pill.

## 3. Two-layer domain model (UI coarse · memory fine)

**Founder direction (2 Nov):** the deep plan (e.g. today’s `lifestyle > sports > gym` draft) lives in a **restructured temporal_note-style memory ontology**, maintained/evolved by a **subagent** — not as a deep folder tree the user must navigate.

**What the user sees:** a short list of **app-owned “domain bots”** (Grok channel grammar: compact, status line, unread when Needs you) — e.g. **Lifestyle · Career · Social · Household** (exact set TBD in §3.1). Idle = compacted and waiting; Active = a task is running under that bucket.

| Layer | Owner | Contents |
|---|---|---|
| **UI bots** | Product shell | 4–7 coarse buckets; task threads hang here |
| **Ontology (temporal_note)** | Memory engine + planning subagent | Fine paths, entities, validity, links (`lifestyle/sports/gym`, provider, membership id…) |
| **Classifier** | Backend | Maps ask → ontology leaf → **rolls up** to one UI bot |

User never “creates a Gym bot.” Ask “renew gym” → ontology hit `…/gym` + entity `Fitness First Marina` → thread appears under **Lifestyle** with chip “Because you train at…”. Demo packs seed ontology so demos never ask stupid questions.

**Services** = fulfilment inside a thread (cards → approve). **Community/Social** may be both a UI bot *and* the Assistant⇄Community surface — decide in §3.1. **Projects** = multi-leaf campaigns that still surface under one UI bot (or a single Projects bot).

### 3.1 UI bots (user-visible — draft options)

Candidate short list (pick/merge later):

```
Lifestyle | Career | Social | Household | Money | Travel | Me
```

Rules of thumb:

- **Lifestyle** — sports/gym, food habits, wellness, cloth, fun/outings, hobbies (ontology holds the depth).
- **Career** — inbox chase, applications, meetings, expenses, visa admin.
- **Social** — community feed/chats, neighbour threads, hosting-with-people (not the same as Reddit surface alone — may deep-link).
- **Household** — AC, laundry, cleaning, building, movers, kids/school *or* kids get their own bot if the short list grows.
- **Money / Travel** — optional 5th/6th if Lifestyle would become a junk drawer.
- **Me** — memory & settings, not a task factory.

Deep trees are **not** rendered as nested sidebar folders.

### 3.2 Ontology map (temporal_note — huge tree)

**Canonical full tree:** [`2026-11-02-residence-ontology-tree.md`](./2026-11-02-residence-ontology-tree.md)

~14 roots, **~200+** leaves at depth 3–4: `identity`, `lifestyle` (sports/gym…), `household`, `kids_family`, `career`, `money`, `health`, `cars`, `travel`, `fun_out`, `tech`, `social`, `civic_gov`, `projects`, plus `meta` for connectors/demo pack. Sourced from founder domains, `docs/plan/journeys.md` (KHDA, insurance network, Mamzar, move, taxi…), existing service categories, and common personal-life taxonomies — Dubai-weighted (DEWA, Salik, DXB, UAE Pass, Ejari, Parkin).

**Subagent job (later):** normalize paths → kinds/edges/validity, rollup → UI bots, deny-lists, seed `meta/demo_resident_pack`.

**Example:** ontology `lifestyle/sports/gym` + entity → UI bot **Lifestyle** thread “Renew Fitness First”.

## 4. “Able to do all of this” bar (PC dogfood)

On founder PC: API `:8030` + site `http://localhost:3000/` (and/or `?desktop`).

For **each domain**, at least one ask that:

1. Creates/updates a task thread in that domain.
2. Shows cards or a multi-step plan.
3. Supports Approve (one tap per side effect) with honest status afterward.
4. Can store/reuse a relevant Me fact when the user states one.

Fixtures and sandbox are allowed. Live government payment and live email send are **not** required for this bar.

### Dogfood matrix (v1)

| # | Domain | Ask |
|---|---|---|
| 1 | Me | Save household facts; “What do you know about me?” + Forget |
| 2 | Money | Bills due + Salik/DEWA reminders |
| 3 | Money | Pay this month’s bills (UAE Pass sandbox demo) |
| 4 | Kids | School tours / KHDA shortlist + approve enquiry draft |
| 5 | Household | AC before Friday |
| 6 | Household | Guests at 8 — clean + food (one tap per side effect) |
| 7 | Career | Chase application / email thread (demo evidence ok) |
| 8 | Career | Reimbursement pack from receipts |
| 9 | Fun | Mamzar Saturday (prep → maps → parking step → meal) |
| 10 | Cloth | One shirt find + size memory (single cloth case) |
| 11 | Tech | Home internet slow — plan/options |
| 12 | Cars | Book service or wash |
| 13 | Cars | Used/new car shortlist research |
| 14 | Projects | Move in 3 weeks — checklist |
| 15 | Health | Insurance-eligible clinic near me |
| 16 | Travel | DXB late arrival **or** taxi lost-bag (see §4.1 — **not** plate-first) |
| 17 | Community | Feed + one chat reply |

AR via [RTV](https://github.com/ZaiqiangWu/RTV): **out of v1 dogfood** unless founder unlocks (PLAN.md still LATER; needs GPU + per-garment ckpt; non-commercial license).

### 4.1 Journey redesign — lost item in taxi (founder, 2 Nov)

**Reject:** opening with “write the car license plate.” Nobody remembers that. Current site stub (`demo-taxi` in `ThreadView`) is **awful** and must be replaced.

**Framing line:** “Let’s track your ride.”

```
Lost bag in taxi
        │
        ▼
 Card: How did you pay / book?
   ├─ Ride-share app or card payment
   │     → pull trip from Careem/Uber/Hala (connector or paste trip link/receipt)
   │     → confirm pickup/dropoff/time from that evidence
   │     → contact driver / in-app lost item  OR  draft RTA if needed
   │
   └─ Cash (street / rank taxi)
         → Cards: roughly where + when (area chips, time window — not plate)
         → optional: roof colour / company only if user offers it
         → prepare RTA lost-and-found draft + Open official portal
         → status stays draft / Waiting / Blocked — never fake Filed
```

Rules:

- Plate / roof colour are **optional later chips** (“anything else you remember?”), never the first gate.
- Cash path is **location + time → contact RTA** (handoff + draft), not pretend GPS of the car.
- Ride-share path = **B+A**: show a labelled **Demo** fixture trip card (Careem/Uber/Hala-style: route, time, last-4 of card or “Paid in app”) **and** offer “Paste trip link / receipt” as fallback. No live connector required for dogfood.
- Staged demo replies labelled **Demo**; RTA send only with real adapter + approval + evidence (rule 1/4).

Dogfood pass for #16: ask “I left my bag in a taxi last night” → “Let’s track your ride” + payment cards → ride-share shows Demo trip card (+ paste option) **or** cash asks where/when → RTA draft — **zero** plate required.

### 4.2 Demo completeness + “don’t ask stupid” (founder, 2 Nov)

**If a thread is `{demo}` / Demo data, it must be fully planned end-to-end** — scripted context, cards, and next steps. A demo that opens with a blank interrogative (“What’s the name of my gym?”, “What phone do you have?”) is **failed product**, not a clever clarifier.

**Context rule (all asks, demo or live):**

| Situation | Behaviour |
|---|---|
| Entity already in Me / prior booking / domain tree (e.g. `lifestyle > sports > gym` → “Fitness First Marina”) | Use it. Chip: “Because you train at Fitness First Marina…” |
| User said it earlier in this or a saved session | Reuse. Never re-ask. |
| Unknown and **not** a demo | Ask **one** high-value question with cards (not an open text quiz). |
| Unknown and **is** a demo | **Invent nothing as live truth** — ship fixture facts in the demo pack so the flow never needs the awful question. |

**Banned openers (examples of awful):**

- “Update my gym membership” → “What’s the name of my gym?”
- “Change my phone” → “What kind of phone do you have?”
- “Lost bag in taxi” → “Write the license plate”

**Gym dogfood (replace current `demo-gym` stub):**  
Ask “Update my gym membership” → thread already knows gym from fixture under lifestyle/sports/gym (or prior book) → cards: renew / freeze / change plan / cancel → detail → approve. Never ask the gym’s name in that demo.

Same bar for tech (phone/plan), cars (the registered car), household providers already used, etc.

## 5. Memory (temporal_note-aware, cloud-slim)

- Port **engine ideas** from founder `temporal_note` (events, entities with validity, hypotheses, context pack, due advice) — **not** personal vault data, not 36 MCP tools as UX, not local disk indexing for cloud users.
- Session facts today → evolve toward Plan 6 (`docs/superpowers/plans/2026-10-23-temporal-memory.md`).
- Rule 9 intact: visible, editable, forgettable; never infer health/religion/ethnicity/nationality-as-trait/gender/sexuality/politics.

## 6. Architecture slices (build order)

1. **Wire `apps/site` → live API** — composer creates real tasks; approval calls registered actions; stop demo-only dead ends where a live path exists on frozen `apps/web`.
2. **Multi-step plan** — shared plan card; each side-effect step needs its own approval tap and evidence (no Yes-to-all, founder 9 Nov).
3. **Fixture journey per domain** — one scripted happy path + failure/blocker path each.
4. **Me recall / forget + context pack** — answers “what do you know?” without inventing.
5. **Money demo** — bills-due fixtures + UAE Pass sandbox stub (connect + draft only).
6. **Browser-agent checkout/portal screenshot** — optional later; not blocking dogfood bar.
7. **Cloth AR (RTV)** — optional labelled demo after v1.

**Frozen:** `apps/web` remains reference (`mobile-pwa-baseline-2026-10-23`); no edits without founder approval. Use it for parity and interim dogfood of airport/taxi/orders.

**Never:** DubaiNow branding/layout; fake Send/Paid; LLM text as authoritative status.

## 7. Current repo state (2 Nov 2026 snapshot)

- Branch: **`main`**, ahead of `origin/main` by 1 commit (`fc33d61` domain-grouped threads).
- Large **uncommitted** desktop-full-load work (Chats/Community/Services/Me, design refs, plan `2026-10-29-desktop-full-load.md`).
- Historical local branches (do not continue product work there): `build`, `ios-swift`, `next-steps`, `redesign`.
- Honest dogfood today: frozen web journeys + site shell; most matrix rows still MISSING or PARTIAL on site.

## 8. Success for this phase

Founder can run **all 17 matrix asks** on one PC in under ~30 minutes, with honest statuses, and point to which domain each thread lives in — without claiming live civic execution.

## 9. Out of scope for this brief

Native iOS/Android packaging, Graphite dark polish, full temporal_note MCP for end users, affiliate mall, live AR try-on as a product pillar.
