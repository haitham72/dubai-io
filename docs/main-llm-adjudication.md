# Dubai-io: adjudication of the review set

**Date:** Mon 19 Oct 2026 · **Branch:** `redesign` @ `678c083`, plus uncommitted working-tree edits to `CLAUDE.md`, `README.md` and `docs/gemini-review.md`
**Status:** review only. Nothing in this file amends canon or authorizes implementation. No code was changed.
**Method:** every claim below was checked against source, git history (`main`, `build`, `redesign`) or test output. Review text was not accepted as evidence.

**Baseline (run today):** `pytest -q tests` → 40 passed, 11 skipped (1.64 s). Node: `profile` 92, `recovery` 8, `luna-client` 7 → 107 checks, all passing. The 11 skips are the live Luna golden cases, gated on `RUN_LIVE=1`. **CI proves the deterministic layer and skips the AI layer.**

**Scope note:** the brief names three reviews. `docs/` holds five: Enhancement (ER), Gemini (GR), Space-bunny (SB), Muse (MU), Sol (SO). The brief's §3 anchors are essentially SB's findings, so I re-derived them from source myself. MU and SO are included where they break a tie or catch something the others missed.

---

## §1 Verdict

1. **Winnable: yes.** The thesis fits the category: the portal describes Best Personal AI Agent as "agents that help people live better every day". The trust architecture is real code (`apps/api/app/actions.py:185-221`). The visual shell is ahead of every review's description of it.
2. **Not submittable today.** No order has ever gone end-to-end. The approval card a judge will tap makes zero network calls and then fabricates `SUBMITTED` → `ACCEPTED` → "Confirmed" on timers (`apps/web/offers.js:215-224`).
3. **The single blocking thing: one real order path.** Today there are two: the fake one in `offers.js` and the honest one in `service-workflow.js`, which always returns `BLOCKED`. Neither reaches a merchant, because no merchant surface, adapter or push path exists.
4. **The canon blocks the fix.** `PLAN.md:363` forbids editing `offers.js` in favour of a branch that no longer exists. `PLAN.md:236` puts a Postgres profiler ahead of any other backend work. Both need a founder ruling before engineering starts.
5. **Runway.** The portal (fetched today) says submission is January 2027, prototype + pitch deck + demo video, with the day not stated. Plan to the 6-week worst case: **rehearsal-ready Fri 20 Nov**, submission package by Fri 18 Dec.

---

## §2 Claims table

Verdicts: **TRUE** (verified, cited) · **FALSE** (contradiction cited) · **PARTLY** · **UNVERIFIED** (external fact, not re-researched per brief) · **OUT OF SCOPE** (may be correct, but not contest work) · **LOCK** (violates a founder lock).

### 2.1 The brief's own anchors (§3 a–l)

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| a | At the documented entry point Luna never runs | **TRUE**, with one nuance | `chat.js:18` `enabled: location.pathname.startsWith('/lab/')`. `main.py:124-126` redirects `/` → `/index.html`. `luna-client.js:25` returns the router with `fallback_reason:'Offline demo'`. Nuance: `main.py:6` (docstring) points to `/lab/home-v2-cyan.html`, a byte-identical file (`cmp` checked) where Luna **does** run. Two documented entry points behave differently. |
| b | No merchant inbox | **TRUE** | `merchant\|inbox\|backstage` across `apps/` matches only labels, fixture copy and comments (`offers.js:2,66,159,213,218,221`, `chat.js:98`, miniapp fine print). No route, view or accept/decline control. |
| c | No adapter registered; `prepare` always `BLOCKED` | **TRUE**, and wider | `actions.py:63-70`: all 8 capabilities have `adapter=None`. `:155` gives `BLOCKED`. Also `fixed_total_aed=None` on all 8, so the honest path carries **no price at all**. The laundry price exists only client-side (`offers.js:12-15`). |
| d | No push path | **TRUE** | The only timer in `apps/web` is placeholder rotation (`app.js:719`). No EventSource, WebSocket, BroadcastChannel or service worker. |
| e | `offers.js:201-225` fabricates merchant states | **TRUE, and worse than stated** | (1) `:217` mints a client-side `DIO-####` reference in the engine's reference format. (2) `:218` posts `SUBMITTED` **without** `sim:true`, so it renders as real (`chat.js:98` labels only `sim` steps). (3) `:223` prints the word "Confirmed" (CLAUDE rule 1). (4) **New finding:** for merchant mini-apps with no `items` (all laundry and pharmacy rows), `:193` builds the total from widget-supplied `x.price`, contradicting its own comment at `:187` and `ARCHITECTURE.md §6.4`. The laundry widgets send `price` (`miniapps/marinaexpress.html:34`, `foldpress.html:34`). |
| f | Offers sort by price, not closest + ★ | **TRUE** | `offers.js:94,106` default `'value'` = `a.from - b.from`. No provider has a distance field. The chat card does the same: "Cheapest first" (`chat.js:133-134`). Contract: `ARCHITECTURE.md:106`. |
| g | Places/Routes exist, zero callers, OSM fixture map | **TRUE** | `google_maps.py:29` (`provider_confirmed`), `:42` (`estimate`). Grep for `api/places\|api/route` in `apps/web` → none. `map.js:1-4,25`. |
| h | No proactive pipeline | **TRUE on `redesign`** | No outbox, scheduler, `dedupe_key` or trigger route in `apps/`. v1 had a client-side 2.5 s dedupe on the `build` branch (`build:demo/app.js:653,677`). Its scenes include mosque/qibla/wudu prompts, which presume religion (rule 9), so they must not be ported as-is. |
| i | `profile.js` is real, not a stub | **TRUE for the math. The safety claim is overstated** | Beta/half-life/supersession are real (`profile.js:13-38,55-80`). But it only ever runs on fixture `EPISODES` (`app.js:267,296,479`). `allowed()` (`profile.js:86`) is **never called by app code**, only by tests. Confirm/Not true/Forget live in memory (`app.js:132,500`), so Forget is lost on reload. There is no sensitive-trait guard in code; safety comes from the curated fixture list. |
| j | `PLAN.md:363` forbids editing `offers.js` for a deleted branch | **TRUE** | `git branch` → `build, main, redesign`, no worktree. `handoff.md:33`. The same lock repeats at `PLAN.md:374, :380, :384`. |
| k | Dead refs (`:279`, `:216`, `:278`, `:265`) | **TRUE, with one correction** | `demo/run.md` and `demo/luna.js` **exist on `build`**, not "on no branch". The v1 port symbols (`laundryDeadline`, `laundryMerchantFlow`, `TRIGGERS`, `fireTrigger`, `traceByCard`, `traceByCash`, `rtaReport`) are at `build:demo/app.js:251,268,653,677,973,1035,1057`. They are **not on `main`**: main's 12 `demo/` files lack them. Caveat: v1 `laundryMerchantFlow` is itself a `sleep()` script that moves the order to `COMPLETED` as "merchant". Porting it ports a fake. |
| l | §7.9 asserts a Luna client that never fires at `/` | **TRUE** | `PLAN.md:378`. Same at `CLAUDE.md:13` ("Web chat calls Luna on the API origin") and `handoff.md:46-47`. |
| — | "12 idea service cases" | **FALSE** | `cases.md:37-50` has **8** at `idea`: C1, C2, C3, C7, C8, C11, C12, C13 (C13 needs a plan change). |
| — | GR §4 says `demo/lab/` is the live frontend; GR tells you to simulate Accept and make Luna emit priced cards | **TRUE at HEAD**, corrected in the working tree | `git show HEAD:docs/gemini-review.md` lines 70, 101, 104. The working-tree copy was rewritten by SB (uncommitted). "Simulate the merchant tapping Accept" is **still live in `handoff.md:78`**. |

### 2.2 Enhancement Review (ER)

| Claim | Verdict | Evidence / note |
|---|---|---|
| §0.2: authority sits in `00-MVP-FREEZE.md`, `05-CONTEST…`, docs 01–08 | **FALSE** | These files exist on no branch (`git ls-tree` over main, build and redesign). ER's authority framework points at nothing. |
| Line 8: written without inspecting code | **TRUE** (self-declared) | It explains every repo-shaped error in ER. |
| §1.1 "comparison, **quote**"; §4.1 **L3 Quote**; §4.4 "quote/slot flow" and agency "quote"; §6.1 `service.quote_updated`; §10.2 `QUOTED`, `OPTIONS_READY`; D03-C "quote inbox"; Spike M "quote request" | **LOCK** | Lines 51, 175, 206, 211, 258, 394, 406, 477, 560. `OPTIONS_READY` was also dropped (`ARCHITECTURE.md:145`). The code honours the lock: no `quote`/`QUOTED` in `apps/`. Related: the asset `design/screens/Dubai Laundry Quote App Mockup.jpg` is named against the lock. |
| §2.1 seven-day arc ending on a simulated fine approval | **OUT OF SCOPE** and NEVER-adjacent | `PLAN.md §3` ends on taxi memory. `PLAN.md:58`: fines are display-only. |
| §3 Google facts (credit excludes AI Studio; Custom Search closed; Places caching limits) | **UNVERIFIED** | External. Not re-researched (brief §6). Custom Search is irrelevant: nothing in the repo uses it. |
| §4.2–4.3 Amazon/Noon; §5 Docling/crawling; §7 human desk; §9 video commerce | **OUT OF SCOPE** | `PLAN.md §2` LATER/absent. |
| §6.2 "manual trigger → real orchestrator → persisted notification" is honest | **TRUE as a principle, not implementable today** | No outbox (2.1 h). |
| §8 telemarketing HOLD | **OUT OF SCOPE for the build. Keep the hold** | Legal citations **UNVERIFIED** by me. |
| §10.3 "LLM proposes, deterministic server executes" | **TRUE**, matches code | `graph.py:13-14,166-169` replaces any reply containing claim/price words. `actions.py:204-209` evidence gate. |
| §10.4 "build one real integration first" | **TRUE** as direction | The repo has zero today (2.1 c). |
| §11 four-tier truth labels | **TRUE as a need** | Adopt as a stage-strand label, not a provenance value (§3, conflict 5). |
| §16.10 "scope inflation" | **TRUE**, and it applies to `PLAN.md §2` itself | §5. |

### 2.3 Gemini review (GR): HEAD version, plus the working-tree "corrections"

| Claim | Verdict | Evidence / note |
|---|---|---|
| Adopt truth-in-status, single proof, compliance hold | **TRUE** (agree) | — |
| HEAD §4: `demo/lab/` is the frontend; archive `demo/` | **FALSE** now | Deleted in `678c083`. |
| D03: merchant dashboard "built in apps/api / lab backstage" | **FALSE** | 2.1 b. |
| D08-A: native typed cards by default | **LOCK** (mini-app lock) | `PLAN.md:39`, `ARCHITECTURE.md §6`. The working-tree correction is right. |
| Working-tree Step 0: `thanks` intent drift "throws and silently drops the turn" | **FALSE** | `thanks` is a **router-only** intent (`chat.js:36,56`). Luna cannot emit it (`schema.py:8`), so `mapUnderstanding` never sees it. The `chat.js:127` branch is live on fallback. GR (working tree) and SB both assert this; **both are wrong**. |
| Working-tree Step 1: `ActionStore.session()` "hands every caller a fresh anonymous owner" | **PARTLY** | A fresh owner is issued only when there is no valid cookie (`actions.py:93-101`). "No roles" is TRUE. |
| Step 2: adapter returning `{provenance:'provider_confirmed', reference}` is the intended shape | **TRUE** | `actions.py:207`. |
| Step 4: price drift already 409s | **TRUE** | `actions.py:196-197`. |
| Provenance of the file itself | **Problem** | The working-tree GR now carries SB's opinions (e.g. D02 → B, "best dropped entirely") under Gemini's name. The file no longer records what Gemini said. |

### 2.4 Space-bunny (SB)

| Claim | Verdict | Evidence / note |
|---|---|---|
| Luna gate, no inbox, no adapter, no push, fake `offers.js` path, price sort, no Places callers, no outbox | **TRUE** | 2.1 a–h. |
| `allowed()` makes hypotheses "structurally incapable" of prefill/approval | **FALSE as stated** | Never called by app code (2.1 i). |
| JS profiler "already satisfies rule 9 and item 12" | **PARTLY** | It satisfies the math. Item 12 ("learns over time") needs real episodes and persisted overrides. |
| "12 idea cases" | **FALSE** | 8. |
| `demo/run.md` "exists on no branch"; "v1 survives on main" | **FALSE / PARTLY** | Both exist on `build`; main lacks the port symbols. |
| Taxi payoff "already built", keep it | **TRUE in code, but conflicts with canon** | `recovery-state.js:37` `PREPARED_NOT_FILED`, 8 tests. But `PLAN.md:343,371-372` and `cases.md:42` record the founder's **rejection** of that handoff and put C6 at `rebuild`. See conflict 11. |
| Routes "needs real coordinates against a fixture basemap" | **FALSE** | Routes needs two coordinates, not a basemap. DXB terminals are constants; the hotel area is user-supplied. |
| Places list row on Services | **TRUE, if not plotted** | SB is silent on the policy issue. SO is right that Places results must not be drawn on the MapLibre map (`map.js:4` and `PLAN.md:324` already say a Google map is needed). |
| Deadline worst case "~10 weeks" | **FALSE arithmetic** | A Dec-1 deadline is 6 weeks. The portal now says January (§7). |
| `.env` has a valid OpenAI key | **PARTLY** | Present (1 non-empty key line). Validity is unverified without spending credits. |
| SB edited `CLAUDE.md`, `README.md` and `gemini-review.md` in place | **Process issue** | The edits are factual and the commands now run (I re-ran them). But a reviewer edited canon plus another reviewer's file, uncommitted. §9. |

### 2.5 Muse and Sol (tie-breakers only)

| Claim | Verdict |
|---|---|
| MU: could not run backend tests ("environment-blocked") | Its backend claims are unverified by MU itself; my run passes. |
| SO: `PLAN.md` Step P precedes any backend feature, so merchant-first plans breach canon | **TRUE** (`PLAN.md:236`, `ARCHITECTURE.md:293`). The only review to catch it. |
| SO: Places-on-MapLibre policy trap | **UNVERIFIED** externally, consistent with `map.js:4` and `PLAN.md:324`. |

---

## §3 Conflicts between the reviews, and rulings

| # | Conflict | Positions | Ruling |
|---|---|---|---|
| 1 | D02 voice | ER C, GR (HEAD) C · SB, MU, SO B | **B, push-to-talk, and optional.** Voice is not in `PLAN.md §3`, and there is zero audio code. It ships only after Gates A–C (§7). |
| 2 | D05 fine appeal | ER A, GR A, `handoff.md:80` "fine appeal twist" · SB, MU, SO D | **D, remove.** See §4. |
| 3 | Profiler sequencing | SB: keep JS, no Postgres · SO: Postgres Step P first · canon: Step P first (`PLAN.md:236`) | **Founder amendment needed (§9-2).** Recommendation: merchant loop first. Keep the profiler as a completion gate, met with the JS math plus SQLite episodes and overrides on the existing store. No Postgres or pgvector for the contest. |
| 4 | Resident/VIP (item 10) | PLAN IN (founder, 12 Oct) · SB cut · MU, SO cut via the cut order | **Defer to LATER for the January submission; revisit for the May final.** It is item 2 of PLAN's own cut order, with zero code and no reference images (`PLAN.md:199`). |
| 5 | Truth taxonomy | SB: add `future_concept` to `Provenance` · ER: separate stage tags | **Separate `strand` label** (`live_internal \| simulated_external \| future_concept`) on stage events. Don't fork the canonical provenance enum (CLAUDE rule 2) for a presentation concern. |
| 6 | Two order paths | SB, GR (working tree): delete the fake · `handoff.md:78`: "simulate the merchant tapping Accept" | **One path.** The `offers.js` approval calls `/api/actions/prepare` and `approve`. Delete `:215-224`. Prices come from a server catalog. Correct the handoff line. |
| 7 | D08 cards vs mini-apps | ER, GR: native cards by default · lock | **The lock wins.** Native card = fallback only. |
| 8 | D07 Google | SB: Places first, Routes if time · GR: both · SO: Places list, no map | **Routes first, for the ride ETA. Places second, as an attributed list never plotted on MapLibre.** See §4. |
| 9 | Proof of novelty | SB: run twice on stage · ER: one open voice variation | **Once on stage with the scripted line. Then invite a judge to type their own request in Q&A.** That costs no stage time and is more convincing. |
| 10 | Who is the merchant | ER: real pilot · `PLAN.md §5`: real or labelled sandbox · SB: a sandbox is "stronger than a real merchant" | **A sandbox operator (teammate on a second device) is the floor; a real merchant is the May-final stretch.** I disagree with SB: a sandbox is weaker evidence, just honest and sufficient. |
| 11 | C6 taxi payoff | SB: built, keep · `PLAN.md §7.8`: manual handoff rejected, agentic execution required · rule 4 and `PLAN.md:58`: no government execution | **Unaddressed canon conflict.** §7.8 cannot be met for RTA without a government capability, which rule 4 forbids. For the contest, `PLAN.md:41` (item 8: prefill → official handoff → "not recovered") must govern C6. Founder ruling in §9-1. |
| 12 | Deadline | SB: Dec, ~10 weeks · canon: Dec vs Jan unresolved | **Portal (today): January 2027, day unstated.** Plan to a 6-week worst case anyway. |

---

## §4 Rulings: D01, D02, D05, D07

**D01: agentic proof = A, the merchant loop, made checkable.** The proof is complete only when all six hold:

| Test | Requirement | Today |
|---|---|---|
| Understanding | Luna (live, at the real entry point) maps a free-text ask to a registered `service` and extracts the deadline as a `user_supplied` fact (`schema.py:11` already has `deadline`) | Gated off (`chat.js:18`) |
| Approval | One card lists recipient, fixed total (server catalog) and exact fields; binds the snapshot hash and revision | Engine built (`actions.py:185-199`). The visible card is fake |
| Dispatch | A registered adapter writes to the merchant inbox; `SUBMITTED` only with a reference (`actions.py:207`) | `adapter=None` |
| Actor | `ACCEPTED`/`READY` come only from a merchant-role session on a second device | No roles, no inbox |
| Follow-through | The server compares `ready_at` with the deadline deterministically and offers "ask for earlier"; price is immutable (`actions.py:196-197`) | No code on `redesign` |
| Delivery | The update arrives in the open chat in under 1 s and survives reload | No push path; status cards don't restore (`chat.js:80`) |

Pitch it honestly: the LLM understands, the server decides and executes, and a person on the merchant side confirms. That is the architecture ER §10.3 recommends. Reject B (a recommendation is not agency), C (no government partner, and rule 4) and D (browser agent on contest Wi-Fi).

**D02: voice = B, push-to-talk, typed is the default.** A wake phrase fails against PA bleed and swallows narration (ER §16.5 names this failure). PTT removes it structurally. Show the live transcript, and let the user edit it before the turn runs. There is no audio code today, so this is a 1.5-day spike that must not displace the floor. Whether iOS Safari's speech API is good enough in the hall is untested. Run ER Spike V (20 phrases, noisy room) before committing.

**D05: fine appeal = D, remove it from the entry.**
1. It is not in `PLAN.md §3`, so removing it restores canon.
2. It is NEVER-adjacent (`PLAN.md:58`, rule 4).
3. Its proposed slot lands about 90 s after the one real confirmation, exactly where the audience is judging whether "Accepted" was real.
4. It depends on Gmail OAuth, which is unconfigured (`oauth.py`; Connect disabled per `PLAN.md:358`).

Delete it from `handoff.md:80`. If it survives anywhere, it belongs in the deck as a labelled `future_concept` slide, never in the app thread.

**D07: Google = A, in a specific order.**
1. **Routes:** one call for the ride card (DXB terminal constant → user-given hotel area), labelled `Estimate · Google`. It replaces the hard-coded "35–45 min" (`guide.js:77`) inside an existing demo beat (`PLAN.md:68`). Half a day.
2. **Places:** an attributed "Live nearby" list on Services or results, with a field mask, `place_id` as pointer, no persistence and **no MapLibre pins**. It is discovery only, never offers: no prices, no turnaround (rule 2). Half a day.

Reject B (a second model vendor with uncertain credit coverage, and the app doesn't need grounding) and C (Gmail serves the removed fine story). At stage plus rehearsal volume, cost is negligible. The real risk is display policy, not price. Check the actual billing account before relying on the $300.

---

## §5 Scope cuts (recommended, not applied)

PLAN's own cut order is `11 → 10 → 9 → 5 → 4` (`PLAN.md:48`). Floor: 1, 2, 3, 6, 7, 8, 12, 13.

| Item | Code today | Recommendation |
|---|---|---|
| 11 Service cases | 8 `idea` cases, none built | **Freeze.** No new cases before submission. Laundry (C4) is part of item 7, not a "case". |
| 10 Resident/VIP | none; no images (`PLAN.md:199`) | **LATER for January.** It reverses the 12 Oct founder decision, so it needs a founder ruling. Revisit for the May final. |
| 9 Photo onboarding | none on `redesign` (`cases.md:46` "built (v1)" refers to deleted code) | **Out of the submission cut.** Its 20 s slot (`PLAN.md:73`) goes to the proactive beat. Candidate for the May final. |
| 5 Ride reasoning | **built** (`guide.js:22-82`, incl. 00:40 demo-time toggle) | **Keep.** No review credits it. |
| 4 Arrival guide | **built** (guide + belt + landmark) | **Keep.** |

Also hold until after submission (all canon targets nobody will ship by January): React/Vite/TS port (`PLAN.md:152-178`), `packages/contracts` codegen, Postgres/pgvector, the `ARCHITECTURE.md §12.4` cold-path profiler graph, OAuth on stage, and dark mode.

**Do not cut** the separate widget origin. Rule 10 is non-negotiable and today's `srcdoc` (`offers.js:166`) does not meet it. None of the three named reviews flags this. A second static origin is about one day (§7).

---

## §6 Staleness sweep

| File:line | Says | Reality |
|---|---|---|
| `PLAN.md:363`, `:374`, `:380`, `:384` | `offers.js` owned by `feat/miniapp-bridge`; don't edit; review the branch | Branch deleted. **This protects the main disqualification risk.** |
| `PLAN.md:236` | Step P before any other backend feature | Conflicts with every reviewer's merchant-first plan (§3-3) |
| `PLAN.md:278` | `/` → `/lab/home-v2-cyan.html`; endpoint list | `/` → `/index.html` (`main.py:126`). List omits `/api/session*`, `/api/actions/*`, `/api/auth/*`. |
| `PLAN.md:279` | Run instructions in `demo/run.md` | Only on `build`. Use `README.md`. |
| `PLAN.md:216-227` | Port from `demo/lab/`, `demo/app.js`, `demo/data.js`, `demo/luna.js` | Port symbols live on **`build`** only. Several are `sleep()` simulations. The trigger scenes include religion-presuming prompts. |
| `PLAN.md:265` | `demo/_ref/visuals-libraries.md` | `docs/references/visuals-libraries.md` |
| `PLAN.md:269` | Contrast with `demo/luna.js` | On `build` only |
| `PLAN.md:343` | v1 `recovery`/`traceByCard` in `demo/app.js` | On `build` only |
| `PLAN.md:14`, `:96` | `demo/` "retired"; Phase-0 `demo/` checkbox | Deleted |
| `PLAN.md:106` | Lab parity incl. time-aware ride reasoning still open | Ride reasoning is done (`guide.js:22-82`); the deadline branch is not |
| `PLAN.md:77` | Inbox labelled "Merchant role, simulated" | Becomes wrong once a real operator taps. Use "Sandbox merchant · live". |
| `PLAN.md:112`, `:152-178`, `:251` | Phase-1 monorepo with `apps/widgets`/contracts/Postgres; §6 titled "Vite + React + TS"; `npm run dev` | No `package.json`. Contradicts §7.1 "HTML first". |
| `PLAN.md:378` | Luna client is real | True in code, but gated off at `/` |
| `ARCHITECTURE.md:3` | "Reference implementation of the UI: `demo/`" | Deleted |
| `ARCHITECTURE.md:6` | Current code is in `apps/web/`… and "`apps/web` … not built" | Self-contradictory (means the React target) |
| `ARCHITECTURE.md:179` vs reviews | `POST /demo/triggers` vs `/api/demo/triggers` | Pick one before building |
| `ARCHITECTURE.md:206` | Legacy tokens `demo/styles.css` | Deleted |
| `CLAUDE.md:13` (working tree) | "Web chat calls Luna on the API origin" | Not at `/` |
| `CLAUDE.md` rule 5 | `screens/archive/` | `design/screens/archive/` |
| `CLAUDE.md` + `README.md` | (uncommitted SB edits) | Factually correct now; commit them deliberately or revert them |
| `docs/handoff.md:4` | Read order ends at GR | Five reviews now exist; it should end at the adjudication |
| `docs/handoff.md:46-47` | Luna "falls back gracefully" | It always falls back at `/` |
| `docs/handoff.md:66` | "100 passed" | 107 across 3 files (it omits `luna-client`) |
| `docs/handoff.md:76-80` | Luna returns the Approval Card; "simulating the merchant tapping Accept … confirmed status"; "fine appeal twist" | Rule 7 (Luna is understanding-only, `graph.py:13`); institutionalises the fake; outside canon |
| `docs/services/cases.md:40` | C4 laundry deadline "built (v1 demo)" | **Not on `redesign`.** The flagship beat looks built and isn't. |
| `cases.md:45-46` | C9, C10 "built (v1)" | Deleted from the tree |
| `cases.md:137,140,143,155` | `demo/app.js`, `demo/lab/*.js` paths | `apps/web/*` or `build` branch |
| `docs/services/intake.md:52` | Registry in `demo/lab/data.js` | `apps/web/data.js` |
| `docs/references/redesign.md` (4×), `visuals-libraries.md` (1×) | `demo/` paths | Stale |
| `apps/web/tests/profile.test.mjs:1` | `node demo/lab/tests/…` | `apps/web/tests/` |
| `apps/api/app/main.py:6` | Open `/lab/home-v2-cyan.html` | Contradicts README's `/`. It is the one entry where Luna runs. |
| `docs/DUBAI-IO_Product_Enhancement_Review.md` §0.2 | Authority docs 00–08 | Exist nowhere |
| `design/screens/Dubai Laundry Quote App Mockup.jpg` | Filename | Names a forbidden concept. Archive or rename. |

Documentation hygiene: five reviews now disagree in `docs/`. Don't add a sixth planning file (CLAUDE.md forbids it). Record the founder's rulings in the existing "Founder decisions" header of `PLAN.md` (lines 5-12). Add a one-line "Adjudicated 19 Oct — see `main-llm-adjudication.md`; frozen" status to each review.

---

## §7 Dated critical path

**Portal facts** (fetched 19 Oct via `dubaichamberdigital.com/en/create-ai-agents`; read through a summariser, so confirm by eye and archive a dated screenshot):
- Registration closes January 2027, and "Submit Your Agent & Pitch Deck" is January 2027. Neither day is stated.
- Artifacts: AI agent prototype, pitch deck, demo video.
- Grand Final: first week of May 2027.
- Eligibility: global (UAE residents and international); this page states no Dubai-licence requirement.
- Judging criteria: none published. IP terms: not stated.
- Note one rule: "original, not copied from an existing repository". Confirm that MIT ports with notices (ShipSwift shaders, vendored libs) are acceptable.

**Runway**

| Scenario | Deadline assumed | Runway from 19 Oct | Target |
|---|---|---|---|
| S-worst (FAQ-style December) | Tue 1 Dec 2026 | 6 weeks | Rehearsal-ready Fri 20 Nov, package by 27 Nov |
| S-portal (January, day unknown) | Fri 1 Jan 2027 | ~10.5 weeks | Same build plan; package by **Fri 18 Dec** (avoids holiday plus unknown day) |
| Grand Final | early May 2027 | ~6.5 months | Real merchant pilot, items 9/10 reconsidered, iPhone polish |

**Plan** (built to S-worst; S-portal gets the slack). One engineer-agent. Estimates are working days. Each step ends at a binary gate.

| When | # | Work | Files | Done means | Days |
|---|---|---|---|---|---|
| Mon 19 – Tue 20 Oct | 0 | Founder rulings §9-1/2/3; doc unlock | `PLAN.md` header + `:363/:374/:380/:384`, `handoff.md:76-80` | `offers.js` editable; D05 and C6 rulings recorded | founder |
| Tue 20 Oct | 1 | Luna gate on API reachability, not pathname | `apps/web/chat.js:18`, `luna-client.test.mjs` | At `/`, the network tab shows `POST /api/luna/turn`; the badge says LangGraph; offline still falls back | 0.5 |
| Tue 20 Oct | 2 | Latency baseline (paid; needs approval) | `RUN_LIVE=1 pytest` + 20 demo utterances | p50/p95 recorded; if p95 > 8 s, stage runs on `LUNA_EFFORT=medium` | 0.5 |
| Wed 21 – Thu 22 Oct | 3 | **One order path** | new server catalog (laundry items + fixed prices) in `apps/api/app/actions.py` or a sibling module; `offers.js:187-224`; `chat.js:133` | Mini-app approval → `prepare`/`approve`. Total rebuilt server-side; tampered widget price ignored (test). No `setTimeout`, `SLOT_CONFIRMED` or client ref. Sort is closest + ★ via `distance_km` (`demo_fixture`) | 2 |
| Fri 23 Oct | 4 | Separate widget origin (rule 10) | `main.py` (second static app/port), `offers.js:156-166` | Mini-apps load by `src` from the other origin, `sandbox="allow-scripts"`, CSP `connect-src 'none'`; bridge `e.source` check kept; out-of-scope kind blocked (test) | 1 |
| Mon 26 – Tue 27 Oct | 5 | Merchant role, canonical transitions, inbox adapter | new `apps/api/app/merchant.py`; `actions.py` (roles; `ACCEPTED`, `READY`, `COMPLETED`, `DECLINED`, `EXPIRED`; `Idempotency-Key` on merchant commands) | Adapter returns the inbox reference. Merchant-isolation test. Accept/decline/cancel tests. Double approve = one order | 2 |
| Wed 28 – Thu 29 Oct | 6 | Merchant inbox UI | new `apps/web/merchant.html`, `merchant.js` | Queue, Accept / Mark ready / Decline; fixed total read-only; "Sandbox merchant" label | 1.5 |
| Thu 29 – Fri 30 Oct | 7 | Push and durable cards | `GET /api/stream` (in-process SSE) + 1.5 s poll fallback; `chat.js:80-100` renders status from the server action | **Gate A:** approve on phone → appears on second device → Accept → phone updates in < 1 s; reload restores the card | 1.5 |
| Mon 2 – Tue 3 Nov | 8 | Deadline follow-through | `actions.py`/`merchant.py` (`ready_at`, deterministic conflict check against the `user_supplied` deadline, `request_earlier` capability, price immutable); `chat.js` | 10:00 → conflict flagged → ask earlier → merchant sets 08:30 → "meets your deadline", with no status word lacking an event. Happy and decline tests | 2 |
| Wed 4 – Thu 5 Nov | 9 | Outbox, scheduler, demo trigger | new outbox and reminders tables; `POST /api/demo/triggers` (operator-only); merchant events routed through the outbox | **Gate B:** same trigger twice → one message; reload persists; `Demo trigger` pill; quiet hours honoured (test) | 2 |
| Fri 6 Nov | — | Buffer / Gate A+B regression | — | All suites green; `rg "quote\.\|QUOTED\|SLOT_CONFIRMED"` empty | 1 |
| Mon 9 – Tue 10 Nov | 10 | Profiler floor (per §9-2) | SQLite episodes from real taps (viewed/chosen/approved), persisted overrides; `app.js` calls `allowed()` at re-rank/prefill boundaries | Profile changes from what the user actually does. Forget survives reload. Tier-leak test (no hypothesis reaches approval, prefill or proactive) | 2 |
| Wed 11 Nov | 11 | Taxi-memory payoff on the stage path | `guide.js:101-112`, `recovery.js`, arc copy, "Scripted demo" label | Plate/roof saved in the guide pre-fill the report; asks only for the bag description; ends "Prepared, not filed" plus official handoff | 1 |
| Thu 12 Nov | 12 | Routes ETA; Places list (optional) | `guide.js:77`, `services.js`/`places.js` | ETA labelled `Estimate · Google`; attributed list, no pins | 1 |
| Fri 13 Nov | 13 | Docs reconciliation (approved items only) | `PLAN.md`, `ARCHITECTURE.md`, `handoff.md`, `cases.md`, `intake.md` | §6 table cleared; checkboxes ticked | 1 |
| Mon 16 Nov | 14 | PTT voice spike (only if Gates A, B and 10 are green) | `chat.js` composer | 20 noisy-room phrases measured; transcript editable; typed fallback | 1.5 → cut-able |
| Tue 17 – Fri 20 Nov | 15 | Rehearsal | stage script (`PLAN.md §3`, with 2:45–3:05 → proactive "shirt ready" reminder) | **Gate C:** 10 clean timed runs ≤ 4:00 on phone + second device; fallback video recorded; live golden set green | 3 |
| 23 Nov – 18 Dec | — | Submission package | deck, demo video, deploy (host + domain or tunnel), small user test, real-merchant attempt (`PLAN.md §5`) | Submitted with dated portal evidence | — |

Load: about 22 engineering days against 24 working days to 20 Nov. Steps 12 and 14 are the first to drop. Steps 3, 5–8 and 15 cannot be compressed.

---

## §8 Judge scorecard (if submitted today)

A champion-category technical judge would most likely say: **"Beautiful and principled. The one interaction that matters is a `setTimeout`."**

| Dimension | Today | Unfinished or wrong? |
|---|---|---|
| Problem / category fit | Strong: arrival → deadline → lost item is concrete and personal | — |
| Visual and UX craft | Strong: shader stage, captive-Wi-Fi arrival, guide with honest Metro reasoning | — |
| Trust architecture | Excellent **in the backend**: snapshot-bound approval, idempotency, evidence gate, `UNKNOWN_STATUS` (`actions.py`); LLM claim-stripping (`graph.py:166-169`) | **Unfinished:** none of it is on the path a judge taps |
| Agent depth | Weak: the LLM is a classifier/slot-filler (`schema.py`), and gated off at `/` | Partly **design**: "LLM understands, server executes" is defensible but must be pitched explicitly, with the deadline check as visible follow-through |
| End-to-end execution | **Fails:** no order has ever reached a merchant; no adapter, inbox or push path | **Unfinished** |
| Honesty of what's shown | **Fails** on the flagship card: unlabelled fake `SUBMITTED` + random ref + "Confirmed"; widget-priced totals | **Unfinished**, but disqualifying if seen. A judge with devtools open sees zero fetches. |
| Proactivity ("Jarvis") | None | **Unfinished** |
| Memory | Told facts are real (API + view/edit/forget). The profile is fixture playback whose Forget doesn't persist | **Unfinished** |
| Engineering hygiene | Good deterministic tests; the AI layer is skipped in CI; two divergent order paths; canon contradicts the code in ≥ 10 places | Mixed |

**Where the idea itself is wrong** (fix by decision, not code): the seven-day film with a simulated fine verdict; Resident/VIP as IN with zero code; a profiler-first gate that blocks the product's proof; a canon still describing a React/Postgres/codegen build that won't exist by January; `§7.8`'s demand for agentic RTA execution, which collides with rule 4.

**Where the build is just unfinished:** inbox, adapter, push, the deadline loop, outbox, widget origin, profiler ingestion, voice. All small, all known, about 4.5 weeks.

---

## §9 What the founder must decide, and by when

1. **By Tue 20 Oct: lock the arc and unlock the code.**
   - Strike the bridge-ownership lock (`PLAN.md:363/374/380/384`) and mandate one order path.
   - Rule D05 = remove, and strike `handoff.md:80`.
   - Rule that C6 meets `PLAN.md:41` (item 8: prefill + official handoff + "not recovered") for the contest, and that §7.8's agentic-execution demand does not apply to RTA, since rule 4 forbids it.
   - Decide whether to commit SB's uncommitted edits to `CLAUDE.md`/`README.md` and revert its rewrite of `gemini-review.md` to Gemini's own text. Correcting the content is fine; signing Gemini's name to it is not.
2. **By Wed 21 Oct: scope and sequencing amendment.**
   - Approve merchant loop first, with the profiler (item 12) as a completion gate met by the JS math plus SQLite. No Postgres/pgvector for the contest.
   - Move Resident/VIP (item 10) to LATER for January, reversing 12 Oct.
   - Take photo onboarding (item 9) out of the submission cut; it is a May candidate.
   - Freeze new cases.
3. **By Fri 23 Oct: deadline, spend and the merchant.**
   - Confirm the portal facts by eye, archive a dated screenshot, and re-anchor `PLAN.md §4` to the Fri 20 Nov rehearsal and Fri 18 Dec submission.
   - Approve live-model spend for the latency baseline and pre-rehearsal golden runs.
   - Name who operates the sandbox merchant device on stage, and whether to try for a real merchant before the May final.

*Stop point: no implementation until these are answered.*
