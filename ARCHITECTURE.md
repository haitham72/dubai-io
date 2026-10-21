# Dubai-io — Architecture

**Updated:** 21 Oct 2026 · Scope: `PLAN.md` · Status: `handoff.md`
**Lock:** no bidding/quote. `quote.request`, `QUOTED`, `QUOTE_ACCEPTED` do not exist.

**Core rule:** the LLM reads and proposes; it never mutates. Every side effect goes through the deterministic action engine after a user tap (approval) or a merchant tap (inbox). Truth in status holds by construction.

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

## 8. Luna (LangGraph)

`normalize` → `understand` (OpenAI structured output; profile digest in context) → `validate` (allowlists, confidence gate, URL/phone/claim stripping) → conditional: `research` for `info_question` (Tavily, SerpAPI fallback; answer only from cited sources; civic questions refused) or `market_quote` (Finnhub, fixed template) → `remember` (stated facts; requests/incidents are not facts). Tool output is untrusted data. Order status is answered from the order record, never model text.

## 9. Security and privacy

Anonymous cookie sessions own their actions, profile and threads; merchants see only their provider's orders and the approved fields; operator triggers need a merchant session. Keys stay server-side. Snapshots in the browser hold plain text and structured data, never raw HTML or OAuth tokens. Google OAuth connector is implemented but unconfigured.

## 10. Deliberately not built

Payments/escrow, third-party purchasing, government write actions, background geofencing, indoor maps, ticket wallet, community, merchant-authored widgets, merchant webhooks, Redis, PostGIS, microservices.

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

recommendations.py owns reviewed topics, server-weighted organic-only events, owner dedupe and per-kind/item caps, session (30-minute half-life / 24-hour expiry) and long-term (30-day half-life / 90-day expiry) projections, stable ranking runs and visible controls. Current candidate ranking accepts bounded caller IDs/topics: trusted provider eligibility, wider surfaces and variety remain REC-03. Behavioral evidence never authorizes sharing, prefill, proactivity or status. Confirmation alone writes a canonical user_supplied preference. Legacy six hypotheses coexist; fixture episodes are never training data.

FocusContext is bounded transient selected UI reference data, passed through LangGraph runtime context rather than storing the focus object. Whole-place chat selection is implemented; fragments, server-validated entity/plan ownership and revisioned itineraries remain planned. Recent checkpointed history is bounded to 24 messages, with 12 used by understanding. Forget deletes all checkpoint versions for the owner under a single-process turn/forget lock; production coordination remains outstanding.

Authoritative execution order, gaps and acceptance gates are in PLAN.md and docs/implementation-plan.md. Google OAuth is explicitly last for the single tester. Supabase Auth/Storage/Edge services being available locally does not mean app identity, file upload or webhook integrations exist.
