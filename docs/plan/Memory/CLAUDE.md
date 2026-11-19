# docs/plan/Memory/ — memory plan only

**Read `memory.md` first.** That is the single memory plan (18 Nov consolidation). Do not walk `_archive/` or invent parallel plans.

| Path | Role |
|---|---|
| `memory.md` | **The plan** — decisions, Hindsight go-to engine, mental model, tables, extract→card loop, §8 cards-UI benefit, **§12 Adaptive Knowledge Base Export Tree (`hindsight-kb-export/`)**, gaps, sources |
| `_archive/` | Historical research inputs (`memory-research-2026-11.md`, `quest-tree-mechanics.md`) + **permanent local benchmark exports (`quest-memory-export/`, `quest-memory-export.zip`, `hindsight-kb-export/`)** |
| **LOCK (`quest-memory-export`)** | **NEVER remove, move, or delete `docs/plan/Memory/_archive/quest-memory-export/`, `quest-memory-export.zip`, `hindsight-kb-export/`, or `design/references/quest/` ever.** They must remain permanently on disk for side-by-side comparison. |

## Nearby (do not copy back here)

| Doc | Why |
|---|---|
| `PLAN.md` §2 | Locked MEM-01 / AC gates |
| `ARCHITECTURE.md` §7 | Memory contracts |
| `apps/api/app/lab/CLAUDE.md` | Lab pipeline + mamty-hindsight playbook |
| `docs/plan/backfill-agent.md` | Backfill queue (after AC-1–3) |
| `docs/plan/morning-brief.md` §8 | Cards, ScopeGuard, generators |
| `docs/references/residence-ontology-tree.md` | Fine topic spine IDs |
| `docs/references/recommender-plan.md` | Interest weights (superseded in part by morning-brief) |

## Rules

- One plan file (`memory.md`). New memory design goes there or ask before splitting.  
- No real chat, Quest personal export, or week JSON inside this folder.  
- App + system prompts fill extract/route/verdict gaps; code owns FTS, aliases, weights, cards, gates.
