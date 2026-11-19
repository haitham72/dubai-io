# docs/plan/ — Active System & Feature Plans

This directory contains the active design specifications across the system's core capabilities.

---

## Plan Directory Map

| File / Folder | Role & Scope | Authority |
|---|---|---|
| **[Memory/](file:///g:/Haitham/VsCode/contest/docs/plan/Memory/)** | **Memory Data Engine & Architecture:** Contains the single authoritative memory specification ([memory.md](file:///g:/Haitham/VsCode/contest/docs/plan/Memory/memory.md)), defining the 10 Postgres tables, schema, retrieval pipeline, and §12 Adaptive Knowledge Base export tree. Its `_archive/` subfolder holds benchmark datasets (`quest-memory-export/` and `hindsight-kb-export/`). | Single Source of Truth for Memory Data Layer |
| **[backfill-agent.md](file:///g:/Haitham/VsCode/contest/docs/plan/backfill-agent.md)** | **Historical Ingestion Agent:** Specifies the multi-tier model routing (Rules → Local Qwen Classifier → Hindsight → Frontier Lead Orchestrator), durable SQLite `backfill_jobs` queue, human review (`blocked`) state machine, and testable "done" contracts for ingesting multi-year chat and email exports. | Locked Design (`PLAN.md` §2, P2-7) |
| **[morning-brief.md](file:///g:/Haitham/VsCode/contest/docs/plan/morning-brief.md)** | **Notice Cards & Morning Brief:** Proactive daily digest, 6 card generators, card lifecycle state machine (`new → seen → actioned → dismissed → resolved`), ScopeGuard privacy barriers, and query rewriters. | Active Feature Design |
| **[two-tower-recommender.md](file:///g:/Haitham/VsCode/contest/docs/plan/two-tower-recommender.md)** | **Two-Tower Recommender & News Pool:** Focus for Contest Entry 1 (Best Personal AI Agent). User Tower (YouTube watch history, dev sessions, memories) cross-matched with Shared News Pool via hybrid search + 10 targeted daily searches (Tavily, Google, NaukriGulf, LinkedIn). | Active Feature Design |
| **[data-ingestion-runbook.md](file:///g:/Haitham/VsCode/contest/docs/plan/data-ingestion-runbook.md)** | **Multi-Source Data Ingestion Runbook:** Operational guide for Gmail live sync (50k tokens cap), YouTube 4-feed signals, local Chrome/Edge SQLite watch history extraction (0.3s), and Claude/Codex dev sessions. | Operational Playbook |
| **[domain-agents.md](file:///g:/Haitham/VsCode/contest/docs/plan/domain-agents.md)** | **Domain Agents & Multi-Agent Mesh:** Specialization boundaries and orchestrator routing across domains (finance, travel, lifestyle, communication). | Proposed Draft |
| **[desktop-sessions.md](file:///g:/Haitham/VsCode/contest/docs/plan/desktop-sessions.md)** | **Desktop Companion App & Sessions:** Window tracking, active session recording, and opt-in desktop context memory capture. | Active Feature Design |
| **[journeys.md](file:///g:/Haitham/VsCode/contest/docs/plan/journeys.md)** | **End-to-End User Journeys:** Master user flow walkthroughs, demo scenarios, and cross-feature integration cases. | Active Product Design |

---

## Rules for Agents

1. **Memory questions:** Go to `Memory/memory.md`. Do not invent secondary memory plans.
2. **Ingestion / Backfill questions:** Go to `backfill-agent.md`. It governs *how* data enters memory via autonomous workers; it does not alter the underlying memory schema in `Memory/memory.md`.
3. **Card generation / UI feeds:** Go to `morning-brief.md`.
4. **Authority:** Repo root `PLAN.md` §2 and `CLAUDE.md` govern all plans here.
