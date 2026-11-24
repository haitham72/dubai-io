import type { Group, Notification, Post, Profile } from "./types";
import { authHeaders, getSessionToken } from "./session";

export const API_BASE =
  process.env.NEXT_PUBLIC_CM_API ?? "http://localhost:8060";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      credentials: "include",
      headers: { "content-type": "application/json", ...authHeaders(typeof window === "undefined" ? null : getSessionToken()) },
      ...init,
    });
  } catch {
    throw new ApiError("Community service unavailable", 0);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch { /* keep default */ }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const getFeed = async (): Promise<Post[]> =>
  (await request<{ posts: Post[] }>("/api/community/feed")).posts ?? [];
export const getGroups = async (): Promise<Group[]> =>
  (await request<{ groups: Group[] }>("/api/community/groups")).groups ?? [];
export const getNotifications = async (): Promise<{ notifications: Notification[]; unread_count: number }> => {
  const r = await request<{ notifications: Notification[]; unread_count?: number; unread?: number }>("/api/community/inbox");
  return { notifications: r.notifications ?? [], unread_count: r.unread_count ?? r.unread ?? 0 };
};
/** The caller's profile, or null when they have none yet (the API answers 200 with `profile: null`). */
export const getMyProfile = async (): Promise<Profile | null> => {
  const r = await request<{ profile?: Profile | null }>("/api/community/profiles/me");
  return r.profile ?? null;
};
export const createPost = async (text: string): Promise<Post> =>
  (await request<{ post: Post }>("/api/community/posts", { method: "POST", body: JSON.stringify({ text }) })).post;
export const markNotificationRead = async (id: string): Promise<void> => {
  await request(`/api/community/notifications/${id}/read`, { method: "POST" });
};

export interface MemoryConsent {
  read_enabled: boolean;
  write_enabled: boolean;
  allow_interest_export: boolean;
  default_off: boolean;
  as_of?: string;
  provenance?: string;
}
export interface ForgetResult { records_forgotten: number; facts_erased: number; as_of?: string }
export const getMemoryConsent = (): Promise<MemoryConsent> => request<MemoryConsent>("/api/community/memory/consent");
export const setMemoryConsent = (c: Pick<MemoryConsent, "read_enabled" | "write_enabled" | "allow_interest_export">): Promise<MemoryConsent> =>
  request<MemoryConsent>("/api/community/memory/consent", { method: "POST", body: JSON.stringify(c) });
export const forgetMemory = (): Promise<ForgetResult> =>
  request<ForgetResult>("/api/community/memory/forget", { method: "POST" });
