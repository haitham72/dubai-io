# Dubai-io — Plan

**Updated:** 24 Nov 2026 (status block below; dated entries are history) · **Owner:** Haitham · State: [docs/status.md](docs/status.md) · Open requests: [docs/request-backlog.md](docs/request-backlog.md) · Active build: `apps/api/app/lab/CLAUDE.md`

The single plan: identity, founder decisions, scope locks, live rulings, contest facts, demo arc, pitch guardrails. Done work lives in git history; the previous version of this file is `git show main:PLAN.md`.

## 0. Current status (24 Nov 2026, D16)

- **Portfolio:** one monorepo, all on `main`: Dubai-io (Personal), Community (Societal, replaces Persocial) and Messenger (Business, owns person-to-person messaging). Founder decisions D1–D16: `docs/submissions/shared/founder-decisions.md`.
- **Delivery matrix:** each product targets an iPhone app in Expo Go, a website, and an Electron desktop app (Dubai-io's website is Expo web). All nine code targets are on `main`. Android and the $99 Apple Developer account are deferred. The founder's PC hosts the demo stack; Cloudflare Tunnel comes later (D13); Azure's $200 demo credit is reserved for later deployment.
- **Immediate milestone:** the E0–E4 real-data round (`apps/memory/upgrade/prompts/`): local startup, Google sign-in and iPhone pairing, consented Gmail, Calendar, YouTube, Takeout, WhatsApp and desktop ingest, then Chat and Today on real memory. The sticker Builder is excluded (D6). Design polish follows that round; the 20 Nov visual spec is parked at `archive/design-spec-20-11`.
- **Memory engine:** temporal_note (`apps/memory`), replacing Hindsight/Honcho/mem0. Current design, gates and the Vault: `docs/plan/Memory/memory.md` §9, §17, §18. The Vault has seven clusters (Career, Learning, Projects, People & family, Events, Home & money, Travel); inner-circle (T1) members are suggested, then user-confirmed; per D19 (25 Nov), memory decays to floor `0.01` and item/source controls **Lower** weights rather than deleting, while account-level **Delete my data** removes external queries and Redis immediately and keeps a de-identified training backup per FAQs.
- Entries below are dated records. Where they name Hindsight, AC-1/AC-3 gates, Mirsal Studio, a single Personal focus, or `apps/site` as the one app, they are superseded by this block.

## 1. Identity (approved by the founder, 9 Nov 2026)

> **Dubai-io is a personal AI agent for people who live and work in Dubai. It gets to know you first — from the sources you connect (Gmail, Calendar, chats you export) — and shows you what it learned as evidence you can confirm or forget. Then it moves your life forward: each day it brings a few things matched to where you are heading, and when you hand it something, it runs it as a task thread to the end, stopping only at decisions that need you. It never claims what it can't prove, never acts without your tap, and never infers what is sensitive.**

**Three pillars:** **Know** (memory, reveal, people map) · **Notice** (daily matched cards and feeds) · **Do** (task threads, journeys, services as capabilities). The trust rules (`CLAUDE.md` 1–10) cut across all three. UI comes after the headless pipeline works.

**References:** Quest (new.quest) is the closest reference for Know and Notice — its experience, not its access methods (a cloud phone linked to the user's WhatsApp, residential proxies, unconfirmed inference of sensitive facts). Grok Bot is the reference for task threads.

**What it is not:** not a visitor or tourist app (visitor framing retired 22 Oct) · not a DubaiNow clone · not a services-only or shop app (services are capabilities inside Do) · not a social network (Dubai-io itself; the social/community track is the separate Community entry, which replaces Persocial; person-to-person messaging belongs to the separate Messenger entry).

## 2. Founder decisions log (newest first)

Only decisions still in force. Superseded ones stay in git history.

**20 Nov 2026 — Sovereign Knowledge Vault, 3:4 Peeking Carousel & Proactive Memory Repair UI Lock (`design/20-11-2026/`)** [24 Nov: visual spec parked at `archive/design-spec-20-11`; Vault now uses temporal_note's seven clusters, hybrid search and a suggested, user-confirmed inner circle (`memory.md` §§9, 17, 18); the Hindsight/Honcho engine line below is superseded]
- **Mobile UI Standard Locked:** Warm luxury white canvas (`#FFFFFF` / `#FAF8F5`), 4-pillar capsule dock (`Today`, `Chat`, `Quests`, `Memory`) with a central floating audio waveform orb. Full catalog and screen breakdown documented in [`design/20-11-2026/INDEX.md`](design/20-11-2026/INDEX.md).
- **3:4 Vertical Card Ergonomics:** Category carousels render cards in 3:4 aspect ratio (~78% viewport width) with an ~18% right edge peek to signal horizontal swipe navigation naturally.
- **Proactive Empathy & Memory Repair Cards:** In-chat gold proactive notification cards (`⚡ Proactive Ping · Memory Repair`) with an instant *"Apology Accepted 👍"* resolution tap, coupled with real-time temporal ingestion badges (`✓ Ingested into Temporal Memory | trust: T1`).
- **Sovereign Knowledge Vault:** Dual-view interactive constellation graph:
  1. *Subjects View:* 458 nodes across 6 life themes (`Career`, `Projects`, `Learning`, `Gaming`, `Travel`, `Health`) anchored by verified knowledge badges.
  2. *People & Places View:* 179 nodes featuring social trust boundaries (`T1` Inner Circle: `Mamty`, `Radwa`, `Khalid`, `Abdelaziz`) and geographic anchors (`Dubai`, `Istanbul`, `Mirsal Studio`).
- **Memory Engine Integration:** Fully wired to the locked memory pipeline: Custom Extractors $\to$ Honcho 3-speed deriver $\to$ Hindsight 4-way verdict engine $\to$ Sovereign Knowledge Base.

**19 Nov 2026 (Evening) [24 Nov: portfolio is now Dubai-io, Community and Messenger; the sticker Builder is excluded (D6)] — Dual Contest Strategy, Mirsal Studio Business Entry & IDE-Companio Skill Integration**
- **Dual Contest Strategy (Dubai Chambers Championship $150k Tracks):**
  1. **Entry 1: Best Personal AI Agent ("AI-Companion: Quest / Dubai IO"):** Flagship personal companion with consented memory management, multi-source temporal ingestion (YouTube 500 titles, Gmail 250 threads, Chrome 23.9k URLs), ScopeGuard privacy shield, and Two-Tower feed spanning 6 life clusters (Gaming, Deals/Hardware, Academics, AI Systems, Design, Career). Presentation elevated to an Executive Showcase Suite.
  2. **Entry 2: Best Business AI Agent ("Mirsal Studio" — working title, renaming pending):** The product is functionally completed at `G:\Haitham\VsCode\emoji-creator\mirsal-builder-io` (FastAPI backend, PostgreSQL with 36 migrations, 1,898-row cultural emoji bank, Kling 4.0/GPT Image 2.5 generative engine, 44-check deterministic verifier, and Arabic design canvas). Next steps: Focus on founder story, presentation deck, running primarily on local models + cloud fallback, subscription-based pricing for users, and direct export to Telegram / messaging.
- **IDE-Companio Ingestion Skill (`app.lab.skills.ide_session`):**
  - Formally integrated into the Personal Assistant extraction pipeline.
  - Scans local developer transcripts (`~/.claude/projects/`, Codex, Git commits) with secret scrubbing and logs them temporally to the memory engine.
  - **Minimal Developer Presentation:** User-facing representation under the 'Developer' category/filter is strictly minimal (one clean card: project name, 1-sentence accomplishment narrative, commit/token stats; zero raw log or prompt dumps).

**19 Nov 2026 [24 Nov: single focus superseded; current milestone is the E0–E4 real-data round] — AI-Companion (Quest) Single Active Focus & Multi-Modal Data Pipeline**
- **Single Active Focus:** We are exclusively building and demonstrating **Entry 1: Best Personal AI Agent ("AI-Companion: Quest")**. The immediate milestone is pulling real personal context data and rendering a high-fidelity, interactive **Figma-style mockup** (`design/17-11-2026/Quest_ Thoughtful Memory Management.png`) to review the complete experience.
- **Next Phases (Deferred & Modular):**
  - *Social (Reddit style with DMs):* Deferred to Phase 5.
  - *Business (`mirsal-builder-io` / `ide-companio`):* Deferred to Phase 5. Both candidate platforms remain intact.
- **The TreeSetter Engine (`docs/plan/Memory/memory.md` §6):**
  - **Pre-LLM (Tree-sitter AST):** Zero-token deterministic grammar/regex parser extracts device models (`tech/devices/phone`), prices in AED, order numbers, and event dates before LLM invocation.
  - **Post-LLM (Balancer & Router):** Places facts into the 7 life themes, splits branches crossing $\ge 12$ facts or $\ge 3$ sub-clusters into `_staging/proposed-tree-splits.md`, and auto-merges alias near-dupes.
- **Multi-Modal Local Ingestion Pipelines (`docs/plan/data-ingestion-runbook.md`):**
  - **Gmail Live Sync (`scripts/sync_google.py`):** Capped at 50,000 tokens per batch, temporal slicing (`newer_than:30d`), and `category:primary` noise filtering. Verified on 250 emails (~34k tokens) in `data/sync/gmail_latest.json`.
  - **YouTube 4-Feed Signal Engine:** API v3 pulls Uploads, Liked Videos (`LL`), Subscriptions, and User Playlists globally (Watch Later `WL` and Watch History `HL` are unavailable in Data API v3). For Watch History: **Google Data Portability API** (`dataportability.myactivity.youtube`) covers official OAuth history in EEA/UK/Switzerland only; globally/UAE & on mobile use **Google Takeout** (manual upload or one-time scheduled `Export every 2 months for 1 year` → `Add to Drive` auto-synced by our Drive connector) or OS Share Sheet. `scripts/extract_youtube_history.py`'s 0.3s Chrome/Edge SQLite parser is **desktop local-dev only** (phone apps cannot read local Chrome SQLite).
  - **Developer Sessions Extractor (`scripts/extract_dev_sessions.py`):** Scans Claude Code transcripts (`~/.claude/projects/`), Codex, and Git commits with secret-redaction.
- **Context Budget & Cost Taxonomy:** 3-tier cost hierarchy: Always-on ($<3.5$k tokens: rules/identity), Runtime ($\le 50$k tokens: memory/thread), On-demand (never auto-loaded: full KB tree).
- **Security & Sanctions:** Zero Gemini API calls; all real data stays in gitignored `data/sync/` or `G:\Haitham\lab-data\`.

**18 Nov 2026 [24 Nov: Hindsight decision superseded by temporal_note; see `memory.md` §18] — Hindsight Go-To Engine, Adaptive KB Export Tree & Permanent Quest Files Lock**
- **Hindsight is the go-to memory engine (`MEM-01`):** Hindsight owns the 3-tier memory lifecycle: Tier 1 Raw Facts (`retain`), Tier 2 Consolidated Beliefs (`observations`), and Tier 3 Living Knowledge Pages (`Mental Models` via `create_mental_model` + background `reflect`). Product retrieval stays FTS/BM25-first (`ScopeGuard` scoped by category/entity/person), with semantic/RRF ranking inside that scoped slice (`docs/plan/Memory/memory.md`).
- **Adaptive Knowledge Base Export Tree (`docs/plan/Memory/memory.md` §12, benchmarked at `docs/plan/Memory/_archive/hindsight-kb-export/`):** Materializes Hindsight Mental Models & consolidated facts into an upgraded markdown vault:
  - **4 Root Control Files:** `USER.md` (7-section profile with leaf citations), `NOW.md` (active open loops, next-30d occasions, rising 21d topics, pending confirmations), `MEMORIES.md` (complete router index with non-empty descriptions and fact counts), and `SOURCES.md` (watermarks, evidence limits, `Never Remember` blocklist).
  - **7 Fixed Life-Theme Spines + Adaptive LLM-Proposed Sub-Branches:** Top-level folders (`01-people/` through `07-travel-and-places/`) remain fixed for UI/generator stability, while the LLM dynamically branches sub-folders by the user's actual craft and life density (`01-people/{inner-circle,friends-and-peers,professional-network}`, `02-career-and-craft/{ai-engineering-2026,motion-3d-and-video}`, `03-projects/{ai-agents-and-memory/dubai-io,applied-ml-and-rag,culture-and-faith-apps}`) once a leaf crosses ≥8 facts or ≥3 sub-threads.
  - **4-Block Leaf File Format & `_staging/` Gate:** Every leaf file separates `Current Snapshot`, `Open Loops & Active Signals`, `Timeline & Fact History` (with supersession notes), and `Evidence Limits`. Unconfirmed inferences and sensitive categories (`family`, `health`, `faith`, `wellbeing`) stay quarantined in `_staging/hypotheses-to-confirm.md` phrased as `"I noticed..."` until user-confirmed.
- **Permanent Quest Reference Lock:** **NEVER remove, move, or delete `docs/plan/Memory/_archive/quest-memory-export/`, `quest-memory-export.zip`, `quest-tree-mechanics.md`, `hindsight-kb-export/`, or `design/references/quest/` (`cards.jpeg`, `connectors.jpeg`, `full memory md files.jpeg`, `people.jpeg`, `user summary.jpeg`) ever.** They remain permanently on disk as our visual and structural benchmarks and must never be cleaned up by any agent.

**17 Nov 2026 — SRE Supervisor rulings & MEM-01 decision (AC-5)**

Locked architectural decisions (do not relitigate without a written counter-evidence section here):

| Decision | Ruling | Rationale |
|---|---|---|
| **Memory backend (`MEM-01`)** | **Hindsight swappable backend retained; rule violations fixed; full re-fit deferred** | Raw → time-anchored facts → embeddings → multi-strategy recall → graph in one container behind `MemoryBackend` + `ScopeGuard`. Fix the Dubai-io rule violations only (`§R-ND` decay-with-floor instead of retention delete, Amazon.ae in AED, `"I noticed"` phrasing with two-visit qualification, sensitive-category confirmation gate). Full Postgres/markdown-tree re-fit is deferred until the card contract and AC-1 (`tests/test_live_hindsight_llm.py` with LLM provider enabled) are proven. |
| **Mem0** | **Rejected as backend**; retained as **audit checklist** | Weak temporal handling; hash-only dedupe; ADD-only. |
| **Graphiti** | **Deferred** | Requires external graph DB; anecdotal latency/quality loss at small corpus. Revisit only if edge-level `valid_at`/`invalid_at` becomes a hard requirement. |
| **n8n** | **Rejected for core**; optional ingestion edge only | Core is verification-bound, not glue-bound. Auth plumbing may use n8n only if it exceeds 3 days; must POST to existing `/api/ingest`. |
| **Local Qwen (1.5B–3B Jev-style fine-tune)** | **Adopt as classification tier** (after AC-1–AC-3 green) | ~93% on closed-set email triage at ~0.07s/email vs 0.34s remote. Pipeline: `Rules → Qwen → Hindsight → Orchestrator` (`docs/plan/morning-brief.md` §8.5). |
| **Task creation / query rewriting** | **Orchestrator only** | Local classifier returns `{category, status, sender_cluster}` labels only; planner decides tasks and rewrites unscoped queries into `ScopedQuery` (`docs/plan/morning-brief.md` §8.1.1). Never let a 1.5B model route. |
| **Card UI ownership** | **App owns UI**; memory repos do not generate cards | Backend feeds the swipe UI (`new → seen → actioned → dismissed → resolved`); it does not render it. |
| **Backfill agent architecture** | **One accountable lead + bounded delegation + durable SQLite queue** | Goal loop = testable `"done"` contract; `blocked` state routes borderline (<10%) cases to human review; frontier plans / cheap executes (`docs/plan/Memory/memory.md` §20). |
| **`mamty-hindsight` weekly extract (`G:\Haitham\lab-data\mamty-hindsight\`)** | **Prompt-level retain lab run only; blocked from `mem_*` until AC-1 + L3/L4** | ISO week (`Mon–Sun`, recent→older) + ~40–80 msg day packets + Egyptian Arabic/Arabizi kept + never overwrite `status=done` weeks. Raw week JSON requires object schema check (reject `list_root`), `circle.json` alias normalization, `sensitive.py` gate, and user confirmation before touching `mem_*` (`apps/api/app/lab/CLAUDE.md`). |

**Gate before new features** [historical: AC-1 and the AC-3 Hindsight rewriter gate are retired as of 24 Nov; current gates are `memory.md` §18]: Do not proceed to new feature work until **AC-1** (Hindsight LLM-provider extraction verified in `tests/test_live_hindsight_llm.py`), **AC-2** (Card lifecycle `new → seen → actioned → dismissed → resolved` + honest `reminder saved — delivery not yet enabled` label), and **AC-3** (Orchestrator query rewriter) are green. Until AC-1 runs live with an LLM provider enabled, `MEM-01` is tracked as **unproven at the LLM fact-extraction layer** in `docs/status.md`.

**16 Nov 2026 — memory design** [24 Nov: the merged 10-table Postgres service is historical; the active store is temporal_note] (single plan: `docs/plan/Memory/memory.md`; historical research: `docs/plan/Memory/_archive/memory-research-2026-11.md`)

Decided (founder, 16 Nov):
- **One memory service on Postgres (Supabase), every table keyed by `user_id`**, merging Mem0 (links between memories), Graphiti (a dated end for a fact), Hindsight (a verdict per new fact against the closest memories), the Quest tree (sections, topic and person files, profile) and the temporal_note engine. **The md tree is an export, not the store.** This settles the open Stage-2 engine pick of 8–9 Nov: no single engine is adopted.
- **About ten tables:** `sources, source_records, chunks, topics, memories, entities, links, followups, profile, alias_suggestions`. The main ones are `memories` (the full temporal capture) and `profile` (personality rows).
- **Topics:** a fixed list of main sections (10–15) with dynamic subtopics that agents can split, merge, add or remove; the seven life themes of 9 Nov stay the user-visible folders.
- **A correction never overwrites:** the old memory gets an end date and a pointer to the new one. Every memory keeps the message range it came from, so "forget everything from this chat" removes everything built from it.
- **End goals added:** (1) profile screens modelled on Quest's "What I noticed about you", "signature moves" and "Your People", with Confirm / Edit / Not true / Forget on every item; (2) a daily recommender under Notice: shared searches per topic, matched to each user's confirmed topics, pushed with a "Because…" reason, response feedback updates the weights. Cross-user signals stay aggregate-only with a visible opt-out (8–9 Nov); no user's memory is ever shown to or searched by another.
- **Queries the product needs:** by subject across years ("select flights"), by topic or person with counts, by date; the agent answers from these and may correct memory through the same write path.
- **Lab implementation (16 Nov, `ed15f47`):** skill-based extraction (`skills/chat.py`, `skills/email.py`), local sentiment/emotion scorers (`scoring.py`, `scorer_worker.py`), hybrid dense + BM25 + RRF search (`searchlib.py`), recurring topic & resolution follow-ups (`followups.py`), Mermaid topic tree/graph (`tree.py`, `tree_assign.py`), and S0–S5 evaluation harness (`evaluate.py`) were implemented in `apps/api/app/lab/`.

Proposed, not yet approved:
- **Extraction:** chunks sized to the model and cut where the conversation changes (a day or a pause is not a boundary); one memory per fact with its time; the sensitive check runs on messages before extraction, not as one flag per chunk; follow-up questions resolved later by a second pass that may answer only from cited memories.
- **GraphRAG and a graph database: parked.** The `links` table keeps the door open; start only when a set of real questions fails on hybrid search plus links.
- **Sources:** YouTube history and Instagram analytics were requested; neither is in the IN list (activity data would be counted, not narrated). Gmail + Calendar and exported chats remain the IN sources.
- **Order of work** (one active item, no re-ranking until #1 is done): 1 a thin end-to-end slice on real data in Postgres · 2 the verdict step with end dates · 3 a minimal UI (progress bar, tree, ask box, Confirm / Forget) · 4 email · 5 one daily push for the real user from confirmed topics · 6 forget by source, demo data, pitch. The internal target stays Fri 18 Dec (§5).

**Open — positioning wording.** On 16 Nov the founder described the app as an "AI companion for Dubai visitors". §1 and the 22 Oct ruling say it is **not** a visitor or tourist app. Neither is edited here; settle it by editing §1.

**9 Nov 2026**
- Identity and pillars as §1.
- **Gmail + Calendar connectors first**, with the founder as a Google test user. Reverses "Google OAuth last" (21 Oct).
- **Rule 6 strict:** one explicit tap per side effect; no "Yes to all" batch approval. Auto / Ask / Learn modes stay rule-compliant: sends and shares always need a tap.
- **Memory folders are user-visible life themes:** Career · Learning · Projects · People & family · Events · Home & money · Travel. The residence ontology stays the fine tree underneath (`docs/references/residence-ontology-tree.md`). Supersedes the 2 Nov UI-bot list and "user never browses folders".
- **WhatsApp only from manually exported chats** (WhatsApp's own Export chat). No linked device, Baileys or Evolution API, no automation of a personal account.
- **Community/social track parked:** [24 Nov: now the separate Community entry on `main`, D2–D3.]  Personalised feeds stay under Notice.
- **UI work paused** while a headless pipeline is built in `apps/api/app/lab/` (guide: `apps/api/app/lab/CLAUDE.md`).
- **Persocial** is a separate, deprioritised project with its own repo. Never build its features into Dubai-io, or the reverse.

**8–9 Nov 2026 — memory engine** (package outside the repo: `%USERPROFILE%\Documents\Claude\Projects\proposals\memory-engine\`) [Settled 16 Nov above: merged 10-table Postgres service adopted; §R-ND and aggregate-only cross-user rules remain in force]
- **Staged engine:** the deterministic temporal_note port is the early layer; Mem0 or Graphiti takes over per user once there is enough captured history. The Stage-2 pick and its trigger are open.
- **Never-drop rule (§R-ND):** no idea is deleted by age; unrefreshed items lose 20–50% of their weight; a refresh resets the clock. App-layer, applies to every engine.
- **Cross-user learning:** aggregate-only, with a visible opt-out; per-user stores stay isolated; no cross-user retrieval.

**2 Nov 2026** (from docs/archive/root/cursor-plan.md) — residence-companion lock, still valid: not DEWA Jarvis, not a shop, not a DubaiNow clone; Services = a feature (cards → detail → approve → honest proof); "Because…" chips stay rare; the temporal_note *engine* (cloud-slim), never the founder's personal vault. Taxi / UAE Pass demos: no fake Paid / Filed. The UI-bot list (Lifestyle · Career · Social · Household · Money · Travel · Me) is superseded by the 9 Nov life themes.

**23 Oct 2026**
- **One React codebase** (`apps/site`) [24 Nov: delivery superseded: `apps/mobile` Expo Go + Expo web, `apps/desktop` Electron; `apps/site` paused] → website, desktop (Tauri/Electron), iOS/Android (Capacitor), with one central design system: a design change is one edit that echoes everywhere. Screens are ported from the original mobile app, as close as possible to it. Light mode first; dark = Graphite after. Wrapping the original as the phone app was declined.
- **`apps/web` frozen** at tag `mobile-pwa-baseline-2026-10-23`: the reference, never "classic"; embedded at `/?devices` with an Original ⇄ New toggle; retired only after parity and explicit founder approval.
- **Native iOS (Swift) STOPPED.**
- **Lock removal:** government/civic transactions, bill top-ups/payments, in-app donations and third-party purchasing are unlocked — only through a real registered adapter with per-action approval and verified provider evidence (rule 4). Without an adapter: show the blocker and an "Open official portal" link, keep the draft. Still locked: the DubaiNow look, fake statuses, invented facts, bidding.
- Dubai-io is the product; Mirsal-redesign is visual craft only. Behaviour target: Grok Bot + ChatGPT Dots + Claude Duet. Memory is modelled on temporal_note — copy the engine freely; the founder's personal data is never imported. Vault control dropped.
- **Cases that must survive:** DXB airport guide and lost item in a taxi.
- **Look:** white `#FFFFFF` / `#F6F7F8` + accent `#357F92`; soft haze only behind the home greeting/composer and onboarding; dark = Graphite `#141618` / `#1B1E21` / `#202428`, accent `#6FA9B8`. Quality bar: Feed is the benchmark screen; Services gets an uplift to Feed's level when ported.
- Unified-app decisions 1–11 (`docs/archive/plan/unified-app-design.md` §5) govern the UI when it resumes, except the Assistant ⇄ Community switch (community parked) and "worker/cron stays out": scheduler/outbox jobs are allowed under rule 8.
- **Real APIs, real users:** keys in local `.env` only, never committed; each newly keyed path shows real data or its honest unavailable state; a staging API and data set before any real user; fixtures never presented as real.

**22 Oct 2026**
- Visitor-companion identity rejected: Dubai-io is for everyday life and work in Dubai. Learn from Dots, Grok Bot and Duet.
- Adaptive suggestions evolve with recent activity and repeated, separated visits; never a constant feed or a permanent label inferred from one visit. Explicit current intent wins; influence is explained and the user can correct or pause learning (`docs/references/recommender-plan.md`).

**21 Oct 2026** — Supabase (PostgreSQL + pgvector, backend-only `dubaiio` schema) is the selected backend; SQLite stays the test/offline fallback.

**19 Oct 2026** — No shadows; chat looks like ChatGPT/Claude (plain AI text, tinted user box, white rounded action boxes). One order path through the server engine. Lost item (C6) = prefilled report + official handoff + honest "not recovered". No new service cases before submission. Live D-rulings: §4.

**13 Oct 2026** — Temporal profile is core: visible hypotheses with Confirm / Not true / Forget (`ARCHITECTURE.md` §7).

**10 Oct 2026** — No bidding, quotes or negotiation, ever. Fixed published prices; every service row opens its own sandboxed modal mini-app.

## 3. Scope

### IN (contest build)

- **The Know / Notice / Do pipeline**, headless first in `apps/api/app/lab/`: Gmail + Calendar connectors and chat-export import → consolidation into the life themes → reveal → people map → daily matched cards.
- **Task threads** that run a hand-off to an honest terminal state (draft, Waiting, Blocked or `UNKNOWN_STATUS` — never an unproven success), including the two surviving cases.
- **The shipped contest spine** (2 Nov; list in `docs/status.md`): live Google Places, Google Shopping AE with try-on, memory lite with "Because…" chips, Maps + Dashboard.
- Held until after submission: merchant onboarding from a price-list photo; new service cases (`docs/services/cases.md` is frozen).

### LATER

Civic RAG with citations · background geofencing · ticket wallet · media memory · Arabic RTL UI · live AR try-on · affiliate marketplace feeds. A broader audience does not automatically activate these features. (Unlocked 23 Oct by founder: resident bills + Salik/DEWA displays, payments and third-party purchasing, government transactions — each ships only behind a real adapter with verified evidence; no fake sends.)

Also deferred / parked [24 Nov: Community and Messenger are separate entries on `main`, not parked]: the `apps/site` Next.js UI (paused) · design polish (follows the E0–E4 round; no UI track is done without founder visual review of a staged preview) · Android and the $99 Apple Developer account · native Swift iOS (`apps/ios`, STOPPED 23 Oct).

### NEVER

Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · copying the official DubaiNow look or Meta/Facebook/WhatsApp marks · bidding / quote / price negotiation in any form · any code, prompts, design, emoji-bank data, or MCP adapter from the contested sticker Builder service (`D:\Vscode\mirsal-builder-io`, D6) · AI image or sticker generation in Messenger (D7) · using the retired Messenger product name as a product name or shipping office-owned branding/code (D1) · building P2P messaging inside Community (D3) · claiming end-to-end encryption without independent assessment.

## 4. Live D-rulings (19 Oct)

| # | Decision | Ruling |
|---|---|---|
| D14 | Merchant growth | Inbound opt-in; **AI cold-calling / bulk WhatsApp on HOLD** (UAE Cabinet Res. 56–57/2024; counsel sign-off required) |
| D15 | "Do the rest" autonomy | One explicit approval per side effect |

The other D-rows (D01–D13, D16–D18) are history: `git show main:PLAN.md`, §3.

## 5. Contest facts

Source: `docs/Researches/contest.md` (official page, last updated 15 Oct 2026). Archive a dated screenshot of the rules before submission.

- **Create AI Agents Championship** (Dubai Chambers). Four categories: Societal, Personal, Business, Youth (lead under 21). Our entries: **Best Personal AI Agent** (Dubai-io), **Best Societal AI Agent** (Community) and **Best Business AI Agent** (Messenger) — agents that "help people live better every day". Each category winner gets a USD 150,000 grant; one of them is also named Dubai AI Agent of the Year.
- **Timeline:** registration opened 7 Oct 2026 · build phase Nov–Dec 2026 · **January 2027: registration closes; submit the agent prototype + pitch deck + demo video** (day not stated) · January: 24 semi-finalists and the Tech Accelerator · March 2027: semi-final pitch day, 12 finalists · **Grand Final: first week of May 2027**.
- **Internal target: Fri 18 Dec 2026** — deck, demo video, hosting or tunnel, small user test.
- **Rules:** individual or team (max 6) · an original solution, not copied or taken from an existing repository · idea, prototype or early-MVP stage, not fully commercialised · must protect personal, confidential and organisational data and prevent leakage · English only · free to enter. **Finalists must present a fully functional, working agent live** — not an MVP.
- No published rubric; IP terms not stated (portal checked 19 Oct).
- **Service cases frozen until submission.** Try for one real merchant willing to answer on video before the May final (fallback: the labelled sandbox merchant). Hosting + domain by submission (fallback: local + tunnel).

## 6. Demo arc (9 Nov)

Connect Google (Gmail + Calendar) and import exported chats → the reveal → confirm two items → the people map → the next morning's matched card. Plus one task thread run to an honest terminal state.

Stage rules still apply: a trigger the user did not cause (such as fast-forwarding to the morning card) is labelled `Demo trigger` (rule 8); fixture data shows `Demo data` (rule 2).

The earlier visitor arc (late-night DXB arrival → laundry deadline → taxi-memory payoff) and its jury answers are in git history: `git show main:PLAN.md`, §3.

## 7. Pitch guardrails

- Say "it coordinates and follows through with your permission". Never "we replace Google/Careem/DubaiNow", and never claim a live government or partner integration that has no registered adapter and provider evidence.
- The on-stage difference from Quest (from docs/archive/Researches/CLAUDE-2026-11-09-quest-direction.md, 9 Nov): nothing about the user is hidden; no sensitive inference; forget by source ("Forget everything from this chat"); daily cards only from confirmed interests; approval before every side effect.
- Strongest evidence beat: 104,000+ items lost in Dubai taxis in 2025, including ~3,000 passports (official data, 9 Oct research). Claims from forums or unverified research are pitched as "reported", never as measured pain.
