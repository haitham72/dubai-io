# Dubai-io Desktop: Multi-LLM Chat + On-Device Session Memory

**Project:** Dubai-io AI Assistant · **Status:** proposed, not approved · **Path:** `docs/plan/desktop-llm-sessions.md` · **Date:** 17 November 2026 · **Ledger:** 16 Nov row "Desktop local-reader imports" (open)

Scope: Windows PC first, Electron shell, several LLM providers, and ingestion of the owner's previous AI sessions on this device into the temporal memory pipeline. Companion: `docs/plan/agent-session-history.md`. Rules: `CLAUDE.md` 1–10; architecture: `ARCHITECTURE.md`.

---

## 1. What we are building

1. **An Electron desktop app** ("Dubai-io Desktop") with one chat surface that talks to several LLMs: Anthropic, OpenAI, Google Gemini, and local models (Ollama / LM Studio).
2. **Session ingestion:** with explicit consent, the app reads the transcripts of AI sessions already on this PC (Claude Code, Codex, and others) and turns them into events.
3. **Temporal memory:** events are chunked, extracted into dated facts, checked against existing memory, and stored with supersession, never overwritten. The user can see, confirm, correct and forget every item. This follows the order of work in `PLAN.md` §2: thin slice first, then verdict, then UI.

**Non-goals (for v1):** driving other apps' UIs; reusing other apps' login tokens; sending raw transcripts to any cloud model without a per-source opt-in; a multi-user backend.

---

## 2. Rules that are not negotiable

These come from `CLAUDE.md` rules 1–10 and the review of the Quest build. Read them before writing code.

| # | Rule | Why |
|---|---|---|
| R1 | **Never read, copy or forward credential files** of other tools (e.g. `~\.claude\.credentials.json`, `~\.codex\auth.json`, Orca or browser token stores). | Those are another product's login. Using them in our app is a security and terms-of-service problem. |
| R2 | **Our LLM access uses our own API keys** (Anthropic API, OpenAI API, Gemini API) stored with Electron `safeStorage`. Never a consumer-subscription token. | Subscription logins are for the official client. Third-party apps use API keys. Check each provider's current terms before shipping. |
| R3 | **Session transcripts are sensitive.** They contain other people's messages, secrets pasted by mistake, and health, family or money details. | Treat as untrusted data (rule: imported content is untrusted; no shadows). |
| R4 | **Opt-in per source.** Each source (Claude Code folder, Codex folder, Orca DB…) is switched on separately in Settings, with the path and the last-read time shown. | The user decides what is read. |
| R5 | **Local first.** Parsing, redaction and the sensitive check run on the device before any model call. Only the redacted, chunked text of an enabled source is sent to the model the user selected. | Minimises what leaves the PC. |
| R6 | **Never infer sensitive traits.** The sensitive check runs on messages before extraction, not as a per-chunk flag. Inferred sensitive facts are never stored. | `PLAN.md` §2 (proposed 16 Nov), and product-safety defect noted in the review. |
| R7 | **Correction never overwrites.** An old memory gets an end date and a pointer to its replacement. Every memory keeps its source session and message range. | Supersede, don't overwrite (review: strong). |
| R8 | **Forget by source works.** "Forget this session / this source" removes every memory and chunk built from it, and blocks re-ingestion until the user re-enables it. | `PLAN.md` order item 6; review's "forget is the one honest side effect." |
| R9 | **No fake "done".** Every action ends in a real result or an honest state (`new / seen / actioned / dismissed / resolved`, or `UNKNOWN_STATUS`). Never show "reminder set" without delivery. | Review: the card-contract gap. |
| R10 | **The LLM proposes; deterministic code executes.** Any side effect (send, write a file, call an API) needs one explicit user tap, one approval per side effect (rule 6). | `CLAUDE.md` rule 6, strict. |

---

## 3. Sources on this PC (verified on 17 Nov 2026 unless marked)

| Source | Location | What we know | Status |
|---|---|---|---|
| **Claude Code** | `%USERPROFILE%\.claude\projects\<encoded-cwd>\<sessionId>.jsonl` | 16 project folders. Each line is one JSON object with `type` (`session-owner`, `queue-operation`, `attachment`, user/assistant messages…), `sessionId` and an ISO `timestamp`. Subagent logs in `<sessionId>\subagents\*.jsonl`. Tool output in `<sessionId>\tool-results\`. Hook events (`attachment` with `hookName`) are noise for memory. | Verified: layout and line types. Exact message schema for each `type`: **verify on a sample before writing the parser.** |
| **Codex** | `%USERPROFILE%\.codex\` (contains `config.toml`, `auth.json`, `cache`, …) | Folder exists. Session folder not yet confirmed. | **Verify.** Read `sessions/` only if present. Never `auth.json`. |
| **Orca** (desktop agent app) | `%APPDATA%\orca\` (includes `agent-session-domain.db`, SQLite with WAL) and `%USERPROFILE%\.orca\agent-hooks\` | Installs hooks into `.claude\settings.json` that post every prompt and tool call to `127.0.0.1:47823`. | **Do not depend on another app's hooks or DB.** Read only if the user explicitly enables it and we only copy the DB (WAL-safe) before reading. Lower priority. |
| **Cursor / Gemini / Cline / Copilot** | `%USERPROFILE%\.cursor`, `.gemini`, `.cline`, `.copilot` | Folders exist. Formats unverified. | **Verify each** before adding an adapter. One adapter per format. |
| **Our own chat** | Electron app's own store | Full control. | Build first. |

**Adapter contract:** every source implements the same interface, so the pipeline never knows the vendor.

```ts
interface SessionSource {
  id: string;                       // "claude-code", "codex", "app-chat"
  label: string;
  discover(): Promise<SourceFile[]>;   // only paths under the user-approved root
  parse(file: SourceFile, fromOffset: number): AsyncIterable<RawEvent>;
  // RawEvent: { source, sessionId, ts, role: 'user'|'assistant'|'tool'|'system', text, cwd?, toolName? }
}
```

Skip non-conversation records (hooks, queue operations, empty text). Keep `tool` events only as a short label, not their full output, unless the user asks.

---

## 4. Architecture

```
dubai-io-desktop/
├─ electron/
│  ├─ main/            # owns files, keys, DB, scheduler, provider calls
│  │  ├─ index.ts
│  │  ├─ keys.ts       # safeStorage read/write for API keys
│  │  ├─ sources/      # SessionSource adapters + file watcher (chokidar)
│  │  ├─ pipeline/     # redact → sensitive check → chunk → extract → verdict → store
│  │  ├─ providers/    # anthropic.ts, openai.ts, gemini.ts, ollama.ts (one interface)
│  │  └─ db.ts         # SQLite (better-sqlite3) — local store
│  ├─ preload/         # contextBridge: typed API only, no raw ipcRenderer
│  └─ renderer/        # React UI: chat, sources, memory timeline, confirm/forget
├─ packages/shared/    # types: RawEvent, Chunk, Memory, Verdict, ProviderRequest
├─ tests/fixtures/     # SYNTHETIC transcripts only — never real ones in the repo
└─ package.json
```

**Electron security baseline (mandatory):**
- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.
- Renderer talks to main only through the preload `contextBridge` with named methods (`chat.send`, `sources.list`, `memory.forget`). No generic `ipcRenderer.invoke(channel)`.
- Content-Security-Policy in `index.html`; no remote code; block `will-navigate` and new windows.
- API keys never reach the renderer. Requests go renderer → main → provider.

---

## 5. Provider layer

One interface, four adapters:

```ts
interface LLMProvider {
  id: 'anthropic' | 'openai' | 'gemini' | 'ollama';
  models(): Promise<string[]>;
  complete(req: { model: string; system?: string; messages: Msg[]; maxTokens?: number }): Promise<{ text: string; usage?: Usage }>;
  stream?(req: ...): AsyncIterable<string>;
}
```

- **Anthropic:** official SDK, API key from `safeStorage`. Model IDs: use the current list from the provider's docs at build time (Claude 5 family in this environment: `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-fable-5-2`). Do not hard-code IDs without checking.
- **OpenAI / Gemini:** same pattern with their SDKs.
- **Ollama / LM Studio:** HTTP to `http://127.0.0.1:<port>`. Lets sensitive sources run fully offline. Recommended for the sensitive check (R6) and for extraction on sources the user marks "local only."
- **Routing:** the user picks a model for chat. Memory extraction uses a cheaper model set in config (`LAB_FOLLOWUP_MODEL`-style env var). Compare a cheap and a strong model on the same chat before choosing (`apps/api/app/lab/CLAUDE.md`).
- **Cost guard:** per-provider monthly token cap and a visible counter in Settings.

---

## 6. Ingestion pipeline (the part that becomes temporal memory)

Run as a background job, incremental, resumable.

1. **Watch:** the file watcher detects new or changed files under approved roots. Each file has a stored byte offset, so reruns only read new lines.
2. **Parse:** adapter turns lines into `RawEvent`s. Malformed lines are logged and skipped, never fatal.
3. **Redact:** strip secrets before anything is stored or sent. Patterns to start with: `sk-ant-…`, `sk-…`, `AIza…`, `ghp_…`, `Bearer …`, private key blocks, card-like numbers, IBAN-like strings. Keep a count of redactions per session.
4. **Sensitive check (R6):** classify messages (health, religion, family, sexuality, finances, legal) with the local classifier or the local model. Flagged spans are excluded from extraction and marked in the UI, not silently dropped.
5. **Segment:** chunk by session, then cut at pauses (e.g. > 30 min) and topic changes. A day is not a boundary (`apps/api/app/lab/CLAUDE.md` proposal). Each chunk stores `sessionId`, `from_msg`, `to_msg`, `source`.
6. **Extract:** LLM returns JSON facts, one per memory, each with `event_time` (the message timestamp, not "now") and `evidence` (message ids). Validate the JSON schema; reject facts without evidence (the review's "evidence or nothing" rule).
7. **Verdict:** compare each new fact with the closest existing memories (hybrid search). Outcomes: `new`, `duplicate` (merge evidence), `updates` (end the old memory at the new `event_time`, link them), `contradicts` (keep both, mark for user review).
8. **Store:** write to `memories` with `valid_from`, `valid_to` (null = current), `ingested_at`, `source`, `session_id`, `msg_range`. Never `UPDATE` the fact text in place.
9. **Index:** embed the memory text. Store the entity links (person, place, topic) in `links`.
10. **Surface:** the Memory screen lists facts by life theme (Career · Learning · Projects · People & family · Events · Home & money · Travel), each with source, date and **Confirm / Edit / Not true / Forget**.

**Temporal test (must pass before any UI):** feed a synthetic session where a job title changes on day 10. Ask "what was my title on day 5?" and "what is it now?" Both must answer from `valid_from`/`valid_to`, not from ingestion time. The review flagged this as the untested core claim.

---

## 7. Storage schema (minimal)

```sql
sources(id, kind, root_path, enabled, offset_map JSON, last_read_at)
source_records(id, source_id, file, byte_offset, sha256, parsed_at)
sessions(id, source_id, external_id, started_at, ended_at, cwd, msg_count, redactions, status)
chunks(id, session_id, from_msg, to_msg, text_redacted, sensitive_spans JSON, status)
memories(id, text, theme, event_time, valid_from, valid_to, ingested_at, source_id, session_id,
         msg_range, confidence, user_status ['pending','confirmed','edited','not_true','forgotten'])
links(from_id, to_id, relation)           -- supersedes | duplicates | contradicts | about_person
followups(id, memory_id, question, answered_by_memory_ids)
audit(id, at, action, target, detail)     -- every forget, approve, send
```

Forget-by-source: `DELETE` chunks and memories where `source_id = ?`, then set `sources.enabled = 0` and keep a tombstone so the watcher does not re-ingest.

---

## 8. Build order (each step must pass its test)

| Step | Build | Done when |
|---|---|---|
| **0** | Truth sheet: 3–4 people, ~10 true facts each, open loops, must-never-say list. Written by the founder by hand. | `truth.yaml` exists. It is the eval for steps 4–7. |
| **1** | Electron shell + secure preload + one provider (Anthropic) chat, key in `safeStorage`. | Chat works; renderer cannot read the key (test it). |
| **2** | Claude Code adapter: parse `.jsonl` → `RawEvent`s, offsets, noise filter. | Parser test on synthetic fixtures; a rerun reads zero new lines. |
| **3** | Redaction + sensitive check. | Fixture with fake keys and a health line: both removed/flagged. |
| **4** | Extraction + verdict + store with valid_from/valid_to. | Temporal test (section 6) passes; evidence-less facts rejected. |
| **5** | Memory screen: list, Confirm / Forget / Not true; forget-by-source. | Forget removes every row built from a source and blocks re-ingest. |
| **6** | Second provider + one local model (Ollama). Compare on the same chat. | Scores written to `scores/<date>.json`. |
| **7** | Codex and other adapters, one at a time, each verified on a sample first. | Each adapter has a happy-path and a failure-path test. |
| **8** | Ask box over memory ("what did I decide about X?") with cited answers. | Every answer cites memory ids; "I don't know" when nothing matches. |

Do **not** start step 7 before step 5 works on real data. The review's lesson: add sources only after one journey is honest end to end.

---

## 9. Testing

- **Fixtures are synthetic.** Real transcripts stay outside the repo (`apps/api/app/lab/CLAUDE.md`: "Real data stays out of the repo"). Never paste real sessions into tests or logs.
- **Unit:** parser, redaction, schema validation, verdict logic, offset resume.
- **Integration:** a fake provider that returns canned JSON; a full run over a fixture session.
- **Eval:** the truth sheet. Score precision (facts that are true), recall (true facts found), and false-sensitive (any sensitive inference is a failure, weight it heavily).
- **Electron:** smoke test that the renderer has no `require`, no `process`, and no key in `window`.
- **Failure paths:** missing folder, locked file, provider 429/timeout, malformed JSON from the model, offline Ollama.

---

## 10. Lessons carried from the Quest review (17 Nov)

- Extraction must be verified **with the LLM on**. A run with provider off proves plumbing, not memory.
- Event time vs ingestion time is the differentiator. Test it explicitly.
- Multi-user scoping (`user_id` on every row and every query) is required even for a single user, because a second user would otherwise be a security gap.
- Retention: **decay with a floor, never delete by age**, if §R-ND holds (founder 9 Nov).
- Build one card or journey end to end with an honest result before adding breadth.
- Background jobs and batching are needed before thousands of emails or long chat histories. A single synchronous path will time out (the review measured ~60 s for one forget).

---

## 11. Open questions for the founder

1. Which sources are in v1: Claude Code only, or Claude Code + Codex?
2. Local-only mode for sensitive sources (Ollama), or cloud extraction with redaction?
3. Does Orca integration stay out of scope? (Recommended: yes.)
4. Which provider keys will the founder supply, and who pays per-token costs?
5. Is Electron the final shell, or should the desktop app wrap the existing `apps/site` (Next.js) UI?

---

*Sources read for this guide: `CLAUDE.md`, `PLAN.md` §2, `docs/CLAUDE.md`, `docs/status.md`, `docs/request-backlog.md`, `apps/api/app/lab/CLAUDE.md`, local folder listings under `%USERPROFILE%\.claude`, `%USERPROFILE%\.codex`, `%APPDATA%\orca`, and the Quest build review pasted on 17 Nov 2026.*
