// Mock video generation — owned by the lead session.
// The pool is media/videos/ (committed Kling demo clips) plus Slides/vids/ (git-ignored, local). Drop an .mp4 there and Vite picks it up
// (the page reloads); a video is "new" until it has been opened once in AI Chat (remembered per browser).
import type { MirsalTask } from "./types";

export interface MockVideo { url: string; title: string }

const files = import.meta.glob(["/Slides/vids/*.{mp4,MP4,mov,MOV,webm}", "/media/videos/*.{mp4,MP4,mov,MOV,webm}"], { query: "?url", import: "default", eager: true }) as Record<string, string>;

/** "mirsal-reel-30s_sound.mp4" → "Mirsal reel 30s". */
function titleOf(path: string) {
  const words = (path.split("/").pop() ?? path).replace(/\.[^.]+$/, "")
    .replace(/[-_]+/g, " ").replace(/\b(sound|final|v\d+)\b/gi, "").replace(/\s+/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Video";
}

export const mockVideos: MockVideo[] = Object.entries(files)
  .map(([path, url]) => ({ url, title: titleOf(path) }))
  .sort((a, b) => a.title.localeCompare(b.title));

const OPENED_KEY = "mirsal.videos.opened";
function loadOpened(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(OPENED_KEY) ?? "[]") as string[]); } catch { return new Set(); }
}
const opened = loadOpened();
export const isVideoOpened = (url: string) => opened.has(url);
export function markVideoOpened(url: string) {
  opened.add(url);
  try { localStorage.setItem(OPENED_KEY, JSON.stringify([...opened])); } catch { /* storage unavailable */ }
}

const shuffle = <T,>(list: T[]) => list.map(v => [Math.random(), v] as const).sort((a, b) => a[0] - b[0]).map(([, v]) => v);

let last: string | undefined;
/** A random clip from the folder (the prompt is ignored on purpose), avoiding an immediate repeat. */
export function pickMockVideo(): MockVideo {
  if (!mockVideos.length) throw new Error("No videos in Slides/vids");
  const pool = mockVideos.length > 1 ? mockVideos.filter(v => v.url !== last) : mockVideos;
  const v = pool[Math.floor(Math.random() * pool.length)];
  last = v.url;
  return v;
}

/** Mirsal Updates on load: every never-opened video (up to 3), topped up with random opened ones to at least 2. */
export function videoSeedTasks(): MirsalTask[] {
  const fresh = shuffle(mockVideos.filter(v => !isVideoOpened(v.url))).slice(0, 3);
  const old = shuffle(mockVideos.filter(v => isVideoOpened(v.url)));
  return [...fresh, ...old].slice(0, Math.max(2, fresh.length)).map((v, i) => {
    const isNew = !isVideoOpened(v.url);
    const at = Date.now() - (2 + i * 9) * 60_000;
    return {
      id: `video-${v.url.split("/").pop()}`, type: "video", title: isNew ? "New video" : "Your video", subtitle: v.title,
      status: "completed", startedAt: at, completedAt: at, unread: isNew,
      result: { type: "video", videoUrl: v.url, prompt: v.title, title: v.title },
    };
  });
}

/** How long the fake "creating" phase lasts, and how often progress ticks. */
export const MOCK_VIDEO_MS = 12_000;
export const MOCK_VIDEO_TICK_MS = 600;
