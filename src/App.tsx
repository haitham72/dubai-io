import { useEffect } from "react";
import { Analytics } from "@vercel/analytics/react";
import { Nav } from "./shell/Nav";
import { screens } from "./screens";
import { actions, useStore } from "./store";
import { ProfileModal, SettingsModal } from "./profile";
import { MobileApp } from "./mobile/MobileApp";
import { useIsMobile } from "./mobile/useIsMobile";
import { MacDesktop } from "./shell/MacDesktop";
import { CommandCard } from "./voice/CommandCard";
import { QuickCards } from "./quick/QuickCards";
import "./updates/persist";
import "./updates/diwan";
import s from "./shell/shell.module.css";

export default function App() {
  const screenId = useStore((st) => st.screen);
  const modal = useStore((st) => st.modal);
  const mobile = useIsMobile();
  const { Sidebar, Main } = screens[screenId];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && actions.closeModal();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (mobile) return (
    <>
      <MobileApp />
      <Analytics />
    </>
  );

  return (
    <MacDesktop>
      <div className={s.app}>
        <Nav />
        {Sidebar && (
          <aside className={s.sidebar} key={`side-${screenId}`}>
            <Sidebar />
          </aside>
        )}
        <main className={s.main} key={`main-${screenId}`}>
          <Main />
        </main>
        {modal === "profile" && <ProfileModal onClose={actions.closeModal} />}
        {modal === "settings" && <SettingsModal onClose={actions.closeModal} />}
        <QuickCards />
        <CommandCard />
      </div>
      <Analytics />
    </MacDesktop>
  );
}
