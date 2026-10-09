# Dubai-io — Contest Plan & MVP Freeze

**Date:** 9 Oct 2026 · **Status:** Proposed. It becomes binding when the founder signs §8.
**Replaces:** `dubai-io-implementation-plan.md` (roadmap) and the missing `00-MVP-FREEZE.md`. On scope, this file outranks `handoff/05–08`.

---

## 1. The one sentence

> One conversation where Dubai-io remembers what matters, gets a real local merchant to answer a real request, and, when something goes wrong, tells you what the official rules actually say.

## 2. MVP freeze

### IN (build these, nothing else)

| # | Capability | Proves |
|---|---|---|
| 1 | Persistent chat: login, history and cards survive a reload, SSE streaming | Companion |
| 2 | Registry search → `service_comparison` card (1 real pilot merchant + ≤2 labelled fixtures) | Services |
| 3 | Quote-request loop: approval → merchant inbox → acknowledge/quote/decline → user accepts → merchant confirms, all updating live | Real action |
| 4 | One first-party `html_widget` (laundry quote) with sandbox, bridge and fallback | WeChat inner-HTML thesis |
| 5 | Civic RAG over a curated consumer-protection corpus → `citation_answer` + evidence + `complaint_draft` + official handoff | Civic trust |
| 6 | Scheduled in-chat reminders (deduplicated, quiet hours) + operator demo trigger | Jarvis, honestly |
| 7 | Parking memory: prompt → photo + typed level/pillar → "where did I park?" recall | Jarvis, relatable |
| 8 | Merchant onboarding: menu photo → extracted draft → operator approves → appears in search | Platform growth |

Order of sacrifice if time runs out: cut 8, then 4, then 7. Items 1, 2, 3 and 5 are the floor.

### OUT (do not build, not even a stub)

Salik/DEWA/vehicle/Mulkiya/Tasjeel flows of any kind (a static "Pilot" placeholder in the Civic tab is the maximum) · background geofencing or motion · indoor maps · ticket wallet · payments/escrow · government write actions or live wait times · community/social/meetups · media vault · peer messaging · merchant-authored widgets · webhooks · automatic visitor/resident detection (mode is a user setting) · restaurant reservations · flight tracking · native apps.

These remain in `handoff/01–08` as vision. Mentioning them in the pitch as roadmap is fine. Demoing them is not.

## 3. The 4-minute demo (replaces `handoff/08 §5` and `05 §3`)

> **Founder direction, 9 Oct 2026:** lead with **"Hello, visitor" → DXB indoor arrival guide → taxi or Metro**, then **multi-merchant HTML mini-apps** (e.g. several pharmacies, each with its own HTML). The prototype is in `demo/`. The airport guide is signage- and landmark-based with user-confirmed steps; no indoor positioning and no invented belts or queues. Rework the table below to this order once the founder confirms the second act (merchant loop + civic recovery).

The split screen shows the user's phone on the left and the merchant inbox on the right. A `Demo data` pill is visible wherever fixtures appear.

| Time | Beat | Pillar |
|---|---|---|
| 0:00–0:25 | Companion opens. A **Demo trigger** card says "Arriving at Dubai Mall: save your parking spot?" The user snaps a photo and types `P2 C14`. Saved. | Jarvis |
| 0:25–1:15 | "Need 5 shirts ironed by tomorrow in Marina." The agent asks one missing question (pickup time) and returns `service_comparison`, then the user opens the laundry widget, picks a quantity and slot, and taps Request. An approval card shows what's shared: area, item count, contact. User approves. | Services + widget |
| 1:15–2:00 | The merchant inbox (right) lights up. The merchant acknowledges and quotes AED X. The user's chat flips to `QUOTED` live. The user accepts, the merchant confirms, and the status reaches `CONFIRMED` with the merchant's reference. A pickup reminder is offered and accepted. | Real action |
| 2:00–3:00 | "They burned one of the shirts." The agent pulls the confirmed order, the user attaches a photo, and the agent returns a `citation_answer` that quotes the retrieved article with source, date and "not legal advice", then a `complaint_draft` with `Open official channel`. Status stays honest: nothing is "filed". | Civic trust |
| 3:00–3:15 | "Where did I park?" The agent shows the photo with P2 C14. | Jarvis payoff |
| 3:15–3:50 | Operator view: a new tailor's menu photo becomes extracted items, the operator approves, and "I need trousers hemmed" now surfaces the new tailor in the same card. | Platform |
| 3:50–4:00 | Close: "Not a chatbot and not a forms directory: one companion that acts, remembers, and is honest about it." | — |

Fallback: if anything fails live, play a pre-recorded run of the same flow, captured during the Phase 5 rehearsals.

## 4. Phases and gates

Gates are binary and testable. The start date is 9 Oct 2026. The calendar assumes one main builder. **Re-anchor all dates once the official submission deadline is verified (task 0.1).**

### Phase 0: Decide and set up (9 – 19 Oct)

| # | Task |
|---|---|
| 0.1 | Verify on official pages: submission deadline, required artifacts (prototype, video, deck?), category criteria, **IP ownership terms**, eligibility. Record links and dates in `docs/contest-rules.md` |
| 0.2 | `git init` and commit the current docs. Archive the Montage screen to `screens/archive/` |
| 0.3 | Scaffold the monorepo (`apps/web`, `apps/api`, `apps/widgets`, `packages/contracts`), docker-compose for Postgres+pgvector, and fill the CLAUDE.md "Commands" section |
| 0.4 | Contracts v1: the card union for P1–P2, the state machine table, and the codegen pipeline with its CI check |
| 0.5 | Pin the LLM model ID and the embedding model (must handle Arabic and English) and record both in config |
| 0.6 | **Start the external tracks now** (§5): pilot merchant outreach, legal corpus list |
| 0.7 | Write 10 eval fixtures for the hero journey (happy and failure paths) |

**Gate 0:** rules verified with links · repo boots · `make contracts` is green · one pilot merchant is at least in conversation · corpus source list drafted.

### Phase 1: Persistent companion (20 Oct – 9 Nov)

Auth (demo users and roles), conversations/messages, SSE stream, a LangGraph turn using `registry.search` + `memory.get`, the card renderer, the `service_comparison` card from fixtures, tokens/theme and the tab shell.

**Gate 1:** chat → comparison card · hard reload restores every message and card · an invalid card is dropped and replaced by a plain-text note · e2e test in CI.

### Phase 2: Real merchant loop + widget (10 Nov – 30 Nov)

Registry tables and fixtures, the `actions` service with the full state machine and idempotency, approval cards, `/merchant` inbox with SSE, the outbox dispatcher, `action_status` cards, then the `laundry-quote` widget with sandbox, bridge and fallback.

**Gate 2:** a merchant action in the inbox appears in the user's chat in **< 1 s** (p95 over 20 runs, local) · a double-tapped approve produces one request · decline, timeout and cancel paths tested · no status changes without an `action_events` row · the widget can't reach the API (test) · fallback renders when the widget origin is down.

### Phase 3: Civic trust (1 Dec – 14 Dec)

Corpus ingest, hybrid retrieval, the deterministic citation check, evidence upload, `citation_answer`, `complaint_draft`, official handoff.

**Gate 3:** on a 25-question eval set, every answer's quotes exist verbatim in a retrieved chunk (automated) · ≥ 5 out-of-corpus questions correctly abstain · **zero** hard-coded law references in code/prompts (grep check) · the founder hand-checks 10 answers against the source.

### Phase 4: Jarvis + onboarding (15 Dec – 28 Dec)

Reminders and scheduler, quiet hours, the demo-trigger endpoint, parking prompt/recall, menu-photo onboarding into a draft and operator approval.

**Gate 4:** the same trigger fired twice → one message · a reminder fires within 5 s of schedule and survives reload · a quiet-hours suppression is logged · parking recall returns the exact saved photo and text · an onboarded provider appears in search without code changes.

### Phase 5: Harden and submit (29 Dec → deadline)

Run the full ≥ 30 scripted eval cases, rehearse the demo 10 times and record the fallback video, write the deck, deploy to a stable host, run a 10–20 person user test if time allows.

**Gate 5:** 10 consecutive clean rehearsals ≤ 4:00 · the fallback video is recorded · eval numbers are reported as measured numerators ("27/30"), not targets.

## 5. External critical path (not engineering, start in Phase 0)

| Track | Owner | Needed by | If it slips |
|---|---|---|---|
| Contest rules, IP, deadline | Founder | 19 Oct | Everything is mis-scheduled |
| 1 consenting pilot merchant (laundry or tailor) who will tap the inbox on stage or on video | Founder | 30 Nov | A team member operates a clearly labelled `Sandbox merchant`. Never present it as a real business |
| Legal corpus: official consumer-protection law + executive regulation + the official complaint channel page, with URLs and dates | Founder + agent | 1 Dec | Narrow the civic answer to the official complaint-process page only |
| Hosting + domain | Builder | 15 Dec | Run locally with a tunnel |

## 6. Open decisions (default applies unless the founder overrides)

| Decision | Default |
|---|---|
| LLM | Claude via `LLM_MODEL` env; start with `claude-sonnet-5-5` for latency, then compare `claude-opus-5-5` on the eval set before the demo |
| Embeddings | A multilingual model tested on 10 Arabic + 10 English corpus queries in Phase 0 |
| Arabic UI | Answers in Arabic in the MVP; the full RTL UI is a stretch |
| Visitor vs resident | One profile setting; no auto-detection |
| Ratings on cards | Omitted unless merchant-submitted *and* labelled as such |

## 7. Risks

| Risk | Mitigation |
|---|---|
| Scope creep from the 250 KB vision docs | §2 OUT list; CLAUDE.md authority table |
| No real merchant | Sandbox merchant labelled as such; the story still holds |
| Wrong legal citation on stage | Citation check + abstain + founder hand-check (Gate 3) |
| Live demo failure | Recorded fallback; the demo runs on fixtures + 1 merchant, not on third-party APIs |
| Solo-builder timeline | The order of sacrifice in §2 is pre-agreed |

## 8. Sign-off

- [ ] Founder approves §2 IN/OUT
- [ ] Founder approves §3 demo
- [ ] 0.1 rules verified (date + links)
