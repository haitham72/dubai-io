# Mirsal log

## 23 Nov 2026 — P1 (Cursor)

Checked the founder spec, the Community inbox and memory sections, `PLAN.md` §1–§5 and §7, `ARCHITECTURE.md` §2, §3, §7, §9 and §11, `actions.py`, `auth.py`, `communities.py`, and `origin/memory:apps/memory/src/temporal_memory/models.py` (via `git show`, branch not checked out). Audited `haitham72/Mirsal-redesign` at `6b45ba4` without copying it and without switching `main`.

Reran `python agents/run.py test` in `D:\Vscode\_scratch\mirsal-p1-tests`. Result: **200 passed, 1 skipped** (`tests/test_store.py:20`, no local Redis). The README’s 169 and 10 were not reproduced.

Wrote `ip-and-baseline.md`, `audit.md`, `IMPLEMENTATION_GAP_MATRIX.md`, `DELIVERY_ROADMAP.md`, `identity-memory-needs.md`, `demo-script.md`, `sources.md`, `open-questions.md`, and this log. M0 recommendation is **clean-room**. No application code.

Top risks:

1. Clean-room plus Gate S means the visual POC cannot be imported, and the 18 Dec package is tight if shared identity slips.
2. There is still no verified `user_id`. Cross-app “same person” must not be shown.
3. The spec’s compact Updates tray and commit `6b45ba4` disagree. A later reuse decision is blocked until the founder picks one.
4. Community already has per-owner `chat_*` tables. A second full messenger on that side would split the product.
5. `workspace.task.create` is not registered. The business tap has nowhere to go until `MS-B5`, and a seeded thread is not the two-user test.

## 23 Nov 2026 — P1 verification (Codex)

Cross-checked Cursor’s nine-file P1 commit and preserved its slice order. Reproduced 200 agent passes with one Redis skip, all 145 offline routing eval items, 40 provider-mock server tests, TypeScript and four photo-window cases. The sandbox prevented a Vite build. Verified the source SHA on GitHub and added the organizer’s originality constraint to M0. Reconciled chat ownership with verified B0 identity and source deletion with memory revocation. The demo calendar now agrees with the approval payload.
