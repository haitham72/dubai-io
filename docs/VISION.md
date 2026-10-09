# Dubai-io — Vision

The long-term picture, condensed from the original handoff (`archive/handoff/01`, `07`, `08`). **Vision only: it adds no build scope.** Scope is in `PLAN.md`.

## The problem

People in Dubai juggle 10–15 apps: government services, taxis, delivery, home services, WhatsApp groups for recommendations, notes for where they parked. Every one is reactive. You open it, remember the deadline, dig through menus and fill in a form.

## The idea

**One conversation that knows you, speaks first when it matters, and grows as services join.** It is built from three ideas:

| Idea | Borrowed from | What it means here |
|---|---|---|
| **Companion** | "Jarvis" | Remembers what you told it, connects events over time, and sends useful messages before you ask. Always on consent, never surveillance |
| **Mini-apps** | WeChat | Services appear *inside* the chat. Standard cards first; a merchant's own HTML mini-app when richer interaction helps. No app per shop |
| **Platform** | Shopify | A shop joins by uploading a photo of its menu or price list. The AI builds its profile and mini-app, a human approves, and it's live |

There are two audiences in one product: **visitors** (arrival, getting around, local help, departure) and **residents** (household services, bills, vehicles, neighbourhood shops). Mode is a user setting.

## Principles

1. **Truth in status.** Suggested ≠ requested ≠ confirmed ≠ paid. Only a real merchant or provider action changes status.
2. **Every fact shows where it came from:** official, merchant, user-supplied, estimate or demo.
3. **Consent before sharing.** The user sees exactly what goes to whom.
4. **Proactive, not creepy.** Opt-in triggers, quiet hours, easy "that's wrong", no background tracking assumed.
5. **Many merchants, few contracts.** Merchants are records in a registry with shared capability contracts, not one integration each.
6. **Merchant maturity levels:** L1 discoverable → L2 contactable → L3 quotes → L4 confirmed booking → L5 tracked fulfilment. A shop joins at whatever level it can actually support.

## Where it goes after the contest

| Horizon | Adds |
|---|---|
| Early product | More merchant categories, resident flows, civic guidance with official citations, departure flow (VAT refund, check-in) |
| Growth | Native app (real geofencing, parking memory), community Q&A, verified offers |
| Ecosystem | Bookings and payments with licensed partners, official integrations where authorised, personal media memory |

## Reference library (archived, still useful)

- `archive/handoff/03` and `06`: 25 scenarios (S01–S25), tourist deep-dives, edge cases and acceptance tests
- `archive/handoff/04`: merchant integration standard (L1–L5, manifests, envelopes)
- `archive/handoff/02`: long-term architecture (community, media, indoor wayfinding, tickets)
