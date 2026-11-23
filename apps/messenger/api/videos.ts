// POST /api/videos {prompt} → {id, status:"running"} | {mode:"mock"} (client then plays a bundled clip);
// GET /api/videos/{id} (rewritten to ?id=) → {id, status, videoUrl?, error?}.
// Kling v3.0 via Higgs: 5 seconds, 16:9, 1080p. Mock when MIRSAL_FAKE_VIDEOS=1 or Higgs isn't configured.
import { body, env, fail, higgsAuth, higgsStatus, higgsSubmit, json, route } from "../lib/http.js";

export const POST = route(async (req) => {
  const { prompt } = await body<{ prompt?: string }>(req);
  if (!prompt?.trim()) return fail(400, "prompt is required");
  if (env("MIRSAL_FAKE_VIDEOS", "1") === "1" || !higgsAuth()) return json({ mode: "mock" });
  const requestId = await higgsSubmit(env("HIGGS_VIDEO_ENDPOINT", "kling-video/v3.0/std/text-to-video"), {
    prompt: prompt.trim(), duration: 5, aspect_ratio: "16:9", resolution: "1080p",
  });
  return json({ id: `hf-${requestId}`, status: "running" });
});

export const GET = route(async (req) => {
  const id = new URL(req.url).searchParams.get("id") ?? "";
  if (!id.startsWith("hf-")) return json({ id, status: "failed", error: "Unknown video job" }, 404);
  const s = await higgsStatus(id.slice(3));
  if (s.status === "completed" && s.video?.url) return json({ id, status: "completed", videoUrl: s.video.url });
  if (s.status === "failed" || s.status === "nsfw") return json({ id, status: "failed", error: s.status === "nsfw" ? "Blocked by the safety filter" : "Video generation failed" });
  return json({ id, status: "running" });
});
