/** Base URL of the Dubai-io API. Local default; no secrets here. */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/** Join a path onto the API base (path must start with "/"). */
export function apiUrl(path: string): string {
  return `${API_BASE.replace(/\/$/, "")}${path}`;
}
