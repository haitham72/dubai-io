# Dubai-io — Build Architecture (contest MVP)

**Updated:** 10 Oct 2026 · **Scope source:** `PLAN.md` (phases referenced as Phase 1–5) · Reference implementation of the UI: `demo/`
**Founder lock (10 Oct, final): bidding/quote ABSOLUTELY REJECTED. `quote.request`, `quote.read`, `QUOTED`, `QUOTE_ACCEPTED` do not exist. Every service opens as a modal HTML mini-app with fixed prices.**

This document covers only what the contest build needs. Long-term vision items (community, media vault, native sensors, indoor maps, ticket wallet) are **not** built here.

---

## 1. Shape

One modular monolith (one Python API, one Next.js app) plus a static widget origin and one Postgres database.

```
┌──────────────────────── apps/web (Next.js PWA) ────────────────────────┐
│  /            Companion chat · card renderer · widget host (iframe)    │
│  /merchant    Merchant inbox (accept / decline / mark ready / confirm) — fixed orders only, no quoting │
│  /ops         Provider onboarding review                               │
└───────────────┬───────────────────────────────▲────────────────────────┘
                │ REST (commands)               │ SSE (per-conversation, per-merchant streams)
┌───────────────▼───────────────────────────────┴────────────────────────┐
│                      apps/api (FastAPI, Python 3.12)                    │
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

## 2. Modules (`apps/api/app/`)

| Module | Owns | Must not |
|---|---|---|
| `auth` | Sessions, roles `user / merchant / operator`, demo login | Store real government IDs |
| `chat` | `conversations`, `messages`, SSE stream endpoint | Hold business state inside message text |
| `agent` | LangGraph graph, prompts, read-only tools, card composition | Call write paths; set any status |
| `cards` | Pydantic card union, validation, provenance enforcement | Accept a card that fails validation (drop it, log it, and send a plain-text fallback) |
| `registry` | `providers`, `capabilities`, widget manifests, fixtures | Expose unapproved providers to search |
| `actions` | Request state machine, approvals, idempotency, `action_events` audit | Accept a transition that isn't in the table in §4 |
| `merchant` | Inbox queries and merchant commands (they go through `actions`) | Let a merchant see other merchants' requests |
| `outbox` | Transactional outbox, dispatcher, NOTIFY | Deliver one event twice (dedupe on `dedupe_key`) |
| `scheduler` | Reminder rows, quiet hours, firing into the outbox | Use the LLM to decide *when* to fire |
| `journey` | Arrival guide steps, landmark matching, map pins from user-confirmed places | Claim a position the user didn't confirm |
| `civic` (LATER) | Official-source retrieval with citations | Answer with no retrieved chunk |
| `evidence` | Photo/receipt uploads, EXIF stripping, signed URLs | Store files in the DB or vector index |
| `onboarding` | Menu-photo extraction into a draft provider for operator approval | Publish without operator approval |
| `memory` | `user_context` (area, language, mode, parking memories) | Infer facts. Everything here is user-supplied or confirmed |

---

## 3. Contracts (`packages/contracts`)

Pydantic v2 is the single source. `make contracts` exports JSON Schema, generates `apps/web/src/contracts/*.ts`, and a CI check fails if the generated files are stale.

### 3.1 Shared primitives

```python
Provenance = Literal["official", "provider_confirmed", "merchant_submitted",
                     "user_supplied", "estimate", "demo_fixture"]

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
- `OPTIONS_READY` and `QUOTED`/`QUOTE_ACCEPTED` from `04 §6` are dropped. Price is fixed at submit time from the merchant's published price list.

---

## 5. Data model (MVP tables)

`users`, `user_context`, `conversations`, `messages` (role, `card` JSONB, `client_msg_id` unique), `providers` (status `draft|approved|suspended`, `is_fixture`), `capabilities` (provider_id, capability_id, level `L1..L3`, input_schema), `widget_manifests`, `service_requests`, `action_events`, `approvals`, `outbox` (dedupe_key unique, available_at, delivered_at), `reminders`, `parking_memories`, `evidence_assets`, `knowledge_sources` (issuer, url, version_date, jurisdiction, license_note), `knowledge_chunks` (embedding vector, section_ref), `audit_log`.

The system of record is **these tables**, not the LangGraph checkpointer. On each turn the agent rebuilds context from `messages` + `user_context` + open `service_requests`. A browser reload replays `messages`, and pending approvals come back automatically because they are cards whose actions still match a request in `AWAITING_APPROVAL` (single approval — there is no second quote approval).

---

## 6. Widget host (the "WeChat inner-HTML" part)

The render order is: Talabat-normal card first, modal HTML widget second, fallback always available.

1. The agent emits `service_comparison` (closest + ★ + price-from + turnaround). Every row offers `Open` → that provider's **modal** HTML mini-app (services / shops / stores / rides — same pattern for all four).
2. The host loads `https://widgets.<domain>/<provider>/<version>/index.html` in `<iframe sandbox="allow-scripts">`. **Never add `allow-same-origin`**: together with `allow-scripts` on a same-site origin, it lets the frame strip its own sandbox. The widget origin is a separate site.
3. Widget CSP: `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'`. The widget cannot call the API.
4. Bridge: `postMessage` with a strict `origin` check on both sides. The host accepts only `{v:1, kind, payload}`, where `kind ∈ manifest.bridge_scopes` (MVP: `order.request` ONLY). `order.request` makes the **host** build an `action_approval` card with the fixed total. The widget never submits anything.
5. If the manifest is missing or unapproved, the iframe fails to load within 3 s, or the client is offline, render `fallback_card`.

For the MVP, Dubai-io writes the single widget (`laundry-order`). Merchant-authored HTML is out of scope.

---

## 7. Proactive pipeline (the "Jarvis" part, honest version)

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

- Tabs: **Companion · Services · Civic · Me**. `Services` is a browse view backed by the same registry search the agent uses. `Civic` contains only Guides for MVP. Other civic sub-tabs show `Pilot`. Community is not in the nav.
- Card renderer: a `switch` on `card.type` over a component registry. Unknown types fall back to `text_note`. Validation is generated from the contracts.
- Visual system (founder decision 9 Oct, replaces Editorial Luxury gold): **iOS light mode with a cyan tint**. System font (SF Pro / -apple-system), grouped background `#F2F2F7`, white cards radius 16px, separators `#E5E5EA`, tint `#0A9CC2`, iMessage-style bubbles (bot `#E9E9EB`, user = tint). Merchant mini-apps keep their own branding. Reference implementation: `demo/styles.css`. Required pills: `Demo data`, `Sandbox`, `User-supplied`, `Estimate`, `Demo trigger`, `Official source`.
- RTL readiness: use logical CSS properties (`margin-inline-start`) from day one. A full Arabic UI is a stretch goal.

---

## 10. Security and privacy (MVP level)

- Roles enforced in API dependencies. Merchants see only their own requests. There is a test for this.
- Uploads: size/type limits, EXIF GPS stripped, served by short-lived signed URL, scoped to the owner.
- Approval cards list the exact fields shared (`CardAction.shares`). The merchant receives only those fields.
- Secrets live in env; `.env` is never committed. Prompts never contain user secrets.
- Logs carry a trace id per turn, plus tool name, latency, token cost and status. PII is redacted.

---

## 11. Deliberately not built

Native geofencing/motion, background location, indoor maps, ticket wallet, payments/escrow, government APIs or write actions, community/social, media vault, peer messaging, merchant-authored widgets, merchant webhooks (the inbox is the integration), Redis, PostGIS, microservices.
