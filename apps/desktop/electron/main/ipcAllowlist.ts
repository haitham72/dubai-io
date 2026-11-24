/**
 * Typed IPC allowlist. The renderer may invoke only these channels,
 * and payloads cannot carry filesystem roots or shell strings.
 */

export const IPC = {
  sessionsScan: "sessions:scan",
  sessionsResume: "sessions:resumeCommand",
  browserPreview: "browser:preview",
  browserImport: "browser:import",
  hookStatus: "hook:status",
  hookToggle: "hook:toggle",
  tokenStatus: "token:status",
  syncStatus: "sync:status",
  syncConfigure: "sync:configure",
  syncRun: "sync:run",
} as const;

export type IpcChannel = (typeof IPC)[keyof typeof IPC];

const CHANNEL_SET = new Set<string>(Object.values(IPC));

const FORBIDDEN_KEYS = new Set([
  "shell",
  "command",
  "cmd",
  "root",
  "roots",
  "path",
  "profileDir",
  "profilePath",
  "args",
  "argv",
  "cwdRaw",
]);

export type AgentTool = "claude-code" | "codex";
export type BrowserKind = "chrome" | "edge" | "brave";

export interface SessionsScanPayload {
  tool?: AgentTool;
  since?: string;
}

export interface ResumePayload {
  agentTool: AgentTool;
  sessionId: string;
  cwd: string;
}

export interface BrowserPayload {
  browser: BrowserKind;
  profileName: string;
  consent?: boolean;
}

export interface HookTogglePayload {
  enabled: boolean;
  model?: string;
  url?: string;
  owner?: string;
}

export const SYNC_SOURCE_NAMES = ["chrome", "edge", "claude-code", "codex"] as const;
export type SyncSourceName = (typeof SYNC_SOURCE_NAMES)[number];

export interface SyncConfigurePayload {
  enabledSources: SyncSourceName[];
  intervalMinutes: 60;
  syncOnFocus: boolean;
}

const TOOLS = new Set<AgentTool>(["claude-code", "codex"]);
const SYNC_SOURCE_SET = new Set<string>(SYNC_SOURCE_NAMES);
const BROWSERS = new Set<BrowserKind>(["chrome", "edge", "brave"]);
const SESSION_ID = /^[A-Za-z0-9_-]{1,128}$/;
const DAY = /^\d{4}-\d{2}-\d{2}$/;
const PROFILE_NAME = /^[A-Za-z0-9][A-Za-z0-9 ._-]{0,80}$/;

export function assertChannel(channel: string): IpcChannel {
  if (!CHANNEL_SET.has(channel)) {
    throw new Error(`IPC channel is not allowlisted: ${channel}`);
  }
  return channel as IpcChannel;
}

function rejectForbidden(payload: object): void {
  for (const key of Object.keys(payload)) {
    if (FORBIDDEN_KEYS.has(key)) {
      throw new Error(`IPC payload cannot include ${key}`);
    }
  }
}

export function parseSessionsScan(payload: unknown): SessionsScanPayload {
  const body = asRecord(payload);
  rejectForbidden(body);
  const tool = body.tool === undefined ? undefined : asTool(body.tool);
  const since = body.since === undefined ? undefined : asDay(body.since);
  return { tool, since };
}

export function parseResume(payload: unknown): ResumePayload {
  const body = asRecord(payload);
  rejectForbidden(body);
  const cwd = asString(body.cwd, "cwd");
  if (/[;&|`]/.test(cwd)) {
    throw new Error("cwd contains shell metacharacters");
  }
  return {
    agentTool: asTool(body.agentTool),
    sessionId: asSessionId(body.sessionId),
    cwd,
  };
}

export function parseBrowser(payload: unknown, kind: "preview" | "import"): BrowserPayload {
  const body = asRecord(payload);
  rejectForbidden(body);
  const browser = asBrowser(body.browser);
  const profileName = asString(body.profileName, "profileName");
  if (!PROFILE_NAME.test(profileName) || profileName.includes("..") || /[\\/]/.test(profileName)) {
    throw new Error("profileName must be a single allowlisted folder name");
  }
  const consent = body.consent === true;
  if (kind === "import" && !consent) {
    throw new Error("browser import requires explicit consent");
  }
  return { browser, profileName, consent };
}

export function parseHookToggle(payload: unknown): HookTogglePayload {
  const body = asRecord(payload);
  rejectForbidden(body);
  if (typeof body.enabled !== "boolean") {
    throw new Error("hook toggle requires enabled: boolean");
  }
  return {
    enabled: body.enabled,
    model: body.model === undefined ? undefined : asString(body.model, "model"),
    url: body.url === undefined ? undefined : asString(body.url, "url"),
    owner: body.owner === undefined ? undefined : asString(body.owner, "owner"),
  };
}

export function parseSyncConfigure(payload: unknown): SyncConfigurePayload {
  const body = asRecord(payload);
  rejectForbidden(body);
  const raw = body.enabledSources;
  if (!Array.isArray(raw)) throw new Error("enabledSources must be a list");
  const enabledSources: SyncSourceName[] = [];
  for (const item of raw) {
    if (typeof item !== "string" || !SYNC_SOURCE_SET.has(item)) {
      throw new Error("sync source is not allowlisted");
    }
    enabledSources.push(item as SyncSourceName);
  }
  if (body.intervalMinutes !== undefined && body.intervalMinutes !== 60) {
    throw new Error("interval must be 60 minutes");
  }
  return {
    enabledSources,
    intervalMinutes: 60,
    syncOnFocus: body.syncOnFocus === true,
  };
}

function asRecord(payload: unknown): Record<string, unknown> {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("IPC payload must be an object");
  }
  return payload as Record<string, unknown>;
}

function asString(value: unknown, name: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${name} must be a non-empty string`);
  }
  return value;
}

function asTool(value: unknown): AgentTool {
  if (typeof value !== "string" || !TOOLS.has(value as AgentTool)) {
    throw new Error("agent tool must be claude-code or codex");
  }
  return value as AgentTool;
}

function asBrowser(value: unknown): BrowserKind {
  if (typeof value !== "string" || !BROWSERS.has(value as BrowserKind)) {
    throw new Error("browser must be chrome, edge, or brave");
  }
  return value as BrowserKind;
}

function asSessionId(value: unknown): string {
  if (typeof value !== "string" || !SESSION_ID.test(value)) {
    throw new Error("sessionId is not an allowlisted id");
  }
  return value;
}

function asDay(value: unknown): string {
  if (typeof value !== "string" || !DAY.test(value)) {
    throw new Error("since must be YYYY-MM-DD");
  }
  return value;
}
