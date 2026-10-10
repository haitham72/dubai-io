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

Demo path: **Hello, visitor** → DXB arrival guide (gate → passport → baggage → customs → arrivals) → taxi or Metro → "find a pharmacy" → each pharmacy opens **its own HTML mini-app** in a modal sandbox → approval → merchant accepts fixed order → confirmed.

Everything in the demo is scripted with fictional merchants and example prices. Nothing is live.

## Docs

| File | What it is |
|---|---|
| `PLAN.md` | **The plan**: scope, demo arc, phases and gates. Start here |
| `ARCHITECTURE.md` | How it will be built: modules, contracts, state machine, sandbox |
| `CLAUDE.md` | Rules for coding agents |
| `docs/DESIGN.md` | Style (iOS light + cyan), layout, trust labels |
| `docs/DECISIONS.md` | Decision log and open questions |
| `docs/VISITORS.md` | Visitor needs as hypotheses to test, the hotel-concierge question, interview script |
| `docs/research/` | Deep-research prompt for Gemini/DeepSeek (⏳ not run yet) and its results |
| `docs/VISION.md` | Long-term vision (no build scope) |
| `archive/` | Original handoff docs 01–08, old plan, past reviews |

**Stage:** sketch (Phase 0).
