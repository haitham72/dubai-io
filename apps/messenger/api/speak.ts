// POST /api/speak {text} → audio/mpeg. Messenger's spoken voice (OpenAI TTS).
import { body, env, fail, openaiKey, route } from "../lib/http.js";

export const POST = route(async (req) => {
  const { text } = await body<{ text?: string }>(req);
  const input = text?.trim().slice(0, 600);
  if (!input) return fail(400, "text is required");
  const res = await fetch("https://api.openai.com/v1/audio/speech", {
    method: "POST",
    headers: { Authorization: `Bearer ${openaiKey()}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: env("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"), voice: env("OPENAI_TTS_VOICE", "nova"), input, response_format: "mp3",
      instructions: "You are Messenger, a warm, calm and concise personal assistant. Speak naturally; in Arabic use a clear Gulf-friendly tone.",
    }),
  });
  if (!res.ok || !res.body) { console.error("[speak api.openai.com]", res.status, (await res.text()).slice(0, 300)); return fail(502, "Speech failed"); }
  return new Response(res.body, { headers: { "Content-Type": "audio/mpeg", "Cache-Control": "no-store" } });
});
