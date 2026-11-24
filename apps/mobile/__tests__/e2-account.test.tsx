import React from "react";
import { act, fireEvent, render, waitFor } from "@testing-library/react-native";
import { Text } from "react-native";
import { AuthProvider, mapPairingErrorCode, parsePairingPayload, useAuth } from "../src/lib/auth";
import { getTodayFeed, postChatTurn } from "../src/lib/api";
import { SourcesCard } from "../src/features/connect/SourcesCard";
import { TodayView } from "../src/components/TodayView";
import { revokeDeviceSession } from "../src/features/connect/connectApi";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));
jest.mock("expo-web-browser", () => ({ openAuthSessionAsync: jest.fn() }));

const BASE = "http://192.168.1.20:8000";
const json = (body: unknown, status = 200) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => body }) as Response;

const sessionBody = (name: string, uid: string) => ({
  session_id: `sid-${uid}`,
  session_token: `tok-${uid}`,
  user_id: uid,
  display_name: name,
  email: `${uid}@example.test`,
});

function Probe() {
  const auth = useAuth();
  return (
    <>
      <Text testID="who">{auth.session?.displayName ?? "nobody"}</Text>
      <Text testID="err">{auth.authError ?? ""}</Text>
    </>
  );
}

describe("QR pairing", () => {
  it("parses a raw code, a JSON payload and a URL payload", () => {
    expect(parsePairingPayload("abc123")).toBe("ABC123");
    expect(parsePairingPayload('{"code":"xy9"}')).toBe("XY9");
    expect(parsePairingPayload("dubaiio://pair?code=zz1")).toBe("ZZ1");
  });

  it("maps expired and reused codes to clear messages", () => {
    expect(mapPairingErrorCode("expired_code", 410)).toMatch(/expired/i);
    expect(mapPairingErrorCode("code_already_used", 409)).toMatch(/already used/i);
    expect(mapPairingErrorCode(undefined, 500)).toMatch(/server error/i);
  });

  async function pair(fetchImpl: typeof fetch, code: string) {
    let ctx: ReturnType<typeof useAuth> | null = null;
    function Grab() {
      ctx = useAuth();
      return null;
    }
    const view = await render(
      <AuthProvider apiBaseUrl={BASE} fetchImpl={fetchImpl}>
        <Grab />
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(ctx?.ready).toBe(true));
    let error: Error | null = null;
    await act(async () => {
      try {
        await ctx!.completePairing(BASE, code);
      } catch (e) {
        error = e as Error;
      }
    });
    return { view, error: error as Error | null };
  }

  it("happy path: phone gets its own session and shows the owner's name", async () => {
    const calls: { url: string; body: string }[] = [];
    const fetchImpl = (async (url: string, init?: RequestInit) => {
      calls.push({ url, body: String(init?.body ?? "") });
      return json(sessionBody("Test Owner", "uid-1"));
    }) as unknown as typeof fetch;
    const { view, error } = await pair(fetchImpl, "code-1");
    expect(error).toBeNull();
    expect(view.getByTestId("who").props.children).toBe("Test Owner");
    expect(calls[0].url).toBe(`${BASE}/api/identity/pair/complete`);
    expect(calls[0].body).toContain('"code":"CODE-1"');
  });

  it("failure paths: expired and reused codes sign nobody in", async () => {
    const expired = (async () => json({ detail: { code: "expired_code" } }, 410)) as unknown as typeof fetch;
    const a = await pair(expired, "old");
    expect(a.error?.message).toMatch(/expired/i);
    expect(a.view.getByTestId("who").props.children).toBe("nobody");

    const reused = (async () => json({ detail: { code: "code_already_used" } }, 409)) as unknown as typeof fetch;
    const b = await pair(reused, "used");
    expect(b.error?.message).toMatch(/already used/i);
    expect(b.view.getByTestId("who").props.children).toBe("nobody");
  });

  it("wrong network gives a clear message", async () => {
    const down = (async () => {
      throw new Error("ECONNREFUSED");
    }) as unknown as typeof fetch;
    const { error } = await pair(down, "code");
    expect(error?.message).toMatch(/could not reach the API server/i);
  });
});

describe("Google sign-in exchange and sign-out", () => {
  it("exchanges the auth_code for a session and revokes it on sign-out", async () => {
    const seen: string[] = [];
    const fetchImpl = (async (url: string, init?: RequestInit) => {
      seen.push(`${init?.method ?? "GET"} ${url}`);
      if (url.endsWith("/google/exchange")) return json(sessionBody("Founder Test", "uid-f"));
      return json({});
    }) as unknown as typeof fetch;
    let ctx: ReturnType<typeof useAuth> | null = null;
    function Grab() {
      ctx = useAuth();
      return null;
    }
    const view = await render(
      <AuthProvider apiBaseUrl={BASE} fetchImpl={fetchImpl}>
        <Grab />
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(ctx?.ready).toBe(true));
    await act(async () => {
      await ctx!.exchangeAuthCode(BASE, "one-time");
    });
    expect(view.getByTestId("who").props.children).toBe("Founder Test");
    await act(async () => {
      await ctx!.signOut(BASE);
    });
    expect(view.getByTestId("who").props.children).toBe("nobody");
    expect(seen).toContain(`DELETE ${BASE}/api/identity/sessions/sid-uid-f`);
  });

  it("a rejected auth_code surfaces the server message and signs nobody in", async () => {
    const fetchImpl = (async () =>
      json({ detail: { message: "auth_code has already been used" } }, 401)) as unknown as typeof fetch;
    let ctx: ReturnType<typeof useAuth> | null = null;
    function Grab() {
      ctx = useAuth();
      return null;
    }
    await render(
      <AuthProvider apiBaseUrl={BASE} fetchImpl={fetchImpl}>
        <Grab />
      </AuthProvider>,
    );
    await waitFor(() => expect(ctx?.ready).toBe(true));
    let msg = "";
    await act(async () => {
      try {
        await ctx!.exchangeAuthCode(BASE, "used");
      } catch (e) {
        msg = (e as Error).message;
      }
    });
    expect(msg).toMatch(/already been used/);
    expect(ctx!.isAuthenticated).toBe(false);
  });

  it("revoking a device calls DELETE on that session with the caller's token", async () => {
    const fetcher = jest.fn(async () => ({ ok: true, status: 200, json: async () => ({}) }));
    await revokeDeviceSession(BASE, "tok-a", "sid-phone", fetcher);
    expect(fetcher).toHaveBeenCalledWith(
      `${BASE}/api/identity/sessions/sid-phone`,
      expect.objectContaining({ method: "DELETE", headers: expect.objectContaining({ "X-App-Session": "tok-a" }) }),
    );
  });
});

describe("Isolation: two synthetic accounts", () => {
  const backend = (async (url: string, init?: RequestInit) => {
    const token = (init?.headers as Record<string, string>)["X-App-Session"];
    if (url.endsWith("/api/today")) {
      if (token === "tok-A") return json({ as_of: "2026-11-24T10:00:00Z", cards: [{ id: "a1", title: "Alpha card", source: "Amazon.ae", because: "Because: A", provenance: "provider_confirmed", as_of: "2026-11-24T10:00:00Z" }] });
      if (token === "tok-B") return json({ as_of: "2026-11-24T10:00:00Z", cards: [{ id: "b1", title: "Bravo card", source: "Amazon.ae", because: "Because: B", provenance: "provider_confirmed", as_of: "2026-11-24T10:00:00Z" }] });
      return json({}, 401);
    }
    if (url.endsWith("/api/chat/turn")) {
      return json({ ok: true, ingested: true, reply: `hello ${token}`, citations: [] });
    }
    return json({}, 404);
  }) as unknown as typeof fetch;

  it("A's feed never contains B's cards and vice versa; no token means no data", async () => {
    const a = await getTodayFeed(BASE, { sessionToken: "tok-A" }, { fetchImpl: backend });
    const b = await getTodayFeed(BASE, { sessionToken: "tok-B" }, { fetchImpl: backend });
    const none = await getTodayFeed(BASE, { sessionToken: null }, { fetchImpl: backend });
    expect(a.cards.map((c) => c.title)).toEqual(["Alpha card"]);
    expect(b.cards.map((c) => c.title)).toEqual(["Bravo card"]);
    expect(none.cards).toEqual([]);
    expect(none.status).toBe("unauthenticated");
  });

  it("the Today screen renders only the signed-in owner's cards and no demo data", async () => {
    const view = await render(
      <TodayView onOpenSettings={() => undefined} apiBaseUrl={BASE} sessionToken="tok-B" displayName="Bravo" fetchImpl={backend} />,
    );
    await waitFor(() => expect(view.getByText("Bravo card")).toBeTruthy());
    expect(view.queryByText("Alpha card")).toBeNull();
    expect(view.queryByText("Demo data")).toBeNull();
    expect(view.queryByText(/Karim/)).toBeNull();
  });

  it("normal-mode chat sends the session token and never the demo owner", async () => {
    const spy = jest.fn(backend);
    const turn = await postChatTurn(BASE, { text: "hi", sessionToken: "tok-A" }, { fetchImpl: spy as unknown as typeof fetch });
    expect(turn.reply).toBe("hello tok-A");
    const init = spy.mock.calls[0][1] as RequestInit;
    expect(String(init.body)).not.toContain("karim");
    expect(String(init.body)).not.toContain("owner");
    const signedOut = await postChatTurn(BASE, { text: "hi", sessionToken: null }, { fetchImpl: spy as unknown as typeof fetch });
    expect(signedOut.ok).toBe(false);
    expect(signedOut.demo).toBe(false);
    expect(spy).toHaveBeenCalledTimes(1);
  });
});

describe("Sources (E3 consent + connect)", () => {
  it("is off by default, consent PUT precedes connect, and failures are shown", async () => {
    const calls: string[] = [];
    let enabled = false;
    const fetcher = jest.fn(async (url: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? "GET"} ${url.replace(BASE, "")}`);
      if (url.endsWith("/api/ingest/status")) {
        return { ok: true, status: 200, json: async () => ({ sources: { gmail: { enabled, connected: false } } }) };
      }
      if (url.endsWith("/api/ingest/consent/gmail")) {
        enabled = true;
        return { ok: true, status: 200, json: async () => ({ source: "gmail", enabled: true }) };
      }
      if (url.endsWith("/api/ingest/google/gmail/connect")) {
        return { ok: true, status: 200, json: async () => ({ authorization_url: "https://accounts.google.com/o/oauth2/v2/auth?x=1" }) };
      }
      return { ok: false, status: 500, json: async () => ({}) };
    });
    const openUrl = jest.fn();
    const view = await render(<SourcesCard apiBaseUrl={BASE} sessionToken="tok-A" fetcher={fetcher} openUrl={openUrl} />);
    await waitFor(() => expect(view.getByTestId("consent-gmail").props.value).toBe(false));
    expect(view.queryByTestId("connect-gmail")).toBeNull();

    await fireEvent(view.getByTestId("consent-gmail"), "valueChange", true);
    await waitFor(() => expect(view.getByTestId("connect-gmail")).toBeTruthy());
    await fireEvent.press(view.getByTestId("connect-gmail"));
    await waitFor(() => expect(openUrl).toHaveBeenCalledWith(expect.stringContaining("accounts.google.com")));
    expect(calls.indexOf("PUT /api/ingest/consent/gmail")).toBeLessThan(calls.indexOf("POST /api/ingest/google/gmail/connect"));
    expect(JSON.stringify(calls)).not.toMatch(/secret/i);
  });

  it("shows an honest error when the connect call is refused", async () => {
    const fetcher = jest.fn(async (url: string) => {
      if (url.endsWith("/api/ingest/status")) {
        return { ok: true, status: 200, json: async () => ({ sources: { gmail: { enabled: true, connected: false } } }) };
      }
      return { ok: false, status: 403, json: async () => ({}) };
    });
    const openUrl = jest.fn();
    const view = await render(<SourcesCard apiBaseUrl={BASE} sessionToken="tok-A" fetcher={fetcher} openUrl={openUrl} />);
    await waitFor(() => expect(view.getByTestId("connect-gmail")).toBeTruthy());
    await fireEvent.press(view.getByTestId("connect-gmail"));
    await waitFor(() => expect(view.getByTestId("sources-notice")).toBeTruthy());
    expect(view.getByTestId("sources-notice").props.children).toMatch(/consent/i);
    expect(openUrl).not.toHaveBeenCalled();
  });
});
