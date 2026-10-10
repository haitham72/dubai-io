// Crisp Collar mini-app. Sends only typed item ids + quantities; the host rebuilds the total.
(() => {
  const ITEMS = [
    { id: "shirt_press", name: "Shirt, hand pressed", note: "collar and cuffs by hand", price: 8 },
    { id: "trouser_press", name: "Trousers, hand pressed", note: "hung, not folded", price: 9 },
    { id: "thobe_press", name: "Thobe, pressed", note: "full steam finish", price: 14 }
  ];
  const qty = {};
  ITEMS.forEach((i) => (qty[i.id] = 0));
  let sent = false;

  function draw() {
    document.getElementById("list").innerHTML = ITEMS.map((i) =>
      `<li><div><b>${i.name}</b><span>${i.note}</span></div>
       <div class="pick"><button data-id="${i.id}" data-d="-1" aria-label="Fewer">−</button><em>${qty[i.id]}</em><button data-id="${i.id}" data-d="1" aria-label="More">+</button></div>
       <div class="price">AED ${i.price}</div></li>`).join("");
    document.querySelectorAll("[data-id]").forEach((b) => (b.onclick = () => {
      qty[b.dataset.id] = Math.max(0, Math.min(20, qty[b.dataset.id] + Number(b.dataset.d)));
      draw();
    }));
    const n = ITEMS.reduce((s, i) => s + qty[i.id], 0);
    document.getElementById("count").textContent = n + (n === 1 ? " item" : " items");
    document.getElementById("go").disabled = n === 0 || sent;
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
