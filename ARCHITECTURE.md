# Dubai-io — Architecture

**Updated:** 25 Nov 2026 (D16–D22 topology, cross-app memory/identity, D19 lower-weight/training backup) · Scope: `PLAN.md` · State: `docs/status.md` · Root `CLAUDE.md` rules 1–10 win over this file.
**Lock:** no bidding/quote. `quote.request`, `QUOTED`, `QUOTE_ACCEPTED` do not exist.

**Core rule:** the LLM reads and proposes; it never mutates. Every side effect goes through the deterministic action engine after a user tap (approval) or a merchant tap (inbox). Truth in status holds by construction.

**Identity (approved 9 Nov 2026; full text in `PLAN.md`):** a personal AI agent for people who live and work in Dubai. Pillars and their sections: **Know** (§7 memory, §14 connectors) · **Notice** (§6 proactive, §15 recommendations) · **Do** (§3 orders, §11 task engine, §12 decisions). UI work is paused while the headless pipeline is built in `apps/api/app/lab/`.

## 1. Shape

```
apps/mobile   Dubai-io client: iPhone via Expo Go, website via Expo web
apps/desktop  Dubai-io Electron desktop client
apps/memory   temporal_note engine (shared memory store; tracker apps/memory/upgrade/)
apps/community, apps/messenger   separate web apps with Expo Go (mobile/) and Electron (desktop/) shells
              shared per-user boundary: apps/api/app/identity + apps/api/app/memory_bridge → temporal_note
apps/site  paused Next.js client (UI work paused 9 Nov)
apps/web   original mobile PWA, FROZEN reference (tag mobile-pwa-baseline-2026-10-23);
           served by apps/api at / (and at /lab, a static alias, unrelated to app/lab/)
apps/dash  founder ops page, static at /dash, reads /api/ops/*
apps/ios   history only
scripts/   local data ingestion pipelines (Gmail 50k tokens cap, YouTube 4-feed signals, local browser history, dev sessions)
      │ REST commands                       ▲ SSE (actions, messages, merchant inbox)
apps/api (FastAPI, Python 3.13, :8000)
  luna/                LangGraph: normalize → understand → validate → [research] → remember
  actions              capabilities, approvals, idempotency, evidence gate, order state machine
  merchant             merchant role, inbox commands (through actions)
  tasks / projects     task threads: revisioned commands, Today lanes, check-backs · workspaces
  proactive            outbox: dedupe_key, consent, quiet hours; reminders, morning brief,
                       assist mode, Demo triggers
  memory/              temporal_note-slim: mem_* tables; timeline, search, hypotheses, forget
  profile/user_profile episodes + hypotheses · profile document + bi-temporal facts
  recommendations/discovery   temporal ranker · owner-bound live place discovery
  mail_profile, oauth, auth   Gmail read-only "needs a reply" · Google grants · connections
  connectors/          universal connector framework (40 catalog specs, 10 plugin modules, encrypted credentials, default-deny outbound)
  reading              pull-only headline metadata
  catalog              host-owned fixed prices (fictional sandbox merchants, demo_fixture)
  google_maps          Places (discovery) · Routes (estimates) · static map · photos
  main: shopping, tryon   Google Shopping AE via SerpAPI · still-photo try-on (tryon.py)
  prayer               Aladhan prayer times
  communities, social_generation   communities/chats/feed + persona replies: PARKED 9 Nov
  ml_api/ml_models/ml_rag/ml_tasks comment sentiment, embeddings, hybrid search (Celery)
  ops                  founder ops /api/ops/* (X-Ops-Token; unset token = 404)
  widgets              separate origin :8001 for mini-apps (CSP connect-src 'none')
  lab/                 headless Know/Notice/Do pipeline — steps 1–2 + skills (chat, email, ide_session), local sentiment/emotion worker, hybrid search, follow-ups, Mermaid topic tree/graph, and S0–S5 eval harness built (16 Nov)
      ▼
Supabase PostgreSQL 17 + pgvector (DATABASE_URL, DATABASE_SCHEMA=dubaiio) — SQLite fallback
(app/db.py). The 2 Nov local run uses SQLite (DATABASE_URL blank); see docs/status.md.
RabbitMQ (broker) + Redis (results) serve only the ML worker; dev runs CELERY_EAGER=1.
```

Native iOS stopped 23 Oct 2026; history in git.

## 2. Contracts

```python
Provenance = Literal["official", "provider_confirmed", "merchant_submitted", "user_supplied", "inferred", "estimate", "demo_fixture"]
# every displayed number carries provenance + as_of; "inferred" is never valid on an approval card or a shared field
Money.kind: Literal["fixed", "from_estimate", "fixture"]   # never "quote"
CardAction: id (registered capability or ui.* only), label, requires_approval, shares[]   # no free-form payload
```

- **Luna output** (`apps/api/app/luna/schema.py`): `intent` ∈ lost_item · airport_guide · service_offers · places_near · order_status · task_help · info_question · market_quote · product_search · greeting · smalltalk · unclear; typed slots; `stated_facts` (allowlisted keys); a short `reply` with no URLs, prices or status words (enforced in `validate`). Research intents add `answer` + `sources[]`.
- **Bridge:** mini-apps may send `order.request` only (`app.ready`, `host.context`, `host.error` are control messages). The host rebuilds items and total from `catalog.py`; widget prices are ignored.

## 3. Order state machine

```
DRAFT ─► AWAITING_APPROVAL ─(user approves exact snapshot)─► DISPATCHING ─(adapter evidence)─► SUBMITTED
SUBMITTED ─(merchant accept + ready_at)─► ACCEPTED ─(merchant)─► READY ─(merchant)─► COMPLETED
SUBMITTED | ACCEPTED | READY ─(merchant)─► DECLINED
DRAFT | BLOCKED | AWAITING_APPROVAL ─(user)─► CANCELLED
ambiguous adapter outcome / interrupted dispatch ─► UNKNOWN_STATUS (no automatic resend)
```

- Ready-time changes are `ready_time` events, not states. The deadline check compares `ready_at` with the user's stated deadline on the server.
- Approval binds snapshot hash + revision + recipient/effect/total; drift → 409. Approval and merchant commands take an `Idempotency-Key`.
- Capabilities without an adapter save drafts as `BLOCKED` with the blocker shown; no fake Send.

## 4. Data

| Area | Tables |
|---|---|
| Actions | `actions` (JSON record + provider), `sessions`, `preparations`, `approvals`, `merchant_sessions`, `merchant_commands` |
| Proactive | `consent`, `outbox` (unique owner + `dedupe_key`), `assist`, `routines` |
| Tasks | `tasks`, `task_events`, `projects`, `project_tasks`, `project_chats`, `project_commands` |
| Profile | `episodes`, `profile_overrides`, `user_profile` (typed core + `attributes` JSONB), `profile_facts` (JSONB value/evidence, validity window, `embedding vector(1536)` reserved) |
| Memory (`memory/schema.py`) | `mem_events`, `mem_entities`, `mem_entity_aliases`, `mem_relationships`, `mem_event_entities`, `mem_patterns`, `mem_advice`, `mem_ontology_paths`. Created at runtime; no versioned Supabase migration or RLS yet (memory-engine checklist C6) |
| Recommender | `recommendation_events`, `profile_interests`, `recommendation_runs` |
| Connectors (`20261114000100_connectors.sql`) | `connector_credentials`, `connector_connections`, `connector_records`, `connector_sync_log`, `connector_outbound_grants` (Google sign-in grants live in `oauth_attempts`, `oauth_grants`) |
| Lab (`app/lab/store.py`, `<data>/lab.sqlite`) | `lab_windows`, `lab_annotations`, `lab_vectors`, `lab_rows`, `lab_followups`, `lab_alias_suggestions` (plus `connector_records` and `mem_*`) |
| Active shared memory store (24 Nov) | temporal_note in `apps/memory`: owner-scoped Postgres records, entities, subjects, facts, evidence and job state; schema and write/read paths in `docs/plan/Memory/memory.md` §18. (The 16 Nov 10-table target in `docs/Researches/memory-research-2026-11.md` is historical.) |
| Shared Identity & Consent (`app/identity/`, `app/memory_bridge/`) | `cs_*` tables (verified user identity mappings, per-app sessions, WS tickets, consent grants, record-ref index, audit/erasure log) |
| Community Entry 2 (`app/community/`, `cm_*` tables) | `cm_profiles`, `cm_follows`, `cm_groups`, `cm_group_members`, `cm_posts`, `cm_post_revisions`, `cm_comments`, `cm_reactions`, `cm_bookmarks`, `cm_group_moderation_log`, `cm_notifications` (**no P2P chat tables**, D3) |
| Messenger Entry 3 (`app/messenger/`, `mg_*` tables) | 1:1/group P2P conversations, messages, media, stickers, business-agent sessions & action approvals (D3/D7) |
| Community (parked 9 Nov — frozen, read-only) | `personas`, `communities`, `community_members`, `posts`, `comments`, `hidden_posts`, `votes`, `chat_threads`, `chat_messages`, `chat_reads`, `chat_archived`, `contacts`, `call_log`, `social_generations`, `comment_labels`, `comment_embeddings` *(not extended; `chat_*` never reused, D3)* |
| Conversation | LangGraph checkpoints |

Backend tables and checkpoints live in the private schema `dubaiio`; browser roles have no access. SQL is written once (`?` placeholders); `app/db.py` translates for Postgres. Tests run on both (`TEST_DATABASE_URL`).

## 5. Widget host

1. Talabat-normal list first (closest + ★ + price-from + turnaround), then each row's modal mini-app, with a fallback when it fails to load within 3 s.
2. Mini-apps load from the widget origin (`WIDGET_PORT`, default 8001) in `<iframe sandbox="allow-scripts">`; never `allow-same-origin`.
3. Widget CSP: `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'`.
4. The host checks `event.source === frame.contentWindow`, version and kind; the provider app checks `event.source === parent`.

## 6. Proactive pipeline

Sources: (a) a reminder the user asked for, (b) order state changes (live over SSE), (c) a check-back the user set on a task (Gate B), (d) the opt-in morning brief routine (Gate F), (e) operator Demo triggers (labelled). Next: daily matched cards (§15). Each message: `dedupe_key` (once per user), consent, quiet hours 23:00–07:00 Dubai (deferred, not dropped), template wording, stored as a normal chat message. No LLM decides when to send. No background geofencing in the PWA.

- **Scheduler/outbox jobs are allowed** (rule 8). Older "worker/cron stays out" wording means no LLM polling or unconsented jobs (rule 8 wins).
- **Check-back:** one outbox row written in the task's transaction, key `checkback:{task}:{at}`; setting it is the consent; reschedule, pause, cancel or complete withdraws the undelivered row.
- **Morning brief:** opt-in, 07:00–22:59 Dubai, expires after 30 days unless renewed.
- **Assist mode** (`/api/assist`: ask · auto · learn) only changes whether consented check-backs and reminders are re-confirmed. No mode sends, shares or pays (§12).

## 7. Profile and memory

| Use | Told / confirmed (`user_supplied`) | Hypothesis (`inferred`) |
|---|---|---|
| Re-rank options | ✓ | ✓ with a visible "Because…" chip |
| Pre-fill a field | ✓ | ✗ |
| Approval card / shared with a merchant | ✓ via the approval card | ✗ |
| Proactive message or daily card | ✓ with consent | ✗ |
| Set any status | ✗ | ✗ |

- **[Superseded 24–25 Nov: the shared memory engine is `temporal_note` (`apps/memory`; `memory.md` §18). The API's older `mem_*` routes and `app/lab` are legacy surfaces. The live engine uses keyword and local multilingual embedding search (`BAAI/bge-m3`), a unified topic tree with per-owner learned terms (`vocab/`), and local/Haiku extraction; T1 membership requires user confirmation. Per D19 (25 Nov), normal user controls never delete/forget — weights lower to hard floor `w_min = 0.01` (below `tau_surface = 0.10`), while account-level Delete my data immediately removes external queries and Redis cache entries while retaining an isolated de-identified training backup per FAQs.]** Historical record follows. **Memory Architecture & MEM-01 Decision (16–17 Nov, `PLAN.md` §2, `docs/Researches/memory-research-2026-11.md`):**
  - **Cross-App Memory via `temporal_note` (`apps/api/app/memory_bridge/`, `docs/submissions/shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md`):**
    - All three entries reach `temporal_note` (`apps/memory/`, `:8040`) exclusively through `memory_bridge` — never a competing engine.
    - **Messages are not memories:** a chat message (`mg_*`) or Community post (`cm_*`) enters `temporal_note` only via explicit user approval/consent (`Off` / `Session only` / `Save approved memories`); third parties' messages stay attributed to their author.
    - **Per-app read boundaries:** Entry 1 (Dubai-io) reads owner-scoped memories & Vault views; Entry 2 (Community) reads **consented interest features only** (never raw chats, emails, or sensitive facts); Entry 3 (Messenger) reads **chat-scoped / consented business context only**.
    - **D19 Lower & Account Delete my data:** item/source lowering drops weight to `w_min = 0.01` (`< 0.10` active threshold; stays visible in Memory Vault and restorable); account-level Delete my data purges Redis/in-process caches synchronously and excludes the owner from all external queries while retaining an isolated de-identified training backup (excluding Google Workspace/YouTube-restricted data per Google Limited Use policy, as disclosed in FAQs).
  - **Swappable Hindsight backend retained (`MEM-01`):** Keep Hindsight behind the swappable `MemoryBackend` + `ScopeGuard` contract (raw → time-anchored facts → embeddings → multi-strategy recall → graph in one container) and fix the 6 Dubai-io rule violations only (`§R-ND` decay-with-floor instead of retention delete, Amazon.ae/AED, `"I noticed"` phrasing with two-visit qualification, sensitive-category confirmation gate, Gmail/Calendar first); defer full Postgres/markdown-tree re-fit until the card contract and AC-1 (`tests/test_live_hindsight_llm.py` with LLM provider enabled) are proven. [24 Nov: superseded — the memory engine is temporal_note in `apps/memory/` (see `docs/plan/Memory/memory.md` §18); Hindsight is not retained.] Mem0 is rejected as a backend and retained only as an extraction/retrieval audit checklist; Graphiti is deferred unless edge-level `valid_at`/`invalid_at` becomes a hard requirement.
  - **10-table Postgres target & `lab.sqlite` (`apps/api/app/lab/`):** `sources, source_records, chunks, topics, memories, entities, links, followups, profile, alias_suggestions` remains the target schema when the full Postgres/markdown-tree re-fit runs. [24 Nov: superseded — the memory engine is temporal_note in `apps/memory/` (see `docs/plan/Memory/memory.md` §18); this 10-table service was not adopted.]
- **Profile document** (`user_profile.py`): `user_profile` is a projection of current `profile_facts` (facets identity · context · situation · preference · like · dislike · routine). A newer statement closes the old fact (`valid_to`, `superseded_by`); Forget deletes the key's history. Only told or confirmed facts are stored here.
- **Hypotheses & Two-Visit Qualification** (`profile.py`, `recommendations.py`, `apps/web/profile.js`): real choices become episodes with allowlisted hypotheses and fixed weights (view 0.5 · dismissal 1 · choice 2); beliefs are Beta(α, β) with half-life decay; surfaced at ≥ 0.7 with ≥ 2 signals across separated visits (**two-visit qualification**, `tests/test_recommendations.py`). Inferred signals are never shown as plain facts — they are phrased as **"I noticed"** with Confirm / Edit / Not true / Forget. Confirm writes a preference fact; Not true / Forget remove it and unlink evidence.
- **Product memory** (`memory/`, temporal_note-slim): owner-scoped `mem_*` events, entities, aliases, relationships, patterns and advice; `/api/memory/*` serves timeline, search, hypotheses, context and forget (Forget removes search/timeline visibility at once). The people map is a view over `mem_relationships`. Personal vault data is never imported.
- **Life-theme folders (founder 9 Nov):** the user sees memory as seven folders: Career, Learning, Projects, People & family, Events, Home & money, Travel. The residence ontology (`docs/references/residence-ontology-tree.md`, `mem_ontology_paths`) stays the fine tree underneath. Supersedes "the user never browses folders" (2 Nov).
- **Every fact keeps its source** (email, chat export, chat turn) plus provenance, so "forget everything from this source" works. Each source shows an evidence-limits line (e.g. "voice notes not read; history before <date> not seen"). (from `docs/Researches/CLAUDE.md` Quest §)
- **Sensitive-category gate (Canon Rule 9 / AC-4, `apps/api/app/lab/sensitive.py`):** **Family, faith/religion, and health** (along with ethnicity, nationality-as-trait, gender, sexuality, politics, credentials, and third parties' private lives) are **never displayed as plain facts** and **never inferred**. `sensitive.py` enforces a two-layer fail-closed filter (deterministic English/Arabic/Arabizi regex + LLM semantic screen `screen()`, tested in `tests/test_lab_rows.py`). Any surface touching family, faith, or health requires explicit user confirmation, phrases inferred candidates as **"I noticed"**, and requires two-visit qualification.
- **Decay follows §R-ND (founder 9 Nov):** nothing is deleted or hidden for being old. An unrefreshed weighted item loses 20–50% of its weight per refresh window; a mention, interaction, Confirm/Edit or provider re-verification resets the clock. Weight floors above zero: the item stays searchable and visible as "faded". Only the user's Forget removes it. Confirmed `user_supplied` facts never decay (a check-in prompt at most). Each decay step stores weight, last_refresh, decayed_at, delta. The recommender's 90-day expiry and temporal_note's linear decay to 0 conflict: §R-ND wins; conversion is open (C3, P4). Source: `%USERPROFILE%\Documents\Claude\Projects\proposals\memory-engine\CONSOLIDATED-PLAN.md` §R-ND.
- **Visual Architecture & 4-Pillar UI Standard (20 Nov 2026, `design/20-11-2026/INDEX.md`):**
  - **4-Pillar Capsule Dock:** `Today` · `Chat` · `Quests` · `Memory`, anchored by a central floating audio waveform trigger orb.
  - **3:4 Peeking Carousels:** Vertical cards rendered in 3:4 aspect ratio (~78% viewport width) with ~18% right-margin peeking to signal horizontal swiping.
  - **Proactive Empathy & Memory Repair:** In-chat gold repair cards (`⚡ Proactive Ping · Memory Repair`) allowing 1-tap apology acceptance (`Apology Accepted 👍`) resolving temporal-memory contradictions, coupled with live temporal memory ingestion badges (`✓ Ingested into Temporal Memory | trust: T1`).
  - **Sovereign Knowledge Vault:** Dual-view interactive constellation graph (`Subjects` with 458 nodes across 6 life clusters; `People & Places` with 179 nodes and `T1` Inner Circle boundary for `Mamty`, `Radwa`, `Khalid`, `Abdelaziz`).
- **Engine stage (settled 16 Nov; superseded 24 Nov by temporal_note, `memory.md` §18):** the deterministic `temporal_note` port (`memory/`) and `apps/api/app/lab/` SQLite pipeline run today; the open 8–9 Nov Stage-2 engine pick was settled on 16 Nov (`PLAN.md` §2) in favor of the merged 10-table Postgres memory service rather than adopting Mem0 or Graphiti separately. No new database without a measured need. [24 Nov: unambiguously superseded — the 10-table service was NOT adopted; the engine is temporal_note in `apps/memory/` (see `docs/plan/Memory/memory.md` §18).]
- **Conversation memory:** LangGraph checkpoints in Postgres, scoped to the session owner and thread. Checkpoints are never the durable record of a task (§11).

## 8. Luna (LangGraph)

`normalize` → `understand` (OpenAI structured output; profile digest in context) → `validate` (allowlists, confidence gate, URL/phone/claim stripping) → conditional: `research` for `info_question` (Tavily, SerpAPI fallback; answer only from cited sources; civic questions refused) or `market_quote` (Finnhub, fixed template) → `remember` (stated facts; requests/incidents are not facts; skipped for task- or project-scoped turns). Tool output is untrusted data. Order status is answered from the order record, never model text. Research queries never copy private project notes.

## 9. Security and privacy

Anonymous cookie sessions own their actions, profile and threads; merchants see only their provider's orders and the approved fields; operator triggers need a merchant session. Keys stay server-side. Snapshots in the browser hold plain text and structured data, never raw HTML or OAuth tokens. Google OAuth grants (identity scopes plus optional `gmail.readonly`) are encrypted server-side; live use needs the founder's OAuth setup (§14). `/api/ops/*` needs `X-Ops-Token`; the token is never logged.

### 9.1 Threat model

| Threat | Mitigation | State |
|---|---|---|
| Prompt injection via hidden text in a page, email, export or notification | Imported content is untrusted quoted data; templated extraction, not raw page text in prompts; `validate` strips URLs/phones/claims; only registered IDs execute (rule 7) | built |
| The agent is a delegated identity | Three modes per domain: **read** (fetch), **recommend** (propose cards, drafts, decisions), **act** (only via a registered adapter after a tap on the exact effect, rules 4, 6) | built (action engine) |
| Credential theft | OAuth2 only; refresh tokens encrypted at rest, never in chat, model input or provider pages; no passwords; no browser/password automation | built |
| Code or OS compromise | Provider HTML only on the sandboxed widget origin (§5); any future agent browsing in an isolated, domain-limited session | widgets built |
| Runaway or abused agent | Throttles and quotas (REV-01); a **kill switch** that stops all agent work at once | kill switch pending |
| No accountability | User-readable **audit log** of every agent action with timestamps; today `task_events`, approvals, `merchant_commands`, outbox | unified log pending |

(from `docs/archive/Researches/Dubai-io_product evolution.md` "Security & Privacy"; only its threat model is adopted, not its desktop/AI-browser product shape)

### 9.2 Data preservation and abuse limits

- **DB-02:** never reset or delete the original (unhealthy) Postgres volume; no destructive repair. Supabase is a new target, not its recovery. Before any import: consistent export, owner/action/fact/outbox/checkpoint inventory, source-vs-target counts and a conflict report. Never overwrite new records or merge owners by display name. Old SQLite checkpoints were archived, not imported. If the old source is unreadable, document the limit.
- **No public `tester` owner override.** Server-owned cookie sessions stay the identity until real auth exists.
- **REV-01:** before public exposure, paid Places/Routes/static-map/photo proxies need owner checks, quotas, bounded validation and honest upstream timeouts (a working key settles nothing), and the sandbox merchant PIN needs attempt throttling. Production merchant/operator roles are separate work; never weaken ownership checks because there is one tester. Fix connection lifecycle and multi-worker turn/forget coordination before claiming production readiness.

### 9.3 Verified cross-app identity (`apps/api/app/identity/`)

- **One verified `user_id` (`cs_users`, `cs_identity_links`):** Resolved strictly by `(issuer, subject)` from cryptographically verified Bearer JWTs or active `cs_app_sessions`. Two distinct `(issuer, subject)` pairs never merge by display name or unverified email; secondary linking requires an authenticated challenge (`cs_link_challenges`), and anonymous adoption requires a signed proof cookie (`cs_session_adoptions`).
- **D11 Self-declared age gate (`cs_users.age_band`):** Community is gated to verified 18+ adults (`ADULT_BANDS`), self-declared and never inferred; any non-adult principal fails closed (`is_minor_protected=True`: zero memory writes, zero cross-app personalisation).
- **Hard anonymous boundary:** Legacy `dubaiio_lab_session` cookies (`actions.py`) stay isolated to Entry 1 anonymous demo usage and never satisfy `require_verified_jwt` or `require_app_principal`. Spoofing headers (`X-User-Id`, `X-Owner`, `X-Owner-Id`, `X-Dubaiio-User`, `X-Principal`) are rejected (`400`).
- **Per-app sessions & WebSocket tickets:** Sessions (`quest`, `community`, `messenger`) carry closed capability allowlists and never cross app boundaries. Messenger real-time WebSockets on `:8070` use `Origin`-bound single-use WS tickets (`cs_ws_tickets`).
- **`temporal_memory` token binding:** `temporal_memory.owners.id == cs_users.user_id`. Each user receives a dedicated `owner-device` token (`cs_memory_tokens`) for `memory_bridge` calls so `temporal_memory` enforces owner isolation independently; `TM_ADMIN_TOKEN` stays server-side.

(from `docs/archive/implementation-plan.md` §0.4, DB-02, REV-01; `docs/archive/references/assistant-review-decisions.md`; D1–D19)

## 10. Deliberately not built

Background geofencing, indoor maps, ticket wallet, merchant-authored widgets, merchant webhooks, PostGIS, microservices, a second competing memory engine, general browser/password automation, and unofficial messaging integrations (WhatsApp linked device, Baileys, Evolution API, session replay). *(Note: Entry 2 Community is unparked on `apps/community/` + `app/community/` + `cm_*`, while the legacy 9 Nov `apps/api/app/communities.py` code and its `chat_*` tables stay frozen and read-only.)* Also deliberately excluded (D3/D6/D7): **P2P messaging inside Community** (owned exclusively by Messenger), **any code/prompts/design/data/MCP from the contested sticker Builder service (`D:\Vscode\mirsal-builder-io`)**, **AI image or sticker generation in Messenger** (founder-made static packs + local background removal only), and **unassessed E2EE claims**. Redis/RabbitMQ/Celery serve the ML/memory pipeline only. Government writes, payments and purchasing run only through real adapters with per-action approval and evidence (rule 4).

## 11. Task engine (Do)

A task thread is the durable record of handed-over work. LangGraph checkpoints hold conversation only.

### 11.1 State machine (target)

States: `DRAFT → WORKING → {WAITING_USER, WAITING_EXTERNAL, BLOCKED} → COMPLETED`; `PAUSED` and `CANCELLED` reachable from any non-terminal state.

| From | Event | To | Guard |
|---|---|---|---|
| DRAFT | accept | WORKING | outcome non-empty; owner matches; idempotency key unused |
| WORKING | need user input | WAITING_USER | the question matters to the next step |
| WORKING | external wait | WAITING_EXTERNAL | an external dependency is open; no local work remains |
| WORKING | source failure | BLOCKED | terminal for this attempt; reason stored |
| WAITING_* | user answers | WORKING | `revision` matches; answer applied atomically |
| WAITING_* | external event | WORKING / COMPLETED | the event is provider evidence, not model text |
| any | pause | PAUSED | no in-flight write may land after the pause revision |
| any | cancel | CANCELLED | `cancelled_at` set; in-flight writes rejected by the guard |
| any | completion | COMPLETED | the outcome is satisfied with evidence for its type |

`COMPLETED` is per outcome, never per model sentence: a draft completes with a draft; a send with provider evidence; a reservation with the provider's evidence (rule 1). **Code today** implements the manual subset: `WAITING_USER ↔ PAUSED → COMPLETED | CANCELLED`; user-reported completion is `user_supplied`, never provider evidence. DRAFT, WORKING, WAITING_EXTERNAL and BLOCKED are not implemented yet.

### 11.2 Revision write guard

```sql
-- every state-changing write:
UPDATE task SET status = :new, revision = revision + 1, updated_at = now()
 WHERE id = :task AND owner = :owner
   AND revision = :expected AND cancelled_at IS NULL;
-- zero rows => rejected (stale worker, cancelled task or concurrent change)
```

1. No transaction spans a provider or LLM call: commit intent, call, commit outcome.
2. After any network wait, re-read and re-assert the revision. A late worker that fails the guard is recorded as a `stale_worker` event, not silently dropped.
3. A cancel after dispatch keeps status CANCELLED but is shown as "cancelled after dispatch: the request may still have reached the provider". The provider's event, if any, still lands in the action engine.
4. Approvals bind to `base_revision` + the exact action snapshot; a changed recipient, price, field set or date invalidates the approval.
5. Every notification is an outbox row whose `dedupe_key` derives from `(task_id, event_seq, kind)`. Outbox dedupe prevents duplicate messages, not duplicate provider calls.

Code today: `tasks.py` adds `AND status IN ('WAITING_USER','PAUSED')`; the `stale_worker` event is not implemented yet.

### 11.3 Race and staleness matrix (each row is a test)

| # | Interleaving | Required behaviour |
|---|---|---|
| 1 | Cancel lands while a provider call is in flight | Guard rejects → `stale_worker` event → task stays CANCELLED with the "may still have reached the provider" note |
| 2 | Two scheduler sweeps fire the same check | `dedupe_key` + `next_check_at` advanced in the same transaction as the claim: one message, one call |
| 3 | User edits a constraint mid-check | Stale result discarded and re-derived; user sees "updated", not "done" |
| 4 | Worker restarts mid-check | `next_check_at` persisted before the work; resume or idempotent re-run; one effect |
| 5 | Quiet hours | The check runs; delivery waits until 07:00 |
| 6 | Ambiguous provider outcome (timeout after send) | `UNKNOWN_STATUS`, reconciled by reading the provider; never a blind retry |
| 7 | Stale worker writes after a revision bump | Guard rejects; `stale_worker`; Today recomputed from current state |
| 8 | Two owners reference the same merchant action | Owner-scoped rows at every read and write |
| 9 | Briefing item read after its source changed | `checked_at` + `max_age` visible; past `max_age` the item is hidden |
| 10 | User edits memory while a task runs | Context is captured per revision; the change applies to the next check and the task shows what changed |

### 11.4 Context and recovery rules

- **Task context is captured per revision, not inherited.** A later memory correction applies to the next step, with a visible "constraints updated" line. Memory edits never silently change approved dates, recipients or shared fields, and stale workers or caches never undo a Forget.
- **References expire.** Focus expires after 30 minutes; a source reference older than its `max_age` is dead, and asking about it says so rather than silently re-fetching.
- **Checkpoints are never the durable record.** Task progress lives in `tasks`/`task_events`; make this a migration-level invariant.
- **Late responses cannot restore old state.** A correction that lands while a Today projection is in flight invalidates it.
- **A late worker never revives a cancelled task.** Revision predicates fence local writes, not external calls already dispatched; late provider evidence stays in the action engine.
- **RUN-01:** persist each transition before saying work is underway; bounded leases, duplicate-event keys, retries only for reads. Recheck revision, cancellation and permissions after network waits. Never hold a database transaction across a provider or LLM call. An ambiguous side effect keeps `UNKNOWN_STATUS` and is reconciled, never auto-repeated. Routines are approved structured steps, never model-written code, with per-run budgets and backoff. A stopped host means no background work; never promise always-on.

(from `docs/archive/references/assistant-experience-review.md` §9.2–9.5; `docs/archive/references/assistant-experience-plan.md` RUN-01; `docs/archive/references/assistant-review-decisions.md` "Engineering qualifications")

### 11.5 Implemented task contracts (`tasks.py`, `projects.py`)

- **Routes:** owner from the cookie session; callers cannot set owner, status or provenance; no model, connector or worker on task reads or commands; terminal tasks cannot be edited or reopened.
- **Idempotency:** create/command keys dedupe retries and reject changed payloads; replay returns current state. Task updates and events commit together under SQLite writer locks or PG owner advisory locks, with the revision predicate as final guard. `ActionStore` owner transactions also fence action claim/result writes, task commands and merchant receipts; adapter calls stay outside the claim transaction.
- **Source links:** `from-action` validates action ownership and creates or reopens one task per source; `from-report` prepares the fixed unconnected recovery capability and tracks it. Neither approves or dispatches. `task.source` is an immutable action ID; tracking changes never touch the source action.
- **Task focus in chat:** the client sends only task ID, revision and selection time; the server resolves ownership, rejects stale revisions, expires it after 30 minutes and passes task data via `AssistantContext`, outside checkpoints, with no authority.
- **Reviewed edits:** `task_help.task_edits` (bounded, allowlisted) → read-only `prepare-change` returns normalized before/after and rejects stale, terminal or ambiguous changes → Apply posts that exact change with revision + command key; Not now applies nothing; one attempt key survives an ambiguous response. Task dates stay in the task, never in global profile facts.
- **Projects:** `projects`, `project_tasks`, `project_chats`, `project_commands` share the owner transaction with creation keys, revision predicates and command hashes. Transcripts stay on the device. Only project ID/revision/time leave the client; the server resolves notes plus ≤ 20 task summaries; a late reply is suppressed if the revision changed. No project command executes actions.
- Verified on SQLite; PostgreSQL and device acceptance pending. Frozen `apps/web` client behaviour (Home feed, Today sheet, gestures) is documented by its code at the baseline tag.

## 12. Decisions and attention

- **Decision-card rule:** a Needs-you item shows what changed, the evidence with source and time, the consequence and the next action. If it cannot fill all four, it is not Needs-you. Unknown evidence cannot manufacture urgency. Needs you holds only crucial stops on tracked sources: approve a send, an unknown send outcome, a missed deadline. Ordinary tasks stay On your list.
- **Show exactly what is approved:** changed times/plan, account, recipient, content, attachments, shared fields or the host-owned fixed price.
- **Approvals bind to revisions:** to the task and action revisions plus the exact snapshot. A changed recipient, price, field set or date invalidates the old approval (409 → reload).
- **A local plan change is not an external send.** Accepting a plan edit never shares, buys, books or confirms anything externally.
- **One tap per side effect (rule 6 strict, founder 9 Nov):** no "Yes to all" or batch approval. Learn mode may offer a standing rule that the user confirms; it may re-rank or pre-select confirmed choices only, and never replaces the tap.
- **Required states:** edit, defer, approve, stale revision, permission revoked, failed read, unknown send outcome, superseded result, source unavailable.

### 12.1 FIN-08 contracts (implemented; every client reuses them)

| Surface | Endpoint(s) | Contract |
|---|---|---|
| Today / Needs you | `GET /api/today` | `needs_you.tasks[].decision` = `{kind: approve\|check\|deadline, title, detail, action_id, revision, snapshot_hash?, amount_aed?, earlier_target?}`. One lane per task (needs_you, running, scheduled, on_list, paused, completed); `counts` = needs_you, running, on_list, paused; `scheduled.tasks` carry `check_back_at`. Running work joins tracked tasks to canonical actions without dispatching; source status shows apart from task status |
| Decision card | `GET /api/actions/{id}`, `POST /api/actions/{id}/approve` (Idempotency-Key, `snapshot_hash`, `revision`), `POST /api/actions/{id}/cancel`, `POST /api/tasks/from-action` (Not now) | Context chip, amount, title, Will be shared / Never shared, note, Approve, Not now (keeps it), Discard. Approve sends the exact revision on screen; 409 means reload |
| Result card | client | Context, title, verdict first, `Updated hh:mm`, Keep on Today (`from-action` / `from-report`), Open. Pinning is device-local and never changes the source |
| Brief | `GET /api/today`, `GET/PUT /api/routines/brief` | "N moving · N need you", one line per item led by a chip. Deterministic, never model text |
| Task commands | `POST /api/tasks/{id}/commands` | edit, pause, resume, cancel, complete, `check_back` (`at` or null), `staged_next`, `collect`; always `expected_revision` + `command_key` |
| Messages | `GET /api/messages`, `/api/messages/stream` | Outbox only (consented, deduped, quiet hours). `task_checkback` carries `task_id`. No LLM decides timing |
| Follow-up mode | `GET/PUT /api/assist` | `ask \| auto \| learn`; `offer_auto` drives Learn's one-time offer. No mode sends, shares or pays |
| Lost item (TAXI-02) | task commands | Receipt-first quick replies; trip confirmed before the report; staged replies labelled at every step; collection only, delivery shown unavailable |

(from `docs/archive/references/ios-swift-plan.md` "Web contracts…(FIN-08)"; `docs/archive/implementation-plan.md` FIN-01..07)

### 12.2 Attention (ATTN-01)

- Reuse outbox consent, dedupe and Dubai quiet hours. A source watcher runs only inside an explicit responsibility or routine with cadence, scope, expiry and revocation.
- Model-generated candidate insights may be reviewed, but deterministic policy decides delivery. Inferred interests alone never start a proactive notification.
- **Bundle routine progress** into the task or an optional digest; **interrupt only for a permitted actionable change.** Define deferral, dismissal and expiry; suppress repeated unchanged updates.
- Reading is in-app by default; news push needs separately chosen topics and rules. Sponsorship stays apart from Today urgency, regulation updates and approval cards. A briefing item never takes a Needs-you slot or counts in "N things to do".
- **A quiet day is valid.** A briefing may be short or empty; no endless scroll or unread pressure. Measure false urgency and repeated interruptions.

(from `docs/archive/references/assistant-experience-plan.md` UX-01, UX-03, BRF-01, ATTN-01; `docs/archive/references/assistant-experience-review.md` RV-03; `docs/archive/references/personal-assistant-direction.md` §7; `docs/archive/references/assistant-review-decisions.md`)

## 13. Turn context and signals

Only the relevant subset of this bounded context enters a turn:

| Context | Contents |
|---|---|
| Current focus | Surface, resolved entity ID, selected card ID and selected fragment; the user can clear or change it |
| Active activity | Request, order, task or plan ID and revision; draft vs confirmed items |
| User situation | Confirmed preferences, party size, relevant dates, stated deadlines, accessibility needs, only when supplied |
| Temporal context | Dubai time, intended date, available time, duration assumptions, travel estimates with sources |
| Evidence | Provider/search responses with source, fetched time, validity and availability status |
| Available actions | Registered capabilities and their blockers |

- **Context never grants permission to execute.** Resolve IDs against server/provider data; check freshness and revision before applying any proposed change.
- **Selected text is untrusted quoted context:** selected fragments, snippets, articles, emails and pages are never instructions and never newly confirmed facts.
- **A browsing focus is never persisted** as a durable preference without user confirmation.
- **A click is a weak, temporary signal; a statement is a visible fact.** A statement or confirmation can become a "You told me" fact at once. Repeated choices may support an editable hypothesis with timestamps, confidence, evidence and expiry, never unlimited transcript accumulation.
- **Implemented:** `luna/schema.py:FocusContext` is bounded transient reference data in LangGraph runtime context, never stored. Whole-place selection works; fragments and server-validated entity/plan ownership are CTX-02. History: 24 checkpointed messages, 12 used by understanding. Forget deletes every checkpoint version for the owner. Chat history is device-local; restored history keeps typed metadata, never executable HTML.

(from `docs/archive/references/assistant-context.md`; `docs/archive/implementation-plan.md` CTX-01)

## 14. Connectors (Know)

- **Every connector declares its real capabilities.** Never promise one with no authorized, supported method.
- **Order (founder 9 Nov):** Gmail + Calendar first, with the founder as Google test user. This reverses "Google OAuth last" (`implementation-plan.md` §0.4) and "manual-first, OAuth-last" (review decision #8).
- **PC-01 manual input first:** a selected message, forwarded text or user-provided appointment becomes a task before any inbox access. The manual path keeps working without OAuth.
- **Gmail contract:** read-only (`gmail.readonly`), explicit scopes and consent, bounded mailbox selection, sender/thread/reference validation, bodies treated as untrusted data, dedupe of repeated events, and honest revoked/stale/unknown handling. **An email is not proof:** a received email is not authoritative evidence of ownership, collection or any status. Outbound contact is a separate approved capability.
- **Calendar:** not built yet. Calendar entries, like emails, are information, not commands granting authority.
- **WhatsApp = manual export only.** The user exports chats with WhatsApp's own Export chat; Dubai-io reads the files (text only; media memory is LATER). No linked device, Baileys, Evolution API or automation of a personal account. Exports carry contact names, not numbers, so merging one person across accounts is an "I noticed: same person?" confirmation.
- **Google Workspace data never feeds advertising.** Gmail/Calendar context used for planning is never eligible for sponsored targeting, and is never mixed into an ad profile to be filtered later.
- **Identity scopes are not an interest profile.** Google sign-in (`openid email profile`) grants neither Gmail/Calendar access nor Google's private ad-interest labels.
- **Outbound (later):** show destination, sender account, exact body and attachments; record provider evidence; a timeout is unresolved, never auto-resent. Contacting someone again is a separate approved effect; no autonomous outreach loops. A Gmail notification is a source event, not permission to act. Other channels (Slack etc.) map external IDs to a proven account and reuse the same task IDs and approvals.
- **Code today:** `/api/auth/google` + `/api/mail/needs-reply` (`oauth.py` grants identity + optional `gmail.readonly`, `mail_profile.py` `/api/mail/status` and `/api/mail/needs-reply` giving an honest blocker without OAuth or `DEMO_MAIL=1` `demo_fixture` cards) is the legacy Google identity/needs-reply pilot. Meanwhile `app/lab/parse.py` (WhatsApp `.txt`) and `app/lab/parse_email.py` (`.mbox`/`.eml`) are now built in `app/lab/` for local export ingestion. A Calendar connector exists in `app/connectors` (mock-tested only, never run against Google).
- **Universal connector framework (14 Nov, `app/connectors` via `/api/connectors/*`):** the universal source-record ingestion framework. It ingests authorized sources into `connector_records` (source id, provider timestamp, `provenance`, `as_of`, metadata). It never writes `mem_events` / `profile_facts`; sync is an explicit request, no new cron worker. Credentials are Fernet-encrypted per owner and connector; outbound sends default to deny until the owner approves the exact payload. Sources without an authorized API register as unavailable or file-import. Detail: `docs/connectors/README.md`.
- **Founder decision pending (WhatsApp Evolution plugin):** the framework includes `plugins/whatsapp_evolution.py` (unofficial Baileys via Evolution API). It is **off** unless `WHATSAPP_EVOLUTION_ENABLED` is set and it contradicts the manual-export-only rule above and §10, which lists Evolution API / Baileys as deliberately not built. Treat it as **not approved**: do not enable it, demo it or mention it as a feature until the founder lifts this line. Likewise the non-Gmail/Calendar sources (Slack, Telegram, Discord, Notion, etc.) are registered capabilities only; the 9 Nov build order stays Gmail + Calendar first.

(from `docs/archive/references/assistant-review-decisions.md` TAXI-02, #8; `docs/archive/references/assistant-context.md`; `docs/archive/references/personal-assistant-direction.md` PC-01, PC-04; `docs/references/recommender-plan.md`; `docs/Researches/CLAUDE.md` rules 5–6 and Quest §)

## 15. Recommendation and suggestion contracts (Notice)

Detail and scoring rationale: `docs/references/recommender-plan.md`.

- **Temporal recommender (REC-01..03B, `recommendations.py`, built):** reviewed app-owned topics; server-weighted, organic-only events; owner dedupe; one option/topic/visit contributes at most its strongest positive signal (save = 1.5) plus a bounded negative. **Session:** 30-min half-life, 24-h expiry. **Long-term:** 30-day half-life, 90-day inferred expiry (a floor under §R-ND, §7). **Two-visit qualification (`temporal-v3`):** inferred long-term influence needs ≥ 2 distinct options and visits ≥ 6 h apart; tabs opened together don't count; category taps are weak signals. Visits rotate after 30 min idle or 24 h. Explicit intent wins at once; negative feedback reduces influence; dismissal hides one item for seven days without a topic dislike. Only confirmation writes a `user_supplied` preference. Behavioural evidence never authorizes sharing, prefill, proactivity or status; fixture episodes never train. Corrections invalidate cached and in-flight reasons. Replay: `python -m app.recommendations`.
- **Trusted discovery (REC-03B):** `POST /api/discovery/places` takes reviewed category/subcategory, coordinates, radius, open-now and sort; fetches one provider batch; filters radius/open-now before ranking (unknown hours fail open-now). Listings are never saved. Budget, date and stock claims are unsupported; the generic rank endpoint authorizes no provider fact or action. Snapshots change only on explicit refresh, filter or navigation.
- **Pending:** REC-03C (host/provider-verified services and products; sandbox completions never train taste; pharmacy/medical activity never trains a health profile); REC-04 (measure p50/p95; scheduled cleanup, reconciled with §R-ND).
- **SUG-01 occasions:** only from user-given facts (birthday, school start, family visit, conference, departure, a saved date), stored with date, recurrence, time zone, provenance and consent, apart from inferred interests. Never infer a milestone or presume children. **Recipient taste stays separate:** a cake for a friend is not the user's preference and trains no recipient traits. Expired occasions stop surfacing. In-app suggestion and proactive notification are different permissions.
- **EVT-01 freshness before personalization:** query the explicit Dubai date window, verify identity, venue and date with the organizer, and drop past, cancelled or out-of-area events before scoring; a favourite artist never revives an expired event. News is not ticket inventory; no source means an honest empty state.
- **ADS-01 sponsorship:** labelled only: sponsor named, `Sponsored` label, "Why this ad", dismiss, organic choices still visible, never mixed into organic scores; no inventory means no ad; never Workspace data, sensitive traits or transcripts. **Today all signals are organic-only;** ad-eligible evidence needs separate consent.
- **CTX-02 ticket-availability guard:** comments, news and snippets are not live inventory. Without an inventory adapter, say availability is unverified and offer a sourced booking-page handoff.
- **Reading (Gate D, `reading.py`):** pull-only metadata. Only public topic labels go upstream; publisher/date/URL filters before display; bounded timeouts, 15-minute cache, per-owner rate bound. No polling, article bodies, generated articles or stored photos. Politics is opt-in. Rights: `docs/references/reading-source-register.md`.
- **Daily matched cards (lab, next):** confirmed interests + recent memory → candidates (news/RSS, GitHub, YouTube) → the ranker → a morning outbox slot → a card with a "Because…" chip and Save / Less like this. Confirming an item in the reveal is what unlocks its cards; an unconfirmed hypothesis never triggers one. See `docs/plan/morning-brief.md` (16 Nov design for the personalized Morning Brief news section, shared public `news_articles` / `news_query_cache` tables, and RRF + content-based reranking).

(from `docs/archive/implementation-plan.md` REC-01..04, CTX-02, SUG-01/01A, EVT-01/01A, ADS-01; `docs/archive/references/assistant-context.md`; `docs/Researches/CLAUDE.md` Quest § step 5)

## 16. Gates A–F (acceptance)

| Gate | Acceptance (condensed) | Code today |
|---|---|---|
| **A** Manual tasks + Today | Owner-scoped CRUD/pause/resume/cancel; idempotent writes; bounded events; zero LLM calls on task routes. Tasks start "Waiting for your update"; saving never starts monitoring or sends; completion is user-reported with provenance. Preview caps never hide overflow. Tests: owner isolation, stale edits, restart, duplicates, terminal states, rollback | Built; SQLite only |
| **B** Delayed check-back | Scheduler/outbox job (rule 8). Explicit time, Dubai zone, consent; persisted claims/expiry, retry limits, restart recovery, fencing; no LLM polling. Without a permitted fresh source it is a manual update request. Cancel/reschedule suppresses obsolete messages. Tests: double sweep, crash, in-flight cancel, quiet hours, owners. Hosting and budget before any always-on promise | FIN-05; live delivery unverified |
| **C** One service vertical | Existing action engine only; decision binds the exact snapshot and revision; evidence survives task cancellation; fixed price; honest sandbox; provider-only completion. Tests: ambiguous send, timeout, late evidence, duplicate dispatch | FIN-01; sandbox only |
| **D** Optional briefing | Not a dependency of A–C. Source register, rights, freshness, taxonomy and sensitive-content rules before adapters; pull-only cards with controls and links; honest outages; no news push, private email ingestion or sponsored urgency | `reading.py`; acceptance pending |
| **E** One connector = **Gmail** (+ Calendar) | **First, not last (founder 9 Nov).** Scope, revoke and isolation tests before use (§14). Tests: manual-input path, wrong recipient/account, ambiguous date, revoked permission, duplicate event, unknown send outcome. No pretending a mailbox is connected; no outbound messages from tests | `gmail.readonly` needs-reply; OAuth unconfigured; no Calendar |
| **F** One reviewed routine | Scheduler/outbox job (rule 8). Needs Gate B durability, explicit activation and expiry, bounded cost, cancellation; useful over repeated cycles; no silent activation or post-cancel action. Channels and browser automation stay later | FIN-07 morning brief |

(from `docs/archive/references/assistant-review-decisions.md` "Delivery gates"; `docs/archive/implementation-plan.md` "Next gates", FIN table; `docs/archive/references/assistant-experience-plan.md` §6; Gate E reordered by the founder 9 Nov)

## 17. Remaining architecture gaps

- Production auth and roles: Supabase Auth, FastAPI bearer verification, proof-based anonymous-owner transfer, separate merchant/operator roles, cross-device accounts. Local Supabase Auth/Storage/Edge does not mean identity, uploads or webhooks exist.
- Real provider adapters beyond the sandbox inbox; provider cancellation.
- Durable task worker: the DRAFT/WORKING/WAITING_EXTERNAL/BLOCKED states, leases and the `stale_worker` event (§11).
- Memory: the shared engine is temporal_note (`apps/memory`). The live temporal_note bridge and contract test mode exist; verify end-to-end wiring on the real-data stack in E0–E4. Current gaps: `docs/plan/Memory/memory.md` §18 and `apps/memory/upgrade/`. (WhatsApp export + `.mbox`/`.eml` parsers and the lab pipeline in `app/lab/` are legacy surfaces.)
- Semantic recall over `profile_facts.embedding` (column reserved, nothing writes it).
- Kill switch and a unified user-visible activity log (§9.1).
- Production multi-worker turn coordination remains a gap; single-tester checkpoint forgetting is implemented and tested. Memory decays over time and is erased only through user-triggered Forget.
- Contract codegen (`packages/contracts` → TypeScript for the clients) once a client consumes the API.
