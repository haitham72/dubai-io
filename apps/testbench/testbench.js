"use strict";

const ports = Object.freeze({ quest: 8000, community: 8060, messenger: 8070, memory: 8040 });
const sessions = new Map();
let deviceToken;
let memoryOwner;

function endpoint(service, path) {
  if (!Object.hasOwn(ports, service) || !path.startsWith("/") || path.startsWith("//")) {
    throw new Error("Invalid local endpoint");
  }
  const base = new URL(window.location.origin);
  base.hostname = window.location.hostname;
  base.port = ports[service];
  const target = new URL(path, base);
  if (target.origin !== base.origin) throw new Error("Endpoint must stay on the selected local service");
  return target;
}

const json = (value) => JSON.stringify(value, (key, field) =>
  ["auth_code", "session_token", "token", "Authorization", "X-App-Session"].includes(key)
    ? "[redacted]" : field, 2);
const query = (path, parameters) => path + "?" + new URLSearchParams(parameters);
const segment = (value) => {
  if (!value || value === "." || value === "..") throw new Error("Enter a valid ID.");
  return encodeURIComponent(value);
};

function node(tag, text) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  return el;
}

function action(section, title, options, build) {
  const form = node("form");
  const fieldset = node("fieldset");
  fieldset.append(node("legend", title));
  for (const [key, label, type, values] of options) {
    const caption = node("label", label + " ");
    const field = node(type === "select" ? "select" : type === "textarea" ? "textarea" : "input");
    field.name = key;
    if (type === "select") {
      for (const value of values) {
        const option = node("option", value);
        option.value = value;
        field.append(option);
      }
    } else if (type !== "textarea") {
      field.type = type || "text";
    }
    if (type === "password") field.autocomplete = "off";
    caption.append(field);
    fieldset.append(caption);
  }
  const button = node("button", title);
  const status = node("p");
  status.setAttribute("role", "status");
  const request = node("pre");
  const response = node("pre");
  const followup = node("div");
  fieldset.append(button, status, request, response, followup);
  form.append(fieldset);
  document.getElementById(section).append(form);

  async function submit(values) {
    button.disabled = true;
    status.textContent = "";
    request.textContent = "";
    response.textContent = "";
    followup.replaceChildren();
    try {
      const specs = [build(values)].flat();
      for (const spec of specs) {
        const url = endpoint(spec.service, spec.path);
        const method = spec.method || "GET";
        const headers = {};
        if (spec.body !== undefined) headers["Content-Type"] = "application/json";
        const session = sessions.get(spec.service);
        if (session && !spec.public) headers["X-App-Session"] = session;
        if (spec.device && deviceToken) headers.Authorization = "Bearer " + deviceToken;
        const body = spec.body === undefined ? undefined : JSON.stringify(spec.body);
        request.textContent += (request.textContent ? "\n\n" : "") + "Request\n" + method + " " + url + "\n" + json({ headers, body: spec.body });
        if (spec.navigate) {
          status.textContent = "Browser navigation. The OAuth exchange shows its own HTTP response.";
          window.location.assign(url);
          return;
        }
        const result = await fetch(url, { method, headers, body, credentials: "include", redirect: "error" });
        status.textContent += (status.textContent ? " ? " : "") + "HTTP " + result.status + " " + result.statusText;
        const text = await result.text();
        let payload;
        try {
          payload = JSON.parse(text);
        } catch {
          response.textContent += (response.textContent ? "\n\n" : "") + (text || "(empty response)");
          continue;
        }
        response.textContent += (response.textContent ? "\n\n" : "") + "Response\n" + json(payload);
        if (result.ok && payload !== null && spec.receive) spec.receive(payload, followup);
      }
    } catch (error) {
      status.textContent += (status.textContent ? " ? " : "") + error.message;
    } finally {
      button.disabled = false;
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void submit(Object.fromEntries(new FormData(form)));
  });
  return submit;
}

const get = (service, path, extra) => ({ service, path, ...extra });
const send = (service, path, body, extra) => ({ service, path, method: "POST", body, ...extra });
const put = (service, path, body) => ({ service, path, method: "PUT", body });
const text = (key, label) => [key, label, "text"];
const choose = (key, label, values) => [key, label, "select", values];
const appChoice = choose("app", "App", ["quest", "community", "messenger"]);
const identity = "/api/identity";
const rememberSession = (app) => (payload) => {
  if (payload.app_id === app && typeof payload.session_token === "string") sessions.set(app, payload.session_token);
};
function clearCredentials() {
  sessions.clear();
  deviceToken = undefined;
  memoryOwner = undefined;
}

for (const [title, service, path] of [
  ["Dubai IO health", "quest", "/api/health"], ["Community health", "community", "/api/health"],
  ["Messenger health", "messenger", "/api/messenger/health"], ["Memory health", "memory", "/health"],
]) {
  action("health", title, [], () => get(service, path, { public: true }));
}
const memoryHealth = node("a", "Open memory health directly if its API blocks cross-origin reads");
memoryHealth.href = endpoint("memory", "/health");
memoryHealth.target = "_blank";
memoryHealth.rel = "noopener noreferrer";
document.getElementById("health").append(memoryHealth);

action("identity", "Google sign-in (PC)", [appChoice], ({ app }) => {
  if (!["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    throw new Error("Open the Test Bench on localhost on the PC, or pair with a code.");
  }
  const returnTo = endpoint("quest", "/testbench/?app=" + app);
  return get("quest", query(identity + "/google/start", { client: "web", return_to: returnTo }), { navigate: true });
});
const exchangeCode = action("identity", "Exchange Google sign-in code", [appChoice, ["code", "One-time code", "password"]], ({ app, code }) =>
  send("quest", identity + "/google/exchange", { auth_code: code, app_id: app, set_cookie: true },
    { public: true, receive: rememberSession(app) }));
const callback = new URL(window.location.href);
const authCode = callback.searchParams.get("auth_code");
const callbackApp = callback.searchParams.get("app");
if (authCode) {
  history.replaceState(null, "", "/testbench/");
  if (["quest", "community", "messenger"].includes(callbackApp)) void exchangeCode({ app: callbackApp, code: authCode });
}
action("identity", "Pair iPhone ? start", [appChoice], ({ app }) => send(app, identity + "/pair/start"));
action("identity", "Pair iPhone ? complete", [appChoice, text("code", "Six-character code")], ({ app, code }) =>
  send(app, identity + "/pair/complete", { code: code.trim(), app_id: app }, { public: true, receive: rememberSession(app) }));
action("identity", "Who am I?", [appChoice], ({ app }) => get(app, identity + "/me"));
action("identity", "List sessions", [appChoice], ({ app }) => get(app, identity + "/sessions"));
action("identity", "Revoke all sessions", [appChoice], ({ app }) =>
  send(app, identity + "/sessions/revoke-all", {}, { receive: clearCredentials }));
action("identity", "Delete my data", [appChoice, text("confirm", "Type DELETE to confirm")], ({ app, confirm }) => {
  if (confirm !== "DELETE") throw new Error("Type DELETE to confirm.");
  return send(app, identity + "/delete-my-data", { confirm: true }, { receive: clearCredentials });
});

action("quest", "Ingest status", [], () => get("quest", "/api/ingest/status"));
for (const [source, label] of [["gmail", "Gmail"], ["calendar", "Calendar"], ["youtube", "YouTube"]]) {
  action("quest", label + " ingest consent", [choose("enabled", "Enabled", ["false", "true"])],
    ({ enabled }) => put("quest", "/api/ingest/consent/" + source, { enabled: enabled === "true" }));
  action("quest", "Connect " + label, [], () =>
    send("quest", "/api/ingest/google/" + source + "/connect", undefined, { receive(payload, target) {
      if (!payload.authorization_url) return;
      const url = new URL(payload.authorization_url);
      if (url.protocol !== "https:" || url.hostname !== "accounts.google.com") return;
      const link = node("a", "Continue to Google");
      link.href = url;
      link.rel = "noreferrer";
      target.append(link);
    } }));
}
action("quest", "Chat turn", [["message", "Ask", "textarea"], text("thread", "Thread ID (optional)")], ({ message, thread }) =>
  send("quest", "/api/chat/turn", { text: message, ...(thread ? { thread_id: thread } : {}) }));
action("quest", "Mint memory device token", [], () => send("quest", identity + "/memory-device-token", { label: "Test Bench" }, {
  receive(payload) {
    if (payload.token && payload.owner_id) {
      deviceToken = payload.token;
      memoryOwner = payload.owner_id;
    }
  },
}));
for (const [title, includeLowered] of [["Memory search", false], ["Explicit recall", true]]) {
  action("quest", title, [text("q", "Query")], ({ q }) => {
    if (!deviceToken || !memoryOwner) throw new Error("Mint a memory device token first.");
    if (!q.trim()) throw new Error("Enter a query first.");
    return get("memory", query("/v1/owners/" + segment(memoryOwner) + "/search",
      { q, include_lowered: includeLowered }), { device: true });
  });
}
action("quest", "Vault timeline", [], () => get("quest", "/api/vault/timeline"));
action("quest", "Lowered vault timeline", [], () => get("quest", "/api/vault/timeline?lowered=true"));
for (const lower of [true, false]) {
  action("quest", lower ? "Lower memory" : "Restore memory", [
    choose("kind", "Target", ["fact_id", "source"]), text("value", "Fact ID or source"),
  ], ({ kind, value }) => send("quest", "/api/vault/lower", { [kind]: value.trim(), lower }));
}
action("quest", "Today feed", [], () => get("quest", "/api/today"));

const cm = "/api/community";
const community = "community";
action(community, "Community session", [], () => get(community, identity + "/me"));
action(community, "For you feed", [], () => get(community, cm + "/feed?sort=hot"));
action(community, "Following feed", [], () => {
  let followed;
  return [
    get(community, cm + "/follows", { receive(payload) {
      if (Array.isArray(payload.following)) followed = new Set(payload.following.map((entry) => entry.owner));
    } }),
    get(community, cm + "/feed?sort=hot", { receive(payload, target) {
      if (!followed || !Array.isArray(payload.posts)) return;
      const posts = payload.posts.filter((post) => followed.has(post.owner));
      target.append(node("pre", "Following ? filtered from the responses\n" + json(posts)));
    } }),
  ];
});
action(community, "Create post", [["message", "Post text", "textarea"]], ({ message }) =>
  send(community, cm + "/posts", { text: message }));
action(community, "Comment", [text("id", "Post ID"), ["message", "Comment", "textarea"]], ({ id, message }) =>
  send(community, cm + "/posts/" + segment(id.trim()) + "/comments", { text: message }));
action(community, "Vote", [text("id", "Post ID"), choose("value", "Vote", ["1", "0", "-1"])], ({ id, value }) =>
  send(community, cm + "/posts/" + segment(id.trim()) + "/vote", { value: Number(value) }));
action(community, "Discovery", [], () => get(community, cm + "/discovery"));
action(community, "Context opt-in", [choose("enabled", "Enabled", ["false", "true"])], ({ enabled }) =>
  put(community, cm + "/profile/usage/settings", { context_aware_enabled: enabled === "true" }));
action(community, "Manual area heartbeat", [choose("area", "Area", [
  "Dubai Marina", "JLT", "DIFC", "Downtown Dubai", "Business Bay", "Jumeirah",
  "Al Quoz", "Deira", "Bur Dubai", "Palm Jumeirah", "Internet City",
])], ({ area }) => send(community, cm + "/context/heartbeat", { area_coarse: area, source: "manual", confidence: 1 }));
action(community, "Usage profile", [], () => get(community, cm + "/profile/usage"));
action(community, "Lower Community memory", [
  choose("kind", "Target", ["topic", "target_id", "source_id"]), text("value", "Value"),
], ({ kind, value }) => {
  if (!value.trim()) throw new Error("Enter the Community memory target to lower.");
  return send(community, cm + "/memory/lower", { [kind]: value.trim() });
});
action(community, "Get Community consent", [], () => get(community, cm + "/memory/consent"));
action(community, "Set Community consent", [
  choose("key", "Setting", ["read_enabled", "write_enabled", "allow_interest_export", "remember_saved_discussions", "remember_public_posts"]),
  choose("enabled", "Enabled", ["false", "true"]),
], ({ key, enabled }) => put(community, cm + "/memory/consent", { [key]: enabled === "true" }));

const messenger = "messenger";
const msg = "/api/messenger";
const conversations = msg + "/conversations";
action(messenger, "Messenger session", [], () => get(messenger, identity + "/me"));
action(messenger, "List conversations", [], () => get(messenger, conversations));
action(messenger, "Send message", [text("id", "Conversation ID"), ["message", "Message", "textarea"]], ({ id, message }) =>
  send(messenger, conversations + "/" + segment(id.trim()) + "/messages", {
    text: message, client_msg_id: Array.from(crypto.getRandomValues(new Uint8Array(16)),
      (byte) => byte.toString(16).padStart(2, "0")).join(""),
  }));
action(messenger, "Owner recall", [text("id", "Conversation ID"), text("q", "Query")], ({ id, q }) =>
  send(messenger, "/api/v1/memory-bridge/messenger/conversations/" + segment(id.trim()) + "/recall", { query: q }));
action(messenger, "Memory settings", [], () => get(messenger, msg + "/memory"));
for (const lower of [true, false]) {
  action(messenger, lower ? "Lower Messenger memory" : "Restore Messenger memory", [text("id", "Record ID")],
    ({ id }) => send(messenger, msg + "/memory/lower", { record_id: id.trim(), lower }));
}
