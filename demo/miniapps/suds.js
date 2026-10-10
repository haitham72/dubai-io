// Suds & Co. mini-app. Sends only typed item ids + quantities; the host rebuilds the total.
(() => {
  const ITEMS = [
    { id: "shirt_press", e: "👔", name: "Shirt, pressed", note: "ready on a hanger", price: 6 },
    { id: "shirt_wash_press", e: "🧺", name: "Shirt, washed and pressed", note: "wash + press", price: 10 },
    { id: "trouser_press", e: "👖", name: "Trousers, pressed", note: "sharp crease", price: 8 }
  ];
  const qty = {};
  ITEMS.forEach((i) => (qty[i.id] = 0));
  let sent = false;

  function draw() {
    document.getElementById("grid").innerHTML = ITEMS.map((i) =>
      `<div class="item"><div class="e">${i.e}</div><div><b>${i.name}</b><span>AED ${i.price} · ${i.note}</span></div>
       <div class="q"><button data-id="${i.id}" data-d="-1" aria-label="Fewer">−</button><b>${qty[i.id]}</b><button data-id="${i.id}" data-d="1" aria-label="More">+</button></div></div>`).join("");
    document.querySelectorAll("[data-id]").forEach((b) => (b.onclick = () => {
      qty[b.dataset.id] = Math.max(0, Math.min(20, qty[b.dataset.id] + Number(b.dataset.d)));
      draw();
    }));
    const t = ITEMS.reduce((s, i) => s + i.price * qty[i.id], 0);
    document.getElementById("total").textContent = "AED " + t;
    document.getElementById("go").disabled = t === 0 || sent;
  }

  document.getElementById("go").onclick = () => {
    if (sent) return;
    sent = true;
    Bridge.send("order.request", { items: ITEMS.filter((i) => qty[i.id] > 0).map((i) => ({ id: i.id, qty: qty[i.id] })) });
    setTimeout(() => { sent = false; draw(); }, 2000);
    draw();
  };

  // Shows what the sandbox blocks: network, storage, cookies, top navigation, and out-of-scope bridge calls.
  document.getElementById("dev").onclick = async () => {
    const r = {};
    try { await fetch("https://example.com"); r.network = "ALLOWED"; } catch (e) { r.network = "blocked"; }
    try { localStorage.setItem("x", "1"); r.storage = "ALLOWED"; } catch (e) { r.storage = "blocked"; }
    try { document.cookie = "a=1"; r.cookies = document.cookie ? "ALLOWED" : "blocked"; } catch (e) { r.cookies = "blocked"; }
    try { top.location.href = "https://example.com"; r.top_navigation = "ALLOWED"; } catch (e) { r.top_navigation = "blocked"; }
    Bridge.send("payment.charge", { amount: 999 });
    const pre = document.getElementById("diag");
    pre.hidden = false;
    pre.textContent = JSON.stringify(r, null, 2) + "\npayment.charge sent to host (it is not in this app's scopes; see Under the hood > Raw log)";
  };

  draw();
  Bridge.send("app.ready", {});
})();
