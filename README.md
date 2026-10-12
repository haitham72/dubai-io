# Dubai-io

A chat-first AI companion for Dubai visitors and residents, built for the Create AI Agents Championship.

## Try the clickable demo

Plain HTML, no build step:

```bash
cd demo
python -m http.server 8765
# open http://localhost:8765
```

On the left is an iPhone-style app. On the right, **Under the hood** shows the agent's tool calls, the sandbox bridge, the request state machine and a merchant inbox you can drive by hand (untick *auto-respond*).

Demo path: **Hello, visitor** (scripted demo, landed 00:40) → DXB arrival guide (gate → passport → baggage → customs → arrivals) → taxi recommended with reason (Metro stopped) → taxi details + receipt saved → "shirt pressed by 9 tomorrow" → Talabat-normal laundry list → mini-app → approval → merchant accepts, ready 10:00 → deadline conflict → earlier slot 08:30 confirmed → new shop joins from price-list photo → "I left my bag in the taxi" → RTA-field report, not recovered → opt-in community discovery (demo fixtures, mutual join) → parking memory + photo search, day-plan draft, VAT departure checklist → graphic tickets (provider-confirmed), prayer times + qibla + mosque proximity (simulated trigger). Every other case (Salik, geofencing claims, disputes…) gets an honest scripted answer: guidance + official handoff, never booked/filed/paid.

Everything in the demo is scripted with fictional merchants and example prices. Nothing is live.

## Docs

| File | What it is |
|---|---|
| `PLAN.md` | **The plan**: scope, demo arc, phases and gates. Start here |
| `ARCHITECTURE.md` | How it will be built: modules, contracts, state machine, sandbox |
| `CLAUDE.md` | Rules for coding agents |
| `demo/` | Clickable prototype (static, no build) |
| `main` branch | Paper trail: `docs/`, `archive/` |

**Stage:** sketch (Phase 0).
