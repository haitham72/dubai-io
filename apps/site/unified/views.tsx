"use client";
// What each screen shows, shared by the desktop Shell and the phone MobileApp.
import { AssistantFrame } from "./assistant/AssistantFrame";
import { Home } from "./assistant/Home";
import { Onboarding } from "./onboarding/Onboarding";
import { PLAN_FOR, TITLE_FOR, type ScreenId } from "./screens";
import { useApp } from "./state";
import { ThreadList } from "./tasks/ThreadList";
import { ThreadView } from "./tasks/ThreadView";
import { ThemeToggle } from "./shell/Rail";
import { Placeholder } from "./ui";

export function MainView({ screen }: { screen: ScreenId }) {
  const { mode, threadId, onboarded } = useApp();
  if (screen === "me") return <div data-testid="me-screen"><Placeholder title="Me" plan={6} /><div style={{ padding: "0 24px" }}><ThemeToggle /></div></div>;
  if (screen !== "assistant") return <Placeholder title={TITLE_FOR[screen]} plan={PLAN_FOR[screen]} />;
  if (onboarded === null) return null;
  if (!onboarded && !threadId && mode === "assistant") return <AssistantFrame haze><Onboarding /></AssistantFrame>;
  if (threadId) return <ThreadView id={threadId} />;
  if (mode === "community") return <AssistantFrame><Placeholder title="Community" plan={3} /></AssistantFrame>;
  return <AssistantFrame haze><Home /></AssistantFrame>;
}

export function SidebarView() {
  return <ThreadList />;
}
