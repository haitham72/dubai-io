# Dubai-io — Review (Claude)

**Date:** 10 Oct 2026 · **Reviewer:** Claude (opencode) · **Scope:** `PLAN.md` v1.0, `ARCHITECTURE.md`, `CLAUDE.md`, `docs/DESIGN.md`, `docs/DECISIONS.md`, `docs/VISITORS.md`, `docs/research/` (5 files), `demo/` (`index.html`, `app.js`, `data.js`, `styles.css`, `miniapps/`, `maps/`), `docs/VISION.md`
**Stage:** Phase 0 sketch. Only code is `demo/`.

## Verdict

Docs are strong and honest. Demo proves chat → mini-app → approval → merchant loop mechanically, but does not implement the v2 arc it claims. Founder direction since v1.0 is correct: drop bidding, go Talabat-normal discovery + WeChat execution, companion first / services last. That direction is not yet written into PLAN/ARCH/demo — doing that is the next doc commit, not code.

Ready to build? No — update PLAN §2/§3 + ARCH §3/§4 + DECISIONS first (1 commit), then Phase 1.

## 1. Research: what was actually read

All 5 files read in full.

| File | Lines | Verdict |
|---|---|---|
| `Deepseek-research.md` | 156 | Usable. 10-bullet summary, tables A–H, 15 quotes, hotel-concierge verdict (convenience layer, fails on price/speed/nights). Weakness: `Sources` column mostly empty, contest = "not published". |
| `Dubai Visitor Pain Points Research.md` | 248 | Strongest. 48-item works-cited. Fixes contest facts (below), fare structure, Metro hours/luggage, SIM trap, meds law, laundry markups. |
| `glm-research.md` | 53 | Not findings — priors + 4 anti-hallucination patches. Use for verification only. One good catch: WhatsApp text OK, voice/video restricted — verify if merchants rely on WhatsApp calling. |
| `qwen-research.md` | 59 | Discard. Failed run, meta-complaint about empty query, zero rows. |
| `research-prompt.md` | 68 | Original prompt, still marked ⏳ NOT RUN. Status line now stale — two tool runs exist. |

Key merged facts (high confidence): Metro no 24h (~05:00–00:00, Fri to ~01:00, last trains before close); T2 no Metro; taxi AED 20 sedan / 25 van + 2.62/km + Salik; RTA lost-item 104,162 reports 2025, ~2M cash, ~3k passports, 2h response via 8009090; hotel laundry AED 35–100/shirt, 24h cycle + 50–100% express, no overnight vs street AED 1–12; SIM 1GB expires 24h; Tourism Dirham 7–20 tiered; VAT min 250 via Planet; meds under Decree-Law 30/2021; EU roaming excludes UAE; Type G; Mon–Fri week.
Contest (from Pain Points report, needs portal check): launch 7 Oct 2026, submit Jan 2027 (prototype + deck + video), semi Feb–Mar, final first week May 2027 live working agent (video-only disqualified), prize >AED 2.5M. Closes `DECISIONS.md:35-37` open item.

## 2. Product direction: bidding → Talabat + WeChat, companion first

Founder is right. Evidence:

* Hero job (shirt by 09:00) is fixed-price, not negotiable. Bidding (`SUBMITTED → ACK → QUOTED → QUOTE_ACCEPTED → CONFIRMED`, `ARCHITECTURE.md:126-135`) adds latency to the task where latency is the failure.
* Research describes fixed lists + WhatsApp/Google discovery (`Deepseek:45-47`), Careem/Washmen 9:00–23:30, delays from missed turnaround — not auctions.
* Competitor matrix: talabat = No on all three tasks, Careem = Partly/Can, DubaiNow = guidance only. A Talabat-normal list (closest + ★ + price-from + turnaround) for independents is the gap — Careem laundry is 2x street price.

But pure Talabat clone kills `PLAN.md:67` jury answer. Keep:
* Discovery = Talabat-normal. `service_comparison` gains `distance_km, rating, rating_count, price_from, sla, open_now` (all `Sourced`, demo stars = `Demo data`). Sort closest + top-rated. Filter "can deliver by 09:00".
* Execution = WeChat (`ARCHITECTURE.md §6`). Per-merchant HTML, `allow-scripts` only, separate origin, scoped bridge. Correct, keep.
* Companion first / services last = priority, not timeline. Companion opens + closes demo (arrival → lost-bag payoff); services in middle only. Don't close on commerce.
* Kill the 10:00-vs-09:00 haggling beat. Replace with filter + fixed order + track. Keep custom quote as L3-only (tailoring/repair).
* Keep approval card (privacy differentiator), keep `order.request` with fixed total (rename from `quote.request`).

## 3. Critical (fix in docs before code)

* C1. PLAN §2 item 7 + §3 1:55–2:45 + ARCH §4 still specify bidding + deadline-conflict drama. Contradicts agreed direction. Rewrite to order lifecycle: `SUBMITTED → ACCEPTED/DECLINED → PREPARING → READY → COMPLETED` (+ `CANCELLED/EXPIRED/FAILED/UNKNOWN_STATUS`), idempotency kept.
* C2. `service_comparison` (`ARCHITECTURE.md:101`) has no rating/distance/SLA fields. Add them or Talabat sort is unbuildable.
* C3. Demo bridge uses `"*"` both ways (`demo/app.js:269`, `miniapps/foldpress.html:26`). Violates ARCH §6 strict-origin. Must not carry into Phase 1.
* C4. Mini-app CSP uses `unsafe-inline` (`miniapps/palmleaf.html:3`) vs ARCH `script-src 'self'` (`ARCHITECTURE.md:160`). Demo would fail real CSP.

## 4. High

* H1. No time-aware ride reasoning (PLAN §2 item 5). Demo shows static taxi/metro/app (`demo/app.js:140-155`), no 00:40 / T2 logic.
* H2. Taxi memory saves number only (`demo/app.js:162-177`). Missing roof colour, receipt photo, pickup/drop-off — breaks RTA-field recovery promise (`PLAN.md:31`).
* H3. No onboarding flow (PLAN item 9). Gate 4 untestable in demo.
* H4. No `fallback_card` on iframe timeout/offline (ARCH §6 item 5). Blank iframe = dead end.
* H5. Civic tab still in demo (`demo/index.html:44-52`) vs DECISIONS:19 remove. No `Scripted demo` label, no cyan host strip.
* H6. XSS pattern: `esc()` drops `'`, `state.dest` inserted unescaped (`demo/app.js:147,171,218`). Low risk now, breaks with free text.
* H7. Reload wipes everything (`demo/app.js:443`). OK for sketch, must not regress Gates 1/2.

## 5. Medium

* Only 2 destinations, 1 laundry (needs 3 laundries for showcase), Groceries/Tailors empty (`demo/data.js:66-121`).
* Chips permanently disable after tap (`demo/app.js:46`); sheets no Esc/focus-trap.
* `research-prompt.md:3` status stale; `VISITORS.md §0`, `PLAN.md §3`, `DECISIONS.md` not yet merged with new findings.
* qwen file should be deleted or marked failed to avoid future agents citing it.

## 6. What's good, keep

* Truth-in-status by construction (LLM reads/proposes, taps mutate) — `ARCHITECTURE.md:40`, `CLAUDE.md:39-48`.
* Provenance + pills everywhere; sandbox self-test (`palmleaf.html:55-64`) blocking `payment.charge` is a great jury moment.
* iOS light + cyan tokens implemented faithfully (`demo/styles.css:2-23`).
* VISITORS honesty grading (Strong/Medium/Weak) + hotel-concierge as open question + interview script.
* Modular monolith, no Redis/PostGIS/microservices; domain tables as system of record.

## 7. Next (in order)

1. 1 commit: PLAN §2/§3 (Talabat + order lifecycle + companion-first wording), ARCH §3/§4 (card fields + state machine + bridge scopes `order.request`), DECISIONS (bidding→order, contest dates, qwen discarded), VISITORS §0 (merge §1 facts), delete/mark qwen.
2. Patch sketch to arc v2.1: 3 ★-rated laundries, time-aware rides, RTA fields, remove Civic tab, scripted label.
3. Verify contest portal (deadlines/artifacts/IP) — re-anchor Phase dates.
4. Then Phase 1 scaffold. Don't extend `demo/app.js` — throwaway.
