import { execFile as execFileCb } from "child_process";
import fs from "fs";
import path from "path";
import { promisify } from "util";
import type { AgentTool, BrowserKind } from "./ipcAllowlist";

const execFileAsync = promisify(execFileCb);

export type ExecFileFn = (
  file: string,
  args: string[],
  options: { cwd?: string; env?: NodeJS.ProcessEnv; windowsHide?: boolean; encoding?: "utf8" },
) => Promise<{ stdout: string; stderr: string }>;

export interface ReaderRoots {
  claudeProjects: string;
  codexSessions: string;
  browsers: Record<BrowserKind, string>;
}

const DENY_SEGMENT = [
  /^\.credentials\.json$/i,
  /^auth\.json$/i,
  /token/i,
  /\.key$/i,
  /^\.env/i,
  /^oauth/i,
  /^cookies$/i,
  /^login data$/i,
  /^web data$/i,
  /^local state$/i,
];

export function defaultRoots(home = process.env.USERPROFILE || process.env.HOME || ""): ReaderRoots {
  const local = path.join(home, "AppData", "Local");
  return {
    claudeProjects: path.join(home, ".claude", "projects"),
    codexSessions: path.join(home, ".codex", "sessions"),
    browsers: {
      chrome: path.join(local, "Google", "Chrome", "User Data"),
      edge: path.join(local, "Microsoft", "Edge", "User Data"),
      brave: path.join(local, "BraveSoftware", "Brave-Browser", "User Data"),
    },
  };
}

export function memorySourceRoot(fromDir = __dirname): string {
  return path.resolve(fromDir, "../../../memory/src");
}

export function credentialSegment(name: string): boolean {
  return DENY_SEGMENT.some((pattern) => pattern.test(name));
}

export function assertNotCredential(target: string): void {
  const parts = path.resolve(target).split(/[\\/]+/);
  for (const part of parts) {
    if (credentialSegment(part)) {
      throw new Error(`Refusing credential path segment: ${part}`);
    }
  }
}

export function assertInsideRoot(
  target: string,
  root: string,
  realpath: (candidate: string) => string = fs.realpathSync,
): void {
  const rootReal = path.resolve(realpath(root));
  const targetReal = path.resolve(realpath(target));
  const rel = path.relative(rootReal, targetReal);
  if (rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error("Path escapes the allowlisted root");
  }
}

export function assertSafePath(target: string, root: string, realpath?: (candidate: string) => string): void {
  assertNotCredential(target);
  assertNotCredential(root);
  assertInsideRoot(target, root, realpath);
}

export function resolveProfile(browser: BrowserKind, profileName: string, roots: ReaderRoots): string {
  const base = roots.browsers[browser];
  const full = path.resolve(base, profileName);
  assertSafePath(full, base);
  return full;
}

export function resolveSessionRoot(tool: AgentTool | undefined, roots: ReaderRoots): string {
  if (tool === "codex") return roots.codexSessions;
  if (tool === "claude-code" || tool === undefined) return roots.claudeProjects;
  throw new Error(`Unsupported agent tool: ${tool}`);
}

export function buildResumeArgs(agentTool: AgentTool, sessionId: string, cwd: string): { argv: string[]; cwd: string } {
  if (!/^[A-Za-z0-9_-]{1,128}$/.test(sessionId)) {
    throw new Error("sessionId is not allowlisted");
  }
  if (/[;&|`]/.test(cwd)) {
    throw new Error("cwd contains shell metacharacters");
  }
  let info: fs.Stats;
  try {
    info = fs.statSync(cwd);
  } catch {
    throw new Error("cwd does not exist");
  }
  if (!info.isDirectory()) {
    throw new Error("cwd is not a directory");
  }
  const binary = agentTool === "claude-code" ? "claude" : "codex";
  const argv = agentTool === "claude-code" ? [binary, "--resume", sessionId] : [binary, "resume", sessionId];
  return { argv, cwd };
}

const PREVIEW_CODE =
  "import json,sys; from temporal_memory.ingest.desktop.browser import preview; json.dump(preview(sys.argv[1]), sys.stdout)";
const SESSIONS_CODE = [
  "import json,sys",
  "from pathlib import Path",
  "from dataclasses import asdict",
  "from temporal_memory.ingest.desktop.agent_sessions import agent_session_records",
  "tool, root, since = sys.argv[1], sys.argv[2], sys.argv[3]",
  "records = agent_session_records('karim', {tool: Path(root)}, since=since or None)",
  "json.dump([asdict(r) for r in records], sys.stdout)",
].join("; ");

export interface ReaderDeps {
  execFile?: ExecFileFn;
  python?: string;
  memorySrc?: string;
  env?: NodeJS.ProcessEnv;
}

function runner(deps: ReaderDeps): ExecFileFn {
  if (deps.execFile) return deps.execFile;
  return (file, args, options) => execFileAsync(file, args, options) as Promise<{ stdout: string; stderr: string }>;
}

async function runPython(deps: ReaderDeps, code: string, scriptArgs: string[]): Promise<string> {
  const memorySrc = deps.memorySrc ?? memorySourceRoot();
  const env = {
    ...process.env,
    ...deps.env,
    PYTHONPATH: memorySrc,
  };
  const result = await runner(deps)(deps.python ?? process.env.TM_PYTHON ?? "python", ["-c", code, ...scriptArgs], {
    cwd: path.resolve(memorySrc, ".."),
    env,
    windowsHide: true,
    encoding: "utf8",
  });
  return result.stdout;
}

export async function previewBrowser(profileDir: string, root: string, deps: ReaderDeps = {}): Promise<Record<string, number>> {
  assertSafePath(profileDir, root);
  const stdout = await runPython(deps, PREVIEW_CODE, [profileDir]);
  return JSON.parse(stdout) as Record<string, number>;
}

export async function importBrowser(
  profileDir: string,
  root: string,
  owner: string,
  deps: ReaderDeps = {},
): Promise<{ argv: string[] }> {
  assertSafePath(profileDir, root);
  if (!/^[a-z0-9][a-z0-9-]{0,63}$/i.test(owner)) {
    throw new Error("owner id is not allowlisted");
  }
  const argv = [
    "-m",
    "temporal_memory.ingest.cli",
    "import",
    "browser",
    profileDir,
    "--owner",
    owner,
    "--no-split",
  ];
  await runner(deps)(deps.python ?? process.env.TM_PYTHON ?? "python", argv, {
    cwd: path.resolve(deps.memorySrc ?? memorySourceRoot(), ".."),
    env: { ...process.env, ...deps.env, PYTHONPATH: deps.memorySrc ?? memorySourceRoot() },
    windowsHide: true,
    encoding: "utf8",
  });
  return { argv };
}

export async function scanSessions(
  tool: AgentTool | undefined,
  since: string | undefined,
  roots: ReaderRoots,
  deps: ReaderDeps = {},
): Promise<{ count: number }> {
  const root = resolveSessionRoot(tool, roots);
  assertNotCredential(root);
  const stdout = await runPython(deps, SESSIONS_CODE, [tool ?? "claude-code", root, since ?? ""]);
  const rows = JSON.parse(stdout) as unknown[];
  return { count: rows.length };
}
