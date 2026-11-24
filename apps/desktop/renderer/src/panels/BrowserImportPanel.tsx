import { useState, type CSSProperties } from "react";
import type { BrowserKind, DesktopBridge } from "../ipc/bridge";
import { flat, theme } from "../theme";

export function BrowserImportPanel({ bridge }: { bridge: DesktopBridge }) {
  const [browser, setBrowser] = useState<BrowserKind>("chrome");
  const [profileName, setProfileName] = useState("Default");
  const [counts, setCounts] = useState<Record<string, number> | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [imported, setImported] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function preview() {
    setError(null);
    setImported(null);
    setConfirmed(false);
    const next = await bridge.previewBrowser({ browser, profileName });
    setCounts(next);
  }

  async function runImport() {
    if (!counts || !confirmed) return;
    try {
      const result = await bridge.importBrowser({ browser, profileName, consent: true });
      setImported(result.imported);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import was not confirmed");
    }
  }

  return (
    <section style={panel} data-testid="browser-import">
      <header style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <h2 style={{ margin: 0, fontFamily: "Georgia, serif" }}>Import Chrome history</h2>
        <span style={pill}>Demo data</span>
      </header>
      <p style={disclaimer} data-testid="history-disclaimer">
        History & Bookmarks only — Cookies, Passwords & Autofill are NEVER touched
      </p>
      <p style={{ color: theme.muted }}>
        Banking, health, and government portals are excluded by the default denylist. Preview writes zero records.
      </p>
      <label>
        Browser{" "}
        <select value={browser} onChange={(event) => setBrowser(event.target.value as BrowserKind)} data-testid="browser-kind">
          <option value="chrome">Chrome</option>
          <option value="edge">Edge</option>
          <option value="brave">Brave</option>
        </select>
      </label>
      <label style={{ marginLeft: 12 }}>
        Profile{" "}
        <input value={profileName} onChange={(event) => setProfileName(event.target.value)} data-testid="profile-name" style={input} />
      </label>
      <div style={{ marginTop: 12 }}>
        <button type="button" onClick={() => void preview()} data-testid="preview-history">
          Preview domain counts
        </button>
      </div>
      {counts ? (
        <ul data-testid="domain-counts">
          {Object.entries(counts).map(([domain, visits]) => (
            <li key={domain}>{domain}: {visits}</li>
          ))}
        </ul>
      ) : (
        <p>No preview yet. Import stays off until you preview and confirm.</p>
      )}
      <label>
        <input
          type="checkbox"
          checked={confirmed}
          disabled={!counts}
          onChange={(event) => setConfirmed(event.target.checked)}
          data-testid="import-confirm"
        />
        I confirm importing these domain counts
      </label>
      <button type="button" disabled={!counts || !confirmed} onClick={() => void runImport()} data-testid="import-history">
        Import history
      </button>
      {imported !== null ? <p data-testid="import-result">Import requested. Records created: {imported}.</p> : null}
      {error ? <p>{error}</p> : null}
    </section>
  );
}

const panel: CSSProperties = { ...flat, background: theme.canvas, padding: 16, borderRadius: 16 };
const disclaimer: CSSProperties = { ...flat, borderColor: theme.goldBorder, background: theme.goldSurface, padding: 12, borderRadius: 12 };
const pill: CSSProperties = { ...flat, borderColor: theme.goldBorder, background: theme.goldSurface, color: theme.gold, borderRadius: 999, padding: "2px 8px", fontSize: 12, fontWeight: 700 };
const input: CSSProperties = { ...flat, borderRadius: 8, padding: "6px 8px" };
