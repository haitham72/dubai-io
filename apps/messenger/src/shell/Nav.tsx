import {
  BarChart3, Calendar, CloudSun, Eraser, FolderClosed, History, Mail, MessageCircle, PanelLeftClose, PanelLeftOpen, Plane,
  Search, Settings,
} from "lucide-react";
import { useState, type ComponentType } from "react";
import type { LucideProps } from "lucide-react";
import { actions, useStore } from "../store";
import { Avatar, ICON } from "../ui";
import type { ScreenId } from "../types";
import { me } from "../chats/data";
import s from "./shell.module.css";

const main: { id: ScreenId; label: string; icon: ComponentType<LucideProps> }[] = [
  { id: "chats", label: "Chats", icon: MessageCircle },
  { id: "files", label: "Files", icon: FolderClosed },
  { id: "flights", label: "Flights", icon: Plane },
  { id: "stocks", label: "Stocks", icon: BarChart3 },
  { id: "weather", label: "Weather", icon: CloudSun },
  { id: "mail", label: "Mail", icon: Mail },
  { id: "calendar", label: "Calendar", icon: Calendar },
  { id: "research", label: "Research", icon: Search },
  { id: "ai-cleaner", label: "Clean AI", icon: Eraser },
];

export function Nav() {
  const screen = useStore((st) => st.screen);
  const unreadTasks = useStore((st) => st.tasks.filter((t) => t.unread).length);
  const [collapsed, setCollapsed] = useState(false);

  const item = (id: ScreenId, label: string, I: ComponentType<LucideProps>, badge?: number) => {
    const on = screen === id || (id === "chats" && screen === "ai"); // Mirsal AI opens from Chats
    return <button key={id} className={`${s.navItem} ${on ? s.navItemActive : ""}`}
      onClick={() => actions.navigate(id)} aria-current={on ? "page" : undefined} title={collapsed ? label : undefined}>
      <I {...ICON} />
      <span>{label}</span>
      {!!badge && <span className={s.navBadge}>{badge > 9 ? "9+" : badge}</span>}
    </button>;
  };

  return (
    <nav className={`${s.nav} ${collapsed ? s.navCollapsed : ""}`} aria-label="Main">
      <div className={s.brand}>
        <img className={s.logo} src="/mirsal-logo.png" alt="" />
        <span className={s.brandName}>Mirsal</span>
        <button className={s.collapseBtn} onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand" : "Collapse"}>
          {collapsed ? <PanelLeftOpen {...ICON} /> : <PanelLeftClose {...ICON} />}
        </button>
      </div>
      <div className={s.navGroup}>
        {main.map((m) => item(m.id, m.label, m.icon, m.id === "chats" ? unreadTasks : undefined))}
      </div>
      <div className={s.navDivider} />
      <div className={s.navGroup}>
        {item("history", "History", History)}
        <button className={s.navItem} onClick={() => actions.openModal("settings")} title={collapsed ? "Settings" : undefined}>
          <Settings {...ICON} />
          <span>Settings</span>
        </button>
      </div>
      <div className={s.spacer} />
      <button className={s.me} onClick={() => actions.openModal("profile")}>
        <Avatar src={me.avatar} size={36} online />
        <span className={s.meText}>
          <span className={s.meName}>{me.name}</span>
          <span className={s.meStatus}>Online</span>
        </span>
      </button>
    </nav>
  );
}
