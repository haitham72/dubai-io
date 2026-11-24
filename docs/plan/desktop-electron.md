# Dubai-io Desktop — Electron App Architecture & Build Plan (`desktop` Branch)

**Date:** 23 Nov 2026 · **Status:** Approved Integration Plan (`HANDOFF_GEMINI.md` §5) · **Base Design:** `docs/plan/desktop-sessions.md` · **Base Branch:** `memory` (`0df08e1`, so `apps/memory/src/temporal_memory/ingest/desktop/` is already in-tree)

---

## 1. Windows-First Electron Shell & Renderer Strategy

- **Shell:** Electron desktop app at `apps/desktop/` (Windows 11 x64 primary target; portable/NSIS unsigned dev build via `electron-builder`).
- **Security Invariants (Non-Negotiable):**
  - `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, `webSecurity: true`.
  - Preload exposes ONLY an allowlisted `window.dubaiDesktop` bridge (`ipcAllowlist.ts`). The renderer NEVER holds raw `fs`, `child_process`, or OS shell privileges and NEVER sends arbitrary filesystem paths or shell strings to main.
- **Renderer Justification:** Build a clean **React + TypeScript + Vite renderer** (`apps/desktop/renderer/`) sharing the same palette/tokens as `design/20-11-2026/INDEX.md` (`packages/design-tokens/` shape: `#FFFFFF` / `#FAF8F5`, gold `#C5A059`, zero shadows) rather than embedding Next.js SSR from `apps/site/` inside Electron. *Why:* `apps/site` is a Next.js App Router server app with Playwright/web dependencies and is still evolving on `main`, whereas a standalone Vite + React renderer compiles to static assets cleanly in `electron-builder` without bundling a Next.js server process, keeps zero edits in `apps/site` on `desktop`, and exposes Desktop-specific Session History + Local Reader Consent panels alongside the 4-pillar shell (`Today` · `Chat` · `Quests` · `Memory`).

---

## 2. Main-Process Local Reader & Rule R1 Guardrails

All disk reads stay in Electron's main/utility process (`electron/main/localReader.ts`) and reuse `apps/memory` directly rather than re-implementing parsing/redaction/Rule 9 logic in JS:
- **Coding-Agent Sessions:** Calls `tm import agent-sessions` / `temporal_memory.ingest.desktop.agent_sessions.agent_session_records(...)` via `execFile` (`argv` array, **never** `exec` or shell interpolation).
  - Supports **Claude Code** (`~\.claude\projects\*\*.jsonl`) and **Codex** (`~\.codex\sessions\**\*.jsonl`); Gemini/Copilot/Cursor stay behind verified format flags (`desktop-sessions.md` §2.3).
  - Keeps title, `cwd` basename (path redacted), timestamps, truncated user prompts & final summaries; one `Record` per session-day (`source=agent:<tool>`).
- **Import Chrome / Edge / Brave History (Consent-Gated Preview Flow):**
  1. **Preview (`browser:preview`):** Calls `tm import browser <profileDir> --preview` / `desktop.browser.preview()` returning `{domain: visits}` counts ONLY — writes zero records.
  2. **Explicit Consent Screen:** Displays domain counts, states `"History & Bookmarks only — Cookies, Passwords & Autofill are NEVER touched"`, lists excluded categories (banking, health, adult, UAE government portals via domain denylist), and waits for explicit user confirmation before calling `browser:import`.
  3. **Import (`browser:import`):** Copies `History` + `Bookmarks` to a temp file and aggregates daily domain/topic/YouTube interest counts (`ingest/youtube.py` Rule 9 holdback).
- **Hard Rule R1 Credential Denylist (enforced in BOTH main process and Python reader):**
  - Never opens `.credentials.json`, `auth.json`, `*token*`, `*.key`, `.env*`, `oauth*`, `Cookies`, `Login Data`, `Web Data`, `Network/*`, `Local State`, or any symlink escaping an allowlisted root.

---

## 3. Owner-Device Token & `$0 App Cost` Owner-Hook Worker

- **Token Storage (`token:status`):** Stores the owner's `owner-device` bearer token and configured API URL (`http://127.0.0.1:8000`) encrypted via Electron `safeStorage`; never exposed in plaintext logs or renderer state beyond masked status.
- **Toggle: `"Process on your own Claude/Codex ($0 app cost)"` (`hook:toggle`):**
  - Starts/stops `apps/memory/hooks/agent_worker.py` (`execFile` with explicit `--url`, `--token`, `--model`, `--owner`, `agent-cli`/`owner-hook` MCP loop), letting the user process their own non-sensitive day packets at `$0` app cost (`processed_by: "your Claude"`).

---

## 4. Session History Panel (`desktop-sessions.md` Part 1)

- Scopes: `Workspace`, `Project`, `All` (capped at 200 rows/page with `"Load more"` pagination).
- Agent filter (`All`, `Claude Code`, `Codex`) + search over **redacted** summaries only.
- Row actions:
  - **Open Log:** read-only viewer displaying file path and redacted summary.
  - **Copy Resume Command:** generates allowlisted `argv` string (`claude --resume <id>` / `codex resume <id>`) after verifying `cwd` exists and contains no shell metacharacters.
  - **Send Selected to Memory:** shows exact selected count and requires explicit tap confirmation (Rule 6).
- **Delete:** disabled in v1 (`desktop-sessions.md` §1.5).

---

## 5. Packaging (`electron-builder`) & Test Strategy

- **Build (`apps/desktop/electron-builder.yml`):** Unsigned Windows NSIS / portable build (`asar: true`, no code signing — code signing certificate documented under `LATER`).
- **Tests (`apps/desktop/tests/`):**
  - **`D-A` (`tests/main/`, Codex — small focused task):** Vitest tests against `apps/memory/tests/fixtures/desktop/` proving R1 credential denylist blocks `.credentials.json`/`auth.json`/`Cookies`/`Login Data`/`.env`, symlink escape rejection, `cwd` metacharacter guard, IPC channel allowlist, and `ownerHook` explicit `--model` argv construction without logging tokens.
  - **`D-B` (`tests/renderer/`, Cursor — UI + packaging):** Vitest + React Testing Library tests for Session History search/filter/pagination, Browser `"Preview -> Consent -> Import"` gate (no import without confirmation), Owner-Hook toggle requiring model selection, plus Playwright-for-Electron smoke test once `D-A` + `D-B` merge on `desktop`.

**Before any merge into `desktop`:** main/renderer test suites green, TypeScript checks clean (`tsc --noEmit`), and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes.
