"use client";
import { useEffect, useState } from "react";
import { getApiBase } from "@/lib/api";
import { authHeaders, getSessionToken, googleStartUrl, setSessionToken } from "@/lib/session";

type Me = { display_name?: string; user_id?: string };

export default function SignInPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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
        <article className="card">
          <p className="ai-text">Sign in with Google. Community only learns your name and a stable account id; memory stays off until you opt in on Profile.</p>
          <button type="button" className="action-box" style={{ maxWidth: 240 }}
            onClick={() => { window.location.href = googleStartUrl(`${window.location.origin}/signin`); }}>
            Continue with Google
          </button>
        </article>
      )}
    </section>
  );
}
