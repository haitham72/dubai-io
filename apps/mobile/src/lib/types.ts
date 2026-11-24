/**
 * Navigation and screen contracts shared with I-B
 * (`src/features/{vault,quests,connect}`).
 * Those folders are not created here.
 */

export type PillarId = "today" | "chat" | "quests" | "memory";

export type Provenance =
  | "official"
  | "provider_confirmed"
  | "merchant_submitted"
  | "user_supplied"
  | "inferred"
  | "estimate"
  | "demo_fixture";

export interface DemoMeta {
  demo: boolean;
  provenance: Provenance;
  asOf: string;
}

export interface DockTab {
  id: PillarId;
  label: string;
  href: "/" | "/chat" | "/quests" | "/memory";
}

export const DOCK_TABS: DockTab[] = [
  { id: "today", label: "Today", href: "/" },
  { id: "chat", label: "Chat", href: "/chat" },
  { id: "quests", label: "Quests", href: "/quests" },
  { id: "memory", label: "Memory", href: "/memory" },
];

export type LifeTheme = "career" | "projects" | "learning" | "gaming" | "travel" | "health";

export interface AuthSession {
  sessionToken: string;
  sessionId: string;
  userId: string;
  displayName: string | null;
  email: string | null;
}

export interface ChatCitation {
  fact_id: string;
  text: string;
  why_url?: string;
  provenance?: string;
  as_of?: string;
}

export interface TodayCard extends DemoMeta {
  id: string;
  title: string;
  subtitle?: string;
  eyebrow?: string;
  interest?: string;
  category?: string;
  imageUrl?: string | null;
  source?: string;
  url?: string | null;
  because: string;
  tone: LifeTheme;
}

export interface TodayRail {
  id: string;
  title: string;
  cards: TodayCard[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  at: string;
  /** True only after a confirmed memory write. Never set on send, offline, or demo fallback. */
  ingested: boolean;
  ingestDetail?: string;
  citations?: ChatCitation[];
  error?: boolean;
  demo: boolean;
}

export interface RepairPing extends DemoMeta {
  id: string;
  title: string;
  body: string;
}

export interface ActionCard extends DemoMeta {
  id: string;
  title: string;
  subtitle: string;
}

export interface LifeDrawerItem {
  id: string;
  label: string;
  detail: string;
}

export interface PillarScreenProps {
  ownerId: string;
  apiBaseUrl: string;
  demo: boolean;
  sessionToken?: string | null;
}

export interface VaultScreenProps extends PillarScreenProps {}

export interface QuestsScreenProps extends PillarScreenProps {}

export interface ConnectScreenProps extends PillarScreenProps {
  onApiBaseUrlChange: (url: string) => void;
  localhostWarning: string | null;
}

export interface MemoryTurnConfirmation {
  ok: boolean;
  ingested?: boolean;
  applied: boolean;
  appliedFactIds: string[];
  citations?: ChatCitation[];
  reply: string;
  runner?: string;
  model?: string;
  asOf?: string;
  trust?: string;
  topic?: string;
  demo: boolean;
  warning: string | null;
  error?: string;
}
