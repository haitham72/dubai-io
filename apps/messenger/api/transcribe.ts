// POST /api/transcribe (raw audio body, Content-Type = recorder mime) → {text}. Voice mode speech-to-text.
// Messenger speaks English and Arabic only. The model auto-detects (and sometimes picks Urdu or Japanese), so the
// first pass is steered with a prompt; if the text still comes back in another script, the same audio is
// transcribed again with the language forced (Arabic-script → "ar", anything else → "en").
import { env, fail, json, openaiKey, route } from "../lib/http.js";

const EXT: Record<string, string> = { "audio/webm": "webm", "audio/mp4": "mp4", "audio/m4a": "m4a", "audio/x-m4a": "m4a", "audio/mpeg": "mp3", "audio/ogg": "ogg", "audio/wav": "wav" };
const MAX_BYTES = 8 * 1024 * 1024;
const PROMPT = "The speaker talks in English or Arabic (often Gulf Arabic), sometimes mixing both. Transcribe in English or Arabic only.";

// Letters used by Urdu/Persian but not Arabic (ٹ ڈ ڑ ں ے ۓ ہ ۂ ۃ etc.), and any script that isn't Latin or Arabic.
const URDU_ONLY = /[ٹڈڑںڻھہ-ۃےۓ]/;
const ARABIC = /[؀-ۿ]/;
const OTHER_SCRIPT = /[^\p{Script=Latin}\p{Script=Arabic}\p{Script=Common}\p{Script=Inherited}]/u;

async function transcribeOnce(audio: ArrayBuffer, type: string, language?: string): Promise<string> {
  const form = new FormData();
  form.append("file", new Blob([audio], { type }), `voice.${EXT[type] ?? "webm"}`);
  form.append("model", env("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"));
  form.append("prompt", PROMPT);
  if (language) form.append("language", language);
  const res = await fetch("https://api.openai.com/v1/audio/transcriptions", { method: "POST", headers: { Authorization: `Bearer ${openaiKey()}` }, body: form });
  if (!res.ok) { console.error("[transcribe api.openai.com]", res.status, (await res.text()).slice(0, 300)); throw fail(502, "Transcription failed"); }
  const { text } = (await res.json()) as { text?: string };
  return (text ?? "").trim();
}

export const POST = route(async (req) => {
  const type = (req.headers.get("content-type") ?? "audio/webm").split(";")[0].trim();
  const audio = await req.arrayBuffer();
  if (!audio.byteLength) return fail(400, "Empty audio");
  if (audio.byteLength > MAX_BYTES) return fail(413, "Audio too long");

  const text = await transcribeOnce(audio, type);
  if (!URDU_ONLY.test(text) && !OTHER_SCRIPT.test(text)) return json({ text });
  // Wrong language: Arabic-script (Urdu/Persian) → Arabic; anything else (Japanese, etc.) → English.
  const forced = URDU_ONLY.test(text) || (ARABIC.test(text) && !OTHER_SCRIPT.test(text)) ? "ar" : "en";
  return json({ text: await transcribeOnce(audio, type, forced) });
});
