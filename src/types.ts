// Shared types used across screens. Change one only with every importer in mind (npm run typecheck finds them).

export type ScreenId =
  | "chats" | "flights" | "stocks" | "weather" | "mail" | "calendar"
  | "files" | "ai" | "research" | "history" | "ai-cleaner";

export type ModalId = "profile" | "settings" | null;
/** A card that opens over whatever screen is showing (desktop: centred; phone: bottom sheet) instead of switching screens. */
export type QuickCard = { kind: "flights"; query: FlightQuery; flights?: Flight[] } | { kind: "draft"; id: string } | null;

/* ---------- chats ---------- */
export interface Contact {
  id: string;
  name: string;
  avatar: string;
  online?: boolean;
}

export type MessageBody =
  | { kind: "text"; text: string }
  | { kind: "image"; url: string; caption?: string }
  | { kind: "voice"; seconds: number }
  | { kind: "video"; url: string; caption?: string }
  /** `taskId` links the card to its Mirsal Updates task (tap opens it and marks it seen). */
  | { kind: "card"; title: string; subtitle: string; icon: "flight" | "research" | "mail"; taskId?: string }
  | { kind: "sticker"; url: string; pack?: string }
  /* @mirsal replies in a chat (rendered faint, with the Mirsal mark) */
  | { kind: "ai"; text: string; label?: string; verdict?: Verdict; sources?: AiSource[]; status?: string; demo?: boolean }
  | { kind: "choices"; mode: "sticker" | "image"; title: string; status?: string; packId?: string;
      options: { url?: string; label?: string; prompt?: string }[]; chosen?: number }
  | { kind: "plan"; plan: TripPlan; flights?: Flight[]; flightsState?: "loading" | "ready" | "none" | "error"; groupId?: string };

export type Verdict = "true" | "mostly_true" | "misleading" | "false" | "unverified";
export interface AiSource { title: string; url: string; domain: string }

/** "@mirsal setup plan for this" — built by the agents service (agents/mirsal_agents/chat_skills.py).
 *  `needsDates` = dates are still missing: the card asks for them and nothing was filed, drafted or scheduled.
 *  `destination` identifies the resolved country/city/airport for date changes. */
export interface TripPlan {
  title: string; summary: string; status: string;
  steps: PlanStep[];
  calendar: { year: number; month: number; from: string; to: string; free: string[] };
  needsDates?: boolean;
  destination?: { country: string; city: string; iata: string };
}
export type PlanStep =
  | { kind: "leave"; title: string; detail: string; data: { leave: { from: string; to: string; days: number; leaveDays: number }; nadi: { ref: string; status: string; balanceBefore: number; balanceAfter: number } } }
  | { kind: "flights"; title: string; detail: string; data: { query: FlightQuery } }
  | { kind: "budget"; title: string; detail: string; data: { aed: number; rate: number; currency: string; local: number } }
  | { kind: "group"; title: string; detail: string; data: { name: string; members: string[]; suggested: string[] } }
  | { kind: "reminder"; title: string; detail: string; data: { events: Omit<CalendarEvent, "id">[] } }
  | { kind: "email"; title: string; detail: string; data: { to: string; subject: string; body: string; draftId?: string } }
  | { kind: "dates"; title: string; detail: string; data: { from?: string } }
  | { kind: "weather"; title: string; detail: string; data: Record<string, unknown> };

export interface Message {
  id: string;
  chatId: string;
  fromMe: boolean;
  time: string; // display time, e.g. "3:03 PM"
  body: MessageBody;
  /** Written by Mirsal (an @mirsal reply), not by a person. */
  by?: "mirsal";
  /** Quoted message this one replies to. */
  replyTo?: { id: string; sender: string; text: string };
}

export interface Chat {
  id: string;
  contact: Contact;
  preview: string;
  time: string;
  unread: number;
  muted?: boolean;
}

/* ---------- Mirsal tasks (powers Mirsal Updates) ---------- */
export type TaskStatus = "queued" | "running" | "completed" | "failed";
export type TaskType = "image" | "flight" | "research" | "email" | "video" | "esign" | "event";

export interface MirsalTask {
  id: string;
  type: TaskType;
  title: string;      // "Image ready" / "Generating image"
  subtitle: string;   // "Your social post visual is ready"
  status: TaskStatus;
  progress?: number;  // 0-100 only if really known
  startedAt: number;  // epoch ms
  completedAt?: number;
  unread: boolean;
  result?: TaskResult;
  error?: string;
  dismissed?: boolean; // hidden from Mirsal Updates; the task still runs and delivers
}

export type TaskResult =
  | { type: "image"; imageUrl: string; prompt: string }
  | { type: "video"; videoUrl: string; prompt: string; title: string }
  | { type: "flight"; query: FlightQuery; flights: Flight[] }
  | { type: "research"; items: ResearchItem[] }
  | { type: "email"; drafts: EmailDraft[] }
  /** A document to sign with UAE PASS (demo). Signed once `signedAt` is set. */
  | { type: "esign"; doc: "eand-renewal"; signature?: string; signedAt?: number }
  /** A UAE event from Diwan (agents service → Diwan MCP); up to 3 pictures from Supabase Storage. */
  | { type: "event"; event: DiwanEvent };

export interface DiwanEvent {
  id: string; title: string; titleAr: string; kind: string; date: string; when: string;
  summary: string; images: string[]; source: string;
  /** Pictures Diwan holds more versions of ("More from this picture"); a subset of `images`. */
  more?: string[];
}

/* ---------- flights ---------- */
export interface FlightQuery {
  from: string;   // IATA, e.g. "DXB"
  to: string;
  depart: string; // YYYY-MM-DD
  return?: string;
  passengers: number;
  cabin: "economy" | "business" | "first";
}

export interface Flight {
  id: string;
  airline: string;
  airlineLogo?: string;
  flightNo: string;
  date: string;      // display, "Thu, 12 Dec"
  fromCode: string;
  fromTime: string;
  toCode: string;
  toTime: string;
  duration: string;  // "7h 25m"
  stops: number;
  price: number;
  currency: string;
  cabin: string;
  bestPrice?: boolean;
}

/* ---------- weather ---------- */
export interface WeatherReport {
  location: string;
  country: string;
  tempC: number;
  feelsLikeC: number;
  condition: string;
  humidity: number;
  windKmh: number;
  uv: number;
  hourly: { time: string; tempC: number; code: number }[];
  daily: { day: string; minC: number; maxC: number; code: number; condition: string }[];
}

/* ---------- calendar ---------- */
export interface CalendarEvent {
  id: string;
  title: string;
  start: string; // ISO
  end: string;   // ISO
  calendar: "personal" | "work" | "travel" | "family" | "flights";
  location?: string;
  notes?: string;
}

/* ---------- content ---------- */
export interface ResearchItem {
  id: string;
  title: string;
  summary: string;
  time: string;
  findings: string[];
  sources?: { title: string; domain: string; url?: string }[];
  image?: string;
  /* deep research (agents service) */
  sections?: { heading: string; body: string }[];
  ranking?: { name: string; why: string; price: string; sources: number[] }[];
  verified?: string; // "9/10" claims checked against their sources
}

export interface EmailDraft {
  id: string;
  to: string;
  subject: string;
  body: string;
  time: string;
  /** Written by Mirsal (e.g. a trip plan's leave email), shown as such in Drafts. */
  by?: "mirsal";
}

/* ---------- AI chat ---------- */
export interface AiMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  imageUrl?: string;
  status?: string; // minimal, e.g. "Searched 8 sources · 12s"
  pending?: boolean;
  taskId?: string; // Mirsal task this reply waits on (e.g. an image job); the image shows when it completes
  enter?: boolean; // play the entrance animation (a newly arrived video)
}
