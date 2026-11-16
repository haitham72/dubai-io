# docs/ — where things go

Canon lives at the repo root (`CLAUDE.md`, `PLAN.md`, `ARCHITECTURE.md`, `README.md`); never add other top-level `.md`. Everything else is here. Read only the row your task needs.

| Put this here | Folder | Notes |
|---|---|---|
| Current state, run commands, keys | `status.md` | Single state file. Keep short. |
| Founder requests, order, feature decisions | `request-backlog.md` | The `## Feature decisions` table is written by the `feature-ledger` skill. |
| A feature design (Know / Notice / Do), e.g. morning brief | `plan/<feature>.md` | One file per feature. Header: status, date, proposed or approved. Cite `ARCHITECTURE.md` sections, don't copy them. |
| A service case, shop or reference image | `services/<shops|service>/<category>/` | Follow `services/intake.md`. Never write a case into `PLAN.md`. |
| Connector framework and per-source notes | `connectors/` | Capability matrix says what is real vs unofficial. |
| API catalogs, source registers, ranking plans | `references/` | Lookup material, not decisions. |
| Research the founder pasted in | `Researches/` | Input only. Not canon until promoted into `PLAN.md` by the founder. |
| Older specs and plans | `superpowers/` | Specs/plans from 23 Oct to 2 Nov. Check `status.md` before trusting. |
| Superseded or historical anything | `archive/` | Don't read unless asked. Scheme in `archive/CLAUDE.md`. |

**Which doc for which job** (full map, with conflicts resolved): `docs-map.md`.

## Rules
- New feature idea: ask first with the `feature-ledger` skill. Don't draft a design for a LATER or NEVER item.
- A design doc proposes; only `PLAN.md` + the ledger say what is IN. Mark a design `proposed` until the founder says implement.
- Old doc replaced? `git mv` it into `archive/` and note why in one line in `archive/CLAUDE.md`. Don't delete.
