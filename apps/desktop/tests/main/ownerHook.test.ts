import type { ChildProcess } from "child_process";
import { describe, expect, it, vi } from "vitest";
import { OwnerHook, TokenStore, redactArgs, workerArgs } from "../../electron/main/ownerHook";

const TOKEN = "synthetic-bearer-token-not-real";

describe("owner hook", () => {
  it("spawns and stops with an explicit model and never logs the bearer token", () => {
    const lines: string[] = [];
    const children: Array<{ killed: boolean; exitCode: number | null; kill: () => void }> = [];
    const spawnFn = vi.fn((_command: string, args: string[]) => {
      const child = {
        killed: false,
        exitCode: null as number | null,
        kill() {
          this.killed = true;
          this.exitCode = 0;
        },
      };
      children.push(child);
      expect(args).toEqual(workerArgs(args[0], { model: "claude-sonnet", token: TOKEN, url: "http://127.0.0.1:8000/mcp", owner: "karim" }));
      return child as unknown as ChildProcess;
    });

    const hook = new OwnerHook({ info: (line) => lines.push(line) }, spawnFn, "python", "agent_worker.py");
    const started = hook.start({
      model: "claude-sonnet",
      token: TOKEN,
      url: "http://127.0.0.1:8000/mcp",
      owner: "karim",
    });
    expect(started).toEqual({ running: true, model: "claude-sonnet" });
    expect(hook.status().running).toBe(true);
    expect(spawnFn).toHaveBeenCalledWith(
      "python",
      expect.arrayContaining(["--model", "claude-sonnet", "--token", TOKEN, "--runner", "owner-hook"]),
      expect.objectContaining({ windowsHide: true }),
    );
    expect(lines.join("\n")).toContain("--model claude-sonnet");
    expect(lines.join("\n")).toContain("[redacted]");
    expect(lines.join("\n")).not.toContain(TOKEN);
    expect(redactArgs(["python", "--token", TOKEN])).toEqual(["python", "--token", "[redacted]"]);

    hook.stop();
    expect(children[0].killed).toBe(true);
    expect(hook.status().running).toBe(false);
    expect(lines.at(-1)).toBe("owner-hook stop");
  });

  it("stores a token as ciphertext and reports only a mask", () => {
    const lines: string[] = [];
    const vault = {
      isEncryptionAvailable: () => true,
      encryptString: (value: string) => Buffer.from(`enc:${value}`),
      decryptString: (value: Buffer) => value.toString("utf8").replace(/^enc:/, ""),
    };
    const store = new TokenStore(vault, { info: (line) => lines.push(line) });
    store.save(TOKEN);
    expect(store.status()).toEqual({ stored: true, masked: "••••••••", encryptionAvailable: true });
    expect(lines.join("\n")).not.toContain(TOKEN);
    let seen = "";
    store.withToken((token) => {
      seen = token;
    });
    expect(seen).toBe(TOKEN);
    expect(JSON.stringify(store.status())).not.toContain(TOKEN);
  });
});
