# Connectors + "know me" profile — plan (DRAFT, 15 Nov 2026)

Status: planning only, nothing built. Testers + contest only. Deployment is a later stage; runs locally (`apps/api` + local Supabase).

## Founder decisions

- Testers connect Instagram, WhatsApp, Slack (+ Gmail/Outlook); Dubai-io gathers info about the user from them (Quest-style "know me" profile).
- WhatsApp: founder uploads own chat export; testers are automatic via Cloud API Coexistence.
- No DM auto-replies here (that's a different app).

## 1. Instagram — Instagram API with Instagram Login (Development mode)

- Reuse the retired `@faz3.posts` Meta app, webhook handling and Graph v23 calls (`Claude---Cowork/proposals/@faz3.posts/supabase/`).
- New: per-user OAuth → long-lived token (60 days, refreshable), stored encrypted with `OAUTH_TOKEN_KEY`. (faz3 used one static token for its own account.)
- Testers are added as Instagram Testers in the Meta app and accept in Instagram (Settings → Apps and websites → Tester invites). API works for Business/Creator accounts only.
- Scopes: `instagram_business_basic`, `instagram_business_manage_insights`, `instagram_business_manage_comments`, `instagram_business_manage_messages` (DM history via Conversations API).
- Data: profile, follower counts, posts (likes, comments), post insights (views, reach, saved, shares), account insights + follower demographics, comments, DM threads.
- Not in the API: who the user follows, posts they liked/saved, personal accounts. Instagram "Download your information" (JSON upload) covers those.

## 2. WhatsApp

- Founder: chat export upload (`.txt`/`.zip`) → parser.
- Testers: Coexistence via Embedded Signup — tester keeps using the WhatsApp Business app; Meta syncs contacts + up to ~6 months of 1:1 history, then new messages by webhook.
- Platform facts to verify before building:
  - Coexistence needs the WhatsApp Business app (not regular WhatsApp).
  - Group chats likely not synced.
  - Embedded Signup for other people's numbers normally needs the Meta app to be a Tech Provider (Business Verification). Check whether app-role testers can onboard in Development mode.

## 3. Slack — Slack app, user-token OAuth

- Enable "Manage distribution" so testers in other workspaces can install it (no Marketplace listing needed).
- Scopes: `channels:history`, `groups:history`, `im:history`, `mpim:history`, `channels:read`, `groups:read`, `im:read`, `users:read`, `search:read`.
- Platform fact: since 2025, non-Marketplace apps in *other* workspaces get ~1 req/min, 15 messages per call on `conversations.history`/`replies`. Founder's own workspace isn't limited. `search.messages` + incremental sync helps.

## 4. Gmail / Outlook (already in `unified-app-design.md` §8 item 7)

- Gmail OAuth "Testing" status: up to 100 test users, no verification; refresh tokens expire every 7 days → "Reconnect".
- Outlook via Microsoft Graph `Mail.Read`.

## 5. Backend shape (`apps/api`)

- `connector_accounts`: `owner_id, provider, external_account_id, scopes, token_ciphertext, token_expires_at, status, last_synced_at, sync_cursor`.
- `source_items`: normalized messages/posts/comments: `owner_id, provider, kind, external_id, author, text, occurred_at, metrics jsonb`. Unique `(provider, external_id)` so re-sync is idempotent.
- `app/connectors/<provider>.py`: `authorize_url()`, `exchange()`, `refresh()`, `sync(cursor)`; one sync runner.
- Webhooks (Instagram, WhatsApp) need a public URL — local tunnel for now.
- Connectors gallery: connect / disconnect / status per source.

## 6. "Know me" profile

1. Sync sources into `source_items`.
2. `FAST_MODEL` fan-out reads batches → JSON candidates `{claim, category, evidence_ids[], confidence}` (interests, routines, places, frequent contacts, work topics, posting habits, tone, …).
3. Merge into the existing profile engine. **One memory system:** `source_items` is the raw layer; everything derived (facts, episodes, hypotheses) goes into the existing temporal tables (`profile_facts` with `valid_from/valid_to`, `episodes`), with `evidence` pointing back to `source_items`. No second memory store.
4. Show in Me with links back to the source message/post.

Instagram analytics numbers go to a Dashboard workspace.

## 7. Order of work

1. Backend shape (§5) + Connectors gallery.
2. Instagram connector + analytics workspace.
3. WhatsApp export upload → first "know me" run end to end.
4. Slack.
5. Gmail / Outlook.
6. Verify the Coexistence question → build Coexistence for testers.

## 8. Open questions

- Coexistence in Development mode for testers' numbers (§2).
- Do testers have Instagram Business/Creator and WhatsApp Business accounts?
