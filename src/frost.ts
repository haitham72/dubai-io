// Frosted-glass tuning (Settings → Appearance). Overrides --frost / --frost-blur
// on <html> so every frosted surface (nav, mobile headers) follows live. Persisted.
export interface Frost { opacity: number; blur: number }
const KEY = "mirsal.frost.v3";
export const DEFAULT_FROST: Frost = { opacity: 0.7, blur: 15 };

export function loadFrost(): Frost {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const v = JSON.parse(raw) as Partial<Frost>;
      if (typeof v.opacity === "number" && typeof v.blur === "number") {
        return {
          opacity: Math.min(1, Math.max(0.5, v.opacity)),
          blur: Math.min(60, Math.max(10, Math.round(v.blur))),
        };
      }
    }
  } catch { /* storage unavailable */ }
  return { ...DEFAULT_FROST };
}

export function applyFrost(f: Frost) {
  const root = document.documentElement.style;
  root.setProperty("--frost", `rgba(255, 255, 255, ${f.opacity})`);
  // Saturation scales with blur so 0px means a true no-op (a flat saturate(180%) reads as haze).
  const sat = Math.min(180, 100 + Math.round(f.blur) * 4);
  root.setProperty("--frost-blur", f.blur <= 0 ? "none" : `blur(${f.blur}px) saturate(${sat}%)`);
  try { localStorage.setItem(KEY, JSON.stringify(f)); } catch { /* storage unavailable */ }
}
