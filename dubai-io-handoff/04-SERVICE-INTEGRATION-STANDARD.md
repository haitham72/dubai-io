# Dubai-io — Service Integration Standard v0.1

**Objective:** Expand an AI city companion by onboarding services without creating a new end-user application for each category.  
**This is an internal proposal**, not a real standard supported by Dubai agencies or third parties.

## 1. Provider onboarding lifecycle

1. **Apply:** merchant provides trading details, supported categories, location, public information and contact methods.
2. **Verify:** authorized operator checks identity, business documentation, terms and ability to deliver the advertised service.
3. **Import:** CSV, form, OpenAPI spec or manually authored connector manifest.
4. **AI-assisted mapping:** transform allowed data to canonical schema; flag uncertain pricing, unsupported actions and missing fields.
5. **Sandbox test:** validate auth, schema, status transitions, rate limits, failure cases and data handling.
6. **Human approval:** sign off on publication and any execution-level capability.
7. **Publish:** versioned capabilities become discoverable through a single service registry.
8. **Monitor:** refresh freshness, audit actions, suspend failed providers, notify users when required.

**Important:** AI-generated adapters cannot auto-deploy directly to production. Merchant inputs are untrusted.

## 2. Five capability maturity levels

| Level | User benefit | Required proof |
|---|---|---|
| `L1_DISCOVER` | Search/find provider | Licensed or provider-submitted listing |
| `L2_CONTACT` | Contact/open official link | Valid contact/handoff endpoint |
| `L3_QUOTE` | Request price and terms | Quote request/merchant acknowledgement |
| `L4_EXECUTE` | Make confirmed reservation/order | Authenticated provider confirmation |
| `L5_FULFILL` | Track/cancel/refund/complete | Verified status events or partner webhook |

Levels cannot be inferred from marketing language. A “Book” button is not `L4` unless a confirmation mechanism exists.

## 3. CSV seed schema (discovery only)

```csv
provider_id,provider_name,category,service_slug,area,price_from_aed,price_source,discount_percent,offer_verified_until,action_mode,source_url,last_verified_at
DEMO-01,Example Laundry,laundry,shirt_ironing,Marina,15,merchant_submitted,0,,contact,,
DEMO-02,Example Cleaning,cleaning,apartment_cleaning,Downtown,80,merchant_submitted,0,,quote_request,,
```

These rows are **fictional fixtures**. Never present them as real suppliers.

For production use, normalize provider, service, location, offer, terms and action capability into separate related tables.

## 4. Provider capability manifest example

```yaml
schema_version: '0.1'
provider_id: 'DEMO-01'
provider_status: sandbox_only
category: laundry
service: shirt_ironing
locale: [en, ar]
operating_areas: [marina]
listing:
  title: Example Laundry — shirt ironing
  data_provenance: merchant_submitted
  last_verified_at: null
capabilities:
  - id: laundry.request_quote
    level: L3_QUOTE
    execution_mode: approved_adapter
    input_schema_ref: '#/schemas/QuoteRequest'
    output_schema_ref: '#/schemas/QuoteResponse'
    requires_user_approval: true
    shares_user_data: [contact_method, pickup_area, item_count]
    timeout_seconds: 10
    idempotent: true
  - id: laundry.contact
    level: L2_CONTACT
    execution_mode: merchant_url
pricing:
  is_estimate: true
  amount_from_aed: 15
  confirmed_discount_percent: null
security:
  allowed_hosts: [sandbox.example.invalid]
  api_credentials_ref: 'secrets://sandbox/example-laundry'
```

## 4b. Mini-app (inner-HTML widget) manifest — WeChat-style, AI-first

Provider HTML is optional and never required to join. Standard widgets render by default; HTML mini-apps are progressive enhancement.

```yaml
schema_version: '0.1'
provider_id: 'DEMO-01'
mini_app:
  entry: 'https://sandbox.example.invalid/mini/quote.html?v=3'
  manifest_version: 3
  sandbox: 'allow-scripts allow-same-origin'  # no allow-top-navigation; no raw eval bridges
  bridge_scopes: [quote.read, quote.request]  # capability-scoped postMessage only
  csp: "default-src 'none'; script-src 'self'; connect-src https://api.dubai-io.example"
  fallback_card: service_comparison  # rendered if HTML blocked / offline / unapproved
```

Rules:
- Host validates `manifest_version` + CSP + allowlisted bridge methods before mounting iframe.
- HTML posts intent (e.g. `{kind: request_quote}`); host executes via approved adapter after user approval. HTML never touches DB/tools/secrets.
- Every mini-app version is human-approved for L3+; L1/L2 HTML is display-only.
- Discovery scales as **many provider records, few capability contracts** — do not create 1 MCP server per shop; shared gateways aggregate (`search_services`, `get_provider`, `compare_offers`, `start_watch`).

## 5. Standardize request/response envelopes

```json
{
  "request_id": "req_001",
  "capability_id": "laundry.request_quote",
  "user_approval_id": "approval_123",
  "input": {"item_count": 5, "deadline_local": "2026-10-09T09:00:00+04:00"},
  "status": "SUBMITTED"
}
```

```json
{
  "request_id": "req_001",
  "provider_reference": "merchant_ref_123",
  "status": "PROVIDER_ACKNOWLEDGED",
  "quoted_total_aed": null,
  "currency": "AED",
  "last_updated_at": "2026-10-08T19:00:00+04:00"
}
```

These are **schema demonstrations only**. The second response is not a completed quote or confirmed booking.

## 6. Universal action status and audit requirements

`DRAFT`, `OPTIONS_READY`, `AWAITING_APPROVAL`, `SUBMITTED`, `PROVIDER_ACKNOWLEDGED`, `QUOTED`, `CONFIRMED`, `COMPLETED`, `CANCELLED`, `FAILED`, `EXPIRED`, `UNKNOWN_STATUS`.

Record: who requested, consent scope, provider, adapter version, input hash, external correlation ID, timestamps, result source and errors. Sensitive payloads require access controls/redaction. Retry only idempotent operations or operations with explicit duplicate detection.

## 7. Dynamic Action Card envelope

```json
{
  "type": "service_comparison",
  "schema_version": "1",
  "title": "Ironing options near Marina",
  "as_of": "2026-10-08T19:00:00+04:00",
  "items": [
    {
      "provider_id": "DEMO-01",
      "price": {"amount": 15, "currency": "AED", "kind": "from_estimate"},
      "availability": "not_checked",
      "verification": "sandbox_example"
    }
  ],
  "actions": [{"id": "laundry.request_quote", "label": "Request quote", "requires_approval": true}]
}
```

Render through a trusted UI component registry. The agent may populate *data*, never arbitrary HTML/JavaScript or executable provider code.

## 8. Optional provider events and subscription contract

A merchant can publish status updates for **authorized existing requests** (for example, an estimated delivery window) by validated webhook or scheduled polling. This is separate from merchant discovery and does **not** grant permission to send arbitrary advertisements.

```yaml
# Illustrative event declaration; not a real provider endpoint
provider_id: DEMO-01
notifications:
  - event: order.delivery_window_updated
    source_authentication: signed_webhook_or_approved_polling
    required_fields: [order_reference, window_start, window_end, timezone, observed_at]
    scopes: [user_order_status]
    user_opt_in: true
    idempotency_key: provider_event_id
    action_card: delivery_window
```

- Normalize event timestamps, dedupe by `(provider_id, external_event_id)`, and link only to the correct owner of the service request.
- Mark information as `provider_confirmed`, `merchant_estimated`, `user_supplied`, or `simulated_demo`.
- An estimated delivery window is not a guarantee; do not promote a mere `SUBMITTED` request to `CONFIRMED` because a message was sent.
- Child tickets/QR assets must originate from the authorized issuer; the companion can **present existing tickets**, never fabricate admission credentials.
- Separate **data sharing permission**, **order execution approval**, **notification subscription**, and **background location opt-in**.

## 9. Event-triggered action-card contract

```json
{
  "type": "ticket_wallet",
  "schema_version": "1",
  "title": "Your family tickets",
  "event_context": "destination.approaching",
  "trigger_confidence": "inferred",
  "as_of": "2026-10-09T09:10:00+04:00",
  "items": [
    {"ticket_id": "example_existing_ticket", "issuer_status": "verified_asset_required"}
  ],
  "actions": [{"id": "tickets.open_existing", "label": "Open tickets", "requires_approval": false}]
}
```

Illustrative only. The UI must refuse to display an actual admission barcode without a valid issuer asset and member authorization. A `parking_photo_prompt` or `indoor_route_step` card uses the same typed envelope and must support user correction.

## 10. Security and legal boundaries

- Allowlisted hosts/endpoints and provider verification are mandatory for write actions.
- User-specific actions require least-privilege authentication and explicit consent.
- Do not store government documents, Places content, or third-party media beyond permitted terms.
- Verify offer expiration; a 10–15% perk is **optional and merchant-confirmed**, not guaranteed.
- Payment, regulated healthcare, formal official filings, insurance eligibility and escrow must have separate authorized integrations.
- Official government datasets are not equivalent to delegated account-action privileges.
- Preserve source/provenance and freshness for prices, availability, terms and legal advice.

## 11. Integration acceptance test checklist

- [ ] Provider authorized and identity verified
- [ ] Source/license permits reuse
- [ ] Manifest/schema validated
- [ ] Required user approvals captured
- [ ] Actions use safe idempotency and timeouts
- [ ] Failure/unknown-state UI tested
- [ ] Real provider confirmation distinguished from estimate
- [ ] Logging redacts sensitive information
- [ ] Version rollback and provider suspension work
- [ ] Human production approval recorded
- [ ] Webhooks authenticated and deduplicated; delayed/replayed events handled
- [ ] Push/in-chat delivery follows explicit subscriptions, TTL and quiet hours
- [ ] Ticket barcodes map to issuer-confirmed records, not AI-generated code
- [ ] Location and motion signals are optional and never silently shared with merchants
- [ ] Map/tenant geometry rights verified before re-rendering venue floor plans
