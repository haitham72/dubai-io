# Dubai-io — Review of the Full Package

**Date:** 9 Oct 2026 · **Reviewed:** `dubai-io-handoff/` README + 01–08 (≈ 220 KB), `dubai-io-implementation-plan.md`, `cursor-plan_review.md`, `Muse-report.md`, `screens/` (5 images)
**Output of this review:** `CLAUDE.md`, `PLAN.md` and `ARCHITECTURE.md`, which resolve everything below.

---

## Verdict

**The product idea is strong, and the honesty rules in `04` and `05` are the best part of the package. But no single document is actually in charge.** Four files say "`00-MVP-FREEZE.md` is the build authority", and that file does not exist. The implementation plan, which is the document a builder would actually follow, was rewritten from `08`'s pitch rather than from `05`'s MVP. As a result it plans exactly the things the other docs ban. Do not start coding from it.

Ready to build? **Yes, from `PLAN.md` + `ARCHITECTURE.md`**, once the Phase 0 items below are done.

---

## Critical (fix before any code)

**C1. The build authority is missing.** `README`, `05`, `07` and `08` all defer to `00-MVP-FREEZE.md`. It was never written (Muse's report says "in progress"). Nothing is binding, so every agent picks its own favorite doc.
→ `PLAN.md` §2 is now the freeze. `CLAUDE.md` holds the authority table.

**C2. The implementation plan contradicts the handoff it claims to implement.** `dubai-io-implementation-plan.md`:
- says "Approved & Finalized … locked", while `08` now says it is *not* build authority
- still uses "Dubai Now" naming, which README v1.4 says was renamed everywhere
- plans "Salik and DEWA balance … top-up approval flow", "petrol delivery hook" and "recovery truck dispatch". `05 §6` and `08 §2` forbid government execution
- uses gates that can't be measured ("100% … zero hallucinations", "runs seamlessly")
- squeezes everything into 28 days, while `05 §4` schedules Oct→Jan

Also, `cursor-plan_review.md` praised an **earlier** version of this file (dated 8 Oct, with a gap list covering `QUOTED`, `requires_approval`, outbox, evidence upload). That gap list was lost in the rewrite, so Cursor's "earns its keep" no longer applies.
→ Marked superseded in `CLAUDE.md`. The gaps are closed in `ARCHITECTURE.md §3–4`.

**C4. The `08 §5` demo script breaks `08`'s own rules.** It says "Tasjeel Al Barsha has a 10-minute wait right now", "Top up Salik 50 AED, and book the test" → "verified confirmation receipt", "evaluates 3 **real** providers", and "Reserve Pierchic?". Every one of these is a live claim or a government/third-party execution the package forbids. The opening line "Gentlemen of the jury" also excludes part of the jury; use "Members of the jury".
→ Replaced by the `PLAN.md §3` demo.

**C5. The widget sandbox spec is exploitable as written.** `04 §4b` says `sandbox: 'allow-scripts allow-same-origin'` and `connect-src https://api.dubai-io.example`. If the widget is served same-site, `allow-scripts` + `allow-same-origin` lets the frame remove its own sandbox. And `connect-src` to the API lets widget HTML call the backend directly, which contradicts the rule two lines below ("HTML never touches DB/tools").
→ `ARCHITECTURE.md §6`: separate origin, `allow-scripts` only, `connect-src 'none'`, bridge-only.

**C6. There's no version control, and several agents are editing the canon.** There's no git repo. Muse's report is dated **10 Oct** (tomorrow) and says it edited `04 §4b` and "done in docs". README has had four revision passes. Nothing can be diffed or rolled back.
→ `PLAN.md` task 0.2: `git init` first.

---

## High

**H1. The state machine is incomplete.** The `04 §6` enum has no merchant *decline* and no second user approval between `QUOTED` and `CONFIRMED`. As specified, a merchant quote could be followed straight by a merchant confirm, without the user ever agreeing to the price. `OPTIONS_READY` mixes card state with request state.
→ `ARCHITECTURE.md §4` adds `DECLINED` and `QUOTE_ACCEPTED` and drops `OPTIONS_READY`.

**H2. The card schema in the implementation plan doesn't carry the honesty fields.** It has no `schema_version`, `as_of`, provenance or `demo` flag. `providers: List[dict]` is untyped. `VehicleStatusCard.nearest_test_center: str` has no source. `CardAction.payload: dict` lets the model write executable payloads. `html_widget` and `citation_answer`, the two cards that carry the thesis, are missing.
→ `ARCHITECTURE.md §3`.

**H3. The "Jarvis" pillar is built on signals a PWA doesn't have.** `08` MM-01…MM-03 depend on geofence, motion and "navigation heading toward DXB". The `08` demo shows "Geofence signal: user enters Dubai Hills Mall". `02 §15` and `05 §6` correctly say a PWA can't do this. The honest version (scheduled reminders, state-change notifications and a labelled demo trigger) still demos well.
→ `ARCHITECTURE.md §7`, with the "Demo trigger" pill.

**H4. External dependencies are on the critical path, and nobody owns them.** The pilot merchant, the legal corpus and the contest rules/IP terms all have to come from the founder, not from code. Cursor flagged this; it still has no owner or date.
→ `PLAN.md §5`, with owners, dates and fallbacks.

**H5. The contest facts are unverified.** Cursor states that registration opened 7 Oct 2026, the build window is Nov–Jan, and the final is in May 2027, with no source captured. The category name and IP terms are also unverified. IP ownership matters if the founder has an employer.
→ `PLAN.md` task 0.1 + `docs/contest-rules.md`.

---

## Medium

**M1. The nav conflicts.** `01` says Companion / Discover / Community / Me; the screens say Companion / Services / Civic / Me. → I picked the screens' version (`ARCHITECTURE.md §9`); Community is out of the MVP.

**M2. "Lock style C" needs a qualifier.** All four options in `4 styles.png`, C included, use the DubaiNow home layout (favorites Salik/DEWA/Vehicles/Parking, Pay/Apply/View, My Hub), which is the same clone risk Muse rejects in S4. Lock C's **visual language** only. The home layout comes from S1 (chat-first).

**M3. Honesty gaps in the screens, beyond those Muse lists:**
- S1: the "As of … Apr 24, **2025**" stamp has the wrong year. The assistant line says "two **highly rated** laundries", which is an unsourced claim.
- S3: a gold **verified badge** on BrightLaundry, which implies verification that doesn't exist.
- S2: "reach **thousands** of residents" is an unbacked claim in the onboarding banner. "Request pickup" reads as L4; use "Request quote".

**M4. Doc sprawl.** About 250 KB of markdown, and `06` alone is 100 KB. `07` tells agents "do not respond with objections", which is an instruction aimed at a specific tool (Sol / ChatGPT Work) that sits inside a spec and works against review. Numbering is also confused: `07` ends with "End of Document 08", and `06` says X01–X14 while it defines X01–X20. → Treat 01/03/06/07/08 as a reference library (`CLAUDE.md`). Don't add more planning docs.

**M5. The stack is over-specified for one builder.** `02` lists PostGIS + Redis, and the plan adds S3, webhooks, multi-provider LLMs and a LangGraph checkpointer as the state store. → Dropped Redis, PostGIS and webhooks; one LLM provider behind config; **domain tables are the system of record**, not the checkpointer (`ARCHITECTURE.md §5`).

**M6. "Automatic visitor/resident switching"** in the plan has no specified mechanism. → It is a user setting.

**M7. Parking "visual OCR capture"** turns a simple feature into an accuracy risk. → OCR may pre-fill; the user confirms; the photo plus text is the record.

---

## Low

Typos: "concantenates" (impl plan §1); "Phase 3 … (Days 15)" / "(Days 20)" (`08 §6`). `08` header says "Visitor & Resident" but the roadmap leaves out dual-mode. The `05 §5` "≥95% RAG" target is fine as an aspiration, but report measured numerators.

---

## What's good, keep it

- The **truth-in-status** discipline (`01 §5`, `04 §2/§6`, `06 §0`) is a real differentiator in front of a jury.
- The **L1–L5 capability levels** and "many provider records, few capability contracts" (`04`, `07 §3.2`) are the right platform thesis.
- `05`'s **hero journey** (laundry → merchant ack → damage → cited recovery) is the strongest demo spine. My demo keeps it and adds Jarvis moments that are honest.
- Screens **S1, S2 and S3** are good canonical visuals: chat-first, with `Sandbox example` and `As of` labels and a manifest/fallback footer. Muse's verdict to archive the Montage clone is right.
- The modular monolith (Next.js + FastAPI + one LangGraph + Postgres) is sized correctly.

---

## Reconciling the earlier reviews

| Point | Cursor | Muse | This review |
|---|---|---|---|
| Write an MVP freeze | Yes | Yes (00-MVP-FREEZE) | Done as `PLAN.md` |
| `html_widget` in MVP | Not discussed | Yes, 1 merchant | Yes, first-party widget, item 4 in the order of sacrifice |
| Demo spine | 05 journey | S1→S2→S3 | Both: 05 journey staged on S1–S3, plus parking memory and onboarding |
| Style | — | Lock C | Lock C's visual language, not its home layout |
| Civic vehicle/Salik | Out | Display + handoff | Out of the demo; at most a "Pilot" placeholder |
| Missed by both | | | Missing freeze file, impl-plan regression, sandbox escape, no git, state machine gaps |

## Immediate next actions (in order)

1. Founder: sign `PLAN.md §8`. Verify the contest rules, deadline and IP terms.
2. `git init`; commit everything as-is; move the Montage screen to `screens/archive/`.
3. Founder: start pilot merchant outreach and the legal corpus list this week.
4. Builder: Phase 0 scaffold + contracts.
