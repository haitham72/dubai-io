# docs/ — where things go

Canon lives at the repo root (`CLAUDE.md`, `PLAN.md`, `ARCHITECTURE.md`, `README.md`); never add other top-level `.md`. Everything else is here. Read only the row your task needs.

| Put this here | Folder | Notes |
|---|---|---|
| Current state, shipped spine, headless lab state, runtime, keys | `status.md` | Single state file. Keep short. |
| Active task, open items, `## Feature decisions` ledger | `request-backlog.md` | The `## Feature decisions` table is written by the `feature-ledger` skill. |
| Active feature designs (Know / Notice / Do) | `plan/<feature>.md` | `morning-brief.md`, `journeys.md`, `Memory/memory.md` §20 (backfill), plus proposed `desktop-sessions.md`, `domain-agents.md`. Header: status, date, proposed or approved. Cite `ARCHITECTURE.md` sections, don't copy them. |
| **Memory plan (single)** | `plan/Memory/memory.md` | Memory design lives in `plan/Memory/memory.md` (§9 export, §17 Vault, §18 engine). Execution lives in `apps/memory/upgrade/`. Folder guide: `plan/Memory/CLAUDE.md`. Historical research only in `plan/Memory/_archive/`. |
| Service intake & cases menu | `services/` | `intake.md`, `cases.md` (plus `services/<shops|service>/<category>/`). Follow `services/intake.md`. Never write a case into `PLAN.md`. |
| Consolidated connector architecture, 40-source capability matrix, priority scores, and WhatsApp evaluation | `connectors/README.md` | Single consolidated reference; split files archived in `archive/connectors/`. |
| API catalogs, source registers, ranking plans, fine ontology | `references/` | `api-catalog.md`, `reading-source-register.md`, `recommender-plan.md`, `residence-ontology-tree.md`. Lookup material, not decisions. |
| Research inputs | `Researches/` | `CLAUDE.md`, `contest.md`. Memory research moved → `plan/Memory/` (see stub `memory-research-MOVED.md`). Input only; not canon until in `PLAN.md`. |
| Superseded or historical anything | `archive/` | Don't read unless asked. Scheme in `archive/CLAUDE.md`. (`superpowers/` retired 17 Nov: `residence-ontology-tree.md` moved to `references/`, remainder in `archive/superpowers/`.) |

**Which doc for which job:** use this table as the current routing guide. Entry specs and decisions live under `submissions/`. `docs-map.md` records the 17 Nov consolidation (historical).

## Rules
- New feature idea: ask first with the `feature-ledger` skill. Don't draft a design for a LATER or NEVER item.
- A design doc proposes; only `PLAN.md` + the ledger say what is IN. Mark a design `proposed` until the founder says implement.
- Old doc replaced? Archive superseded project docs under `docs/archive/` and record why in its guide (`archive/CLAUDE.md`). Don't delete. Preserve everything under `docs/plan/Memory/_archive/` and `design/references/quest/` in place.
