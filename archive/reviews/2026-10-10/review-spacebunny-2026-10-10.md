# Review — dubai-io (independent, Space Bunny) · 2026-10-10

Read: PLAN, ARCHITECTURE, CLAUDE, docs/{DESIGN,DECISIONS,VISITORS,VISION}, docs/research/* (5), demo/* (7). Did not open docs/reviews/.
Provenance tags: `official` · `merchant` (vendor/commercial) · `user-supplied` (forum/review, not a survey) · `estimate` · `demo_fixture`.

## Verdict

The engineering spec is genuinely strong — `ARCHITECTURE.md:40,159-161` (agent reads/proposes, host builds the approval card, no `allow-same-origin`) is the best artefact in the repo, and the demo proves its own security claims instead of asserting them. The research run, however, **made the hero beat weaker, not stronger**: the one new first-hand report about an independent laundry shows it failing the deadline too. That undercuts "use a local shop instead of the hotel," which is the whole merchant pitch.

**Ready to build? No** — not because the plan is wrong, but because two binary unknowns (contest dates, laundry-vs-hotel evidence) are cheap to settle now and expensive after the Phase 1 scaffold anchors on them. No new code until they're settled.

## Research: per-file verdict

| File | Verdict | Why |
|---|---|---|
| `research-prompt.md` | **usable** | Well-built instrument; §3 patches in `glm-research.md:36-46` are the right fix for exactly the failure below. |
| `Dubai Visitor Pain Points Research.md` | **usable, with caveats** | Only file with real permalinks + numbered citations. But headline facts lean on SEO/affiliate sites (`dubaitripguide.com`, `dxblounges.com`, `uaeexperthub.com`) and `r/dubai` (expat-weighted, 2021-24), so its own "verified against official sources" claim (`:69`) overstates. Treat as leads, re-verify before merging. |
| `Deepseek-research.md` | **priors-only** | Every "Sources" cell in all five evidence tables (`:26-102`) is **empty**; all 15 quotes name a source with no link. Unciteable under `VISITORS.md:3`. Numbers are plausible and mostly corroborate the Pain Points file, but nothing here can be merged as evidence. |
| `glm-research.md` | **priors-only** | Explicitly self-labelled priors with a "verify at" column (`:3`). Ends mid-conversation (`:53`). Most honest file in the set. Its `:19` WhatsApp-calls caveat is the sharpest unexamined risk in the repo. |
| `qwen-research.md` | **discard** | Zero research content — a 59-line essay on why the prompt wasn't found. Delete. |

## Top 5 merged facts

1. **RTA handled 104,162 lost-property reports in 2025** — ~35,000 devices, ~3,000 passports, >AED 2M cash; most contacted within 2h. `official` (RTA Media Office Jan 2026) via `VISITORS.md:18` + `Deepseek-research.md:112-113`. **High.** The only figure with two independent restatements of one official release. Caveat: this proves *volume*, not that a visitor wants an app for it.
2. **No Metro at T2; station hours end ~00:00 (Fri ~01:00).** `official`/`estimate`, mixed. `VISITORS.md:19`, `Pain Points:20,83-91`, `Deepseek:81-82`, `glm:7-8` all agree. **Med-High on T2, Med on exact hours.** Only one `rta.ae` link exists (`Pain Points:204`) and it is a PDF nobody has opened.
3. **Laundry price/speed gap — the load-bearing fact for the hero merchant.** `merchant` + `user-supplied`. `VISITORS.md:22` rates it **Weak**. The research did **not** upgrade it: the only concrete hotel-price quote is a competitor's ad (`Deepseek:110`, Laundrykhalas claiming AED 40 vs its own AED 11); the Pain Points backing is expat threads about their own laundry (`:23,53`); and `Deepseek:117` quote 10 is a report that an **independent laundry missed the deadline too**. **Low.** This is a genuine regression in the pitch, not an upgrade.
4. **Car-rental deposit disputes are the highest-volume, highest-cost visitor complaint** (42% of tourist complaints, ~1,200/quarter). `official`/`user-supplied`: `VISITORS.md:20` (Khaleej Times/DET) + deepest first-hand corpus in the pack (`Pain Points` quotes 2,3,5,6). **Med-High on frequency; Low on "visitor" framing** — the corpus is `r/dubai`, resident-weighted.
5. **Hotel concierge fails deadline/urgent tasks** — outsourced laundry, cutoffs, no RTA integration. `user-supplied` + inference only: `Deepseek:128-134`, `Pain Points:51-55`. **Low.** Four research files ran and **none settled it** — and it is the single most decision-relevant unknown (`DECISIONS:35`, `VISITORS.md §1`). That the question survived a full research round *is* the finding.

## Product direction — my take on the 3 questions

**1. Bidding/quote vs Talabat-normal fixed order → neither; fixed price + a promised *slot*.**
*Agree with the founder on the beat, disagree on the mechanism.* The 10:00-vs-09:00 conflict (`PLAN.md:56`) is a **time** conflict and works fine without bidding. What bidding adds — price negotiation — has **zero** first-hand support anywhere in the four research files. Worse, the observed small-merchant channel is direct and fixed: merchants "rely heavily on WhatsApp as their primary communication, ordering, and invoicing channel" (`Pain Points:60`), and the stated workaround for a missed deadline is "confirm turnaround time in writing" (`Deepseek:48`), not "get more quotes." A merchant who can't price in ten seconds won't answer a bid request — so the flow adds cold-start friction on the side you have zero of (H7, `VISITORS.md:62`, is untested).
Concretely: keep `QUOTED`, but make it a merchant-submitted **slot + fixed price**, and collapse `QUOTE_ACCEPTED` (`ARCHITECTURE.md:130`) into the single approval you already have. Bidding can be a Phase 6 merchant-maturity level (`L3`, `VISION.md:28`), not the MVP spine.

**2. "WeChat for Dubai" as the execution layer → keep the sandbox, drop the slogan.**
The sandbox design is the best thing here and should survive intact. But note the internal contradiction: the differentiator is per-merchant mini-apps (`DECISIONS:25`, "The core differentiator"), while `ARCHITECTURE.md:164` explicitly says *"Dubai-io writes the single widget. Merchant-authored HTML is out of scope."* The two branded demo mini-apps are **your own HTML in merchant colours** (`demo/data.js:80-121`). The positioning bet is precisely the capability the architecture defers to Phase 4 (`PLAN.md:32`).
Reframe on what's actually built and can't be copied: **no merchant HTML can do anything — it can only ask the host to ask you.** That survives whether or not merchant-authored HTML ever ships, and it's provable on stage (`demo/app.js:273-277` really does block an out-of-scope `payment.charge`). Note also `glm-research.md:19`: UAE WhatsApp voice/video calling has been restricted and the status is in flux — that matters because WhatsApp is how merchants are actually reached (`Pain Points:60`), not because Dubai-io runs on it.

**3. Companion first / services last → yes, and take it further than the founder does.**
The evidence is asymmetric in your favour. Research is thick exactly where the companion lives (arrival, transport, lost items) and thin exactly where the services story lives (`Deepseek:151` admits the "repeated information" pain had "very few explicit first-hand reports"). Keep companion first — but move the **hero merchant off laundry** for the reasons in finding 3, and put the rental-deposit beat on stage as the evidence-backed story (`DECISIONS:36` already flags it). Be honest about the trade: deposits are a *dispute/evidence* flow, not a *merchant-order* flow, so it strengthens the demo's evidence and weakens its marketplace coherence. That trade is worth making, but it's the founder's call, not a silent one.

## Issues

**Critical**
1. `docs/research/qwen-research.md:1-59` — null result sitting in the evidence folder. Anyone skimming `docs/research/` will read it as a source. Delete or archive.
2. The hero beat's evidence got *worse*, not better, after research (`VISITORS.md:22` Weak; `Deepseek:110` vendor ad; `Deepseek:117` quote 10 independent-also-failed; `Pain Points:23,53` expats). Yet laundry is still the centre of gravity (`PLAN.md:46`, `DECISIONS.md:16`).

**High**
3. `Deepseek-research.md:26-102` — every source cell empty, no links. Cannot be merged as evidence under `VISITORS.md:3`.
4. Contest dates contradict across files: `Deepseek:97-102` "Not published" vs `Pain Points:178-184` (submission Jan 2027, final first week May 2027, AED 2.5M pool, with official-domain links). `PLAN.md:75,113` still assumes unanchored. Settle before Phase 1.
5. The demo is arc **v1**; the plan locks **v2** (`PLAN.md:84` ticked, `PLAN.md:77` Phase 0 closed) while `PLAN.md:89` admits the sketch still needs the deadline branch, time-aware rides and RTA fields. Confirmed absent: `demo/app.js:140-155` reasons from nothing but destination; `demo/app.js:409-411` has taxi number/route/time but **no roof colour, plate or receipt photo**; `demo/index.html:44-52,75` Civic tab still shipped despite `DECISIONS:19`.
6. `demo/app.js:262-265,269,275` — no `e.origin` check and `postMessage(..., "*")`. `ARCHITECTURE.md:161` requires "a strict `origin` check on both sides". Since `demo/` is the declared reference implementation (`ARCHITECTURE.md:3`), it demonstrates the opposite. Same at `demo/miniapps/foldpress.html:26`.
7. `demo/miniapps/foldpress.html:3`, `demo/miniapps/palmleaf.html:3` — widget CSP is `script-src 'unsafe-inline'`; `ARCHITECTURE.md:160` mandates `script-src 'self'`. And `demo/index.html:88` prints "sandbox · no network" as a UI string a static server cannot enforce.

**Medium**
8. `demo/app.js:351` — `total = estimate + 7`. On stage, "5 shirts × AED 5" (`foldpress.html:20`) becomes **AED 32.00**. Arithmetic checks are a live jury risk.
9. `demo/app.js:359` — `provenance: "merchant_reported"` is not in the enum at `ARCHITECTURE.md:72-73` (`merchant_submitted`). `CLAUDE.md:67`: that's a bug.
10. `CLAUDE.md:19` and `research-prompt.md:3` still say the research "has not been run yet" — stale after four files, and the `results-*.md` naming convention wasn't followed, so the "remind the founder" trigger will now fire forever.
11. `demo/index.html:122`, `demo/app.js:444`, `demo/data.js:80-121` — 3 pharmacies to 1 laundry; inbox still says "Order something from a pharmacy mini-app". Arc v1 talking.
12. `demo/app.js:419` — "I'll check in with you tomorrow morning about the bag" with no scheduler behind it. The demo promises the exact capability the pitch claims.
13. `Pain Points:43,53` — a **Paris** hotel FlyerTalk thread is cited as support for Dubai's 24-hour hotel laundry cycle. Wrong geography; do not merge.
14. `Pain Points:69` claims official-source verification for facts sourced to affiliate sites and `r/dubai`. Downgrade the claim or upgrade the sources.

## Good — keep

- `ARCHITECTURE.md:40` and `:159-161`. Read/propose vs mutate, no `allow-same-origin`, `connect-src 'none'`, host builds the approval card. This makes truth-in-status structural rather than a promise.
- `ARCHITECTURE.md:134` — "stays SUBMITTED; UI shows *Waiting for merchant* (no invented status)". The anti-lying detail most teams skip.
- `demo/app.js:262-282` + `palmleaf.html:55-63` — the sandbox self-test actually fires `payment.charge` to be denied live. A demo that proves the claim instead of asserting it.
- `demo/app.js:112-121` — "I'm lost" → landmark → resume, with no fake indoor GPS.
- `docs/VISITORS.md:3,52` — evidence vs hypothesis separated, frequency/consequence/workaround split. That discipline is why finding 3 was visible *before* the research landed.
- `PLAN.md:42` NEVER + `CLAUDE.md:39-48`. Unusually disciplined for a pre-seed repo.

## Next 4 actions

1. **Rule on laundry, in `docs/DECISIONS.md`.** Either (a) keep laundry as the *mechanism* demo while the rental-deposit beat carries the *evidence*, or (b) run the 5-interview script (`VISITORS.md §5`) before Phase 1. Do it before scaffolding — `PLAN.md §2 item 7` and `§3` both hang off it.
2. **Verify the contest on official sources only** (`dubaichamberdigital.com`, Dubai Media Office / WAM) and resolve contradiction #4. Binary, cheap, and it re-anchors every phase date.
3. **Rebuild `demo/` to arc v2 in one pass** — deadline-conflict branch, time+terminal ride reasoning, RTA field set, drop Civic, drop pharmacy from the main path, add the "Scripted demo" label. Right now the demo cannot be shown against `PLAN.md §3` without reading as under-delivery.
4. **Fix contract/trust drift now, because it becomes the scaffold's seed:** strict origin checks + `script-src 'self'`, `merchant_submitted` provenance, kill the `+7`, and either script the follow-up promise or delete the line.

*(Ordering is deliberate: 1 and 2 are decisions, not code, and both are far cheaper now than after the Phase 1 scaffold commits to them.)*