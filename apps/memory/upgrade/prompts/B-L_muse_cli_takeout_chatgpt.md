# B-L — Muse: Wire `tm import takeout|chatgpt` CLI + Full `memory` Suite + Scoped Drive Takeout Plan Check

Paste below the line into **Muse**.

---

Branches `mem-wpH` (DB pool fix), `mem-wpI` (`cli.py` desktop wiring), `mem-wpJ` (`ingest/takeout.py`), and `mem-wpK` (`ingest/ai_exports.py`) are merged on `memory`. Now finish the CLI integration seam and verify the whole engine green:

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and `prompts\SUBAGENTS.md`. **Sub-agents: Muse 1.3 Contributor only (never Wonder).**
- **Never edit `G:\Haitham\VsCode\contest`** (`main`), **never touch `apps/web`**, `models.py`, `privacy/forget.py`.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpL -b mem-wpL memory
cd G:\Haitham\VsCode\contest-mem-wpL\apps\memory
```

### Strictly Owned Paths
- `apps/memory/src/temporal_memory/ingest/cli.py`
- `apps/memory/src/temporal_memory/ingest/__init__.py`
- `apps/memory/tests/test_cli_takeout_chatgpt.py` (new)

### Deliverables
1. Wire `tm import takeout <zip_or_dir> --owner <id> [--since YYYY-MM-DD]` in `ingest/cli.py`:
   - Calls `temporal_memory.ingest.takeout.takeout_records(args.owner, target_path, since=args.since)` and routes through `ingest_records(db, args.owner, records, split=not args.no_split, apply_triage=False)`.
   - Handles `TakeoutError` cleanly (exits non-zero with clear error message, never stack trace).
2. Wire `tm import chatgpt <zip_or_json> --owner <id> [--since YYYY-MM-DD]` in `ingest/cli.py`:
   - Calls `temporal_memory.ingest.ai_exports.chatgpt_records(args.owner, target_path, since=args.since)` and routes through `ingest_records(...)`.
   - Handles malformed/zip-bomb `ValueError` cleanly (exits non-zero with clear message).
3. Export `takeout_records`, `TakeoutError`, and `chatgpt_records` from `ingest/__init__.py`.
4. Tests (`tests/test_cli_takeout_chatgpt.py`):
   - Synthetic Takeout `.zip` end-to-end through `cli.main(["import", "takeout", ...])` -> verifies Postgres records + `content_hash` re-import dedupe + zip-bomb/traversal non-zero exit + Rule-9 holdback;
   - Synthetic ChatGPT `conversations.json` / `.zip` through `cli.main(["import", "chatgpt", ...])` -> verifies Postgres records + `since` filter + re-import dedupe + malformed export non-zero exit;
   - Cross-check all existing `tm import` kinds (`whatsapp`, `gmail-json`, `youtube`, `dev-sessions`, `temporal-note`, `agent-sessions`, `browser`, `takeout`, `chatgpt`) + `tm export --help`.
5. Run the **full** `pytest -q` suite (and if Docker is up, verify `TM_RUN_E2E=1 TM_E2E_GOLD_DIR=G:\Haitham\lab-data\memory-bakeoff\gold pytest -q -m e2e` too).

**Done when** `pytest -q` is 100% green and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes. Commit on `mem-wpL` and report: branch, unit counts (and e2e counts if run), any gaps.
