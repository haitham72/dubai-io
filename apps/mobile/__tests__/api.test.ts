import { isIngestConfirmed, localhostWarning, postMemoryChatTurn } from "../src/lib/api";

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 500,
    json: async () => body,
  } as Response;
}

describe("API client", () => {
  it("warns on localhost and accepts a LAN address", () => {
    expect(localhostWarning("http://localhost:8000")).toMatch(/localhost/i);
    expect(localhostWarning("http://127.0.0.1:8000")).toMatch(/localhost/i);
    expect(localhostWarning("http://192.168.1.20:8000")).toBeNull();
  });

  it("falls back to demo data when the backend is unreachable and does not confirm ingest", async () => {
    const fetchImpl = jest.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    const turn = await postMemoryChatTurn(
      "http://192.168.1.20:8000",
      { ownerId: "karim", text: "hello", demo: true },
      { fetchImpl: fetchImpl as unknown as typeof fetch },
    );
    expect(turn.demo).toBe(true);
    expect(turn.ok).toBe(false);
    expect(turn.applied).toBe(false);
    expect(isIngestConfirmed(turn, { demo: turn.demo, httpOk: false })).toBe(false);
    expect(turn.reply).toMatch(/demo data/i);
  });

  it("confirms ingest only from an applied or ok response", async () => {
    const fetchImpl = jest.fn(async () =>
      jsonResponse({
        ok: true,
        applied: true,
        applied_fact_ids: ["fact-1"],
        reply: "Stored.",
        trust: "T1",
        topic: "gaming/preferences",
      }),
    );
    const turn = await postMemoryChatTurn(
      "http://192.168.1.20:8000",
      { ownerId: "karim", text: "remember gaming" },
      { fetchImpl: fetchImpl as unknown as typeof fetch },
    );
    expect(turn.demo).toBe(false);
    expect(turn.applied).toBe(true);
    expect(isIngestConfirmed(turn, { demo: false, httpOk: true })).toBe(true);

    const rejected = await postMemoryChatTurn(
      "http://192.168.1.20:8000",
      { ownerId: "karim", text: "nope" },
      { fetchImpl: (async () => jsonResponse({ ok: false }, false)) as unknown as typeof fetch },
    );
    expect(rejected.demo).toBe(false);
    expect(rejected.ok).toBe(false);
    expect(isIngestConfirmed(rejected, { demo: false, httpOk: false })).toBe(false);
  });
});
