# U1b handoff: started by a previous agent (quota ran out, 24 Nov)

**Claude's note (24 Nov):** the worktree `G:\Haitham\VsCode\contest-mem-wpU1b` (branch `mem-wpU1b`) had no commits, so Claude **fast-forwarded it from `e05371f` to `memory` @ `267b0cf`**. It now contains U0a (provenance / `user_confirmed_at` / `closeness_suggested` / `link_evidence` columns, the migrations runner) and U1a (bridge + Forget on Postgres). Its untracked `baseline_gold*.log` files are kept. The baseline numbers below were measured on `e05371f`, so rerun the suite (now 348 passed, 8 skipped) before relying on them.

---

## The previous agent's handoff (verbatim)

**Where**
- Worktree: `G:\Haitham\VsCode\contest-mem-wpU1b`, branch `mem-wpU1b`. Created; nothing committed.
- Task spec: `prompts\U1b_applier_leaks_and_provenance.md`. Also read `B0_common_rules.md`, `TN_UPGRADE_PLAN.md` §2 R3 / R5, §2b B2, §6, §7 D-c, Codex 01 / 05, Gemini F02 / F05 / F11, root rule 9.
- Env ready: `.venv` (Python 3.13), `pip install -e ".[dev,cloud,mcp]"` done. Docker stack already up on :5442 / :5682 / :6390.

**Done**
- Baseline green: `pytest -q tests --ignore=tests/e2e` → 335 passed; gold-month e2e (`TM_RUN_E2E=1`, `TM_E2E_GOLD_DIR`=gold dir) → 1 passed in 92 s. Logs: `apps\memory\baseline_gold*.log` in the worktree.
- Read the owned code: `core/applier.py`, `privacy/policy.py`, `privacy/sensitive.py`, `ingest/triage.py`, plus `tests/e2e/test_gold_month.py`, `oracle_runner.py`, the gold ledger.

**Key analysis (no code changed yet)**
- `f039` is falsely quarantined as `family_third_party`. `f045` (g097) and `f109` (g149) are dropped by ingest triage as noise email (sender `noreply@` / `news@`, unsubscribe / weekly-digest patterns).
- Gold: 110 facts, 8 sensitive (`f018`–`f025`), 102 clean. The e2e currently **masks** 5 gate false positives + 2 triage false positives through `CANONICAL_QUARANTINES` and `TRIAGED_PUBLIC_FACTS`. Fixing the 3 means: remove `f039` from that quarantine map, empty `TRIAGED_PUBLIC_FACTS`, and expect the record count to go 1010 → 1012.
- The remaining accepted gate disagreements are `f017`, `f049`, `f061` and `f084` (deliberately out of scope per the prompt).
- Main applier work still open:
  - evidence-gated creation of entities, aliases and links;
  - per-link `link_evidence`;
  - stored provenance (`inferred` vs `user_supplied` + `user_confirmed_at`);
  - auto-promotion that changes status only;
  - D-c `closeness_suggested` (never `closeness_tier`; no family / health / faith inputs);
  - late-chain updates to `superseded` / `ended` targets.

**Next:** implement the owned files + `test_no_orphan_leaks.py`, run the full suite incl. Postgres / e2e, commit on `mem-wpU1b`, and report the branch, files, test counts, and the gate false positives / true positives before → after.

*Note: the audit-style sub-agents it had just launched were cancelled with no results; no audit file was written.*
