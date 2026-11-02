/** Open a merchant/school site when Dubai-io has no adapter. Never invent success. */

const SAFE = /^https:\/\//i;
const HTTP_OK = /^https?:\/\//i;

/** Prefer https; upgrade bare http school sites from Places. */
export function businessHref(url: string | null | undefined): string | null {
  if (!url || typeof url !== "string") return null;
  const u = url.trim();
  if (SAFE.test(u)) return u;
  if (HTTP_OK.test(u)) return u.replace(/^http:\/\//i, "https://");
  return null;
}

export function openBusinessSite(url: string | null | undefined): boolean {
  const href = businessHref(url);
  if (!href || typeof window === "undefined") return false;
  window.open(href, "_blank", "noopener,noreferrer");
  return true;
}

/** Official directories when we have no per-school KHDA deep link. */
export const KHDA_DIRECTORY = "https://www.khda.gov.ae/en/directory";
export const FITNESS_FIRST_MEMBERSHIP =
  "https://uae.fitnessfirstme.com/memberships";
