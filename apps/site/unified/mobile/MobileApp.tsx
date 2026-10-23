"use client";
import { useState } from "react";
import { MainView } from "../views";
import { Placeholder } from "../ui";
import { useApp } from "../state";
import { TabBar, type Tab } from "./TabBar";
import s from "./mobile.module.css";

/** Phone layout (<= 820 px, and inside the ?device frame). Tabs: Home, Chat, Services, Feed + Ask. */
export function MobileApp() {
  const { setMode, setScreen } = useApp();
  const [tab, setTab] = useState<Tab>("home");

  const go = (t: Tab) => {
    setTab(t);
    if (t === "home") { setScreen("assistant"); setMode("assistant"); }
    if (t === "feed") { setScreen("assistant"); setMode("community"); }
  };
  const ask = () => {
    go("home");
    window.setTimeout(() => document.querySelector<HTMLTextAreaElement>("[data-testid=composer-input]")?.focus(), 0);
  };

  return (
    <div className={s.phone}>
      <div className={s.body}>
        {tab === "home" || tab === "feed" ? <MainView screen="assistant" />
          : tab === "chat" ? <Placeholder title="Chats" plan={3} />
          : <Placeholder title="Services" plan={4} />}
      </div>
      <TabBar tab={tab} onTab={go} onAsk={ask} />
    </div>
  );
}
