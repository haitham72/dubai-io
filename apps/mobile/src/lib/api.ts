import { OFFLINE_ASSISTANT_REPLY, demoRepair } from "./fixtures";
import type { MemoryTurnConfirmation, RepairPing } from "./types";

export const ENDPOINTS = {
  health: "/api/health",
  lunaTurn: "/api/luna/turn",
  memoryChatTurn: "/api/memory/chat/turn",
  memoryChatPings: "/api/memory/chat/pings",
} as const;

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

export function defaultApiBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL?.trim();
  return fromEnv && fromEnv.length > 0 ? fromEnv.replace(/\/$/, "") : "";
}

/** A physical iPhone cannot open the PC's localhost. Warn whenever that host is configured. */
export function localhostWarning(baseUrl: string): string | null {
  const trimmed = baseUrl.trim();
  if (!trimmed) {
    return "Set your PC LAN IP (http://192.168.x.x:8000) or the Expo tunnel URL. A phone cannot use localhost.";
  }
  let host = "";
  try {
    host = new URL(trimmed).hostname.toLowerCase();
  } catch {
    return "API base URL is not a valid URL. Use http://192.168.x.x:8000 or a tunnel URL.";
  }
  if (LOCAL_HOSTS.has(host)) {
    return "localhost is not reachable from a physical iPhone. Use your PC LAN IP or an Expo tunnel URL.";
  }
  return null;
}

export function isIngestConfirmed(
  body: { ok?: boolean; applied?: boolean } | null | undefined,
  meta: { demo: boolean; httpOk: boolean },
): boolean {
  if (!body || meta.demo || !meta.httpOk) return false;
  return body.applied === true || body.ok === true;
}

export interface RequestDeps {
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

async function request(
  url: string,
  init: RequestInit,
  deps: RequestDeps,
): Promise<Response> {
  const fetchImpl = deps.fetchImpl ?? fetch;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), deps.timeoutMs ?? 8000);
  try {
    return await fetchImpl(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function joinUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

export async function getHealth(baseUrl: string, deps: RequestDeps = {}): Promise<boolean> {
  if (!baseUrl.trim() || localhostWarning(baseUrl)) {
    try {
      const response = await request(joinUrl(baseUrl || "http://127.0.0.1", ENDPOINTS.health), { method: "GET" }, deps);
      return response.ok;
    } catch {
      return false;
    }
  }
  try {
    const response = await request(joinUrl(baseUrl, ENDPOINTS.health), { method: "GET" }, deps);
    return response.ok;
  } catch {
    return false;
  }
}

interface TurnBody {
  ok?: boolean;
  applied?: boolean;
  applied_fact_ids?: string[];
  reply?: string;
  text?: string;
  trust?: string;
  topic?: string;
}

function readTurn(body: TurnBody, httpOk: boolean, warning: string | null): MemoryTurnConfirmation {
  const appliedFactIds = Array.isArray(body.applied_fact_ids) ? body.applied_fact_ids.filter((id) => typeof id === "string") : [];
  const confirmed = isIngestConfirmed(body, { demo: false, httpOk });
  return {
    ok: body.ok === true,
    applied: body.applied === true,
    appliedFactIds,
    reply: typeof body.reply === "string" ? body.reply : typeof body.text === "string" ? body.text : "",
    trust: confirmed && typeof body.trust === "string" ? body.trust : undefined,
    topic: confirmed && typeof body.topic === "string" ? body.topic : undefined,
    demo: false,
    warning,
  };
}

function offlineTurn(warning: string | null): MemoryTurnConfirmation {
  return {
    ok: false,
    applied: false,
    appliedFactIds: [],
    reply: OFFLINE_ASSISTANT_REPLY,
    demo: true,
    warning,
  };
}

export async function postMemoryChatTurn(
  baseUrl: string,
  input: { ownerId: string; text: string },
  deps: RequestDeps = {},
): Promise<MemoryTurnConfirmation> {
  const warning = localhostWarning(baseUrl);
  if (!baseUrl.trim()) return offlineTurn(warning);
  try {
    const response = await request(
      joinUrl(baseUrl, ENDPOINTS.memoryChatTurn),
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ owner: input.ownerId, text: input.text }),
      },
      deps,
    );
    if (!response.ok) return offlineTurn(warning);
    const body = (await response.json()) as TurnBody;
    const turn = readTurn(body, true, warning);
    if (!isIngestConfirmed(body, { demo: false, httpOk: true }) && !turn.reply) {
      return { ...offlineTurn(warning), ok: turn.ok, applied: turn.applied };
    }
    return turn;
  } catch {
    return offlineTurn(warning);
  }
}

export async function postLunaTurn(
  baseUrl: string,
  input: { ownerId: string; text: string },
  deps: RequestDeps = {},
): Promise<{ ok: boolean; reply: string; demo: boolean; warning: string | null }> {
  const warning = localhostWarning(baseUrl);
  if (!baseUrl.trim()) {
    return { ok: false, reply: OFFLINE_ASSISTANT_REPLY, demo: true, warning };
  }
  try {
    const response = await request(
      joinUrl(baseUrl, ENDPOINTS.lunaTurn),
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ owner: input.ownerId, text: input.text }),
      },
      deps,
    );
    if (!response.ok) return { ok: false, reply: OFFLINE_ASSISTANT_REPLY, demo: true, warning };
    const body = (await response.json()) as { ok?: boolean; reply?: string; text?: string };
    return {
      ok: body.ok === true,
      reply: body.reply || body.text || "",
      demo: false,
      warning,
    };
  } catch {
    return { ok: false, reply: OFFLINE_ASSISTANT_REPLY, demo: true, warning };
  }
}

export async function getMemoryPings(
  baseUrl: string,
  deps: RequestDeps = {},
): Promise<{ pings: RepairPing[]; demo: boolean; warning: string | null }> {
  const warning = localhostWarning(baseUrl);
  if (!baseUrl.trim()) return { pings: [demoRepair], demo: true, warning };
  try {
    const response = await request(joinUrl(baseUrl, ENDPOINTS.memoryChatPings), { method: "GET" }, deps);
    if (!response.ok) return { pings: [demoRepair], demo: true, warning };
    const body = (await response.json()) as { pings?: RepairPing[] };
    if (!Array.isArray(body.pings)) return { pings: [demoRepair], demo: true, warning };
    return { pings: body.pings, demo: false, warning };
  } catch {
    return { pings: [demoRepair], demo: true, warning };
  }
}
