# docs/plan/Memory/ — memory plan only

**Read `memory.md` first.** That is the single memory plan (18 Nov consolidation). Do not walk `_archive/` or invent parallel plans.

| Path | Role |
|---|---|
| `memory.md` | **The plan** — decisions, mental model, tables, **§9 Quest-like export tree**, §17 Vault UI, and **§18 the current engine: temporal_note** (24 Nov; Hindsight superseded 23 Nov) |
| `_archive/` | Historical research inputs (`memory-research-2026-11.md`, `quest-tree-mechanics.md`) + **permanent local benchmark exports (`quest-memory-export/`, `quest-memory-export.zip`, `hindsight-kb-export/`)** |
| **LOCK (`quest-memory-export`)** | **NEVER remove, move, or delete `docs/plan/Memory/_archive/quest-memory-export/`, `quest-memory-export.zip`, `hindsight-kb-export/`, or `design/references/quest/` ever.** They must remain permanently on disk for side-by-side comparison. |

## Nearby (do not copy back here)

| Doc | Why |
|---|---|
| `docs/plan/Memory/memory.md` §18 | Current engine and gates (MEM-01 / AC gates superseded). Execution: `apps/memory/upgrade/TN_UPGRADE_PLAN.md`, `prompts/`, `reports/STATUS.md` |
| `ARCHITECTURE.md` §7 | Memory contracts |
| `apps/api/app/lab/CLAUDE.md` | Lab pipeline + mamty-hindsight playbook |
| `docs/plan/backfill-agent.md` | Historical backfill queue (lab and older backfill/brief docs are context only) |
| `docs/plan/morning-brief.md` §8 | Cards, ScopeGuard, generators |
| `docs/references/residence-ontology-tree.md` | Fine topic spine IDs |
| `docs/references/recommender-plan.md` | Interest weights (superseded in part by morning-brief) |

## Rules

- One plan file (`memory.md`). New memory design goes there or ask before splitting.  
- No real chat, Quest personal export, or week JSON inside this folder.  
- App + system prompts fill extract/route/verdict gaps; code owns FTS, aliases, weights, cards, gates.
