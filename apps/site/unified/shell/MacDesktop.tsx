"use client";
// `?desktop`: the app as a window on a Mac-style desktop (menu bar, traffic lights, Dock), ported from Mirsal and slimmed:
// red closes (reopen from the Dock), yellow minimizes to the Dock, green fills the screen. No drag/resize in plan 1.
import { useEffect, useState, type ReactNode } from "react";
import { BatteryFull, Search, Wifi } from "lucide-react";
import s from "./mac.module.css";

type WindowState = "normal" | "zoomed" | "minimized" | "closed";
const MENUS = ["File", "Edit", "View", "Window", "Help"];

function Clock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = window.setInterval(() => setNow(new Date()), 15_000);
    return () => window.clearInterval(id);
  }, []);
  if (!now) return null;
  return <span>{now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}&nbsp;&nbsp;{now.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}</span>;
}

export function MacDesktop({ children }: { children: ReactNode }) {
  const [win, setWin] = useState<WindowState>("normal");
  const reopen = () => setWin((w) => (w === "zoomed" ? w : "normal"));
  return (
    <div className={s.desktop}>
      <header className={s.menubar}>
        <span className={s.menuApp}><i className={s.menuLogo}>D</i>Dubai-io</span>
        {MENUS.map((m) => <span key={m} className={s.menuItem}>{m}</span>)}
        <span className={s.menuRight}>
          <BatteryFull size={18} strokeWidth={1.75} /><Wifi size={16} strokeWidth={2} /><Search size={15} strokeWidth={2} /><Clock />
        </span>
      </header>

      <main className={s.stage}>
        {win !== "closed" && (
          <section
            data-testid="mac-window"
            className={`${s.window} ${win === "zoomed" ? s.zoomed : ""} ${win === "minimized" ? s.minimized : ""}`}
            aria-label="Dubai-io window"
          >
            <div className={s.titlebar} onDoubleClick={() => setWin(win === "zoomed" ? "normal" : "zoomed")}>
              <span className={s.lights}>
                <button className={s.red} aria-label="Close" onClick={() => setWin("closed")}><i>×</i></button>
                <button className={s.yellow} aria-label="Minimize" onClick={() => setWin("minimized")}><i>−</i></button>
                <button className={s.green} aria-label={win === "zoomed" ? "Exit full screen" : "Enter full screen"} onClick={() => setWin(win === "zoomed" ? "normal" : "zoomed")}><i>{win === "zoomed" ? "↙" : "↗"}</i></button>
              </span>
              <span className={s.title}>Dubai-io</span>
            </div>
            <div className={s.content}>{children}</div>
          </section>
        )}
      </main>

      <nav className={`${s.dock} ${win === "zoomed" ? s.dockHidden : ""}`} aria-label="Dock">
        <button className={s.dockApp} aria-label="Dubai-io" onClick={reopen}>
          <span className={s.dockLogo}>D</span>
          {win !== "closed" && <i className={s.running} />}
        </button>
      </nav>
    </div>
  );
}
