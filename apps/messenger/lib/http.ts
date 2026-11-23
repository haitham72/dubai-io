// Shared helpers for the API routes (Web-standard Request → Response; runs on Vercel and in the Vite dev server).
// Lives outside api/ so it is bundled into the routes, not deployed as a function of its own.
declare const process: { env: Record<string, string | undefined> };

export const env = (key: string, fallback = "") => process.env[key] || fallback;

export const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });

export const fail = (status: number, message: string) =>
  new Response(message, { status, headers: { "Content-Type": "text/plain" } });

/** Read a JSON body or fail with 400. */
export async function body<T>(req: Request): Promise<T> {
  try { return (await req.json()) as T; } catch { throw fail(400, "Invalid JSON body"); }
}

/** Last path segment of the URL. */
export const lastSegment = (req: Request) => decodeURIComponent(new URL(req.url).pathname.split("/").filter(Boolean).pop() ?? "");

/** Run a handler; a thrown Response is returned as-is, anything else becomes a 500 (no secrets leaked). */
export function route(fn: (req: Request) => Promise<Response>) {
  return async (req: Request) => {
    try { return await fn(req); } catch (err) {
      if (err instanceof Response) return err;
      console.error("[api]", err instanceof Error ? err.message : err);
      return fail(500, "Server error");
    }
  };
}

/* ---------- providers: Nara (text) + OpenAI (audio, streaming, Decisions) ---------- */
export function openaiKey() {
  const key = env("OPENAI_API_KEY");
  if (!key) throw fail(503, "OpenAI key missing");
  return key;
}

export function naraKey() {
  const key = env("NARA_API_KEY");
  if (!key) throw fail(503, "Nara key missing");
  return key;
}

/** Text-model endpoint root (the router). */
export const naraBase = () =>
  (env("NARA_BASE_URL", env("OPENAI_BASE_URL", "https://router.bynara.id/v1")) || "https://router.bynara.id/v1").replace(/\/$/, "");

/** Host of a URL, for log lines (never the key). */
const hostOf = (url: string) => { try { return new URL(url).host; } catch { return "llm"; } };

const OPENAI_BASE = "https://api.openai.com/v1";

/** Chat/completions-style call against OpenAI (audio, and anything OpenAI-only). */
export async function openai<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${OPENAI_BASE}/${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${openaiKey()}`, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) { console.error(`[llm ${hostOf(OPENAI_BASE)}]`, res.status, (await res.text()).slice(0, 300)); throw fail(502, "AI request failed (api.openai.com)"); }
  return res.json() as Promise<T>;
}

/** Chat call against the Nara router (text only; it serves no strict json_schema or /audio/*). */
export async function nara<T>(path: string, payload: unknown): Promise<T> {
  const base = naraBase();
  const res = await fetch(`${base}/${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${naraKey()}`, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) { console.error(`[llm ${hostOf(base)}]`, res.status, (await res.text()).slice(0, 300)); throw fail(502, `AI request failed (${hostOf(base)})`); }
  return res.json() as Promise<T>;
}

/** gpt-6-luna is a reasoning model with its own quirks: fixed temperature 1, max_completion_tokens, effort "none" for tools. */
export const isLuna = (model: string) => model.toLowerCase().includes("luna");

/** Parse model JSON tolerantly: routers may wrap it in fences, reasoning or prose. Throws when no object is found. */
export function parseModelJson<T>(raw: string | null | undefined): T {
  const s = (raw ?? "").trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  try { return JSON.parse(s) as T; } catch { /* fall through to the substring scan */ }
  const start = s.indexOf("{"), end = s.lastIndexOf("}");
  if (start >= 0 && end > start) return JSON.parse(s.slice(start, end + 1)) as T;
  throw new Error("no JSON object");
}

/** Visible text when the model answered in prose: fence markers out, trimmed. */
export const stripFences = (raw: string | null | undefined) =>
  (raw ?? "").replace(/```(?:json)?/gi, "```").replace(/```/g, "").trim();

export interface ChatCompletion {
  choices: { message: { content: string | null; tool_calls?: { function: { name: string; arguments: string } }[] } }[];
}
