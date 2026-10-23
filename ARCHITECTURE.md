# Dubai-io — Architecture

**Updated:** 22 Oct 2026 · Scope: `PLAN.md` · Status: `handoff.md`
**Lock:** no bidding/quote. `quote.request`, `QUOTED`, `QUOTE_ACCEPTED` do not exist.

**Core rule:** the LLM reads and proposes; it never mutates. Every side effect goes through the deterministic action engine after a user tap (approval) or a merchant tap (inbox). Truth in status holds by construction.

**22 Oct product direction:** everyday life/work in Dubai supersedes the visitor-first persona. Persistent responsibilities, Today/decisions, routines and connected communications are proposed in `docs/references/personal-assistant-direction.md`; they are not implemented architecture. The existing components below remain foundations. No runtime or native migration was performed for the product-research task.

## 1. Shape

```
apps/web (HTML/CSS/ES modules, served by apps/api at :8000)
  /               chat · cards · Services · Maps · Me · guide · recovery
  /merchant.html  sandbox merchant inbox + operator Demo triggers
        │ REST commands                      ▲ SSE (order, messages, merchant inbox)
apps/api (FastAPI, Python 3.13)
  luna/       LangGraph: normalize → understand → validate → [research] → remember
  actions     capabilities, approvals, idempotency, evidence gate, state machine
  merchant    merchant role, inbox commands (through actions)
  proactive   outbox: dedupe_key, consent, quiet hours, reminders, Demo triggers
  profile / user_profile   episodes + hypotheses overrides · profile document + bi-temporal facts
  catalog     host-owned fixed prices for partner mini-apps
  google_maps Places (discovery) · Routes (estimates)
  widgets     separate origin :8001 for mini-apps (CSP connect-src 'none')
        ▼
Supabase PostgreSQL 17 + pgvector (DATABASE_URL, DATABASE_SCHEMA=dubaiio; dedicated local stack) — SQLite fallback for tests/offline (app/db.py)
```

## 2. Contracts

```python
Provenance = Literal["official", "provider_confirmed", "merchant_submitted", "user_supplied", "inferred", "estimate", "demo_fixture"]
# every displayed number carries provenance + as_of; "inferred" is never valid on an approval card or a shared field
Money.kind: Literal["fixed", "from_estimate", "fixture"]   # never "quote"
CardAction: id (registered capability or ui.* only), label, requires_approval, shares[]   # no free-form payload
```

- **Luna output** (`apps/api/app/luna/schema.py`): `intent` ∈ lost_item · airport_guide · service_offers · places_near · order_status · info_question · market_quote · greeting · smalltalk · unclear; typed slots; `stated_facts` (allowlisted keys); a short `reply` with no URLs, prices or status words (enforced in `validate`). Research intents add `answer` + `sources[]`.
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

## 4. Data (Postgres)

`actions` (JSON record + provider), `sessions`, `preparations`, `approvals`, `merchant_sessions`, `merchant_commands`, `consent`, `outbox` (unique owner+dedupe_key), `episodes`, `profile_overrides`, `user_profile` (typed core + `attributes` JSONB), `profile_facts` (JSONB value/evidence, validity window, `embedding vector(1536)` reserved), OAuth grant tables, recommendation_events, profile_interests, recommendation_runs and LangGraph checkpoints. Supabase backend tables/checkpoints are in private schema dubaiio; browser roles have no access. SQL is written once (`?` placeholders); `app/db.py` translates for Postgres. Tests run on both (`TEST_DATABASE_URL`).

## 5. Widget host

1. Talabat-normal list first (closest + ★ + price-from + turnaround), then each row's modal mini-app, with a fallback when it fails to load within 3 s.
2. Mini-apps load from the widget origin (`WIDGET_PORT`, default 8001) in `<iframe sandbox="allow-scripts">`; never `allow-same-origin`.
3. Widget CSP: `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'`.
4. The host checks `event.source === frame.contentWindow`, version and kind; the provider app checks `event.source === parent`.

## 6. Proactive pipeline

Sources: (a) a reminder the user asked for, (b) order state changes (live over SSE), (c) operator Demo triggers (labelled). Each message: `dedupe_key` (once per user), consent, quiet hours 23:00–07:00 Dubai (deferred, not dropped), template wording, stored as a normal chat message. No LLM decides when to send. No background geofencing in the PWA.

## 7. Profile and memory

| Use | Told / confirmed (`user_supplied`) | Hypothesis (`inferred`) |
|---|---|---|
| Re-rank options | ✓ | ✓ with a visible "Because…" chip |
| Pre-fill a field | ✓ | ✗ |
| Approval card / shared with a merchant | ✓ via the approval card | ✗ |
| Proactive message | ✓ with consent | ✗ |
| Set any status | ✗ | ✗ |

- **Profile document** (`user_profile.py`): `user_profile` is a projection of current `profile_facts` (facets identity · context · situation · preference · like · dislike · routine). A newer statement closes the old fact (`valid_to`, `superseded_by`); Forget deletes the key's history. Only told or confirmed facts are stored here.
- **Hypotheses** (`profile.py` + `apps/web/profile.js`): real choices become episodes with allowlisted hypotheses and fixed weights (view 0.5 · dismissal 1 · choice 2); beliefs are Beta(α, β) with half-life decay; surfaced at ≥ 0.7 with ≥ 2 signals; Confirm writes a preference fact, Not true / Forget remove it and unlink evidence.
- **Never inferred:** health, religion, ethnicity, nationality-as-trait, gender, sexuality, politics (the hypothesis allowlist cannot express them).
- **Conversation memory:** LangGraph checkpoints in Postgres, scoped to the session owner and thread.

- **Temporal recommendation boundaries (22 Oct):** `recommendations.py` projects app-owned organic events with strongest-signal caps per option/visit. `temporal-v3` requires two distinct options and visits separated by six hours before inferred long-term influence; session/long-term signals decay independently. Category taps are weak signals, not distinct-option evidence. Confirmed preferences and paused controls remain separate; negative feedback reduces inferred influence.
- **Trusted discovery:** cookie-owned `POST /api/discovery/places` accepts reviewed category/subcategory, coordinates, radius, open-now and sort. It fetches one provider batch, checks supported constraints and ranks transient candidates. Provider listing payloads are not saved in recommendation runs. Unsupported budget/date/stock constraints are not verified by this contract; the generic rank endpoint cannot authorize provider facts or actions.
- **Display stability:** result snapshots change on explicit refresh/filter/navigation rather than each click; profile corrections/visit rotation invalidate saved and in-flight explanations. Single-item dismissal is owner-scoped for seven days and does not create a topic dislike. Current Supabase adoption/verification gate is in the detailed implementation plan.

## 8. Luna (LangGraph)

`normalize` → `understand` (OpenAI structured output; profile digest in context) → `validate` (allowlists, confidence gate, URL/phone/claim stripping) → conditional: `research` for `info_question` (Tavily, SerpAPI fallback; answer only from cited sources; civic questions refused) or `market_quote` (Finnhub, fixed template) → `remember` (stated facts; requests/incidents are not facts). Tool output is untrusted data. Order status is answered from the order record, never model text.

## 9. Security and privacy

Anonymous cookie sessions own their actions, profile and threads; merchants see only their provider's orders and the approved fields; operator triggers need a merchant session. Keys stay server-side. Snapshots in the browser hold plain text and structured data, never raw HTML or OAuth tokens. Google OAuth connector is implemented but unconfigured.

## 10. Deliberately not built

Payments/escrow, third-party purchasing, government write actions, background geofencing, indoor maps, ticket wallet, community, merchant-authored widgets, merchant webhooks, Redis, PostGIS, microservices. (Two items left this list by founder direction: community was built as the 23 Oct redesign; Redis/RabbitMQ/Celery were adopted the same day for the ML pipeline. The rest stands.)

## 11. Remaining architecture gaps

- Production auth and roles (token auth for native, operator role separate from merchant), cross-device accounts.
- Real provider adapters beyond the sandbox inbox; provider cancellation.
- Semantic recall over `profile_facts.embedding` (column reserved, nothing writes it).
- Production multi-worker coordination for turn/forget and scheduled retention cleanup; single-tester checkpoint forgetting is implemented and tested.
- Contract codegen (`packages/contracts` → TS/Swift) when a second client starts.

## 12. Native client boundary (21 Oct)

`apps/ios` is a SwiftUI client, not a web-app wrapper. Initial native discovery/chat uses the existing cookie session over URLSession; production Supabase Auth/roles and anonymous-owner migration are a separate gate. Models and transport live in a small Swift package; UI state is owned by focused main-actor observable models. Backend LLM/provider keys remain server-side.

Third-party browsing uses a Safari sheet and preserves chat/focus on return. Authentication requires a dedicated authentication session and compatible backend callbacks. General websites never receive the mini-app action bridge. Native Google Places results remain on a Google-provided map; a separate illustrative MapKit 3D preview contains no Google Places pins. Native approvals/status updates must use the existing server engine when that slice is implemented. See `docs/references/ios-swift-plan.md`.

## 13. Implemented temporal recommender and context checkpoint

recommendations.py owns reviewed topics, server-weighted organic-only events, owner dedupe and aggregate per-option/visit strongest-signal caps, session (30-minute half-life / 24-hour expiry) and long-term (30-day half-life / 90-day expiry) projections, stable ranking runs and visible controls. Current candidate ranking accepts bounded caller IDs/topics: trusted provider eligibility, wider surfaces and variety remain REC-03. Behavioral evidence never authorizes sharing, prefill, proactivity or status. Confirmation alone writes a canonical user_supplied preference. Legacy six hypotheses coexist; fixture episodes are never training data.

FocusContext is bounded transient selected UI reference data, passed through LangGraph runtime context rather than storing the focus object. Whole-place chat selection is implemented; fragments, server-validated entity/plan ownership and revisioned itineraries remain planned. Recent checkpointed history is bounded to 24 messages, with 12 used by understanding. Forget deletes all checkpoint versions for the owner under a single-process turn/forget lock; production coordination remains outstanding.

Authoritative execution order, gaps and acceptance gates are in PLAN.md and docs/implementation-plan.md. Google OAuth is explicitly last for the single tester. Supabase Auth/Storage/Edge services being available locally does not mean app identity, file upload or webhook integrations exist.

REC-02 adds explicit reviewed-topic Edit, atomic canonical-fact/control updates, capped deterministic event replay and owner-serialized ranking snapshots. Interest reads expose bounded recent evidence and separate session/long-term expiry without retaining listing snapshots. Browser mutation pauses invalidate applied/cached/in-flight reasons; stale responses cannot restore a corrected interest. Existing local projections were reconciled to temporal-v2. Next task is REC-03; complete eligibility across provider surfaces is still pending.

## 11. Gate A manual tasks ? 22 Oct source addition

`tasks.py`: backend-owned `tasks` and `task_events`; no unused Decision/Job/Artifact tables. `POST/GET /api/tasks`, `GET /api/tasks/{id}`, revision-bound `POST /api/tasks/{id}/commands`, bounded activity pagination and `GET /api/today`. Cookie owner comes from the existing store; callers cannot set owner/status/provenance. Manual state: WAITING_USER ? PAUSED; either may be explicitly CANCELLED or COMPLETED with a user-supplied result. Terminal tasks cannot be edited/reopened. No model, connector or worker participates; user-reported completion is not provider evidence.

Create and command keys dedupe retries and reject changed payloads. Replay returns current state rather than restoring an older response. Task updates/events commit together; SQLite writer locks or PG owner advisory locks protect competing handles, with a revision predicate as final guard. Reads are bounded; event history pages are owner scoped. These local guards do not establish scheduling or external dispatch safety; Gates B/C still need durable claims/recovery and action snapshot binding.

`tasks.js`/`tasks.css`: Today is a page-host sheet above preserved visual Home/onboarding, with a handle-only gesture plus tap/keyboard alternatives. `/api/today` returns owner-scoped uncapped totals, due-ordered manual preview, dynamic urgency flags and paused/completed projections. No real Decision/worker is present, so Needs you/Running stay empty/hidden. Task detail uses a mounted polite announcement region and focused state chip after commands; refresh retains cached Today. Versioned migration `20261022000100_tasks.sql` enables RLS/revokes browser-role access in the private schema; live Supabase application/access tests are pending. Full SQLite: 145 passed, 11 skipped (17 task checks). Browser checks cover both requested phone sizes, normal/reduced motion, keyboard and computed no-shadow behavior; physical iPhone/screen-reader and PG remain unverified. `status-labels.js` maps component codes to plain text while `data-status` retains codes. Keep-track bridge, taxi replies, Reading, workers and Gmail are outside this correction; see PLAN.md.

### 11.1 Additive source links and task discussion

The subsequent finish-the-app authorization lifts the bounded correction's feature holds without a redesign. `POST /api/tasks/from-action` validates canonical action ownership and creates/reopens one task per source using a reserved creation key under the owner write transaction. `POST /api/tasks/from-report` idempotently prepares the fixed unconnected recovery capability and tracks it; neither route approves or dispatches. `task.source` is an immutable action ID reference inside existing task JSON, so no new schema is required. Detail resolves current source data; missing sources leave task/history accessible. Tracking cancellation/completion does not mutate the source action.

Client `task_focus` contains only task ID/revision/selection time. The API resolves ownership, rejects stale revisions and expires references after 30 minutes. Canonical task/source reference data is supplied through `AssistantContext`, outside checkpoint state; normal user/assistant conversation text remains ordinary conversation history. It is never authority to change a task, execute an action, or create a confirmed profile fact. `task_help` extends the existing intent allowlist; all previous intents/handlers remain. Chat renders task status from the canonical route and preserves a task link across reload. Reviewed chat edit proposals and actual Decisions are still the next steps. Full SQLite suite at this checkpoint: 150 passed/11 skipped; PG and physical-device acceptance remain separate.

### 11.2 Reviewed task edits from chat

`task_help.task_edits` is a bounded allowlisted suggestion list, never executable instructions. The app posts a suggested `TaskChanges` plus expected revision to `POST /api/tasks/{id}/prepare-change`. The owner-scoped read-only route rejects stale/terminal tasks and unsupported/ambiguous fields, returning normalized before/after values. Apply posts that exact normalized change through the existing revision/idempotency command contract; Not now applies nothing. The review retains one attempt key after an ambiguous response; it never guesses whether to repeat a different operation. Task editing never alters linked Action data. No new table is needed for this local-task review contract.

Task-focused conversation does not automatically add global profile facts: task constraints/dates belong to the task revision. Runtime context stays outside checkpoint state; ordinary conversation text persists as before. Current verification: 154 SQLite passed/11 skipped, four phone-size/motion browser variants, one deliberately lost-response retry, and two synthetic live model checks (task proposal/original lost-item routing). Actual Decisions remain next; PG/device/hosting and full live golden coverage remain separate.


## 12. Home task feed, chat history and pull-only News (22 Oct)

The web client remains plain ES modules. `homeFeed` owns normal vertical scrolling: the preserved `homeHero` card area, inline owner-scoped Today/task history, then Reading after pagination is exhausted. A task-detail/review sheet remains distinct from this feed. Vertical touch is native browser panning; card dragging claims only horizontal gestures. Hidden Home has parent opacity zero as well as inertness so inline-visible WebGL card elements cannot show through chat or Services.

`/api/today.current_work` joins tracked, active owner tasks to canonical Actions without reconciliation/dispatch. Current source-backed work takes deck priority; otherwise up to five existing qualified recommendation starters are used. Current-source subscriptions reuse the Action status stream, bounded by the five cards, and debounce summary refresh. Source status is shown separately from the manual task status; provider completion never reports that the user completed a manual note.

Device-local chat storage keeps the existing session format and lazily adds archived conversations. New chat changes only thread identity; saved facts and drafts remain. History restoration retains typed source/task/proposal metadata, never saved executable HTML. Switching aborts in-flight model turns and detaches old source watchers. UI uses a standard native-dialog history sidebar and the existing user menu. This is not cloud-synced conversation storage. Project workspaces are implemented as described below.

Reading is a pull-only metadata adapter. Owner-scoped inspected interests select allowlisted public topics; only public query labels go upstream. HTTPS/publisher/date/URL/title filters precede display; publication dates are explicitly provider-reported. An eight-second provider timeout, 15-minute public-metadata process cache and per-owner rate bound prevent repeated scroll loads. Preferences are checked again after retrieval; client correction generations drop older results. Hide/Show and topic choice remain controls. Headline context in Ask is transient metadata, not a claim of full-article access or new confirmed memory. No polling, article generation, article bodies or publisher photos. Source/reuse and production gates: `docs/references/reading-source-register.md`.

ActionStore owner transactions now coordinate Action claim/result writes, task command fences and merchant receipts. Optional guard callbacks run within the claim transaction; adapter calls remain outside it. Receipts and source changes commit/roll back together. These guards are prerequisites for real Decisions/check-backs, which remain pending.


## 13. Project workspaces (22 Oct)

`projects`, `project_tasks`, `project_chats` and `project_commands` use the shared owner transaction boundary. Creation keys, revision predicates and command hashes make create/edit/link/archive commands replay-safe. Task membership validates canonical ownership; a chat reference is owner-scoped and cannot read another owner's transcript. Transcripts remain on the device. Unlink and archive preserve task/chat records. Commands retain metadata/hashes instead of old shared-note text. Runtime PostgreSQL RLS plus the versioned private-schema migration are source-delivered, with deployment tests still gated.

The standard sidebar opens Projects and its linked records. Empty project chats remain locally restorable. The selected workspace is visible in chat; known project turns wait for its ownership lookup; unscoped chat keeps its existing fallback. Only project ID/revision/time leave the client for the model endpoint. The server validates chat membership and resolves the current shared notes plus at most 20 task summaries. Stale references return a clarification without routing a new service intent; late replies are suppressed if the workspace revision changes during a model call. Model runtime data is transient; `remember` suppresses global profile writes for project/task-scoped turns. Research query expansion cannot copy private project notes. Ordinary chat messages can contain quoted notes, so edits affect future context and do not claim to erase existing conversations. These semantics were covered by owner/concurrency/rollback/replay/context tests, four browser variants and one synthetic live model check. No project command executes Actions.
