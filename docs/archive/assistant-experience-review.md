# Independent review of the extended assistant experience plan — 22 Oct 2026

Status: **external critique of a planning proposal. No product decision, implementation claim or scope change is made by this document.** Subject: [assistant-experience-plan.md](assistant-experience-plan.md) (pushed as `a8ab19c` on `redesign`). Subordinate to [PLAN.md](../../PLAN.md); it does not override it. Product rationale: [personal-assistant-direction.md](personal-assistant-direction.md). The review prompt this answers is [assistant-plan-review-prompt.md](assistant-plan-review-prompt.md).

Method: I read the plan against the repo's own canon (`CLAUDE.md` rules 1–10, `PLAN.md`, `docs/implementation-plan.md`, `handoff.md`, the existing action engine, outbox and profile implementation), then checked the three reference products and the news/regulatory data landscape against current official sources on 22 Oct 2026. Findings are labelled **Fact** (verified this session, with a source), **Inference** (my reading of facts; could be wrong) or **Open decision** (needs the founder). Findings are numbered `RV-01…RV-16` and referenced from the recommendation tables so the plan can be amended line by line.

**Bottom line:** the plan is a better planning artifact than most, and a worse product thesis than its author thinks. Its specifications are careful; its *premise* — that DubaiIO should become a personal assistant with a Today view, a swipe-up news briefing, routines and multi-channel access — is a re-implementation of three products that shipped in 2026, while the one thing DubaiIO can uniquely own is mentioned in six lines of a regulation sub-section. The recommendation is not to abandon the plan but to **narrow it to the receipts thesis** and to treat the news briefing as a later, optional, pull-only surface rather than a delivery gate.

---

## 1. Verdict

**A coherent, well-disciplined proposal built on a thesis that a jury will read as a smaller version of OpenAI Dots.**

The plan's craft is genuinely good: it separates task state from memory from source context from approvals; it forbids LLM text from setting status; it requires provenance and as-of on numbers; it refuses invented urgency; it names politics opt-in, source rights, newsletters privacy, cancellation races, stale workers and duplicate events; it says an empty day is valid and a broken feed must not become a fictional feed. Very few product proposals are this disciplined. §3's state inventories, §4's BRF-04's announced/enacted/effective/amended/withdrawn distinction, §5's RUN-01's "commit intent, commit provider outcome deliberately, keep `UNKNOWN_STATUS`" and §8's test list are better than most shipped systems.

The problem is not the craft. It is that **the plan's headline capability set is a commodity**, and the plan never states the non-commodity capability it does own. §1 says "personal assistant for everyday life and work in Dubai". §2 says "targeted redesign". §6 ships a task system, a briefing, connectors, routines and channels. What a jury can actually see on stage in May 2027 is: a chat app, a task list, and a news feed. Dots, Claude Duet and Grok Bot already ship all three, with 6,000+ connectors, cloud browsers, native apps and a hundred times the distribution.

The fix is one sentence of positioning plus a hard filter on every slice:

> **DubaiIO is the assistant for Dubai that shows its receipts: it never signs into your accounts, it never spends your money, and it never says "confirmed" without a provider's own event behind it.**

That sentence is *not* a limitation — it is a guarantee the three reference products cannot make. Dots runs a cloud browser that holds your logged-in sessions. Duet can pay through Link/Stripe. Grok Bot's own guide warns that a site logged into by one bot is reachable by every other bot, and that its safety rules are natural-language instructions the model is trusted to follow. DubaiIO's guarantee is enforced in code, by a registered-capability registry, an approval snapshot, and a provider-evidence gate. **That is the differentiator, and it is already built.** The plan's error is that it treats the differentiator as a constraint to work around rather than as the product to build on, and spends §4 on a feature every phone has.

---

## 2. Evidence base

### 2.1 Verified this session (Fact)

| # | Claim | Source |
|---|---|---|
| E-01 | Dots is a first-class ChatGPT product: "an always-on agent that keeps work moving and asks for your input when a decision needs you"; cloud-hosted with its own computer and browser; "can keep working even when your computer is off"; powered by GPT-6 Astra | `learn.chatgpt.com/codex/dots` (fetched 22 Oct 2026) |
| E-02 | Dots visibility surfaces are **Activity**, **Scheduled**, **Computers**; controls are **Take over / Return control**, **Pause / Resume**, **Stop**, **Delete**, **Allow access / Revoke access / Offline**; "open your dot's profile and select Activity, then open a task to inspect its progress, results, or requests for input" | `learn.chatgpt.com/codex/dots` |
| E-03 | Dots uses a custom-rule model with four modes: "Take action without asking" / "Take action when you say so" / "Ask before taking action" / "Hand off to you"; and "Asking your dot to draft replies doesn't give it permission to send them" | `learn.chatgpt.com/codex/dots/controls` |
| E-04 | Dots memory is three layers — conversation context, ChatGPT memory, and the dot's own saved notes — and notes are **updated, not forgotten**: "your dot can update these notes to reflect new decisions and changing priorities. Changing a ChatGPT saved-memory setting doesn't necessarily change the notes your dot has already made." | `learn.chatgpt.com/codex/dots/tasks-and-memory` |
| E-05 | Dots task scoping: "A new task receives instructions and context from your dot for that work. It has its own conversation; it doesn't automatically receive every conversation you've had with your dot." | `learn.chatgpt.com/codex/dots/tasks-and-memory` |
| E-06 | Dots admits: "stopping a task doesn't undo actions it has already completed"; "A completed run doesn't by itself confirm that the requested result was achieved or delivered"; "Mobile web is not supported"; "Some websites block cloud browsers or require extra verification" | `learn.chatgpt.com/codex/dots` |
| E-07 | Dots usage accounting: "Conversations with your dot don't count toward your ChatGPT usage limits. Tasks your dot starts or manages in Work or Codex count toward those products' usage limits as usual." | `learn.chatgpt.com/codex/dots` |
| E-08 | Dots is US/EU-limited by tier: Pro tiers "outside the European Economic Area, United Kingdom, and Switzerland"; Business Premium and Enterprise "rolling out worldwide" | `learn.chatgpt.com/codex/dots` |
| E-09 | Claude Duet announced 21 Oct 2026, research preview, waitlist, **US Pro and Max only**; standalone iOS/Android app plus claude.ai; powered by Opus 5.5; Team/Enterprise not included | `claude.com/resources/articles/claude-duet` |
| E-10 | Duet's decision UI vocabulary: tabs "Message / Chat / Tasks / Make"; counters "5 things in progress and 2 that need you"; card states "Approve / Not now", "Paid", "Expires in 8 min", "Yes / No / Not now", "Send from you?", "Not now / Send", "Refreshes daily at 5:30 AM" | `claude.com/product/claude-duet` |
| E-11 | Duet background cost: "Claude Duet checks your connected accounts every few hours, because checking nonstop would use up your plan's limits much faster." and "Its background checks count against those limits." | `claude.com/resources/articles/claude-duet` |
| E-12 | Duet admits it "can miss something that arrives between checking in with you", "might misread a thread or miscalibrate what is urgent", that "personal errands, such as booking tickets, aren't quite as strong", and that it "can't yet show you its browser" | `claude.com/resources/articles/claude-duet` |
| E-13 | Duet's approval model: "before it sends a message, makes a payment, signs a document, or deletes anything, it shows you exactly what it's about to do and waits for your approval"; off-limits even with approval: "trading securities or moving money between accounts"; leak control is a classifier + safety prompt rejecting "credit card numbers and government identification" | `claude.com/resources/articles/claude-duet` |
| E-14 | Duet can spend: "using Link, Stripe's digital wallet… Link asks you to approve the spend. It then pays with a virtual card" | `claude.com/resources/articles/claude-duet` |
| E-15 | Grok Bot: bots are "an agent with a computer… The computer lives in the cloud. It has a desktop, a filesystem, a terminal, and apps"; bots ship **disabled until enabled**; runs after the laptop is closed | `x.ai/bot/guides` (x.ai/bot and x.ai/changelog/bot returned HTTP 403) |
| E-16 | Grok Bot's safety model is prompt-based and the vendor says so: "Bots are kept in check by permissions, a reviewer, and allow/block lists. You write the rules in natural language… A separate review agent checks proposed actions and can allow, block, or escalate to you… You are trusting the model to follow what you wrote." | `x.ai/bot/guides` |
| E-17 | Grok Bot shared-session blast radius, per its own guide: "if you log into a site with one bot, every other bot can reach that site too" | `x.ai/bot/guides` |
| E-18 | Grok Bot routines: "A bot can set its own schedule or listen for events from other apps… it can watch a Slack thread or a GitHub PR"; cron-style rules written in prompt text; "review the results on your own schedule, from the Grok Bot Mobile App" | `x.ai/bot/guides` |
| E-19 | NewsAPI.org free Developer plan: 100 requests/day, 24-hour article delay, ~1 month of history, **"may be used for development and testing in a development environment only… cannot be used in a staging or production environment"**; Business $449/mo (250k req/mo), Advanced $1,749/mo | `newsapi.org/pricing` (fetched 22 Oct 2026) |
| E-20 | Currents free tier: 250 requests/day, 20 results/request, 30-day lookback, **300-character preview**, no commercial-use position stated; paid Builder $69/mo — and its own page states that "display or reuse remains subject to the Terms and publisher permissions" | `currentsapi.services/en/free-news-api` |
| E-21 | `u.ae` (Official Portal of the UAE Government) publishes labour, visa, justice and business-regulation pages, each with an "Updated On" date, and offers "Subscribe to updates and alerts on Justice system and the law" | `u.ae` (fetched 22 Oct 2026) |
| E-22 | `uaelegislation.gov.ae` is "the official platform of the legislations of the UAE government. Developed and managed by the General Secretariat of the UAE Cabinet"; filterable by law type, sector and year (1,000+ laws); provides "a list of the amended laws and all the legislative updates in chronological sequence"; site carries "The site was last updated on : …" timestamps | `uaelegislation.gov.ae` (fetched 22 Oct 2026) |
| E-23 | The Government of Dubai Media Office newsroom (`mediaoffice.ae`) publishes decrees and government announcements as news items, e.g. "Mohammed bin Rashid issues Decree on Dubai …" | `mediaoffice.ae` (fetched 22 Oct 2026) |
| E-24 | DubaiIO's existing engine already does the hard things: `apps/api/app/actions.py` rejects unregistered capability IDs, checks required fields, **fingerprints the payload for idempotency**, snapshots the approval (`capability_id, recipient, effect, fixed_total_aed, fields, order`), refuses dispatch without a provider cancellation capability, and drives execution through a registered adapter that returns provider evidence | `apps/api/app/actions.py:193-285` (read 22 Oct 2026) |
| E-25 | DubaiIO's outbox already has consent, per-owner dedupe (`UNIQUE(owner, dedupe_key)`), delivery state and Dubai quiet hours 23:00–07:00 | `apps/api/app/proactive.py:27-59` (read 22 Oct 2026) |
| E-26 | DubaiIO's memory already supports **Forget** across facts, observations, projections *and* LangGraph checkpoints, with a visible learning pause and Resume — i.e. it can delete, which Dots' notes model (E-04) cannot | `docs/implementation-plan.md` REC-02, CTX-01 |
| E-27 | The 22 Oct local Supabase write path stalled (`WALWrite`/object locks, Docker HTTP 500) during isolated test-schema creation; reads worked; no shared restart or volume reset occurred; the older Postgres volume is separate and untouched | `handoff.md` runtime checkpoint; `docs/implementation-plan.md` REC-03A/B gate |
| E-28 | Google OAuth is founder-deferred to last; only `openid email profile` scopes exist today; no Gmail/Calendar scope is held | `docs/implementation-plan.md` §0.4, DB-03 |

### 2.2 Could not verify (must not be assumed)

| # | Open item | Why it matters | Status |
|---|---|---|---|
| U-01 | Whether `u.ae`, `uaelegislation.gov.ae` or `mediaoffice.ae` expose RSS, JSON or a public API | BRF-04 assumes "source adapters"; "detect a new or amended regulation" is only cheap if a change feed exists | Not found. These portals presented as HTML-first with dates and filters; no feed endpoint confirmed. `uaelegislation.gov.ae`'s "Subscribe to updates" and email-alert paths were not exercised. |
| U-02 | Whether a **Dubai-level** legislation portal or gazette feed exists (distinct from federal `uaelegislation.gov.ae`) | BRF-04 explicitly distinguishes federal vs Dubai jurisdiction | Not found this session. `dubai.ae` / `mediaoffice.ae` are newsrooms, not legal instruments. Counsel check required. |
| U-03 | The rule that federal laws reach the Official Gazette within ~2 weeks of signature | Determines the announcement→effective gap and therefore how early a "regulation" alert can be | Recalled, **not verified**. Do not use in BRF-04 until confirmed with the Ministry of Justice / Official Gazette. |
| U-04 | Google News RSS terms, and whether any Dubai/UAE publisher permits republication of summaries | Determines whether a briefing can use Google News as an adapter at all | Not checked. Assume no until a publisher or counsel says otherwise. |
| U-05 | UAE press/content-reuse and local data-protection obligations for storing newsletter text and user reading history | BRF-05/BRF-03 compliance | Not checked by me. This is a counsel task, not an engineering task; do not let an agent close it. |
| U-06 | Whether Dots or Claude Duet are actually **available to users in the UAE** | If Duet ships in the UAE, the "morning brief" comparison becomes much sharper than the plan assumes | Not checked. E-08/E-09 state US/EU/rollout limits; UAE availability unknown. |
| U-07 | Grok Bot plan tiers, geography and usage accounting | Needed for a complete competitive matrix | `x.ai/bot` and `x.ai/changelog/bot` returned **HTTP 403** on every attempt. E-15–E-18 come from `/bot/guides*` and `/bot/use-cases` only. |
| U-08 | Model pricing for DubaiIO's summarisation tier at contest scale | §12's cost model | Not verified; `LUNA_MODEL`/effort are configured in `app/config.py` and the repo forbids hard-coding model IDs. Measure, do not assume. |

---

## 3. Competitive teardown

### 3.1 Capability matrix

Legend: ● shipped, ○ partial, ○/◐ weak or admitted gap, — not shipped, **★** where DubaiIO can beat the reference set.

| Capability | Dots (OpenAI) | Duet (Anthropic) | Grok Bot (xAI) | DubaiIO today (verified) | DubaiIO as planned | DubaiIO position |
|---|---|---|---|---|---|---|
| Always-on background work | ● cloud computer, works with your devices off | ● own VM + browser | ● runs after laptop closed | ○ deterministic outbox only (reminders, demo triggers) | ● RUN-01 worker | **behind** (no host, no budget) |
| Persistent multi-responsibility | ● "more than one responsibility at a time" | ● tasks + in-progress counters | ● bots with titles/descriptions | — | ● DATA-01 Task | behind |
| Progress inspection | ● Activity view | ● Tasks tab, "5 things in progress" | ● remote desktop + chat | — | ● UX-02 | behind |
| Pause / resume / cancel | ● Pause/Resume/Stop, separate for delegated vs scheduled | ○ not stated on official pages | ○ not stated | — | ● UX-02 | behind |
| Cross-channel entrance | ● ChatGPT, voice, Slack, Teams, iOS widget, Shortcuts | ○ typing + voice in one thread; Slack only as connector | ● chat, routines, other bots, group chat, mobile | — web only (native parked) | ○ CHANNEL-01 (later) | far behind, and deferred |
| Cross-channel memory | ● "Changing where you talk to it doesn't start a new dot or reset its memory" | ○ one thread | ○ filesystem persistence | — | ○ | behind |
| Private/shared boundary | ● "your dot checks that you've allowed it" before sharing | ○ classifier + safety prompt (E-13) | ○ prompt rules; shared-login blast radius (E-17) | ● owner scoping in code, per-owner dedupe, `dubaiio` private schema | ○ CHANNEL-01 | ★ **code-enforced, not classifier- or prompt-enforced** |
| Approval before side effect | ● automatic review → proceed / ask / hand off | ● shows exactly what it will do, waits | ● reviewer agent allows/blocks/escalates | ● registered capability + approval snapshot | ● | ★ **registry-enforced, testable** |
| Approval bound to exact content | ○ snapshot-ish, not stated | ○ "exactly what it's about to do" | ○ prompt rules | ● snapshot + revision binding (E-24) | ● | ★ ahead |
| Credential custody | ● cloud browser holds your sessions; save-to-passwords | ● never sees credentials (Managed Agents) | ● 2FA/CAPTCHA handoff, secure forms | ● **none — DubaiIO never logs in** | ● | ★ **no credential custody at all** |
| Payment / purchase | — | ● can pay via Link/Stripe | ○ marketplace "parks the submit" | ● **NEVER: no purchasing/payments** | ● NEVER preserved | ★ **structurally cannot spend your money** |
| Learned routines | ● Scheduled, event triggers, editable | ○ morning brief only | ● "show a bot how it's done" → saves a routine | — | ○ ROUTINE-01 | behind |
| Proactive brief | ● "reaches out with results or decisions that need you" | ● daily 5:30 refresh + morning brief | ○ | ○ outbox messages | ● BRF-01 | behind on *delivery*, ★ on *truthfulness* |
| Explicit "needs you" inbox | ● Activity → "requests for input" | ● "2 that need you" | ○ reviewer escalation | ○ decision cards in chat | ● UX-01 | behind, but vocabulary can be adopted from Duet (E-10) |
| Honest failure / unknown outcome | ○ "A completed run doesn't by itself confirm that the requested result was achieved or delivered" | ○ "can miss something that arrives between checking in with you" | ○ not stated | ● `UNKNOWN_STATUS`, blocked reasons, no fake Send | ● | ★ **the reference set admits this gap; DubaiIO's design closes it** |
| Memory correction / forgetting | ○ notes updated, not deleted (E-04) | ○ not stated | ○ not stated | ● Forget across facts, observations, projections, checkpoints | ● | ★ **deletion is implemented; Dots' is not** |
| Local / regional specificity | — | — | — | ● Google Places discovery, service catalog, fixed prices, official handoffs, lost-item report | ● | ★ **the only axis nobody else occupies** |
| Service execution with provider evidence | ○ (cloud browser + approvals) | ○ | ○ | ● sandbox merchant loop, provider-confirmed status, one approval | ● CORE-02 | ★ |
| Connectors (mail/calendar/Slack) | ● Gmail, Drive, GitHub via plugins | ● 6,000+ Marketplace connectors | ● Gmail, Calendar, Drive, Slack, Notion, GitHub | — | ○ CONNECT-01 (later) | far behind; also the wrong axis |
| Native mobile | ● iOS widget, app | ● standalone iOS/Android | ● iOS + macOS | ○ parked on `ios-swift` | ○ parked | behind, deliberately |
| Cost transparency of background work | ● separate usage accounting (E-07) | ● background checks consume plan limits (E-11) | ○ not stated | ○ none | ○ RUN-01 budgets | ★ if built: show the user a ceiling |

### 3.2 Where the plan is right, and where it is behind

**The reference set has already won the features the plan is proposing to build.** All three ship background work, cross-channel entry, routines and approval gates. All three are work-first and US/EU-centric; all three run cloud browsers. Any plan that proposes to match them feature-for-feature, without a connector catalogue, a cloud compute tier, native apps or distribution, loses.

**But the reference set has admitted, in their own words, exactly the weaknesses DubaiIO's existing architecture was built to prevent.** Duet "might misread a thread or miscalibrate what is urgent" and "can miss something that arrives between checking in with you" (E-12). Dots: "A completed run doesn't by itself confirm that the requested result was achieved or delivered" (E-06). Grok Bot's safety is "natural language… You are trusting the model to follow what you wrote" (E-16), and its guide discloses that a site one bot logged into is reachable by every other bot (E-17). **These are not marketing concessions; they are the architectural consequences of a cloud browser holding your sessions and a model adjudicating its own permissions.**

**Inference:** a jury that understands the category will find DubaiIO's "it never signs into your accounts, it never spends your money, it never claims a result it can't prove" more interesting than a smaller Dots — but only if the product is *built* around that sentence rather than around a generic assistant with a news feed bolted on. Today the plan's §1 promise, §2 redesign and §6 sequence are all generic.

**The one place DubaiIO can be categorically ahead and the plan under-uses it: regulation.** Dots, Duet and Grok Bot are US/EU products with no jurisdiction model, no effective-date semantics and no local issuer. §4 BRF-04 already specifies issuer, jurisdiction, official reference, publication date, effective date, amendment/status and checked-at, and separates announced / enacted / effective / amended / withdrawn. That is a schema, not a feature. It is a real, defensible, Dubai-only capability that a competitor cannot copy without building a legal-ops function.

---

## 4. The five most serious problems, ranked by impact

### RV-01 — The thesis is commodity, and the differentiator is unspoken (impact: existential)

**Fact.** Every headline capability in the plan — persistent responsibilities (E-01, E-02), work continuing while you are away (E-01), cross-channel access with shared memory (E-05, E-08/E-15), learned routines (E-18), a daily brief (E-09/E-10), approval before side effects (E-03, E-13), inspectable progress (E-02, E-10) — ships in at least one reference product today.

**Fact.** The plan's sequence (EXP-00 → CORE-01 → CORE-02 → BRIEF-01 → CONNECT-01 → ROUTINE-01 → CHANNEL-01 → EXPAND-01) is a re-ordering of that same feature set, with the "Today/task" slice first and the local service slice (the only genuinely local asset) third.

**Inference.** Read as a portfolio, the plan's remaining runway is spent rebuilding commodity capability while the two assets nobody else can copy — the provider-evidence local service loop, and the jurisdiction/regulatory model — are scheduled as supporting material. On stage in May 2027 the app is a chat, a task list and a news feed, next to three products that ship all three with a hundred times the reach.

**Consequence.** The pitch has no answer to "why not ChatGPT/Duet?" that is not "it's for Dubai", which is a location, not a capability.

**Remedy.**
1. Rewrite the promise in §1 to the receipts thesis, in one sentence, with three testable clauses: never logs in, never spends, never claims without evidence.
2. Add a **thesis filter** to §6: every slice must be describable in terms of evidence, provenance, approved fields or provider-confirmation. A slice that cannot be is off-thesis, however attractive (this excludes most of BRIEF-01 and CHANNEL-01 as specified).
3. Demote the briefing from a delivery slice to a *surface*, and promote the regulation watch to a first-class slice with its own taxonomy, watch list and gate.
4. Rewrite §8's demo proposal so the merchant-with-evidence loop is the spine and the briefing is one supporting scene — the current §8 proposal ("a relevant briefing item") replaces the strongest provable thing in the repo with the weakest.

### RV-02 — BRIEF-01 has no source, no rights basis and no cost basis; the regulation topic has no change feed (impact: high)

**Fact.** BRF-03 requires "published sources whose retrieval/display rights and access are verified" and the plan names none. The market reality: NewsAPI's free tier is dev-only with 100 req/day and a 24-hour delay (E-19); GDELT is free but global, ~15-minute delayed and has no SLA (reported by a vendor comparison page, **not** verified against GDELT directly); Currents' free tier gives 250 calls/day and 300-character previews, and even its paid tier leaves display/reuse to publisher permissions (E-20). There is no free, production-legal, Dubai-relevant feed.

**Fact.** For the regulation topic, no machine-readable feed could be confirmed for `u.ae`, `uaelegislation.gov.ae` or `mediaoffice.ae` (U-01). `uaelegislation.gov.ae` is a filterable index of laws with amendment and chronological-update listings and "site last updated" timestamps (E-22) — a browsable catalogue, not a change feed. Detecting an *amendment* therefore requires permitted retrieval plus change detection, or an email subscription path (E-21).

**Inference.** "Start with published sources whose rights and access are verified" is not an adapter decision; it is the whole product risk of BRIEF-01, and it is scheduled as if it were a technical detail. The plan's own required state — "A broken feed must not silently become a fictional demo feed" — protects truth but not the *rights* exposure of storing and re-summarising publisher text, nor the *staleness* of a portal that changes without notification. BRF-04's distinction between announcement and effect is also undercut by a publication lag of up to weeks (U-03): a user could be told a rule is "announced" days before it reaches the Gazette and weeks before it bites, which is precisely the audience (labour, tenancy, visa) most harmed by late notice.

**Consequence.** Rights exposure, silent staleness, an unbounded per-source integration cost, and a second product (news) that a competitor can out-distribute tomorrow.

**Remedy.**
1. Move BRIEF-01 off the critical path; it is not a gate on task completion.
2. If it proceeds, the **narrow** version only: ≤3 items, 2 topics, 1 fetch/day, 6h cache, stale-labelled, publisher + publication timestamp + link mandatory, per-publisher rights recorded in a source register before the first fetch. No full-article storage. Summaries generated from permitted excerpts only.
3. Restructure the differentiated feature as **Regulation watch for one narrow domain** (e.g. Dubai tenancy, or UAE labour for a self-employed user), with a user-scoped watch list, a documented retrieval method, and a "last checked" surface. If retrieval can only be manual/diff-based, say so in the UI ("checked 06:00, may have changed").
4. Until a source register exists, label the whole briefing surface as **not implemented** in every artifact. Do not put "BRIEF-01" in a demo plan as if it were a queued engineering task.

### RV-03 — Two products on one screen, with no item budget and no precedence rule (impact: high)

**Fact.** UX-01 specifies four Home sections (Needs you, In progress, Waiting, Recently completed) plus a briefing handle "above the browse dock" plus the browse dock plus the single composer. The plan states "Keep urgent decisions visible before optional reading" and "Distinct from task urgency and approvals" but sets no item cap, no rule for when the briefing handle is visible, and no precedence rule when a briefing item and a task both need a tap.

**Fact.** Duet, whose entire product is a brief, admits its urgency judgement is "still being tuned" and it "might… miscalibrate what is urgent" (E-12). A general-interest news layer is by construction not "what needs you", so it loses every comparison against a real task; it then becomes a second app you open, not a surface you live in.

**Inference.** The plan's own stated discipline — "Unknown evidence cannot manufacture urgency", "An empty day is valid" — is undermined by a Home screen that can always be made to look full. The most crowded-out section will be **Recently completed**, which is what a returning user most wants and the section that best demonstrates the receipts thesis (a completed result *with its evidence*).

**Consequence.** False urgency (repo rules 1 and 3), a permanently busy Home, and a briefing that is opened out of curiosity rather than need — the opposite of a habit loop.

**Remedy.**
1. Three lanes, not four: **Needs you** (≤3, decisions and blockers only), **Running** (compact rows, each showing the next check), and one quiet progress line plus a "Recently completed" disclosure capped at 3. "Waiting" is a *state on a running row*, not a lane.
2. Hard rule: a briefing item may never occupy a Needs-you slot, and the briefing surface never appears in a "you have N things to do" count.
3. The briefing is reachable by explicit tap on a labelled handle; it is not a gesture region (see RV-06).
4. Every Needs-you row must show: what changed, the evidence with source and time, the consequence, and the next action. If any row cannot fill that, it is not Needs-you.

### RV-04 — The platform is 2–3× the pilot, and the concurrency-critical parts are the least specified (impact: high)

**Fact.** DATA-01 introduces seven object types (Task, Task event, Artifact, Decision, Job, Routine/run, Briefing item/source). API-01 adds task create/list/detail/revision-bound edit, pause/resume/cancel, activity, results, Today projection, decision-response, briefing retrieval/feedback/source controls. RUN-01 adds leases, heartbeats, attempt bounds, cancellation generations. Nothing in §6 says which of these the two pilot jobs actually require.

**Fact.** RUN-01's hardest sentence — "Recheck task revision/cancellation and permissions after network waits" — never defines the lease owner, the fencing mechanism, the write rule, or which side wins a cancel-versus-send race. §8's test list names "pause/cancel race" and "stale workers" but there is no interleaving specification to test against.

**Fact.** The repo already contains the primitives: payload fingerprinting for idempotency, an approval snapshot, a registered-capability check, a provider-evidence gate, a cancellation capability requirement before dispatch, an outbox with per-owner dedupe and quiet hours (E-24, E-25).

**Inference.** A parallel job/lease system alongside the existing action engine creates two execution paths, two sources of truth about "did it happen", and a class of bugs that are invisible in a single-tester demo but fatal in front of a jury that interrupts the flow ("cancel that — no, actually do it").

**Consequence.** Either the pilot slips past the January submission, or the concurrency bugs land in the foundations where they are most expensive to remove.

**Remedy.**
1. Pilot data model = **Task + TaskEvent + Decision**, with the existing `Action` serving as the execution/artifact record. Defer Artifact versioning (use TaskEvent payloads), Routine, and Briefing item/source to their own slices.
2. Reuse the action engine as the **only** execution path — no second executor, per API-01's own instruction ("Do not duplicate execution in a new chat route").
3. Make the concurrency rules concrete: a monotonic `revision` on the task; `cancelled_at`; every state write asserts `WHERE revision = :expected AND cancelled_at IS NULL` **in the same statement** as the write; every external call re-reads and re-asserts the revision after the network wait; a cancel that lands after a dispatch is recorded as "cancelled after dispatch — external effect may have happened" and never as "cancelled".
4. Specify the interleavings explicitly (see §10.4) and test each one.

### RV-05 — Background work is scheduled as a feature before cost and host are decided (impact: high)

**Fact.** RUN-01 requires "a running backend/worker and healthy durable writes"; ATTN-01 adds source watchers; ROUTINE-01 adds recurring runs; BRIEF-01 adds a briefing refresh. Duet deliberately polls "every few hours, because checking nonstop would use up your plan's limits much faster" and its background checks consume plan limits (E-11). Dots meters background work separately from chat (E-07). DubaiIO has no metered plan, no revenue, a founder's Windows laptop, and a documented local write stall (E-27).

**Inference.** Every background slice multiplies a recurring, unmetered LLM/provider bill against a product whose commercial model is explicitly undecided (PLAN.md D18) and whose hosting is deferred (DB-03). A pilot with 5 users running 1 task each with 2 daily checks is a rounding error; a pilot with 5 users running 1 briefing each day plus 1 routine plus 2 tasks is ~1,000+ LLM turns/month with no revenue offset and no hosted target.

**Consequence.** The founder quietly pays an unbounded bill, or background work silently does not run — and the plan's honest line ("do not promise always-on operation from an unsigned app build or a browser mock") becomes an accident rather than a design decision.

**Remedy.**
1. The **first** background capability built is the one that proves the thesis (Gate B, §9): a due_at sweep on the existing outbox, one check-back per task per day maximum, with a per-task monthly LLM-call ceiling.
2. The briefing is **pull-only** (fetch on open, cached, 6h TTL). Pull-only cannot leak a notification, cannot double-fire, and costs nothing when unused.
3. Add a user-visible "Cost & limits" surface in **Me** (per-task call ceiling, spend-to-date, caps) — and note that no reference product exposes this to an end user; it is a trust feature.
4. Treat "hosted worker + monthly budget" as a **Gate D dependency**, not a later row.

### RV-06 to RV-16 — additional problems worth fixing

| # | Problem | Evidence / mechanism | Fix |
|---|---|---|---|
| RV-06 | **Gesture conflict.** UX-01 places the briefing handle "above the browse dock" (bottom band) while BRF-01 says "Do not capture the system Home gesture" | On a phone these are the same gesture region; the system Home indicator is at the bottom edge | Tap-only handle; the sheet is a full-screen overlay so natural swipe-up-to-scroll works without a bespoke region. Never bind a custom swipe in the bottom band. |
| RV-07 | **"Newsletters" is silently redefined.** BRF-05: "Working interpretation: 'newsletters' includes a curated published-news briefing" | The founder's phrase most plausibly meant *email newsletters* — a different product with mailbox permissions, private-content handling and a different trust model. A definition swap hides a decision | Disambiguate in the plan: (a) published-news briefing, (b) user-selected publication digests, (c) connected email newsletters. Ship (a) only; keep (c) explicitly deferred with a privacy note. |
| RV-08 | **Relevance reasons bypass the hypothesis model.** BRF-02 says "Explain reasons honestly" with no routing | A chip reading "Because you follow UAE business news" is a stored inference about the user. Repo rule 9: inferences are hypotheses with Confirm/Edit/Not true/Forget, may only re-rank, and never appear on approval cards | Route every reason through the existing hypothesis model. Reason vocabulary limited to: a chosen topic, an explicitly saved area/watch, or a visible hypothesis chip. Behavioural reasons ("you've been reading…") require a hypothesis. |
| RV-09 | **Politics is gated by topic, not by source** | Selecting "Region" or "UAE updates" will surface political coverage by proximity, even though the plan only promises "Politics is an explicit opt-in topic" | Make politics a **source-level** gate applied after topic filtering: an item from a political source is shown only with the Politics opt-in, whatever the topic. Additionally, no engagement with a politics item may feed any interest signal, in any topic. |
| RV-10 | **Duplicate clustering is research-grade in an adapter row** | BRF-03 requires "duplicate clustering" and "A similar headline or copied report is not an independent confirming source" | Pilot dedupe = canonical URL + publisher + normalised-title key. Independent-confirmation detection is a research project; say so rather than implying it exists. |
| RV-11 | **"All tasks: searchable/filterable" in the first slice** | Search and filter over two pilot jobs is premature scale; it is also the classic place where "we built a task manager" leaks in | Move to a later slice. The pilot needs list + detail + state, not a query language. |
| RV-12 | **The demo arc downgrades the strongest proof** | §8 proposes "a task outcome, one evidenced change/decision and a relevant briefing item" — replacing a provable merchant outcome with an unprovable news card | Keep the merchant-with-evidence loop as the spine; make the briefing a supporting scene. Never build a demo moment around an item whose source you cannot cite. |
| RV-13 | **No per-source TTL or staleness budget for the briefing** | BRF-03 lists "stale source" as a required state but no source adapter has a stated maximum age, and no UI convention defines "stale" | Every source adapter declares `max_age`, `checked_at`, and a visible "as of" line. Beyond `max_age`, the item is hidden, not shown dimmed. |
| RV-14 | **Provenance classification is unstated for briefing content** | Repo rule 2: every number carries `provenance` and `as_of`. Briefing cards carry publication time, event date, checked-at, publisher ratings | Define the briefing's provenance vocabulary explicitly: `official` (issuer material), `publisher_reported` (named publisher), `aggregated` (syndicated copy — not independent), `estimate` (event date derived). Brand new categories need a documented rule, not an ad-hoc one. |
| RV-15 | **The user cannot see what the assistant spends or is allowed to do** | No reference product exposes either; no plan surface does | Add **Me → Assistant limits**: per-task call ceilings, daily check-back cap, monthly spend-to-date, connected-source list with revoke, and "what will never happen without your approval". This is a differentiator, not a chore. |
| RV-16 | **No explicit anti-scope statement for the new plan** | `personal-assistant-direction.md` §8 has a deferral list; `assistant-experience-plan.md` has none of its own | Carry the deferral list into the extended plan explicitly, so the scope survives session changes. |

---

## 5. Recommendations

### 5.1 Keep (do not touch)

| Keep | Why it is a strength |
|---|---|
| The existing action engine as the only execution path: registered capability IDs, required-field checks, payload fingerprinting, approval snapshot, provider-evidence gate, cancellation capability required before dispatch (E-24) | It is the product. It is also the answer to Grok Bot's disclosed "trusting the model to follow what you wrote" (E-16) and to Duet's classifier-based leak control (E-13) |
| Task state / memory / source context / approvals kept separate; LLM text never sets status; `UNKNOWN_STATUS` for ambiguous outcomes | Directly answers Dots' admitted gap (E-06) and Duet's polling gap (E-12) |
| Provenance + as-of on every number; fixture/estimate labelling | Repo rule 2; stronger than any reference product's public behaviour |
| The outbox's consent, per-owner dedupe and Dubai quiet hours (E-25) | Already the deterministic proactive substrate; the plan should reuse, not replace |
| Forget semantics across facts, observations, projections *and* checkpoints (E-26) | A real capability Dots cannot match (E-04) |
| "An empty day is valid"; "no endless-scroll, no unread pressure"; "a broken feed must not silently become a fictional demo feed" | Rare, credible, and directly opposite to the engagement mechanics of the apps being learned from |
| One composer, cyan/gradients, no shadows, browse-dock-to-chat transition, explicit 2D/3D | Visual continuity is a felt asset, and the review scope forbids replacing it |
| BRF-04's issuer/jurisdiction/publication-date/effective-date/amendment/checked-at schema and the announced→enacted→effective→amended→withdrawn distinction | The best-specified idea in the plan, and the only one a competitor cannot copy quickly |
| Deferral discipline: no iOS through this plan; OAuth last; no sponsored placement in the decision inbox | Consistent with PLAN.md and correctly repeated |

### 5.2 Change

| Change | Detail |
|---|---|
| **C-1. Rewrite the promise** | §1 becomes the receipts thesis with three testable clauses (never logs in / never spends / never claims without evidence). Every later section references it. |
| **C-2. Re-plan the sequence** | Task core → check-back loop → one service vertical → *then* optional briefing (pull-only) → *then* one connector. See §9. |
| **C-3. Compress the data model** | Task + TaskEvent + Decision; existing Action as the execution record. Defer Artifact versioning, Routine, Briefing item/source to their own slices. |
| **C-4. Today becomes three lanes** | Needs you (≤3), Running (with next check), quiet progress + Recently completed (≤3, disclosure). Waiting becomes a row state. |
| **C-5. Briefing becomes a pull-only surface** | Tap handle → full-screen sheet; ≤3 items; 2 topics; 1 fetch/day; 6h cache; per-source `max_age`; publisher + timestamp + link mandatory; "as of" always visible; never in Needs-you. |
| **C-6. Politics becomes a source gate** | Applied after topic filtering, to every topic, with no signal feedback from political items. |
| **C-7. Relevance reasons route through hypotheses** | Chosen topic / saved area / visible hypothesis only. |
| **C-8. Concurrency rules become explicit** | `revision` + `cancelled_at` + atomic write assertions; interleavings specified and tested (§10.4). |
| **C-9. Add a cost/limits surface** | Me → Assistant limits: ceilings, spend, sources, and the "never without approval" list. |
| **C-10. Add an anti-scope section** | Carry §8 of the direction doc into the extended plan. |
| **C-11. Adopt Duet's vocabulary where it is better** | "Needs you" / "in progress" / "Needs review" / "Approve · Not now" / "Send from you?" / "Refreshes at 06:00" (E-10) — proven comprehension, free to adopt, and it lets a jury map the UI to the reference set in one sentence. |
| **C-12. Demo arc re-centred** | Merchant-with-evidence is the spine; the briefing is one supporting scene; a regulation item with a real issuer link is a better second scene than a generic article. |

### 5.3 Remove

| Remove | Reason |
|---|---|
| The bespoke swipe-up gesture region | Conflict risk (RV-06) and no benefit over a tap handle that opens a scrollable sheet |
| "All tasks: searchable/filterable" from the first slice | Premature scale (RV-11) |
| BRF-03's "duplicate clustering" as a pilot requirement | Research-grade (RV-10) |
| The parallel Job/lease/heartbeat layer in the pilot | Duplicate execution path (RV-04) |
| Any news push/notification variant of the briefing | Push requires a hosted worker and a budget (RV-05); the pull-only version carries the thesis without it |
| "Newsletters" as a single concept | Disambiguate (RV-07) |

### 5.4 Defer

Gmail/Calendar (OAuth is last — E-28; manual-input path is sufficient for both pilot jobs) · Slack and all channel work · routines/marketplace · email newsletter ingestion · cloud browser or any credential custody · sponsored placement beyond the existing frozen ADS-01 · native parity (parked) · household/team collaboration.

---

## 6. Recommended Home and user journey

### 6.1 Home ("Today") layout

```
┌──────────────────────────────────────────┐
│  Wednesday, 22 October · Dubai           │   greeting + user-confirmed context only
│                                          │   (never inferred from map/browsing)
├──────────────────────────────────────────┤
│  NEEDS YOU  (max 3)                      │
│  ┌────────────────────────────────────┐  │
│  │ Shirt pressing — Al Quoz laundry   │  │
│  │ Ready 10:00, your deadline 09:00   │  │  ← what changed
│  │ Shop confirmed · 2 min ago         │  │  ← evidence + source + time
│  │ Reschedule, or pick another        │  │  ← consequence + next action
│  └────────────────────────────────────┘  │
├──────────────────────────────────────────┤
│  RUNNING  (compact rows)                 │
│  ⏱ Chase NOC renewal · next check Thu 09 │
│  ⏱ Weekend options · waiting on you    │
├──────────────────────────────────────────┤
│  Reading ▸ 3 items · updated 06:00       │   tap-only handle → sheet
│                                          │   never counted as "needs you"
├──────────────────────────────────────────┤
│  ▸ Recently completed (3)                 │   disclosure, evidence attached
│  ▾ Done quietly                          │
└──────────────────────────────────────────┘
   [ browse dock ] → collapses to one composer
```

Rules enforced by the layout, not by copy:
- **Needs you** holds only rows that can fill all four fields (change, evidence+time, consequence, next action). If evidence is missing, the row lives in Running as a blocker, not here.
- **Running** rows show the *next check* — a concrete promise with a time. A row without a next check is a bug, not a state.
- **Reading** is visually subordinate and is never counted in any badge.
- **Recently completed** is collapsed by default after the first three items; the whole point is that a returning user can see finished work *with its evidence* in one tap.

### 6.2 Task detail

Three regions, no tabs on a phone: **Brief** (outcome, confirmed constraints, accepted plan + revision, current step, next check) → **Evidence** (results with sources/as-of, provider evidence, unknowns) → **History** (append-only readable events, each with actor and time). The primary action follows state: answer / review decision / open result / retry eligible failed read / pause / resume / cancel. Back restores the parent's scroll and focus; opening a source never loses the task draft. Cancelled and blocked are *states with a reason*, never a silent empty screen.

### 6.3 Chat and the reading-to-action flow

Chat is a conversation, not a command channel: only an explicit "delegate" intent creates a task; ordinary questions do not. When a task is in focus, the composer shows a removable chip naming it, and "make it tomorrow" modifies *that* task when unambiguous, otherwise asks which. From a briefing item, "Ask about this" carries the exact source, publication timestamp and fragment as *reference data* — never as instructions, never as memory writes, never as permission (repo rule 10, BRF-06). The path from reading to work is: item → one tap → an explicit choice among "compare this / save this / remind me / draft a plan" → a *draft* task the user confirms → it appears in Running.

### 6.4 The one-sentence journey to demo

> "I need the shirt pressed by 9." → Today shows it Running with a next check → the shop confirms 10:00 → the assistant surfaces a decision (reschedule or find another) **with the shop's own confirmation as the evidence** → the user taps once → the result appears under Recently completed with the provider's evidence attached, and the app never once claimed anything it could not show.

---

## 7. Two pilot jobs

Both are chosen so that they exercise **every** hard state machine in the plan (persistence, waiting, blocked, cancellation, evidence, notification) **without a single connector, OAuth scope, external partnership or news source**. That is what makes them the smallest *complete* pilot rather than the smallest demo.

### 7.1 Job A — "The thing I already started" (a service, with provider evidence)

| | |
|---|---|
| **Trigger** | User delegates an outcome with a deadline: "get my shirt pressed for tomorrow 09:00" |
| **Inputs** | Manual (text + selected place from existing discovery). No account connection |
| **Work** | Existing catalog → service list with published fixed prices → chosen merchant → one approval listing exactly the shared fields → merchant-side action (sandbox operator until a real merchant exists) → provider event |
| **States exercised** | Working → Waiting externally → Needs you (deadline risk) → Approved → Completed with evidence; plus Blocked (no provider) and Cancelled |
| **What proves the thesis** | The status changes only on the shop's event, not on model text; the approval lists the exact shared fields; a real price and window are shown with provenance |
| **Failure paths that must pass** | merchant never answers; provider times out (→ `UNKNOWN_STATUS`, not a retry storm); price changed between approval and accept; user cancels after the shop accepted (→ "cancelled after dispatch" wording, never "cancelled") |
| **Gate** | See Gate C (§9) |
| **Demo value** | Highest in the repo today; already browser-verified; keep it as the spine |

### 7.2 Job B — "The thing I forgot" (a delayed check-back with a loop)

| | |
|---|---|
| **Trigger** | User delegates a commitment with a deadline: "chase the office about the NOC by Thursday" |
| **Inputs** | Manual forwarded text or typed note. The user can also paste a link; the link is *reference data*, not instruction |
| **Work** | Task created with outcome, deadline and next check → the assistant checks back on a schedule → the check either produces a decision (change of plan, new evidence) or is a no-op → exactly one notification on a real change, none otherwise |
| **States exercised** | Working → Waiting (on user) → Needs you → Completed; plus Paused, Cancelled-before-check, and Blocked (source unreachable) |
| **What proves the thesis** | Continuity: the task survives app close, restart and a week; the notification is deduplicated; a cancel before the check-time prevents any action; a late worker cannot revive it |
| **Failure paths that must pass** | duplicate scheduled sweep fires twice; user reschedules mid-flight ("make it Friday"); source unavailable; task cancelled while a check is in flight; quiet hours (23:00–07:00 Dubai) deferral |
| **Gate** | See Gate B (§9) |
| **Why this job and not a news job** | It is the recurring weekly loop. It is the whole thesis in one sentence. And it needs no rights clearance, no feed, no budget |

### 7.3 Explicitly *not* a pilot job: the briefing

It is a surface, not a job. It may only be built after Gates B and C pass, and only in the pull-only form (§5.2 C-5). If the founder wants one differentiated feature built early instead of a generic one, build **Regulation watch for one domain** — one user-scoped watch list, one authoritative source, one documented retrieval method, visible "checked at" — and let the general news feed wait for a source register.

---

## 8. Revised delivery sequence

Gates are sequential. A gate that fails blocks the next one; it does not trigger a "design it in parallel" exception, because that exception is how BRIEF-01 currently risks masking unfinished task work.

| Gate | Deliverable | Depends on | Measurable acceptance (all must pass) | Explicitly not started |
|---|---|---|---|---|
| **A. Today + Task (read-only)** | Today three lanes; task create / list / detail; revision-bound edit; pause / resume / cancel; Today projection | DB write health (E-27 gate); existing owner model; DATA-01 subset (Task, TaskEvent) | 5 seeded tasks → 5 correct states incl. Waiting/Blocked/Paused; cross-owner read denied; **zero LLM calls on the read path** (p95 < 150 ms); restart preserves state and revision; stale read never resurrects a cancelled task | briefing, connectors, routines, native |
| **B. The check-back loop** | `due_at`/`next_check` sweep on the existing scheduler + outbox; one notification per real change; per-task call ceiling; Me → limits | Gate A; existing outbox consent/dedupe/quiet hours (E-25) | 7-day run with ≥3 genuine check-backs; **0 duplicate notifications** under a double sweep; "make it Friday" reschedules the same task (no duplicate task created); **100% of cancels before check-time produce no action**; a late worker cannot write after cancel; quiet-hours deferral honoured; 0 writes past the call ceiling | push notifications, non-task watchers |
| **C. One service vertical** | Pilot job A end to end with provider evidence | Gate A + B; existing action engine; merchant/provider access (real or clearly labelled sandbox) | fixed published price + window; provider event is the only status source; **0 invented confirmations**; deadline risk surfaced *before* the window is missed; approval snapshot honoured when the revision changes; ambiguous send stays `UNKNOWN_STATUS`; cancel-after-dispatch wording is honest | second vertical, payments, bidding (NEVER) |
| **D. Briefing (pull-only)** — *optional* | ≤3 items, 2 topics, 1 fetch/day, 6h cache, per-source `max_age`, source register, "as of" line | Gate C; **a named, rights-cleared source set**; hosted worker + budget **only if** a push variant is wanted | 14-day run; **≥50% of items opened or acted on**; 0 items marked irrelevant twice; per-user-week cost measured and within the stated ceiling; no political item without the Politics opt-in; every item shows publisher + publication timestamp + link; stale items hidden, not dimmed; a broken feed shows an honest empty/error state | push, newsletters, clustering, sponsored items |
| **E. One connector** | Exactly one of Gmail or Calendar, with the manual path proven first | Gate B or C showing retention with one user; **deliberate, explicit OAuth reorder** (E-28) | 1 week manual → 1 week connected; **0 channel leakage** (private context never crosses to a shared surface); revoked access → honest degradation, no silent stale reads; duplicate events deduped; unknown-send stays unresolved | Slack, all other channels |
| **F. Routine** | One user-reviewed recurring preparation, with expiry and cancel | Gate B; scheduler; budgets; consent | useful across ≥3 cycles; **0 post-cancel actions**; no silent activation (explicit user decision every time); expiry enforced; per-run cost within ceiling | marketplace, passive routine detection |

**Cost-of-delay note.** A and B are the two gates that make the product a *product*. Everything else is optional surface. If the January submission arrives with only A and B shipped, DubaiIO can still be defended: a persistent, evidence-bound, cancel-safe delegation loop in a market where the three reference products admit they cannot tell you whether a task actually succeeded (E-06).

---

## 9. Technical specification deltas

### 9.1 Minimal pilot data model

Reuse the repo's `dubaiio` private schema and existing owner conventions. Proposed logical tables (names provisional; migrations are an implementation deliverable, not a claim):

| Table | Key fields | Notes |
|---|---|---|
| `task` | `id`, `owner`, `idempotency_key`, `outcome`, `constraints` (json, each with provenance), `status`, `revision` (int, monotonic), `cancelled_at`, `due_at`, `next_check_at`, `check_count`, `created_at`, `updated_at` | `UNIQUE(owner, idempotency_key)`; `revision` increments on every accepted change |
| `task_event` | `id`, `task_id`, `owner`, `seq`, `kind`, `actor`, `payload` (bounded), `at` | append-only; readable history; no secrets, no full provider payloads |
| `task_decision` | `id`, `task_id`, `owner`, `base_revision`, `kind`, `action_ref`, `summary`, `expires_at`, `resolution` | external effects still execute through the existing action engine; this table records *the user's answer* and *what it was bound to* |
| (existing) `action` / approvals / outbox | unchanged | the execution record, evidence store and notification substrate |

Explicitly **not** in the pilot: `artifact` (use `task_event` payloads), `job` (use `next_check_at` + the existing outbox), `routine`, `briefing_item`, `briefing_source`.

### 9.2 Task state machine

States (and only these): `DRAFT → WORKING → {WAITING_USER, WAITING_EXTERNAL, BLOCKED} → COMPLETED`, with `PAUSED` and `CANCELLED` reachable from any non-terminal state.

| From | Event | To | Guard |
|---|---|---|---|
| DRAFT | accept | WORKING | outcome non-empty; owner matches; idempotency key unused |
| WORKING | need user input | WAITING_USER | question material to the next step |
| WORKING | external wait | WAITING_EXTERNAL | an external dependency is open; no local work remains |
| WORKING | source failure | BLOCKED | failure is terminal for this attempt; a reason is stored |
| WAITING_* | user answers | WORKING | `revision` matches; answer is applied atomically |
| WAITING_* | external event | WORKING / COMPLETED | the event is provider evidence, not model text |
| any | pause | PAUSED | no in-flight write may land after the pause revision |
| any | cancel | CANCELLED | `cancelled_at` set; in-flight writes are rejected by the write guard |
| any | completion | COMPLETED | the *outcome* is satisfied with evidence, per the outcome type |

`COMPLETED` is per-outcome, never per-model-sentence: a draft completes with a draft; a send completes with provider evidence; a reservation completes with the provider's evidence (repo rule 1).

### 9.3 Revision, fencing and the write guard

```
-- every state-changing write:
UPDATE task
   SET status = :new, revision = revision + 1, updated_at = now()
 WHERE id = :task AND owner = :owner
   AND revision = :expected_revision
   AND cancelled_at IS NULL;
-- zero rows updated  =>  the write is rejected (stale worker, cancelled task, or concurrent change)
```

Rules that follow from the guard, stated once so they can be tested:
1. **No transaction spans a provider or LLM call.** Commit intent, call, then commit outcome.
2. **After any network wait, re-read and re-assert the revision** before writing. A late worker that fails the guard is recorded as a `stale_worker` event, not silently dropped.
3. **A cancel that arrives after dispatch is never rendered as "cancelled".** It is "cancelled after dispatch — the external effect may have happened", and the provider's event, if any, still lands.
4. **Approvals bind to `base_revision` + exact action snapshot.** A changed recipient, price, field set or date invalidates the old approval (the action engine already refuses to dispatch a changed snapshot — E-24).
5. **Every notification is an outbox row with a `dedupe_key`** derived from `(task_id, event_seq, kind)`. Two sweeps firing the same check produce one message (E-25).

### 9.4 Race, duplicate and staleness matrix (the interleavings §8 asks for)

| # | Interleaving | Wrong behaviour to avoid | Required behaviour | Test |
|---|---|---|---|---|
| 1 | Cancel lands while a provider call is in flight | The provider's response overwrites the cancelled state and the task shows "Working" | Write guard rejects (rows = 0) → `stale_worker` event → task stays CANCELLED, with a visible "the request may still have reached the provider" note | concurrent cancel + dispatch, assert final state CANCELLED and one event |
| 2 | Two scheduler sweeps fire the same check | Two notifications, two provider calls, two state writes | `dedupe_key` on the outbox + `next_check_at` advanced in the same transaction as the work claim | force double sweep; assert one notification, one call |
| 3 | User edits a constraint mid-check | The check completes against the old constraint and publishes a stale result | Guard on `revision`; stale result discarded and re-derived; user sees "updated" not "done" | edit during an in-flight check |
| 4 | App/worker restarts mid-check | The task is silently lost, or a step repeats | `next_check_at` persisted before the work; on restart the check resumes or re-runs idempotently | kill the worker mid-check; restart; assert one effect |
| 5 | Quiet hours | A notification fires at 03:00 | Delivery deferred to 07:00; the *check* still runs | set clock into quiet hours |
| 6 | Provider returns an ambiguous outcome (timeout after send) | Retry storms; a second duplicate order | `UNKNOWN_STATUS` retained and reconciled by reading the provider, never by blind retry | simulated timeout after dispatch |
| 7 | A stale worker writes after a revision bump | Old plan restored; a stale result published as current | Guard rejects; `stale_worker` event; Today projection recomputed from current state | bump revision, then let the old worker write |
| 8 | Two owners reference the same merchant action | Cross-owner visibility of fields or evidence | Owner-scoped rows at every read and write | cross-owner fetch denied |
| 9 | A briefing item is read after the source changed | A summary presented as current | `checked_at` + `max_age` visible; beyond `max_age` the item is hidden | age the cache past `max_age` |
| 10 | User edits memory while a task runs | The task silently inherits a new fact | Task context is captured per revision; memory changes apply to the next check, and the task shows what changed | confirm/forget a fact mid-task |

### 9.5 Stale-context rules

- **Task context is captured, not inherited.** Each task records the constraint set it was given; a later memory correction applies to the *next* step, and the task shows a "constraints updated" line.
- **Focus expiry already exists** (30 minutes, ephemeral runtime context). Keep it, and extend the same rule to briefing-item focus: a source reference older than the session's `max_age` is dead, and asking about it must say so rather than re-fetching silently.
- **No checkpoint is the durable record.** LangGraph checkpoints support conversation state only; task progress lives in `task`/`task_event` (the plan says this; make it a migration-level invariant, not a convention).
- **Late responses cannot restore old reasons.** The existing cache invalidation behaviour (profile corrections and visit rotation invalidate in-flight results) must be extended to task state: a correction that lands while a Today projection is in flight must invalidate that projection, not race it.

---

## 10. The briefing, in its narrowest defensible form

### 10.1 Source admission criteria (a source register, not a wish list)

Each candidate source needs a row in a register before the first fetch: publisher; retrieval method (feed / permitted API / permitted manual extraction); what may be stored (headline, publisher, publication timestamp, canonical URL, permitted excerpt only); what may be displayed (headline + attributed summary + link); attribution format; rate/TTL limits; last checked; failure behaviour; rights basis and the date it was recorded. **A source with no completed row is not eligible.** This is what BRF-03 asks for; it is a document, not code, and it should be written before any adapter exists.

### 10.2 Cost reality (verified)

| Option | Verified terms | Fit |
|---|---|---|
| NewsAPI.org | 100 req/day, 24 h delay, dev-use only; $449/mo for production (E-19) | Too slow, too delayed, and dev-only for the pilot's legal footing |
| GDELT | free, unlimited, ~15-min delay, no SLA (vendor-reported; not verified directly) | Free and fast enough, but global coverage, no Dubai-specific guarantee, and licence/reuse terms need checking (U-04) |
| Currents | 250/day, 300-char previews; $69/mo Builder; display/reuse remains subject to publisher permissions (E-20) | Cheapest commercial option; preview length and publisher permission still govern |
| Guardian Open Platform | free with attribution, single publisher | Not a Dubai briefing |
| Publisher's own feed/RSS | **per-publisher, no verified feed found for the UAE regulatory portals (U-01)** | Needs U-01/U-02 answered; a media-office or official-portal permission conversation is a founder task, not an agent task |
| Regulation watch via `uaelegislation.gov.ae` | Official, filterable, amendment lists, chronological updates, "site last updated" timestamps (E-22) | **The best-aligned source for the differentiated feature** — but change detection must be built, not fetched |

### 10.3 Narrow briefing rules

1. Pull-only. Fetch on open; 6h cache; ≤1 fetch/day; ≤3 items; 2 topics maximum at launch.
2. Every card shows publisher, publication timestamp, topic, an attributed summary, the reason it is here, and the canonical link. No card without all six.
3. `checked_at` and per-source `max_age` are visible. Past `max_age`, the item is hidden, not dimmed.
4. Politics is a source gate applied after topic filtering, and political items feed no interest signal in any topic.
5. Relevance reasons are: a chosen topic, an explicitly saved area/watch, or a visible hypothesis chip — never a bare behavioural claim.
6. A saved or dismissed article is not evidence of agreement with it, and is not written to confirmed memory.
7. Source failures produce an honest empty/error state with the failing source named — never a synthetic feed, never a fixture presented as live.
8. Item text is reference data. It can never call a tool, write memory, or grant permission.
9. No sponsored item appears in Today, in a regulation card, or in a decision inbox.

### 10.4 Cost model to actually measure

Per user-week, the pilot briefing costs: `1 fetch/day × 7 × (fetch cost + N_items × summarisation cost)`. With 3 items, that is 21 summarisations per user-week. The decisive unknown is the per-summarisation model cost, which must be *measured* from the configured model rather than assumed (U-08). Required outputs before Gate D: a measured p50/p95 summarisation cost, a measured per-user-week total, and a hard monthly ceiling per pilot user shown in Me → Assistant limits. If the measured cost per useful item is not clearly below the value of one kept task, the briefing is not worth building — and that should be a number, not a feeling.

---

## 11. Operating-cost and hosting reality

**Fact.** Background work is metered everywhere it exists: Duet's background checks consume plan limits (E-11); Dots meters delegated work separately from chat (E-07); Grok Bot ships with its own usage, "so anything you hand off to a Bot won't count against your existing usage" (x.ai announcement, 11 Aug 2026).

**Inference.** DubaiIO's position is structurally different and worse: it has no metered plan to charge, no revenue (D18 is explicitly undecided), no hosted target (DB-03 deferred), and a local write path that stalled on 22 Oct (E-27). "Background work survives interruptions" (the plan's §8) is therefore a *hosting* requirement, not a code requirement.

**Recommendation.** Treat hosting as a deliverable of Gate B, not a later row: a small always-on worker (a hosted container or a cheap always-on VM) with durable Postgres, deployed alongside the API, plus a monthly budget line. Until that exists, the honest product promise is "the assistant works while its worker is running; here is its current status" — and the app should *show* worker health, because a task system that silently stops is the failure mode users describe when they abandon such products.

**Also required (RV-15):** a user-visible limits surface. No reference product exposes this. It is cheap (the counters already exist in the outbox and task rows) and it converts a hidden cost into a visible guarantee.

---

## 12. Risk register

| # | Risk | Sev | Likelihood | Trigger to watch | Mitigation | Owner |
|---|---|---|---|---|---|---|
| RK-1 | Task says "done" without provider evidence | Critical | Medium if guards regress | Any state change to COMPLETED lacking an evidence ref | Completion only via evidence or outcome-type rule; regression test | engineering |
| RK-2 | Duplicate external effect (double order, double send) | Critical | Low | Duplicate action rows or double outbox keys | Idempotency fingerprint + dedupe key + single execution path | engineering |
| RK-3 | Cancel/send race produces a wrong state | High | Medium | `stale_worker` events without a user-visible resolution | Write guard + explicit "cancelled after dispatch" state | engineering |
| RK-4 | Briefing rights exposure (republished publisher text) | High | Medium | Any summary containing more than the permitted excerpt | Source register before first fetch; store excerpt-only; link out | founder + counsel |
| RK-5 | Regulation alert states an effect that has not arrived | High | Medium | A card saying "effective" without an official effective date | Unknown stays unknown; announced ≠ effective; issuer link mandatory | engineering |
| RK-6 | Political content surfaces without the opt-in | High | Medium | Any political-source item in a non-politics topic | Source-level gate + no-signal-feedback rule + test | engineering |
| RK-7 | Unbounded LLM spend from background work | High | High | Spend-to-date exceeding the per-task ceiling | Per-task ceiling + daily check cap + visible limits + budget alarm | founder |
| RK-8 | Local DB write stall recurs; tasks are lost or duplicated | High | Medium | Write errors during check-back | Durable Postgres for anything durable; local-only is non-production; fail loudly, never silently | engineering |
| RK-9 | Channel leakage (private content to a shared surface) | Critical | Low before channels exist | Any cross-owner read | Owner scope at every read/write; no shared `tester` identity; test per surface | engineering |
| RK-10 | Inference leakage (behaviour becomes a stored belief) | High | Medium | A reason string with no hypothesis/choice behind it | Reason vocabulary + hypothesis routing (RV-08) | engineering |
| RK-11 | Product reads as a smaller Dots | Critical | High if the briefing ships as the headline | A demo that opens on the news sheet | Reframe to the receipts thesis; briefing never the spine; demo centred on evidence | founder |
| RK-12 | Scope drift back into visitor framing | Medium | Medium | Copy mentioning arrival/hotel as the default | Onboarding copy stays everyday-first; airport replay is contextual | founder |
| RK-13 | "AI" features replace engine features (model proposes, engine decides) | Critical | Low | A capability that triggers without a registry entry | Registered capabilities only; model fills data, never payloads (repo rule 7) | engineering |
| RK-14 | Notification fatigue from repeated unchanged updates | Medium | Medium | Dismissed items returning | Suppress unchanged updates; per-item dismissal TTL; quiet hours | engineering |

---

## 13. Test matrix additions

Beyond the plan's §8 list, add:

**Task core**
- Revision conflict on concurrent edit; stale-revision edit rejected with a user-visible reason.
- Pause in flight; cancel in flight; resume after cancel refused; cancel-after-dispatch wording.
- Restart mid-check → one effect, no duplicate notification.
- Owner isolation: every list, detail, event, decision and artifact read/write denied cross-owner.
- Idempotent create: the same idempotency key returns the same task, not a second one.
- Context isolation: two concurrent tasks do not inherit each other's constraints, dates or recipients.

**Briefing (if built)**
- Politics opt-in absent → zero political-source items in every topic.
- Political item engagement → no interest signal recorded anywhere.
- Stale item past `max_age` → hidden.
- Source failure → honest error naming the source; no synthetic item.
- Correction/forget → briefing cache invalidated; a subsequent fetch cannot restore the old reason.
- Malicious source text → cannot call a tool, write memory, or set a task instruction.
- Item without publisher/timestamp/link → not renderable.

**Cost and limits**
- Per-task call ceiling enforced; breach surfaces as a visible, honest stop.
- Quiet hours deferral and daylight delivery.

**Regulatory (if built)**
- Announced vs published vs effective rendering; superseded text; missing effective date shown as unknown; conflicting media report marked unconfirmed; jurisdiction (federal vs Dubai) never inferred from a URL.

---

## 14. Decisions I recommend you take (one-word answers)

| # | Decision | Recommended default | Consequence if you choose otherwise |
|---|---|---|---|
| 1 | Product promise | **Receipts thesis** (§1) | The pitch stays "a smaller Dots" |
| 2 | Briefing scope | **Pull-only surface, deferred off the critical path**; regulation watch is the differentiated slice | Rights exposure, cost, and a commodity feature on the demo's critical path |
| 3 | Pilot jobs | **Job A (service with evidence) + Job B (check-back loop)** | A pilot that cannot prove continuity or truth |
| 4 | Data model | **Task + TaskEvent + Decision**, existing Action as the execution record | Two execution paths; platform-scale work before a pilot |
| 5 | Demo spine | **Merchant-with-evidence loop**; briefing as a supporting scene | A demo built on an item you cannot cite |
| 6 | Politics | **Source-level gate, no signal feedback** | Rule 9 exposure |
| 7 | Hosting | **Hosted worker is a Gate B dependency, with a budget line** | Background work that "works" only on a laptop that is on |
| 8 | User-visible limits | **Ship Me → Assistant limits in Gate B** | Hidden cost; no differentiator |
| 9 | Connectors | **Stay deferred**; manual path first; OAuth last | Rule 10 and the single-tester constraint hold; a slower but honest ramp |
| 10 | News "newsletters" | **Disambiguate into three concepts**; ship only the published-news digest | A hidden product decision buried in a definition |

---

## 15. Five questions whose answers would materially change the plan

1. **Who is the first pilot user, and what is their recurring weekly pain?** This has been open since 22 Oct and the plan has been designed around anyway. The answer changes the task taxonomy, the two jobs, the demo arc, the value of the briefing, and whether regulation tracking is the centre or a footnote. *(My recommendation: a self-employed professional or a small-team operator resident in Dubai, because they have recurring deadlines, a real weekly calendar, and a legitimate reason to want a briefing and a regulation watch.)*
2. **What exactly is "newsletter" in the founder's request — a published-news digest, a user-chosen publication list, or connected email newsletters?** These are three products with three different trust and privacy models, and BRF-05 currently collapses them. *(Recommendation: the digest only.)*
3. **Is the briefing allowed to be free at a $0 margin, and is there budget for the worker and the model?** If the answer is no, the briefing is a mockup and should be labelled as one in the plan, not scheduled as BRIEF-01. *(Recommendation: yes for ≤3 pilot users at pull-only, with a measured ceiling and a visible cap.)*
4. **Is regulation tracking the lead differentiator or an optional topic?** If it is the lead, it needs its own taxonomy, watch list, retrieval method and gate — not a bullet inside BRF-04. *(Recommendation: lead.)*
5. **What is the demo's spine — the merchant-with-evidence loop, or a daily briefing?** If the briefing, the product is competing on a commodity against Apple News, Duet and Dots with no connector, no push and a rights-constrained feed. *(Recommendation: merchant-with-evidence.)*

---

## 16. What I would not do

- Do not build a general news feed to look like Dots/Duet. It is the one feature all three of them, every news app, and every messenger already have.
- Do not add a cloud browser, credential custody, or 1Password-style login handling. It is the largest new attack surface, it is the source of Grok Bot's disclosed shared-session blast radius (E-17), and it is the reason Duet and Dots need credential-isolation machinery at all.
- Do not add payments, purchasing, subscriptions, or a marketplace. It is a NEVER here, and a competitor feature in two of the three reference products. Keep the guarantee "DubaiIO can never spend your money."
- Do not build a general task manager: no subtasks, no dependencies, no kanban, no collaboration, no custom fields.
- Do not add multi-agent or multiple visible bots. Duet, Dots and Grok Bot all have them; none of them is what makes a single assistant trustworthy.
- Do not add a dashboard of metrics, a "productivity score", a streak, or a gamified reward loop.
- Do not add proactive push for anything the user did not explicitly ask to watch, and do not add a daily "good morning" nudge unless a routine was explicitly created.
- Do not let an inference touch an approval card, a notification, a deadline, or a status (repo rule 9).
- Do not add a sponsored slot to Today, a regulation card, or a decision inbox.

---

## 17. Steelman: where the plan is right and I would argue against my own review

A fair review has to state the other side.

1. **The plan's restraint is its main quality.** "A briefing is allowed to be short or empty; no endless-scroll requirement or unread-pressure mechanics" and "a broken feed must not silently become a fictional demo feed" are sentences a competitor's product team would not write. Most AI product plans optimise for engagement; this one refuses to.
2. **The state inventories are correct and unusually complete.** UX-01/02/03's required states cover the failure modes that actually ship broken: stale revision, permission revoked, unknown send outcome, superseded result, source unavailable, deferred item, failed read. Whoever wrote §3 has run software.
3. **BRF-04 is genuinely good and ahead of the market.** Issuer + jurisdiction + reference + publication date + effective date + amendment status + checked-at, and the announced/enacted/effective/amended/withdrawn separation, is a legal-ops schema. The plan under-rates it.
4. **"Approval before side effects, bound to a revision" is the right core.** A changed recipient invalidating an old approval (UX-03) is precisely the failure mode that makes approval UIs theatre. The plan gets it right where most proposals do not.
5. **Deferral is a design decision here, not timidity.** "Do not add several bottom tabs or consolidate Maps/Services into Explore without a demonstrated navigation need" and "No new top-level destination until use warrants it" protect a visual identity the founder has already earned, and they resist the tab-bar inflation every new surface invites.
6. **The politics/regulatory/privacy reasoning is more careful than the review prompt's own framing.** "A topic subscription is not evidence of agreement with the article"; "Private newsletter text stays private and cannot be shared to Slack… simply because it appeared in the briefing"; "A source article, email or webpage is reference data, never instructions granting permissions" — these are the right lines, drawn early, in a design document rather than after an incident.
7. **The plan's §7 backlog mapping is honest about what does not exist.** "Do not pretend arts/politics/regulation topics already exist in code" is the sentence most proposals omit.
8. **It is right that news aggregation must not hide unfinished task work.** The plan says it; my only complaint is that its own sequence then puts BRIEF-01 adjacent to CORE-01 rather than clearly after it.

**Where I would hold my ground despite the steelman:** the thesis problem (RV-01) is not a detail. A plan that is excellent at specifying features it does not need to differentiate is still a plan for losing, and this one is heading toward a news briefing on the critical path with two jobs undefined and a demo arc that drops the strongest proof in the repo. The fix is not more specification. It is a smaller product, a sharper sentence, and a source register or nothing.

---

## 18. Verification log

| Check | Method | Date | Result |
|---|---|---|---|
| `learn.chatgpt.com/docs/dots` (+6 sub-pages) | webfetch, `.md` variants | 22 Oct 2026 | Retrieved; quotes in E-01–E-08 |
| `x.ai/news/introducing-grok-bot` | webfetch | 22 Oct 2026 | Retrieved (announcement, 11 Aug 2026) |
| `x.ai/bot`, `x.ai/changelog/bot` | webfetch | 22 Oct 2026 | **HTTP 403** on every attempt; tier/geo/limits **not verified** (U-07) |
| `x.ai/bot/guides*`, `/bot/use-cases` | webfetch | 22 Oct 2026 | Retrieved; quotes in E-15–E-18 |
| `claude.com/resources/articles/claude-duet` | webfetch | 22 Oct 2026 | Retrieved; quotes in E-09–E-14 |
| `claude.com/product/claude-duet` | webfetch | 22 Oct 2026 | Retrieved; quote in E-10 |
| `newsapi.org/pricing` | websearch result (official page content) | 22 Oct 2026 | E-19 |
| `currentsapi.services/en/free-news-api` | websearch result (vendor page) | 22 Oct 2026 | E-20 (self-reported for its own tier) |
| GDELT terms | vendor comparison page only | 22 Oct 2026 | **Not verified directly** (treated as U-item) |
| `u.ae`, `uaelegislation.gov.ae`, `mediaoffice.ae` | websearch result (official site content) | 22 Oct 2026 | E-21–E-23; **no feed/API confirmed** (U-01) |
| Repo grounding | read `PLAN.md`, `docs/implementation-plan.md`, `handoff.md`, `docs/request-backlog.md`, `docs/references/personal-assistant-direction.md`, `apps/api/app/actions.py`, `apps/api/app/proactive.py`; `git log`/`git status` | 22 Oct 2026 | E-24–E-28; working tree clean at `a8ab19c` on `redesign` before this document |

---

*Prepared as an independent critique on 22 Oct 2026. Facts are sourced; inferences are labelled; open decisions are listed in §14 and §15. This document changes no scope, authorises no implementation, and does not override PLAN.md.*
