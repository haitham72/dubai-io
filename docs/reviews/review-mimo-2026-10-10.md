# Review — MiMo · 2026-10-10 · independent (`docs/reviews/` not opened)

Read in full: `PLAN.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `docs/{DESIGN,DECISIONS,VISITORS,VISION}.md`, all 5 files in `docs/research/`, `demo/{index.html,app.js,data.js,styles.css}`, `demo/miniapps/{foldpress,palmleaf}.html`. Listed only: `demo/maps/` (4 images), `archive/reviews/` (3 files), `demo/miniapps/` (4 files — all 4 referenced by `data.js` exist).

## Verdict
Docs are unusually disciplined (authority ladder, provenance rules, honest self-labelling) and the demo already *demonstrates* the two hardest claims — sandboxed merchant HTML and status that only merchants change. But the research folder has a stale status line, one failed run and two mis-citations, and the bridge/state contracts drift between `ARCHITECTURE.md` and `demo/`.
**Ready to build? Yes** — Phase 1 (contracts, chat, cards) is not blocked by any of the three open questions — **on condition that Q1 and the bridge scope list are ruled in week 1 of Phase 1, before `packages/contracts` freezes** (`CLAUDE.md:67`).

## Research — per-file verdict
| File | Verdict | Why |
|---|---|---|
| `docs/research/research-prompt.md` | **usable** (instrument, not findings) | Anti-hallucination rules at `:56-60` are good; status at `:3` is now stale |
| `docs/research/Deepseek-research.md` | **priors-only** | Every evidence-table Sources column is empty (`:28-31`, `:37-39`, `:81-91`) and the 15 "verbatim first-hand quotes" have no URLs (`:108-122`) |
| `docs/research/Dubai Visitor Pain Points Research.md` | **usable, with 2 flags** | 48 numbered citations incl. official RTA/DET/u.ae/Dubai Chamber (`:201-248`); but `:53` cites `[22]` = "Tipping culture" for AED 50–100/shirt pricing and `[43]` = Park Hyatt **Paris** for Dubai turnaround |
| `docs/research/glm-research.md` | **priors-only** | Self-declared (`:1-3`); leaked transcript tail at `:53` |
| `docs/research/qwen-research.md` | **discard** | Failed run — a meta-essay about the user's empty prompt (`:5-9`), zero Dubai research |

### Top 5 merged facts (confidence)
1. **104,162 taxi lost-property reports in Dubai in 2025**, incl. ~3,000 passports and >AED 2M cash; most contacted within 2h — provenance **official** (RTA figures, `VISITORS.md:18`; RTA Media Office quote `Deepseek-research.md:112`) — **High**.
2. **After midnight the Metro is not an option, and T2 has no Metro station** — provenance **official/guide** (`VISITORS.md:19`; `Pain Points:83` citing dubaiairports.ae + RTA; `glm-research.md:7-8`) — **High** on the fact, **Medium** on exact hours/fares (official sources conflict: AED 20 vs AED 25 flagfall, `Pain Points:7`).
3. **Hotel laundry is expensive/slow; concierge is thin at budget and serviced properties** — provenance **vendor + user-supplied reviews** (`Deepseek:110` quotes *Laundrykhalas*, a seller; `Pain Points:51-55`; `VISITORS.md:22` rates it **Weak**) — **Medium-Low**: consistent across 3 files, no official price source.
4. **Car-rental deposits are the #1 tourist complaint (42%)** — provenance **consumer-protection figures via Khaleej Times** (`VISITORS.md:20`), corroborated by first-hand threads (`Pain Points:24-25`) — **Medium-High**. Matches `DECISIONS.md:36`.
5. **Contest launched 7 Oct 2026 by Dubai Chamber, prize >AED 2.5M, submission Jan 2027 (prototype + deck + video), May 2027 live final; judging criteria and IP terms not published** — provenance **press/secondary** (`Pain Points:14`, `:176-197` citing dubaichamberdigital.com, BusinessWire, tbreak; `Deepseek:97-102` = "not published") — **Medium**: dates not yet confirmed on the official page.

## Product direction — the three questions
**Q1: bidding/quote (ARCH §4) or Talabat-normal fixed order? → Neither, and not both equally: fixed `price-from` as the default, quote only for rush/custom, and `ready_by` promoted to a first-class field.**
The visitor persona has no local knowledge and no time (`VISITORS.md:45`); making them bid re-creates the "chase replies" pain we claim to remove (`VISITORS.md:57`, H2). Our own growth story assumes publishable prices — onboarding ingests a **price list** (`PLAN.md:32`, `ARCHITECTURE.md:111`) and `foldpress.html:20` already shows "AED 5 each". Meanwhile the current "quote" is arithmetic, not merchant judgement: `app.js:351` sets `quote = estimate + 7` with a fixed eta, and `app.js:383` fires it 2s after ack. What genuinely needs a merchant turn is **time, not price** — the pitch's one agentic beat is a *deadline* conflict (`PLAN.md:56`, `DECISIONS.md:17`), and no deadline exists anywhere in demo state (`app.js:7`). Recommendation: keep ARCH §4's state machine as transport (it already models approval #2 on price, `ARCHITECTURE.md:130`), but change merchant default behaviour to "auto-quote from the published price list + ready-by slot", human quote only when the price list can't cover it. Renders like Talabat in <2s, needs no state-machine rewrite, and preserves the deadline beat. Star-sorting must wait: zero verified ratings exist and saying otherwise breaks `CLAUDE.md:40` (`app.js:230` is honest today).

**Q2: "WeChat for Dubai" as the execution layer? → Yes for the contest, but rename it.**
The security claim is real and demoable, not aspirational: `ARCHITECTURE.md:159-164` (no `allow-same-origin`, `connect-src 'none'`, scoped bridge), proved live by `palmleaf.html:55-64` (network/storage/cookies/top-nav blocked, `payment.charge` denied at `app.js:273-277`). Merchant branding contrast is a designed differentiator (`DESIGN.md:19`, `DECISIONS.md:25`). Three caveats: (a) `ARCHITECTURE.md:164` says **Dubai-io writes the single widget** — so today this is a rendering claim, not a network/platform claim; (b) the scopes the demo actually sends (`cart.request`, `rx.request`, `pickup.request` — `data.js:89`, `:99`, `:109`) are not in the architecture's MVP list (`quote.read`, `quote.request` — `ARCHITECTURE.md:161`), and `quote.read` is unused by the demo; (c) production CSP `script-src 'self'` (`ARCHITECTURE.md:160`) is violated by both mini-apps' inline scripts (`foldpress.html:3`, `palmleaf.html:3`) and by any photo-generated mini-app. Call it "sandboxed merchant mini-apps" until one real merchant ships HTML.

**Q3: companion first / services last? → Yes, with one correction: companion *only*, not companion-plus-a-second-entry-point.**
"Companion = product, mini-apps = mechanism" is the right call (`DECISIONS.md:15`, after an external review said the demo read as three products) and `PLAN.md:12` states it cleanly. But the demo still ships Services as a co-equal browse tab (`index.html:35-42`, `:75`) plus a Civic tab the founder already removed (`DECISIONS.md:19`, `PLAN.md:38`) that literally says "Not part of this demo" (`index.html:50`) — while `ARCHITECTURE.md:200` still mandates Civic "for MVP", contradicting `CLAUDE.md:13`. Keep Services as a thin registry shortcut for the jury; kill Civic everywhere in the same commit.

**Where I disagree with the founder:** the arc spends 1:10–2:45 on the laundry beat (`PLAN.md:55-56`), the *weakest*-evidenced beat (`VISITORS.md:22`, `DECISIONS.md:10`), while the best-evidenced one (`VISITORS.md:26`) gets 3:05–3:40. Make the taxi-memory payoff the through-line — it already starts at 0:35 with plate capture (`PLAN.md:52`) — and present laundry as the *mechanism* demo, not the pitch's claim.

## Issues
**Critical**
- `PLAN.md:122` says contest rules/deadline/IP were needed by **Phase 0**; still open (`DECISIONS.md:37`, `PLAN.md:88`) — yet `Pain Points:182`, `:197` already report a Jan 2027 submission and a May 2027 live final requiring a working agent. If true, dates re-anchor *now*; `PLAN.md:75` currently makes every gate a guess.

**High**
- `CLAUDE.md:19` + `research-prompt.md:3` still say the research was never run and order every agent to nag the founder about it — four result files already exist. Agents will keep requesting duplicate work; `PLAN.md:87` repeats it.
- Bridge-scope contract drift: `ARCHITECTURE.md:161` vs `data.js:89/99/109`. `CLAUDE.md:45` requires card-action ids to match registry capability ids — freeze the scope list before contracts.
- The deadline beat has no code path: `app.js:7` (no deadline in state), `app.js:330` (the foldpress pickup slot in `p.summary` is discarded because `p.items` is non-empty), `app.js:351` (fixed fake quote). This is the demo's headline moment (`PLAN.md:56`) and it is unbuilt (`PLAN.md:89`).
- `Deepseek-research.md:28-39`, `:108-122`: no links anywhere. Do not merge any of its claims into `VISITORS.md §0` unless independently linked (only fact #1 above already is).

**Medium**
- Civic tab survives its removal: `DECISIONS.md:19` / `PLAN.md:38` vs `ARCHITECTURE.md:200`, `DESIGN.md:23`, `index.html:44`, `:75`.
- CSP mismatch: `ARCHITECTURE.md:160` vs inline scripts at `foldpress.html:3`, `palmleaf.html:3` (plan a bundler, or amend the CSP).
- `postMessage(..., "*")` outgoing (`app.js:269`, `:275`, `palmleaf.html:40`) vs "strict origin check on both sides" (`ARCHITECTURE.md:161`). Fine in demo, fix in Phase 3.
- Dead research files will get quoted by someone: `qwen-research.md` (failed run) and `glm-research.md:53` (leaked transcript tail). Delete or rename to `results-*` per `research-prompt.md:2`.
- Demo state machine omits `EXPIRED` / `UNKNOWN_STATUS` / `FAILED` (`app.js:313-320` vs `ARCHITECTURE.md:130-136`), and `AWAITING_APPROVAL` is never held (`app.js:341` → `:343`) though `app.js:387` filters on it. Expected at sketch stage; must not survive into Phase 3.

## What's good — keep
- Truth-in-status enforced by construction (`ARCHITECTURE.md:40`) and *visible* in the demo: illegal transitions rejected with a security log (`app.js:348`), "Not filed yet" / "Bag not recovered yet" (`app.js:409`, `:416`), honest handoff card (`app.js:205`).
- Provenance pills rendered everywhere, not just documented (`styles.css:91-96`, `app.js:62` "You told me").
- The sandbox self-test button (`palmleaf.html:55-64`) is the best single jury moment in the repo — it *proves* the security rule instead of asserting it.
- `VISITORS.md` argues against itself: it labels its own hero beat Weak (`:22`) and keeps the hotel-concierge question open (`:31-39`). Rare.
- `CLAUDE.md:37-48` (10 non-negotiables) and the one-line-per-decision log (`DECISIONS.md`) are strong; don't dilute them.

## Next 4 actions, in order
1. Verify the contest deadline, artifacts, judging criteria and IP on the official Dubai Chamber page; re-anchor `PLAN.md §4` dates. Closes `PLAN.md:122`.
2. Fix research bookkeeping: set `research-prompt.md:3` to partial/partially-run, rewrite `CLAUDE.md:19`, rename the four files to the `results-*` convention, discard `qwen-research.md`.
3. Rule Q1 (auto-quote from price list + `ready_by`) and freeze the bridge scope list → then write `packages/contracts` for `service_requests` and manifests.
4. Build the deadline-conflict beat into `demo/` (`PLAN.md:89` item 1) so the arc on stage matches `PLAN.md §3`.
