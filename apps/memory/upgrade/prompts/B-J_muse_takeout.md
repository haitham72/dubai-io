# B-J — Muse: Google Takeout importer (YouTube watch history · Chrome history · Gemini Apps activity)

Paste below the line into **Muse**.

---

For UAE / rest-of-world users there's no API for YouTube watch history. The path is a **Google Takeout export**, uploaded once or scheduled to Drive (see `docs/plan/onboarding-youtube-sources.md` on branch `memory`). Build the memory-side importer for that zip. Privacy is the hard part, which is why it's yours.

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and `prompts\SUBAGENTS.md`. **Sub-agents: Muse 1.3 Contributor only (never Wonder).** Suggested: porter + red-team + verifier.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpJ -b mem-wpJ memory
cd G:\Haitham\VsCode\contest-mem-wpJ\apps\memory
```

**You own only** `src/temporal_memory/ingest/takeout.py` and `tests/test_takeout.py` + `tests/fixtures/takeout/`. **Don't edit `ingest/cli.py`** (Cursor owns it this round; the integrator wires `tm import takeout` after).

1. `takeout_records(owner, path, since=None) -> list[Record]`. `path` is a Takeout `.zip` **or** an extracted folder. Read only:
   - **YouTube watch history** `Takeout/YouTube and YouTube Music/history/watch-history.json` (+ `search-history.json`);
   - **Chrome history** `Takeout/Chrome/BrowserHistory.json` (`"Browser History": [{title, url, time_usec, …}]`);
   - **Gemini Apps activity** `Takeout/My Activity/Gemini Apps/MyActivity.json`.

   Verify the field shapes against Google's documented Takeout structure; your synthetic fixtures mimic it. **Ignore every other folder in the zip.**
2. **Reuse, don't duplicate:** the YouTube per-day interest aggregation from `ingest/youtube.py` (B-F) and the domain denylist and aggregation from `ingest/desktop/browser.py` (B-G). YouTube and Chrome produce **aggregated daily interest records**, never per-video or per-page facts. Gemini Apps prompts are kept as the user's own prompts (truncated, redacted with `ingest/desktop/_redact.safe_text`), one record per day.
3. **Rule 9 red-team:** faith, health, politics and sexuality topics in watch, search or browse history are **held back**, never inferred. Third-party names in titles aren't promoted. Zip-bomb and path-traversal entries are refused, and there's a size cap.
4. **Tests** built from a synthetic zip created in the test. Must cover: missing parts are OK; sensitive topics are held; denylisted domains never appear; a malicious zip is refused; `since` filters.

**Done when** `python -m pytest -q` is green. Commit on `mem-wpJ` and report: branch, counts, the shapes you verified.
