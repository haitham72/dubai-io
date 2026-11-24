# B-G — Codex: desktop importers (local LLM/agent sessions + "import Chrome history")

Paste below the line into **Codex**.

---

Your WP-E is merged on `memory` (Docker e2e). Thanks. Next: **desktop importers**. These run on the user's own PC with consent, the same way other apps offer "Import Chrome history" or read your local agent sessions. The mobile app can't do this; it's the desktop lane.

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` (note the new rule: never edit the `G:\Haitham\VsCode\contest` folder itself) and `prompts\SUBAGENTS.md`. **Your sub-agents use gpt-6.2 sol.** Suggested split: porter (session formats) · implementer (browser) · red-team (credential and denylist safety) · verifier.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpG -b mem-wpG memory
cd G:\Haitham\VsCode\contest-mem-wpG\apps\memory
```

**Design source:** `docs/plan/desktop-sessions.md` in your worktree. Use §1.1 (paths per agent), §2.2 (rules, **R1: never read, copy or forward other tools' credential files**) and §2.3 (sources verified 17 Nov; rows marked "verify" must be verified on fixtures, never assumed).

**You own only:** `src/temporal_memory/ingest/desktop/` (new) and `tests/test_desktop_ingest.py` + `tests/fixtures/desktop/`. **Don't edit `ingest/cli.py`**: Gemini is editing it (B-F). Expose functions; the integrator wires `tm import agent-sessions|browser` afterwards.

1. **`ingest/desktop/agent_sessions.py`:** `agent_session_records(owner, roots: dict[str, Path] | None = None, since=None) -> list[Record]`.
   - **Claude Code** `~\.claude\projects\<encoded-cwd>\<sessionId>.jsonl` and **Codex** `~\.codex\sessions\**\*.jsonl` first. Gemini CLI (`~\.gemini\tmp`), Copilot and Cursor only if you can confirm the format from a real **structure** (field names) on this PC without copying content. Otherwise leave a `# TODO verify format` stub that yields nothing.
   - Keep: session title, project (cwd basename, path redacted), timestamps, **the user's own prompts** (truncated), assistant final summaries (truncated). Drop: bulk tool outputs, file dumps, diffs.
   - **One record per session-day** (`source=agent:<tool>`) so they join the cross-source day packets.
   - **Secret redaction:** port `contest/scripts/extract_dev_sessions.py:26-40`, plus API-key, token, password and private-key patterns.
   - **R1 hard denylist:** never open `.credentials.json`, `auth.json`, `*token*`, `*.key`, `.env*`, `oauth*`, keychains. Don't follow symlinks out of a root, and cap file sizes.
2. **`ingest/desktop/browser.py`:** the "import browser history" consent flow for Chrome / Edge / Brave profiles.
   - `preview(profile_dir) -> {domain: visits}`: counts only, creates no records, for the consent screen.
   - `browser_records(owner, profile_dir, since=None, deny_domains=…) -> list[Record]`: copy `History` and `Bookmarks` to a temp file (Chrome locks them), and read only `urls` / `visits` (url, title, visit time) and the Bookmarks JSON.
   - **Never open** `Cookies`, `Login Data`, `Web Data`, `Network\*`, `Local State` keys, or session/token stores. This is history sharing, not account access.
   - Apply a default domain denylist (banking, health, adult, government portals; configurable) **before** any record is made.
   - Emit **aggregated interest records** per day (domain/topic counts), not per-page facts. YouTube watch URLs → per-day channel/topic counts (same rule as B-F: never per-video facts; sensitive topics held back).
3. **Tests** (synthetic only): fake session folders with jsonl, and a tiny SQLite `History` built in the test with the Chrome table subset. Must cover:
   - credential files present in the folder are **never opened** (assert with a monkeypatched `open`);
   - secrets in prompts are redacted;
   - a symlink escape is refused;
   - denylisted domains never appear;
   - `preview` creates no records;
   - a locked or missing History file gives a clear error.

**Report:** branch, counts, which agent formats you confirmed vs stubbed, contract requests.
