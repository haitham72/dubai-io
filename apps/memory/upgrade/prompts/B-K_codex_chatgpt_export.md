# B-K — Codex: ChatGPT data-export importer (small, one source)

Paste below the line into **Codex**.

---

Your B-G (desktop importers) is merged on `memory`: 250 tests green. Next, one small importer: a user's **ChatGPT data export** (Settings → Data controls → Export). A person's own AI prompts are one of the strongest memory signals.

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md`. **Sub-agents: gpt-6.2 sol**, at most 1–2 (porter + verifier). Keep it small.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpK -b mem-wpK memory
cd G:\Haitham\VsCode\contest-mem-wpK\apps\memory
```

**You own only** `src/temporal_memory/ingest/ai_exports.py` and `tests/test_ai_exports.py` + `tests/fixtures/ai_exports/`. **Don't edit `ingest/cli.py`** (the integrator wires `tm import chatgpt` after).

1. `chatgpt_records(owner, path, since=None) -> list[Record]`. `path` is the export `.zip` or its `conversations.json`. Verify the shape (conversations with `title`, `create_time`, and a `mapping` of message nodes with `author.role`, `content.parts`, `create_time`) from the documented export format; your synthetic fixture mimics it.
2. Keep **the user's own prompts** and conversation titles, truncated. Keep assistant text only as a ≤ 300-char final summary per conversation. Drop attachments, code dumps and system/tool messages. Redact with `ingest/desktop/_redact.safe_text`.
3. **One record per conversation-day**, `source=ai:chatgpt`, so they join the cross-source day packets. `content_hash` dedupe makes re-importing the same export a no-op.
4. **Tests:** happy path, re-import is a no-op, `since` filters, secrets are redacted, a malformed or zip-bomb export is refused.

**Done when** `python -m pytest -q` is green. Commit on `mem-wpK` and report: branch and counts.
