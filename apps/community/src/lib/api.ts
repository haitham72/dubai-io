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
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* keep default */ }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

// ---------------------------------------------------------------- types
export interface Comment {
  id: string; post_id: string; owner: string; parent_id: string | null;
  text: string; author: { owner?: string; handle: string; display_name?: string };
  provenance?: string; created_at?: string; mine?: boolean;
}
export interface DiscoveryItem {
  kind: "post" | "group" | string; id: string; post_id?: string; group_id?: string | null;
  name?: string; handle?: string; description?: string; text?: string;
  score?: number; features_used?: string[]; why_this?: string; why_chip?: string;
  provenance?: string; as_of?: string; members?: number; origin?: string; demo_data?: boolean;
}
export interface DiscoveryResult {
  items: DiscoveryItem[]; candidates?: DiscoveryItem[]; reason?: string | null;
  empty?: boolean; source?: string; why_chip?: string;
}
export interface SearchResults { groups: Group[]; profiles: Profile[]; posts: Post[]; q: string }
export interface FollowEntry { owner: string; handle: string | null }
export interface ReactionResult { post_id: string; kind: string; reacted: boolean; active: boolean; count: number; reactions: number }
export interface ProfileIn {
  handle: string; display_name?: string; bio?: string; area?: string;
  interests?: string[]; age_band: string; privacy?: "public" | "private" | "followers";
}
export interface GroupIn { name: string; handle?: string; description?: string; visibility?: "public" | "private" }

const j = (body: unknown) => JSON.stringify(body);

// ---------------------------------------------------------------- feed / posts
export const getFeed = async (limit = 50): Promise<Post[]> =>
  (await request<{ posts: Post[] }>(`/api/community/feed?limit=${limit}`)).posts ?? [];
export const getPost = async (id: string): Promise<Post> =>
  (await request<{ post: Post }>(`/api/community/posts/${encodeURIComponent(id)}`)).post;
export const createPost = async (text: string, groupId?: string | null): Promise<Post> =>
  (await request<{ post: Post }>("/api/community/posts", {
    method: "POST", body: j({ text, ...(groupId ? { group_id: groupId } : {}) }),
  })).post;
export const updatePost = async (id: string, text: string): Promise<Post> =>
  (await request<{ post: Post }>(`/api/community/posts/${encodeURIComponent(id)}`, {
    method: "PUT", body: j({ text }),
  })).post;
export const deletePost = async (id: string): Promise<void> => {
  await request(`/api/community/posts/${encodeURIComponent(id)}`, { method: "DELETE" });
};

// ---------------------------------------------------------------- comments
export const getComments = async (postId: string): Promise<Comment[]> =>
  (await request<{ comments: Comment[] }>(`/api/community/posts/${encodeURIComponent(postId)}/comments`)).comments ?? [];
export const addComment = async (postId: string, text: string, parentId?: string | null): Promise<Comment> =>
  (await request<{ comment: Comment }>(`/api/community/posts/${encodeURIComponent(postId)}/comments`, {
    method: "POST", body: j({ text, ...(parentId ? { parent_id: parentId } : {}) }),
  })).comment;

// ---------------------------------------------------------------- reactions / bookmarks
export const toggleReaction = async (postId: string, kind = "like"): Promise<ReactionResult> =>
  request<ReactionResult>(`/api/community/posts/${encodeURIComponent(postId)}/reactions`, {
    method: "POST", body: j({ kind }),
  });
export const addBookmark = async (postId: string): Promise<void> => {
  await request(`/api/community/posts/${encodeURIComponent(postId)}/bookmarks`, { method: "POST" });
};
export const removeBookmark = async (postId: string): Promise<void> => {
  await request(`/api/community/posts/${encodeURIComponent(postId)}/bookmarks`, { method: "DELETE" });
};

// ---------------------------------------------------------------- follows / profiles
export const getFollows = async (): Promise<FollowEntry[]> => {
  const r = await request<{ follows?: FollowEntry[]; following?: FollowEntry[] }>("/api/community/follows");
  return r.follows ?? r.following ?? [];
};
export const follow = async (handle: string): Promise<void> => {
  await request(`/api/community/follows/${encodeURIComponent(handle)}`, { method: "POST" });
};
export const unfollow = async (handle: string): Promise<void> => {
  await request(`/api/community/follows/${encodeURIComponent(handle)}`, { method: "DELETE" });
};
export const getMyProfile = async (): Promise<Profile | null> => {
  const r = await request<{ profile?: Profile | null }>("/api/community/profiles/me");
  return r.profile ?? null;
};
export const getProfile = async (handle: string): Promise<Profile> =>
  (await request<{ profile: Profile }>(`/api/community/profiles/${encodeURIComponent(handle)}`)).profile;
export const upsertProfile = async (p: ProfileIn): Promise<Profile> =>
  (await request<{ profile: Profile }>("/api/community/profiles/me", { method: "PUT", body: j(p) })).profile;

// ---------------------------------------------------------------- groups
export const getGroups = async (): Promise<Group[]> =>
  (await request<{ groups: Group[] }>("/api/community/groups")).groups ?? [];
export const getGroup = async (id: string): Promise<Group> =>
  (await request<{ group: Group }>(`/api/community/groups/${encodeURIComponent(id)}`)).group;
export const createGroup = async (g: GroupIn): Promise<Group> =>
  (await request<{ group: Group }>("/api/community/groups", { method: "POST", body: j(g) })).group;
export const joinGroup = async (id: string): Promise<Group> =>
  (await request<{ group: Group }>(`/api/community/groups/${encodeURIComponent(id)}/join`, { method: "POST" })).group;
export const leaveGroup = async (id: string): Promise<void> => {
  await request(`/api/community/groups/${encodeURIComponent(id)}/leave`, { method: "POST" });
};
export const getGroupPosts = async (id: string, limit = 50): Promise<Post[]> =>
  (await request<{ posts: Post[] }>(`/api/community/groups/${encodeURIComponent(id)}/posts?limit=${limit}`)).posts ?? [];
export const createGroupPost = async (id: string, text: string): Promise<Post> =>
  (await request<{ post: Post }>(`/api/community/groups/${encodeURIComponent(id)}/posts`, {
    method: "POST", body: j({ text }),
  })).post;

// ---------------------------------------------------------------- discovery / search / inbox
export const getDiscovery = async (limit = 20): Promise<DiscoveryResult> =>
  request<DiscoveryResult>(`/api/community/discovery?limit=${limit}`);
export const searchCommunity = async (q: string): Promise<SearchResults> =>
  request<SearchResults>(`/api/community/search?q=${encodeURIComponent(q)}`);
export const getNotifications = async (): Promise<{ notifications: Notification[]; unread_count: number }> => {
  const r = await request<{ notifications: Notification[]; unread_count?: number; unread?: number }>("/api/community/inbox");
  return { notifications: r.notifications ?? [], unread_count: r.unread_count ?? r.unread ?? 0 };
};
export const markNotificationRead = async (id: string): Promise<void> => {
  await request(`/api/community/notifications/${id}/read`, { method: "POST" });
};
export const markAllNotificationsRead = async (): Promise<void> => {
  await request("/api/community/notifications/read-all", { method: "POST" });
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
