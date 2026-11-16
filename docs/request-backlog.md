# Request backlog — 9 Nov 2026

Founder requests and their execution order. Scope: `PLAN.md`. State: [status.md](status.md). Requirements, implementation and verification are separate states; a partial result is not completion. Closed and superseded items (the 21–23 Oct ledger, checkpoints, reordering record) are in git history: `git show main:docs/request-backlog.md`.

## Working rule

Finish the active task before taking the next. New messages refine the active task or enter this backlog; questions get an answer without replacing the task. Reorder only when the founder explicitly changes priorities or the agent explains a logical reordering in the same session and updates this ledger. Preserve unresolved requests across handoffs.

**Gate (23 Oct):** no UI track is done without founder visual review of a staged preview — build-green is not design-accepted.

## Lock removal record (23 Oct, founder)

Unlocked: government transactions, bill top-ups/payments, in-app donations, third-party purchasing — each only through a real registered adapter with per-action approval and verified provider evidence (rule 4). Without an adapter: show the blocker + "Open official portal" and keep the draft. Still locked: copying the DubaiNow look (NEVER), fake statuses, invented facts, bidding/negotiation.

## ACTIVE — LAB-01 headless Know / Notice / Do pipeline (9 Nov)

Founder, 9 Nov: pause UI work; build the pipeline headless in `apps/api/app/lab/`. Numbered steps, specs and acceptance: `apps/api/app/lab/CLAUDE.md`. Each slice ships with fixtures plus a happy-path and a failure-path test. Build order (from docs/Researches/CLAUDE.md, 9 Nov):

- **Import:** Gmail + Calendar connectors (founder as Google test user); parser for manually exported WhatsApp chats (iOS, Android and copy-paste formats; multi-line, media-omitted and system lines; Arabic/Arabizi; text only). Every event stores its source.
- **Consolidate:** into `mem_*`, shown as the life themes (Career · Learning · Projects · People & family · Events · Home & money · Travel); source + date per entry; an evidence-limits line per source. Builds on the existing tables; does not wait for the engine pick (MEM-01).
- **Reveal:** "What I noticed", strengths, signature moves — hypotheses with evidence and Confirm / Edit / Not true / Forget; nothing sensitive inferred.
- **People map** from `mem_relationships`.
- **Today:** confirmed interests + recent memory → candidates → `recommendations.py` ranker → morning outbox slot → card with "Because…" and Save / Less like this.
- **One task thread** run to an honest terminal state.

Blocked on: the founder's Google OAuth keys (`status.md`).

## Open items (updated for the 9 Nov decisions)

Grouped Know → Notice → Do → platform. Dates are when the request was logged.

| ID | Logged | Request | State / next |
|---|---|---|---|
| CONN-01 (Gate E) | 22 Oct; reordered 9 Nov | One read-only scoped connector with consent / revoke / isolation — **now first: Gmail + Calendar**, founder as Google test user (was "OAuth last") | Built: `oauth.py`, `mail_profile.py` (`gmail.readonly`), `/api/mail/needs-reply` (`DEMO_MAIL=1` fixture). Missing: Calendar connector, live OAuth keys. Contract (from assistant-review-decisions.md, 22 Oct): read-only, sender/thread validation, an email is not proof. Google allows up to 100 test users without app verification; a public launch with mailbox scopes needs verification plus a security assessment (from memory, re-check). |
| MEM-01 | 8–9 Nov | Memory-engine Stage-2 pick (Mem0 / Graphiti / port-only) and its "enough history" trigger; §R-ND decay rates per store; P4: convert the recommender's 90-day expiry to floor behaviour | Decision pending. Package: `%USERPROFILE%\Documents\Claude\Projects\proposals\memory-engine\` (`DECISION-BRIEF.md` D1–D3, checklist C1–C7, eval set first). |
| COMP-CF | 2 Nov | Residence-companion phases C–F | C1–C3 started (`mem_*`, `/api/memory/*`, Me timeline); C4 demo-resident seed pending (fixture facts are `demo_fixture`). D Builder MCP, E five demo journeys, F UAE Pass sandbox + bill-pay draft (lines stay Waiting/Blocked) are parked. "Yes to all" is removed from E3/E5: one tap per side effect. Plan: `docs/archive/superpowers/plans/2026-11-02-residence-companion-mcp.md`. |
| Gate B | 22 Oct | Consented check-backs: user-chosen time, persisted, deduped, quiet hours, outbox message; cancel/reschedule suppresses pending ones | FIN-05 built 23 Oct (backend + original mobile app; clock-controlled tests). Not verified: live delivery in a browser, PostgreSQL apply of `20261023000100_assist.sql`. Not in `apps/site`. The daily-card slot reuses it. |
| Gate F | 22 Oct | Morning brief: optional daily brief at a chosen time, stored as a chat message; activation, pause and expiry explicit | FIN-07 built 23 Oct on FIN-05; same verification gaps. |
| Gate D | 22 Oct | Personalised news / reading cards | Headline pilot built (attributed, dated links via Tavily; pull-only). Open: admitted source register, rights, freshness, URL dedupe, explicit sensitive-topic opt-in (`docs/references/reading-source-register.md`). Never mixed with decision urgency. Now under Notice, matched to confirmed interests. |
| SUG-01 / EVT-01 | 21 Oct | Confirmed occasions (birthday, school start, visiting family…); dated, sourced future events (festivals, artist visits) | Pending. Occasions are user-saved, never inferred; event dates are organizer-verified; news is not ticket stock. Proactive delivery needs consent, dedupe and quiet hours (rule 8). |
| REC-03C / REC-04 | 22 Oct | Trusted services/products + verified completions; measurement and lifecycle | Pending. Completions only from engine events; sandbox never trains taste. Measure ranking p50/p95; scheduled retention cleanup. The daily-card ranker builds on `recommendations.py`. |
| ADS-01 | 21 Oct | Sponsored food discovery — **low priority** | Pending. Food context only; Sponsored + "Why this ad" labels; organic alternatives; caps and dismissal; empty inventory = no card; never Workspace data or sensitive traits. |
| TAXI-02 | 22 Oct | Lost-item recovery: staged replies first, Gmail later | Staged recovery built 23 Oct (FIN-04). Open: the Gmail receipt-evidence step (after CONN-01) and an evidence-bound collection/delivery decision. No authority or courier contact, no recovery claim. |
| CTX-02 / PLAN-01 | 21 Oct | Selected-card follow-ups; versioned itinerary drafts (museum example) | Pending task-thread work. CTX-02: server-resolved entity/card IDs, selected fragments with provenance, ticket-availability guard (snippets are not inventory). PLAN-01: owner-scoped draft plans, revision-bound before/after diffs, locked items, estimates labelled; a plan is not a booking. |
| SVC-01 | 23 Oct | Services directory expansion: DubaiNow-equivalent coverage in our own design — police info/filing where a real channel exists, DEWA/Salik/bills + top-ups, licensed-charity directory + donations, RTA/parking/visa/health info + booking | Not built; parked with UI. Every entry carries provenance; execution only via a registered adapter (rule 4), otherwise the blocker + "Open official portal". File per category via `docs/services/intake.md`. |
| DB-02 / DB-03 | 21–22 Oct | Recover the original Postgres; hosted Supabase + production identity | DB-02: export the original unhealthy Postgres without resetting its volume; report conflicts before any import. DB-03: follows the hosting recommendation (`status.md`); not set up. |
| REV-01 | 21 Oct | Security/reliability before any public host | Owner checks, quotas and rate limits on paid Places/Routes/map/photo proxies; merchant PIN throttling + roles; multi-worker turn/forget coordination. |
| REV-03 | 22 Oct | Submission package | Founder walkthrough, ten clean ≤4-minute rehearsals, fallback video, deck, hosting/tunnel, small user test — internal target 18 Dec 2026 (`PLAN.md` §5). |
| VIS-02 | 22 Oct | Freely licensed images for all content placeholders | Parked with UI. |

Contracts for the pending IDs above: `docs/archive/implementation-plan.md`.

Idea only, no code or commitment (23 Oct): license the approvals engine (prepare → approve exact side effect → adapter → provider evidence) as SaaS. Revisit after the engine is proven.

## Feature decisions

Written by the `feature-ledger` skill (`.claude/skills/feature-ledger/SKILL.md`). Newest first. A changed mind adds a row and marks the old one `superseded`; rows are never deleted.

| date | feature | decision | note | status |
|---|---|---|---|---|
| 16 Nov | Desktop local-reader imports (Phone Link call log, coding-agent sessions, browser data) via Tauri/Electron, one-click per-source consent | open | Founder 16 Nov ("add these features"). Gate: `docs/Researches/CLAUDE.md` says no phone connector is approved; Phone Link DB is undocumented and unverified; desktop/UI work paused 9 Nov. Needed for the call-log half of the open-loop notice. Awaiting founder: approve in PLAN / later | pending |
| 16 Nov | Google Takeout bulk import (Gmail mbox, Calendar, Contacts; My Activity) | open | Founder 16 Nov. Mbox/ics/vcf as test data is consistent with IN; My Activity (YouTube/Search/Chrome) conflicts with PLAN §2 (YouTube/Instagram not IN, activity counted not narrated) and rule 9. Awaiting founder: scope | pending |
| 16 Nov | ChatGPT/Claude imports: export zip + "paste what it knows" box; tailored extraction skill (user turns only, assistant text never a fact, pasted blocks skipped, sensitive filter) | implement (queued behind demo) | Founder 16 Nov, own message. Manual import, no new connector. Paste = `user_supplied`, "You told me". Optional; not counted in the 3-chat cap | queued under demo |
| 16 Nov | Telegram export and Messenger/Instagram DM export ("Download your information") as manual imports | implement (queued behind demo) | Founder 16 Nov. Manual export only, consistent with ARCHITECTURE §14. Answers the pending "non-Gmail/Calendar sources" row for exports only; live APIs stay out | queued under demo |
| 16 Nov | Chat scope: WhatsApp manual `.txt` export, up to 3 closest chats; email (Gmail/Outlook OAuth; Takeout mbox for test data) as backbone; Google Calendar | implement (queued behind demo) | Founder 16 Nov. Already IN (PLAN §3: Gmail + Calendar, chat-export import). The cap is a product choice, not a technical limit. WhatsApp linked-device and Business-API routes stay out | queued under demo |
| 16 Nov | Dubai deadline notices from email (Emirates ID, visa, vehicle registration, DEWA, Salik, fines) | implement (queued behind demo) | Founder 16 Nov. Notice pillar; read-only prompts from email, execution stays under rule 4 (real adapter + approval). Fits the 23 Oct resident-bills unlock | queued under demo |
| 16 Nov | Open-loop notice: request found in a message + closing event from a connected source + scheduler rule (e.g. "no call to Mom since yesterday") | implement (queued behind demo) | Founder 16 Nov. Rules 1, 2, 8, 9: claim scoped to connected sources, quote and as-of shown, Done / Not today / Wrong buttons, deterministic scheduler, `Demo trigger` label on stage. Without a call-log source, run on chat + email evidence only | queued under demo |
| 16 Nov | **Headless personal demo (no heavy UI):** paste full chat logs (founder + mother) + connect Gmail -> "what can you say about me" (reveal) -> daily morning brief | implement (now) | Founder 16 Nov, own message. Maps to lab steps 1-6 in `apps/api/app/lab/CLAUDE.md`. Pasted logs = manual export, so consistent with PLAN §2 WhatsApp rule. Real data stays outside the repo. Blocker: no Google OAuth credentials set | active |
| 16 Nov | Morning brief (news section, on-demand search) | implement (via the demo above, brief first, news after reveal scores well) | Design: `docs/plan/morning-brief.md` | queued under demo |
| 16 Nov | Personalized morning brief with news section + on-demand search (`docs/plan/morning-brief.md`) | open | Extends the Notice pillar. Adds news providers and a public article cache; reuses routines, outbox, confirmed profile facts. Awaiting founder: implement / later / other | superseded 16 Nov (see morning brief + demo rows above) |
| 16 Nov | WhatsApp live link (Evolution/Baileys plugin, merged from `cursor/universal-connectors-395e`) | open | Code merged but off. Conflicts with ARCHITECTURE §14 "manual export only". Awaiting founder: implement / later / other | pending |
| 16 Nov | Non-Gmail/Calendar connector sources (Slack, Telegram, Notion, etc.) | open | Registered capabilities only; build order stays Gmail + Calendar first | pending |
