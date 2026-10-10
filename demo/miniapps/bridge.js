// Shared bridge helper for every mini-app. The widget can only SEND to the host.
// - The host passes its own origin in the URL (?host=...). The widget uses it as an explicit targetOrigin, never a wildcard.
// - A sandboxed iframe (no allow-same-origin) has an opaque origin, so no host-to-widget message channel exists.
//   Any display data the widget needs (e.g. the generated shop's catalog) arrives in the URL (?cfg=...).
// - The only kinds a widget may send: app.ready (lifecycle) and the manifest scope order.request.
(function () {
  const params = new URLSearchParams(location.search);
  const HOST = params.get("host");

  function send(kind, payload) {
    if (!HOST || HOST === "null") return false;
    try { parent.postMessage({ v: 1, kind: kind, payload: payload || {} }, HOST); return true; }
    catch (e) { return false; }
  }

  function cfg() {
    try { return JSON.parse(params.get("cfg") || "null"); } catch (e) { return null; }
  }

  window.Bridge = { send: send, cfg: cfg };
})();
