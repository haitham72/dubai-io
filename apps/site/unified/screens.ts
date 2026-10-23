import { Building2, LayoutGrid, MapPin, MessageCircle, Sparkles, UserRound, type LucideIcon } from "lucide-react";

export type ScreenId = "assistant" | "chats" | "services" | "maps" | "dashboard" | "me";

export const RAIL: { id: ScreenId; label: string; icon: LucideIcon; plan: number }[] = [
  { id: "assistant", label: "Assistant", icon: Sparkles, plan: 1 },
  { id: "chats", label: "Chats", icon: MessageCircle, plan: 3 },
  { id: "services", label: "Services", icon: LayoutGrid, plan: 4 },
  { id: "maps", label: "Maps", icon: MapPin, plan: 4 },
  { id: "dashboard", label: "Dashboard", icon: Building2, plan: 5 },
  { id: "me", label: "Me", icon: UserRound, plan: 6 },
];

export const PLAN_FOR: Record<ScreenId, number> = Object.fromEntries(RAIL.map((r) => [r.id, r.plan])) as Record<ScreenId, number>;
export const TITLE_FOR: Record<ScreenId, string> = Object.fromEntries(RAIL.map((r) => [r.id, r.label])) as Record<ScreenId, string>;
