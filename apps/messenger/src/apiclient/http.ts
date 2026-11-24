// Shared plumbing for the api-client domain modules. `json` is intentionally NOT
// re-exported by the src/api.ts barrel: it is an internal helper.
export async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  return res.json() as Promise<T>;
}
