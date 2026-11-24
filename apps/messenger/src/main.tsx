import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { actions, getState } from "./store";
import { exchangeGoogleAuthCode } from "./apiclient/chatCore";
import "./tokens.css";

(window as unknown as Record<string, unknown>).__messenger = { actions, getState };
// Google sign-in lands here with ?auth_code=...: redeem it for a messenger session, then fall back to a saved session.
async function boot() {
  const url = new URL(window.location.href);
  const code = url.searchParams.get("auth_code");
  if (code) {
    window.history.replaceState({}, "", url.pathname);
    try {
      const out = await exchangeGoogleAuthCode(code);
      await actions.signInWithSessionToken(out.session_token, { displayName: out.display_name });
      return;
    } catch { /* fall through to the saved session / signed-out state */ }
  }
  await actions.restoreSession();
}
void boot();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
