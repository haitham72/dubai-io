# OPUS HANDOFF — Finalize Dubai-io (10 Oct 2026, Owner: Haitham)

You are finalizing, not exploring. Canonical docs are already fixed for your run — obey them over all reviews.

## 1. Authority (highest first)

1. This file + `docs/DECISIONS.md` 2026-10-10 rows (founder locks, final)
2. `CLAUDE.md` (hard rules) → `PLAN.md` v1.1 draft → `ARCHITECTURE.md`
3. `docs/DESIGN.md`, `docs/VISITORS.md`, `docs/VISION.md` (vision adds no scope)
4. `docs/research/` (evidence only — see §4)
5. `docs/reviews/` (advisory only — see §5)
6. `archive/` — reference only, never build from it

If anything below contradicts PLAN/ARCH, this file wins and you must port the fix back into PLAN/ARCH in the same commit.

## 2. Founder locks (DO NOT REOPEN, no alternatives, no "hybrid")

1. **Bidding/quote ABSOLUTELY REJECTED.** No `quote.request`, `quote.read`, `cart.request`, `rx.request`, `pickup.request` as concepts, no `QUOTED`, `QUOTE_ACCEPTED`, `PROVIDER_ACKNOWLEDGED`, no price negotiation, no second approval. `Money.kind` is `fixed | from_estimate | fixture`. If you find the word "quote" in PLAN/ARCH/demo (except this ban), delete it or rename to fixed order.
2. **Every service opens as a MODAL HTML mini-app.** Services / shops / stores / rides — same pattern: Talabat-normal list row → tap → modal `<iframe sandbox="allow-scripts">` (separate widget origin, `connect-src 'none'`, strict `origin` check both sides) → fixed menu → `order.request` → host builds `action_approval` (single approval, fixed total + shares list) → merchant accepts/declines at published price → ready → completed. Fallback card if load fails in 3 s / offline / unapproved manifest.
3. **Discovery is Talabat-normal.** `service_comparison` rows sorted closest + ★ highest, showing price-from (fixed), `distance_km`, `rating` + `rating_count` (Sourced or omitted — NEVER invented; demo = `Demo data` pill), `turnaround_sla`, `open_now`. Filter "can deliver by 09:00" is the agent value-add.
4. **Companion first, services last.** Companion (arrival, memory, proactive, lost-bag payoff) opens + closes demo and pitch. Services live only in the middle as fulfillment. Positioning: "One conversation, every local shop as a mini-app." Never pitch as super-app/platform first (category = Best Personal AI Agent).
5. Deadline beat = **time conflict on a FIXED price** (ready 10:00 vs need 09:00 → ask earlier → 08:30, price unchanged). No re-quote.

## 3. Final state machine (copy verbatim into ARCH §4 + contracts)

```
DRAFT ─► AWAITING_APPROVAL ─(user approves send, single approval)─► SUBMITTED
SUBMITTED ─(merchant accepts)─► ACCEPTED ─(merchant marks ready)─► READY ─(merchant marks done | user reports done)─► COMPLETED
SUBMITTED | ACCEPTED | READY ─(merchant)─► DECLINED
any non-terminal ─(user)─► CANCELLED
any non-terminal ─(ttl)─► EXPIRED
SUBMITTED ─(no accept within N min)─► stays SUBMITTED; UI shows "Waiting for merchant"
adapter error unknown outcome ─► UNKNOWN_STATUS
```

Terminal: `COMPLETED, DECLINED, CANCELLED, EXPIRED, FAILED`. Every transition = 1 `action_events` row + 1 outbox row. `Idempotency-Key` on approve + all merchant commands.

## 4. Research — how to use it

* `Dubai Visitor Pain Points Research.md` (248 lines, 48 cites) — strongest, use it. Contest dates reported: submit Jan 2027 (prototype+deck+video), final first week May 2027 live (video-only DQ), prize >AED 2.5M, launch 7 Oct 2026.
* `Deepseek-research.md` (156 lines) — usable but Sources columns EMPTY, quotes have no URLs. Do NOT merge its claims into VISITORS/DECISIONS unless independently linked.
* `glm-research.md` — priors only, self-labelled. Keep WhatsApp voice/video caveat.
* `qwen-research.md` — DISCARD (failed run, zero Dubai content). Delete or leave untouched; never cite.
* Still open: verify contest facts on OFFICIAL portal only (dubaichamberdigital.com, Media Office/WAM), then re-anchor PLAN §4 dates. Do not re-run forum research.

## 5. Reviews — how to weight them

Five files in `docs/reviews/`. They conflict on bidding — resolved as follows:

* `review-claude-2026-10-10.md` — ALIGNED with founder (fixed order). Follow its §7 next-actions.
* `review-mimo-2026-10-10.md` — best on contracts (auto-quote→fixed + `ready_by` first-class, bridge-scope drift ARCH §6 vs `data.js`, Civic-tab contradiction). Follow its fixes, but its "neither/both" on bidding = rejected; fixed-only wins.
* `review-spacebunny-2026-10-10.md` — best on evidence regression (laundry beat got weaker, Paris-cite error, `+7` math bug, `merchant_reported` enum bug). Follow its fixes.
* `review-cline-2026-10-10.md` Q1 + `review-llm-2026-10-10.md` §1 — **REJECTED.** They argue to keep bidding/quote. Founder overrules (DECISIONS 10 Oct). Do not follow, do not compromise, do not add L3-bidding "later" to the MVP.

## 6. What you must deliver (in order)

1. `PLAN.md` → v1.1 final: §§1–3 with §§2 locks above, jury answers without "quote", Gate 3 = double-tap→one order, carried items rewritten (no "deadline-conflict branch" quote language; research = portal-check only).
2. `ARCHITECTURE.md`: §3 card fields (`distance_km, rating, rating_count, turnaround_sla, open_now`), §3.3 `propose_order_request`, §4 machine verbatim, §6 `order.request`-only + modal-for-all-four + fallback, §7 triggers (accepted/ready), §9 tabs (kill Civic everywhere — ARCH §9 + DESIGN + demo still contradict DECISIONS:19), `providers` table gets area/rating/price-list/hours/SLA columns.
3. `docs/DECISIONS.md`: one row confirming finalize + portal-check result.
4. `demo/` patch to arc v2.1 in ONE pass: 3 ★ laundries (Talabat rows → modal HTML), time+terminal ride reasoning (00:40/T2), RTA taxi fields (plate/receipt photo/roof colour/route/start), drop Civic tab, `Scripted demo` label, cyan approval, persistent Demo pill on status cards, strict origin + `script-src 'self'`, kill `+7`, fix `merchant_reported` → `merchant_submitted`, migrate all bridge kinds to `order.request`.
5. Report: portal-check outcome, remaining contradictions (file:line), 10 clean demo runs ≤4:00 readiness.

## 7. NEVER (Opus must enforce)

Fake Confirmed/Booked/Paid/Filed/Verified/Delivered · invented positions, belts, gates, queues, prices, ratings, distances · any bidding/quote/negotiation UI, copy, state, test, or comment · government execution · DubaiNow look · background geofencing · payments/escrow · merchant HTML calling the API · `allow-same-origin` · `postMessage "*"` in new code · new planning docs.

Go.
