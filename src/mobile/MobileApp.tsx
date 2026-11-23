// iPhone layout: 4 tabs (Chats · Mirsal AI · Apps · Settings), pushed pages, sheets.
// Navigation still goes through `actions` in src/store.ts; this shell only maps store.screen to a tab.
import { useEffect, useRef, useState } from "react";
import {
  ArrowDownUp, BatteryFull, Bell, Signal, Wifi, HardDrive, LayoutGrid, MessageCircle, Monitor, Settings, ShieldCheck, Sparkles, UserRound,
} from "lucide-react";
import { useStore } from "../store";
import type { ScreenId } from "../types";
import { ProfileModal, SettingsModal } from "../profile";
import { actions } from "../store";
import { ChatList } from "./ChatList";
import { AppsHome } from "./Apps";
import { AiPage, ConversationPage, SettingsPage, WorkspacePage } from "./Pages";
import { UpdatesSheet } from "./UpdatesSheet";
import { DynamicIsland } from "./DynamicIsland";
import { CommandCard } from "../voice/CommandCard";
import { MediaFeed } from "./Feed";
import { devicePreview } from "./useIsMobile";
import { QuickCards } from "../quick/QuickCards";
import s from "./mobile.module.css";

type Tab = "chats" | "ai" | "apps" | "settings";
const tabOf = (screen: ScreenId): Tab => (screen === "chats" ? "chats" : screen === "ai" ? "ai" : "apps");

const settingsCells = [
  [
    { tone: s.toneCyan, icon: Sparkles, label: "Mirsal AI", value: "Nano Banana 2" },
    { tone: s.toneBlue, icon: UserRound, label: "Account" },
    { tone: s.toneGreen, icon: MessageCircle, label: "Chats" },
    { tone: s.toneRed, icon: Bell, label: "Notifications" },
    { tone: s.toneBlue, icon: ShieldCheck, label: "Privacy" },
  ],
  [
    { tone: s.toneGrey, icon: Monitor, label: "Mirsal Web/Desktop" },
    { tone: s.toneGreen, icon: ArrowDownUp, label: "Data Usage" },
    { tone: s.toneOrange, icon: HardDrive, label: "Storage Usage", value: "2.4 GB" },
  ],
];

export function MobileApp() {
  const screen = useStore((st) => st.screen);
  const modal = useStore((st) => st.modal);
  const activeChatId = useStore((st) => st.activeChatId);
  const chatRequest = useStore(st => st.chatRequest);
  const lastMine = useStore((st) => { for (let i = st.messages.length - 1; i >= 0; i--) if (st.messages[i].fromMe) return st.messages[i].id; return ""; });
  const unread = useStore((st) => st.tasks.filter((t) => t.unread && !t.dismissed).length);

  const [tab, setTab] = useState<Tab>(tabOf(screen));
  const [chatOpen, setChatOpen] = useState(false);
  const [appOpen, setAppOpen] = useState(tabOf(screen) === "apps");
  const [updates, setUpdates] = useState<{ id?: string } | null>(null);

  // Any navigate() (Updates "View all flights", AI links…) lands on the right tab and page.
  useEffect(() => {
    setTab(tabOf(screen));
    if (tabOf(screen) === "apps") setAppOpen(true);
    setUpdates(null);
  }, [screen]);

  // "Use in chat" / openChat from anywhere opens that conversation.
  const seen = useRef(`${lastMine}|${activeChatId}|${chatRequest}`);
  useEffect(() => {
    const key = `${lastMine}|${activeChatId}|${chatRequest}`;
    if (key === seen.current) return;
    seen.current = key;
    setTab("chats"); setChatOpen(true); setUpdates(null);
  }, [lastMine, activeChatId, chatRequest]);

  const go = (t: Tab) => {
    setTab(t);
    if (t === "chats") { actions.navigate("chats"); setChatOpen(false); }
    if (t === "ai") actions.navigate("ai");
    if (t === "apps") setAppOpen(false);
  };

  const openUpdates = (id?: string) => setUpdates({ id });
  const updatesRequest = useStore((st) => st.updatesRequest);
  useEffect(() => { if (updatesRequest) setUpdates({}); }, [updatesRequest]);
  const pushed = (tab === "chats" && chatOpen) || (tab === "apps" && appOpen && screen !== "chats" && screen !== "ai");

  return (
    <div className={`${s.app} ${devicePreview ? s.device : ""}`}>
      {devicePreview && <DeviceChrome />}
      {tab === "chats" && (chatOpen
        ? <ConversationPage onBack={() => setChatOpen(false)} onUpdates={() => openUpdates()} />
        : <ChatList onOpenChat={() => setChatOpen(true)} onOpenUpdates={openUpdates} />)}
      {tab === "ai" && <AiPage onUpdates={() => openUpdates()} />}
      {tab === "apps" && (pushed ? <WorkspacePage id={screen} onBack={() => setAppOpen(false)} /> : <AppsHome />)}
      {tab === "settings" && <SettingsPage cells={settingsCells} />}

      {!pushed && (
        <nav className={s.tabbar}>
          {([
            ["chats", "Chats", MessageCircle],
            ["ai", "Mirsal AI", Sparkles],
            ["apps", "Apps", LayoutGrid],
            ["settings", "Settings", Settings],
          ] as const).map(([id, label, I]) => (
            <button key={id} className={`${s.tab} ${tab === id ? s.tabOn : ""}`} aria-current={tab === id ? "page" : undefined} onClick={() => go(id)}>
              <I size={24} strokeWidth={1.75} />
              {label}
              {id === "chats" && unread > 0 && tab !== "chats" && <span className={s.tabBadge}>{unread}</span>}
            </button>
          ))}
        </nav>
      )}

      <MediaFeed />
      <DynamicIsland onOpen={openUpdates} />
      {updates && <UpdatesSheet initialId={updates.id} onClose={() => setUpdates(null)} />}
      <CommandCard />
      {modal === "profile" && <ProfileModal onClose={actions.closeModal} />}
      {modal === "settings" && <SettingsModal onClose={actions.closeModal} />}
      <QuickCards />
    </div>
  );
}

/** ?device preview only: what iOS itself draws on an iPhone 17 Pro Max (light status bar + hardware island). */
function DeviceChrome() {
  return (
    <div className={s.deviceChrome} aria-hidden="true">
      <span>9:41</span>
      <i className={s.hwIsland} />
      <span className={s.deviceIcons}><Signal size={17} strokeWidth={2.4} /><Wifi size={17} strokeWidth={2.4} /><BatteryFull size={22} strokeWidth={1.8} /></span>
    </div>
  );
}
