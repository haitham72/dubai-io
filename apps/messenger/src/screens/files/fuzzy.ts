// Instant, typo-tolerant photo filter (Apple TV / iOS search feel). Runs over the
// already-loaded photo list on every keystroke; the server hybrid search runs on Enter.
import type { PhotoHit } from "../../api";

/** Lowercase, strip Latin + Arabic diacritics, fold Arabic letter variants, split on punctuation. */
function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[ً-ٰٟـ]/g, "")
    .replace(/[أإآ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

/** Levenshtein distance, early-exits once it exceeds `max`. */
function distance(a: string, b: string, max: number): number {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    let rowMin = i;
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      rowMin = Math.min(rowMin, cur[j]);
    }
    if (rowMin > max) return max + 1;
    prev = cur;
  }
  return prev[b.length];
}

/** How well one query word matches one field's words (0 = no match). */
function wordScore(q: string, words: string[]): number {
  let best = 0;
  const typos = q.length >= 7 ? 2 : q.length >= 4 ? 1 : 0;
  for (const w of words) {
    if (w === q) return 1;
    if (w.startsWith(q)) best = Math.max(best, 0.85);
    else if (q.length >= 3 && w.includes(q)) best = Math.max(best, 0.6);
    else if (typos) {
      // Compare against the word and against its same-length prefix (typo while still typing).
      const d = Math.min(distance(q, w, typos), distance(q, w.slice(0, q.length), typos));
      if (d <= typos) best = Math.max(best, 0.5 - d * 0.1);
    }
  }
  return best;
}

interface Indexed { hit: PhotoHit; fields: { words: string[]; weight: number }[] }
const cache = new WeakMap<PhotoHit, Indexed>();

function index(hit: PhotoHit): Indexed {
  let entry = cache.get(hit);
  if (!entry) {
    const field = (text: string | undefined | null, weight: number) =>
      ({ words: normalize(text ?? "").split(" ").filter(Boolean), weight });
    entry = {
      hit,
      fields: [
        field(hit.meta.event, 1),
        field(hit.tags.join(" "), 0.9),
        field(`${hit.meta.account ?? ""} ${hit.meta.date ?? ""} ${hit.meta.year ?? ""}`, 0.8),
        field(`${hit.caption} ${hit.caption_ar ?? ""}`, 0.7),
        field(`${hit.file} ${hit.meta.extra ?? ""}`, 0.6),
      ],
    };
    cache.set(hit, entry);
  }
  return entry;
}

/** Photos matching every word of `query` (fuzzily), best first. Needs ≥2 characters. */
export function fuzzyPhotos(photos: PhotoHit[], query: string): PhotoHit[] {
  const words = normalize(query).split(" ").filter(Boolean);
  if (words.join("").length < 2) return [];
  const scored: { hit: PhotoHit; score: number }[] = [];
  for (const photo of photos) {
    const { fields } = index(photo);
    let total = 0;
    for (const q of words) {
      let best = 0;
      for (const f of fields) best = Math.max(best, wordScore(q, f.words) * f.weight);
      if (!best) { total = 0; break; }
      total += best;
    }
    if (total) scored.push({ hit: photo, score: total });
  }
  // Stable sort keeps the newest-first order for ties.
  return scored.sort((a, b) => b.score - a.score).map((s) => s.hit);
}
