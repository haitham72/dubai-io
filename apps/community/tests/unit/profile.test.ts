import { afterEach, describe, expect, test, vi } from "vitest";
import { getMyProfile } from "@/lib/api";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("getMyProfile", () => {
  test("no profile yet is null from ONE call (200, no 404 for the console)", async () => {
    const f = stubFetch(200, { profile: null });
    expect(await getMyProfile()).toBeNull();
    expect(f).toHaveBeenCalledTimes(1);
  });
  test("returns the profile when it exists", async () => {
    stubFetch(200, { profile: { handle: "alice_dxb", privacy: "public" } });
    expect((await getMyProfile())?.handle).toBe("alice_dxb");
  });
  test("a real failure still rejects", async () => {
    stubFetch(500, { detail: "boom" });
    await expect(getMyProfile()).rejects.toThrow();
  });
});
