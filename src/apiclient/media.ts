// Image + video generation (Nano Banana 2 / Kling 3.0 via Higgs on the server;
// fake jobs when not configured).
import { json } from "./http";

/* ---------- image generation ---------- */
export interface ImageJob { id: string; status: "running" | "completed" | "failed"; imageUrl?: string; error?: string }

/** `image` = an existing image URL to edit (Nano Banana 2 image-to-image); omit for a new image. */
export async function startImage(prompt: string, image?: string): Promise<ImageJob & { fake?: boolean }> {
  return json<ImageJob & { fake?: boolean }>(await fetch("/api/images", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt, ...(image ? { image } : {}) }),
  }));
}

export async function getImageJob(id: string): Promise<ImageJob> {
  return json<ImageJob>(await fetch(`/api/images/${id}`));
}

/* ---------- video generation ({mode:"mock"} = play a bundled clip) ---------- */
export type VideoStart = { mode: "mock" } | { id: string; status: "running" };
export interface VideoJob { id: string; status: "running" | "completed" | "failed"; videoUrl?: string; error?: string }

export async function startVideo(prompt: string): Promise<VideoStart> {
  return json<VideoStart>(await fetch("/api/videos", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt }),
  }));
}

export async function getVideoJob(id: string): Promise<VideoJob> {
  return json<VideoJob>(await fetch(`/api/videos/${encodeURIComponent(id)}`));
}
