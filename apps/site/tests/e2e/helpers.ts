import type { Page, Route } from "@playwright/test";

export type Json = Record<string, unknown>;

export const EMPTY_LANE = { tasks: [], has_more: false };
export const EMPTY_TODAY = {
  needs_you: EMPTY_LANE, running: EMPTY_LANE, scheduled: EMPTY_LANE, on_list: EMPTY_LANE, paused: EMPTY_LANE, completed: EMPTY_LANE,
  counts: { needs_you: 0, running: 0, on_list: 0, paused: 0 }, current_work: [], as_of: "2026-10-23T10:00:00+04:00",
};

export function lane(tasks: Json[]) {
  return { tasks, has_more: false };
}

export interface ApiMock {
  today?: Json;
  turn?: (route: Route) => Promise<void> | void;
  memory?: Record<string, string>;
  tasks?: Record<string, { task: Json; events: Json[] }>;
  onRequest?: (method: string, url: string, body: string | null) => void;
}

/** Hermetic API: every /api call is answered here, so e2e never depends on a running backend. */
export async function mockApi(page: Page, mock: ApiMock = {}) {
  const told: Record<string, { value: string }> = {};
  for (const [k, v] of Object.entries(mock.memory ?? {})) told[k] = { value: v };
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    mock.onRequest?.(req.method(), path, req.postData());
    const json = (body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/api/session") return json({ user_id: "u1", mode: "anonymous_lab_session" });
    if (path === "/api/today") return json(mock.today ?? EMPTY_TODAY);
    if (path === "/api/luna/turn") {
      if (mock.turn) return mock.turn(route);
      return json({ reply: "Hello from Luna", intent: "chat" });
    }
    if (path === "/api/session/memory" && req.method() === "GET") return json({ told });
    const put = path.match(/^\/api\/session\/memory\/(\w+)$/);
    if (put && req.method() === "PUT") {
      const value = JSON.parse(req.postData() ?? "{}").value as string;
      told[put[1]] = { value };
      return json({ fact: { key: put[1], value } });
    }
    const detail = path.match(/^\/api\/tasks\/([^/]+)(\/activity)?$/);
    if (detail) {
      const t = mock.tasks?.[detail[1]];
      if (!t) return json({ detail: "Not found" }, 404);
      return json(detail[2] ? { events: t.events, before_seq: null } : { task: t.task, linked_item: null, events: t.events, before_seq: null });
    }
    return json({ detail: "Not mocked" }, 404);
  });
}
