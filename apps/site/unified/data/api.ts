// Same-origin API client (the /api rewrite keeps the anonymous session cookie on the site's origin).
// Wrap-friendly: base comes from NEXT_PUBLIC_API_BASE ?? "" so Capacitor/Tauri builds can point elsewhere.
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let session: Promise<void> | null = null;

/** Test hook: forget that the session call happened. */
export function resetSession() {
  session = null;
}

async function send(method: string, path: string, body?: unknown): Promise<Response> {
  try {
    return await fetch(`${BASE}${path}`, {
      method,
      credentials: "include",
      headers: body === undefined ? undefined : { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Could not reach Dubai-io");
  }
}

async function ensureSession() {
  if (!session) {
    session = (async () => {
      const res = await send("GET", "/api/session");
      if (!res.ok) throw new ApiError(res.status, "Session unavailable");
    })().catch((e) => { session = null; throw e; });
  }
  return session;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  await ensureSession();
  const res = await send(method, path, body);
  const text = await res.text();
  let data: unknown = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* non-JSON body */ }
  if (!res.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail;
    throw new ApiError(res.status, typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  return data as T;
}

export const apiGet = <T>(path: string) => request<T>("GET", path);
export const apiPost = <T>(path: string, body: unknown) => request<T>("POST", path, body);
export const apiPut = <T>(path: string, body: unknown) => request<T>("PUT", path, body);
