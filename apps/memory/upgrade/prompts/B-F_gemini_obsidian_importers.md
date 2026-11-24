# B-F — Gemini: export CLI · importers for the founder's 4 extra sources · `model_observed`

Paste below the line into **Gemini**.

---

Your WP-A, WP-B and WP-D are merged on branch `memory` (Dubai-io repo, `apps/memory/`): **160 tests green**. Next task, in the new layout:

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpF -b mem-wpF memory
cd G:\Haitham\VsCode\contest-mem-wpF\apps\memory
```

Rules: `prompts/B0_common_rules.md`. Sub-agents: `prompts/SUBAGENTS.md`. **Your sub-agents use a lower/cheaper Gemini tier, not Neo.** Suggested split: porter (importers) · implementer (export CLI + model_observed) · red-team (privacy on YouTube) · verifier. Don't touch `privacy/`, `Dockerfile`, `docker-compose.yml` or `tests/e2e/` (Codex is working there).

## 1. Export CLI only (no Obsidian work)

The founder doesn't need Obsidian compatibility; the Quest-style export stays as it is. Only add the command `tm export --owner <id> --out <dir>` (refuse a `<dir>` inside the repo) that writes the existing `export_md.render()` tree to disk. One test: it writes the files and refuses an in-repo path.

## 2. Importers for the founder's real sources (`ingest/`)

The real files exist; **don't open or copy them into tests**. Their shapes (field names only):

| Source | Path (founder's machine) | Shape |
|---|---|---|
| YouTube history | `g:\Haitham\VsCode\contest\data\sync\youtube_watch_history.json` | `list[{title, url, channel, watched_at, source}]` (500) |
| Gmail export | `…\data\sync\gmail_latest.json` | `list[{id, thread_id, date, from, subject, snippet, internal_date, est_tokens}]` (250) |
| Dev sessions | `…\data\sync\dev_sessions.json` | `{extracted_at, claude_sessions:[{source, title, project, cwd, git_branch, session_file, timestamp, prompts_sample, total_prompts}], recent_git_commits:[{hash, author, date, message}]}` |
| temporal_note | `C:\Users\h.ibrahim\Documents\Claude\Projects\temporal_note\` | `timeline.md`: fenced YAML blocks (`date, incident, thread, location, severity, emotion, entities[], links[], tags[], period?, retrospective?, note?`) each followed by a prose paragraph with `[[wikilinks]]`. `ENTITY_ALIASES.md`: `## \`Name\`` sections with `**Canonical name:**`, `**Role:**`, `**Also referred to as:** "a," "b"` |

Add `tm import youtube|gmail-json|dev-sessions|temporal-note <path> --owner <id>`. Requirements:

- **temporal_note `ENTITY_ALIASES.md` → seed entities + aliases as `user_supplied`** (the founder wrote them). This is a big precision win for alias resolution. Timeline blocks become records (`source=temporal_note`, `at=date` or `retrospective`), with entities/links/tags passed as hints.
- **YouTube is an interest signal, not a fact stream:** aggregate per day packet into channel/topic counts. Never emit per-video facts. Sensitive topics (faith, health, politics) from watch history are **always held back** (Rule 9: never inferred). Add red-team tests for this.
- **Gmail JSON:** same triage as mbox (promos, OTPs, newsletters dropped), `thread_id` kept.
- **Dev sessions:** project/subject evidence only. Redact paths and secrets (port the redaction from `contest/scripts/extract_dev_sessions.py:26-40`).
- All of them: `content_hash` dedupe, a `forget_rules` check, then **cross-source day packets** → `extract.day` jobs.
- **Tests use synthetic fixtures that mimic these shapes**, never the real files.

## 3. `model_observed` (contract v1.2, already on `memory`)

`Attempt.model_observed` was added: the server still stamps the **declared** `model`, and the runner adds what the CLI/API reports.

- Add the column to `job_attempts`.
- In `core/extract.py` runners and `hooks/agent_worker.py`, fill it from metadata: `claude -p` JSON `modelUsage` keys, the anthropic response `model`, LM Studio `model`, the codex/gemini CLI JSON if available, else null.
- Flag a mismatch in the attempt verdict reasons (`model_mismatch`) **without rejecting**.
- Ops shows the declared vs observed counts.

**Done when** `python -m pytest -q` is green, `tm export` writes the gold slice's Quest tree to a folder outside the repo, and the four importers pass their synthetic tests. Commit on `mem-wpF` and report: branch, counts, contract requests.
