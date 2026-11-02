"use client";
// What each screen shows, shared by the desktop Shell and the phone MobileApp.
import { AssistantFrame } from "./assistant/AssistantFrame";
import { Home } from "./assistant/Home";
import { Onboarding } from "./onboarding/Onboarding";
import type { ScreenId } from "./screens";
import { useApp } from "./state";
import { ThreadList } from "./tasks/ThreadList";
import { ThreadView } from "./tasks/ThreadView";
import { ChatsView } from "./chats/ChatsView";
import { CommunityView } from "./community/CommunityView";
import { MeView } from "./me/MeView";
import { ServicesView } from "./services/ServicesView";
import { MapsView } from "./maps/MapsView";
import { DashboardView } from "./dashboard/DashboardView";

export function MainView({ screen }: { screen: ScreenId }) {
  const { mode, threadId, onboarded } = useApp();
  if (screen === "me") return <MeView />;
  if (screen === "chats") return <ChatsView />;
  if (screen === "services") return <ServicesView />;
  if (screen === "maps") return <MapsView />;
  if (screen === "dashboard") return <DashboardView />;
  if (onboarded === null) return null;
  if (!onboarded && !threadId && mode === "assistant") return <AssistantFrame haze><Onboarding /></AssistantFrame>;
  if (threadId) return <ThreadView id={threadId} />;
  if (mode === "community") return <AssistantFrame><CommunityView /></AssistantFrame>;
  return <AssistantFrame haze><Home /></AssistantFrame>;
}

export function SidebarView() {
  return <ThreadList />;
}
