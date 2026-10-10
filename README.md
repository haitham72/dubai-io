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

Demo path (target, `PLAN.md §3`): **Hello, visitor** → DXB arrival guide → taxi chosen for a reason (00:40, Metro closed) with trip details saved → "shirt pressed by 9 tomorrow" → three laundries, each opening **its own HTML mini-app** in a modal sandbox → approval → merchant accepts the fixed order → ready-time conflict caught → earlier slot confirmed → "I left my bag in the taxi" report pre-filled from memory.

The current sketch still shows the older pharmacy path; updating it is the first build task.

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
| `docs/research/` | Deep-research results (run 10 Oct, closed) |
| `docs/VISION.md` | Long-term vision (no build scope) |
| `archive/` | Original handoff docs 01–08, old plan, past reviews |

**Stage:** planning locked (10 Oct 2026). Next: Phase 1 build.
