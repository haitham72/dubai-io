import { useState, type CSSProperties } from "react";
import type { DesktopBridge, SessionRow } from "../ipc/bridge";
import { AnalyticsPanel } from "./AnalyticsPanel";
import { BrowserImportPanel } from "./BrowserImportPanel";
import { SessionHistoryPanel } from "./SessionHistoryPanel";
import { SettingsPanel } from "./SettingsPanel";
import { flat, theme } from "../theme";

const TABS = ["Today", "Chat", "Quests", "Memory", "Analytics", "Sessions", "Local Import", "Settings"] as const;
type Tab = (typeof TABS)[number];

export function AppShell({ bridge, sessions }: { bridge: DesktopBridge; sessions: SessionRow[] }) {
  const [tab, setTab] = useState<Tab>("Today");
  return (
    <div style={{ background: theme.canvas, color: theme.ink, minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <header style={{ ...flat, borderLeft: "none", borderRight: "none", borderTop: "none", padding: 16, display: "flex", justifyContent: "space-between" }}>
        <strong style={{ fontFamily: "Georgia, serif", fontSize: 22 }}>Dubai-io</strong>
        <span style={pill}>Demo data</span>
      </header>
      <nav style={{ display: "flex", gap: 8, padding: 16, flexWrap: "wrap" }}>
        {TABS.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setTab(item)}
            data-testid={`tab-${item.toLowerCase().replace(" ", "-")}`}
            style={{
              ...flat,
              borderColor: tab === item ? theme.gold : theme.border,
              background: tab === item ? theme.goldSurface : theme.canvas,
              borderRadius: 999,
              padding: "8px 12px",
            }}
          >
            {item}
          </button>
        ))}
      </nav>
      <main style={{ padding: 16 }}>
        {tab === "Analytics" ? <AnalyticsPanel bridge={bridge} /> : null}
        {tab === "Sessions" ? <SessionHistoryPanel bridge={bridge} sessions={sessions} /> : null}
        {tab === "Local Import" ? <BrowserImportPanel bridge={bridge} /> : null}
        {tab === "Settings" ? <SettingsPanel bridge={bridge} /> : null}
        {tab !== "Analytics" && tab !== "Sessions" && tab !== "Local Import" && tab !== "Settings" ? (
          <section style={{ ...flat, background: theme.surface, borderRadius: 16, padding: 16 }}>
            <h2 style={{ fontFamily: "Georgia, serif" }}>{tab}</h2>
            <p>This pillar is a desktop placeholder. Fixture cards stay labelled.</p>
            <span style={pill}>Demo data</span>
          </section>
        ) : null}
      </main>
    </div>
  );
}

const pill: CSSProperties = {
  ...flat,
  borderColor: theme.goldBorder,
  background: theme.goldSurface,
  color: theme.gold,
  borderRadius: 999,
  padding: "2px 8px",
  fontSize: 12,
  fontWeight: 700,
};
