# Review — Cline (independent), 2026-10-10

Independent pass. I did **not** open `docs/reviews/` or the contents of `archive/reviews/`. Read in full: `PLAN.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `docs/DESIGN.md`, `docs/DECISIONS.md`, `docs/VISITORS.md`, `docs/VISION.md`, all 5 files in `docs/research/`, and the whole demo (`index.html`, `app.js`, `data.js`, `styles.css`, `miniapps/foldpress.html`, `miniapps/palmleaf.html`). Listed only: `demo/maps/` = 4 placeholder images (`dxb-overview.png`, `t3-check-in.jpg`, `t3-duty-free.jpg`, `t3-business-lounge.jpg`); `archive/reviews/` = `cursor-plan_review.md`, `Muse-report.md`, `REVIEW.md`.

## Verdict
Unusually disciplined for a Phase 0 sketch: a deterministic "LLM proposes, user/merchant taps mutate" core (`ARCHITECTURE.md:40`, `DECISIONS.md:29`) makes truth-in-status hold by construction, and every displayed fact carries provenance (`CLAUDE.md:40`). The companion/arrival spine is the best-evidenced part and the demo proves the sandbox + scoped-bridge story cleanly. The load-bearing weakness: the hero story's key competitor — the hotel concierge — is still unproven, and the only research touching it is the least citable tool.

**Ready to build? Yes — start Phase 1–2 (companion + arrival) now.** The floor (memory + follow-through) is well-evidenced and the architecture is sound, so scaffolding can begin. Do **not** lock the pitch narrative or Phase 3 services scope until two gaps close: (1) a citable concierge verdict, (2) the contest deadline confirmed on the official site.

## Research — per-file verdict
| File | Verdict | Note |
|---|---|---|
| `research-prompt.md` | **Usable (as instrument)** | Well-built anti-hallucination prompt (`:48-60`). But status still reads "NOT RUN YET" (`:3`) though results now exist — stale. |
| `Dubai Visitor Pain Points Research.md` | **Usable** | Strongest file: numbered footnotes with URLs (`:224-248`), separates official vs review. Spot-check links before citing. Fills the laundry/concierge/deposit/contest gaps. |
| `Deepseek-research.md` | **Priors-only until linked** | Every evidence table has an **empty "Sources" column** (`:26,35,43,52`) and quotes give source *names*, no permalinks (`:108-121`). `glm-research.md:45` warned this tool's forum search is weak. Its concierge verdict (`§4`) is decision-relevant yet least reliable. |
| `glm-research.md` | **Priors-only (by its own words)** | Self-labels "training knowledge… not findings," "verify before DECISIONS" (`:1-3,22-23`). Valuable as a sanity-check and for the WhatsApp voice-call caveat (`:19`). |
| `qwen-research.md` | **Discard** | Contains **zero Dubai content** — a meta-analysis of a failed empty-prompt interaction (`:5-9`). No evidence value. |

## Top 5 merged facts (confidence)
1. **Taxi lost-items: high volume, high stakes, recovery needs exactly the details a companion remembers** (time, pickup/drop-off, roof colour, plate, receipt). **High.** 104,162 reports in 2025, ~35k devices, ~3k passports, AED 2M cash, most contacted <2h (`VISITORS.md:18`, official RTA via news; corroborated `Deepseek:12,113`, `Pain Points:12`).
2. **Post-midnight / T2 arrivals have no Metro** → taxi/ride-hail is the realistic choice; a genuine time+terminal→mode decision. **High** (corroborated: `glm:7-8`, `Deepseek:9-10`, `Pain Points:5-6`, `VISITORS:19`). Exact times vary by source.
3. **Hotel concierge partially solves deadline + lost-item tasks but has real gaps** (outsourced/slow laundry, won't take late orders, no concierge at budget/serviced, can't recover a taxi item). **Medium** — pivotal finding, but rests on review anecdotes + the weakest-sourced tool. Must be verified before it anchors the pitch.
4. **Car-rental deposit retention is the #1 tourist consumer complaint** (42%; deposits charged not pre-auth'd; 30-day refund rule). **High** on frequency (`VISITORS:20`, consumer-protection figures); **Medium** on the AED 1,000–10,000 range (`Pain Points:9`). Best-evidenced *post-contest* case (`DECISIONS.md:36`).
5. **Laundry deadline is the weakest-evidenced beat; independents are reached via WhatsApp/Google and quotes are negotiated.** **Low-Medium as a pain, High as a mechanism.** Laundry prices conflict wildly across files (independents AED 5-12 vs hotel AED 35-100) → treat as vendor/marketing, not citable. Keep as showcase only (`VISITORS:22,28`).

## Product direction — the 3 questions
**Q1 — Quote/bid vs fixed order: keep quote/bid, scoped to deadline services.** Agree with the founder. It is the agentic differentiator — "a deadline creates a real agent decision" (`DECISIONS.md:16-17`) — and it mirrors how independent shops actually operate (negotiated quote via WhatsApp, `Deepseek §C`). A Talabat fixed-order is commoditized where talabat/Careem are strong. The repo already encodes this correctly: `foldpress` uses `quote.request` (`data.js:119`), `palmleaf` uses `cart.request` (`data.js:89`), distinguished by `bridge_scopes`. Keep fixed-order for pharmacy/grocery, quote only for deadline services.

**Q2 — Per-merchant sandboxed mini-apps: yes, the right execution layer — with one honesty caveat.** The technical execution is genuinely good and a real differentiator: separate origin, `allow-scripts` only, never `allow-same-origin`, `connect-src 'none'`, scoped bridge, host-executes-widget-never (`ARCHITECTURE.md:154-164`), demonstrated live by the palmleaf self-test (`palmleaf.html:54-64`). Caveat: `ARCHITECTURE.md:164` admits the MVP writes *one* platform widget and merchant-authored HTML is out of scope — so "WeChat" is aspirational framing. Soften on-stage to "mini-app runtime"; consider whether standard cards + one mini-app carries the Services pillar with less surface area for a solo builder (Phase 3 = ~3 weeks, `PLAN.md:103`).

**Q3 — Companion first / services last: strongly agree; best decision in the repo.** Evidence-aligned: the best-evidenced beat is the lost-item memory payoff (`VISITORS:18`), the weakest is the laundry deadline (`VISITORS:22`). So services must be the *mechanism* proving follow-through, not the headline claim — exactly the founder's framing (`PLAN.md:12`, `DECISIONS.md:15`). The cut order protecting memory+follow-through (`PLAN.md:34`) is correct.

## Issues
**Critical**
- **C1. The concierge-competitor question is unanswered and only touched by the weakest-sourced research.** It is the load-bearing risk to the hero story ("the hardest open question," `VISITORS:31-39`; open in `DECISIONS.md:35`), yet `Deepseek §4`'s concierge verdict has no sources. If the concierge wins in reality, the hero has no gap. Verify with link-filled evidence before pitching services.

**High**
- **H1. The deadline-conflict beat — the whole reason the quote flow matters — is not in the demo.** `transition` to `QUOTED` just sets `price=estimate+7`, `eta="35-45 min"` (`app.js:351`); nothing compares it to the user's 09:00 deadline or proposes an earlier slot. Listed as unbuilt (`PLAN.md:30,89`). The pitch's core agentic moment is currently a promise, not a demo.
- **H2. `Deepseek-research.md` has no source links** (empty Sources columns, `:26-55`), so it cannot be merged into `VISITORS`/`DECISIONS` as evidence without filling them. Exactly the failure `glm:45` predicted.
- **H3. Demo miniapps use `script-src 'unsafe-inline'`** (`foldpress.html:3`, `palmleaf.html:3`); `ARCHITECTURE.md:160` requires `'self'`. Demo-only, but a copy-paste hazard into the Phase 3 widget CSP.

**Medium**
- **M1. `postMessage(..., "*")` everywhere** in demo + host (`foldpress.html:26`, `palmleaf.html:40`, `app.js:269`); `ARCHITECTURE.md:161` requires strict origin checks. Harmless same-origin in the demo, but must not carry into the real bridge.
- **M2. Contest facts exist only in research, unverified.** `Pain Points:14` gives a concrete deadline (submissions Jan 2027, final May 2027, launched Oct 7 2026, prize pool >AED 2.5M), yet `PLAN.md:16,88` and `DECISIONS.md:37` still say "to verify." Verify on the official site, then re-anchor phases (`PLAN.md:75`).
- **M3. Confirmed-request status card shows no visible demo/sandbox pill.** Approval shows "Demo merchant" (`app.js:331`), but the status tracker after it does not (`app.js:369`) — "Merchant confirmed · ref FP-1234" (`app.js:352,321`) can read as real on stage. Keep a persistent Demo pill on live request cards.
- **M4. Research hygiene:** `qwen-research.md` sits beside real research with zero Dubai content; files don't follow the prescribed `results-<tool>-<date>.md` naming (`research-prompt.md:3`); status line (`research-prompt.md:3`) and the `CLAUDE.md:19` "remind founder to run it" are now stale.
## What's good — keep
- **LLM reads/proposes, only taps mutate** (`ARCHITECTURE.md:40`): the single best architectural call; makes honesty structural, keeps the agent simple.
- **Provenance on every fact + required trust pills** (`ARCHITECTURE.md:71-79`, `DESIGN.md:29`): rare, and a real trust differentiator.
- **Honest handoffs** — ride app "handed off" (`app.js:205`), recovery "not filed / not recovered" (`app.js:409-419`), no invented belts/gates (`data.js:8-9`). Exactly right for a demo that must not overclaim.
- **Widget sandbox design** (`ARCHITECTURE.md:154-164`) and its live self-test (`palmleaf.html:54-64`): well-reasoned and demonstrated.
- **Companion-first positioning + protected cut order** (`PLAN.md:12,34`): evidence-aligned.

## Next 4 actions (in order)
1. **Verify contest rules on the official Create AI Agents Championship site** (deadline, artifacts, judging, IP). Cheapest high-leverage step; sets the clock and unblocks re-anchoring (`PLAN.md:16,75,88`). The Jan-2027 date is research-sourced, unverified by me.
2. **Settle the concierge question with citable, link-filled evidence** (fill `Deepseek` Sources from `Pain Points` citations or discard that verdict; verify `Pain Points` review links). Gate: if the concierge wins, pivot to serviced-apartment/Airbnb/off-hotel needs before Phase 3 (`VISITORS:39`).
3. **Build the deadline-conflict branch in the demo** (arc v2): when a quoted slot misses the user's stated 09:00 deadline, the companion flags the conflict and proposes an earlier slot (`PLAN.md:30,89`). Makes the core differentiator visible.
4. **Fix research hygiene:** mark `qwen-research.md` discarded/meta, rename outputs to the `results-<tool>-<date>.md` convention, and update the stale status line (`research-prompt.md:3`) and `CLAUDE.md:19` reminder to match that results now exist.


