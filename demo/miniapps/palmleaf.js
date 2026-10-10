// Palm Leaf Pharmacy mini-app. Sends only typed item ids + quantities (order.request); the host rebuilds the total.
(() => {
  const ITEMS = [
    { id: "paracetamol", e: "💊", name: "Paracetamol 500mg x24", price: 9 },
    { id: "ors", e: "🥤", name: "Oral rehydration salts x10", price: 18 },
    { id: "sunscreen", e: "🧴", name: "Sunscreen SPF 50", price: 59 },
    { id: "nasal_spray", e: "👃", name: "Saline nasal spray", price: 22 },
    { id: "plasters", e: "🩹", name: "Blister plasters", price: 16 },
    { id: "lip_balm", e: "💋", name: "Lip balm", price: 12 }
  ];
  const qty = {};
  ITEMS.forEach((i) => (qty[i.id] = 0));
  let sent = false;

  function draw() {
    document.getElementById("grid").innerHTML = ITEMS.map((i) =>
      `<div class="item"><div class="e">${i.e}</div><b>${i.name}</b><span>AED ${i.price}</span>
       <div class="q"><button data-id="${i.id}" data-d="-1" aria-label="Fewer">−</button>${qty[i.id]}<button data-id="${i.id}" data-d="1" aria-label="More">+</button></div></div>`).join("");
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

  draw();
  Bridge.send("app.ready", {});
})();
