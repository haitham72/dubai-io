import { useEffect, useState, type CSSProperties } from "react";
import {
  DEMO_ONBOARDING,
  LIFE_THEMES,
  type DesktopBridge,
  type OnboardingStatus,
  type SyncSource,
} from "../ipc/bridge";
import { flat, theme } from "../theme";

const CONSENTED: SyncSource[] = ["chrome", "edge", "claude-code", "codex"];

export function AnalyticsPanel({
  bridge,
  owner = "karim",
  apiBaseUrl = "http://127.0.0.1:8000",
  fetcher,
}: {
  bridge: DesktopBridge;
  owner?: string;
  apiBaseUrl?: string;
  fetcher?: (url: string) => Promise<OnboardingStatus>;
}) {
  const [data, setData] = useState<OnboardingStatus>(DEMO_ONBOARDING);
  const [offline, setOffline] = useState(true);
  const [pulling, setPulling] = useState(false);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    const load = fetcher ?? ((url: string) => fetch(url).then((res) => {
      if (!res.ok) throw new Error(`onboarding-status ${res.status}`);
      return res.json() as Promise<OnboardingStatus>;
    }));
    load(`${apiBaseUrl}/v1/owners/${owner}/onboarding-status`)
      .then((body) => {
        if (!live) return;
        setData(body);
        setOffline(body.demo_data === true);
      })
      .catch(() => {
        if (!live) return;
        setData(DEMO_ONBOARDING);
        setOffline(true);
      });
    void bridge.syncStatus().then((status) => {
      if (!live) return;
      setPulling(status.enabledSources.length > 0 && status.syncOnFocus);
      setLastSyncAt(status.lastSyncAt);
    });
    return () => {
      live = false;
    };
  }, [apiBaseUrl, bridge, fetcher, owner]);

  async function togglePull() {
    const next = !pulling;
    const status = await bridge.syncConfigure({
      enabledSources: next ? CONSENTED : [],
      intervalMinutes: 60,
      syncOnFocus: next,
    });
    setPulling(next && status.enabledSources.length > 0);
    if (next) {
      const ran = await bridge.syncRun();
      setLastSyncAt(ran.lastSyncAt);
      setNotice(`Continuous pull is on. ${ran.enqueued} new day packets enqueued.`);
    } else {
      setNotice("Continuous pull is off. Disabled sources are not read.");
    }
  }

  const shield = data.analytics.privacy_shield;
  const saved = data.analytics.compute_saved;
  return (
    <section style={panel} data-testid="analytics-panel">
      <header style={row}>
        <h2 style={{ margin: 0, fontFamily: "Georgia, serif" }}>Analytics & what I know about you</h2>
        {offline ? <span style={pill}>Demo data</span> : null}
      </header>
      <p data-testid="completeness-jump">
        36% mobile Google login → {data.completeness_pct}% after PC Chrome/Edge (+18%) and AI sessions (+19%)
      </p>
      <div style={row}>
        <button type="button" data-testid="sync-toggle" aria-pressed={pulling} onClick={() => void togglePull()} style={flat}>
          Keep Pulling Consented Sources (Every 60m / On Focus)
        </button>
        <span data-testid="sync-state">{pulling ? "On · every 60m" : "Off"}</span>
        {lastSyncAt ? <span data-testid="last-sync">Last sync {lastSyncAt}</span> : null}
      </div>
      {notice ? <p data-testid="sync-notice">{notice}</p> : null}

      <h3>What your data says about you</h3>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {LIFE_THEMES.map((themeName) => {
          const stat = data.analytics.by_theme[themeName];
          const rising = stat?.rising_21d || data.analytics.rising_21d.includes(themeName);
          const slug = themeName.toLowerCase().replace(/[^a-z0-9]+/g, "-");
          return (
            <li key={themeName} data-testid={`theme-${slug}`} style={bar}>
              <span>{themeName}</span>
              <span>{stat?.facts ?? 0} facts</span>
              {rising ? <span data-testid={`rising-${slug}`}>+{stat?.delta ?? 0} rising_21d</span> : null}
            </li>
          );
        })}
      </ul>

      <h3>Cross-source mix</h3>
      <ul>
        {Object.entries(data.analytics.by_source).map(([source, counts]) => (
          <li key={source} data-testid={`source-${source}`}>{source}: {counts.records} records · {counts.facts} facts</li>
        ))}
      </ul>

      <h3>Known so far</h3>
      {Object.entries(data.known_so_far).map(([themeName, facts]) => (
        <div key={themeName}>
          <strong>{themeName}</strong>
          {facts.map((fact) => (
            <p key={fact.id}>
              {fact.text} · src: {fact.evidence.join(", ")} · as_of: {fact.as_of}
            </p>
          ))}
        </div>
      ))}

      <article style={panel} data-testid="privacy-shield">
        <h3>Rule-9 privacy shield</h3>
        <p>{shield.held_back_total} sensitive items held back</p>
        <ul>
          {Object.entries(shield.by_category).map(([category, count]) => (
            <li key={category}>{category}: {count}</li>
          ))}
        </ul>
      </article>

      <article style={panel} data-testid="compute-saved">
        <h3>Compute & cost saved</h3>
        <p>{saved.owner_hook_facts} owner_hook_facts · tokens_in {saved.tokens_in} · tokens_out {saved.tokens_out}</p>
        <p>processed on your Claude/Codex · $0 app cost</p>
      </article>
    </section>
  );
}

const panel: CSSProperties = { ...flat, background: theme.canvas, borderRadius: 16, padding: 16, marginBottom: 12 };
const row: CSSProperties = { display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", margin: "12px 0" };
const bar: CSSProperties = { ...flat, background: theme.surface, borderRadius: 12, padding: 8, marginBottom: 8, display: "flex", gap: 12 };
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
