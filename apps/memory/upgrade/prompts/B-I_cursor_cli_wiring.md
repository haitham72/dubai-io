# B-I — Cursor: wire the desktop importers into the `tm` CLI (small)

Paste below the line into **Cursor**.

---

You're joining a multi-agent build of the Dubai-io memory engine (`apps/memory/`, branch `memory`, Dubai-io repo). Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` first. Key rules:
- only files under `apps/memory/`;
- never edit the folder `G:\Haitham\VsCode\contest` itself (that's `main`);
- synthetic test data only;
- you commit only on your own branch.

Sub-agents: optional for this small task; if you use them, keep to 1–2 on Cursor's default/fast model.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpI -b mem-wpI memory
cd G:\Haitham\VsCode\contest-mem-wpI\apps\memory
```

**You own only** `src/temporal_memory/ingest/cli.py` and `tests/test_cli_desktop.py`. You're the **single owner of `cli.py`** in this round; other agents only expose functions.

1. Add `tm import agent-sessions [ROOT] --owner <id> [--since YYYY-MM-DD] [--tool claude-code|codex|…]`. It calls `temporal_memory.ingest.desktop.agent_sessions.agent_session_records(...)`. With no ROOT it uses the defaults that function already knows.
2. Add `tm import browser <PROFILE_DIR> --owner <id> [--since …] [--preview]`. `--preview` prints `desktop.browser.preview()` domain counts and **creates nothing**. Without it, call `browser_records(...)`.
3. Both go through the same pipeline as the other kinds (`ingest_records` → `content_hash` dedupe → forget rules → `import.split`, unless `--no-split`).
4. **Tests** (synthetic fixtures already in `tests/fixtures/desktop/`): happy paths for both, `--preview` writes 0 records, and a missing profile dir gives a clear error.

**Done when** `python -m pytest -q` is green. Commit on `mem-wpI` and report: branch and counts.
