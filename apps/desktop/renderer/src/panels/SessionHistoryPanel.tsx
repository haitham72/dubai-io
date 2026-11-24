import { useMemo, useState, type CSSProperties } from "react";
import type { AgentTool, DesktopBridge, SessionRow } from "../ipc/bridge";
import { flat, theme } from "../theme";

const PAGE_CAP = 200;

export function SessionHistoryPanel({
  bridge,
  sessions,
  pageSize = PAGE_CAP,
}: {
  bridge: DesktopBridge;
  sessions: SessionRow[];
  pageSize?: number;
}) {
  const size = Math.min(pageSize, PAGE_CAP);
  const [consent, setConsent] = useState(false);
  const [scope, setScope] = useState<"workspace" | "project" | "all">("all");
  const [agent, setAgent] = useState<"all" | AgentTool>("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [sendReady, setSendReady] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [open, setOpen] = useState<SessionRow | null>(null);
  const [copied, setCopied] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return sessions.filter((row) => {
      if (scope !== "all" && row.scope !== scope) return false;
      if (agent !== "all" && row.tool !== agent) return false;
      if (!q) return true;
      return `${row.title} ${row.summary}`.toLowerCase().includes(q);
    });
  }, [sessions, scope, agent, query]);

  const pages = Math.max(1, Math.ceil(filtered.length / size));
  const safePage = Math.min(page, pages - 1);
  const visible = filtered.slice(safePage * size, safePage * size + size);

  async function scan() {
    if (!consent) return;
    const tool = agent === "all" ? undefined : agent;
    const result = await bridge.scanSessions({ tool });
    setNotice(`Scanned ${result.count} sessions after consent. Nothing was sent yet.`);
  }

  async function copyResume(row: SessionRow) {
    const result = await bridge.resumeCommand({
      agentTool: row.tool,
      sessionId: row.id,
      cwd: row.cwd,
    });
    const text = result.argv.join(" ");
    await navigator.clipboard.writeText(text);
    setCopied(text);
  }

  async function sendSelected() {
    if (!consent || !sendReady || selected.length === 0) return;
    await bridge.scanSessions({ tool: agent === "all" ? undefined : agent });
    setNotice(`Sent ${selected.length} selected sessions to memory.`);
  }

  return (
    <section style={panel} data-testid="session-history">
      <header style={row}>
        <h2 style={title}>Session history</h2>
        <span style={pill}>Demo data</span>
      </header>
      <p style={muted}>Redacted summaries only. Scanning waits for a per-source opt-in.</p>
      <label style={row}>
        <input
          type="checkbox"
          checked={consent}
          onChange={(event) => setConsent(event.target.checked)}
          data-testid="session-consent"
        />
        Allow reading Claude Code and Codex session summaries
      </label>
      <div style={row}>
        <label>
          Scope{" "}
          <select value={scope} onChange={(event) => { setScope(event.target.value as typeof scope); setPage(0); }} data-testid="scope-filter">
            <option value="workspace">Workspace</option>
            <option value="project">Project</option>
            <option value="all">All</option>
          </select>
        </label>
        <label>
          Agent{" "}
          <select value={agent} onChange={(event) => { setAgent(event.target.value as typeof agent); setPage(0); }} data-testid="agent-filter">
            <option value="all">All</option>
            <option value="claude-code">Claude Code</option>
            <option value="codex">Codex</option>
          </select>
        </label>
        <input
          value={query}
          onChange={(event) => { setQuery(event.target.value); setPage(0); }}
          placeholder="Search redacted summaries"
          data-testid="session-search"
          style={input}
        />
        <button type="button" disabled={!consent} onClick={() => void scan()} data-testid="scan-sessions">
          Scan sessions
        </button>
      </div>
      <ul style={list}>
        {visible.map((session) => (
          <li key={session.id} style={card} data-testid={`session-${session.id}`}>
            <label>
              <input
                type="checkbox"
                checked={selected.includes(session.id)}
                onChange={(event) => {
                  setSelected((current) =>
                    event.target.checked ? [...current, session.id] : current.filter((id) => id !== session.id),
                  );
                }}
              />{" "}
              {session.title}
            </label>
            <div style={muted}>{session.tool} · {session.scope} · {session.at}</div>
            <button type="button" onClick={() => setOpen(session)}>Open log</button>
            <button type="button" onClick={() => void copyResume(session)} data-testid={`copy-${session.id}`}>
              Copy Resume Command
            </button>
          </li>
        ))}
      </ul>
      <div style={row}>
        <button type="button" disabled={safePage === 0} onClick={() => setPage((value) => Math.max(0, value - 1))} data-testid="page-prev">
          Previous
        </button>
        <span data-testid="page-label">Page {safePage + 1} of {pages} · {visible.length} shown · cap {PAGE_CAP}</span>
        <button type="button" disabled={safePage >= pages - 1} onClick={() => setPage((value) => value + 1)} data-testid="page-next">
          Next
        </button>
      </div>
      <label style={row}>
        <input type="checkbox" checked={sendReady} onChange={(event) => setSendReady(event.target.checked)} data-testid="send-confirm" />
        I confirm sending {selected.length} selected sessions to memory
      </label>
      <button type="button" disabled={!consent || !sendReady || selected.length === 0} onClick={() => void sendSelected()} data-testid="send-selected">
        Send selected to memory
      </button>
      {copied ? <p data-testid="copied-command">{copied}</p> : null}
      {notice ? <p data-testid="session-notice">{notice}</p> : null}
      {open ? (
        <div role="dialog" style={card} data-testid="log-preview">
          <strong>{open.title}</strong>
          <p>{open.summary}</p>
          <p style={muted}>File path is not shown. This text is redacted.</p>
          <button type="button" onClick={() => setOpen(null)}>Close</button>
        </div>
      ) : null}
    </section>
  );
}

const panel: CSSProperties = { ...flat, background: theme.canvas, padding: 16, borderRadius: 16 };
const card: CSSProperties = { ...flat, background: theme.surface, padding: 12, borderRadius: 12, marginBottom: 8 };
const title: CSSProperties = { margin: 0, fontFamily: "Georgia, serif" };
const muted: CSSProperties = { color: theme.muted, fontSize: 13 };
const row: CSSProperties = { display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", margin: "12px 0" };
const list: CSSProperties = { listStyle: "none", padding: 0 };
const input: CSSProperties = { ...flat, background: theme.canvas, borderRadius: 8, padding: "6px 8px" };
const pill: CSSProperties = { ...flat, borderColor: theme.goldBorder, background: theme.goldSurface, color: theme.gold, borderRadius: 999, padding: "2px 8px", fontSize: 12, fontWeight: 700 };
