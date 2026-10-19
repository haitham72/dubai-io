# Dubai-io — Build Architecture (contest MVP)

**Updated:** 13 Oct 2026 (step 00: current slice versus target architecture) · **Scope source:** `PLAN.md` (phases referenced as Phase 1–5) · Reference implementation of the UI: `demo/`
**Founder lock (10 Oct, final): bidding/quote ABSOLUTELY REJECTED. `quote.request`, `quote.read`, `QUOTED`, `QUOTE_ACCEPTED` do not exist. Every service opens as a modal HTML mini-app with fixed prices.**

This document defines the **target** contest architecture; its tables, modules and gates are requirements, not claims that they already exist. Current code: cyan ES-module lab in `apps/web/` and a Python 3.13 FastAPI/LangGraph slice in `apps/api/` (Luna, JSON told-fact memory, Places/Routes proxies). The lab now calls Luna on the API origin with a labelled router fallback. Local action/session persistence uses SQLite; browser conversation/report snapshots contain plain text and structured data. `apps/web`, `apps/widgets`, `packages/contracts`, Postgres, production account/role handling, SSE, transactional outbox and persistent profiler are not built. Google connection code is prepared but credentials are absent.

Long-term vision items (community, media vault, native sensors, indoor maps, ticket wallet) remain LATER. Historical fixtures/reference prompts do not override `PLAN.md` §2; its scope conflicts must be resolved before porting affected flows.

---

## 1. Shape

Target: one modular monolith (one Python API, one Vite + React + TypeScript PWA) plus a static widget origin and one Postgres database. Current lab hosting is documented in `README.md`.

```
┌──────────────────────── apps/web (Vite + React PWA) ────────────────────────┐
│  /            Companion chat · card renderer · widget host (iframe)    │
│  /merchant    Merchant inbox (accept / decline / mark ready / confirm) — fixed orders only, no quoting │
│  /ops         Provider onboarding review                               │
└───────────────┬───────────────────────────────▲────────────────────────┘
                │ REST (commands)               │ SSE (per-conversation, per-merchant streams)
┌───────────────▼───────────────────────────────┴────────────────────────┐
│                      apps/api (FastAPI, Python 3.13)                    │
│                                                                         │
│  chat ──► agent (LangGraph, read-only tools) ──► cards ──► messages     │
│                    │ proposes                                           │
│                    ▼                                                    │
│  actions (state machine, approvals, idempotency, audit) ◄── merchant    │
│                    │ emits                                              │
│                    ▼                                                    │
│  outbox ──► dispatcher ──► messages + SSE fan-out (LISTEN/NOTIFY)       │
│  scheduler (reminders) ──► outbox                                       │
│  registry (providers, capabilities, manifests)                          │
│  journey (arrival guide)  memory  evidence (uploads)  onboarding        │
└───────────────┬─────────────────────────────────────────────────────────┘
                ▼
     PostgreSQL 16 + pgvector  ·  object storage (local disk in dev, S3-compatible in prod)

apps/widgets  ── separate origin (e.g. widgets.<domain>), static HTML/JS only
```

**Core design decision:** the LLM agent can *read* and *propose*. It cannot *mutate*. Every side effect goes through the deterministic `actions` service, triggered by a user tap or a merchant tap on a REST endpoint. This one rule makes the truth-in-status principle hold by construction, and it keeps LangGraph simple: no interrupt/resume across HTTP requests.

---

## 2. Planned modules (`apps/api/app/`)

| Module | Owns | Must not |
|---|---|---|
| `auth` | Sessions, roles `user / merchant / operator`, demo login | Store real government IDs |
| `chat` | `conversations`, `messages`, SSE stream endpoint | Hold business state inside message text |
| `agent` | LangGraph graph, prompts, read-only tools, card composition | Call write paths; set any status |
| `cards` | Pydantic card union, validation, provenance enforcement | Accept a card that fails validation (drop it, log it, and send a plain-text fallback) |
| `registry` | `providers`, `capabilities`, widget manifests, fixtures, **`categories`** (data-driven category registry behind the Services surface; a new category is a row, not code) | Expose unapproved providers to search |
| `actions` | Request state machine, approvals, idempotency, `action_events` audit | Accept a transition that isn't in the table in §4 |
| `merchant` | Inbox queries and merchant commands (they go through `actions`) | Let a merchant see other merchants' requests |
| `outbox` | Transactional outbox, dispatcher, NOTIFY | Deliver one event twice (dedupe on `dedupe_key`) |
| `scheduler` | Reminder rows, quiet hours, firing into the outbox | Use the LLM to decide *when* to fire |
| `journey` | Arrival guide steps, landmark matching, map pins from user-confirmed places | Claim a position the user didn't confirm |
| `civic` (LATER) | Official-source retrieval with citations | Answer with no retrieved chunk |
| `evidence` | Photo/receipt uploads, EXIF stripping, signed URLs | Store files in the DB or vector index |
| `onboarding` | Menu-photo extraction into a draft provider for operator approval | Publish without operator approval |
| `memory` | `user_context` (area, language, mode, parking memories): facts the user told | Store anything the user can't see; hold inferences (those live in `profiler` as hypotheses) |
| `profiler` | Temporal profile (§12): `episodes`, `profile_facts`, `intents`, `routines`, `profile_snapshots`; hot-path digest, cold-path LangGraph | Use an unconfirmed hypothesis for sharing, pre-fill, proactive messages or status; infer sensitive traits; call write paths |

---

## 3. Planned shared contracts (`packages/contracts`)

Target: Pydantic v2 is the single source. Planned `make contracts` exports JSON Schema, generates `apps/web/src/contracts/*.ts`, and CI checks freshness. None of this tooling exists yet. The current Luna contract is `apps/api/app/luna/schema.py` plus the response metadata in `graph.py`; see `PLAN.md` §6.9.

### 3.1 Shared primitives

```python
Provenance = Literal["official", "provider_confirmed", "merchant_submitted",
                     "user_supplied", "inferred", "estimate", "demo_fixture"]
# "inferred" = a profiler hypothesis (§12); never valid on an approval card or a shared field

class Sourced(BaseModel):          # wraps any displayed fact
    value: str | float | int | date
    provenance: Provenance
    as_of: datetime | None = None  # required unless provenance == "user_supplied"
    source_url: HttpUrl | None = None

class Money(BaseModel):
    amount: Decimal
    currency: Literal["AED"] = "AED"
    kind: Literal["fixed", "from_estimate", "fixture"]  # NEVER "quote" — bidding rejected 10 Oct

class CardAction(BaseModel):
    id: str                        # MUST match a registry capability id or a ui.* local action
    label: str
    requires_approval: bool        # canonical name; `approval_required` is not accepted
    shares: list[str] = []         # fields disclosed to a third party, shown on the approval card
    # no free-form payload: the server rebuilds the payload from the card's own data
```

### 3.2 Card envelope and MVP union

Every card has `type`, `schema_version`, `card_id`, `title`, `as_of`, `actions: list[CardAction]`, `demo: bool`.

| `type` | Purpose | Phase |
|---|---|---|
| `text_note` | Plain fallback | 1 |
| `service_comparison` | Talabat-normal list, ≤3 providers sorted closest + ★ highest: name, `Money` (price-from, fixed), `distance_km` (`Sourced`), `rating` + `rating_count` (`Sourced` or omitted — never invented), `turnaround_sla` + `open_now` (`Sourced`), capability level. Every row's action opens that merchant's **modal HTML mini-app** | 3 |
| `action_approval` | What will be sent, to whom, which fields, and the fixed total if any | 3 |
| `action_status` | Request id, current status, last authoritative event, `provider_reference` | 3 |
| `html_widget` | `manifest_id`, `manifest_version`, `bridge_scopes`, `fallback_card` (inline `service_comparison`) | 3 |
| `journey_step` | Step title/body, zone, map ref + pin (user-confirmed), Next / I'm lost | 2 |
| `ride_options` | Taxi/Metro/app with estimate labels; handoff actions only | 2 |
| `memory_saved` | Key, value, `user_supplied` | 2 |
| `evidence_bundle` | Request or trip ref, attached photos/receipts, timeline | 4 |
| `recovery_checklist` | Lost-item steps built from saved memory, official contact handoff (never "filed") | 4 |
| `reminder` | What, when, why (`trigger_source`), snooze/dismiss | 2 |
| `provider_draft` | Onboarding: extracted items with per-field provenance → generated mini-app preview | 4 |

**Out of the MVP union:** `vehicle_status`, `ticket_wallet`, `indoor_route_step`, `delivery_window`, `trip_checklist`, `community_summary`, anything with bidding/quote fields. Add one only when `PLAN.md` moves it into scope.

### 3.3 Agent tools (read-only)

`registry.search(category, area, deadline)`, `registry.get_provider(id)`, `requests.get(user, id)`, `memory.get(keys)`, `parking.latest()`.
"Propose" tools create pending rows but no external effect: `actions.propose_order_request(provider_id, inputs)` returns an `action_approval` card with the fixed total, and `scheduler.propose_reminder(...)` returns a `reminder` card that needs confirmation. `propose_quote_request` does not exist — bidding rejected.

---

## 4. Request state machine (single source of truth)

Fixed-order lifecycle (Talabat-normal). No bidding, no second approval. Merchant either accepts or declines the order at their published price.

```
DRAFT ─► AWAITING_APPROVAL ─(user approves send)─► SUBMITTED
SUBMITTED ─(merchant accepts)─► ACCEPTED ─(merchant marks ready)─► READY ─(merchant marks done | user reports done)─► COMPLETED
SUBMITTED | ACCEPTED | READY ─(merchant)─► DECLINED
any non-terminal ─(user)─► CANCELLED
any non-terminal ─(ttl)─► EXPIRED
SUBMITTED ─(no ack within N min)─► stays SUBMITTED; UI shows "Waiting for merchant" (no invented status)
adapter error with unknown outcome ─► UNKNOWN_STATUS
```

- Terminal: `COMPLETED, DECLINED, CANCELLED, EXPIRED, FAILED`.
- Each transition is a row in `action_events` (actor, from, to, source, payload hash, at). The `service_requests.status` column is derived from it and updated in the same transaction.
- Each transition writes one outbox row → `action_status` message in the user's conversation and an inbox update for the merchant.
- **Idempotency:** `POST /actions/{id}/approve` and every merchant command take an `Idempotency-Key`. A replay returns the original result.
- Legacy `OPTIONS_READY` and `QUOTED`/`QUOTE_ACCEPTED` are dropped. Price is fixed at submit time from the merchant's published price list.
- Current lab `offers.js` emits `SLOT_CONFIRMED` in its simulated track; it is not a canonical lifecycle state above. Align slot confirmation as provider-event metadata/wording without inventing a new lifecycle state.

---

## 5. Planned data model (MVP tables)

`users`, `user_context`, `conversations`, `messages` (role, `card` JSONB, `client_msg_id` unique), `providers` (status `draft|approved|suspended`, `is_fixture`), `capabilities` (provider_id, capability_id, level `L1..L3`, input_schema), `widget_manifests`, `service_requests`, `action_events`, `approvals`, `outbox` (dedupe_key unique, available_at, delivered_at), `reminders`, `parking_memories`, `evidence_assets`, `knowledge_sources` (issuer, url, version_date, jurisdiction, license_note), `knowledge_chunks` (embedding vector, section_ref), `audit_log`, `categories`, and the profiler tables `episodes`, `profile_facts`, `intents`, `routines`, `profile_snapshots` (§12).

The system of record is **these tables**, not the LangGraph checkpointer. On each turn the agent rebuilds context from `messages` + `user_context` + open `service_requests`. A browser reload replays `messages`, and pending approvals come back automatically because they are cards whose actions still match a request in `AWAITING_APPROVAL` (single approval — there is no second quote approval).

---

## 6. Target widget host (the "WeChat inner-HTML" part)

The render order is: Talabat-normal card first, modal HTML widget second, fallback always available.

1. The agent emits `service_comparison` (closest + ★ + price-from + turnaround). Every row offers `Open` → that provider's **modal** HTML mini-app (services / shops / stores / rides — same pattern for all four).
2. The host loads `https://widgets.<domain>/<provider>/<version>/index.html` in `<iframe sandbox="allow-scripts">`. **Never add `allow-same-origin`**: together with `allow-scripts` on a same-site origin, it lets the frame strip its own sandbox. The widget origin is a separate site.
3. Widget CSP: `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'`. The widget cannot call the API.
4. Bridge: allowlist the widget URL/origin before loading. With `sandbox="allow-scripts"`, the child has an opaque origin (`event.origin` is `"null"`); comparing it with the widget URL origin is not a valid authentication check. The host must verify `event.source === activeFrame.contentWindow`, protocol, per-frame session token and payload schema. The child checks the configured host origin/source; replies to the opaque child require `targetOrigin: "*"` on that exact window. Business scope is `order.request` ONLY; `app.ready` / `host.context` / `host.error` are control messages, not extra business capabilities. The **host** rebuilds items and totals from its approved catalog and creates an approval card. The widget never submits anything.
5. If the manifest is missing or unapproved, the iframe fails to load within 3 s, or the client is offline, render `fallback_card`.

Widgets are app-owned templates for approved providers (laundry first). Merchant-authored HTML remains out of scope. The lab uses fetched HTML in sandboxed `srcdoc`; separate-origin hosting, full payload validation and host-owned prices for every template are unfinished gates. Legacy reference scopes such as sign-in, join, purchase-report and policy selection need the `PLAN.md` §2 scope decision before implementation.

---

## 7. Planned proactive pipeline (the "Jarvis" part, honest version)

```
trigger source ──► reminders / demo trigger API ──► outbox(dedupe_key, available_at)
   ▲                                                    │ dispatcher (poll 1s, FOR UPDATE SKIP LOCKED)
   │                                                    ▼
user-confirmed plan, state transition,     consent? quiet hours? still relevant? ──no──► drop + audit
or POST /demo/triggers (operator-only,                  │ yes
labelled "Demo trigger")                                ▼
                                          compose card (template; LLM wording optional)
                                                        ▼
                                          INSERT message + NOTIFY ──► SSE ──► chat
```

- MVP trigger sources: (a) user-confirmed reminders ("remind me when my parents land Friday 14:15"), (b) request state changes (merchant accepted / ready), (c) the operator demo-trigger endpoint, used to stand in for a geofence on stage. Its cards always carry `trigger_source: "demo"`, and the UI shows it.
- Parking: the trigger only *prompts*. The memory is saved from the user's photo plus their typed level/pillar. OCR may pre-fill the fields, and the user must confirm them. Recall is a plain read.
- Gate test: fire the same trigger twice and exactly one message appears. Reload and the message persists.

---

## 8. Civic RAG (LATER, not in the contest build)

- Corpus: an operator-curated list in `knowledge_sources`. Each row needs issuer, URL, version date, jurisdiction and a reuse note. Ingest from saved copies (PDF/HTML) with section/article anchors.
- Retrieval: hybrid search (Postgres FTS + pgvector), top-k chunks, then the answer is generated **only** from those chunks.
- Citation check (deterministic, after generation): every `citation.quote` must appear as a substring of a retrieved chunk, and every article label must exist in that chunk's metadata. If either check fails, the system abstains with "I couldn't find this in the official sources I have" plus the official channel link.
- Output: a `citation_answer` with a "general information, not legal advice" line, then a `complaint_draft` that the user edits. The action is `Open official channel` (a URL handoff), never "file".
- Arabic and English: store the source language; the answer follows the user's language. Citations stay in the source language with a translation note.

---

## 9. Frontend

- Tabs (13 Oct): **io · Maps · Services · Me**. `io` is Home (card stage + composer); `Maps` is the full-screen map with floating glass menus and a results sheet; `Services` uses the `01-home.png` hero/card layout above grouped service categories, with competing offers one level down (`PLAN.md` §7.5); `Me` holds the profile. Civic is not in the nav (LATER). Community is not in the nav.
- Card renderer: a `switch` on `card.type` over a component registry. Unknown types fall back to `text_note`. Validation is generated from the contracts.
- Visual system (founder decision 9 Oct, replaces Editorial Luxury gold): **iOS light mode with a cyan tint**. System font (SF Pro / -apple-system), grouped background `#F2F2F7`, white cards radius 16px, separators `#E5E5EA`, tint `#0A9CC2`, iMessage-style bubbles (bot `#E9E9EB`, user = tint). Merchant mini-apps keep their own branding. Legacy tokens: `demo/styles.css`; current cyan lab: `apps/web/stage.css`, `stage-v3.css`, `data.js`. Required pills: `Demo data`, `Sandbox`, `User-supplied`, `Estimate`, `Demo trigger`, `Official source`.
- RTL readiness: use logical CSS properties (`margin-inline-start`) from day one. Full Arabic RTL UI remains LATER in `PLAN.md` §2.

---

## 10. Planned security and privacy gates (MVP level)

- Required: roles enforced in API dependencies and a merchant-isolation test. Neither exists in the current slice; its `user_id` and `thread_id` are caller-supplied. Treat it as a local demo until isolation is implemented.
- Uploads: size/type limits, EXIF GPS stripped, served by short-lived signed URL, scoped to the owner.
- Approval cards list the exact fields shared (`CardAction.shares`). The merchant receives only those fields.
- Secrets live in env; `.env` is never committed. Prompts never contain user secrets.
- Logs carry a trace id per turn, plus tool name, latency, token cost and status. PII is redacted.

---

## 11. Deliberately not built

Native geofencing/motion, background location, indoor maps, ticket wallet, payments/escrow, government APIs or write actions, community/social, media vault, peer messaging, merchant-authored widgets, merchant webhooks (the inbox is the integration), Redis, PostGIS, microservices.

---

## 12. Planned temporal profiler (founder priority, 13 Oct)

Step P is not built. The lab’s `profile.js` replays synthetic `data.js` episodes; Luna’s JSON store contains model-extracted told facts. Neither is the persistent profiler below.

Target: the profile learns from what the user does over time, and stays honest by keeping every inference **visible**. It is event-sourced and bi-temporal: the Graphiti model (valid time + transaction time, invalidate rather than delete) implemented in Postgres + pgvector, with no graph database.

### 12.1 Honesty tiers

| Use | Confirmed / told (`user_supplied`) | Hypothesis (`inferred`, unconfirmed) |
|---|---|---|
| Re-rank or highlight options | ✓ | ✓ with a visible "Because…" chip |
| Pre-select / pre-fill a field | ✓ | ✗ (may suggest, never select) |
| Approval card / shared with a merchant | ✓ only via the approval card | ✗ |
| Proactive message / reminder | ✓ with consent, via the scheduler | ✗ (only *asked about* in context) |
| Set any status | ✗ | ✗ |

- **Surfacing:** an in-context "I noticed…" chip appears only at confidence ≥ 0.7 with ≥ 2 independent pieces of evidence. Every hypothesis is always listed in the profile view.
- **"Not true"** is stored as a negative fact (not re-raised for 90 days). **"Forget"** purges the fact and unlinks its evidence.
- **Never inferred** (UAE PDPL sensitive data): health, religion, ethnicity, nationality-as-trait, gender, sexuality, politics. These are stored only when told.

### 12.2 Tables

| Table | Purpose | Key columns |
|---|---|---|
| `episodes` | Append-only observations: message, tap, option viewed, choice, approval, merchant event, shared video, booking, rating, dismissal, consented location | `kind`, `payload`, `occurred_at` (valid), `recorded_at` (txn), `source_ref`, `dedupe_key` unique, `embedding` |
| `profile_facts` | Bi-temporal facts and hypotheses | `facet`, `predicate`, `value`, `condition`, `provenance`, `status` (`hypothesis\|confirmed\|rejected\|forgotten`), `alpha`, `beta`, `half_life`, `evidence[]`, `valid_from`, `valid_to`, `recorded_at`, `superseded_at`, `superseded_by` |
| `intents` | Goal state machine `latent → expressed → active → fulfilled \| abandoned \| dormant` | `domain`, `constraints` (budget, deadline, prefs), `horizon`, `linked_requests[]` |
| `routines` | Periodic patterns | `period`, `jitter`, `next_expected_at`, `n_obs`, `confidence` |
| `profile_snapshots` | As-of digest per turn (hot path, timeline replay) | `as_of`, `digest` |

Facets v1:
- identity/context (mode, areas, languages, household, vehicles)
- situation (short-lived)
- preferences **per domain** (price sensitivity, speed-vs-price policy, min ★, distance tolerance, provider affinity, styles/sizes)
- decision style
- routines
- provider relations
- active intents

### 12.3 Temporal math (deterministic)

- **Confidence** = α / (α + β). α and β decay toward the prior with the facet's half-life: situation 1–3 d · intent until horizon + grace · preference 90 d · identity 365 d.
- **Evidence weights:** told 3 · choice 2 · view/dwell 0.5 · dismissal 1 added to β.
- **Contradiction** closes the old row (`valid_to`, `superseded_by`) and opens a new one. Confirmed beats hypothesis; within a tier, recency wins.
- **Conditional facts** carry a `condition`, e.g. `{deadline_slack_days: {lt: 7}}`, as in "minimise price subject to deadline".
- **As-of reads:** `profile_at(user, valid_t, known_t)`.
- **Routines:** ≥ 3 inter-arrival samples give period ± jitter.
- **One shared vector file** (`packages/contracts/profile-vectors.json`; `apps/web/fixtures/` until scaffolded) tests the Python and JS implementations.

### 12.4 Graph (`apps/api/app/profiler/`)

- **Hot path** (≤ 300 ms, no LLM): `load_profile` → facets relevant to the detected domain (rules + pgvector) → a digest for Luna / case agents. Every item carries its tier, so consumers enforce 12.1.
- **Cold path** (background, outbox-driven, idempotent on `dedupe_key`), in order:
  1. `ingest`
  2. `extract`: LLM, Pydantic structured output; temporal expressions normalised to dates
  3. `resolve`: SQL + pgvector; rules first, LLM only for ties
  4. `temporal_update`
  5. `intent_tracker`
  6. `routine_miner`
  7. `surface_hypotheses`
  8. `snapshot`
- **Nightly `consolidate`:** dedupe, apply decay, summarise old episodes.
- **Rebuildable:** `rebuild_profile(user)` replays episodes, with extraction cached by episode hash, so a rebuild equals the incremental result.
- The profiler only reads and proposes. Reminders go through `scheduler.propose_reminder`.
- Config: `LLM_MODEL`, `PROFILER_MODEL`.

### 12.5 Evaluation (gate before any other backend feature)

- **Golden timelines** (synthetic multi-week users) with as-of checkpoint assertions.
- **Metrics:** fact precision/recall, temporal accuracy, contradiction closure, decay, intent accuracy, routine lead time, ranking lift (NDCG with vs. without the profile), hot-path p95.
- **Tier-leak test:** no hypothesis ever reaches an approval, a pre-fill or a proactive send.
- **Property tests:** monotonic decay; confirmed dominance; idempotent ingestion; rebuild == incremental.
- **LLM-judge** on held-out extraction cases.

## 13. Host pages and Google connection

Host-owned pages use page-host.js. Provider cards are native full-card Open buttons; website/marketplace rows route to service-workflow.js. Merchant iframes retain their own sandbox and order-only bridge. A host page is UI, not execution evidence; arbitrary website embedding is not promised.

GoogleOAuth in oauth.py implements a configured server flow: session-bound one-time state, PKCE, exact owned callback/origin, server code exchange and verified Google userinfo. Grants are encrypted with Fernet and owned by the private local session. OAuth tokens never enter cards, URLs, callback HTML or localStorage. Backend access_token checks granted scopes and serializes refresh; disconnect revokes and deletes the grant. Callback postMessage is a refresh signal only. Missing credentials leave Connect disabled.

Configuration: GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI; optional OAUTH_TOKEN_KEY. The lab creates an ignored local oauth.key when configured if no key is supplied. Deployment must provide a managed key and proper production sessions/roles. Identity scopes are openid/email/profile; additional provider capabilities need explicit incremental scopes, not inferred permission. This connects Google to the current browser session; cross-device account merging/login is not implemented. [Google server flow](https://developers.google.com/identity/protocols/oauth2/web-server), [Google token practices](https://developers.google.com/identity/protocols/oauth2/resources/best-practices), [Fernet](https://cryptography.io/en/latest/fernet/).

## 14. Shared local action engine

Implemented in actions.py, with SQLite lab tables for sessions, actions, preparation keys and approval results. Capabilities declare allowed/required user-supplied fields, recipient, effect, optional server-published total and an adapter. Seven service categories plus taxi recovery are registered for preparation; every runtime adapter is absent. This is local infrastructure, not completed production/provider integration.

prepare validates the capability/fields, preserves missing facts, deduplicates retries and saves DRAFT, BLOCKED or AWAITING_APPROVAL. approve binds snapshot hash and revision plus current recipient/effect/published cost. It persists DISPATCHING before the adapter call, prevents duplicate/concurrent dispatch and accepts SUBMITTED only on registered provider evidence. Exceptions/unverified responses/interrupted dispatch become UNKNOWN_STATUS and cannot automatically resend. Discard only affects unsent drafts; dispatched cancellation needs a provider-specific capability. Timestamped events and drafts survive restart.

The frontend reviews exact fields/effect, preserves per-provider edits, exposes saved requests and does not offer Send for unconnected capabilities. Taxi's rejected static official-guidance page is removed. Manual copying is secondary only. Nothing has been filed or ordered through a live adapter.

Luna calls remain understanding-only. The cookie session owner scopes its thread and stated-fact API; legacy caller-supplied IDs/routes remain local-demo compatibility, not production authorization. User-given facts can be viewed, edited or forgotten. Conversation snapshots save plain text and structured report data, never raw HTML or OAuth credentials; server transcript replay and full checkpoint forgetting are still planned.

Remaining gates: production Postgres/roles, approved catalog/bridge integration, live adapters with evidence parsing/reconciliation, cross-device auth, actual provider cancellation, SSE/outbox, persistent profiler and device review. The existing government execution restriction remains; a narrow validated RTA capability is required before enabling submission.
