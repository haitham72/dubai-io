# Canon Patch Proposal: `ARCHITECTURE.md`

- **Target file:** `ARCHITECTURE.md` (currently 358 lines at `origin/main` `f016856` / `contest-shared` `206b9ff`)
- **Affected line ranges:** lines `1-49` (header + §1 Shape), `86-93` (§4 Data), `118-138` (§7 Profile and memory), `143-167` (§9 Security and privacy — add §9.3), `168-171` (§10 Deliberately not built), `349-358` (§17 Remaining architecture gaps)
- **Status:** **PROPOSAL ONLY — DO NOT APPLY ON `contest-shared`.**
- **D16 (24 Nov):** all branches merge into `main` after their gates; describe the paths as `main` folders once merged.
- **When to apply:** Only after the founder reconciles the other PC's unpushed `main` with `origin/main` and approves merging the three-entry contract into `main`.
- **Merge-conflict notes:**
  - `origin/memory` (`fc2e24a`), `origin/desktop` (`d07ee53`), and `origin/ios` (`3b12997`) all have **zero diffs** against `origin/main` in `ARCHITECTURE.md`.
  - Check `main` after `memory`, `desktop` and `ios` are merged into it for any updates it made to `ARCHITECTURE.md` (especially §1 Shape and §7 Memory for `apps/memory/` `temporal_memory`, `apps/desktop/`, `apps/mobile/`). Align exact `apps/memory/` routes/ports before applying.

---

## Hunk 1 — Header & §1 Shape (`ARCHITECTURE.md:1-49`)

**Rationale:** Documents the reconciled multi-entry topology (`apps/memory/` `temporal_memory` service on `:8040`, `apps/community/` + `app.community.server` on `:8060`, `apps/messenger/` + `app.messenger.server` on `:8070`, shared `app/identity/` and `app/memory_bridge/`, plus `apps/desktop/` & `apps/mobile/` from PC2 `main`), while keeping parked `communities, social_generation` frozen.

```diff
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -1,19 +1,27 @@
 # Dubai-io — Architecture
 
-**Updated:** 17 Nov 2026 · Scope: `PLAN.md` · State: `docs/status.md` · Root `CLAUDE.md` rules 1–10 win over this file.
+**Updated:** <post-merge date> · Scope: `PLAN.md` · State: `docs/status.md` · Root `CLAUDE.md` rules 1–10 win over this file.
 **Lock:** no bidding/quote. `quote.request`, `QUOTED`, `QUOTE_ACCEPTED` do not exist.
 
 **Core rule:** the LLM reads and proposes; it never mutates. Every side effect goes through the deterministic action engine after a user tap (approval) or a merchant tap (inbox). Truth in status holds by construction.
 
-**Identity (approved 9 Nov 2026; full text in `PLAN.md`):** a personal AI agent for people who live and work in Dubai. Pillars and their sections: **Know** (§7 memory, §14 connectors) · **Notice** (§6 proactive, §15 recommendations) · **Do** (§3 orders, §11 task engine, §12 decisions). UI work is paused while the headless pipeline is built in `apps/api/app/lab/`.
+**Identity (9 Nov 2026; three-entry portfolio 23 Nov 2026, `PLAN.md` §1):** Entry 1 (Quest / Dubai-io) is a personal AI agent for people who live and work in Dubai — **Know** (§7 memory, §14 connectors) · **Notice** (§6 proactive, §15 recommendations) · **Do** (§3 orders, §11 task engine, §12 decisions). Entry 2 (Dubai-io Community, Facebook-like, no P2P messaging) and Entry 3 (Messenger, WhatsApp-like, owns all P2P messaging + business agents) share one verified `user_id` (§9.3) and one `temporal_note` memory service (§7).
 
 ## 1. Shape
 
 ```
 apps/site  THE app: one React codebase (Next.js) → website now; desktop (Tauri/Electron) and
            iOS/Android (Capacitor) packaging parked. UI work paused 9 Nov.
+apps/desktop   Entry 1 Electron desktop shell + local reader (from PC2 main)
+apps/mobile    Entry 1 Expo Go 4-pillar shell + packages/design-tokens (from PC2 main)
 apps/web   original mobile PWA, FROZEN reference (tag mobile-pwa-baseline-2026-10-23);
            served by apps/api at / (and at /lab, a static alias, unrelated to app/lab/)
 apps/dash  founder ops page, static at /dash, reads /api/ops/*
 apps/ios   history only
+apps/community Entry 2 web client (Dubai-io Community; NO P2P messaging, D3)
+apps/messenger Entry 3 client (Messenger, rebranded from founder redesign 6b45ba4; ALL P2P messaging, D1/D3/D4)
+apps/memory    temporal_note engine (package temporal_memory, FastAPI :8040 + StreamableHTTP MCP + Postgres 17/pgvector + RabbitMQ/Redis; D5)
 scripts/   local data ingestion pipelines (Gmail 50k tokens cap, YouTube 4-feed signals, local browser history, dev sessions)
       │ REST commands                       ▲ SSE (actions, messages, merchant inbox)
 apps/api (FastAPI, Python 3.13, :8000 / :8030)
@@ -35,10 +43,14 @@
   google_maps          Places (discovery) · Routes (estimates) · static map · photos
   main: shopping, tryon   Google Shopping AE via SerpAPI · still-photo try-on (tryon.py)
   prayer               Aladhan prayer times
-  communities, social_generation   communities/chats/feed + persona replies: PARKED 9 Nov
+  communities, social_generation   PARKED 9 Nov & frozen (read-only; Entry 2 uses app/community/ + cm_* tables; chat_* NOT extended, D3)
+  identity/            Shared verified user_id, JWT/session verification, per-app capabilities (CS-B0, §9.3)
+  memory_bridge/       Shared client of apps/memory (temporal_note) with consent scopes & Forget propagation (CS-B0, §7)
+  community/           Entry 2 backend (app.community.server:app on :8060, cm_* tables; notifications only, no P2P chat)
+  messenger/           Entry 3 backend (app.messenger.server:app on :8070, mg_* tables; P2P messaging + registered business-agent actions)
   ml_api/ml_models/ml_rag/ml_tasks comment sentiment, embeddings, hybrid search (Celery)
   ops                  founder ops /api/ops/* (X-Ops-Token; unset token = 404)
   widgets              separate origin :8001 for mini-apps (CSP connect-src 'none')
   lab/                 headless Know/Notice/Do pipeline — steps 1–2 + skills (chat, email, ide_session), local sentiment/emotion worker, hybrid search, follow-ups, Mermaid topic tree/graph, and S0–S5 eval harness built (16 Nov)
```

---

## Hunk 2 — §4 Data (`ARCHITECTURE.md:86-93`)

**Rationale:** Records `apps/memory/` (`temporal_memory`) as the active shared memory store (superseding the 16 Nov target row without deleting it) and adds isolated `cs_*`, `cm_*`, and `mg_*` table namespaces while marking the parked `chat_*` tables frozen (D3).

```diff
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -86,7 +86,10 @@
 | Recommender | `recommendation_events`, `profile_interests`, `recommendation_runs` |
 | Connectors (`20261114000100_connectors.sql`) | `connector_credentials`, `connector_connections`, `connector_records`, `connector_sync_log`, `connector_outbound_grants` (Google sign-in grants live in `oauth_attempts`, `oauth_grants`) |
 | Lab (`app/lab/store.py`, `<data>/lab.sqlite`) | `lab_windows`, `lab_annotations`, `lab_vectors`, `lab_rows`, `lab_followups`, `lab_alias_suggestions` (plus `connector_records` and `mem_*`) |
-| Memory Service Target (decided 16 Nov, `PLAN.md` §2) | 10 Postgres tables keyed by `user_id` (`sources, source_records, chunks, topics, memories, entities, links, followups, profile, alias_suggestions`, `vector(768)` + `tsvector`; DDL in `docs/Researches/memory-research-2026-11.md`) |
-| Community (parked) | `personas`, `communities`, `community_members`, `posts`, `comments`, `hidden_posts`, `votes`, `chat_threads`, `chat_messages`, `chat_reads`, `chat_archived`, `contacts`, `call_log`, `social_generations`, `comment_labels`, `comment_embeddings` |
+| Memory Engine (`apps/memory/`, `temporal_memory`, D5 — 23 Nov) | Dedicated Postgres 17 + pgvector schema (`TM_DATABASE_URL`, entity ↔ subject graph, queued job ledger, canonical sensitive gate, generation-fenced Forget-by-source, MCP tokens) |
+| Memory Service Target *[Superseded 23 Nov by `apps/memory/` D5]* (decided 16 Nov, `PLAN.md` §2) | 10 Postgres tables keyed by `user_id` (`sources, source_records, chunks, topics, memories, entities, links, followups, profile, alias_suggestions`, `vector(768)` + `tsvector`; DDL in `docs/Researches/memory-research-2026-11.md`) |
+| Shared Identity & Consent (`app/identity/`, `app/memory_bridge/`) | `cs_*` tables (verified user identity mappings, per-app sessions, WS tickets, consent grants, record-ref index, Forget/revoke audit log) |
+| Community Entry 2 (`app/community/`, 23 Nov) | `cm_*` tables (posts, groups, memberships, community agents, notification inbox; **no P2P chat tables**, D3) |
+| Messenger Entry 3 (`app/messenger/`, 23 Nov) | `mg_*` tables (1:1/group P2P conversations, messages, media, stickers, business-agent sessions & action approvals, D3/D7) |
+| Community (parked 9 Nov — frozen, read-only) | `personas`, `communities`, `community_members`, `posts`, `comments`, `hidden_posts`, `votes`, `chat_threads`, `chat_messages`, `chat_reads`, `chat_archived`, `contacts`, `call_log`, `social_generations`, `comment_labels`, `comment_embeddings` *(not extended; `chat_*` never reused as a chat product, D3)* |
 | Conversation | LangGraph checkpoints |
```

---

## Hunk 3 — §7 Profile and Memory: Cross-App Memory via `temporal_note` (`ARCHITECTURE.md:118-138`)

**Rationale:** Preserves the 16–17 Nov `MEM-01` / Hindsight lines as superseded history (D5) and specifies the active `temporal_note` (`apps/memory/`) cross-app contract: `memory_bridge` as sole client, messages-are-not-memories, per-app read/write isolation, consent scopes, and generation-fenced Forget propagation.

```diff
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -118,10 +118,16 @@
 | Proactive message or daily card | ✓ with consent | ✗ |
 | Set any status | ✗ | ✗ |
 
-- **Memory Architecture & MEM-01 Decision (16–17 Nov, `PLAN.md` §2, `docs/Researches/memory-research-2026-11.md`):**
-  - **Swappable Hindsight backend retained (`MEM-01`):** Keep Hindsight behind the swappable `MemoryBackend` + `ScopeGuard` contract (raw → time-anchored facts → embeddings → multi-strategy recall → graph in one container) and fix the 6 Dubai-io rule violations only (`§R-ND` decay-with-floor instead of retention delete, Amazon.ae/AED, `"I noticed"` phrasing with two-visit qualification, sensitive-category confirmation gate, Gmail/Calendar first); defer full Postgres/markdown-tree re-fit until the card contract and AC-1 (`tests/test_live_hindsight_llm.py` with LLM provider enabled) are proven. Mem0 is rejected as a backend and retained only as an extraction/retrieval audit checklist; Graphiti is deferred unless edge-level `valid_at`/`invalid_at` becomes a hard requirement.
+- **Cross-App Memory via `temporal_note` (23 Nov 2026, D5; contract: `docs/submissions/shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md`):**
+  - **Single memory engine (`apps/memory/`, package `temporal_memory`):** Entity ↔ subject temporal graph, instant L1 context (`live/context.py`), queued extraction workers, HTTP API (`:8040`, `/v1/*`, `/vault/*`, `/hypotheses`, `/timeline`, `/why/{fact_id}`, `/export/md.zip`), StreamableHTTP MCP server (`mcp/server.py`, 7 tools), canonical sensitive gate (`privacy/sensitive.py`), and generation-fenced Forget-by-source (`privacy/forget.py`). **Hindsight and Honcho are not used**; Hindsight `AC-1` / `MEM-01` gates do not apply.
+  - **Client bridge (`apps/api/app/memory_bridge/`):** All three entries reach `temporal_note` exclusively through `memory_bridge` — never build a second memory engine, and never write directly into Entry 1's legacy `mem_*` store (`apps/api/app/memory/`, read-only to Entries 2 and 3).
+  - **Messages are not memories:** A chat message (`mg_*`) or community post (`cm_*`) belongs to its own app. Facts enter `temporal_note` only through consented, source-linked extraction tagged with `(source, actor, host, timestamp, scope, trust_tier)` under explicit conversation/source consent (`Off` / `Session only` / `Save approved memories`). Other people's messages are third-party content, never facts about the user.
+  - **Per-app read boundaries:** Entry 1 (Quest / Dubai-io) reads owner-scoped memories and Vault views; Entry 2 (Community) reads **consented interest features only** (never raw chats, email, sensitive facts, or family details); Entry 3 (Messenger) reads **chat-scoped / consented business-context memories only**.
+  - **Forget & revoke propagation:** Source/scope revocation and Forget invoke `temporal_note`'s `privacy/forget.py` generation fence so forgotten items cannot resurrect from in-flight workers, wipe derived projection caches synchronously, and append a user-visible audit event in `cs_memory_audit`.
+- **Memory Architecture & MEM-01 Decision (16–17 Nov, `PLAN.md` §2, `docs/Researches/memory-research-2026-11.md`)** *[Superseded 23 Nov 2026 by D5 (`temporal_note` above)]*:
+  - **[Superseded 23 Nov 2026 — D5] Swappable Hindsight backend retained (`MEM-01`):** Keep Hindsight behind the swappable `MemoryBackend` + `ScopeGuard` contract (raw → time-anchored facts → embeddings → multi-strategy recall → graph in one container) and fix the 6 Dubai-io rule violations only (`§R-ND` decay-with-floor instead of retention delete, Amazon.ae/AED, `"I noticed"` phrasing with two-visit qualification, sensitive-category confirmation gate, Gmail/Calendar first); defer full Postgres/markdown-tree re-fit until the card contract and AC-1 (`tests/test_live_hindsight_llm.py` with LLM provider enabled) are proven. Mem0 is rejected as a backend and retained only as an extraction/retrieval audit checklist; Graphiti is deferred unless edge-level `valid_at`/`invalid_at` becomes a hard requirement.
   - **10-table Postgres target & `lab.sqlite` (`apps/api/app/lab/`):** `sources, source_records, chunks, topics, memories, entities, links, followups, profile, alias_suggestions` remains the target schema when the full Postgres/markdown-tree re-fit runs.
@@ -131,8 +137,8 @@
 - **Visual Architecture & 4-Pillar UI Standard (20 Nov 2026, `design/20-11-2026/INDEX.md`):**
   - **4-Pillar Capsule Dock:** `Today` · `Chat` · `Quests` · `Memory`, anchored by a central floating audio waveform trigger orb.
   - **3:4 Peeking Carousels:** Vertical cards rendered in 3:4 aspect ratio (~78% viewport width) with ~18% right-margin peeking to signal horizontal swiping.
-  - **Proactive Empathy & Memory Repair:** In-chat gold repair cards (`⚡ Proactive Ping · Memory Repair`) allowing 1-tap apology acceptance (`Apology Accepted 👍`) resolving Hindsight contradictions, coupled with live temporal memory ingestion badges (`✓ Ingested into Temporal Memory | trust: T1`).
+  - **Proactive Empathy & Memory Repair:** In-chat gold repair cards (`⚡ Proactive Ping · Memory Repair`) allowing 1-tap apology acceptance (`Apology Accepted 👍`) resolving temporal-memory contradictions *(updated from Hindsight under D5)*, coupled with live temporal memory ingestion badges (`✓ Ingested into Temporal Memory | trust: T1`).
   - **Sovereign Knowledge Vault:** Dual-view interactive constellation graph (`Subjects` with 458 nodes across 6 life clusters; `People & Places` with 179 nodes and `T1` Inner Circle boundary for `Mamty`, `Radwa`, `Khalid`, `Abdelaziz`).
-- **Engine stage (settled 16 Nov):** the deterministic `temporal_note` port (`memory/`) and `apps/api/app/lab/` SQLite pipeline run today; the open 8–9 Nov Stage-2 engine pick was settled on 16 Nov (`PLAN.md` §2) in favor of the merged 10-table Postgres memory service rather than adopting Mem0 or Graphiti separately. No new database without a measured need.
+- **Engine stage (settled 16 Nov; superseded 23 Nov by D5 `temporal_note` in `apps/memory/`):** the deterministic `temporal_note` port (`memory/`) and `apps/api/app/lab/` SQLite pipeline run for Entry 1; cross-app memory is served by `apps/memory/` (`temporal_memory`) via `apps/api/app/memory_bridge/`.
```

---

## Hunk 4 — §9 Security and Privacy: Add §9.3 Verified Cross-App Identity (`ARCHITECTURE.md:145-167`)

**Rationale:** Documents the shared verified `user_id` boundary (`apps/api/app/identity/`), strict separation from anonymous `dubaiio_lab_session` cookies, no-merge-by-display-name, per-app sessions + WS tickets, and 1:1 `temporal_memory.owners.id` + per-user `owner-device` token binding.

```diff
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -162,4 +162,14 @@
 - **DB-02:** never reset or delete the original (unhealthy) Postgres volume; no destructive repair. Supabase is a new target, not its recovery. Before any import: consistent export, owner/action/fact/outbox/checkpoint inventory, source-vs-target counts and a conflict report. Never overwrite new records or merge owners by display name. Old SQLite checkpoints were archived, not imported. If the old source is unreadable, document the limit.
 - **No public `tester` owner override.** Server-owned cookie sessions stay the identity until real auth exists.
 - **REV-01:** before public exposure, paid Places/Routes/static-map/photo proxies need owner checks, quotas, bounded validation and honest upstream timeouts (a working key settles nothing), and the sandbox merchant PIN needs attempt throttling. Production merchant/operator roles are separate work; never weaken ownership checks because there is one tester. Fix connection lifecycle and multi-worker turn/forget coordination before claiming production readiness.
 
+### 9.3 Verified cross-app identity (`apps/api/app/identity/`)
+
+- **One verified `user_id` (`cs_users`, `cs_identity_links`):** Resolved strictly by `(issuer, subject)` from cryptographically verified Bearer JWTs (`HS256`, `RS256`, `ES256`, `EdDSA`; `alg="none"` and algorithm confusion rejected) or active `cs_app_sessions`. Two distinct `(issuer, subject)` pairs never merge by display name or unverified email; secondary linking requires an authenticated challenge (`cs_link_challenges`), and pre-B0 anonymous owners adopt at most once via proof cookie (`cs_session_adoptions`).
+- **D9 Self-declared age gate (`cs_users.age_band`):** `under_13 | teen_13_17 | adult_18_plus | unknown`, self-declared only and never inferred. Any non-`adult_18_plus` principal is fail-closed minor-protected (`is_minor_protected=True`): zero memory writes, zero cross-app personalisation, private-by-default Community profiles, hidden from adults outside shared groups, and moderation priority.
+- **Hard anonymous boundary:** Legacy `dubaiio_lab_session` cookies (`actions.py`) remain isolated to Entry 1 anonymous demo/lab usage and never satisfy `require_verified_jwt`, `require_app_principal`, or `require_ws_principal`. Spoofing headers (`X-User-Id`, `X-Owner`, `X-Owner-Id`, `X-Dubaiio-User`, `X-Principal`) are rejected (`400`).
+- **Per-app sessions & WebSocket tickets:** Sessions (`quest`, `community`, `messenger`) carry closed capability allowlists and never cross app boundaries. Messenger real-time WebSockets on `:8070` use `Origin`-bound single-use WS tickets (`cs_ws_tickets`) or same-origin HttpOnly `cs_session_messenger` cookies and disconnect immediately on session revocation or membership removal (`dubaiio` stays backend-only; browser Supabase Realtime is not used).
+- **`temporal_memory` token binding:** `temporal_memory.owners.id == cs_users.user_id`. Each user receives a dedicated `owner-device` token (`cs_memory_tokens`) for `memory_bridge` calls so `temporal_memory` enforces owner isolation independently; `TM_ADMIN_TOKEN` stays server-side and `worker` tokens are never used for user reads (`docs/submissions/shared/handoff-temporal-note.md`).
+
 (from `docs/archive/implementation-plan.md` §0.4, DB-02, REV-01; `docs/archive/references/assistant-review-decisions.md`)
```

---

## Hunk 5 — §10 Deliberately Not Built & App Boundaries (`ARCHITECTURE.md:168-171`)

**Rationale:** Records D2/D3 Community unparking (keeping `communities.py` `chat_*` frozen), D3 no P2P messaging in Community, D6 Builder exclusion, D7 no AI sticker/image generation, and no unassessed E2EE claims.

```diff
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -168,4 +168,4 @@
 ## 10. Deliberately not built
 
-Background geofencing, indoor maps, ticket wallet, merchant-authored widgets, merchant webhooks, PostGIS, microservices, a new database without a measured need, general browser/password automation, and unofficial messaging integrations (WhatsApp linked device, Baileys, Evolution API, session replay). Community was built 23 Oct and **parked 9 Nov** (code stays; personalised feeds stay under Notice). Redis/RabbitMQ/Celery serve the ML pipeline only. Government writes, payments and purchasing run only through real adapters with per-action approval and evidence (rule 4).
+Background geofencing, indoor maps, ticket wallet, merchant-authored widgets, merchant webhooks, PostGIS, microservices, a second competing memory engine, general browser/password automation, and unofficial messaging integrations (WhatsApp linked device, Baileys, Evolution API, session replay). *(Superseded 23 Nov by D2/D3 for Entry 2: Community is unparked on `apps/community/` + `cm_*`, while the 9 Nov `apps/api/app/communities.py` code and its `chat_*` tables stay frozen and read-only.)* Also deliberately excluded (23 Nov, D3/D6/D7): **P2P messaging inside Community** (owned exclusively by Messenger), **any code/prompts/design/data/MCP from the contested sticker Builder service (`D:\Vscode\mirsal-builder-io`)**, **AI image or sticker generation in Messenger** (founder-made static asset packs + local background removal only), and **unassessed E2EE claims**. Redis/RabbitMQ/Celery serve the ML/memory pipeline only. Government writes, payments and purchasing run only through real adapters with per-action approval and evidence (rule 4).
```

---

## Hunk 6 — §17 Remaining Architecture Gaps (`ARCHITECTURE.md:349-358`)

**Rationale:** Aligns remaining auth and memory gaps with B0 `identity`/`memory_bridge` and `apps/memory/` (`temporal_memory`) `CR-TM-1..4`.

```diff
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -349,10 +349,10 @@
 ## 17. Remaining architecture gaps
 
-- Production auth and roles: Supabase Auth, FastAPI bearer verification, proof-based anonymous-owner transfer, separate merchant/operator roles, cross-device accounts. Local Supabase Auth/Storage/Edge does not mean identity, uploads or webhooks exist.
+- Production auth and roles: wiring `apps/api/app/identity/` (FastAPI Bearer JWT verification, per-app sessions, WS tickets, challenge linking) to live Supabase Auth (`enable_signup` + staging RLS apply for `apps/community/supabase/` and `apps/messenger/supabase/`), proof-based anonymous-owner transfer, separate merchant/operator roles, and migrating `apps/desktop/` & `apps/mobile/` off default `"karim"` owners.
 - Real provider adapters beyond the sandbox inbox; provider cancellation.
 - Durable task worker: the DRAFT/WORKING/WAITING_EXTERNAL/BLOCKED states, leases and the `stale_worker` event (§11).
-- Memory: WhatsApp export + `.mbox`/`.eml` parsers and skill-based extraction/search/tree/eval are built in `app/lab/`; the remaining memory gap is migrating the 16 Nov 10-table Postgres schema (`PLAN.md` §2) + verdict step to Supabase Postgres (alongside `mem_*` migration/RLS parity C6, the §R-ND sweep C3, and Calendar connector live-run).
+- Memory: `apps/memory/` (`temporal_memory`, D5) + `apps/api/app/memory_bridge/` replace the superseded 16 Nov 10-table Hindsight target; remaining gaps are landing `CR-TM-1..4` (`records`, `forget`, `resolve`, HTTP `context`/`search`) and upstream `vault.py`/`forget.py` fixes on `temporal_memory`, switching `MEMORY_BRIDGE_BACKEND=http` against the live service, Calendar connector live-run, and §R-ND sweep reconciliation.
 - Semantic recall over `profile_facts.embedding` (column reserved, nothing writes it).
 - Kill switch and a unified user-visible activity log (§9.1).
 - Production multi-worker coordination for turn/forget and scheduled retention cleanup; single-tester checkpoint forgetting is implemented and tested.
```
