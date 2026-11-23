// Settings modal (spec §21): same frosted shell as Profile, six tabs with working local state.
// Every tab stays mounted (hidden when inactive) so toggles keep their values while switching tabs.
import { useState, type ReactElement } from "react";
import { Bell, Blocks, Palette, Shield, Sparkles, UserRound } from "lucide-react";
import { Shell, useToast, type Tab } from "../shared";
import { AccountTab, AiTab, AppearanceTab, AppsTab, NotificationsTab, PrivacyTab, type TabProps } from "./tabs";
import st from "./settings.module.css";

const tabs: (Tab & { heading: string; sub: string; Body: (p: TabProps) => ReactElement })[] = [
  { id: "account", label: "Account", icon: UserRound, heading: "Account", sub: "Your sign-in, security and regional preferences.", Body: AccountTab },
  { id: "appearance", label: "Appearance", icon: Palette, heading: "Appearance", sub: "Theme, text size and how your chats look.", Body: AppearanceTab },
  { id: "notifications", label: "Notifications", icon: Bell, heading: "Notifications", sub: "Choose what reaches you, and when.", Body: NotificationsTab },
  { id: "privacy", label: "Privacy", icon: Shield, heading: "Privacy", sub: "Control what others can see and what Messenger keeps.", Body: PrivacyTab },
  { id: "apps", label: "Connected Apps", icon: Blocks, heading: "Connected Apps", sub: "Services Messenger can read from or send to.", Body: AppsTab },
  { id: "ai", label: "AI Preferences", icon: Sparkles, heading: "AI Preferences", sub: "How Messenger AI searches, remembers and responds.", Body: AiTab },
];

export function SettingsModal({ onClose }: { onClose: () => void }) {
  const [active, setActive] = useState("account");
  const [toast, say] = useToast();
  const tab = tabs.find((t) => t.id === active) ?? tabs[0];

  return (
    <Shell title="Settings" tabs={tabs} active={tab.id} onTab={setActive} onClose={onClose}
      heading={tab.heading} subheading={tab.sub} toast={toast}>
      {tabs.map(({ id, Body }) => (
        <div key={id} className={st.pane} hidden={id !== tab.id}><Body say={say} /></div>
      ))}
    </Shell>
  );
}
