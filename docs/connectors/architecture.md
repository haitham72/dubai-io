# Connector architecture

Universal ingestion for Dubai-io. A connector is an independent module. The record schema does not change when one is added.

Profile memory is a different store. `mem_events` and `profile_facts` stay user-supplied or explicitly confirmed. A sync never writes them, never fills an approval card, and never sets an order status. Connector rows are source memory: what a provider or an imported file actually contained.

## Requirements

| # | Requirement | Where it lives |
|---|---|---|
| 1 | Authentication and authorization | `prepare` / `probe`. Tokens are encrypted per `(owner, connector)` before they touch the database. |
| 2 | Initial import | `fetch_page` with an empty cursor. |
| 3 | Incremental sync | The same call with the cursor stored on the connection. The cursor shape is private to the connector. |
| 4 | Webhooks or polling | Telegram and WhatsApp accept a signed webhook. Everything else is an explicit `POST /sync`. No background poller is started. |
| 5 | Universal memory format | `RawItem` → `connector_records`. |
| 6 | Source id and timestamp | Stored as the provider sent them. The code does not reformat a timestamp it was given. |
| 7 | Dedup and retry | Unique `(owner, dedupe_key)`. Unchanged content is a duplicate. HTTP 429/5xx schedules capped exponential backoff (max 5 attempts). |
| 8 | Health and sync status | `health` on the connection (`healthy`, `degraded`, `auth_required`, `rate_limited`, `error`, `unknown`) and a row in `connector_sync_log`. |
| 9 | Revoke and disconnect | Disconnect deletes the local secret and keeps records. Revoke also asks the provider when a real revoke endpoint exists, then deletes the local secret. |
| 10 | User data deletion | `DELETE /api/connectors/{id}/data` removes records, credentials, cursors, sync log, and outbound grants for that owner and connector. It does not delete the user's mailbox, Drive files, or folder on disk. WhatsApp also asks Evolution to log out and delete that user's instance. |
| 11 | Outbound permission | Default deny. `propose` stores the exact recipient and text. `execute` runs only after that owner approves that payload, once, before it expires. A mismatch sends nothing. |

## Record

`connector_records` columns are the same for every source:

`owner`, `connector_id`, `source_id`, `source_timestamp`, `ingested_at`, `dedupe_key`, `kind`, `title`, `text`, `provenance`, `as_of`, `metadata`.

`dedupe_key` is `{connector_id}:{source_id}`. Provider reads are `provider_confirmed`. File imports are `user_supplied`. An imported file cannot label itself `official`. Amounts copied from a file keep `provenance: user_supplied` and an `as_of`. Source-specific fields (attachment names, media mimetype, group id) stay inside `metadata`.

Live syncs are bounded pages. `read_history: true` means the API can be paged, not that one call downloads a lifetime archive.

## Registry

`app/connectors/catalog.py` is the capability declaration: official vs unofficial vs export vs unavailable, auth method, what can be read, whether outbound exists, rate-limit notes, and the six priority scores.

`app/connectors/plugins/*.py` registers builders. `registry.discover()` imports that package. A new official source is a new module plus a catalog row. Unavailable sources have a catalog row and no builder, so a sync cannot invent data for them.

## Credentials

Fernet ciphertext in `connector_credentials`, same pattern as Google OAuth grants. The key is `CONNECTOR_TOKEN_KEY`, or `OAUTH_TOKEN_KEY`, or `apps/api/data/connector.key` (mode 0600, not committed). API responses return account labels and, once, a webhook secret. They do not return tokens.

The existing Google sign-in (`/api/auth/google`) stays the identity and mail-profiler grant. Connector credentials are a separate row so disconnecting a connector does not drop that login.

## HTTP

`GET /api/connectors` lists declarations plus this owner's connection. Connect, sync, import, disconnect, revoke, delete, health, records, reconnect, outbound propose/decide/execute, and `POST /api/connectors/hooks/{id}/{hook_id}` with header `X-Connector-Secret`. The webhook owner is the connection looked up by hook id, not the caller's cookie.

## What is not claimed

No worker or cron was added. Quiet hours and the outbox are unchanged. Government, bank, and shop adapters are not implied by a connector id. Sources without an authorized personal API are `unavailable` or `export` (a file the user already downloaded). See the [capability matrix](capability-matrix.md), the [priority scores](prioritization.md), and the [WhatsApp evaluation](whatsapp-evolution.md).

Tables: `supabase/migrations/20261114000100_connectors.sql` (RLS on, browser roles revoked). SQLite tests create the same tables at runtime.
