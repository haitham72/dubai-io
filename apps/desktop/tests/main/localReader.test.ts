import fs from "fs";
import os from "os";
import path from "path";
import { describe, expect, it, vi } from "vitest";
import {
  assertInsideRoot,
  assertSafePath,
  buildResumeArgs,
  importBrowser,
  previewBrowser,
  scanSessions,
  type ExecFileFn,
  type ReaderRoots,
} from "../../electron/main/localReader";

const FIXTURES = path.resolve(__dirname, "../../../memory/tests/fixtures/desktop");

function tempRoots(): { dir: string; roots: ReaderRoots } {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "dubai-desktop-"));
  const roots: ReaderRoots = {
    claudeProjects: path.join(dir, "claude", "projects"),
    codexSessions: path.join(dir, "codex", "sessions"),
    browsers: {
      chrome: path.join(dir, "chrome"),
      edge: path.join(dir, "edge"),
      brave: path.join(dir, "brave"),
    },
  };
  fs.mkdirSync(roots.claudeProjects, { recursive: true });
  fs.mkdirSync(roots.codexSessions, { recursive: true });
  fs.mkdirSync(roots.browsers.chrome, { recursive: true });
  return { dir, roots };
}

describe("local reader guards", () => {
  it("blocks credential filenames before any process spawn", async () => {
    const { dir, roots } = tempRoots();
    const execFile = vi.fn<ExecFileFn>();
    const blocked = [
      ".credentials.json",
      "auth.json",
      "Cookies",
      "Login Data",
      ".env",
      "session.token",
      "api.key",
    ];
    for (const name of blocked) {
      const target = path.join(roots.claudeProjects, name);
      fs.writeFileSync(target, "synthetic", "utf8");
      expect(() => assertSafePath(target, roots.claudeProjects)).toThrow(/credential/i);
    }
    await expect(previewBrowser(path.join(roots.browsers.chrome, "Cookies"), roots.browsers.chrome, { execFile })).rejects.toThrow(
      /credential/i,
    );
    expect(execFile).not.toHaveBeenCalled();
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("rejects a symlink that leaves the allowlisted root", () => {
    const { dir, roots } = tempRoots();
    const outside = path.join(dir, "outside");
    fs.mkdirSync(outside);
    fs.writeFileSync(path.join(outside, "secret.txt"), "synthetic", "utf8");
    const link = path.join(roots.claudeProjects, "escape");
    fs.symlinkSync(outside, link, "junction");
    expect(() => assertInsideRoot(link, roots.claudeProjects)).toThrow(/escapes/i);
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("rejects a cwd with shell metacharacters and builds a display-safe argv", () => {
    const cwd = fs.mkdtempSync(path.join(os.tmpdir(), "dubai-cwd-"));
    expect(() => buildResumeArgs("claude-code", "sess_1", `${cwd};rm`)).toThrow(/metacharacter/i);
    expect(() => buildResumeArgs("codex", "sess_1", cwd + " & calc")).toThrow(/metacharacter/i);
    expect(buildResumeArgs("claude-code", "sess_1", cwd)).toEqual({
      argv: ["claude", "--resume", "sess_1"],
      cwd,
    });
    expect(buildResumeArgs("codex", "sess_1", cwd)).toEqual({
      argv: ["codex", "resume", "sess_1"],
      cwd,
    });
    fs.rmSync(cwd, { recursive: true, force: true });
  });

  it("points session scan and browser import at the memory package with an argv array", async () => {
    const { dir, roots } = tempRoots();
    const sessionDir = path.join(roots.claudeProjects, "project-a");
    fs.mkdirSync(sessionDir);
    fs.copyFileSync(path.join(FIXTURES, "claude-session.jsonl"), path.join(sessionDir, "session.jsonl"));
    const profile = path.join(roots.browsers.chrome, "Default");
    fs.mkdirSync(profile);
    fs.copyFileSync(path.join(FIXTURES, "Bookmarks"), path.join(profile, "Bookmarks"));

    const execFile = vi.fn<ExecFileFn>(async (_file, args) => {
      if (args[0] === "-c" && String(args[1]).includes("agent_session_records")) return { stdout: "[]", stderr: "" };
      if (args[0] === "-m") return { stdout: "", stderr: "" };
      return { stdout: "{}", stderr: "" };
    });

    const scan = await scanSessions("claude-code", "2026-11-17", roots, { execFile, python: "python" });
    expect(scan.count).toBe(0);
    const scanArgs = execFile.mock.calls[0][1];
    expect(scanArgs[0]).toBe("-c");
    expect(scanArgs).toContain(roots.claudeProjects);
    expect(scanArgs.slice(2).join(" ")).not.toMatch(/[;&|`]/);

    const imported = await importBrowser(profile, roots.browsers.chrome, "karim", { execFile, python: "python" });
    expect(imported.argv).toEqual([
      "-m",
      "temporal_memory.ingest.cli",
      "import",
      "browser",
      profile,
      "--owner",
      "karim",
      "--no-split",
    ]);
    expect(execFile.mock.calls.every((call) => !("shell" in (call[2] ?? {})))).toBe(true);
    fs.rmSync(dir, { recursive: true, force: true });
  });
});
