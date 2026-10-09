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

Demo path: **Hello, visitor** → DXB arrival guide (gate → passport → baggage → customs → arrivals) → taxi or Metro → "find a pharmacy" → each pharmacy opens **its own HTML mini-app** in a sandbox → approval → merchant quote → confirmed.

Everything in the demo is scripted with fictional merchants and example prices. Nothing is live.

## Docs

| File | What it is |
|---|---|
| `CLAUDE.md` | Rules for coding agents and document authority |
| `PLAN.md` | MVP freeze, demo, phases, gates |
| `ARCHITECTURE.md` | Build architecture and contracts |
| `REVIEW.md` | Review of the full planning package |
| `dubai-io-handoff/` | Original vision and reference docs |
