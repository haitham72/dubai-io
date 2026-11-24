// POST /api/research {topic} → ResearchItem. Tavily web search → OpenAI writes a short brief with 5 findings.
import { body, env, fail, isLuna, json, openai, parseModelJson, route, type ChatCompletion } from "../lib/http.js";

interface TavilyResult { title: string; url: string; content: string }

export const POST = route(async (req) => {
  const { topic } = await body<{ topic?: string }>(req);
  if (!topic?.trim()) return fail(400, "topic is required");
  const key = env("TVLY_API_KEY") || env("TAVILY_API_KEY");
  if (!key) return fail(503, "Research key missing");

  const started = Date.now();
  const search = await fetch("https://api.tavily.com/search", {
    method: "POST", headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ query: topic.trim(), max_results: 8, search_depth: "basic" }),
  });
  if (!search.ok) { console.error("[tavily]", search.status); return fail(502, "Search failed"); }
  const results = ((await search.json()) as { results?: TavilyResult[] }).results ?? [];

  const sources = results.map((r, i) => `[${i + 1}] ${r.title} (${r.url})\n${r.content.slice(0, 700)}`).join("\n\n");
  const schema = {
    type: "object", additionalProperties: false, required: ["title", "summary", "findings"],
    properties: {
      title: { type: "string", description: "Short report title" },
      summary: { type: "string", description: "Two-sentence executive summary" },
      findings: { type: "array", items: { type: "string" }, description: "Exactly 5 key findings, one sentence each" },
    },
  };
  const model = env("OPENAI_MODEL", "gpt-4o-mini");
  const resp = await openai<ChatCompletion>("chat/completions", {
    model,
    messages: [
      { role: "system", content: "You write crisp research briefs for a busy executive in the UAE. Use only the sources given. Reply in the topic's language. Your entire response must be exactly one JSON object and nothing else: {\"title\": \"<short report title>\", \"summary\": \"<two-sentence executive summary>\", \"findings\": [\"<finding one>\", \"<finding two>\", \"<finding three>\", \"<finding four>\", \"<finding five>\"]}. No prose, no markdown fences." },
      { role: "user", content: `Topic: ${topic}\n\nSources:\n${sources}` },
    ],
    response_format: { type: "json_schema", json_schema: { name: "brief", strict: true, schema } },
    ...(isLuna(model) ? { reasoning_effort: "none" } : {}),
  });
  let brief: { title: string; summary: string; findings: string[] };
  try {
    brief = parseModelJson(resp.choices[0]?.message.content);
    if (!brief.title || !brief.summary || !Array.isArray(brief.findings)) throw new Error("bad brief");
  } catch { return fail(502, "Brief failed"); }
  const domain = (u: string) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return u; } };
  return json({
    id: `r-${Date.now()}`, title: brief.title, summary: brief.summary, findings: brief.findings.slice(0, 5),
    time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
    sources: results.slice(0, 6).map((r) => ({ title: r.title, domain: domain(r.url) })),
    status: `Searched ${results.length} sources · ${Math.max(1, Math.round((Date.now() - started) / 1000))}s`,
  });
});
