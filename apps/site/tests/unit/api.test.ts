import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ApiError, apiGet, apiPost, apiPut, resetSession } from "../../unified/data/api";

const ok = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
let calls: string[] = [];

beforeEach(() => {
  calls = [];
  resetSession();
});
afterEach(() => vi.unstubAllGlobals());

test("session is fetched once, first, with credentials", async () => {
  const init: RequestInit[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, i: RequestInit) => { calls.push(`${i?.method ?? "GET"} ${url}`); init.push(i); return ok({ x: 1 }); }));
  await apiGet("/api/today");
  await apiPost("/api/luna/turn", { text: "hi" });
  await apiPut("/api/session/memory/area", { value: "Marina" });
  expect(calls).toEqual(["GET /api/session", "GET /api/today", "POST /api/luna/turn", "PUT /api/session/memory/area"]);
  expect(init.every((i) => i.credentials === "include")).toBe(true);
});

test("non-2xx throws ApiError with status and message", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => (url === "/api/session" ? ok({}) : ok({ detail: "OPENAI_API_KEY is not set" }, 503))));
  await expect(apiPost("/api/luna/turn", { text: "x" })).rejects.toMatchObject({ status: 503, message: "OPENAI_API_KEY is not set" });
  await expect(apiGet("/api/x")).rejects.toBeInstanceOf(ApiError);
});

test("a failed session call is retried on the next request", async () => {
  let n = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => { if (url === "/api/session" && n++ === 0) throw new TypeError("offline"); return ok({}); }));
  await expect(apiGet("/api/today")).rejects.toBeInstanceOf(ApiError);
  await expect(apiGet("/api/today")).resolves.toEqual({});
});
