// Voice (OpenAI speech-to-text / text-to-speech on the server).
import { json } from "./http";

export async function transcribe(audio: Blob): Promise<string> {
  const res = await fetch("/api/transcribe", { method: "POST", headers: { "Content-Type": audio.type || "audio/webm" }, body: audio });
  return (await json<{ text: string }>(res)).text;
}

export async function speak(text: string): Promise<Blob> {
  const res = await fetch("/api/speak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  return res.blob();
}
