// Image and video generation are not part of this app.
export interface ImageJob { id: string; status: "running" | "completed" | "failed"; imageUrl?: string; error?: string }
export type VideoStart = { mode: "mock" } | { id: string; status: "running" };
export interface VideoJob { id: string; status: "running" | "completed" | "failed"; videoUrl?: string; error?: string }

/** Image and video generation are not part of this app. */
export async function startImage(_prompt: string, _image?: string): Promise<ImageJob & { fake?: boolean }> {
  return { id: "unavailable", status: "failed", error: "Image generation is not part of this app" };
}

export async function getImageJob(_id: string): Promise<ImageJob> {
  return { id: "unavailable", status: "failed", error: "Image generation is not part of this app" };
}

export async function startVideo(_prompt: string): Promise<VideoStart> {
  return { mode: "mock" };
}

export async function getVideoJob(id: string): Promise<VideoJob> {
  return { id, status: "failed", error: "Video generation is not part of this app" };
}
