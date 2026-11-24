import { createHash } from "crypto";
import fs from "fs";
import path from "path";
import { assertSafePath, credentialSegment, type ReaderRoots } from "./localReader";

export const SYNC_SOURCES = ["chrome", "edge", "claude-code", "codex"] as const;
export type SyncSource = (typeof SYNC_SOURCES)[number];

export interface SyncCandidate {
  source: SyncSource;
  contentHash: string;
  day: string;
  target: string;
  root: string;
}

export interface PacketReader {
  list(source: SyncSource): SyncCandidate[];
}

export interface SyncStatus {
  enabledSources: SyncSource[];
  intervalMinutes: 60;
  syncOnFocus: boolean;
  lastSyncAt: string | null;
  enqueued: number;
}

export interface SyncRunResult {
  enqueued: SyncCandidate[];
  skipped: number;
  status: SyncStatus;
}

const SOURCE_SET = new Set<string>(SYNC_SOURCES);

export function isSyncSource(value: string): value is SyncSource {
  return SOURCE_SET.has(value);
}

/**
 * Opt-in pull. Disabled sources are never listed. Each candidate must pass
 * localReader R1 (credential denylist + symlink/root escape) before it can
 * be enqueued, and a repeated content_hash is skipped.
 */
export class ContinuousSync {
  private enabled = new Set<SyncSource>();
  private seen = new Set<string>();
  syncOnFocus = false;
  lastSyncAt: string | null = null;
  private enqueued = 0;

  constructor(private readonly reader: PacketReader) {}

  configure(sources: SyncSource[], syncOnFocus: boolean): SyncStatus {
    this.enabled = new Set(sources);
    this.syncOnFocus = syncOnFocus;
    return this.status();
  }

  status(): SyncStatus {
    return {
      enabledSources: SYNC_SOURCES.filter((source) => this.enabled.has(source)),
      intervalMinutes: 60,
      syncOnFocus: this.syncOnFocus,
      lastSyncAt: this.lastSyncAt,
      enqueued: this.enqueued,
    };
  }

  runSyncNow(now = new Date().toISOString()): SyncRunResult {
    const fresh: SyncCandidate[] = [];
    let skipped = 0;
    for (const source of SYNC_SOURCES) {
      if (!this.enabled.has(source)) continue;
      for (const candidate of this.reader.list(source)) {
        assertSafePath(candidate.target, candidate.root);
        if (this.seen.has(candidate.contentHash)) {
          skipped += 1;
          continue;
        }
        this.seen.add(candidate.contentHash);
        fresh.push(candidate);
      }
    }
    this.enqueued += fresh.length;
    this.lastSyncAt = now;
    return { enqueued: fresh, skipped, status: this.status() };
  }
}

function sourceRoot(source: SyncSource, roots: ReaderRoots): string {
  if (source === "chrome") return roots.browsers.chrome;
  if (source === "edge") return roots.browsers.edge;
  if (source === "codex") return roots.codexSessions;
  return roots.claudeProjects;
}

function walkFiles(root: string, visit: (file: string) => void): void {
  if (!fs.existsSync(root)) return;
  const entries = fs.readdirSync(root, { withFileTypes: true });
  for (const entry of entries) {
    if (credentialSegment(entry.name)) continue;
    const full = path.join(root, entry.name);
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) walkFiles(full, visit);
    else if (entry.isFile()) visit(full);
  }
}

export function filesystemPacketReader(roots: ReaderRoots, now = new Date()): PacketReader {
  const day = now.toISOString().slice(0, 10);
  return {
    list(source) {
      const root = sourceRoot(source, roots);
      const packets: SyncCandidate[] = [];
      walkFiles(root, (file) => {
        const body = fs.readFileSync(file);
        packets.push({
          source,
          contentHash: createHash("sha256").update(body).digest("hex"),
          day,
          target: file,
          root,
        });
      });
      return packets;
    },
  };
}
