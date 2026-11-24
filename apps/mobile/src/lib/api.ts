import { OFFLINE_ASSISTANT_REPLY, demoRepair } from "./fixtures";
import type { ChatCitation, LifeTheme, MemoryTurnConfirmation, Provenance, RepairPing, TodayCard } from "./types";

export const ENDPOINTS = {
  health: "/api/health",
  lunaTurn: "/api/luna/turn",
  chatTurn: "/api/chat/turn",
  today: "/api/today",
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
  body: { ok?: boolean; applied?: boolean; ingested?: boolean } | null | undefined,
  meta: { demo: boolean; httpOk: boolean },
): boolean {
  if (!body || meta.demo || !meta.httpOk) return false;
  return body.ingested === true || body.applied === true || body.ok === true;
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
  ingested?: boolean;
  applied?: boolean;
  applied_fact_ids?: string[];
  citations?: unknown[];
  reply?: string;
  text?: string;
  runner?: string;
  model?: string;
  as_of?: string;
  trust?: string;
  topic?: string;
}

function parseCitations(raw: unknown): ChatCitation[] {
  if (!Array.isArray(raw)) return [];
  const out: ChatCitation[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const rec = item as Record<string, unknown>;
    const factId = typeof rec.fact_id === "string" ? rec.fact_id : "";
    const text = typeof rec.text === "string" ? rec.text : "";
    if (!factId && !text) continue;
    out.push({
      fact_id: factId,
      text,
      why_url: typeof rec.why_url === "string" ? rec.why_url : undefined,
      provenance: typeof rec.provenance === "string" ? rec.provenance : undefined,
      as_of: typeof rec.as_of === "string" ? rec.as_of : undefined,
    });
  }
  return out;
}

function readTurn(body: TurnBody, httpOk: boolean, warning: string | null): MemoryTurnConfirmation {
  const citations = parseCitations(body.citations);
  const appliedFactIds = Array.isArray(body.applied_fact_ids)
    ? body.applied_fact_ids.filter((id) => typeof id === "string")
    : citations.map((c) => c.fact_id).filter(Boolean);
  const ingested = body.ingested === true || body.applied === true;
  const confirmed = isIngestConfirmed(body, { demo: false, httpOk });
  return {
    ok: body.ok === true,
    ingested,
    applied: ingested,
    appliedFactIds,
    citations,
    reply: typeof body.reply === "string" ? body.reply : typeof body.text === "string" ? body.text : "",
    runner: typeof body.runner === "string" ? body.runner : undefined,
    model: typeof body.model === "string" ? body.model : undefined,
    asOf: typeof body.as_of === "string" ? body.as_of : undefined,
    trust: confirmed && typeof body.trust === "string" ? body.trust : undefined,
    topic: confirmed && typeof body.topic === "string" ? body.topic : undefined,
    demo: false,
    warning,
  };
}

function errorTurn(warning: string | null, error: string, demoFallback = false): MemoryTurnConfirmation {
  return {
    ok: false,
    ingested: false,
    applied: false,
    appliedFactIds: [],
    citations: [],
    reply: demoFallback ? OFFLINE_ASSISTANT_REPLY : "",
    demo: demoFallback,
    warning,
    error,
  };
}

/** E4 chat endpoint: POST /api/chat/turn with X-App-Session header. */
export async function postChatTurn(
  baseUrl: string,
  input: { text: string; threadId?: string; sessionToken?: string | null; demo?: boolean },
  deps: RequestDeps = {},
): Promise<MemoryTurnConfirmation> {
  const warning = localhostWarning(baseUrl);
  const demoFallback = input.demo === true;
  if (!baseUrl.trim()) {
    return errorTurn(warning, "Set your API Server URL in Connect to chat.", demoFallback);
  }
  if (!input.sessionToken && !demoFallback) {
    return errorTurn(warning, "Sign in on Connect to chat with your memory.", false);
  }
  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (input.sessionToken) {
      headers["X-App-Session"] = input.sessionToken;
    }
    const response = await request(
      joinUrl(baseUrl, ENDPOINTS.chatTurn),
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          text: input.text,
          thread_id: input.threadId ?? "default",
        }),
      },
      deps,
    );
    if (!response.ok) {
      const msg =
        response.status === 401
          ? "Session expired or invalid. Sign in again on Connect."
          : `Chat service returned HTTP ${response.status}. Nothing was ingested.`;
      return errorTurn(warning, msg, demoFallback);
    }
    const body = (await response.json()) as TurnBody;
    return readTurn(body, true, warning);
  } catch {
    return errorTurn(warning, "Unable to reach chat service. Nothing was ingested.", demoFallback);
  }
}

export async function postMemoryChatTurn(
  baseUrl: string,
  input: { ownerId: string; text: string; sessionToken?: string | null; demo?: boolean },
  deps: RequestDeps = {},
): Promise<MemoryTurnConfirmation> {
  const warning = localhostWarning(baseUrl);
  const demoFallback = input.demo === true;
  if (!baseUrl.trim()) return errorTurn(warning, "API server URL is not set.", demoFallback);
  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (input.sessionToken) headers["X-App-Session"] = input.sessionToken;
    const response = await request(
      joinUrl(baseUrl, ENDPOINTS.memoryChatTurn),
      {
        method: "POST",
        headers,
        body: JSON.stringify({ owner: input.ownerId, text: input.text }),
      },
      deps,
    );
    if (!response.ok) return errorTurn(warning, `Chat error (${response.status})`, demoFallback);
    const body = (await response.json()) as TurnBody;
    const turn = readTurn(body, true, warning);
    if (!isIngestConfirmed(body, { demo: false, httpOk: true }) && !turn.reply) {
      return { ...errorTurn(warning, "Memory service did not confirm turn.", demoFallback), ok: turn.ok, applied: turn.applied };
    }
    return turn;
  } catch {
    return errorTurn(warning, "Unable to reach the memory service.", demoFallback);
  }
}

export async function postLunaTurn(
  baseUrl: string,
  input: { ownerId: string; text: string },
  deps: RequestDeps = {},
): Promise<{ ok: boolean; reply: string; demo: boolean; warning: string | null }> {
  const warning = localhostWarning(baseUrl);
  if (!baseUrl.trim()) {
    return { ok: false, reply: "", demo: false, warning };
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
    if (!response.ok) return { ok: false, reply: "", demo: false, warning };
    const body = (await response.json()) as { ok?: boolean; reply?: string; text?: string };
    return {
      ok: body.ok === true,
      reply: body.reply || body.text || "",
      demo: false,
      warning,
    };
  } catch {
    return { ok: false, reply: "", demo: false, warning };
  }
}

export interface TodayFeedResponse {
  cards: TodayCard[];
  emptyReason: string | null;
  asOf: string | null;
  status: "ok" | "not_ready" | "unauthenticated" | "offline";
}

function toneForCategory(category: unknown, interest: unknown): LifeTheme {
  const raw = `${String(category ?? "")} ${String(interest ?? "")}`.toLowerCase();
  if (raw.includes("game") || raw.includes("hardware")) return "gaming";
  if (raw.includes("career") || raw.includes("work")) return "career";
  if (raw.includes("learn") || raw.includes("study")) return "learning";
  if (raw.includes("travel") || raw.includes("place")) return "travel";
  if (raw.includes("health")) return "health";
  return "projects";
}

function parseProvenance(value: unknown): Provenance {
  const allowed: Provenance[] = [
    "official",
    "provider_confirmed",
    "merchant_submitted",
    "user_supplied",
    "inferred",
    "estimate",
    "demo_fixture",
  ];
  return typeof value === "string" && allowed.includes(value as Provenance) ? (value as Provenance) : "inferred";
}

/** E4 Today feed: GET /api/today with X-App-Session header. Never returns demo cards. */
export async function getTodayFeed(
  baseUrl: string,
  input: { sessionToken?: string | null },
  deps: RequestDeps = {},
): Promise<TodayFeedResponse> {
  if (!baseUrl.trim()) {
    return { cards: [], emptyReason: "Connect to your API server in Connect.", asOf: null, status: "offline" };
  }
  if (!input.sessionToken) {
    return { cards: [], emptyReason: "Sign in on Connect to load your Today feed.", asOf: null, status: "unauthenticated" };
  }
  try {
    const res = await request(
      joinUrl(baseUrl, ENDPOINTS.today),
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          "X-App-Session": input.sessionToken,
        },
      },
      deps,
    );
    if (res.status === 401) {
      return { cards: [], emptyReason: "Session expired. Sign in again on Connect.", asOf: null, status: "unauthenticated" };
    }
    if (res.status === 404 || !res.ok) {
      return { cards: [], emptyReason: null, asOf: null, status: "not_ready" };
    }
    const body = (await res.json()) as {
      cards?: Array<Record<string, unknown>>;
      empty_reason?: string | null;
      as_of?: string | null;
    };
    const asOf = typeof body.as_of === "string" ? body.as_of : null;
    const rawCards = Array.isArray(body.cards) ? body.cards : [];
    const cards: TodayCard[] = rawCards.map((c, idx) => ({
      id: typeof c.id === "string" && c.id ? c.id : `card-${idx}`,
      interest: typeof c.interest === "string" ? c.interest : undefined,
      category: typeof c.category === "string" ? c.category : undefined,
      title: typeof c.title === "string" ? c.title : "",
      subtitle: typeof c.subtitle === "string" ? c.subtitle : undefined,
      eyebrow: typeof c.category === "string" ? c.category : typeof c.interest === "string" ? c.interest : undefined,
      imageUrl: typeof c.image_url === "string" ? c.image_url : null,
      source: typeof c.source === "string" ? c.source : undefined,
      url: typeof c.url === "string" ? c.url : null,
      because: typeof c.because === "string" ? c.because : "",
      tone: toneForCategory(c.category, c.interest),
      demo: false,
      provenance: parseProvenance(c.provenance),
      asOf: typeof c.as_of === "string" ? c.as_of : asOf ?? "",
    }));
    if (cards.length === 0) {
      return {
        cards: [],
        emptyReason: typeof body.empty_reason === "string" ? body.empty_reason : null,
        asOf,
        status: "not_ready",
      };
    }
    return { cards, emptyReason: null, asOf, status: "ok" };
  } catch {
    return { cards: [], emptyReason: "Could not reach the API server.", asOf: null, status: "offline" };
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
