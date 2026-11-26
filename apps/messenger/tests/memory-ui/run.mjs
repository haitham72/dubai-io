// Node tests for the Messenger "Save to memory" approval card, flow and client. Synthetic data only.
import assert from "node:assert/strict";
const { createApprovalFlow, createMemoryClient, MemoryApiError, ApprovalCard, renderToStaticMarkup, createElement } = await import("./bundle.mjs");

const preview = (over = {}) => ({
  offerable: true, can_save_now: true, blockers: [], provenance: "user_supplied", as_of: "2026-11-24T10:00:00Z",
  fields: [
    { name: "Message text", value: "Kiosk panels are due Friday." },
    { name: "Written by", value: "You" },
    { name: "Sent at", value: "2026-11-24T10:00:00Z" },
    { name: "Scope", value: "This conversation only (not shared with other apps)" },
  ], ...over,
});
const fakeClient = (over = {}) => {
  const calls = { preview: 0, save: 0, mode: 0 };
  return {
    calls,
    preview: async () => { calls.preview++; return preview(); },
    save: async () => { calls.save++; return { saved: true, status: "applied", held_back: false, record_id: "mgmsg:1", as_of: "T" }; },
    state: async () => ({ enabled: true, as_of: "T", items: [] }),
    setConsent: async () => ({ enabled: false, as_of: "T" }),
    setChatMode: async () => { calls.mode++; return { mode: "save" }; },
    setLowered: async () => ({ records: 1, lowered: true, as_of: "T" }),
    ...over,
  };
};
const html = (state) => renderToStaticMarkup(createElement(ApprovalCard, { state, onApprove() {}, onCancel() {}, onAllow() {} }));

// approval card lists exactly the fields the server previewed
{
  const c = fakeClient(); const f = createApprovalFlow(c, "c1", "m1");
  await f.open();
  const h = html(f.get());
  for (const n of ["Message text", "Written by", "Sent at", "Scope"]) assert.ok(h.includes(n), `field ${n} listed`);
  assert.ok(h.includes("Kiosk panels are due Friday.") && h.includes("user_supplied"));
  assert.equal(c.calls.save, 0, "opening the card sends nothing");
}
// cancel = nothing sent
{
  const c = fakeClient(); const f = createApprovalFlow(c, "c1", "m1");
  await f.open(); f.cancel(); await f.approve();
  assert.equal(f.get().phase, "closed"); assert.equal(c.calls.save, 0);
}
// approve = exactly one call, even if tapped twice; status shown is the server's
{
  const c = fakeClient(); const f = createApprovalFlow(c, "c1", "m1");
  await f.open(); await Promise.all([f.approve(), f.approve()]); await f.approve();
  assert.equal(c.calls.save, 1); assert.equal(f.get().phase, "done");
  assert.ok(html(f.get()).includes("Server status: applied"));
}
// held back by the server: honest, no success state
{
  const c = fakeClient({ save: async () => ({ saved: false, status: "quarantined", held_back: true, record_id: "x", as_of: "T" }) });
  const f = createApprovalFlow(c, "c1", "m1"); await f.open(); await f.approve();
  assert.equal(f.get().phase, "error"); assert.ok(f.get().error.includes("Held back"));
  assert.ok(!html(f.get()).includes("Server status"));
}
// sensitive: never offered, no fields, no approve button
{
  const c = fakeClient({ preview: async () => preview({ offerable: false, can_save_now: false, fields: [], blockers: [{ code: "held_back", message: "Held back: this looks sensitive, so it is never offered for memory." }] }) });
  const f = createApprovalFlow(c, "c1", "m1"); await f.open(); await f.approve();
  const h = html(f.get());
  assert.ok(h.includes("Held back") && !h.includes("Approve and save") && !h.includes("These fields"));
  assert.equal(c.calls.save, 0);
}
// blocked (memory off for chat): approve refused client-side too, and Allow is an explicit separate tap
{
  const c = fakeClient({ preview: async () => preview({ can_save_now: false, blockers: [{ code: "ai_default_off", message: "Memory is off for this chat." }] }) });
  const f = createApprovalFlow(c, "c1", "m1"); await f.open(); await f.approve();
  assert.equal(c.calls.save, 0); assert.ok(html(f.get()).includes("Allow memory in this chat"));
  await f.allowInThisChat(); assert.equal(c.calls.mode, 1);
}
// server error on save keeps the card in error with the server message
{
  const c = fakeClient({ save: async () => { throw new MemoryApiError(403, "group_off", "Not every member has memory on."); } });
  const f = createApprovalFlow(c, "c1", "m1"); await f.open(); await f.approve();
  assert.equal(f.get().phase, "error"); assert.equal(f.get().error, "Not every member has memory on.");
}
// client: Forget happy + error path against a fake fetch; session header only, base joined
{
  const seen = [];
  const ok = createMemoryClient("tok", { apiBase: "http://x", fetchImpl: async (u, i) => { seen.push([u, i]); return new Response(JSON.stringify({ records: 2, lowered: true, as_of: "T" }), { status: 200 }); } });
  const r = await ok.setLowered("mgmsg:1", true);
  assert.equal(r.records, 2);
  assert.equal(seen[0][0], "http://x/api/messenger/memory/lower"); assert.equal(seen[0][1].headers["X-App-Session"], "tok");
  assert.deepEqual(JSON.parse(seen[0][1].body), { record_id: "mgmsg:1", lower: true });
  const bad = createMemoryClient("tok", { apiBase: "http://x", fetchImpl: async () => new Response(JSON.stringify({ detail: { code: "x", message: "nope" } }), { status: 403 }) });
  await assert.rejects(() => bad.setLowered("m", true), (e) => e instanceof MemoryApiError && e.message === "nope" && e.status === 403);
  const down = createMemoryClient("tok", { apiBase: "http://x", fetchImpl: async () => { throw new TypeError("fail"); } });
  await assert.rejects(() => down.state(), /unavailable/);
  // consent switch and save carry only what is intended
  const log = [];
  const c2 = createMemoryClient("tok", { apiBase: "", fetchImpl: async (u, i) => { log.push([u, i.method, i.body]); return new Response("{}", { status: 200 }); } });
  await c2.setConsent(false); await c2.save("c 1", "m1");
  assert.deepEqual(log[0], ["/api/messenger/memory/consent", "PUT", '{"enabled":false}']);
  assert.deepEqual(log[1], ["/api/messenger/conversations/c%201/messages/m1/memory", "POST", '{"confirmed":true}']);
}
console.log("MEMORY-UI OK (10 checks)");
