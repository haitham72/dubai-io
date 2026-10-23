"use client";
import "./tokens.css";
import { useEffect, useState } from "react";
import { presentation, type Presentation } from "./presentation";
import { AppProvider, useApp } from "./state";
import { Shell } from "./shell/Shell";
import { MacDesktop } from "./shell/MacDesktop";
import { MobileApp } from "./mobile/MobileApp";
import { DeviceFrame } from "./mobile/DeviceFrame";
import { useIsMobile } from "./mobile/useIsMobile";
import { MainView, SidebarView } from "./views";

function Layout({ mode }: { mode: Presentation }) {
  const { screen } = useApp();
  const mobile = useIsMobile();
  const desktopLayout = <Shell screen={screen} sidebar={<SidebarView />} main={<MainView screen={screen} />} />;

  if (mode === "device") return <DeviceFrame><MobileApp /></DeviceFrame>;
  if (mode === "desktop") return <MacDesktop>{desktopLayout}</MacDesktop>;
  return <div style={{ height: "100vh" }}>{mobile ? <MobileApp /> : desktopLayout}</div>;
}

export default function App() {
  const [mode, setMode] = useState<Presentation | null>(null);
  useEffect(() => setMode(presentation(window.location.search)), []);
  if (!mode) return null;
  return (
    <AppProvider>
      <Layout mode={mode} />
    </AppProvider>
  );
}
