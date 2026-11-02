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
  const told: { key: string; value: string }[] = Object.entries(mock.memory ?? {}).map(([key, value]) => ({ key, value }));
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
      const i = told.findIndex((f) => f.key === put[1]);
      if (i >= 0) told[i] = { key: put[1], value }; else told.push({ key: put[1], value });
      return json({ fact: { key: put[1], value } });
    }
    const detail = path.match(/^\/api\/tasks\/([^/]+)(\/activity)?$/);
    if (detail) {
      const t = mock.tasks?.[detail[1]];
      if (!t) return json({ detail: "Not found" }, 404);
      return json(detail[2] ? { events: t.events, before_seq: null } : { task: t.task, linked_item: null, events: t.events, before_seq: null });
    }
    if (path === "/api/communities") {
      return json({
        communities: [
          { id: "marina-foodies", name: "Marina Foodies", about: "Neighbour eats", members: 1200, joined: false, provenance: "demo_fixture" },
        ],
      });
    }
    if (path === "/api/feed") {
      return json({
        posts: [
          {
            id: "p1",
            text: "Best way from DXB Terminal 1 to Dubai Marina at 1am?\nLanding late — reliable options?",
            community: { id: "dubai", name: "Dubai Community", joined: false },
            author: { name: "Yusuf Demir" },
            created_at: "2026-10-23T07:00:00+00:00",
            provenance: "demo_fixture",
            comments: 2,
            score: 24,
          },
        ],
        stories: [],
      });
    }
    if (path === "/api/chats") return json({ threads: [], unread: 0, archived_count: 0 });
    if (path === "/api/places/search" && req.method() === "POST") {
      const body = JSON.parse(req.postData() ?? "{}") as { query?: string };
      const q = (body.query || "").toLowerCase();
      if (q.includes("school") || q.includes("british") || q.includes("khda")) {
        return json({
          places: [
            {
              id: "mock-school-1",
              name: "Arcadia British School",
              rating: 4.4,
              lat: 25.04,
              lng: 55.20,
              short_address: "Jumeirah Village Triangle",
              website: "https://arcadia.sch.ae/",
              maps_url: "https://maps.google.com/?q=Arcadia+British+School",
              provenance: "provider_confirmed",
            },
            {
              id: "mock-school-2",
              name: "Dubai British School Jumeirah Park",
              rating: 4.1,
              lat: 25.05,
              lng: 55.16,
              short_address: "Jumeirah Park",
              website: "https://www.dubaibritishfs.ae/",
              maps_url: "https://maps.google.com/?q=Dubai+British+School",
              provenance: "provider_confirmed",
            },
          ],
          attribution: "Google",
          as_of: "2026-11-02T07:00:00+00:00",
          cache: "none",
        });
      }
      if (q.includes("gym") || q.includes("fitness")) {
        return json({
          places: [
            {
              id: "mock-gym-wellfit",
              name: "Wellfit Marina",
              rating: 4.6,
              ratings: 210,
              lat: 25.0805,
              lng: 55.1403,
              short_address: "Dubai Marina",
              open_now: true,
              website: "https://www.wellfit.ae/",
              maps_url: "https://maps.google.com/?q=Wellfit+Marina",
              photo: "places/mockgym/photos/abc",
              photo_by: ["Google contributor"],
              provenance: "provider_confirmed",
            },
            {
              id: "mock-gym-1",
              name: "Fitness First Dubai Marina Gate",
              rating: 4.4,
              ratings: 120,
              lat: 25.081,
              lng: 55.141,
              short_address: "Marina Gate",
              open_now: true,
              website: "https://uae.fitnessfirstme.com/clubs/dubai/marina-gate-dubai",
              maps_url: "https://maps.google.com/?q=Fitness+First+Marina",
              photo: "places/mockgym/photos/abc",
              photo_by: ["Google contributor"],
              provenance: "provider_confirmed",
            },
          ],
          attribution: "Google",
          as_of: "2026-11-02T07:00:00+00:00",
          cache: "none",
        });
      }
      return json({
        places: [
            {
              id: "mock-cafe-1",
              name: "Starbucks Dubai Marina",
              rating: 4.2,
              lat: 25.081,
              lng: 55.142,
              short_address: "Marina Walk",
              website: "https://www.starbucks.ae/",
              maps_url: "https://maps.google.com/?q=Starbucks+Marina",
              photo: "places/mockcafe/photos/def",
              photo_by: ["Google contributor"],
              provenance: "provider_confirmed",
            },
            {
              id: "mock-cafe-2",
              name: "Costa Coffee Marina Walk",
              rating: 4.1,
              lat: 25.0808,
              lng: 55.1415,
              short_address: "Marina Walk",
              website: "https://www.costacoffee.ae/",
              maps_url: "https://maps.google.com/?q=Costa+Marina",
              photo: "places/mockcafe/photos/ghi",
              photo_by: ["Google contributor"],
              provenance: "provider_confirmed",
            },
        ],
        attribution: "Google",
        as_of: "2026-11-02T07:00:00+00:00",
        cache: "none",
      });
    }
    if (path === "/api/maps/config") {
      return json({ detail: "Interactive map not configured in e2e" }, 503);
    }
    if (path.startsWith("/api/places/photo")) {
      const png = Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "base64",
      );
      return route.fulfill({ status: 200, contentType: "image/png", body: png });
    }
    if (path.startsWith("/api/staticmap")) {
      // 1x1 png
      const png = Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "base64",
      );
      return route.fulfill({ status: 200, contentType: "image/png", body: png });
    }
    if (path === "/api/prayer-times") {
      return json({
        status: "ok",
        city: "Dubai",
        country: "UAE",
        date: "02 Nov 2026",
        timings: { Fajr: "05:20", Sunrise: "06:30", Dhuhr: "12:10", Asr: "15:30", Maghrib: "17:45", Isha: "19:00" },
        source: "Aladhan",
        provenance: "provider_confirmed",
      });
    }
    if (path.startsWith("/api/reading")) {
      return json({
        articles: [
          {
            id: "n1",
            title: "Dubai Marina weekend outlook",
            url: "https://example.com/marina",
            source: "Mock News",
            snippet: "Mild evening temperatures along the waterfront.",
          },
        ],
        status: "ready",
        attribution: "Headlines via Tavily (mocked in e2e).",
        checked_at: "2026-11-02T07:00:00+00:00",
      });
    }
    if (path === "/api/shopping/search" && req.method() === "POST") {
      return json({
        products: [
          {
            title: "Giordano Men's Green Shirt XL",
            price: "AED 95.00",
            source: "Giordano",
            link: "https://www.google.com/search?ibp=oshop&q=shirt",
            thumbnail: "https://encrypted-tbn0.gstatic.com/shopping?q=tbn:ANd9GcMock",
            provenance: "provider_confirmed",
            as_of: "2026-11-02T07:00:00+00:00",
          },
          {
            title: "Namshi Casual Green Oxford XL",
            price: "AED 65.00",
            source: "Namshi",
            link: "https://www.google.com/search?ibp=oshop&q=shirt2",
            thumbnail: "https://encrypted-tbn0.gstatic.com/shopping?q=tbn:ANd9GcMock2",
            provenance: "provider_confirmed",
            as_of: "2026-11-02T07:00:00+00:00",
          },
        ],
        because: [{ key: "clothing_size", value: "XL", label: "size XL" }],
        search_query: "green shirt XL Dubai",
        attribution: "Google Shopping",
        tool: "google_shopping",
        as_of: "2026-11-02T07:00:00+00:00",
      });
    }
    if (path === "/api/auth/connections") {
      return json({
        providers: [
          {
            id: "google",
            label: "Google",
            status: "not_configured",
            can_connect: false,
            scopes: ["openid", "email", "profile"],
            account_label: null,
          },
        ],
      });
    }
    if (path === "/api/mail/status" || path === "/api/mail/needs-reply") {
      return json({
        heading: "Needs a reply",
        items: [],
        source: "none",
        blocker: "Connect Google with Gmail read access to profile your inbox.",
        oauth_configured: false,
        connected: false,
        demo_available: false,
      });
    }
    if (path === "/api/memory/timeline") return json({ items: [] });
    if (path === "/api/memory/hypotheses") return json({ items: [] });
    if (path === "/api/memory/search") return json({ hits: [] });
    if (path === "/api/tryon/status") {
      return json({ ready: true, fixture: true, vertex: false, openai: false });
    }
    if (path === "/api/tryon" && req.method() === "POST") {
      const png =
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";
      return json({
        image_base64: png,
        media_type: "image/png",
        provider: "fixture",
        provenance: "demo_fixture",
        caption: "AI preview · demo fixture · not a size guide",
        demo: true,
      });
    }
    if (/^\/api\/posts\//.test(path)) {
      if (path.endsWith("/comments")) return json({ comments: [] });
      return json({
        post: {
          id: "p1",
          text: "Best way from DXB Terminal 1 to Dubai Marina at 1am?\nLanding late — reliable options?",
          community: { id: "dubai", name: "Dubai Community" },
          author: { name: "Yusuf Demir" },
          created_at: "2026-10-23T07:00:00+00:00",
          provenance: "demo_fixture",
        },
      });
    }
    return json({ detail: "Not mocked" }, 404);
  });
}
