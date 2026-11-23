// Agents service (Python, /agents: health, voice stream, deep research, watchlist,
// Gmail, memory tasks) plus the other agents-backed routes (Diwan, stickers, GIFs)
// and the generic server probe. Every caller has a fallback, so the demo (and the
// Vercel deploy, which has no /agents) works unchanged when the service is off.
import type { DiwanEvent, MirsalTask } from "../types";
import type { ResearchResult } from "./research";
import { json } from "./http";

/** Base path of the agents service (Vite dev server proxies it to :8787). */
export const AGENTS = "/agents";

export interface ChatContextLine { sender: string; text: string }
/** POST a JSON body to the agents service. Shared with mirsal.ts; not part of the public barrel. */
export const post = async <T>(path: string, body: unknown): Promise<T> =>
  json<T>(await fetch(`${AGENTS}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }));

export interface AgentsHealth {
  ok: boolean; store: "redis" | "memory";
  live: { decisions: boolean; stt: boolean; research: boolean };
  budget: { spentUsd: number; capUsd: number; stopped: boolean };
  mail: { configured: boolean; linked: boolean; mode: "gmail" | "demo" };
}
let healthCache: { at: number; value: Promise<AgentsHealth | null> } | null = null;

/** Health of the agents service, cached for 30 s; null when it is not running. */
export function agentsHealth(force = false): Promise<AgentsHealth | null> {
  if (!force && healthCache && Date.now() - healthCache.at < 30_000) return healthCache.value;
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 1500);
  const value = fetch(`${AGENTS}/health`, { signal: ctl.signal })
    .then((r) => (r.ok ? (r.json() as Promise<AgentsHealth>) : null))
    .catch(() => null)
    .finally(() => clearTimeout(timer));
  healthCache = { at: Date.now(), value };
  return value;
}

/** Voice command stream. Protocol: agents/mirsal_agents/session.py. `sid` keeps a question and its answer together. */
export function openVoiceStream(sid: string): WebSocket {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}${AGENTS}/voice?sid=${encodeURIComponent(sid)}`);
  ws.binaryType = "arraybuffer";
  return ws;
}

export interface DeepBrief {
  id: string; topic: string; title: string; summary: string; findings: string[]; findingSources: number[][];
  sections: { heading: string; body: string }[];
  ranking: { name: string; why: string; price: string; sources: number[] }[];
  related: string[]; sources: { n: number; title: string; domain: string; url: string }[];
  stats: { searched: number; read: number; cited: number; claims: number; verified: number; seconds: number };
  status: string; mode: "live" | "demo"; createdAt: number; cached?: boolean; watch?: string;
}

export async function deepResearch(topic: string, force = false): Promise<DeepBrief> {
  return json<DeepBrief>(await fetch(`${AGENTS}/research`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ topic, force }),
  }));
}

export function briefToItem(b: DeepBrief): ResearchResult {
  return {
    mode: b.mode,
    id: b.id, title: b.title, summary: b.summary, findings: b.findings, status: b.status,
    time: new Date(b.createdAt * 1000).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
    sources: b.sources.map(({ title, domain, url }) => ({ title, domain, url })),
    sections: b.sections, ranking: b.ranking, verified: `${b.stats.verified}/${b.stats.claims}`,
  };
}

export interface WatchTopic { id: string; title: string; topic: string; every_hours: number; due: boolean; brief: DeepBrief | null }
export async function getWatchlist(): Promise<WatchTopic[]> {
  return json<WatchTopic[]>(await fetch(`${AGENTS}/watch`));
}

export interface GmailMessage {
  id: string; threadId: string; sender: string; address: string; subject: string; date: string; preview: string;
  unread: boolean; starred: boolean; category: "Primary" | "Social" | "Updates" | "Promotions"; internalDate: number; body?: string;
}
export async function getMailbox(q = "in:inbox"): Promise<{ mode: "gmail" | "demo"; messages: GmailMessage[] }> {
  return json(await fetch(`${AGENTS}/mail/messages?${new URLSearchParams({ q })}`));
}
export async function getMailMessage(id: string): Promise<GmailMessage> {
  return json<GmailMessage>(await fetch(`${AGENTS}/mail/messages/${encodeURIComponent(id)}`));
}
/** Sends from the linked Gmail test account. Call only from a visible confirmation (the server refuses otherwise). */
export async function sendMail(to: string, subject: string, body: string): Promise<{ id: string }> {
  return json(await fetch(`${AGENTS}/mail/send`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ to, subject, body, confirmed: true }),
  }));
}

/** Mirsal Updates tasks kept by the agents service (Redis), so they survive a reload. */
export async function loadTasks(): Promise<MirsalTask[]> {
  return (await json<{ tasks: MirsalTask[] }>(await fetch(`${AGENTS}/memory/tasks`))).tasks;
}
export async function saveTasks(tasks: MirsalTask[]): Promise<void> {
  await fetch(`${AGENTS}/memory/tasks`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tasks }) });
}

/** Which live services the Vercel/dev API has configured (booleans only). */
export async function serverHealth(): Promise<{ openai: boolean; images: boolean; flights: boolean } | null> {
  try { return await json(await fetch("/api/health")); } catch { return null; }
}

/* ---------- Diwan: today's and upcoming UAE events (agents service → Diwan MCP; pictures from Supabase Storage) ---------- */
export async function getDiwanEvents(): Promise<{ events: DiwanEvent[]; mode: "live" | "demo" }> {
  return json(await fetch(`${AGENTS}/diwan/events`));
}
/** "More from this picture": versions Diwan already holds of one event picture (Diwan MCP `more_from_image`). */
export async function moreFromEventPicture(event: string, image: string): Promise<{ images: { url: string; width?: number; height?: number }[]; source: string }> {
  return json(await fetch(`${AGENTS}/diwan/more?${new URLSearchParams({ event, image })}`));
}

/* ---------- stickers from Mirsal Builder (3 options to swipe) and GIFs ---------- */
export interface BuilderOption { id: string; title: string; stickers: { url: string; format: string; emoji?: string }[] }
export const generateStickerOptions = (request: string, context: ChatContextLine[]) =>
  post<{ mode: "builder" | "demo"; options: BuilderOption[] }>("/stickers/generate", { request, context });
export async function listStickerPacks(): Promise<{ id: string; title: string; stickers: string[]; urls: string[] }[]> {
  try {
    const { packs } = await json<{ packs: { id: string; title: string; stickers: string[] }[] }>(await fetch(`${AGENTS}/stickers`));
    return packs.map((p) => ({ ...p, urls: p.stickers.map((f) => `${AGENTS}/stickers/file/${p.id}/${f}`) }));
  } catch {
    return (await bundledStickerPacks()).map((p) => ({ ...p, urls: p.stickers.map((f) => `/stickers/${p.id}/${f}`) }));
  }
}
export interface StickerPack { id: string; title: string; tags: string[]; stickers: string[]; urls: string[]; matched?: boolean }
/** Bundled demo packs (public/stickers) when the agents service is off. */
export async function bundledStickerPacks(): Promise<Omit<StickerPack, "urls">[]> {
  return (await json<{ packs: Omit<StickerPack, "urls">[] }>(await fetch("/stickers/index.json"))).packs;
}
export interface Gif { id: string; title: string; preview: string; url: string; width: number; height: number }
export async function searchGifs(q: string): Promise<{ mode: "giphy" | "off"; gifs: Gif[] }> {
  try { return await json(await fetch(`${AGENTS}/gifs?${new URLSearchParams({ q })}`)); } catch { return { mode: "off", gifs: [] }; }
}
