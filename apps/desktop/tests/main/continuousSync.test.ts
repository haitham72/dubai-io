import fs from "fs";
import os from "os";
import path from "path";
import { describe, expect, it, vi } from "vitest";
import { ContinuousSync, type PacketReader, type SyncCandidate, type SyncSource } from "../../electron/main/continuousSync";

function candidate(source: SyncSource, hash: string, target: string, root: string): SyncCandidate {
  return { source, contentHash: hash, day: "2026-11-24", target, root };
}

describe("continuous sync", () => {
  it("pulls only consented sources, skips a repeated content hash, and refuses a credential path", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "dubai-sync-"));
    const root = path.join(dir, "notes");
    fs.mkdirSync(root);
    const note = path.join(root, "typography.txt");
    fs.writeFileSync(note, "synthetic karim note", "utf8");
    const cookies = path.join(root, "Cookies");
    fs.writeFileSync(cookies, "synthetic", "utf8");

    const calls: SyncSource[] = [];
    const reader: PacketReader = {
      list(source) {
        calls.push(source);
        if (source === "chrome") return [candidate("chrome", "hash-typography", note, root)];
        if (source === "edge") return [candidate("edge", "hash-edge", note, root)];
        return [];
      },
    };
    const sync = new ContinuousSync(reader);
    sync.configure(["chrome"], false);
    const first = sync.runSyncNow("2026-11-24T04:00:00Z");
    expect(calls).toEqual(["chrome"]);
    expect(first.enqueued.map((row) => row.contentHash)).toEqual(["hash-typography"]);
    expect(first.status.intervalMinutes).toBe(60);
    expect(first.status.lastSyncAt).toBe("2026-11-24T04:00:00Z");

    const second = sync.runSyncNow("2026-11-24T05:00:00Z");
    expect(second.enqueued).toEqual([]);
    expect(second.skipped).toBe(1);
    expect(calls.filter((source) => source !== "chrome")).toEqual([]);

    const denied = vi.fn();
    const blocked = new ContinuousSync({
      list() {
        denied();
        return [candidate("chrome", "hash-cookies", cookies, root)];
      },
    });
    blocked.configure(["chrome", "claude-code"], true);
    expect(() => blocked.runSyncNow()).toThrow(/credential/i);
    expect(denied).toHaveBeenCalledOnce();
    expect(blocked.status().enqueued).toBe(0);

    fs.rmSync(dir, { recursive: true, force: true });
  });
});
