import { useState, type CSSProperties } from "react";
import type { DesktopBridge } from "../ipc/bridge";
import { flat, theme } from "../theme";

const MODELS = ["claude-sonnet-4-5", "claude-haiku-4-5", "o3-mini"] as const;

export function SettingsPanel({ bridge }: { bridge: DesktopBridge }) {
  const [model, setModel] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [status, setStatus] = useState("Hook is off.");
  const [error, setError] = useState<string | null>(null);
  const [sources, setSources] = useState({ chrome: false, claude: false, codex: false });
  const [forgetArmed, setForgetArmed] = useState(false);
  const [forgot, setForgot] = useState<string | null>(null);

  async function toggleHook() {
    const next = !enabled;
    if (next && !model.trim()) {
      setError("Choose a model before turning on your own Claude or Codex.");
      return;
    }
    setError(null);
    const result = await bridge.hookToggle({ enabled: next, model: model || undefined, owner: "karim" });
    setEnabled(result.running);
    setStatus(result.running ? `Processing on ${result.model} ($0 app cost).` : "Hook is off.");
  }

  return (
    <section style={panel} data-testid="settings-panel">
      <h2 style={{ marginTop: 0, fontFamily: "Georgia, serif" }}>Settings</h2>
      <p>Owner-device token stays in the main process. This screen shows only a mask.</p>
      <p data-testid="token-mask">Token: not shown</p>
      <label>
        Model{" "}
        <select value={model} onChange={(event) => setModel(event.target.value)} data-testid="model-picker">
          <option value="">Select a model</option>
          {MODELS.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
      </label>
      <div>
        <button type="button" onClick={() => void toggleHook()} data-testid="hook-toggle" aria-pressed={enabled}>
          Process on your own Claude/Codex ($0 app cost): {enabled ? "On" : "Off"}
        </button>
      </div>
      <p data-testid="hook-status">{status}</p>
      {error ? <p data-testid="hook-error">{error}</p> : null}
      <h3>Source consent</h3>
      <p>Every source stays off until you opt in.</p>
      {(Object.keys(sources) as Array<keyof typeof sources>).map((source) => (
        <label key={source} style={{ display: "block" }}>
          <input
            type="checkbox"
            checked={sources[source]}
            onChange={(event) => setSources((current) => ({ ...current, [source]: event.target.checked }))}
            data-testid={`consent-${source}`}
          />
          {source}
        </label>
      ))}
      <h3>Forget by source</h3>
      <button type="button" onClick={() => setForgetArmed(true)} data-testid="forget-arm">
        Forget browser source
      </button>
      {forgetArmed ? (
        <button
          type="button"
          onClick={() => {
            setForgot("Browser source marked for forget. No records were deleted in this preview.");
            setForgetArmed(false);
          }}
          data-testid="forget-confirm"
        >
          Confirm forget
        </button>
      ) : null}
      {forgot ? <p>{forgot}</p> : null}
    </section>
  );
}

const panel: CSSProperties = { ...flat, background: theme.canvas, padding: 16, borderRadius: 16 };
