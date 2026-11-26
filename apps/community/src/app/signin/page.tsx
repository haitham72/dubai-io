"use client";
import { useEffect, useState } from "react";
import { getApiBase } from "@/lib/api";
import { authHeaders, getSessionToken, googleStartUrl, setSessionToken } from "@/lib/session";

type Me = { display_name?: string; user_id?: string };

export default function SignInPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pairCode, setPairCode] = useState("");
  const [pairing, setPairing] = useState(false);

  useEffect(() => {
    let live = true;
    const url = new URL(window.location.href);
    const code = url.searchParams.get("auth_code");
    async function run() {
      if (code) {
        window.history.replaceState({}, "", url.pathname);
        const r = await fetch(`${getApiBase()}/api/identity/google/exchange`, {
          method: "POST", headers: { "content-type": "application/json" },
          body: JSON.stringify({ auth_code: code, app_id: "community", device_label: "Community web" }),
        });
        if (!r.ok) throw new Error("Sign-in could not be completed. Try again.");
        setSessionToken((await r.json()).session_token ?? null);
      }
      const token = getSessionToken();
      if (!token) return;
      const r = await fetch(`${getApiBase()}/api/identity/me`, { headers: authHeaders(token) });
      if (!r.ok) { setSessionToken(null); return; }
      if (live) setMe(await r.json());
    }
    run().catch((e) => { if (live) setNotice(String(e.message ?? e)); });
    return () => { live = false; };
  }, []);

  async function handlePair() {
    const clean = pairCode.trim().toUpperCase();
    if (!clean) {
      setNotice("Enter the 6-character pairing code from your PC.");
      return;
    }
    setNotice(null);
    setPairing(true);
    try {
      const r = await fetch(`${getApiBase()}/api/identity/pair/complete`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ code: clean, app_id: "community", device_label: "Community phone" }),
      });
      if (!r.ok) {
        let msg = "Pairing code invalid or expired. Try a fresh code.";
        try {
          const err = await r.json();
          if (typeof err?.detail === "string" && err.detail.trim()) msg = err.detail;
          else if (typeof err?.detail?.message === "string" && err.detail.message.trim()) msg = err.detail.message;
        } catch { /* keep default message */ }
        throw new Error(msg);
      }
      const data = await r.json();
      const token: string | null = data?.session_token ?? null;
      setSessionToken(token);
      if (!token) throw new Error("Pairing code invalid or expired. Try a fresh code.");
      const meRes = await fetch(`${getApiBase()}/api/identity/me`, { headers: authHeaders(token) });
      if (!meRes.ok) {
        setSessionToken(null);
        throw new Error("Signed in, but could not load your account. Try again.");
      }
      setMe(await meRes.json());
      setPairCode("");
    } catch (e) {
      setNotice(e instanceof Error && e.message ? e.message : "Pairing code invalid or expired. Try a fresh code.");
    } finally {
      setPairing(false);
    }
  }

  return (
    <section>
      <h1>Sign in</h1>
      <p className="sub">The same account as Quest and Messenger.</p>
      {notice && <div className="notice" role="status">{notice}</div>}
      {me ? (
        <article className="card">
          <h2>Signed in as {me.display_name || "your account"}</h2>
          <button type="button" className="action-box" style={{ maxWidth: 180 }}
            onClick={() => { setSessionToken(null); setMe(null); }}>Sign out</button>
        </article>
      ) : (
        <>
          <article className="card">
            <p className="ai-text">Sign in with Google. Community only learns your name and a stable account id; memory stays off until you opt in on Profile.</p>
            <button type="button" className="action-box" style={{ maxWidth: 240 }}
              onClick={() => { window.location.href = googleStartUrl(`${window.location.origin}/signin`); }}>
              Continue with Google
            </button>
          </article>
          <article className="card">
            <h2>Pair with PC code</h2>
            <p className="ai-text">On PC Chrome, open Dubai-io &rarr; Pair iPhone, then enter the 6-character code here.</p>
            <div className="actions" style={{ alignItems: "center" }}>
              <input
                type="text"
                value={pairCode}
                onChange={(e) => setPairCode(e.target.value.toUpperCase())}
                placeholder="6-character code"
                aria-label="6-character pairing code"
                maxLength={6}
                autoCapitalize="characters"
                autoCorrect="off"
                spellCheck={false}
                style={{ maxWidth: 180, letterSpacing: "0.12em", fontFamily: "ui-monospace, monospace" }}
              />
              <button
                type="button"
                className="action-box"
                style={{ maxWidth: 160 }}
                disabled={pairing}
                onClick={() => { void handlePair(); }}
              >
                {pairing ? "Pairing..." : "Pair device"}
              </button>
            </div>
          </article>
        </>
      )}
    </section>
  );
}
