import { describe, expect, it } from "vitest";
import {
  IPC,
  assertChannel,
  parseBrowser,
  parseResume,
  parseSessionsScan,
} from "../../electron/main/ipcAllowlist";
import { webPreferencesBase } from "../../electron/main/security";

describe("ipc allowlist", () => {
  it("accepts the seven desktop channels and rejects anything else", () => {
    expect(assertChannel(IPC.sessionsScan)).toBe("sessions:scan");
    expect(assertChannel(IPC.browserPreview)).toBe("browser:preview");
    expect(assertChannel(IPC.hookToggle)).toBe("hook:toggle");
    expect(assertChannel(IPC.tokenStatus)).toBe("token:status");
    expect(() => assertChannel("fs:read")).toThrow(/not allowlisted/i);
    expect(() => assertChannel("shell:exec")).toThrow(/not allowlisted/i);
  });

  it("refuses filesystem roots, raw commands, and unconfirmed browser import", () => {
    expect(parseSessionsScan({ tool: "codex", since: "2026-11-17" })).toEqual({
      tool: "codex",
      since: "2026-11-17",
    });
    expect(() => parseSessionsScan({ root: "C:\\Users\\karim\\.claude" })).toThrow(/root/i);
    expect(() => parseResume({ agentTool: "claude-code", sessionId: "abc", command: "claude --resume abc" })).toThrow(
      /command/i,
    );
    expect(() => parseBrowser({ browser: "chrome", profileDir: "C:\\secret" }, "preview")).toThrow(/profileDir/i);
    expect(() => parseBrowser({ browser: "chrome", profileName: "..\\Default" }, "preview")).toThrow(/profileName/i);
    expect(() => parseBrowser({ browser: "chrome", profileName: "Default" }, "import")).toThrow(/consent/i);
    expect(parseBrowser({ browser: "edge", profileName: "Default", consent: true }, "import").consent).toBe(true);
  });

  it("locks the preload window to context isolation without node integration", () => {
    expect(webPreferencesBase).toEqual({
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
    });
  });
});
