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

export type SyncSource = "chrome" | "edge" | "claude-code" | "codex";

export interface SyncStatus {
  enabledSources: SyncSource[];
  intervalMinutes: 60;
  syncOnFocus: boolean;
  lastSyncAt: string | null;
  enqueued: number;
}

export interface ThemeStat {
  facts: number;
  recent_21d: number;
  baseline_21d: number;
  delta: number;
  rising_21d: boolean;
}

export interface OnboardingStatus {
  owner: string;
  completeness_pct: number;
  breakdown: Record<string, number>;
  sources_present: string[];
  next_recommended_action: string;
  known_so_far: Record<string, { id: string; text: string; evidence: string[]; provenance: string; as_of: string }[]>;
  analytics: {
    by_source: Record<string, { records: number; facts: number }>;
    by_theme: Record<string, ThemeStat>;
    rising_21d: string[];
    privacy_shield: { held_back_total: number; by_category: Record<string, number> };
    compute_saved: {
      owner_hook_facts: number;
      tokens_in: number;
      tokens_out: number;
      demo_cost_saved_usd: number;
    };
  };
  provenance: string;
  as_of: string;
  demo_data: boolean;
}

export const LIFE_THEMES = [
  "Career",
  "Learning",
  "Projects",
  "People & family",
  "Events",
  "Home & money",
  "Travel",
] as const;

function emptyTheme(): ThemeStat {
  return { facts: 0, recent_21d: 0, baseline_21d: 0, delta: 0, rising_21d: false };
}

export const DEMO_ONBOARDING: OnboardingStatus = {
  owner: "karim",
  completeness_pct: 73,
  breakdown: {
    gmail: 14,
    calendar: 10,
    youtube_api: 12,
    whatsapp: 0,
    youtube_history: 0,
    browser: 18,
    agent_sessions: 19,
  },
  sources_present: ["gmail", "calendar", "youtube_api", "browser", "agent_sessions"],
  next_recommended_action: "add_whatsapp_or_youtube_history",
  known_so_far: {
    Career: [
      {
        id: "f-demo-career",
        text: "A product-role search is open in Dubai",
        evidence: ["g1"],
        provenance: "demo_fixture",
        as_of: "2026-11-18",
      },
    ],
  },
  analytics: {
    by_source: {
      gmail: { records: 2, facts: 1 },
      "youtube:interests": { records: 1, facts: 1 },
      whatsapp: { records: 0, facts: 0 },
      browser: { records: 4, facts: 1 },
      "agent:claude-code": { records: 1, facts: 0 },
      "agent:codex": { records: 1, facts: 0 },
      "ai:chatgpt": { records: 0, facts: 0 },
      "takeout:*": { records: 0, facts: 0 },
    },
    by_theme: {
      Career: { facts: 2, recent_21d: 2, baseline_21d: 1, delta: 1, rising_21d: true },
      Learning: emptyTheme(),
      Projects: emptyTheme(),
      "People & family": emptyTheme(),
      Events: emptyTheme(),
      "Home & money": emptyTheme(),
      Travel: emptyTheme(),
    },
    rising_21d: ["Career"],
    privacy_shield: { held_back_total: 3, by_category: { health: 2, credential: 1 } },
    compute_saved: { owner_hook_facts: 1, tokens_in: 1200, tokens_out: 400, demo_cost_saved_usd: 0 },
  },
  provenance: "demo_fixture",
  as_of: "2026-11-24",
  demo_data: true,
};

export interface AuthStatus {
  signedIn: boolean;
  userId: string | null;
  displayName: string | null;
  email: string | null;
  hasDeviceToken: boolean;
}

export interface DesktopBridge {
  authStatus(): Promise<AuthStatus>;
  authSignIn(payload?: { apiBaseUrl?: string }): Promise<AuthStatus>;
  authSignOut(): Promise<AuthStatus>;
  scanSessions(payload: { tool?: AgentTool; since?: string }): Promise<{ count: number }>;
  resumeCommand(payload: { agentTool: AgentTool; sessionId: string; cwd: string }): Promise<ResumeResult>;
  previewBrowser(payload: { browser: BrowserKind; profileName: string }): Promise<Record<string, number>>;
  importBrowser(payload: { browser: BrowserKind; profileName: string; consent: true }): Promise<{ imported: number }>;
  hookStatus(): Promise<HookStatus>;
  hookToggle(payload: { enabled: boolean; model?: string; url?: string; owner?: string }): Promise<HookStatus>;
  tokenStatus(): Promise<TokenStatus>;
  syncStatus(): Promise<SyncStatus>;
  syncConfigure(payload: { enabledSources: SyncSource[]; intervalMinutes?: 60; syncOnFocus: boolean }): Promise<SyncStatus>;
  syncRun(): Promise<SyncStatus>;
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

const SIGNED_OUT: AuthStatus = { signedIn: false, userId: null, displayName: null, email: null, hasDeviceToken: false };

export function demoBridge(): DesktopBridge {
  return {
    async authStatus() {
      return { ...SIGNED_OUT };
    },
    async authSignIn() {
      throw new Error("Sign-in is available in the desktop app, not in this preview.");
    },
    async authSignOut() {
      return { ...SIGNED_OUT };
    },
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
    async syncStatus() {
      return { enabledSources: [], intervalMinutes: 60 as const, syncOnFocus: false, lastSyncAt: null, enqueued: 0 };
    },
    async syncConfigure(payload) {
      return {
        enabledSources: payload.enabledSources,
        intervalMinutes: 60 as const,
        syncOnFocus: payload.syncOnFocus,
        lastSyncAt: null,
        enqueued: 0,
      };
    },
    async syncRun() {
      return { enabledSources: [], intervalMinutes: 60 as const, syncOnFocus: false, lastSyncAt: null, enqueued: 0 };
    },
  };
}

export function resolveBridge(win: Window = window): DesktopBridge {
  const native = (win as Window & { dubaiDesktop?: DesktopBridge }).dubaiDesktop;
  return native ?? demoBridge();
}
