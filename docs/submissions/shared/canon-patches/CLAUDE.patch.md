# Canon Patch Proposal: `CLAUDE.md`

- **Target file:** `CLAUDE.md` (currently 81 lines on `contest-shared` `206b9ff`; 69 lines on `origin/main` `f016856`)
- **Affected line ranges:** lines `48-61` (`## Repo layout`, reconciling `origin/memory`'s line `53`) and lines `71-81` (`## Contest submissions`, already appended on `contest-shared`)
- **Status:** **PROPOSAL ONLY — DO NOT APPLY ON `contest-shared`.**
- **When to apply:** After `memory`, `desktop` and `ios` are merged into `main`. **D16 (24 Nov): all branches merge into `main` after their gates**, so the entry and shared paths below become normal `main` folders.
- **Merge-conflict notes:**
  - `origin/memory` (`fc2e24a`) and `origin/desktop` (`d07ee53`) insert `+apps/memory/       temporal-memory engine (own service + Docker stack; branch \`memory\`; guide apps/memory/CLAUDE.md)` at line `53` inside `## Repo layout` (commit `9444421`).
  - `contest-shared` (`206b9ff`) appends `## Contest submissions` at lines `70-81` (18 lines below line `53`, so no hunk overlap).
  - If `main` (after merging `memory`, `desktop`, `ios`) also appended lines at EOF of `CLAUDE.md`, `docs/submissions/CLAUDE.md:29` requires keeping **both sides**.
  - Preserves `CLAUDE.md:46` strictly: max 4 top-level `*.md` files (`CLAUDE.md`, `PLAN.md`, `ARCHITECTURE.md`, `README.md`), never creating `HANDOFF.md`.

---

## Hunk 1 — `## Repo layout` Reconciliation (`CLAUDE.md:48-61`)

**Rationale:** Reconciles `origin/memory`'s `apps/memory/` layout line (`9444421`) with Entry 1's desktop/mobile clients and Entries 2 & 3 + shared B0 paths without touching rules 1–10 or gates.

```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -50,9 +50,15 @@
 ```
 apps/api/          FastAPI + LangGraph backend, tests/
 apps/api/app/lab/  Headless Know / Notice / Do pipeline (extraction skills: chat, email, ide_session)
+apps/api/app/identity/       Shared verified user_id, per-app sessions, WS tickets (contest-shared)
+apps/api/app/memory_bridge/  Shared client of temporal_note with consent & Forget propagation (contest-shared)
+apps/memory/       temporal-memory engine (own service + Docker stack; guide apps/memory/CLAUDE.md; D5)
 apps/site/         THE app: one React codebase → website, desktop app (Tauri/Electron), iOS/Android (Capacitor); UI paused 9 Nov
+apps/desktop/      Entry 1 Electron desktop client (from PC2 main)
+apps/mobile/       Entry 1 Expo Go mobile client + packages/design-tokens (from PC2 main)
+apps/community/    Entry 2 Dubai-io Community web app (societal; no P2P messaging, D3)
+apps/messenger/    Entry 3 Messenger client (business; rebranded founder redesign 6b45ba4, D1/D3/D4)
 apps/web/          Original mobile app PWA — FROZEN, the reference (tag mobile-pwa-baseline-2026-10-23), embedded at /?devices
 apps/ios/          Native SwiftUI client — STOPPED 23 Oct (history only)
```

---

## Hunk 2 — Post-Merge One-Section `## Contest submissions` (`CLAUDE.md:71-81`)

**Rationale:** Updates the existing `contest-shared` EOF section post-merge to link the approved shared contract (`SHARED_MEMORY_CROSS_APP_CONTRACT.md`) and `founder-decisions.md` (D1–D7) cleanly, while preserving the zero-conflict / non-merge-into-main guardrails for ongoing entry work.

```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -71,11 +71,11 @@
 ## Contest submissions (branches `contest-shared`, `societal`, `business`; founder, 23 Nov 2026)
 
-`main` is Entry 1, **Best Personal AI Agent** (Quest / Dubai-io). Two more entries share one verified `user_id` and one memory service with it. Each lives on its own long-lived branch, built by external agents (Cursor, Muse, Codex, Antigravity) from the briefs on that branch: plan first, then build, with subagents.
+`main` hosts Entry 1, **Best Personal AI Agent** (Quest / Dubai-io), plus shared `identity/` and `memory_bridge/` once Gate S merges. Entries 2 and 3 share one verified `user_id` and one `temporal_note` memory service (`apps/memory/`, D5) under `docs/submissions/shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md`. Each entry still builds on its own branch from its briefs: plan first, then build, with subagents.
 
 | Track | Entry | Branch | Folder |
 |---|---|---|---|
-| Shared base: identity, memory bridge, cross-app contract | — | `contest-shared` | `docs/submissions/shared/` |
-| Best Societal AI Agent | Dubai-io Community | `societal` | `docs/submissions/community/` |
-| Best Business AI Agent | Messenger (WhatsApp-like; name pending) | `business` | `docs/submissions/messenger/` |
+| Shared base: identity, memory bridge, cross-app contract | — | `contest-shared` | `docs/submissions/shared/` |
+| Best Societal AI Agent | Dubai-io Community (no P2P messaging, D3) | `societal` | `docs/submissions/community/` |
+| Best Business AI Agent | Messenger *(working name; O2 pending; all P2P messaging, D1/D3/D4/D6/D7)* | `business` | `docs/submissions/messenger/` |
 
-On those branches, read `docs/submissions/CLAUDE.md` first: the branch and merge protocol, owned vs read-only paths, phase gates, and the Messenger's IP and naming gate. Founder answers of 23 Nov: `docs/submissions/shared/founder-decisions.md`. **Never commit to or push `main` from these branches, and never merge them into `main`.** The other PC's `main` is ahead of `origin/main`, so it comes in by merge (into `contest-shared` first) only after it is pushed. Rules 1–10 apply to every entry.
+On those branches, read `docs/submissions/CLAUDE.md` and `docs/submissions/shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md` first: branch/merge protocol, owned vs read-only paths, phase gates, and the Messenger IP/naming gate. Founder rulings: `docs/submissions/shared/founder-decisions.md` (D1–D7). **Never commit to or push `main` from entry branches, and never merge entry branches into `main` without founder sign-off.** Rules 1–10 apply to every entry.
```
