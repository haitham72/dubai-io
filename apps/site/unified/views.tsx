"use client";
// What each screen shows, shared by the desktop Shell and the phone MobileApp.
import { Home } from "./assistant/Home";
import { PLAN_FOR, TITLE_FOR, type ScreenId } from "./screens";
import { useApp } from "./state";
import { Placeholder } from "./ui";

export function MainView({ screen }: { screen: ScreenId }) {
  const { mode } = useApp();
  if (screen !== "assistant") return <Placeholder title={TITLE_FOR[screen]} plan={PLAN_FOR[screen]} />;
  if (mode === "community") return <Placeholder title="Community" plan={3} />;
  return <Home />;
}

export function SidebarView() {
  return null;
}
