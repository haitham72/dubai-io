"use client";
import { useEffect, useState, type ReactNode } from "react";
import { DynamicIsland } from "./DynamicIsland";
import s from "./mobile.module.css";

const W = 430, H = 932;

/** `?device`: the phone layout inside an iPhone-style frame, scaled to fit the window. */
export function DeviceFrame({ children, island }: { children: ReactNode; island?: ReactNode }) {
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const fit = () => setScale(Math.min(1, (window.innerHeight - 32) / (H + 24), (window.innerWidth - 16) / (W + 24)));
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);
  return (
    <div className={s.stage}>
      <div className={s.bezel} data-testid="device-frame" style={{ zoom: scale }}>
        <div className={s.screen} style={{ width: W, height: H }}>
          <div className={s.statusBar}><span>9:41</span><span /></div>
          <DynamicIsland>{island}</DynamicIsland>
          <div className={s.screenBody}>{children}</div>
          <div className={s.homeBar} />
        </div>
      </div>
    </div>
  );
}
