import type { ContextEnvelope, Group, Notification, Post, Profile } from "./types";
import type { FeedSort } from "./feed";
import { authHeaders, getSessionToken, rewriteLoopbackForLanHost } from "./session";

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

/** Testable LAN rewrite; production `getApiBase` uses shared `rewriteLoopbackForLanHost`. */
export function resolveApiBase(
  configured: string | undefined = process.env.NEXT_PUBLIC_CM_API,
  browserHostname?: string,
  browserProtocol?: string,
): string {
  const trimmed = configured?.trim();
  const base = (trimmed || "http://localhost:8060").replace(/\/+$/, "");
  if (browserHostname === undefined && browserProtocol === undefined) {
    return rewriteLoopbackForLanHost(base);
  }
  const host = browserHostname;
  if (!host || LOCAL_HOSTS.has(host.toLowerCase())) {
    return base;
  }
  const proto = browserProtocol;
  try {
    const parsed = new URL(base);
    if (LOCAL_HOSTS.has(parsed.hostname.toLowerCase())) {
      const port = parsed.port || "8060";
      const useProto = proto === "https:" ? "https:" : parsed.protocol || "http:";
      return `${useProto}//${host}:${port}`;
    }
  } catch {
    const useProto = proto === "https:" ? "https:" : "http:";
    return `${useProto}//${host}:8060`;
  }
  return base;
}

export function getApiBase(): string {
  const envBase = process.env.NEXT_PUBLIC_CM_API?.trim();
  return rewriteLoopbackForLanHost(envBase || "http://localhost:8060");
}

export const API_BASE = getApiBase();

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  const base = getApiBase();
  try {
    res = await fetch(`${base}${path}`, {
      credentials: "include",
      headers: {
        "content-type": "application/json",
        ...authHeaders(typeof window === "undefined" ? null : getSessionToken()),
      },
      ...init,
    });
  } catch {
    throw new ApiError("Community service unavailable", 0);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* keep default */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

// ---------------------------------------------------------------- types
export interface Comment {
  id: string;
  post_id: string;
  owner: string;
  parent_id: string | null;
  text: string;
  author: { owner?: string; handle: string; display_name?: string };
  provenance?: string;
  created_at?: string;
  mine?: boolean;
  score?: number;
  upvotes?: number;
  downvotes?: number;
  my_vote?: number;
}

export interface VoteResult {
  target_type?: string;
  target_id?: string;
  score: number;
  upvotes?: number;
  downvotes?: number;
  my_vote: number;
  value?: number;
}

export interface TrendingTag {
  tag: string;
  count: number;
  score?: number;
}

export interface DiscoveryItem {
  kind: "post" | "group" | string;
  id: string;
  post_id?: string;
  group_id?: string | null;
  name?: string;
  handle?: string;
  description?: string;
  text?: string;
  score?: number;
  features_used?: string[];
  why_this?: string;
  why_chip?: string;
  provenance?: string;
  as_of?: string;
  members?: number;
  origin?: string;
  demo_data?: boolean;
}

export interface DiscoveryResult {
  items: DiscoveryItem[];
  candidates?: DiscoveryItem[];
  reason?: string | null;
  empty?: boolean;
  source?: string;
  why_chip?: string;
  context_applied?: boolean;
  driving_mode?: boolean;
  context?: ContextEnvelope;
}

export interface SearchResults {
  groups: Group[];
  profiles: Profile[];
  posts: Post[];
  q: string;
}

export interface FollowEntry {
  owner: string;
  handle: string | null;
}

export interface ReactionResult {
  post_id: string;
  kind: string;
  reacted: boolean;
  active: boolean;
  count: number;
  reactions: number;
}

export interface ProfileIn {
  handle: string;
  display_name?: string;
  bio?: string;
  area?: string;
  interests?: string[];
  age_band: string;
  privacy?: "public" | "private" | "followers";
}

export interface GroupIn {
  name: string;
  handle?: string;
  description?: string;
  visibility?: "public" | "private";
}

export type MuteKind = "owner" | "group" | "tag";

export interface SafetyBlockEntry {
  owner?: string;
  handle: string;
  display_name?: string;
  created_at?: string;
}

export interface SafetyMuteEntry {
  kind: MuteKind | string;
  target: string;
  created_at?: string;
}

export interface SafetyState {
  blocked: SafetyBlockEntry[];
  mutes: SafetyMuteEntry[];
}

export interface ModerationEvent {
  id: string;
  event_id?: string;
  report_id?: string | null;
  source?: string;
  label?: string;
  evidence?: string;
  categories?: string[];
  target_type: string;
  target_id: string;
  target_owner?: string | null;
  group_id?: string | null;
  status: string;
  target_state?: string;
  resolved_by?: string | null;
  resolution?: string | null;
  is_minor?: boolean;
  priority?: number;
  created_at?: string;
  resolved_at?: string | null;
}

export interface InteractionEventIn {
  event_type: string;
  post_id?: string;
  group_id?: string;
  topic_slug?: string;
  tags?: string[];
  dwell_ms?: number;
  context?: ContextEnvelope;
}

export interface UsageBucket {
  topic_key: string;
  topic_label?: string;
  time_bucket?: string;
  area_coarse?: string;
  device_class?: string;
  user_state?: string;
  format?: string;
  weight: number;
  effective_weight?: number;
  raw_count?: number;
  session_count?: number;
  status?: string;
  lowered_at?: string | null;
  last_seen_at?: string | null;
}

export interface UsageProfileResult {
  context_aware_enabled: boolean;
  buckets: UsageBucket[];
  as_of?: string;
}

const j = (body: unknown) => JSON.stringify(body);

// ---------------------------------------------------------------- feed / posts / voting / tags / repost
export const getFeed = async (
  limit = 50,
  sort?: FeedSort,
  tag?: string | null,
): Promise<Post[]> => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (sort) qs.set("sort", sort);
  const cleanTag = tag?.trim().replace(/^#+/, "").toLowerCase();
  if (cleanTag) qs.set("tag", cleanTag);
  return (await request<{ posts: Post[] }>(`/api/community/feed?${qs.toString()}`)).posts ?? [];
};

export const getPost = async (id: string): Promise<Post> =>
  (await request<{ post: Post }>(`/api/community/posts/${encodeURIComponent(id)}`)).post;

export const createPost = async (
  text: string,
  groupId?: string | null,
  opts?: { flair?: string | null; tags?: string[] },
): Promise<Post> =>
  (
    await request<{ post: Post }>("/api/community/posts", {
      method: "POST",
      body: j({
        text,
        ...(groupId ? { group_id: groupId } : {}),
        ...(opts?.flair ? { flair: opts.flair } : {}),
        ...(opts?.tags && opts.tags.length > 0 ? { tags: opts.tags } : {}),
      }),
    })
  ).post;

export const updatePost = async (id: string, text: string): Promise<Post> =>
  (
    await request<{ post: Post }>(`/api/community/posts/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: j({ text }),
    })
  ).post;

export const deletePost = async (id: string): Promise<void> => {
  await request(`/api/community/posts/${encodeURIComponent(id)}`, { method: "DELETE" });
};

export const votePost = async (id: string, value: 1 | -1 | 0): Promise<VoteResult> =>
  request<VoteResult>(`/api/community/posts/${encodeURIComponent(id)}/vote`, {
    method: "POST",
    body: j({ value }),
  });

export const voteComment = async (id: string, value: 1 | -1 | 0): Promise<VoteResult> =>
  request<VoteResult>(`/api/community/comments/${encodeURIComponent(id)}/vote`, {
    method: "POST",
    body: j({ value }),
  });

export const getTrendingTags = async (limit = 12): Promise<TrendingTag[]> => {
  const r = await request<{ tags?: TrendingTag[]; items?: TrendingTag[] }>(
    `/api/community/tags/trending?limit=${limit}`,
  );
  return r.tags ?? r.items ?? [];
};

export const repostPost = async (
  id: string,
  text?: string,
  groupId?: string | null,
): Promise<Post> => {
  const r = await request<{ post?: Post } & Post>(
    `/api/community/posts/${encodeURIComponent(id)}/repost`,
    {
      method: "POST",
      body: j({
        ...(text?.trim() ? { text: text.trim() } : {}),
        ...(groupId ? { group_id: groupId } : {}),
      }),
    },
  );
  return r.post ?? r;
};

// ---------------------------------------------------------------- comments
export const getComments = async (postId: string): Promise<Comment[]> =>
  (await request<{ comments: Comment[] }>(`/api/community/posts/${encodeURIComponent(postId)}/comments`))
    .comments ?? [];

export const addComment = async (
  postId: string,
  text: string,
  parentId?: string | null,
): Promise<Comment> =>
  (
    await request<{ comment: Comment }>(
      `/api/community/posts/${encodeURIComponent(postId)}/comments`,
      {
        method: "POST",
        body: j({ text, ...(parentId ? { parent_id: parentId } : {}) }),
      },
    )
  ).comment;

// ---------------------------------------------------------------- reactions / bookmarks
export const toggleReaction = async (postId: string, kind = "like"): Promise<ReactionResult> =>
  request<ReactionResult>(`/api/community/posts/${encodeURIComponent(postId)}/reactions`, {
    method: "POST",
    body: j({ kind }),
  });

export const addBookmark = async (postId: string): Promise<void> => {
  await request(`/api/community/posts/${encodeURIComponent(postId)}/bookmarks`, {
    method: "POST",
  });
};

export const removeBookmark = async (postId: string): Promise<void> => {
  await request(`/api/community/posts/${encodeURIComponent(postId)}/bookmarks`, {
    method: "DELETE",
  });
};

// ---------------------------------------------------------------- follows / profiles
export const getFollows = async (): Promise<FollowEntry[]> => {
  const r = await request<{ follows?: FollowEntry[]; following?: FollowEntry[] }>(
    "/api/community/follows",
  );
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
  (await request<{ profile: Profile }>(`/api/community/profiles/${encodeURIComponent(handle)}`))
    .profile;

export const upsertProfile = async (p: ProfileIn): Promise<Profile> =>
  (await request<{ profile: Profile }>("/api/community/profiles/me", { method: "PUT", body: j(p) }))
    .profile;

// ---------------------------------------------------------------- groups
export const getGroups = async (): Promise<Group[]> =>
  (await request<{ groups: Group[] }>("/api/community/groups")).groups ?? [];

export const getGroup = async (id: string): Promise<Group> =>
  (await request<{ group: Group }>(`/api/community/groups/${encodeURIComponent(id)}`)).group;

export const createGroup = async (g: GroupIn): Promise<Group> =>
  (await request<{ group: Group }>("/api/community/groups", { method: "POST", body: j(g) })).group;

export const joinGroup = async (id: string): Promise<Group> =>
  (
    await request<{ group: Group }>(`/api/community/groups/${encodeURIComponent(id)}/join`, {
      method: "POST",
    })
  ).group;

export const leaveGroup = async (id: string): Promise<void> => {
  await request(`/api/community/groups/${encodeURIComponent(id)}/leave`, { method: "POST" });
};

export const getGroupPosts = async (id: string, limit = 50): Promise<Post[]> =>
  (
    await request<{ posts: Post[] }>(
      `/api/community/groups/${encodeURIComponent(id)}/posts?limit=${limit}`,
    )
  ).posts ?? [];

export const createGroupPost = async (
  id: string,
  text: string,
  opts?: { flair?: string | null; tags?: string[] },
): Promise<Post> =>
  (
    await request<{ post: Post }>(`/api/community/groups/${encodeURIComponent(id)}/posts`, {
      method: "POST",
      body: j({
        text,
        ...(opts?.flair ? { flair: opts.flair } : {}),
        ...(opts?.tags && opts.tags.length > 0 ? { tags: opts.tags } : {}),
      }),
    })
  ).post;

// ---------------------------------------------------------------- safety / block / mute / moderation
export const blockUser = async (handle: string): Promise<void> => {
  await request(`/api/community/blocks/${encodeURIComponent(handle)}`, { method: "POST" });
};

export const unblockUser = async (handle: string): Promise<void> => {
  await request(`/api/community/blocks/${encodeURIComponent(handle)}`, { method: "DELETE" });
};

export const muteTarget = async (kind: MuteKind, target: string): Promise<void> => {
  await request("/api/community/mutes", { method: "POST", body: j({ kind, target }) });
};

export const unmuteTarget = async (kind: MuteKind, target: string): Promise<void> => {
  const qs = new URLSearchParams({ kind, target });
  await request(`/api/community/mutes?${qs.toString()}`, { method: "DELETE" });
};

export const getSafety = async (): Promise<SafetyState> => {
  const r = await request<{
    blocked?: SafetyBlockEntry[];
    blocks?: SafetyBlockEntry[];
    mutes?: SafetyMuteEntry[];
    muted?: SafetyMuteEntry[];
  }>("/api/community/safety");
  return {
    blocked: r.blocked ?? r.blocks ?? [],
    mutes: r.mutes ?? r.muted ?? [],
  };
};

export const reportTarget = async (
  targetType: "post" | "comment" | "profile",
  targetId: string,
  reason: string,
  detail?: string,
): Promise<{ report?: unknown; event?: ModerationEvent }> =>
  request("/api/community/reports", {
    method: "POST",
    body: j({
      target_type: targetType,
      target_id: targetId,
      reason,
      ...(detail?.trim() ? { detail: detail.trim() } : {}),
    }),
  });

export const getModerationQueue = async (groupId?: string): Promise<ModerationEvent[]> => {
  const qs = new URLSearchParams();
  if (groupId) qs.set("group_id", groupId);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const r = await request<{ events?: ModerationEvent[]; queue?: ModerationEvent[] }>(
    `/api/community/moderation/queue${suffix}`,
  );
  return r.events ?? r.queue ?? [];
};

export const resolveModeration = async (
  eventId: string,
  decision: "keep" | "remove" | "restore",
  note?: string,
): Promise<{ event?: ModerationEvent; target_state?: string }> =>
  request(`/api/community/moderation/${encodeURIComponent(eventId)}/resolve`, {
    method: "POST",
    body: j({ decision, ...(note?.trim() ? { note: note.trim() } : {}) }),
  });

// ---------------------------------------------------------------- discovery / search / inbox
export const getDiscovery = async (
  limit = 20,
  context?: ContextEnvelope | null,
  sort?: FeedSort,
): Promise<DiscoveryResult> => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (sort) qs.set("sort", sort);
  if (context && !context.paused) {
    if (context.area_coarse) qs.set("area_coarse", context.area_coarse);
    if (context.device_class) qs.set("device_class", context.device_class);
    if (context.time_bucket) qs.set("time_bucket", context.time_bucket);
    if (context.user_state) qs.set("user_state", context.user_state);
  }
  return request<DiscoveryResult>(`/api/community/discovery?${qs.toString()}`);
};

export const searchCommunity = async (q: string): Promise<SearchResults> =>
  request<SearchResults>(`/api/community/search?q=${encodeURIComponent(q)}`);

export const getNotifications = async (): Promise<{
  notifications: Notification[];
  unread_count: number;
}> => {
  const r = await request<{
    notifications: Notification[];
    unread_count?: number;
    unread?: number;
  }>("/api/community/inbox");
  return { notifications: r.notifications ?? [], unread_count: r.unread_count ?? r.unread ?? 0 };
};

export const markNotificationRead = async (id: string): Promise<void> => {
  await request(`/api/community/notifications/${id}/read`, { method: "POST" });
};

export const markAllNotificationsRead = async (): Promise<void> => {
  await request("/api/community/notifications/read-all", { method: "POST" });
};

// ---------------------------------------------------------------- memory consent (split + D19 lower)
export interface MemoryConsent {
  read_enabled: boolean;
  write_enabled?: boolean;
  remember_saved_discussions?: boolean;
  remember_public_posts?: boolean;
  allow_interest_export: boolean;
  default_off: boolean;
  as_of?: string;
  provenance?: string;
}

export type MemoryConsentInput = {
  read_enabled: boolean;
  write_enabled?: boolean;
  remember_saved_discussions?: boolean;
  remember_public_posts?: boolean;
  allow_interest_export: boolean;
};

export interface ForgetResult {
  records_forgotten: number;
  facts_erased: number;
  as_of?: string;
}

export interface LowerMemoryResult {
  lowered?: boolean;
  weights_lowered?: number;
  w_min?: number;
  as_of?: string;
}

export const getMemoryConsent = (): Promise<MemoryConsent> =>
  request<MemoryConsent>("/api/community/memory/consent");

export const setMemoryConsent = (c: MemoryConsentInput): Promise<MemoryConsent> =>
  request<MemoryConsent>("/api/community/memory/consent", {
    method: "POST",
    body: JSON.stringify(c),
  });

export const forgetMemory = (): Promise<ForgetResult> =>
  request<ForgetResult>("/api/community/memory/forget", { method: "POST" });

export const lowerCommunityMemory = (): Promise<LowerMemoryResult> =>
  request<LowerMemoryResult>("/api/community/memory/lower", { method: "POST" });

// ---------------------------------------------------------------- context & usage profile (E14b + D19/D19b)
export const sendContextHeartbeat = async (ctx: ContextEnvelope): Promise<ContextEnvelope> => {
  const r = await request<{ context?: ContextEnvelope } & ContextEnvelope>(
    "/api/community/context/heartbeat",
    {
      method: "POST",
      body: j(ctx),
    },
  );
  return r.context ?? r;
};

export const getCurrentContext = async (): Promise<ContextEnvelope | null> => {
  const r = await request<{ context?: ContextEnvelope | null }>("/api/community/context/current");
  return r.context ?? null;
};

export const logInteractionEvent = async (ev: InteractionEventIn): Promise<void> => {
  await request("/api/community/events", { method: "POST", body: j(ev) });
};

export const getUsageProfile = async (includeLowered = true): Promise<UsageProfileResult> => {
  const r = await request<{
    context_aware_enabled?: boolean;
    buckets?: UsageBucket[];
    items?: UsageBucket[];
    as_of?: string;
  }>(`/api/community/usage/profile?include_lowered=${includeLowered}`);
  return {
    context_aware_enabled: r.context_aware_enabled ?? true,
    buckets: r.buckets ?? r.items ?? [],
    as_of: r.as_of,
  };
};

export const lowerUsageTopic = async (
  topicKey: string,
): Promise<{ bucket?: UsageBucket; weight?: number }> =>
  request("/api/community/usage/lower", {
    method: "POST",
    body: j({ topic_key: topicKey }),
  });

export const restoreUsageTopic = async (
  topicKey: string,
): Promise<{ bucket?: UsageBucket; weight?: number }> =>
  request("/api/community/usage/restore", {
    method: "POST",
    body: j({ topic_key: topicKey }),
  });

export const recallUsageTopic = async (
  topicKey?: string,
  query?: string,
): Promise<{ recalled?: UsageBucket[]; matched?: UsageBucket[]; buckets?: UsageBucket[] }> =>
  request("/api/community/usage/recall", {
    method: "POST",
    body: j({
      ...(topicKey?.trim() ? { topic_key: topicKey.trim() } : {}),
      ...(query?.trim() ? { query: query.trim() } : {}),
    }),
  });

export const setUsageSettings = async (
  contextAwareEnabled: boolean,
): Promise<{ context_aware_enabled: boolean }> =>
  request("/api/community/usage/settings", {
    method: "PUT",
    body: j({ context_aware_enabled: contextAwareEnabled }),
  });
