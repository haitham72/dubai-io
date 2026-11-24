export type AgentTool = "claude-code" | "codex";
export type BrowserKind = "chrome" | "edge" | "brave";

export interface SessionRow {
  id: string;
  tool: AgentTool;
  scope: "workspace" | "project";
  title: string;
  summary: string;
  cwd: string;
  at: string;
  demo: true;
}

export interface ResumeResult {
  argv: string[];
  cwd: string;
}

export interface HookStatus {
  running: boolean;
  model: string | null;
}

export interface TokenStatus {
  stored: boolean;
  masked: string | null;
}

export interface DesktopBridge {
  scanSessions(payload: { tool?: AgentTool; since?: string }): Promise<{ count: number }>;
  resumeCommand(payload: { agentTool: AgentTool; sessionId: string; cwd: string }): Promise<ResumeResult>;
  previewBrowser(payload: { browser: BrowserKind; profileName: string }): Promise<Record<string, number>>;
  importBrowser(payload: { browser: BrowserKind; profileName: string; consent: true }): Promise<{ imported: number }>;
  hookStatus(): Promise<HookStatus>;
  hookToggle(payload: { enabled: boolean; model?: string; url?: string; owner?: string }): Promise<HookStatus>;
  tokenStatus(): Promise<TokenStatus>;
}

export const DEMO_SESSIONS: SessionRow[] = [
  {
    id: "sess-typography",
    tool: "claude-code",
    scope: "project",
    title: "Interface typography notes",
    summary: "Karim asked for a short book on interface typography. Paths and secrets were removed.",
    cwd: "C:\\demo\\raseef",
    at: "2026-11-17",
    demo: true,
  },
  {
    id: "sess-shorebirds",
    tool: "codex",
    scope: "workspace",
    title: "Coastal birds reading list",
    summary: "Start with a guide to shorebirds. No credentials were kept.",
    cwd: "C:\\demo\\notes",
    at: "2026-11-17",
    demo: true,
  },
  {
    id: "sess-layout",
    tool: "claude-code",
    scope: "workspace",
    title: "Morning layout pass",
    summary: "Karim wanted the report sections less dense.",
    cwd: "C:\\demo\\raseef",
    at: "2026-11-18",
    demo: true,
  },
];

const DEMO_COUNTS: Record<string, number> = {
  "research.example": 3,
  "docs.example": 2,
};

export function demoBridge(): DesktopBridge {
  return {
    async scanSessions() {
      return { count: DEMO_SESSIONS.length };
    },
    async resumeCommand(payload) {
      const argv =
        payload.agentTool === "claude-code"
          ? ["claude", "--resume", payload.sessionId]
          : ["codex", "resume", payload.sessionId];
      return { argv, cwd: payload.cwd };
    },
    async previewBrowser() {
      return { ...DEMO_COUNTS };
    },
    async importBrowser(payload) {
      if (payload.consent !== true) throw new Error("browser import requires explicit consent");
      return { imported: 0 };
    },
    async hookStatus() {
      return { running: false, model: null };
    },
    async hookToggle(payload) {
      if (payload.enabled && !payload.model?.trim()) throw new Error("model is required");
      return { running: payload.enabled, model: payload.enabled ? payload.model ?? null : null };
    },
    async tokenStatus() {
      return { stored: false, masked: null };
    },
  };
}

export function resolveBridge(win: Window = window): DesktopBridge {
  const native = (win as Window & { dubaiDesktop?: DesktopBridge }).dubaiDesktop;
  return native ?? demoBridge();
}
