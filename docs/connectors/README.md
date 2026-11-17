# Connectors — Architecture, Capability Matrix, Priorities & Policies

Universal ingestion for Dubai-io. A connector is an independent module. The record schema does not change when one is added.

Profile memory is a different store. `mem_events` and `profile_facts` stay user-supplied or explicitly confirmed. A sync never writes them, never fills an approval card, and never sets an order status. Connector rows are source memory: what a provider or an imported file actually contained.

## 1. Architecture & Record Contract

### Requirements

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

### Record

`connector_records` columns are the same for every source:

`owner`, `connector_id`, `source_id`, `source_timestamp`, `ingested_at`, `dedupe_key`, `kind`, `title`, `text`, `provenance`, `as_of`, `metadata`.

`dedupe_key` is `{connector_id}:{source_id}`. Provider reads are `provider_confirmed`. File imports are `user_supplied`. An imported file cannot label itself `official`. Amounts copied from a file keep `provenance: user_supplied` and an `as_of`. Source-specific fields (attachment names, media mimetype, group id) stay inside `metadata`.

Live syncs are bounded pages. `read_history: true` means the API can be paged, not that one call downloads a lifetime archive.

### Registry

`app/connectors/catalog.py` is the capability declaration: official vs unofficial vs export vs unavailable, auth method, what can be read, whether outbound exists, rate-limit notes, and the six priority scores.

`app/connectors/plugins/*.py` registers builders. `registry.discover()` imports that package. A new official source is a new module plus a catalog row. Unavailable sources have a catalog row and no builder, so a sync cannot invent data for them.

### Credentials

Fernet ciphertext in `connector_credentials`, same pattern as Google OAuth grants. The key is `CONNECTOR_TOKEN_KEY`, or `OAUTH_TOKEN_KEY`, or `apps/api/data/connector.key` (mode 0600, not committed). API responses return account labels and, once, a webhook secret. They do not return tokens.

The existing Google sign-in (`/api/auth/google`) stays the identity and mail-profiler grant. Connector credentials are a separate row so disconnecting a connector does not drop that login.

### HTTP

`GET /api/connectors` lists declarations plus this owner's connection. Connect, sync, import, disconnect, revoke, delete, health, records, reconnect, outbound propose/decide/execute, and `POST /api/connectors/hooks/{id}/{hook_id}` with header `X-Connector-Secret`. The webhook owner is the connection looked up by hook id, not the caller's cookie.

### What is not claimed

No worker or cron was added. Quiet hours and the outbox are unchanged. Government, bank, and shop adapters are not implied by a connector id. Sources without an authorized personal API are `unavailable` or `export` (a file the user already downloaded). See the [capability matrix](#2-capability-matrix-40-connectors), the [priority scores](#3-priority-scores), and the [WhatsApp evaluation](#4-whatsapp-via-evolution-api--baileys-unofficial-off-by-default).

Tables: `supabase/migrations/20261114000100_connectors.sql` (RLS on, browser roles revoked). SQLite tests create the same tables at runtime.

---

## 2. Capability Matrix (40 Connectors)

Declared in `app/connectors/catalog.py`. `available` in the API is false for `unavailable` rows and for WhatsApp until `WHATSAPP_EVOLUTION_ENABLED`, `EVOLUTION_API_BASE_URL`, and `EVOLUTION_API_KEY` are all set. `outbound: true` still does nothing until the owner approves the exact payload.

`read_history` means the source can be paged. It does not mean one sync downloads a full archive. Attachment `metadata` is a name or mimetype, not the bytes.

| id | category | integration | mode | auth | read | history | attachments | realtime | outbound | content | summary |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `browser_bookmarks` | browser | export_import | export | file_import | true | false | none | none | false | full | No live bookmark API. Import an export you downloaded. |
| `browser_history` | browser | export_import | export | file_import | true | false | none | none | false | full | No live browser-history API. Import an export you downloaded. |
| `browser_saved_pages` | browser | export_import | export | file_import | true | false | none | none | false | full | No live saved-pages API. Import an export you downloaded. |
| `google_calendar` | calendar | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Google Calendar read of the primary calendar. |
| `outlook_calendar` | calendar | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Outlook calendar read through Microsoft Graph. |
| `github` | development | official_api | live | api_token | true | true | none | polling | false | full | Official GitHub notification read with a personal access token. |
| `gitlab` | development | official_api | live | api_token | true | true | none | polling | false | full | Official GitLab activity read. |
| `jira` | development | official_api | live | api_token | true | true | none | polling | false | full | Official Jira Cloud read of issues assigned to you. |
| `gmail` | email | official_api | live | oauth_bearer | true | true | metadata | polling | false | full | Official Gmail read API for headers, snippets, and attachment names. |
| `imap` | email | official_api | live | imap_password | true | true | none | polling | false | full | Official IMAP for a mailbox you can log into with an app password. |
| `outlook` | email | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Microsoft Graph inbox read with delta sync. |
| `dropbox` | files | official_api | live | oauth_bearer | true | true | metadata | polling | false | metadata | Official Dropbox folder listing with cursor continuation. |
| `filesystem` | files | official_api | live | filesystem_path | true | true | content | polling | false | full | Reads a folder you choose on this server. Does not scan the whole disk. |
| `google_drive` | files | official_api | live | oauth_bearer | true | true | metadata | polling | false | metadata | Official Google Drive metadata list. |
| `onedrive` | files | official_api | live | oauth_bearer | true | true | metadata | polling | false | metadata | Official OneDrive metadata list through Microsoft Graph. |
| `finance_provider` | finance | unavailable | unavailable | none | false | false | none | none | false | none | No financial-data provider is configured. Use an imported statement file. |
| `finance_statements` | finance | export_import | export | file_import | true | false | none | none | false | full | Import bank or card statements you exported. No bank is contacted. |
| `saved_media` | media | export_import | export | file_import | true | false | none | none | false | full | Import a media list you supply. Does not scrape a streaming site. |
| `spotify` | media | official_api | live | oauth_bearer | true | true | none | polling | false | metadata | Official Spotify read of your saved tracks. |
| `youtube` | media | official_api | live | oauth_bearer | true | true | none | polling | false | metadata | Official YouTube read of your uploads playlist. Not watch history. |
| `discord` | messaging | official_api | live | bot_token | true | true | none | polling | false | full | Official Discord bot read of one channel you name. Not personal DMs. |
| `signal` | messaging | unavailable | unavailable | none | false | false | none | none | false | none | Signal has no authorized personal API. No unofficial client is included. |
| `slack` | messaging | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Slack read of conversations the token can access. |
| `telegram` | messaging | official_api | live | bot_token | true | false | none | webhook_or_polling | true | full | Official Telegram bot for messages sent to that bot, not your private history. |
| `whatsapp` | messaging | unofficial | live | qr_linked_device | true | true | metadata | webhook_or_polling | true | full | Optional unofficial WhatsApp link through a self-hosted Evolution API (Baileys). Off by default. |
| `android_notifications` | mobile | unavailable | unavailable | none | false | false | none | none | false | none | Android notification access needs a device app this server does not include. |
| `contacts` | mobile | unavailable | unavailable | none | false | false | none | none | false | none | Contacts stay on the device. This server does not import them. |
| `ios_permitted` | mobile | unavailable | unavailable | none | false | false | none | none | false | none | iOS does not permit this server to read other apps' data. No connector is offered. |
| `linear` | productivity | official_api | live | api_token | true | true | none | polling | false | full | Official Linear read of issues assigned to you. |
| `notion` | productivity | official_api | live | oauth_bearer | true | true | none | polling | false | metadata | Official Notion page list for pages shared with the integration. |
| `todoist` | productivity | official_api | live | api_token | true | true | none | polling | false | full | Official Todoist task read. |
| `trello` | productivity | official_api | live | api_token | true | true | none | polling | false | full | Official Trello card read. |
| `amazon` | shopping | export_import | export | file_import | true | false | none | none | false | full | No consumer Amazon order API. Import a file you exported. |
| `ebay` | shopping | export_import | export | file_import | true | false | none | none | false | full | No buyer purchase-history API is used. Import a file you exported. |
| `noon` | shopping | export_import | export | file_import | true | false | none | none | false | full | No Noon order API. Import a file you exported. |
| `purchase_receipts` | shopping | export_import | export | file_import | true | false | none | none | false | full | Import purchase receipts you already have. No shop is contacted. |
| `instagram` | social | export_import | export | file_import | true | false | none | none | false | full | Personal Instagram DMs are unavailable. A file you exported can be imported. |
| `linkedin` | social | export_import | export | file_import | true | false | none | none | false | full | No personal LinkedIn API. Import a data download you exported. |
| `reddit` | social | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Reddit read of your saved posts. |
| `x` | social | official_api | live | oauth_bearer | true | false | none | polling | false | full | Official X API for your own recent posts. Direct messages are not available. |

### Limitations that are easy to miss

- Gmail stores the snippet and attachment **names**. It does not download attachment bytes and it does not send.
- Microsoft mail and calendar use Graph delta links, and those links are refused unless the host is `graph.microsoft.com`.
- Jira and self-managed GitLab URLs must be public `https` hosts. Loopback and private addresses are rejected.
- IMAP reads headers and the first 2KB of text over TLS. Revoke deletes the stored password; the app password itself is removed at the mailbox host.
- The local folder refuses the disk root, skips secret-shaped names (`.env`, private keys), and does not follow a symlink out of the folder.
- Dropbox, Drive, and OneDrive list metadata. They do not download file bytes.
- Slack reads conversations the token can see. It does not post.
- Telegram outbound is `sendMessage` to a chat that has talked to the bot, and only after approval. Personal history is not available.
- Reddit is saved posts. X is the user's own posts, not DMs. YouTube is uploads, not watch history. Spotify is saved tracks.

---

## 3. Priority Scores

Scores are 1–5. Higher is better on every column, including maintainability (a 5 is cheap to keep working). They are judgements for a personal assistant in Dubai, stored in `app/connectors/catalog.py` so the API and this table stay on the same numbers.

| Criterion | What a 5 means |
|---|---|
| user_value | Used in ordinary life or work in Dubai |
| api_access | An authorized API or protocol exists and this server can call it |
| completeness | The call returns the records a person would expect, not a thin slice |
| reliability | The integration survives provider changes |
| privacy_legal | Consent is explicit, terms allow it, and other people's data is limited |
| maintainability | One person can keep it working without reverse engineering |

`live` calls a real API. `export` only stores a file the user uploads. `unavailable` has no builder and cannot sync. WhatsApp is `live` in code and **off** unless its feature flag is set; the score already prices that in.

Build order follows the total, then the id. Official mail, calendar, tasks, and a local folder come before anything unofficial.

| id | mode | user_value | api_access | completeness | reliability | privacy_legal | maintainability | total |
|---|---|---|---|---|---|---|---|---|
| google_calendar | live | 5 | 5 | 5 | 5 | 5 | 5 | 30 |
| gmail | live | 5 | 5 | 4 | 5 | 5 | 5 | 29 |
| filesystem | live | 4 | 5 | 5 | 5 | 4 | 5 | 28 |
| github | live | 4 | 5 | 4 | 5 | 5 | 5 | 28 |
| outlook | live | 5 | 5 | 4 | 5 | 5 | 4 | 28 |
| outlook_calendar | live | 4 | 5 | 5 | 5 | 5 | 4 | 28 |
| todoist | live | 4 | 5 | 4 | 5 | 5 | 5 | 28 |
| google_drive | live | 4 | 5 | 4 | 5 | 5 | 4 | 27 |
| dropbox | live | 3 | 5 | 4 | 5 | 5 | 4 | 26 |
| gitlab | live | 3 | 5 | 4 | 5 | 5 | 4 | 26 |
| linear | live | 3 | 5 | 4 | 5 | 5 | 4 | 26 |
| notion | live | 4 | 5 | 4 | 4 | 5 | 4 | 26 |
| onedrive | live | 3 | 5 | 4 | 5 | 5 | 4 | 26 |
| imap | live | 4 | 5 | 4 | 4 | 4 | 4 | 25 |
| trello | live | 3 | 5 | 4 | 4 | 5 | 4 | 25 |
| jira | live | 3 | 5 | 4 | 4 | 5 | 3 | 24 |
| slack | live | 4 | 5 | 3 | 4 | 4 | 4 | 24 |
| spotify | live | 3 | 5 | 3 | 4 | 5 | 4 | 24 |
| youtube | live | 3 | 5 | 3 | 4 | 5 | 4 | 24 |
| finance_statements | export | 4 | 1 | 3 | 5 | 5 | 5 | 23 |
| purchase_receipts | export | 4 | 1 | 3 | 5 | 5 | 5 | 23 |
| telegram | live | 4 | 3 | 2 | 4 | 4 | 4 | 21 |
| reddit | live | 3 | 4 | 3 | 3 | 4 | 3 | 20 |
| saved_media | export | 2 | 1 | 2 | 5 | 5 | 5 | 20 |
| browser_bookmarks | export | 2 | 1 | 2 | 4 | 4 | 5 | 18 |
| browser_history | export | 3 | 1 | 2 | 4 | 4 | 4 | 18 |
| discord | live | 3 | 3 | 2 | 4 | 3 | 3 | 18 |
| noon | export | 4 | 1 | 2 | 3 | 4 | 4 | 18 |
| amazon | export | 3 | 1 | 2 | 3 | 4 | 4 | 17 |
| browser_saved_pages | export | 2 | 1 | 2 | 4 | 4 | 4 | 17 |
| linkedin | export | 4 | 1 | 2 | 3 | 3 | 4 | 17 |
| ebay | export | 2 | 1 | 2 | 3 | 4 | 4 | 16 |
| x | live | 3 | 3 | 2 | 3 | 3 | 2 | 16 |
| android_notifications | unavailable | 4 | 1 | 2 | 2 | 3 | 2 | 14 |
| whatsapp | live | 5 | 1 | 3 | 2 | 1 | 1 | 13 |
| finance_provider | unavailable | 4 | 1 | 1 | 1 | 3 | 2 | 12 |
| instagram | export | 3 | 1 | 1 | 2 | 2 | 3 | 12 |
| contacts | unavailable | 3 | 1 | 1 | 1 | 2 | 2 | 10 |
| ios_permitted | unavailable | 4 | 1 | 1 | 1 | 2 | 1 | 10 |
| signal | unavailable | 4 | 1 | 1 | 1 | 2 | 1 | 10 |

Notes that move a source down even when user value is high:

- **Telegram** is the official Bot API. It does not see personal chat history.
- **Discord** is an official bot in one channel you name. A user token (self-bot) is not implemented.
- **X** can list the authenticated user's own recent posts. Direct messages are not requested. Access is restricted and often paid.
- **YouTube** reads the uploads playlist, not watch history. Watch history is not in the Data API.
- **Noon, Amazon, eBay, LinkedIn, Instagram** have no authorized personal-inbox or order API for this app. Import is a file the user already downloaded.
- **Signal, iOS, Android notifications, contacts, open banking** have no authorized server integration here. They stay unavailable rather than unofficial.

---

## 4. WhatsApp via Evolution API / Baileys (Unofficial, Off by Default)

**Decision:** optional, default off, unofficial. It is not a WhatsApp Cloud API or Business API integration, and it is not offered as a reliable inbox.

### What Baileys is

[Evolution API](https://doc.evolution-api.com) is a third-party HTTP server. Its `WHATSAPP-BAILEYS` integration speaks the private WhatsApp Web linked-device protocol through the Baileys library. A successful QR scan creates a linked device on the person's own number. Meta does not support that for third-party assistants. The official Cloud API is a different product: a business phone number, templates, and webhooks registered with Meta. It does not link someone's personal WhatsApp, and this repo does not call it.

### What this connector does

Behind `WHATSAPP_EVOLUTION_ENABLED=1` plus `EVOLUTION_API_BASE_URL` and `EVOLUTION_API_KEY`:

| Step | Behaviour |
|---|---|
| Link | `POST /instance/create` with `integration: WHATSAPP-BAILEYS`, then `GET /instance/connect/{instance}`. The response includes the QR (base64) or pairing code. The instance name is `dbi` + a hash of the Dubai-io owner. The client cannot choose it. |
| Incoming | `POST /chat/findMessages/{instance}` and a webhook (`messages.upsert`) verified with a per-connection secret. Direct chats and `@g.us` groups are stored. |
| History | `syncFullHistory` is requested on create. The sync result is always `partial: true` and `health: degraded`. Baileys often returns only a recent slice. An empty page is not a confirmed empty chat. |
| Media | mimetype, file length, file name, and caption are stored. Bytes are not downloaded. |
| Reconnect | `connectionState`. If it is not `open`, the connector fetches a new QR and does not invent messages. |
| Send | `POST /message/sendText/{instance}` only after the owner approves the exact `to` and `text`. The result says the provider accepted the request. It is not a delivery receipt and it is not a `Delivered` status. |
| Revoke / delete | Logout and delete that instance, then drop the local secret. Delete-my-data also removes stored messages. |
| Isolation | One instance per owner. Requests for owner A never use owner B's instance path. The Evolution API key is a server secret, not a per-user WhatsApp password. |

The base URL must be `https`, or `http` on localhost. It cannot carry a username or a query string.

### Risks (shown on connect)

- WhatsApp can ban the number, log the linked device out, or flag the account. Do not use a number you cannot afford to lose.
- Sessions break when WhatsApp changes the private Web protocol. Expect disconnects.
- History is incomplete.
- The Evolution process holds the linked-device session. Run it on a machine you control. A shared hosted Evolution server is another party with the session.
- This violates WhatsApp's terms for automated personal use. That is a product risk, not a legal opinion.

### Why it stays off

User value in Dubai is high (score 5) and API access, reliability, privacy/legal, and maintainability are all 1. Priority total is 13, near the bottom of the registry. Gmail, Calendar, Outlook, and a local folder outrank it because they are official and supportable.

Polling still works if Evolution cannot forward the webhook header. There is no background poller in this process.

### Configuration

```
WHATSAPP_EVOLUTION_ENABLED=0
EVOLUTION_API_BASE_URL=
EVOLUTION_API_KEY=
```

Leave the flag unset. Turning it on is an explicit choice to accept the ban and reliability risks above.

---

## 5. Proposed Tester Onboarding Notes (15 Nov Draft — Not Built)

**Status: proposed 15 Nov, not built** (rescued from `76516cf:docs/plan/connectors.md`). Testers + contest only; local dev (`apps/api` + local Supabase); no DM auto-replies.

- **Instagram — Instagram API with Instagram Login (Development mode):**
  - Reuse the retired `@faz3.posts` Meta app, webhook handling, and Graph v23 calls (`Claude---Cowork/proposals/@faz3.posts/supabase/`).
  - Add per-user OAuth → long-lived token (60 days, refreshable), encrypted with `OAUTH_TOKEN_KEY`.
  - Add testers as Instagram Testers in the Meta app (they accept under Instagram Settings → Apps and websites → Tester invites). Works for Business/Creator accounts only.
  - Scopes: `instagram_business_basic`, `instagram_business_manage_insights`, `instagram_business_manage_comments`, `instagram_business_manage_messages` (DM history via Conversations API).
  - Data: profile, follower counts, posts (likes, comments), post insights (views, reach, saved, shares), account insights + follower demographics, comments, DM threads. Personal accounts, who the user follows, and liked/saved posts are not in the API (covered by Instagram "Download your information" JSON upload).
- **WhatsApp — Export Upload (Founder) + Cloud API Coexistence (Testers):**
  - Founder path: upload `.txt`/`.zip` chat export → parser.
  - Tester path: Coexistence via Embedded Signup — tester keeps using the WhatsApp Business app; Meta syncs contacts + up to ~6 months of 1:1 history, then new messages via webhook.
  - Open platform checks before building: Coexistence requires the WhatsApp Business app (not regular WhatsApp); group chats are likely not synced; Embedded Signup for other people's numbers normally requires Business Verification (Tech Provider) — verify whether app-role testers can onboard in Development mode.
- **Slack — User-token OAuth:**
  - Enable "Manage distribution" so testers in other workspaces can install without a Marketplace listing.
  - Scopes: `channels:history`, `groups:history`, `im:history`, `mpim:history`, `channels:read`, `groups:read`, `im:read`, `users:read`, `search:read`.
  - Rate limit constraint (since 2025): non-Marketplace apps in *other* workspaces get ~1 req/min and 15 messages per call on `conversations.history`/`replies` (founder's own workspace is not limited). Mitigate with `search.messages` + incremental sync.
- **Gmail / Outlook:** Gmail OAuth in "Testing" status supports up to 100 test users without verification (refresh tokens expire every 7 days → "Reconnect"); Outlook uses Microsoft Graph `Mail.Read`.
