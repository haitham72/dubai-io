"use client";
import { Home, LayoutGrid, MessageCircle, Newspaper, Search } from "lucide-react";
import s from "./mobile.module.css";

export type Tab = "home" | "chat" | "services" | "feed" | "ask";
const TABS = [
  { id: "home", label: "Home", icon: Home },
  { id: "chat", label: "Chat", icon: MessageCircle },
  { id: "services", label: "Services", icon: LayoutGrid },
  { id: "feed", label: "Feed", icon: Newspaper },
] as const;

export function TabBar({ tab, onTab, onAsk }: { tab: Tab; onTab: (t: Tab) => void; onAsk: () => void }) {
  return (
    <nav className={s.tabbar} data-testid="tabbar" aria-label="Main">
      <div className={s.tabs}>
        {TABS.map(({ id, label, icon: I }) => (
          <button key={id} className={`${s.tab} ${tab === id ? s.tabActive : ""}`} aria-current={tab === id ? "page" : undefined} onClick={() => onTab(id)}>
            <I size={22} strokeWidth={1.6} />
            <span>{label}</span>
          </button>
        ))}
      </div>
      <button className={s.ask} onClick={onAsk}>
        <Search size={22} strokeWidth={1.8} />
        <span>Ask</span>
      </button>
    </nav>
  );
}
