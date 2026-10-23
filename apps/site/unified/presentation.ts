export type Presentation = "website" | "desktop" | "device";

/** Plain URL = website; `?desktop` = Mac window; `?device` = iPhone frame. `device` wins if both are given. */
export function presentation(search: string): Presentation {
  const q = new URLSearchParams(search);
  if (q.has("device")) return "device";
  if (q.has("desktop")) return "desktop";
  return "website";
}
