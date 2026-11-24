# D-A — Codex: Electron Main-Process Local Reader & Preload IPC Allowlist (`desktop` Branch)

Paste below the line into **Codex**.

---

You're building the **Electron main process + preload security layer** for **Dubai-io Desktop** (`apps/desktop/`, branch `desktop`, based on `memory` so `ingest/desktop/` is already in-tree). Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and `docs/plan/desktop-electron.md` (on branch `desktop`) first.
- **Never edit `G:\Haitham\VsCode\contest`** (`main`), **never touch `apps/web`** or `apps/memory/`.
- **Keep this task small and focused on main/preload + main tests only** (Cursor owns `apps/desktop/renderer/` + packaging in `D-B`).
- Sub-agents: **gpt-6.2 sol** (at most 1–2, or none). Commit only on your own branch.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-desktop-main -b desktop-main desktop
cd G:\Haitham\VsCode\contest-desktop-main
```

### Strictly Owned Paths
- `apps/desktop/package.json` (scripts: `test:main`, `typecheck:main`; deps: `electron` dev, `vitest`, `typescript`)
- `apps/desktop/tsconfig.main.json`
- `apps/desktop/electron/main/` (`window.ts`, `ipcAllowlist.ts`, `localReader.ts`, `ownerHook.ts`, `index.ts`)
- `apps/desktop/electron/preload/` (`index.ts`)
- `apps/desktop/tests/main/` (`localReader.test.ts`, `ipcAllowlist.test.ts`, `ownerHook.test.ts`)

### Deliverables
1. **Secure `BrowserWindow` & Preload (`electron/main/window.ts`, `electron/preload/index.ts`):**
   - Enforce `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, `webSecurity: true`.
   - `ipcAllowlist.ts`: strict typed channel allowlist (`sessions:scan`, `sessions:resumeCommand`, `browser:preview`, `browser:import`, `hook:status`, `hook:toggle`, `token:status`). Renderer NEVER supplies arbitrary filesystem roots or raw shell commands.
2. **Main-Process Local Reader (`electron/main/localReader.ts`):**
   - Calls `apps/memory`'s Python CLI (`tm import browser --preview`, `tm import browser`, `tm import agent-sessions`) OR `temporal_memory.ingest.desktop.{agent_sessions,browser}` cleanly via `execFile` (`argv` array — NEVER `exec` / shell strings).
   - **Rule R1 hard credential denylist (main process pre-guard too):** refuse paths touching `.credentials.json`, `auth.json`, `*token*`, `*.key`, `.env*`, `oauth*`, `Cookies`, `Login Data`, `Web Data`, `Local State`, or symlink escapes outside allowlisted user roots (`~\.claude\projects`, `~\.codex\sessions`, Chrome/Edge/Brave profile dirs).
   - `buildResumeArgs(agentTool, sessionId, cwd)`: validates allowlisted binary + existing `cwd` directory with no metacharacters (`;`, `&`, `|`, `` ` ``), returning display-safe argv array (`claude --resume <id>` / `codex resume <id>`).
3. **Owner-Hook Toggle (`electron/main/ownerHook.ts`):**
   - Manages the `"Process on your own Claude/Codex ($0 app cost)"` worker state by spawning/stopping `apps/memory/hooks/agent_worker.py` with explicit `--model`, `--token` (from Electron `safeStorage` wrapper, never logged), and `--url` (`argv` list only).
4. **Tests (`apps/desktop/tests/main/` — Vitest, synthetic fixtures only):**
   - Reuse `apps/memory/tests/fixtures/desktop/` + in-test temp profiles;
   - R1 credential denylist blocks `.credentials.json`, `auth.json`, `Cookies`, `Login Data`, `.env`;
   - Symlink escape & unsafe `cwd` shell metacharacters are rejected;
   - IPC allowlist rejects unknown channels;
   - `ownerHook` spawns/stops with explicit `--model` and never logs the bearer token.

**Done when** `npm run test:main` and `npm run typecheck:main` in `apps/desktop/` pass, and `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes. Commit on `desktop-main` and report: branch, counts, contract requests for `D-B`.
