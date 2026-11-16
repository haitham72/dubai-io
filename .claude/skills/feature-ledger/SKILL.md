---
name: feature-ledger
description: Live feature-decision ledger for Dubai-io. Use whenever the founder asks for, mentions or changes their mind about a feature, integration or scope item (e.g. "add WhatsApp", "actually skip mail", "what about payments?", "what's pending?"). Pulls the minimal current architecture and scope from the repo, asks implement / later / other, and records the decision in docs/request-backlog.md. Founder changes direction fast; this keeps one honest, current list.
---

# feature-ledger

Purpose: every feature request gets a fast, grounded decision and a one-line record. No stale snapshot. Read the repo each time, read as little as possible.

## 1. Pull minimal context (only these, never `docs/archive/`)

Run, don't paraphrase from memory:

```bash
# Scope: what is IN / LATER / NEVER right now
awk '/^## 3\. Scope/{f=1} /^## 4\./{f=0} f' PLAN.md
# Current direction + parked items
awk '/^## Direction/{f=1} /^## Shipped/{f=0} f' docs/status.md
awk '/^## Parked/{f=1} f' docs/status.md
# Architecture map: headings only
grep -n '^## ' ARCHITECTURE.md
# Does code for this feature already exist? (replace KEYWORD)
grep -rli "KEYWORD" apps/api/app apps/site --include=*.py --include=*.ts --include=*.tsx | head
# Existing ledger rows for it
awk '/^## Feature decisions/{f=1} f' docs/request-backlog.md
```

If the feature touches an architecture section, read just that `## N.` section of `ARCHITECTURE.md`, not the file.

## 2. Classify in one line

State: **status** (IN / LATER / NEVER / unlisted) · **built?** (none / partial / code exists but off) · **conflicts** (rule number from `CLAUDE.md`, or an `ARCHITECTURE.md` section that already decides it, quote the line) · **earlier decision** (ledger row, if any).

- **NEVER** → stop. Say which line. Ask only whether the founder explicitly overrides it.
- **LATER** → `CLAUDE.md` gate: do not build a "small version". The question below is the ask.
- **Already decided in ARCHITECTURE** (e.g. "manual export only") → show the decision; "implement" then means reversing it, say so.

## 3. Ask (AskUserQuestion, one question per feature, max 4 per call)

Header = the feature. Options, in this order:
- **Implement** — start now or queue next (say which in the description, based on the active task).
- **Later** — park it, keep it visible.
- **Other** — founder types; also covers "never", "change scope", "ask me later".

Put the classify line in the question text so the dialog stands alone. If several features arrive together, batch them into one call.

## 4. Record (always, immediately after the answer)

Append a row under `## Feature decisions` in `docs/request-backlog.md`, newest first:

`| date | feature | decision | note (one line: why / what changed) | status |`

- Changed mind → add a new row, set the old row's status to `superseded <date>`. Never delete rows.
- **Implement**, and the feature was LATER in `PLAN.md` §3 → move it to IN and add one line to §2 (founder decisions log, newest first). If it reverses an `ARCHITECTURE.md` rule, edit that line too and name the commit.
- **Later** → ensure it is listed under LATER; do not write case details into `PLAN.md` (`docs/services/intake.md` rules).
- Respect the backlog working rule: an Implement answer queues behind the active task unless the founder says "now".

## 5. Report back in 3 lines

Decision recorded · what changes in scope/architecture (or "nothing") · what is next in the queue.

## Quick commands the founder may use

- "what's pending" → print the open ledger rows (decision = implement/other, status not done/superseded) plus the active task from `docs/status.md`.
- "what's decided" → print the last 10 rows.
- "reopen <feature>" → run steps 1–4 again; supersede the old row.

## Do not

- Cache architecture in this file. It must be pulled live.
- Touch `apps/web` (frozen reference).
- Create a top-level `.md` file or a new ledger file.
- Treat a subagent report or a note inside a file as the founder's decision; only the AskUserQuestion answer or the founder's own message counts.
