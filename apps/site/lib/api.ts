/** Base URL of the Dubai-io API. Local default; no secrets here. */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/** Restricted browser Maps key (referrer-restricted in Google Cloud). Never a secret. */
export const MAPS_KEY = process.env.NEXT_PUBLIC_MAPS_KEY ?? "";

/** Join a path onto the API base (path must start with "/"). */
export function apiUrl(path: string): string {
  return `${API_BASE.replace(/\/$/, "")}${path}`;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** GET JSON from the API, carrying the anonymous cookie session. */
export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers: { accept: "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(
      res.status,
      body || `Request failed (${res.status})`,
    );
  }
  return (await res.json()) as T;
}

/** POST JSON to the API, carrying the anonymous cookie session. */
export async function apiPost<T>(
  path: string,
  body?: unknown,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    credentials: "include",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, text || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/* Loose shapes for backend payloads. Fields stay optional so the site
   degrades gracefully when the backend adds or renames something. */

export interface TaskItem {
  id?: string;
  title?: string;
  detail?: string;
  status?: string;
  due_at?: string | null;
  updated_at?: string;
  source_status?: string;
  decision?: {
    kind?: string;
    title?: string;
    detail?: string;
    action_id?: string;
    revision?: number;
    snapshot_hash?: string;
    amount_aed?: number;
  };
}

export interface TodayLane {
  tasks: TaskItem[];
  has_more?: boolean;
  count?: number;
}

export interface TodayData {
  needs_you?: TodayLane;
  running?: TodayLane;
  on_list?: TodayLane;
  paused?: TodayLane;
  scheduled?: TodayLane;
  counts?: { needs_you?: number; running?: number; on_list?: number; paused?: number };
  current_work?: Array<{ task?: TaskItem; source?: { status?: string } }>;
  as_of?: string;
}

export interface NewsArticle {
  id?: string;
  title?: string;
  subtitle?: string;
  url?: string;
  source?: string;
  published_at?: string;
  thumbnail?: { url?: string; credit?: string } | null;
  provenance?: string;
}

export interface Community {
  id: string;
  name: string;
  handle?: string;
  topic?: string;
  about?: string;
  image?: string | null;
  members?: number;
  joined?: boolean;
  provenance?: string;
}

export interface Author {
  name?: string;
  handle?: string;
  emoji?: string;
}

export function authorName(author?: Author | string | null): string {
  if (!author) return "Someone";
  if (typeof author === "string") return author;
  return author.name ?? author.handle ?? "Someone";
}

export interface Post {
  id: string;
  community?: { id?: string; name?: string; joined?: boolean };
  author?: Author | string;
  text?: string;
  image?: string | null;
  created_at?: string;
  provenance?: string;
  comments?: number;
  likes?: number;
  mine?: boolean;
}

export interface FeedComment {
  id: string;
  author?: Author | string;
  text?: string;
  created_at?: string;
  provenance?: string;
  parent_id?: string | null;
  mine?: boolean;
}

export interface ChatThread {
  id: string;
  title?: string;
  kind?: string;
  unread?: number;
}

export interface ChatMessage {
  id?: string;
  author?: string;
  text?: string;
  created_at?: string;
  at?: string;
  provenance?: string;
  mine?: boolean;
}

export interface CatalogItem {
  id: string;
  name: string;
  /** The backend serialises fixed prices as strings ("6") or numbers. */
  price_aed?: number | string;
}

export function priceAed(value: number | string | undefined): number | null {
  if (value === undefined || value === null) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export interface CatalogProvider {
  id: string;
  name: string;
  service: string;
  items?: CatalogItem[];
  slots?: string[];
}
