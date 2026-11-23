// Photo search (annotated collection: CDN images + Postgres metadata).
import { json } from "./http";

export interface PhotoHit {
  file: string;
  meta: { account?: string; year?: number | null; event?: string; date?: string | null; extra?: string };
  caption: string; caption_ar?: string; tags: string[];
  score?: number; why?: string[]; url: string;
}
export interface PhotoSearch { mode: string; count: number; results: PhotoHit[] }

export async function searchPhotos(q: string, k = 12): Promise<PhotoSearch> {
  const params = new URLSearchParams({ q, k: String(k) });
  return json<PhotoSearch>(await fetch(`/api/photos?action=search&${params}`));
}

export interface PhotoList { mode: string; count: number; total: number; offset: number; results: PhotoHit[] }

/** One page of annotated photos, newest first. `total` counts the whole collection. */
export async function listPhotos(limit = 24, offset = 0): Promise<PhotoList> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return json<PhotoList>(await fetch(`/api/photos?action=list&${params}`));
}
