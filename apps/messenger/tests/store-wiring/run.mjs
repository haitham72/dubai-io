// Node regression tests for Messenger store wiring, auth, WS replay/outbox, demo mode, and tunnel routing.
const makeMemStorage = () => ({
  _s: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
  setItem(k, v) { this._s[k] = String(v); },
  removeItem(k) { delete this._s[k]; },
});

globalThis.localStorage = makeMemStorage();
globalThis.sessionStorage = makeMemStorage();

const mod = await import("./bundle.mjs");
const {
  actions,
  getState,
  readChatListSnapshot,
  fetchMessages,
  sendMessageRest,
  resolveWsUrl,
  img,
  avatar,
  ORB,
} = mod;

const fail = (msg) => {
  console.error("FAIL:", msg);
  process.exit(1);
};
const assert = (cond, msg) => {
  if (!cond) fail(msg);
};
const waitFor = async (pred, timeoutMs = 4000, label = "condition") => {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (pred()) return;
    await new Promise((r) => setTimeout(r, 15));
  }
  fail(`Timed out waiting for ${label}`);
};

/* ---------- Mock /api/identity/* + /api/messenger/* + WS backend ---------- */
function createMockBackend() {
  let seqCounter = 0;
  let ticketCounter = 0;
  let msgCounter = 0;
  let convCounter = 0;

  const sessions = new Map(); // token -> { user_id, age_band }
  const tickets = new Map(); // ticket -> { user_id, origin, used }
  const conversations = new Map(); // id -> { id, kind, title, member_ids }
  const messages = new Map(); // convId -> ChatMessageRow[]
  const receipts = [];
  const requestedUrls = [];
  const wsUrls = [];
  const subscribeFrames = [];
  const sentClientMsgIds = [];

  const state = {
    restOffline: false,
    failMeWith401: false,
    ticketsIssued: 0,
    activeSockets: [],
  };

  function jsonRes(status, data) {
    return {
      ok: status >= 200 && status < 300,
      status,
      async text() { return JSON.stringify(data); },
      async json() { return data; },
    };
  }

  function requireSession(headers) {
    const token = headers["X-App-Session"] || headers["x-app-session"];
    const sess = token ? sessions.get(token) : null;
    if (!sess) return null;
    return { token, ...sess };
  }

  function isMember(convId, userId) {
    const conv = conversations.get(convId);
    return !!conv && conv.member_ids.includes(userId);
  }

  function sendBackendMessage(convId, senderId, clientMsgId, text) {
    if (!isMember(convId, senderId)) {
      return { error: { status: 404, code: "not_found" } };
    }
    const list = messages.get(convId) ?? [];
    const existing = list.find((m) => m.sender_id === senderId && m.client_msg_id === clientMsgId);
    if (existing) {
      return { message: existing };
    }
    seqCounter += 1;
    msgCounter += 1;
    const row = {
      id: `msg-${msgCounter}`,
      conversation_id: convId,
      sender_id: senderId,
      client_msg_id: clientMsgId,
      seq: seqCounter,
      body: text,
      created_at: new Date().toISOString(),
      edited_at: null,
      deleted: false,
    };
    list.push(row);
    messages.set(convId, list);
    return { message: row };
  }

  const fetchImpl = async (url, init = {}) => {
    requestedUrls.push(url);
    if (state.restOffline) {
      throw new TypeError("Network offline");
    }
    const u = new URL(url, "http://localhost");
    const path = u.pathname;
    const method = (init.method || "GET").toUpperCase();
    const headers = init.headers || {};
    const body = init.body ? JSON.parse(init.body) : {};

    if (path === "/api/identity/sessions" && method === "POST") {
      const auth = String(headers.Authorization || headers.authorization || "");
      const jwt = auth.replace(/^Bearer\s+/i, "");
      if (!jwt) return jsonRes(401, { detail: { code: "missing_jwt" } });
      const userId = jwt.startsWith("jwt-") ? jwt.slice(4) : "user-1";
      const sessionToken = `sess-${userId}-${sessions.size + 1}`;
      sessions.set(sessionToken, { user_id: userId, age_band: null });
      return jsonRes(200, {
        session_id: `sid-${sessions.size}`,
        session_token: sessionToken,
        user_id: userId,
        app_id: "messenger",
        capabilities: ["messenger:chat", "messenger:ws"],
        age_band: null,
        expires_at: Math.floor(Date.now() / 1000) + 3600,
      });
    }

    if (path === "/api/identity/age-band" && method === "POST") {
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: { code: "invalid_session" } });
      sessions.get(sess.token).age_band = body.age_band;
      return jsonRes(200, {
        user_id: sess.user_id,
        age_band: body.age_band,
        age_source: "self_declared",
        is_minor_protected: false,
      });
    }

    if (path === "/api/identity/me" && method === "GET") {
      if (state.failMeWith401) {
        return jsonRes(401, { detail: { code: "invalid_session" } });
      }
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: { code: "invalid_session" } });
      return jsonRes(200, {
        user_id: sess.user_id,
        app_id: "messenger",
        capabilities: ["messenger:chat", "messenger:ws"],
        auth_mode: "session",
        age_band: sess.age_band,
        is_minor_protected: false,
        is_verified: true,
        session_id: "sid-1",
        session_version: 1,
        expires_at: Math.floor(Date.now() / 1000) + 3600,
      });
    }

    if (path === "/api/identity/ws-ticket" && method === "POST") {
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: { code: "session_required" } });
      const origin = headers.Origin || headers.origin || body.origin || "";
      if (!origin) return jsonRes(403, { detail: { code: "origin_required" } });
      ticketCounter += 1;
      state.ticketsIssued += 1;
      const ticket = `wst-${ticketCounter}`;
      tickets.set(ticket, { user_id: sess.user_id, origin, used: false });
      return jsonRes(200, {
        ticket,
        expires_at: Math.floor(Date.now() / 1000) + 60,
        session_id: "sid-1",
        app_id: "messenger",
      });
    }

    if (path === "/api/messenger/conversations" && method === "GET") {
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: "unauthorized" });
      const list = [...conversations.values()]
        .filter((c) => c.member_ids.includes(sess.user_id))
        .map((c) => {
          const msgs = messages.get(c.id) ?? [];
          return { ...c, last_message: msgs[msgs.length - 1] ?? null };
        });
      return jsonRes(200, { conversations: list });
    }

    if (path === "/api/messenger/conversations" && method === "POST") {
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: "unauthorized" });
      convCounter += 1;
      const id = `conv-${convCounter}`;
      const members = Array.from(new Set([sess.user_id, ...(body.member_ids || [])]));
      conversations.set(id, {
        id,
        kind: body.kind || "direct",
        title: body.title || "",
        member_ids: members,
      });
      messages.set(id, []);
      return jsonRes(200, { id });
    }

    const msgMatch = path.match(/^\/api\/messenger\/conversations\/([^/]+)\/messages$/);
    if (msgMatch && method === "GET") {
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: "unauthorized" });
      const convId = decodeURIComponent(msgMatch[1]);
      if (!isMember(convId, sess.user_id)) return jsonRes(404, { detail: "not_found" });
      const after = Number(u.searchParams.get("after") || "0");
      const rows = (messages.get(convId) ?? []).filter((m) => m.seq > after);
      return jsonRes(200, { messages: rows });
    }

    if (msgMatch && method === "POST") {
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: "unauthorized" });
      const convId = decodeURIComponent(msgMatch[1]);
      const res = sendBackendMessage(convId, sess.user_id, body.client_msg_id, body.text);
      if (res.error) return jsonRes(res.error.status, { detail: res.error.code });
      sentClientMsgIds.push(body.client_msg_id);
      return jsonRes(200, res.message);
    }

    const editMatch = path.match(/^\/api\/messenger\/conversations\/([^/]+)\/messages\/([^/]+)\/edit$/);
    if (editMatch && method === "POST") {
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: "unauthorized" });
      const convId = decodeURIComponent(editMatch[1]);
      const msgId = decodeURIComponent(editMatch[2]);
      if (!isMember(convId, sess.user_id)) return jsonRes(404, { detail: "not_found" });
      const list = messages.get(convId) ?? [];
      const row = list.find((m) => m.id === msgId && m.sender_id === sess.user_id && !m.deleted);
      if (!row) return jsonRes(404, { detail: "not_found" });
      row.body = String(body.text || "").trim();
      row.edited_at = new Date().toISOString();
      return jsonRes(200, row);
    }

    const delMatch = path.match(/^\/api\/messenger\/conversations\/([^/]+)\/messages\/([^/]+)\/delete$/);
    if (delMatch && method === "POST") {
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: "unauthorized" });
      const convId = decodeURIComponent(delMatch[1]);
      const msgId = decodeURIComponent(delMatch[2]);
      if (!isMember(convId, sess.user_id)) return jsonRes(404, { detail: "not_found" });
      const list = messages.get(convId) ?? [];
      const row = list.find((m) => m.id === msgId && m.sender_id === sess.user_id);
      if (!row) return jsonRes(404, { detail: "not_found" });
      row.body = "";
      row.deleted = true;
      return jsonRes(200, row);
    }

    const rcptMatch = path.match(/^\/api\/messenger\/conversations\/([^/]+)\/receipts$/);
    if (rcptMatch && method === "POST") {
      const sess = requireSession(headers);
      if (!sess) return jsonRes(401, { detail: "unauthorized" });
      const convId = decodeURIComponent(rcptMatch[1]);
      if (!isMember(convId, sess.user_id)) return jsonRes(404, { detail: "not_found" });
      receipts.push({ convId, userId: sess.user_id, ...body });
      return jsonRes(200, { ok: true });
    }

    return jsonRes(404, { detail: "unknown_route" });
  };

  class MockWebSocket {
    constructor(url) {
      this.url = url;
      wsUrls.push(url);
      this.readyState = 0;
      this.onopen = null;
      this.onmessage = null;
      this.onclose = null;
      this.onerror = null;
      state.activeSockets.push(this);

      const u = new URL(url, "http://localhost");
      const ticket = u.searchParams.get("ticket");
      const entry = ticket ? tickets.get(ticket) : null;
      if (!entry || entry.used) {
        setTimeout(() => {
          this.readyState = 3;
          this.onerror?.(new Error("invalid_or_reused_ticket"));
          this.onclose?.({ code: 4001 });
        }, 5);
        return;
      }
      entry.used = true;
      this.userId = entry.user_id;

      setTimeout(() => {
        if (this.readyState !== 0) return;
        this.readyState = 1;
        this.onopen?.({});
        this.onmessage?.({
          data: JSON.stringify({ op: "ready", user_id: this.userId }),
        });
      }, 5);
    }

    send(raw) {
      if (this.readyState !== 1) return;
      const frame = JSON.parse(raw);
      if (frame.op === "subscribe") {
        subscribeFrames.push(frame);
        const convId = frame.conversation_id;
        const lastSeq = Number(frame.last_seq || 0);
        if (!isMember(convId, this.userId)) {
          this.onmessage?.({ data: JSON.stringify({ op: "error", code: "not_found" }) });
          return;
        }
        const rows = (messages.get(convId) ?? []).filter((m) => m.seq > lastSeq);
        this.onmessage?.({ data: JSON.stringify({ op: "replay", messages: rows }) });
      } else if (frame.op === "send") {
        const res = sendBackendMessage(
          frame.conversation_id,
          this.userId,
          frame.client_msg_id,
          frame.text,
        );
        if (res.error) {
          this.onmessage?.({ data: JSON.stringify({ op: "error", code: res.error.code }) });
          return;
        }
        sentClientMsgIds.push(frame.client_msg_id);
        this.onmessage?.({ data: JSON.stringify({ op: "ack", message: res.message }) });
      }
    }

    close(code = 1000) {
      if (this.readyState === 3) return;
      this.readyState = 3;
      this.onclose?.({ code });
    }

    drop() {
      if (this.readyState === 3) return;
      this.readyState = 3;
      this.onclose?.({ code: 1006, reason: "network_drop" });
    }
  }

  function seedServerConversation(convId, memberIds, initialMessages = []) {
    conversations.set(convId, { id: convId, kind: "direct", title: "Private", member_ids: memberIds });
    const rows = initialMessages.map((m) => {
      seqCounter += 1;
      msgCounter += 1;
      return {
        id: `msg-${msgCounter}`,
        conversation_id: convId,
        sender_id: m.senderId,
        client_msg_id: m.clientMsgId,
        seq: seqCounter,
        body: m.text,
        created_at: new Date().toISOString(),
        edited_at: null,
        deleted: false,
      };
    });
    messages.set(convId, rows);
    return rows;
  }

  return {
    state,
    fetchImpl,
    MockWebSocket,
    conversations,
    messages,
    requestedUrls,
    wsUrls,
    subscribeFrames,
    sentClientMsgIds,
    seedServerConversation,
    appendServerMessage(convId, senderId, clientMsgId, text) {
      return sendBackendMessage(convId, senderId, clientMsgId, text);
    },
  };
}

/* ---------- (a) Real mode boots empty ---------- */
{
  const st = getState();
  assert(st.mode === "real", `expected real mode, got ${st.mode}`);
  assert(st.messages.length === 0, `expected empty messages in real mode, got ${st.messages.length}`);
  assert(st.conversations.length === 0, `expected empty conversations in real mode, got ${st.conversations.length}`);
  assert(st.activeChatId === "", `expected empty activeChatId, got ${st.activeChatId}`);
  const serialized = JSON.stringify(st.messages);
  assert(!serialized.includes("Arif Khan"), "seedMessages leaked into real mode");
  const snap = readChatListSnapshot();
  assert(snap.list.length === 0, `expected empty useChatList in real mode, got ${snap.list.length}`);
  assert(snap.activeFallback.contact.name === "Chats", "expected safe fallback chat in empty real mode");
  console.log("PASS (a): real mode boots empty with zero seed data");
}

/* ---------- (b) Demo mode toggle ---------- */
{
  actions.enterDemoMode();
  assert(getState().mode === "demo", "enterDemoMode did not switch mode to demo");
  assert(getState().messages.length > 0, "enterDemoMode did not load seedMessages");
  assert(getState().activeChatId === "arif", "enterDemoMode did not select arif");
  const demoSnap = readChatListSnapshot();
  assert(demoSnap.list.length > 0, "demo chat list is empty");
  assert(
    demoSnap.list.every((c) => c.preview.startsWith("Demo data · ")),
    "every seeded demo chat must be labelled 'Demo data · ...'",
  );

  actions.exitDemoMode();
  assert(getState().mode === "real", "exitDemoMode did not return to real mode");
  assert(getState().messages.length === 0, "exitDemoMode left messages behind");
  assert(getState().conversations.length === 0, "exitDemoMode left conversations behind");
  assert(getState().activeChatId === "", "exitDemoMode did not clear activeChatId");
  assert(readChatListSnapshot().list.length === 0, "exitDemoMode left chats in useChatList");
  console.log("PASS (b): demo mode labels seeded chats and exitDemoMode wipes back to empty real mode");
}

/* ---------- (c) Auth + WS + REST edit/delete + fetchMessages reload ---------- */
const mock = createMockBackend();
const API_BASE = "http://127.0.0.1:18070";

let activeConvId = "";
{
  const session = await actions.signInWithJwt("jwt-user-1", {
    apiBase: API_BASE,
    displayName: "User One",
    origin: "http://localhost:5173",
    fetchImpl: mock.fetchImpl,
    WebSocketImpl: mock.MockWebSocket,
  });
  assert(session.userId === "user-1", `unexpected userId: ${session.userId}`);
  assert(getState().auth.status === "signed_in", "auth status should be signed_in");
  assert(mock.state.ticketsIssued === 1, `expected 1 ws-ticket, got ${mock.state.ticketsIssued}`);

  await waitFor(() => getState().connection === "connected", 2000, "initial WS connected");

  activeConvId = await actions.createConversation({
    memberIds: ["user-2"],
    kind: "direct",
    title: "User Two",
  });
  assert(activeConvId === "conv-1", `unexpected convId ${activeConvId}`);
  assert(getState().activeChatId === activeConvId, "createConversation should open the created chat");
  await waitFor(
    () => mock.subscribeFrames.some((f) => f.conversation_id === activeConvId),
    2000,
    "WS subscribe after createConversation",
  );

  const clientId = actions.sendToChat({ kind: "text", text: "hello live ws" }, activeConvId);
  await waitFor(
    () => getState().messages.some((m) => m.chatId === activeConvId && m.id !== clientId && m.body.kind === "text" && m.body.text === "hello live ws"),
    2000,
    "WS ack replacing optimistic message",
  );
  assert(getState().outbox.length === 0, "outbox should be empty after WS ack");
  const serverMsg = getState().messages.find((m) => m.chatId === activeConvId);
  assert(serverMsg && serverMsg.id.startsWith("msg-"), "expected server message id");

  await actions.editMessage(activeConvId, serverMsg.id, "hello edited");
  const edited = getState().messages.find((m) => m.id === serverMsg.id);
  assert(edited?.body.kind === "text" && edited.body.text === "hello edited", "editMessage did not update store");

  await actions.deleteMessage(activeConvId, serverMsg.id);
  assert(getState().messages.filter((m) => m.chatId === activeConvId).length === 0, "deleteMessage did not remove message");

  const reloaded = await fetchMessages(getState().auth.sessionToken, activeConvId, 0, {
    apiBase: API_BASE,
    fetchImpl: mock.fetchImpl,
  });
  assert(reloaded.length === 1 && reloaded[0].deleted === true, "REST fetchMessages reload should reflect deleted=true");
  await actions.openChat(activeConvId);
  assert(getState().messages.filter((m) => m.chatId === activeConvId).length === 0, "openChat should not resurrect deleted message");
  console.log("PASS (c): signInWithJwt, ws-ticket, WS send/ack, edit, delete, and REST reload passed");
}

/* ---------- (d) Offline outbox & reconnect retry with replay + idempotency ---------- */
{
  // Send a confirmed message so last_seq advances.
  const preId = actions.sendToChat({ kind: "text", text: "before drop" }, activeConvId);
  await waitFor(
    () => getState().messages.some((m) => m.id !== preId && m.body.kind === "text" && m.body.text === "before drop"),
    2000,
    "pre-drop ack",
  );
  const seqBeforeDrop = Math.max(...(mock.messages.get(activeConvId) ?? []).map((m) => m.seq));
  const ticketsBeforeDrop = mock.state.ticketsIssued;
  const subCountBeforeDrop = mock.subscribeFrames.length;

  // Simulate full network drop (WS drops + REST unreachable).
  mock.state.restOffline = true;
  const currentWs = mock.state.activeSockets[mock.state.activeSockets.length - 1];
  currentWs.drop();
  await waitFor(() => getState().connection === "reconnecting", 1000, "reconnecting state");

  const offlineClientId = actions.sendToChat({ kind: "text", text: "offline msg" }, activeConvId);
  // Wait briefly so retryOutbox's failed REST attempt settles cleanly while offline.
  await new Promise((r) => setTimeout(r, 40));
  assert(getState().outbox.length === 1, `expected 1 outbox item, got ${getState().outbox.length}`);
  assert(getState().outbox[0].clientMsgId === offlineClientId, "outbox clientMsgId mismatch");
  assert(getState().outbox[0].status === "queued", `expected queued outbox status, got ${getState().outbox[0].status}`);

  // Peer sends a message on the server while we are offline.
  mock.appendServerMessage(activeConvId, "user-2", "peer-msg-1", "while you were away");

  // Restore network and wait for automatic reconnect + replay + outbox flush.
  mock.state.restOffline = false;
  await waitFor(() => getState().connection === "connected", 4000, "WS reconnect");
  await waitFor(() => getState().outbox.length === 0, 4000, "outbox flush on reconnect");
  await waitFor(
    () =>
      getState().messages.some((m) => m.body.kind === "text" && m.body.text === "while you were away") &&
      getState().messages.some((m) => m.id !== offlineClientId && m.body.kind === "text" && m.body.text === "offline msg"),
    4000,
    "replay + offline msg ack",
  );

  assert(
    mock.state.ticketsIssued > ticketsBeforeDrop,
    "reconnect must mint a fresh single-use ws-ticket",
  );
  const replaySub = mock.subscribeFrames.slice(subCountBeforeDrop).find((f) => f.conversation_id === activeConvId);
  assert(
    replaySub && replaySub.last_seq === seqBeforeDrop,
    `expected reconnect subscribe last_seq=${seqBeforeDrop}, got ${replaySub?.last_seq}`,
  );

  // Re-sending the exact same client_msg_id via REST must remain idempotent with zero duplicates.
  const countBeforeDup = (mock.messages.get(activeConvId) ?? []).filter(
    (m) => !m.deleted && m.body === "offline msg",
  ).length;
  await sendMessageRest(getState().auth.sessionToken, activeConvId, offlineClientId, "offline msg", {
    apiBase: API_BASE,
    fetchImpl: mock.fetchImpl,
  });
  const countAfterDup = (mock.messages.get(activeConvId) ?? []).filter(
    (m) => !m.deleted && m.body === "offline msg",
  ).length;
  assert(countBeforeDup === 1 && countAfterDup === 1, "idempotent client_msg_id produced duplicate rows");
  console.log("PASS (d): offline outbox, fresh ws-ticket reconnect, replay from last_seq, and idempotent flush passed");
}

/* ---------- (e) Non-member 404 denial ---------- */
{
  mock.seedServerConversation("unauth-conv", ["user-2", "user-3"], [
    { senderId: "user-2", clientMsgId: "secret-1", text: "top secret" },
  ]);
  await actions.openChat("unauth-conv");
  assert(getState().lastError === "not_found", `expected lastError==='not_found', got ${getState().lastError}`);
  assert(
    getState().messages.filter((m) => m.chatId === "unauth-conv").length === 0,
    "unauthorized messages must never enter store",
  );
  assert(
    !JSON.stringify(getState().messages).includes("top secret"),
    "unauthorized message text leaked into store",
  );
  console.log("PASS (e): non-member 404 sets lastError='not_found' with zero unauthorized messages");
}

/* ---------- (f) D13 HTTPS tunnel apiBase routing ---------- */
{
  actions.signOut();
  const TUNNEL_BASE = "https://messenger-tunnel.example.test";
  assert(
    resolveWsUrl(TUNNEL_BASE) === "wss://messenger-tunnel.example.test/api/messenger/ws",
    `expected wss:// tunnel url, got ${resolveWsUrl(TUNNEL_BASE)}`,
  );

  const reqStart = mock.requestedUrls.length;
  const wsStart = mock.wsUrls.length;
  await actions.signInWithJwt("jwt-user-1", {
    apiBase: TUNNEL_BASE,
    displayName: "Tunnel User",
    origin: TUNNEL_BASE,
    fetchImpl: mock.fetchImpl,
    WebSocketImpl: mock.MockWebSocket,
  });
  await waitFor(() => getState().connection === "connected", 2000, "tunnel WS connected");

  const tunnelReqs = mock.requestedUrls.slice(reqStart);
  const tunnelWsUrls = mock.wsUrls.slice(wsStart);
  assert(
    tunnelReqs.some((u) => u.startsWith("https://messenger-tunnel.example.test/api/identity/")),
    `expected identity REST call routed to tunnel base, got ${JSON.stringify(tunnelReqs)}`,
  );
  assert(
    tunnelWsUrls.some((u) => /^wss:\/\/messenger-tunnel\.example\.test\/api\/messenger\/ws\?ticket=/.test(u)),
    `expected WS routed to wss://messenger-tunnel.example.test/api/messenger/ws?ticket=..., got ${JSON.stringify(tunnelWsUrls)}`,
  );
  console.log("PASS (f): HTTPS tunnel apiBase routes REST to https://.../api/* and WS to wss://.../api/messenger/ws?ticket=...");
}

/* ---------- (g) restoreSession() re-hydrates & clears expired 401 ---------- */
{
  // Current session is persisted in sessionStorage; simulate reload by calling restoreSession().
  const restored = await actions.restoreSession({
    fetchImpl: mock.fetchImpl,
    WebSocketImpl: mock.MockWebSocket,
  });
  assert(restored === true, "restoreSession should succeed for valid persisted session");
  assert(getState().auth.status === "signed_in", "restoreSession should set signed_in");

  // Simulate expired/invalid 401 on /api/identity/me.
  mock.state.failMeWith401 = true;
  const expired = await actions.restoreSession({
    fetchImpl: mock.fetchImpl,
    WebSocketImpl: mock.MockWebSocket,
  });
  assert(expired === false, "restoreSession should return false on 401");
  assert(getState().auth.status === "signed_out", "expired restoreSession should reset to signed_out");
  assert(globalThis.sessionStorage.getItem("messenger.session") === null, "expired session must be cleared");
  console.log("PASS (g): restoreSession re-hydrates valid session and clears 401 session cleanly");
}

/* ---------- (h) Local /demo/ asset paths & zero hotlinks ---------- */
{
  const isLocalDemoAsset = (v) =>
    typeof v === "string" &&
    v.length > 0 &&
    v.startsWith("/demo/") &&
    !/^https?:\/\//i.test(v);

  const sceneIds = [
    "photo-1512453979798-5ea266f8880c",
    "photo-1507525428034-b723cf961d3e",
    "photo-1511895426328-dc8714191300",
    "photo-1542751371-adc38448a05e",
    "photo-1522202176988-66273c2fd55f",
    "photo-1436491865332-7a61a109cc05",
    "photo-1537996194471-e657df975ab4",
    "photo-1498837167922-ddd27525d352",
    "photo-1486406146926-c627a92ad1ab",
    "photo-1495616811223-4d98c6e9c869",
    "photo-1555400038-63f5ba517a47",
    "photo-1504674900247-0877df9cc836",
    "photo-1511512578047-dfb367046420",
    "photo-1519046904884-53103b34b206",
    "photo-1434030216411-0b793f4b4173",
    "photo-1556909114-f6e7ad7d3136",
    "photo-1586724237569-f3d0c1dee8c6",
    "photo-1503177119275-0aa32b3a9368",
    "photo-1513635269975-59663e0ac1ad",
    "photo-1497366754035-f200968a6e72",
    "photo-1516321318423-f06f85e504b3",
    "photo-1519389950473-47ba0277781c",
  ];
  for (const id of sceneIds) {
    const out = img(id);
    assert(isLocalDemoAsset(out) && out === `/demo/scenes/${id}.jpg`, `unexpected img("${id}"): ${out}`);
  }
  const fallbackImg = img("unknown-scene-id");
  assert(
    isLocalDemoAsset(fallbackImg) && fallbackImg === "/demo/scenes/photo-1512453979798-5ea266f8880c.jpg",
    `unexpected fallback img(): ${fallbackImg}`,
  );

  for (const n of [-3, 0, 1, 9, 10, 14, 2.7]) {
    const out = avatar(n);
    assert(isLocalDemoAsset(out) && /^\/demo\/avatars\/avatar-(?:0[1-9]|10)\.jpg$/.test(out), `unexpected avatar(${n}): ${out}`);
  }

  assert(isLocalDemoAsset(ORB) && ORB === "/demo/messenger-orb.svg", `unexpected ORB: ${ORB}`);
  console.log("PASS (h): img(), avatar(), and ORB return local /demo/ asset paths with zero hotlinks");
}

actions.signOut();
console.log("ALL STORE-WIRING CHECKS PASSED");
