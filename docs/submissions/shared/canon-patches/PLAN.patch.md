# Canon Patch Proposal: `PLAN.md`

- **Target file:** `PLAN.md` (currently 190 lines at `origin/main` `f016856` / `contest-shared` `206b9ff`)
- **Affected line ranges:** lines `3`, `7-15` (§1), `17-125` (§2 decision log — insert new 23 Nov entry + non-destructive supersession tags on lines `28`, `30-33`, `39-43`, `54-56`, `62-78`, `80`, `105-107`, `121-124`), `139-157` (§3 Scope), `171` (§5 Contest facts)
- **Status:** **PROPOSAL ONLY — DO NOT APPLY ON `contest-shared`.**
- **When to apply:** Only after the founder reconciles the other PC's unpushed `main` with `origin/main` and approves merging the three-entry contest portfolio into `main`.
- **Merge-conflict notes:**
  - `origin/memory` (`fc2e24a`) and `origin/desktop` (`d07ee53`) both edit **`PLAN.md:49`** (commit `33ea030`, expanding the YouTube 4-Feed Signal Engine bullet). This proposal deliberately leaves lines `44-53` untouched so it does not collide with `origin/memory` / `origin/desktop`. Keep `origin/memory`'s line 49 verbatim on merge.
  - `origin/ios` (`3b12997`) does not touch `PLAN.md`.
  - Check the reconciled PC2 `main` for any new §2 entries dated after 20 Nov 2026 (e.g., `temporal_note` engine lock, Electron desktop, Expo mobile) and place the 23 Nov entry chronologically above them without deleting history.
- **D1 historical-name note:** Legacy lines `PLAN.md:27, 30, 33, 43, 121` contain the retired product name inside earlier decision history. Per the non-deletion rule, those entries are preserved and tagged `[Superseded 23 Nov 2026 — D1/D6]`; no new text uses the retired name as a product name. (If the founder explicitly wants historical occurrences scrubbed during reconciliation, do so only with founder sign-off.)

---

## Hunk 1 — Header & §1 Identity + Three-Entry Portfolio (`PLAN.md:1-16`)

**Rationale:** Preserves the founder-approved 9 Nov 2026 Entry 1 identity verbatim while recording the 23 Nov 2026 three-entry portfolio (D1–D3) and unparking Community (D2) with the strict no-P2P-messaging boundary (D3).

```diff
--- a/PLAN.md
+++ b/PLAN.md
@@ -1,6 +1,6 @@
 # Dubai-io — Plan
 
-**Updated:** 17 Nov 2026 · **Owner:** Haitham · State: [docs/status.md](docs/status.md) · Open requests: [docs/request-backlog.md](docs/request-backlog.md) · Active build: `apps/api/app/lab/CLAUDE.md`
+**Updated:** <post-merge date> · **Owner:** Haitham · State: [docs/status.md](docs/status.md) · Open requests: [docs/request-backlog.md](docs/request-backlog.md) · Active builds: Entry 1 (`apps/memory/`, `apps/desktop/`, `apps/mobile/`) · Shared (`apps/api/app/identity/`, `apps/api/app/memory_bridge/`) · Entries 2 & 3 (`docs/submissions/CLAUDE.md`)
 
 The single plan: identity, founder decisions, scope locks, live rulings, contest facts, demo arc, pitch guardrails. Done work lives in git history; the previous version of this file is `git show main:PLAN.md`.
 
@@ -12,4 +12,13 @@
 
 **References:** Quest (new.quest) is the closest reference for Know and Notice — its experience, not its access methods (a cloud phone linked to the user's WhatsApp, residential proxies, unconfirmed inference of sensitive facts). Grok Bot is the reference for task threads.
 
-**What it is not:** not a visitor or tourist app (visitor framing retired 22 Oct) · not a DubaiNow clone · not a services-only or shop app (services are capabilities inside Do) · not a social network (community parked 9 Nov; Persocial is a separate project).
+**What Entry 1 is not:** not a visitor or tourist app (visitor framing retired 22 Oct) · not a DubaiNow clone · not a services-only or shop app (services are capabilities inside Do) · not a social network (the 9 Nov community parking and separate-Persocial ruling are **superseded 23 Nov 2026 by D2/D3**: Dubai-io Community is Entry 2 and replaces Persocial, while Entry 1 stays a personal AI companion).
+
+### Three-entry contest portfolio (approved by the founder, 23 Nov 2026; D1–D7)
+
+All three Dubai Chambers entries share **one verified `user_id`** (`apps/api/app/identity/`) and **one authorised long-term memory service** (`apps/memory/`, package `temporal_memory`, reached through `apps/api/app/memory_bridge/`). Each entry keeps its own app, agentic workflow, and honest evidence:
+
+| # | Track | Entry | Reference shape | Owns |
+|---|---|---|---|---|
+| 1 | Best Personal AI Agent | **Quest / Dubai-io** | ChatGPT-like | Memory-based personal agentic companion (Know / Notice / Do) |
+| 2 | Best Societal AI Agent | **Dubai-io Community** | Facebook-like | Feed, profiles, posts, groups, discovery, community agents (**replaces Persocial**; **NO P2P messaging** — Inbox is notifications only) |
+| 3 | Best Business AI Agent | **Messenger** *(working name; final name pending)* | WhatsApp-like | **All person-to-person messaging** (1:1, groups, media, stickers) and chat-to-action business agents |
```

---

## Hunk 2 — §2 Founder Decisions Log: Insert 23 Nov 2026 Entry & Mark Superseded Entries (`PLAN.md:17-125`)

**Rationale:** Records D1–D7 at the top of §2 and marks superseded prior rulings in-place (20 Nov, 19 Nov Evening, 19 Nov, 18 Nov, 17 Nov, 16 Nov, 9 Nov, 23 Oct) without deleting any historical record. Explicitly preserves the Permanent Quest Reference Lock (`PLAN.md:60`) and leaves `PLAN.md:49` untouched for `origin/memory` reconciliation.

```diff
--- a/PLAN.md
+++ b/PLAN.md
@@ -17,19 +17,34 @@
 ## 2. Founder decisions log (newest first)
 
-Only decisions still in force. Superseded ones stay in git history.
+Earlier entries superseded by later founder rulings remain below, explicitly marked `[Superseded <date>]`, for audit traceability.
+
+**23 Nov 2026 — Three-Entry Contest Portfolio, Messenger IP/Name & Stickers, Community Age Gate/Visuals, Ops & `temporal_note` Engine (`docs/submissions/shared/founder-decisions.md` D1–D10)**
+- **Three-entry strategy (sequential & gated):** Entry 1 = Quest / Dubai-io (Best Personal AI Agent); Entry 2 = Dubai-io Community (Best Societal AI Agent); Entry 3 = Messenger *(working name; final name pending)* (Best Business AI Agent). All three share one verified `user_id` and one `temporal_note` memory service; each is delivered through gated phases (P1 Plan → P2 Shared Contract → B0 Shared Build / Gate S → B Entry Builds).
+- **D1 & D8 (Messenger IP, retired name, M0 keep/drop & stickers):** The office owns the old product and its brand; the old product name is **retired** and must never be used as a product name again. Founder-authored redesign code (`github.com/haitham72/Mirsal-redesign`) enters via `--squash` snapshot + immediate rebrand (`MG-B1`/`MG-B2` approved); Diwan, Nadi, `remove-ai-watermarks`, `lib/higgsCli.ts`, and any asset visibly showing the old name/logo are dropped.
+- **D2 (Persocial replaced):** Dubai-io Community is the new home of the Persocial idea; Persocial stops as a separate project.
+- **D3 (App & messaging boundary):** Entry 1 = ChatGPT-like companion; Entry 2 = Facebook-like Community (**no P2P messaging** — Inbox is notifications only; "message this person" hands off to Messenger; parked `chat_*` tables in `apps/api/app/communities.py` stay frozen); Entry 3 = WhatsApp-like Messenger (**owns all P2P messaging** + chat-to-action business agents).
+- **D4 (Messenger current design):** The redesign repo's 19 Nov **AI workspace** (commit `6b45ba4`, "AI workspace replaces Updates tray") is current.
+- **D5 (Memory engine = rewritten `temporal_note`):** Memory for all three entries is the rewritten **temporal_note** engine (`apps/memory/`, package `temporal_memory`). **Hindsight and Honcho are not used**, and Hindsight `AC-1` / `MEM-01` gates do not apply. `apps/api/app/memory_bridge/` is a client of `temporal_note`, never a second engine.
+- **D6 & D7 & D8 (Stickers & Builder excluded):** The contested sticker Builder service (`D:\Vscode\mirsal-builder-io`) is **completely excluded**. Built-in packs are manually founder-made static asset files; user-made stickers support any subject via local U²-Net background removal (Apache-2.0, MediaPipe Selfie Segmentation fallback only) with **no AI image or sticker generation** (zero Higgsfield).
+- **D9 (Community rulings):** Visual authority = `design/references/v3-higgsfield/` layout (`l01,l05,l08,l09` + `m02,m04,m08,m09`, no `r/dubai`, no Stories, `m04` chat → Messenger) styled with `design/20-11-2026/` (Higgsfield never used inside any product). All ages with self-declared age gate (never inferred; under-18s get zero cross-app personalisation, zero memory writes, private-by-default, hidden from adults outside shared groups, moderation priority; UAE child-safety/under-13 policy sourced before `CM-B3`). Private groups invisible to non-members (member invite + mod approval, 1 owner, logged/reversible mod actions). Scene C uses allowlisted official public pages (no integration claim) + non-civic fallback.
+- **D10 (Operations):** 18 Dec demo & `>= 5` consenting-adult tests run over a secure tunnel from the founder's PC; separate Supabase staging project for Entries 2 & 3 (Auth/RLS scripted from `apps/{community,messenger}/supabase/`, `supabase/migrations/` frozen); `temporal_note` requests (`CR-TM-1..4` + 2 fixes) tracked in `docs/submissions/shared/handoff-temporal-note.md` (`FakeTemporalMemoryClient` until landed); founder emails `createaiagents@dubaichamber.com` on prototype reuse.
 
 **20 Nov 2026 — Sovereign Knowledge Vault, 3:4 Peeking Carousel & Proactive Memory Repair UI Lock (`design/20-11-2026/`)**
 - **Mobile UI Standard Locked:** Warm luxury white canvas (`#FFFFFF` / `#FAF8F5`), 4-pillar capsule dock (`Today`, `Chat`, `Quests`, `Memory`) with a central floating audio waveform orb. Full catalog and screen breakdown documented in [`design/20-11-2026/INDEX.md`](design/20-11-2026/INDEX.md).
 - **3:4 Vertical Card Ergonomics:** Category carousels render cards in 3:4 aspect ratio (~78% viewport width) with an ~18% right edge peek to signal horizontal swipe navigation naturally.
 - **Proactive Empathy & Memory Repair Cards:** In-chat gold proactive notification cards (`⚡ Proactive Ping · Memory Repair`) with an instant *"Apology Accepted 👍"* resolution tap, coupled with real-time temporal ingestion badges (`✓ Ingested into Temporal Memory | trust: T1`).
 - **Sovereign Knowledge Vault:** Dual-view interactive constellation graph:
   1. *Subjects View:* 458 nodes across 6 life themes (`Career`, `Projects`, `Learning`, `Gaming`, `Travel`, `Health`) anchored by verified knowledge badges.
   2. *People & Places View:* 179 nodes featuring social trust boundaries (`T1` Inner Circle: `Mamty`, `Radwa`, `Khalid`, `Abdelaziz`) and geographic anchors (`Dubai`, `Istanbul`, `Mirsal Studio`).
-- **Memory Engine Integration:** Fully wired to the locked memory pipeline: Custom Extractors $\to$ Honcho 3-speed deriver $\to$ Hindsight 4-way verdict engine $\to$ Sovereign Knowledge Base.
+- **Memory Engine Integration** *[Superseded 23 Nov 2026 by D5: replaced by rewritten `temporal_note` engine in `apps/memory/`; Honcho and Hindsight are not used]*: Fully wired to the locked memory pipeline: Custom Extractors $\to$ Honcho 3-speed deriver $\to$ Hindsight 4-way verdict engine $\to$ Sovereign Knowledge Base.
 
-**19 Nov 2026 (Evening) — Dual Contest Entry Strategy, Mirsal Studio Business Entry & IDE-Companio Skill Integration**
+**19 Nov 2026 (Evening) — Dual Contest Entry Strategy, Mirsal Studio Business Entry & IDE-Companio Skill Integration** *[Partially superseded 23 Nov 2026 by D1, D3, D6, D7: portfolio expanded to 3 entries; Business entry is now Messenger (rebranded from founder's redesign repo); sticker Builder service completely excluded due to contested ownership (D6). IDE-Companio skill remains in force.]*
 - **Dual Contest Strategy (Dubai Chambers Championship $150k Tracks):**
   1. **Entry 1: Best Personal AI Agent ("AI-Companion: Quest / Dubai IO"):** Flagship personal companion with consented memory management, multi-source temporal ingestion (YouTube 500 titles, Gmail 250 threads, Chrome 23.9k URLs), ScopeGuard privacy shield, and Two-Tower feed spanning 6 life clusters (Gaming, Deals/Hardware, Academics, AI Systems, Design, Career). Presentation elevated to an Executive Showcase Suite.
-  2. **Entry 2: Best Business AI Agent ("Mirsal Studio" — working title, renaming pending):** The product is functionally completed at `G:\Haitham\VsCode\emoji-creator\mirsal-builder-io` (FastAPI backend, PostgreSQL with 36 migrations, 1,898-row cultural emoji bank, Kling 4.0/GPT Image 2.5 generative engine, 44-check deterministic verifier, and Arabic design canvas). Next steps: Focus on founder story, presentation deck, running primarily on local models + cloud fallback, subscription-based pricing for users, and direct export to Telegram / messaging.
+  2. **[Superseded 23 Nov 2026 — D1, D6, D7] Entry 2: Best Business AI Agent ("Mirsal Studio" — working title, renaming pending):** The product is functionally completed at `G:\Haitham\VsCode\emoji-creator\mirsal-builder-io` (FastAPI backend, PostgreSQL with 36 migrations, 1,898-row cultural emoji bank, Kling 4.0/GPT Image 2.5 generative engine, 44-check deterministic verifier, and Arabic design canvas). Next steps: Focus on founder story, presentation deck, running primarily on local models + cloud fallback, subscription-based pricing for users, and direct export to Telegram / messaging.
 - **IDE-Companio Ingestion Skill (`app.lab.skills.ide_session`):**
   - Formally integrated into the Personal Assistant extraction pipeline.
   - Scans local developer transcripts (`~/.claude/projects/`, Codex, Git commits) with secret scrubbing and logs them temporally to the memory engine.
   - **Minimal Developer Presentation:** User-facing representation under the 'Developer' category/filter is strictly minimal (one clean card: project name, 1-sentence accomplishment narrative, commit/token stats; zero raw log or prompt dumps).
 
-**19 Nov 2026 — AI-Companion (Quest) Single Active Focus & Multi-Modal Data Pipeline**
-- **Single Active Focus:** We are exclusively building and demonstrating **Entry 1: Best Personal AI Agent ("AI-Companion: Quest")**. The immediate milestone is pulling real personal context data and rendering a high-fidelity, interactive **Figma-style mockup** (`design/17-11-2026/Quest_ Thoughtful Memory Management.png`) to review the complete experience.
-- **Next Phases (Deferred & Modular):**
-  - *Social (Reddit style with DMs):* Deferred to Phase 5.
-  - *Business (`mirsal-builder-io` / `ide-companio`):* Deferred to Phase 5. Both candidate platforms remain intact.
+**19 Nov 2026 — AI-Companion (Quest) Single Active Focus & Multi-Modal Data Pipeline** *[Partially superseded 23 Nov 2026 by D2, D3, D6: three entries now run sequentially and gated; Community is Facebook-like with NO P2P DMs; sticker Builder excluded. TreeSetter, ingestion pipelines, cost budget, and zero-Gemini rules remain in force.]*
+- **Single Active Focus** *[Superseded 23 Nov 2026]*: We are exclusively building and demonstrating **Entry 1: Best Personal AI Agent ("AI-Companion: Quest")**. The immediate milestone is pulling real personal context data and rendering a high-fidelity, interactive **Figma-style mockup** (`design/17-11-2026/Quest_ Thoughtful Memory Management.png`) to review the complete experience.
+- **Next Phases (Deferred & Modular)** *[Superseded 23 Nov 2026 — D2, D3, D6]*:
+  - *Social (Reddit style with DMs):* Deferred to Phase 5.
+  - *Business (`mirsal-builder-io` / `ide-companio`):* Deferred to Phase 5. Both candidate platforms remain intact.
@@ -54,10 +69,10 @@
-**18 Nov 2026 — Hindsight Go-To Engine, Adaptive KB Export Tree & Permanent Quest Files Lock**
-- **Hindsight is the go-to memory engine (`MEM-01`):** Hindsight owns the 3-tier memory lifecycle: Tier 1 Raw Facts (`retain`), Tier 2 Consolidated Beliefs (`observations`), and Tier 3 Living Knowledge Pages (`Mental Models` via `create_mental_model` + background `reflect`). Product retrieval stays FTS/BM25-first (`ScopeGuard` scoped by category/entity/person), with semantic/RRF ranking inside that scoped slice (`docs/plan/Memory/memory.md`).
+**18 Nov 2026 — Hindsight Go-To Engine, Adaptive KB Export Tree & Permanent Quest Files Lock** *[Hindsight engine choice superseded 23 Nov 2026 by D5 (`temporal_note` in `apps/memory/`); Permanent Quest Reference Lock below remains permanently in force.]*
+- **[Superseded 23 Nov 2026 — D5] Hindsight is the go-to memory engine (`MEM-01`):** Hindsight owns the 3-tier memory lifecycle: Tier 1 Raw Facts (`retain`), Tier 2 Consolidated Beliefs (`observations`), and Tier 3 Living Knowledge Pages (`Mental Models` via `create_mental_model` + background `reflect`). Product retrieval stays FTS/BM25-first (`ScopeGuard` scoped by category/entity/person), with semantic/RRF ranking inside that scoped slice (`docs/plan/Memory/memory.md`).
 - **Adaptive Knowledge Base Export Tree (`docs/plan/Memory/memory.md` §12, benchmarked at `docs/plan/Memory/_archive/hindsight-kb-export/`):** Materializes Hindsight Mental Models & consolidated facts into an upgraded markdown vault:
@@ -62,4 +77,4 @@
-**17 Nov 2026 — SRE Supervisor rulings & MEM-01 decision (AC-5)**
+**17 Nov 2026 — SRE Supervisor rulings & MEM-01 decision (AC-5)** *[Hindsight `MEM-01` row and `AC-1` gate superseded 23 Nov 2026 by D5 (`temporal_note`); Mem0/Graphiti/n8n/orchestrator/card-UI/backfill rulings remain in force.]*
@@ -78,6 +93,6 @@
-**Gate before new features:** Do not proceed to new feature work until **AC-1** (Hindsight LLM-provider extraction verified in `tests/test_live_hindsight_llm.py`), **AC-2** (Card lifecycle `new → seen → actioned → dismissed → resolved` + honest `reminder saved — delivery not yet enabled` label), and **AC-3** (Orchestrator query rewriter) are green. Until AC-1 runs live with an LLM provider enabled, `MEM-01` is tracked as **unproven at the LLM fact-extraction layer** in `docs/status.md`.
+**Gate before new features** *[AC-1 / Hindsight `MEM-01` gate superseded 23 Nov 2026 by D5 (`temporal_note`); AC-2 and AC-3 remain relevant to Entry 1]*: Do not proceed to new feature work until **AC-1** (Hindsight LLM-provider extraction verified in `tests/test_live_hindsight_llm.py`), **AC-2** (Card lifecycle `new → seen → actioned → dismissed → resolved` + honest `reminder saved — delivery not yet enabled` label), and **AC-3** (Orchestrator query rewriter) are green. Until AC-1 runs live with an LLM provider enabled, `MEM-01` is tracked as **unproven at the LLM fact-extraction layer** in `docs/status.md`.
 
-**16 Nov 2026 — memory design** (single plan: `docs/plan/Memory/memory.md`; historical research: `docs/plan/Memory/_archive/memory-research-2026-11.md`)
+**16 Nov 2026 — memory design** (single plan: `docs/plan/Memory/memory.md`; historical research: `docs/plan/Memory/_archive/memory-research-2026-11.md`) *[Engine implementation settled 23 Nov 2026 by D5 as `apps/memory/` (`temporal_memory`); `user_id` isolation, non-destructive correction, source-linked Forget, and aggregate-only cross-user rules remain in force.]*
@@ -105,6 +120,6 @@
-- **Community/social track parked:** code stays, not in the contest build. Personalised feeds stay under Notice.
+- **Community/social track parked** *[Superseded 23 Nov 2026 by D2, D3: unparked as Entry 2 (Dubai-io Community) with new `cm_` tables and NO P2P messaging; parked `apps/api/app/communities.py` code stays frozen]*: code stays, not in the contest build. Personalised feeds stay under Notice.
 - **UI work paused** while a headless pipeline is built in `apps/api/app/lab/` (guide: `apps/api/app/lab/CLAUDE.md`).
-- **Persocial** is a separate, deprioritised project with its own repo. Never build its features into Dubai-io, or the reverse.
+- **Persocial** *[Superseded 23 Nov 2026 by D2: Dubai-io Community replaces Persocial; Persocial stops as a separate project]* is a separate, deprioritised project with its own repo. Never build its features into Dubai-io, or the reverse.
@@ -121,7 +136,7 @@
-- Dubai-io is the product; Mirsal-redesign is visual craft only. Behaviour target: Grok Bot + ChatGPT Dots + Claude Duet. Memory is modelled on temporal_note — copy the engine freely; the founder's personal data is never imported. Vault control dropped.
+- Dubai-io is the product; Mirsal-redesign is visual craft only *[Partially superseded 23 Nov 2026 by D1, D4: founder-authored redesign features now form Entry 3 (Messenger), fully rebranded; 19 Nov AI workspace `6b45ba4` is current]*. Behaviour target: Grok Bot + ChatGPT Dots + Claude Duet. Memory is modelled on temporal_note — copy the engine freely; the founder's personal data is never imported. Vault control dropped.
 - **Cases that must survive:** DXB airport guide and lost item in a taxi.
 - **Look:** white `#FFFFFF` / `#F6F7F8` + accent `#357F92`; soft haze only behind the home greeting/composer and onboarding; dark = Graphite `#141618` / `#1B1E21` / `#202428`, accent `#6FA9B8`. Quality bar: Feed is the benchmark screen; Services gets an uplift to Feed's level when ported.
-- Unified-app decisions 1–11 (`docs/archive/plan/unified-app-design.md` §5) govern the UI when it resumes, except the Assistant ⇄ Community switch (community parked) and "worker/cron stays out": scheduler/outbox jobs are allowed under rule 8.
+- Unified-app decisions 1–11 (`docs/archive/plan/unified-app-design.md` §5) govern the UI when it resumes, except the Assistant ⇄ Community switch (community now lives as separate Entry 2 app per D3) and "worker/cron stays out": scheduler/outbox jobs are allowed under rule 8.
```

---

## Hunk 3 — §3 Scope (IN / LATER / NEVER) & §5 Contest Facts (`PLAN.md:141-177`)

**Rationale:** Adds shared identity + `temporal_note` memory bridge and Entries 2 & 3 to IN; updates LATER to reflect Community unparking (while keeping `apps/site` UI pause distinct from Entry 2/3 demo UIs); encodes D1, D3, D6, D7 hard prohibitions into NEVER; updates §5 to reflect all three Dubai Chambers award tracks.

```diff
--- a/PLAN.md
+++ b/PLAN.md
@@ -141,19 +141,25 @@
 ### IN (contest build)
 
-- **The Know / Notice / Do pipeline**, headless first in `apps/api/app/lab/`: Gmail + Calendar connectors and chat-export import → consolidation into the life themes → reveal → people map → daily matched cards.
+- **Shared foundation (all three entries):** one verified `user_id` (`apps/api/app/identity/`), one `temporal_note` memory engine (`apps/memory/`, package `temporal_memory`) accessed via `apps/api/app/memory_bridge/` with explicit consent scopes and generation-fenced Forget propagation.
+- **Entry 1 — Quest / Dubai-io (Personal):** the Know / Notice / Do pipeline (`apps/memory/` + `apps/api/app/lab/`), Gmail + Calendar connectors and manual chat-export import → reveal → people map → daily matched cards; desktop (`apps/desktop/`) and mobile (`apps/mobile/`) clients.
 - **Task threads** that run a hand-off to an honest terminal state (draft, Waiting, Blocked or `UNKNOWN_STATUS` — never an unproven success), including the two surviving cases.
 - **The shipped contest spine** (2 Nov; list in `docs/status.md`): live Google Places, Google Shopping AE with try-on, memory lite with "Because…" chips, Maps + Dashboard.
+- **Entry 2 — Dubai-io Community (Societal):** Facebook-like social network (`apps/community/`, `apps/api/app/community/`, `cm_*` tables) with community agents and consented interest-feature ranking; **no P2P messaging** (Inbox = notifications only; hands off to Messenger).
+- **Entry 3 — Messenger *(working name)* (Business):** WhatsApp-like AI messenger (`apps/messenger/`, `apps/api/app/messenger/`, `mg_*` tables) rebranded from founder-confirmed redesign code (19 Nov AI workspace `6b45ba4`), owning **all P2P messaging** + chat-to-action business agents; built-in founder-made asset packs + local image background-removal stickers only.
 - Held until after submission: merchant onboarding from a price-list photo; new service cases (`docs/services/cases.md` is frozen).
 
 ### LATER
 
 Civic RAG with citations · background geofencing · ticket wallet · media memory · Arabic RTL UI · live AR try-on · affiliate marketplace feeds. A broader audience does not automatically activate these features. (Unlocked 23 Oct by founder: resident bills + Salik/DEWA displays, payments and third-party purchasing, government transactions — each ships only behind a real adapter with verified evidence; no fake sends.)
 
-Also out of the contest build for now: **community/social track** (parked 9 Nov; code stays) · **UI work** (paused 9 Nov until the headless pipeline works; when it resumes, no UI track is done without founder visual review of a staged preview) · native iOS (STOPPED 23 Oct).
+Also out of the contest build for now: legacy `apps/site` UI rework (paused 9 Nov; Entries 2 and 3 ship dedicated demo UIs under founder visual review of staged previews, and Entry 1's desktop/mobile shells live in `apps/desktop/` and `apps/mobile/`) · native Swift iOS (`apps/ios`, STOPPED 23 Oct). *(Note: the 9 Nov parking of the community/social track is superseded 23 Nov 2026 by D2/D3 for Entry 2; the old `apps/api/app/communities.py` code stays frozen.)*
 
 ### NEVER
 
-Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · copying the official DubaiNow look · bidding / quote / price negotiation in any form.
+Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · copying the official DubaiNow look or Meta/Facebook/WhatsApp marks · bidding / quote / price negotiation in any form · **any code, prompts, design, emoji-bank data, or MCP adapter from the contested sticker Builder service (`D:\Vscode\mirsal-builder-io`, D6)** · **AI image or sticker generation in Messenger (D7)** · **using the retired product name as a product name or shipping office-owned branding/code (D1)** · **building P2P messaging inside Community (D3)** · **claiming end-to-end encryption without independent assessment**.
@@ -168,7 +174,7 @@
 
 Source: `docs/Researches/contest.md` (official page, last updated 15 Oct 2026). Archive a dated screenshot of the rules before submission.
 
-- **Create AI Agents Championship** (Dubai Chambers). Four categories: Societal, Personal, Business, Youth (lead under 21). Our entry: **Best Personal AI Agent** — agents that "help people live better every day". Each category winner gets a USD 150,000 grant; one of them is also named Dubai AI Agent of the Year.
+- **Create AI Agents Championship** (Dubai Chambers). Four categories: Societal, Personal, Business, Youth (lead under 21). **Our three entries (23 Nov 2026; multiple applications permitted per FAQ):** (1) **Best Personal AI Agent** — Quest / Dubai-io; (2) **Best Societal AI Agent** — Dubai-io Community; (3) **Best Business AI Agent** — Messenger *(working name)*. Each category winner gets a USD 150,000 grant; one of them is also named Dubai AI Agent of the Year.
```
