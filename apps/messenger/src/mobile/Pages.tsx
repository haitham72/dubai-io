// Pushed / tab pages that wrap the existing screen components for the phone.
import { useState } from "react";
import { ChevronLeft, ChevronRight, History, List, Phone, SquarePen, Video, type LucideIcon } from "lucide-react";
import { actions, useStore, type Theme } from "../store";
import type { ScreenId } from "../types";
import { ICON } from "../ui";
import { screens } from "../screens";
import { useChat } from "../chats/list";
import { useContactTyping } from "../chats/autoReply";
import { ai } from "../ai/state";
import { me } from "../profile/data";
import { APPS } from "./Apps";
import { GlassButton, LargeTitle, NavBar, ORB, OrbButton } from "./parts";
import { Sheet, closeOnRowTap } from "./Sheet";
import s from "./mobile.module.css";

/** Conversation: floating glass toolbar over the existing Chats conversation (its desktop header hides on phones). */
export function ConversationPage({ onBack, onUpdates }: { onBack: () => void; onUpdates: () => void }) {
  const activeId = useStore((st) => st.activeChatId);
  const chat = useChat(activeId);
  const typing = useContactTyping(activeId);
  const status = typing !== undefined ? (typing ? `${typing} is typing…` : "typing…") : chat.contact.online ? "online" : "last seen recently";
  const { Main } = screens.chats;
  return (
    <div className={s.page}>
      <NavBar>
        <GlassButton icon={ChevronLeft} label="Back" onClick={onBack} />
        <div className={`${s.gpill} ${s.who}`}>
          <img src={chat.contact.avatar} alt="" />
          <span><b>{chat.contact.name}</b><small className={chat.contact.online || typing !== undefined ? s.whoOnline : ""}>{status}</small></span>
        </div>
        <div className={s.gpill}>
          <button className={s.pillBtn} aria-label="Video call"><Video {...ICON} /></button>
          <button className={s.pillBtn} aria-label="Voice call"><Phone {...ICON} /></button>
        </div>
        <OrbButton onClick={onUpdates} />
      </NavBar>
      <div className={s.fill}><Main /></div>
    </div>
  );
}

/** Messenger AI tab: the existing AI conversation; its chat history opens as a sheet. */
export function AiPage({ onUpdates }: { onUpdates: () => void }) {
  const [history, setHistory] = useState(false);
  const { Main, Sidebar } = screens.ai;
  return (
    <div className={s.page}>
      <NavBar>
        <GlassButton icon={History} label="Chat history" onClick={() => setHistory(true)} />
        <div className={`${s.gpill} ${s.who} ${s.whoCenter}`}>
          <img src={ORB} alt="" />
          <span><b>Messenger AI</b><small>Images · video · research</small></span>
        </div>
        <GlassButton icon={SquarePen} label="New chat" onClick={ai.newChat} />
        <OrbButton onClick={onUpdates} />
      </NavBar>
      <div className={s.fill}><Main /></div>
      {history && Sidebar && (
        <Sheet label="Chat history" onClose={() => setHistory(false)}>
          <div className={s.sideSheet} onClickCapture={closeOnRowTap(() => setHistory(false))}><Sidebar /></div>
        </Sheet>
      )}
    </div>
  );
}

const sideLabel: Partial<Record<ScreenId, string>> = {
  flights: "Bookings", calendar: "Calendars", stocks: "Watchlist", files: "Folders",
  mail: "Inbox", research: "Reports", history: "All activity",
};

/** A workspace opened from Apps: back to Apps, its title, and its sidebar as a sheet. */
export function WorkspacePage({ id, onBack }: { id: ScreenId; onBack: () => void }) {
  const [side, setSide] = useState(false);
  const { Main, Sidebar } = screens[id];
  const app = APPS.find((a) => a.id === id);
  return (
    <div className={s.page}>
      <div className={s.wsBar}>
        <button className={s.backLink} onClick={onBack}><ChevronLeft {...ICON} size={24} />Apps</button>
        <h1 className={s.wsTitle}>{app?.label}</h1>
        {Sidebar ? <button className={s.backLink} onClick={() => setSide(true)}><List {...ICON} />{sideLabel[id]}</button> : <span className={s.wsSpacer} />}
      </div>
      <div className={`${s.fill} ${s.workspace}`} key={id}><Main /></div>
      {side && Sidebar && (
        <Sheet label={sideLabel[id] ?? "Menu"} onClose={() => setSide(false)}>
          <div className={s.sideSheet} onClickCapture={closeOnRowTap(() => setSide(false))}><Sidebar /></div>
        </Sheet>
      )}
    </div>
  );
}

const themes: { value: Theme; label: string }[] = [{ value: "light", label: "Light" }, { value: "dark", label: "Dark" }, { value: "system", label: "Auto" }];

function Cell({ tone, icon: I, label, value, onClick }: {
  tone: string; icon: LucideIcon; label: string; value?: string; onClick?: () => void;
}) {
  return (
    <button className={s.cell} onClick={onClick}>
      <span className={`${s.cellIcon} ${tone}`}><I size={18} strokeWidth={1.75} /></span>
      <span className={s.cellBody}>
        <span className={s.cellLabel}>{label}</span>
        {value && <span className={s.cellValue}>{value}</span>}
        <ChevronRight size={18} strokeWidth={1.75} className={s.chev} />
      </span>
    </button>
  );
}

export function SettingsPage({ cells }: { cells: { tone: string; icon: LucideIcon; label: string; value?: string }[][] }) {
  const theme = useStore((st) => st.theme);
  return (
    <div className={s.scroll}>
      <LargeTitle title="Settings" />
      <div className={s.group}>
        <button className={s.meCard} onClick={() => actions.openModal("profile")}>
          <img src={me.avatar} alt="" />
          <span><b>{me.name}</b><span>{me.email}</span></span>
          <ChevronRight size={18} strokeWidth={1.75} className={s.chev} />
        </button>
      </div>
      <div className={`${s.group} ${s.groupPad}`}>
        <span className={s.cellLabel}>Appearance</span>
        <div className={s.seg} role="tablist">
          {themes.map((t) => <button key={t.value} role="tab" aria-selected={theme === t.value} className={theme === t.value ? s.segOn : ""} onClick={() => actions.setTheme(t.value)}>{t.label}</button>)}
        </div>
      </div>
      {cells.map((group, i) => (
        <div key={i} className={s.group}>
          {group.map((c) => <Cell key={c.label} {...c} onClick={() => actions.openModal("settings")} />)}
        </div>
      ))}
    </div>
  );
}
