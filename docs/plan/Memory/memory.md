# Memory plan (single source)

**Status:** Proposed design + locked rulings from `PLAN.md` §2 · **Date:** 19 Nov 2026  
**Authority:** root `CLAUDE.md` → `PLAN.md` → `ARCHITECTURE.md` §7 → this file. Research dumps live in `_archive/` — do not treat them as the plan.

---

## 1. What we decided (locked)

| Item | Ruling |
|---|---|
| Backend (`MEM-01`) | Hindsight kept as **swappable** `MemoryBackend` + `ScopeGuard`. Fix Dubai-io rule gaps only. Full Postgres/markdown re-fit **after** AC-1–AC-3. |
| Provider Exclusivity | **One active external MemoryBackend** at a time. The lightweight local session layer is always-on and additive. |
| Store | One Postgres service (`user_id` everywhere). **Markdown tree = export/view, not the store.** |
| Engines merged (ideas, not four products) | Hindsight verdicts · Graphiti end-dates · Mem0-style links (checklist) · Quest tree as export · temporal_note read path · Honcho 3-speed deriver/dreamer & peer scopes |
| Mem0 / Honcho DB | Rejected as backends (importing conceptual primitives only) |
| Graphiti DB | Deferred |
| GraphRAG / graph DB | **Parked.** Use typed `links` + hybrid search first |
| Topics | Fixed spine (~10–15 sections / ontology leaves) + **dynamic** subtopics (split/merge/add) |
| User folders | Seven life themes: `01-people` · `02-career-and-craft` · `03-projects` · `04-learning-and-ideas` · `05-home-and-money` · `06-events-and-occasions` · `07-travel-and-places` |
| Cards | **App owns UI.** Memory feeds state; it does not render cards |
| Knowledge Vault UI | **Dual-View Sovereign Graph:** `Subjects` (458 nodes across 6 life clusters) and `People & Places` (179 nodes with `T1` Inner Circle boundary). Locked 20 Nov 2026 in `design/20-11-2026/INDEX.md`. |
| Gate | No new memory feature work until **AC-1** (live Hindsight LLM retain), **AC-2** (card lifecycle), **AC-3** (query rewriter) are green. *(Proposed AC-4: cross-agent restart continuity test).* |
| LLM Provider Rule | **Zero Gemini API calls.** All extractions run through local LLMs / LM Studio / Qwen 1.5B–3B / Ollama or Antigravity/Haiku/Codex hooks. |
| Provider Health Probe | **Startup verification required:** Backend must respond to health probe and pass 1 test round-trip; otherwise mark degraded and fall back to local session layer with visible notice. |

Lab evidence (`G:\Haitham\lab-data\mamty-hindsight\`): ~57 weeks, ~444 facts = **prompt-level retain only**. Not live Hindsight. Blocked from `mem_*` until schema + aliases + `sensitive.py` + confirm.

---

## 2. Mental model (how to think)

One useful row:

| datetime | topic | actor_id | trust_tier | relation | note |
|---|---|---|---|---|---|
| `2026-11-14 20:15` | `tech/devices/phone` | `agent:chat_listener` | `T2` (user-stated) | `user → buy? → mother[phone]` | mother prefers current Samsung; declined new phone |

That maps to tables: **`memories`** + **`topics`** + **`entities`** + **`links`**.  
`user → buy? → mother[mobile]` is a **typed link**, not GraphRAG (no community clustering).

---

## 3. Tables (ten — summary)

`sources` → `source_records` (`session_id`, `host_id`) → `chunks` → **`memories`** (temporal facts, `valid_from`/`valid_to`, `superseded_by`, `actor_id`, `host_id`, `trust_tier`, `recall_scope`, `edited_by`, `erased_at`) · **`topics`** (section, name, **aliases[]**, `embedding_model_version`, embedding) · **`entities`** (kind: `user | person | agent | org | device`, aliases, identities) · **`links`** · `followups` · `profile` · `alias_suggestions`.

* **Append-only & Audit Trail:** A change **ends** the old row and inserts a new one with `edited_by` (never a silent overwrite). Soft deletion sets `erased_at` with an audit log. Forget-by-source cascades from `sources`.
* **Multi-Host Writer Attribution (`host_id`):** Every write carries `host_id` + `actor_id` so sync engines avoid last-write-wins collisions across machines.
* **Recall Scopes:** `memories.recall_scope` (`default`, `work`, `family`, `health`) bounds what contexts can inform retrieval at query time.
* **Fine ontology (engine IDs):** [docs/references/residence-ontology-tree.md](file:///g:/Haitham/VsCode/contest/docs/references/residence-ontology-tree.md)  
  Example spine leaf for phones: **`tech/devices/phone`** with aliases `{mobile, phone, iphone, samsung, honor, موبايل, تليفون, هاتف}`.

---

## 4. Mnemosyne vs Hindsight (roles & cost tiers)

| | Mnemosyne-like | Hindsight |
|---|---|---|
| Role here | Live **session** / cheap local layer | Long-term **bank** + batch backfill |
| Cost Tier | **ALWAYS-ON** (Built-in session context) | **RUNTIME** (Fetched on-demand, budget-capped) |
| Write | Light; extract optional | `retain` → facts, time, entities |
| Recall | FTS + vector + importance | Semantic + BM25 + graph + time (RRF) |
| Consolidate | Sleep / episodic | Observations + reflect (Dreamer job) |

**Product hybrid policy (founder 18 Nov):** FTS/BM25 **first** (speed/cost); light semantic second inside the FTS/topic slice — not semantic-first over the whole corpus. Dialectic multi-pass reasoning is a Tier-3 escape hatch only for deep "why/where" queries.

---

## 5. Three-Speed Extraction Pipeline (Derive → Summarize → Dream)

```
Incoming Stream (Chat, Email, YouTube, Notes)
  │
  ├── 1. DERIVER (Per-Write, Instant/Cheap)
  │      └── TreeSetter AST + regex -> explicit facts, dates, amounts, quoted entities
  │
  ├── 2. SUMMARIZER (Per-Session / Daily)
  │      └── Rolling short/long session summaries -> session_records
  │
  └── 3. DREAMER / CONSOLIDATOR (Periodic / Scheduled Batch)
         └── Verdict vs bank (unrelated | repeats | changes | ends)
         └── Cross-session deduplication & supersession (valid_to / superseded_by)
         └── Updates lasting profile bullets (profile_interests weights)
         └── Feeds Morning Brief Notice card generators (ScopeGuard gated)
```

**System prompts** fill extract/route/verdict/query-rewrite gaps. **Code** owns FTS schema, aliases, weights, card rank, providers, sensitive gates.

---

## 6. The TreeSetter Engine: Structural AST & Dynamic Ontology Balancer

To prevent memory sprawl and LLM hallucinations, ingestion runs through **TreeSetter**:

### 6.1 Tree-sitter AST Structural Extractor (Pre-LLM)
* **Zero-token, microsecond parsing:** Uses deterministic grammar/regex patterns on raw emails, receipts, order notices, and device specs before LLM extraction.
* **Deterministic entity syntax:**
  $$\texttt{[Device]} \longrightarrow \texttt{brand: Apple, model: iPhone 13 Pro Max, condition: scratched, date: 2024-03-12}$$
  $$\texttt{[Purchase]} \longrightarrow \texttt{merchant: Amazon.ae, item: phone case, amount: 89, currency: AED}$$
* **Invariant:** Numbers, dates, order IDs, and exact model names are copied verbatim into typed slots, preventing LLM fabrication.

### 6.2 TreeSetter Router & Balancer (Post-LLM)
* **Auto-Placement ("The Setter"):** Maps extracted facts to the nearest spine leaf in `docs/references/residence-ontology-tree.md` or the 7 life themes.
* **Dynamic Tree Balancer:**
  * **Auto-Split Threshold:** When any leaf accumulates **$\ge 12$ facts** or **$\ge 3$ distinct sub-clusters**, TreeSetter proposes an adaptive subdivision in `_staging/proposed-tree-splits.md`.
  * **Auto-Merge & Alias Normalizer:** Merges near-duplicate topics (`mobile` / `phone` / `smartphone`) into a single canonical leaf key and updates `topics.aliases[]`.
  * **Max Depth Invariant:** Strict 3-tier folder hierarchy: $\text{Root} \to \text{Life Theme (01--07)} \to \text{Sub-Branch} \to \text{Leaf.md}$.
  * **Link Weaver:** Creates typed cross-links between leaves (e.g. `01-people/inner-circle/mamty.md` $\leftrightarrow$ `05-home-and-money/tech/phone.md` via `user -> buy? -> mother[phone]`).

---

## 7. Multi-Source Ingestion Contracts & Signal Matrix

### 7.1 Gmail Live Sync Pipeline
* **Token Budget Ceiling:** Dynamically streams messages and terminates downloads once reaching the target token cap (`--tokens 50000`, ~110k chars).
* **Temporal Slicing:** Bounds batches to exact time horizons (`--days 30` or `--since / --until`).
* **Category Filtering:** Defaults to `category:primary -in:spam -in:trash`, stripping newsletters and promotional noise.
* **Storage:** Raw dump cached locally in `data/sync/gmail_latest.json` (gitignored).

### 7.2 YouTube 4-Feed Signal Engine (Two-Tower Recommender Fuel)
YouTube activity feeds into the **User Tower** of the Dubai-io candidate generator, cross-matched with Dubai lifestyle & services:

| Feed | Volume Target | Source / Transport | Strategic Role in Memory |
|---|---|---|---|
| **1. Watch History** | Up to 500 titles | **Production/Mobile:** Google Data Portability API (`dataportability.myactivity.youtube`, EEA/UK/CH only) OR Google Takeout (`watch-history.json`, manual or scheduled "Add to Drive" every 2 months globally/UAE) + Share Sheet. **Desktop Dev Only:** Chrome/Edge local SQLite (`extract_youtube_history.py`). | **Actual Consumption (Interest Counts Only):** Aggregated topic/channel signals feeding User Tower (sensitive categories held back). |
| **2. Subscriptions & User Playlists** | Up to 500 titles | Live YouTube Data API v3 (`v3/subscriptions`, `v3/playlists`) — *note: Watch Later (`WL`) is restricted/empty in API v3* | **Aspirational Intent:** Channels followed and user-curated playlists. |
| **3. Liked Videos** | Up to 500 titles | Live YouTube Data API (`v3/playlistItems?playlistId=LL`) | **High-Resonance Signals:** High-affinity topics, favorite creators (e.g. PyTorch LLMs, 3D motion design). |
| **4. Uploads** | Up to 500 titles | Live YouTube Data API (channel uploads playlist) | **Active Craft & Output:** Direct reflection of current creative or technical work (e.g. channel `iHisam`). |

*Note on Watch History Portability:* YouTube Data API v3 removed watch history in 2016 and restricts Watch Later (`WL`). Google's **Data Portability API** (`dataportability.myactivity.youtube`) restores official OAuth watch history with 30/180-day refreshes, **but only for users in the EEA, UK, and Switzerland** (requires restricted-scope verification). Globally (including UAE/Dubai and mobile users), the low-friction mobile path is a one-time Google Takeout schedule (`Export every 2 months for 1 year` → `Add to Drive`) auto-synced via the Google Drive connector, plus manual Takeout upload or Share Sheet; local Chrome SQLite (`scripts/extract_youtube_history.py`) is desktop-only.

---

## 8. Holistic Semantic Retrieval & Query Expansion ("Phone" Case)

When the user queries `"phone"`:
1. **AC-3 Query Rewriter:** Looks up `tech/devices/phone` in the ontology spine and expands to aliases:
   $$\{\text{iphone}, \text{samsung}, \text{honor}, \text{mobile}, \text{smartphone}, \text{موبايل}, \text{تليفون}, \text{هاتف}\}$$
2. **Hybrid Search (BM25 + Dense Embeddings):**
   * BM25 retrieves exact receipts and device mentions (`iPhone 13 Pro Max`, `scratched screen`).
   * Dense vectors retrieve semantic context (`new flagship purchase`, `mobile trade-in`).
   * Reranked using Reciprocal Rank Fusion (RRF, Top 100).
3. **Temporal Link Synthesis:**
   ```
   - Fact 1 (Owned):       "user owns iPhone 13 Pro Max (Graphite)" [valid_from: 2021-10]
   - Fact 2 (Incident):    "user's iPhone back glass was scratched during travel" [event_ts: 2024-03-12]
   - Fact 3 (Intent):      "user intends to upgrade to iPhone 18 Pro Max upon release" [valid_from: 2026-09]
   - Typed Link:           user -> buy? -> mother[phone] (Note: mother prefers Samsung, declined upgrade)
   ```

---

## 9. Adaptive Knowledge Base Export Tree (`hindsight-kb-export/`)

**Locked (18 Nov 2026, founder):** **Hindsight is the go-to memory engine.** Alongside its Postgres temporal fact bank, Hindsight Mental Models materialize to disk via a 36-file upgraded export tree matching Quest 1:1:

### 9.1 Root Control Files (Disambiguated from Runtime)
* **`USER.md`** *(Export View only)* — 7-section executive synthesis (*Identity, Core Craft, Personality, Values, Strengths/Tensions, Interests, Drive*), citing leaf `.md` files. *(Runtime active preference file is named `PROFILE_RUNTIME.md` to prevent name collisions).*
* **`NOW.md`** — Active radar: open loops, next-30-day deadlines, rising 21-day interests vs baseline, pending confirmations.
* **`MEMORIES.md`** — Master tree index & Step-1 router map with 1-line descriptions and fact counts.
* **`SOURCES.md`** — Connected source watermarks, explicit evidence limits, and `Never Remember` blocklists.
* **`MECHANICAL_INDEX.md`** *(Zero-cost provenance)* — Mechanical session index generated without LLM calls, linking subject tags directly to raw session snippets.

### 9.2 Seven Fixed Life Spines (`01`–`07`) + `_staging/` Governance
* `01-people/` — Tiered by closeness (`inner-circle/`, `friends-and-peers/`, `professional-network/`).
* `02-career-and-craft/` — LLM-branched craft clusters (`ai-engineering-2026/`, `motion-3d-and-video/`).
* `03-projects/` — Domain projects (`ai-agents-and-memory/dubai-io/`, `applied-ml-and-rag/`).
* `04-learning-and-ideas/` — Courses, research, reading queues, YouTube learning topics.
* `05-home-and-money/` — Residence/admin, owned devices, subscriptions, shopping wishlists.
* `06-events-and-occasions/` — Birthdays, meetups (AI Tinkerers Dubai), routines.
* `07-travel-and-places/` — Trips, flights, confirmed Dubai places.
* `_staging/` — `hypotheses-to-confirm.md` (unconfirmed `"I noticed..."` items) + `proposed-tree-splits.md` (LLM-proposed sub-branches).

### 9.3 Four-Block Leaf Format
Every leaf file follows:
1. **YAML Frontmatter:** `title`, `description`, `theme`, `ontology_id`, `aliases`, `sources`, `last_verified`.
2. **`## Current Snapshot`:** 2–4 bullets of current state.
3. **`## Open Loops & Active Signals`:** Active questions, upcoming events, buy intents.
4. **`## Timeline & Fact History` + `## Evidence Limits`:** Append-only dated bullets with supersession links.

---

## 10. Strategic Architecture: 3 Contest Entries (Dubai Chambers Championship)

Per [docs/Researches/contest.md](file:///g:/Haitham/VsCode/contest/docs/Researches/contest.md), the system splits cleanly into three \$150k award entries:

```mermaid
flowchart TD
    subgraph Core ["Shared Core Architecture"]
        Engine["Hindsight Temporal Backend + TreeSetter"]
        Vault[("Postgres: memories + topics + links")]
        Engine --> Vault
    end

    subgraph Track1 ["Entry 1: Best Personal AI Agent"]
        Vault --> MB["Morning Brief & Proactive Cards"]
        Vault --> ColdStart["Dubai Resident / Visitor Cold-Start Onboarding"]
    end

    subgraph Track2 ["Entry 2: Best Societal AI Agent"]
        Vault --> Reddit["Dubai Civic Social & Community Mesh"]
        Vault --> DMs["Topic Channels & Direct Messaging"]
    end

    subgraph Track3 ["Entry 3: Best Business AI Agent"]
        Vault --> Ext["VS Code Extension + Dashboard (ide-companio)"]
        Vault --> Slack["Slack Integrator & Agent Audit Evaluator"]
    end
```

1. **Track 1: Best Personal AI Agent** (*Personal Assistant & Onboarding*):
   * Quest-style proactive memory cards (Morning Brief digest).
   * Cold-start assistant for new Dubai residents/visitors (Emirates ID, banking, housing, gyms, places).
2. **Track 2: Best Societal AI Agent** (*Dubai Civic & Community Social*):
   * Reddit-style civic communities (`apps/api/app/communities.py`) with verified local recommendations.
   * Real-time community threads, spam-screened civic interactions, and DMs.
3. **Track 3: Best Business AI Agent** (*Workspace Agent Evaluator & Analytics*):
   * **Core Tool:** `G:\Haitham\VsCode\ide-companio` (Claude Report VS Code Extension).
   * **Capabilities:** Multi-agent transcript inspection (Claude Code, Codex, Antigravity), token burn-rate monitoring, quota reset countdowns, and automated executive achievement reports (sample: `Report_11-19-2026_14-42-34_h-ibrahim.html`).
   * **Slack / Enterprise Integrator:** Evaluates team AI agent outputs and surfaces friction/velocity metrics to leadership.
   * *(Note on `mirsal-builder-io`: Evaluated as a Motion Graphics video asset kit; `ide-companio` is the production software product for the Business Agent entry).*

---

## 11. Implementation Phases & Active Roadmap

### Phase 1: Foundations & Lab Verification (COMPLETE)
* [x] Consolidated single memory specification ([memory.md](file:///g:/Haitham/VsCode/contest/docs/plan/Memory/memory.md)).
* [x] Permanent lock of Quest baseline files (`_archive/quest-memory-export/`).
* [x] 36-file upgraded Hindsight Adaptive KB export tree (`_archive/hindsight-kb-export/`).
* [x] SRE & Ingestion test suite green (`154 passed` in `apps/api/tests/`).
* [x] Live OAuth transport pipeline for Gmail (50k tokens cap) & YouTube (Channel uploads + Liked videos).

### Phase 2: Acceptance Gates & Ingestion Execution (CURRENT ACTIVE)
* [ ] **AC-1:** Live Hindsight LLM-provider extraction proof (`HINDSIGHT_URL` + provider enabled).
* [ ] **AC-2:** Card lifecycle state machine (`new → seen → actioned → dismissed → resolved`).
* [ ] **AC-3:** Orchestrator query rewriter (`phone` $\to$ `tech/devices/phone` + aliases).
* [ ] **Proposed AC-4:** Cross-agent continuity test across restarts with stable `user_id` resolution.
* [ ] **TreeSetter AST implementation:** Rule-based regex/grammar parser for devices and amounts in `apps/api/app/lab/`.
* [ ] **YouTube Watch History import:** Ingest Takeout `watch-history.json` (manual or scheduled "Add to Drive" every 2 months; desktop Chrome SQLite fallback in dev) as aggregated daily interest counts into `04-learning-and-ideas/`.

### Phase 3: Postgres Data Layer & Recommender Wiring (UPCOMING)
* [ ] Thin Postgres schema deployment: `memories`, `topics`, `entities`, `links` with `actor_id` & `session_id`.
* [ ] Promotion gate: promoted confirmed facts from `data/sync/` into `mem_*` tables with `sensitive.py` checks.
* [ ] Two-Tower candidate matching between YouTube interests and Dubai-io service blogs.

### Phase 4: Product Tracks & Contest Delivery (UPCOMING)
* [ ] **Personal Agent:** Wire Morning Brief cards UI to memory store with ScopeGuard.
* [ ] **Societal Agent:** Stand up Reddit-style community threads and civic discovery.
* [ ] **Business Agent:** Package `ide-companio` extension and executive report exporter for submission.

---

## 12. Context Window Budget & 3-Tier Cost Taxonomy

The context window is **the desk, not permanent storage**. Injected memory is governed by explicit cost tiers:

| Cost Tier | Lifecycle | Contents | Token Invariant |
|---|---|---|---|
| **Tier 1: ALWAYS-ON** | Resident every turn | Agent identity, safety rules, active task constraints (`SOUL.md`, `AGENTS.md`). | $< 3,500$ tokens |
| **Tier 2: RUNTIME** | Injected on-demand per query | Relevant memory facts, thread context, ScopeGuard evidence cards (`PROFILE_RUNTIME.md`). | Capped by `inject_budget_tokens` ($\le 50,000$ tokens) |
| **Tier 3: ON-DEMAND** | Read only during deep research | Full Knowledge Base export tree (`hindsight-kb-export/`), raw archives, research dumps. | Never auto-loaded |

* **Budget Overrun Policy:** If retrieved memories exceed the turn's budget, the engine drops lowest-ranked items by RRF score; it never silently truncates facts mid-sentence.
* **Tool & Sub-Agent Tax:** Pipeline agents use per-agent tool allowlists. Extraction agents receive no card tools; card generators receive read-only bank tools.
* **Pointer-Not-Payload Rule:** Resident files (`SOUL.md`, `PROFILE_RUNTIME.md`, system prompts) carry identity, rules, and pointers—**never raw facts, lists, or historical logs**. Exceeding the resident character ceiling is a build failure. Any fact found in a resident file is moved to the bank and replaced by a pointer.

---

## 13. Strategic Scope Lock: AI-Companion (Quest) is the Single Active Build

**Ruling (19 Nov 2026):** We are strictly building **Entry 1: Best Personal AI Agent ("AI-Companion: Quest")**. 
* **Single Active Focus:** Quest-style memory engine, Morning Brief notice cards, and the Two-Tower daily recommendation feed.
* **Next Phases (Deferred / Separate):**
  * *Social (Reddit with DMs):* Parked for Phase 5.
  * *Business (`mirsal-builder-io` / `ide-companio`):* Parked for Phase 5.
* These sister projects will link into the shared memory backend later (following the Meta Facebook/WhatsApp/Instagram modular portfolio model) without diluting or delaying the AI-Companion build.

---

## 13. Multi-Agent Identity & Peer Attribution

To support multi-agent collaboration across surfaces:
1. **Agent Identity (`actor_id`):** Facts record *who* asserted them (`user`, `agent:chat_extractor`, `agent:backfill_worker`). "Agent concluded X about person Y" is tracked distinctly from "User stated X".
2. **Identity Resolution Ladder:**
   $$\texttt{Explicit circle.json Alias} \longrightarrow \texttt{Source-Scoped Prefix (e.g. gmail:user)} \longrightarrow \texttt{Provisional Identity in \_staging/}$$
   * Never merge identities on string similarity alone; proposals require confirmation.
3. **SOUL vs AGENTS Convention:**
   * `SOUL.md`: Who the agent is universally (personality, core constraints).
   * `AGENTS.md`: Shared operational rules across harnesses.
   * `CLAUDE.md`: Lightweight harness pointer.

---

## 14. Onboarding & Cold-Start Interview

Backfill from noisy chat exports is slow and requires extensive filtering. The sanctioned fast bootstrap path is **Interactive Interview Mode**:
* **Mechanism:** The onboarding agent conducts a structured 10-question interview covering life themes (craft, family circle, devices owned, active goals).
* **Authority:** Answers produce **Tier-1 confirmed facts** directly stamped with `trust_tier = 'T1'` and `confirmed_at = NOW()`.
* **Benefit:** Bypasses inference uncertainty and populates high-stakes categories (`family`, `health`, `devices`) with zero hallucination.

---

## 15. Living Project State, HANDOFF.md & Pre-Compression Preservation

1. **`HANDOFF.md` Protocol:** For long-running agent tasks and model switches, each active project maintains a living `HANDOFF.md` at its root:
   * Current milestone state & locked rulings.
   * Completed actions & open blockers.
   * Ready-to-paste resumption prompt for the next agent/model.
   * *Rule:* `HANDOFF.md` is operational world knowledge; it is never written into the user profile table.
2. **Pre-Compression Fact Preservation:**
   * Compression is a memory-loss event. The engine triggers a `derive` pass to commit lasting facts to Postgres **before** context window compression or session close.

---

## 16. Trust Tiers, Egress Scrubbing & Memory Poisoning Defense

All data entering and leaving memory is governed by 4 trust tiers and egress filters:

### 16.1 Trust Tiers
* **Tier 1 (User-Confirmed):** Explicitly verified by the user (`[Confirm]` button or interview answer). Allowed to drive unconstrained proactive cards.
* **Tier 2 (User-Stated):** Direct user text from active conversations. High confidence; sensitive categories still require confirm.
* **Tier 3 (Agent-Inferred):** Inferred by LLMs or patterns; must pass the **two-visit qualification** before entering `_staging/`.
* **Tier 4 (External / Untrusted):** Scraped web text, unverified email bodies, YouTube titles. **Treated strictly as DATA, never instructions.** Cannot alter rules, create sensitive traits, or update profile identities.

### 16.2 Egress Redaction Filter
Before any prompt or memory payload leaves the local system:
* Scans and scrubs auth headers, API keys, tokens, and signed URLs.
* Blocks unconfirmed sensitive health/faith traits from external cloud requests.
* Enforces least-privilege: retrieval agents have read-only access to the knowledge tree.

---

## 17. Visual Knowledge Vault & Active Chat UI Standard (20 Nov 2026)

Documented and verified against production mockups in `design/20-11-2026/` ([INDEX.md](file:///g:/Haitham/VsCode/contest/design/20-11-2026/INDEX.md)):

### 17.1 Dual-View Sovereign Knowledge Graph
The memory engine's export and graph representation is rendered to the user via two specialized interactive visualizer modes:
1. **Subjects Graph (`Dubai-io Knowledge Graph Vault.jpg`, Left Frame):**
   - **Scale:** 458 nodes anchored by central `Haitham` node.
   - **Clusters:** Mapped to life themes — `Career` (142 nodes), `Projects` (98 nodes), `Learning` (76 nodes), `Gaming` (64 nodes), `Travel` (41 nodes), `Health` (37 nodes).
   - **Verification:** Verified facts carry gold/check badges directly corresponding to confirmed `trust_tier = 'T1'` rows in `memories`.
2. **People & Places Graph (`Dubai-io Knowledge Graph Vault.jpg`, Right Frame):**
   - **Scale:** 179 nodes across `People (28)`, `Places (19)`, `Relations (132)`.
   - **Inner Circle (T1) Boundary:** Explicit visual demarcation of `Mamty (T1)`, `Khalid (Family)`, `Radwa (Family)`, and `Abdelaziz (Friend)`.
   - **Geographic Anchors:** `Dubai (Home)`, `Istanbul (Travel)`, and `Mirsal Studio (Project)`.

### 17.2 Chat Stream Integration & Proactive Memory Repair
1. **Real-Time Temporal Ingestion Badge:** Every confirmed chat turn or feedback emits an inline feedback badge:
   `✓ Ingested into Temporal Memory | trust: T1 · topic: <domain>`
   This provides transparent evidence of the bi-temporal write pipeline (`POST /api/memory/chat/turn`).
2. **Proactive Empathy & Memory Repair Cards:**
   When background reflection identifies missed user preferences or contradictions, the engine surfaces an in-chat gold alert (`⚡ Proactive Ping · Memory Repair`) with an instant *"Apology Accepted 👍"* button. Tapping this issues a Hindsight `ends` verdict to invalidate the stale belief and establish the corrected preference without manual profile editing.

