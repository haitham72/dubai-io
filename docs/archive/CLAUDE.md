# docs/archive/ — historical, not authoritative

**Do not read these unless the founder asks.** Every rule, contract, and decision still in force was rescued into the live docs before each archive pass — start from root `CLAUDE.md` → `PLAN.md` → `ARCHITECTURE.md` → `docs/status.md` → `apps/api/app/lab/CLAUDE.md`.

## Archive passes

- **Round 1 (9 Nov 2026, `docs/archive/docs-map-2026-11-09.md`):** Archived superseded directions (visitor companion, native iOS, Today sheet / Tasks Home / domains / UI-bot shells, the community track, the 22–23 Oct gate ledger). Includes `root/` (former top-level `handoff.md`, `handoff-ios.md`, `cursor-plan.md`), `plan/` (`calls-services-panels.md`, `dashboard.md`, `domains.md`, `ios-upgrade.md`, `review-prompt.md`, `unified-app-design.md`, `website-rebuild.md`), `references/` (22 Oct review docs, community plans, `redesign.md`, `visuals-libraries.md`, etc.), `superpowers/plans/` (23 Oct–2 Nov plans), `Researches/` (`CLAUDE-2026-11-09-quest-direction.md`, phone-notification research, `Dubai-io_product evolution.md`), and top-level `implementation-plan.md`, `user-app-review-guide.md`.
- **Round 2 (17 Nov 2026, `docs/docs-map.md`):** Consolidated split specs and retired `docs/superpowers/`:
  - `docs-map-2026-11-09.md` — former 9 Nov `docs/docs-map.md`, superseded by the 17 Nov consolidation map.
  - `connectors/` — `architecture.md`, `capability-matrix.md`, `prioritization.md`, `whatsapp-evolution.md` (merged into `docs/connectors/README.md`).
  - `superpowers/plans/2026-10-23-temporal-memory.md` (superseded by 16 Nov `PLAN.md` §2 Postgres memory service) and `superpowers/specs/` (`2026-11-02-demo-journeys.md`, `2026-11-02-demo-resident.md`, `2026-11-02-residence-companion-design.md` — rescued into `docs/plan/journeys.md`).
  - `plan/agent-session-history.md` & `plan/desktop-llm-sessions.md` (merged into `docs/plan/desktop-sessions.md`).
  - `Researches/persocial-intake.md` (separate, deprioritised Persocial project).
  - `references/v3-higgsfield-README.md` (former `design/references/v3-higgsfield/README.md`, folded into `design/CLAUDE.md` and `design/29-10-2026/INDEX.md`).
  - The 17 Nov Hark (`quest-feed` / `BUILD_REPORT.md`) prototype was superseded directly into `docs/plan/morning-brief.md` §8 (`ScopeGuard`, 6 metadata-first card generators, Bayesian feedback smoothing), `apps/api/app/lab/CLAUDE.md` (`.ics`/`.vcf` Takeout parsers, `forget_rules` ingestion blocklist, `content_hash` dedupe, `superseded_by`), and `docs/Researches/memory-research-2026-11.md` §7 (Hindsight 1.2.1 live benchmark notes), and `docs/references/Hark/` was removed.

Earlier versions of docs rewritten in place (`CLAUDE.md`, `PLAN.md`, `ARCHITECTURE.md`, `README.md`, `docs/status.md`, `docs/request-backlog.md`): `git show main:<path>`.

Never cite an archived doc as current. Never move a doc back without the founder's approval.
