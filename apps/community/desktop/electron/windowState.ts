import fs from "node:fs";
import path from "node:path";

export interface WindowBoundsState {
  width: number;
  height: number;
  x?: number;
  y?: number;
  isMaximized?: boolean;
}

export const DEFAULT_WINDOW_STATE: WindowBoundsState = {
  width: 1280,
  height: 840,
  isMaximized: false,
};

const MIN_WIDTH = 640;
const MIN_HEIGHT = 480;

export function parseWindowState(raw: string): WindowBoundsState {
  try {
    const parsed = JSON.parse(raw) as Partial<WindowBoundsState>;
    const width =
      typeof parsed.width === "number" && Number.isFinite(parsed.width)
        ? Math.max(MIN_WIDTH, Math.round(parsed.width))
        : DEFAULT_WINDOW_STATE.width;
    const height =
      typeof parsed.height === "number" && Number.isFinite(parsed.height)
        ? Math.max(MIN_HEIGHT, Math.round(parsed.height))
        : DEFAULT_WINDOW_STATE.height;

    const state: WindowBoundsState = {
      width,
      height,
      isMaximized: Boolean(parsed.isMaximized),
    };

    if (typeof parsed.x === "number" && Number.isFinite(parsed.x)) {
      state.x = Math.round(parsed.x);
    }
    if (typeof parsed.y === "number" && Number.isFinite(parsed.y)) {
      state.y = Math.round(parsed.y);
    }
    return state;
  } catch {
    return { ...DEFAULT_WINDOW_STATE };
  }
}

export function loadWindowState(userDataDir: string): WindowBoundsState {
  const filePath = path.join(userDataDir, "window-state.json");
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    return parseWindowState(raw);
  } catch {
    return { ...DEFAULT_WINDOW_STATE };
  }
}

export function saveWindowState(
  userDataDir: string,
  state: WindowBoundsState,
): void {
  const filePath = path.join(userDataDir, "window-state.json");
  try {
    fs.mkdirSync(userDataDir, { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(state, null, 2), "utf8");
  } catch {
    // Non-fatal: window bounds persistence should never crash app exit.
  }
}
