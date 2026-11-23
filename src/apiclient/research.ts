// Research: deep research on the agents service when it runs, else Tavily → OpenAI brief on the server.
import type { ResearchItem } from "../types";
import { json } from "./http";
import { agentsHealth, briefToItem, deepResearch } from "./agents";

export type ResearchResult = ResearchItem & { status?: string; mode: "live" | "demo" };
export async function runResearch(topic: string): Promise<ResearchResult> {
  if ((await agentsHealth())?.ok) {
    try { return briefToItem(await deepResearch(topic)); } catch { /* fall through to the server route */ }
  }
  const brief = await json<ResearchItem & { status?: string }>(await fetch("/api/research", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ topic }),
  }));
  return { ...brief, mode: "live" }; // the server route only answers with live search + model
}
