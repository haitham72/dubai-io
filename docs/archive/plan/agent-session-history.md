# Agent Session History for Dubai-io Desktop (Orca reference)

**Project:** Dubai-io AI Assistant · **Status:** proposed, not approved · **Path:** `docs/plan/agent-session-history.md` · **Date:** 17 November 2026 · **Ledger:** 16 Nov row "Desktop local-reader imports" (open)

Companion: `docs/plan/desktop-llm-sessions.md` (LLM chat and memory ingestion). Reference studied: `https://github.com/stablyai/orca` at commit `c026da2c` (MIT). Paths below are Orca's; re-clone the repo to check them.

---

## 1. What Orca actually does (verified in source and docs)

Orca's **Agent Session History** panel (right sidebar → Agents tab) lists past sessions from many coding-agent CLIs and offers Resume, Copy resume command, Open log, and Delete.

- **Scopes:** `Workspace` (current worktree), `Project` (active project), `All` (every session found on the machine). Source: `docs/site/content/docs/agents/session-history.mdx`.
- **Scan on demand:** a **Refresh Session History** button rescans. There is no hidden background crawl of the disk; the docs say the scan runs after the next refresh.
- **Default cap:** `DEFAULT_AI_VAULT_SCAN_LIMIT = 1000` (`src/shared/ai-vault/scanning/ai-vault-session-depth.ts`). An `unlimited` option exists for the "All" view. **This is the "load every session" behaviour you saw.**
- **Per-agent discovery:** each CLI has its own root. Verified in `src/main/ai-vault/discovery/session-scanner-agent-sources.ts` and `ai-vault-scan-roots.ts`:

| Agent | Default root (Windows: `%USERPROFILE%`) |
|---|---|
| Claude Code | `~\.claude\projects` (plus managed account profile dirs) |
| Codex | `~\.codex\sessions` (plus `additionalCodexSessionsDirs`) |
| Gemini | `~\.gemini\tmp` |
| Copilot | `$COPILOT_HOME` or `~\.copilot` |
| Cursor | `~\.cursor\projects` |
| CodeBuddy | `~\.codebuddy\projects` |
| Rovo Dev | `~\.rovodev\sessions` |
| Pi | `$PI_CODING_AGENT_DIR` or `~\.pi\agent\sessions` |
| Droid | `~\.factory\sessions` and `~\.factory\projects` |
| Cline | `$CLINE_SESSION_DATA_DIR` or `~\.cline\data\sessions` |
| Qoder | `~\.qoder\projects` |
| Jcode | `$JCODE_HOME` or `~\.jcode\sessions` |
| OpenCode | `$XDG_DATA_HOME` or `~\.local\share\opencode\opencode.db` (SQLite) |
| Antigravity, Hermes, OMP, Kimi, Muse, Devin, Grok, Kiro, Zcode, OpenClaw, Prime Agent, Rovo | one scanner folder each under `scanners/` |

- **WSL:** Orca also scans the home folders of running WSL distros (`wsl/discovery/…`). Relevant if the user runs Codex inside WSL.
- **Parse cache:** per-transcript rows in a versioned SQLite cache (`parse-cache/session-parse-cache-database.ts`). A file whose size/mtime hasn't changed is not re-parsed. Sidecar files (`session-sidecar-stat.ts`) are tracked the same way.
- **Scan service:** the heavy work runs in a separate child process (`scan-service/session-scanner-service-entry.ts`, with a versioned message protocol, a request deadline, and a restart policy). The UI never blocks on disk I/O.
- **Search:** a SQLite **FTS5** index (`messages_fts`, in `src/main/ai-vault-search/`) with a query planner, postings, and snippets with highlighted matches.
- **Titles and first prompt:** a title resolver reads each transcript's title and first user message (`session-titles/`, `prompts/`). List rows keep a short preview; full text loads when the row is opened.
- **Resume:** runs the agent's own resume command in a new terminal in the session's `cwd` (e.g. `claude --resume <id>`, `codex resume <id>`). Only from a local workspace.
- **Delete:** `src/main/ai-vault/deletion/session-delete.ts` deletes transcript files. Treat as a high-risk action in our version.
- **Licence:** MIT (Copyright 2026 Lovecast Inc.). Reusing code requires keeping the notice. Recommended: reimplement from the design, not copy files.

**Key insight:** Orca's panel answers "what can I resume?" It does not extract meaning. Dubai-io needs two different things, and they should be separate stages:

1. **Index (cheap, local, no LLM):** list and search sessions on this PC. This is Orca's job.
2. **Ingest to memory (LLM, consent per session):** extract dated facts. This is the job in `docs/plan/desktop-llm-sessions.md`.

Do not wire stage 2 to "all sessions." The index can hold everything; memory extraction runs only on sessions the user selects or on a per-source opt-in with a visible count.

---

## 2. Target design for Dubai-io Desktop

```
Renderer (React)
  └─ Session History panel: scope toggle, agent filter, search, row actions
        │  typed IPC (preload contextBridge only)
Electron main
  ├─ sources/registry.ts      ← one entry per agent: id, roots[], parser, enabled
  ├─ scan/scanService.ts      ← utilityProcess: discover → parse → cache → emit rows
  ├─ scan/parseCache.ts       ← SQLite: path, size, mtime, sha256, parsedVersion, summary JSON
  ├─ search/fts.ts            ← SQLite FTS5 over REDACTED message text
  ├─ actions/resume.ts        ← allowlisted commands only, local workspaces only
  ├─ actions/delete.ts        ← confirm + audit + tombstone
  └─ memory/ingest.ts         ← stage 2, from the guide; consumes selected sessions only
```

### 2.1 Source registry (one adapter per agent)

```ts
export interface SessionSourceDef {
  id: 'claude-code' | 'codex' | 'gemini' | 'cursor' | 'opencode' | /* … */ string;
  label: string;
  enabled: boolean;                 // user consent, default false for everything but our own chat
  roots(): Promise<string[]>;       // resolved from env overrides + defaults, never ~ or / by accident
  listFiles(root: string): AsyncIterable<{ path: string; size: number; mtimeMs: number }>;
  parseSummary(file: string, signal: AbortSignal): Promise<SessionSummary>;   // title, cwd, startedAt, updatedAt, msgCount, firstPrompt(≤300 chars)
  parseMessages(file: string, fromOffset: number, signal: AbortSignal): AsyncIterable<RawMessage>;
  resumeCommand?(s: SessionSummary): string[] | null;   // argv array, never a shell string
  parserVersion: number;            // bump to invalidate the cache
}
```

Rules:
- **Start with 3 agents:** Claude Code (`~\.claude\projects`), Codex (`~\.codex\sessions`), and our own chat. Add the rest one at a time, each with a fixture and a test.
- **Roots are allowlisted.** Never accept a path from the renderer. Resolve symlinks and reject any file whose real path is outside its root.
- **Default off.** Each agent is enabled in Settings with the path shown and a "Scan now" button.

### 2.2 Scan service (utilityProcess)

- Run the scanner in `utilityProcess.fork()` so a bad transcript cannot freeze the UI or crash main.
- Protocol: `{ type: 'scan', requestId, scope, agents[], limit, since? }` → streamed `{ type: 'row', … }`, `{ type: 'progress', done, total }`, `{ type: 'done', tally }`, `{ type: 'error', … }`. Include a `protocolVersion`.
- **Cancel:** every scan takes an `AbortSignal`; a new scan cancels the previous one.
- **Deadline:** 30 s per agent per request, then return partial results with a "timed out" issue row. Do not silently drop.
- **Restart policy:** restart the child at most 3 times in 5 minutes, then show "Session index unavailable — see log."

### 2.3 Parse cache (the reason it is fast)

Table `parse_cache(path PRIMARY KEY, agent, size, mtime_ms, sha256_head, parser_version, summary_json, parsed_at)`.
- Reuse a row only if `size`, `mtime_ms`, and `parser_version` match.
- Hash the first 4 KB to detect rotated or replaced files with the same size and mtime.
- `parser_version` bump invalidates all rows for that agent.
- Store the summary only, not the full transcript.

### 2.4 Search index (FTS5)

- Table `messages_fts` (FTS5, `tokenize='unicode61 remove_diacritics 2'`; test Arabic and Arabizi input) with `session_id`, `role`, `ts`, `text_redacted`.
- **Index only redacted text** (apply the redaction from the LLM guide §6 step 3 first). The index is plaintext on disk, so it is as sensitive as the transcripts.
- Quote user input before `MATCH` so punctuation is literal (Orca does this in `session-search-query-planner.ts`).
- Provide "forget by source" that deletes the index rows as well as the cache rows.

### 2.5 Scope and "pull every session"

Implement the same three scopes as Orca, with two changes:
- **"All" is capped by default** (e.g. 200 rows). A "Load more" button shows the next page. Each page is a query, not a rescan.
- **Show the count before any heavy action**: "Found 1 480 sessions across 3 agents, 2.1 GB. Index them? [Index] [Index last 30 days]". Indexing all of them needs one tap.

### 2.6 Actions

| Action | Rule |
|---|---|
| Open log | Read-only, in a viewer that shows the file path. Fine. |
| Copy session ID / resume command | Fine. |
| Resume | Allowlisted argv per agent, local workspace only, `cwd` from the session record and checked to be an existing folder. One tap; no shell string. |
| Send session to memory | Separate consent per source; shows the count and the sensitive-check result before sending any text to a model. Rule 6 from the LLM guide. |
| Delete transcript file | Off in v1. If added: explicit confirmation, one approval per deletion (rule 6), audit row, and never from the memory screen. |

---

## 3. Build order (each step has a pass test)

| Step | Build | Pass test |
|---|---|---|
| **S1** | Source registry with Claude Code only; discovery of `~\.claude\projects`. | Lists fixture sessions; ignores symlinks that leave the root. |
| **S2** | Summary parser (title, cwd, timestamps, msg count, first prompt ≤ 300 chars). | Fixture of 3 sessions gives exact summaries; malformed line is skipped and counted. |
| **S3** | Scan service in `utilityProcess` with protocol, cancel, and deadline. | Cancel mid-scan returns partial rows; killing the child shows "unavailable," not a crash. |
| **S4** | Parse cache. | Second scan of unchanged fixtures parses 0 files (assert by counter). Changing one file re-parses only that file. |
| **S5** | Panel UI: scope toggle (Workspace / Project / All), agent filter, search box, pagination, row details. | Works at 16 px gutter on a narrow window; "All" never loads more than one page at once. |
| **S6** | FTS5 index over redacted text; forget-by-source removes index rows. | Search finds Arabic and English fixture terms; redaction test: a fake `sk-ant-…` is not findable. |
| **S7** | Resume action (Claude Code, Codex), allowlisted argv, local only. | Resume is disabled for remote workspaces; a crafted `cwd` with `&` is not executed. |
| **S8** | Second and third agents (Codex, Gemini or Cursor), each verified on a real sample first. | Each adapter has happy-path and failure-path tests. |
| **S9** | Hand-off to memory ingest (stage 2 of the LLM guide) for selected sessions only. | Ingest count equals the number of selected sessions; no session is sent unselected. |

Do not start S9 before S6 works on real data. The review's lesson applies: one honest journey first.

---

## 4. Security and privacy checklist

- [ ] Renderer cannot choose roots, file paths, or commands; main validates everything.
- [ ] Roots come from the registry, with env overrides validated as absolute directories.
- [ ] No reading of credential files (`.credentials.json`, `auth.json`, token stores). Enforce with a deny-list in the registry, not a convention.
- [ ] Transcripts are opened read-only (`fs.open` with `'r'`), never written.
- [ ] Redaction runs before anything is written to the FTS index, the cache summary, logs, or a model.
- [ ] Logs contain counts and paths, never message text.
- [ ] The FTS and cache databases live under the app's user-data folder with user-only ACLs; consider SQLCipher or DPAPI-wrapped key if the user asks for encryption at rest.
- [ ] "Forget source" deletes: cache rows, FTS rows, memory rows built from it, and sets a tombstone so the watcher does not re-index.
- [ ] Audit log row for every scan that reads a new root, every resume, and every send-to-memory.
- [ ] Orca's hooks are not used. Dubai-io reads transcripts itself, from folders the user approved.

---

## 5. Things not to copy from Orca

- **Unlimited "All" by default.** It is convenient for a browser of past work. For a personal memory product it is a privacy risk. Keep the cap and the explicit count.
- **Hooks into other CLIs** (Orca's `orca-agent-hook.exe` and the `127.0.0.1:47823` listener). They give another app live access to every prompt and tool call. Do not depend on them.
- **Delete from the panel.** It is one click in Orca; for us it needs approval, audit, and a path that cannot touch memory or other agents' files.

---

## 6. Open questions for the founder

1. Do we want the **index** (browse and search past sessions) in v1, or only the **memory** feature from the LLM guide? The index is much cheaper to build and is useful on its own.
2. Default scope: `Project` (this app's workspace) or `All` with a page size of 200?
3. Which agents matter first: Claude Code and Codex only, or also Cursor and Gemini?
4. Encryption at rest for the index: required for v1 or later?
5. Licence: reimplement from this design (recommended), or reuse Orca's MIT code with the notice kept?

---

## 7. Appendix: how to verify these claims yourself

```powershell
# Clone (read-only reference)
git clone --depth 1 https://github.com/stablyai/orca.git
# Scanner entry and discovery
Get-Content orca\src\main\ai-vault\session-scanner.ts | Select-Object -First 120
Get-Content orca\src\main\ai-vault\discovery\session-scanner-agent-sources.ts
# Docs for the panel
Get-Content orca\docs\site\content\docs\agents\session-history.mdx
```

Note: the clone that produced this guide printed a checkout warning on Windows (a path-length or case issue in the repo tree). The files used here were present and readable; re-run `git restore --source=HEAD :/` inside the clone if you see missing files.
