# WhatsApp via Evolution API (Baileys)

**Decision:** optional, default off, unofficial. It is not a WhatsApp Cloud API or Business API integration, and it is not offered as a reliable inbox.

## What Baileys is

[Evolution API](https://doc.evolution-api.com) is a third-party HTTP server. Its `WHATSAPP-BAILEYS` integration speaks the private WhatsApp Web linked-device protocol through the Baileys library. A successful QR scan creates a linked device on the person's own number. Meta does not support that for third-party assistants. The official Cloud API is a different product: a business phone number, templates, and webhooks registered with Meta. It does not link someone's personal WhatsApp, and this repo does not call it.

## What this connector does

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

## Risks (shown on connect)

- WhatsApp can ban the number, log the linked device out, or flag the account. Do not use a number you cannot afford to lose.
- Sessions break when WhatsApp changes the private Web protocol. Expect disconnects.
- History is incomplete.
- The Evolution process holds the linked-device session. Run it on a machine you control. A shared hosted Evolution server is another party with the session.
- This violates WhatsApp's terms for automated personal use. That is a product risk, not a legal opinion.

## Why it stays off

User value in Dubai is high (score 5) and API access, reliability, privacy/legal, and maintainability are all 1. Priority total is 13, near the bottom of the registry. Gmail, Calendar, Outlook, and a local folder outrank it because they are official and supportable.

Polling still works if Evolution cannot forward the webhook header. There is no background poller in this process.

## Configuration

```
WHATSAPP_EVOLUTION_ENABLED=0
EVOLUTION_API_BASE_URL=
EVOLUTION_API_KEY=
```

Leave the flag unset. Turning it on is an explicit choice to accept the ban and reliability risks above.
