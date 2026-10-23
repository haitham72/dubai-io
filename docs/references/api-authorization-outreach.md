# API authorization outreach — tracker + templates (23 Oct)

Founder sends everything from their own identity and accounts. Agents never contact providers, never fill applications, never handle credentials. Detail per provider: `docs/references/api-catalog.md`.

## Tracker

| Provider | What we need | Path | Status |
|---|---|---|---|
| Google Places / Maps | Places + Maps JS keys (site key referrer-restricted) | Self-serve Cloud Console | ☐ requested |
| Tavily | Search key (news/research) | Self-serve signup | ☐ requested |
| SerpAPI | Search fallback key | Self-serve signup | ☐ requested |
| NewsData | News key | Self-serve signup | ☐ requested |
| Finnhub | Market quotes key | Self-serve signup | ☐ requested |
| Careem / Uber | Ride-hailing: MCP/affiliate or business access terms | Partnership / developer application | ☐ requested |
| Talabat / Deliveroo | Food ordering: affiliate/API terms (fixed prices only) | Partnership inquiry | ☐ requested |
| noon / Amazon | Product links: affiliate terms | Affiliate signup | ☐ requested |
| RTA / DEWA / Salik / du | Display-only deep links + attribution rules | None needed (no execution, rule 4) | N/A |

## Rules

- Keys go in local `apps/api/.env` only. Never committed, never pasted into chats, tickets, or screenshots.
- Each newly-keyed path must show real data or its honest unavailable state. No silent fixture substitution.
- No bidding/quotes/negotiation ever; no government execution; approvals before any send/share. If a provider's terms require otherwise, stop and re-scope.

## Application checklist (per provider)

1. Read the catalog entry + the provider's current terms/fees/rate limits.
2. Apply from the founder account; record ticket/reference ID in the tracker.
3. On grant: store key in `.env`, run the path's tests, verify one real response, update catalog + status.

## Template — partnership inquiry

> Subject: API / affiliate access for Dubai-io (personal assistant app)
>
> Hello — I'm building Dubai-io, a personal assistant for everyday life in Dubai (contest-stage, single tester). I'm looking for [API access / affiliate terms] for [read-only listings + fixed-price ordering with explicit user approval per order]. No bidding, no automated purchasing beyond user-approved fixed orders. Could you share the application process, terms, rate limits, and any sandbox? Happy to attribute per your brand rules.
>
> Thanks, Haitham
