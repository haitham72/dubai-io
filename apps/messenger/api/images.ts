// POST /api/images {prompt, image?} → {id, status:"running"}; GET /api/images/{id} (rewritten to ?id=) → {id, status, imageUrl?, error?}.
// Stateless: the job id carries what the poll needs (Higgs request id, CLI job id, or the fake job's start time).
//   - New images: fake (no credits) when MIRSAL_FAKE_IMAGES=1 or Higgs isn't configured.
//   - Edits ({image}: the original URL as reference — "Prompt your edits" in Mirsal Studio): always real when a Higgs
//     backend exists — the API (HF_CREDENTIALS + HIGGS_IMAGE_ENDPOINT) or, on the local dev server, the logged-in CLI.
import { body, env, fail, higgsAuth, higgsStatus, higgsSubmit, json, route } from "../lib/http.js";
import { cliAvailable, cliJob, cliStartEdit } from "../lib/higgsCli.js";

// Verified to load (curl → 200): stock beach photo for fake jobs.
const FAKE_IMAGE_URL = "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1600";
const FAKE_MS = 4000;
const apiReady = () => !!higgsAuth() && !!env("HIGGS_IMAGE_ENDPOINT");

export const POST = route(async (req) => {
  const { prompt, image } = await body<{ prompt?: string; image?: string }>(req);
  if (!prompt?.trim()) return fail(400, "prompt is required");

  if (image) {
    // Nano Banana 2 edit: keep the picture, apply the requested change
    const instruction = `Edit this image: ${prompt.trim()}. Keep everything else about the image the same.`;
    if (apiReady()) {
      const requestId = await higgsSubmit(env("HIGGS_IMAGE_ENDPOINT"), { prompt: instruction, image_references: [image], resolution: "1k" });
      return json({ id: `hf-${requestId}`, status: "running" });
    }
    if (cliAvailable()) return json({ id: `cli-${await cliStartEdit(image, instruction)}`, status: "running" });
    return json({ id: `fake-${Date.now()}`, status: "running", fake: true });
  }

  if (env("MIRSAL_FAKE_IMAGES") === "1" || !apiReady()) return json({ id: `fake-${Date.now()}`, status: "running" });
  // Nano Banana 2 (nano_banana_flash): square, 2k
  const requestId = await higgsSubmit(env("HIGGS_IMAGE_ENDPOINT"), { prompt: prompt.trim(), aspect_ratio: "1:1", resolution: "2k" });
  return json({ id: `hf-${requestId}`, status: "running" });
});

export const GET = route(async (req) => {
  const id = new URL(req.url).searchParams.get("id") ?? "";
  if (id.startsWith("fake-")) {
    const done = Date.now() - Number(id.slice(5)) > FAKE_MS;
    return json(done ? { id, status: "completed", imageUrl: FAKE_IMAGE_URL } : { id, status: "running" });
  }
  if (id.startsWith("cli-")) {
    const j = await cliJob(id.slice(4));
    return json(j.status === "completed" ? { id, status: "completed", imageUrl: j.url } : { id, status: j.status, error: j.error });
  }
  if (!id.startsWith("hf-")) return json({ id, status: "failed", error: "Unknown image job" }, 404);
  const s = await higgsStatus(id.slice(3));
  if (s.status === "completed" && s.images?.[0]?.url) return json({ id, status: "completed", imageUrl: s.images[0].url });
  if (s.status === "failed" || s.status === "nsfw") return json({ id, status: "failed", error: s.status === "nsfw" ? "Blocked by the safety filter" : "Image generation failed" });
  return json({ id, status: "running" });
});
