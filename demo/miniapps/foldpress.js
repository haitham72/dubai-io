// Fold & Press mini-app. Shows its own catalog and a running total for the customer's convenience.
// It sends ONLY typed item ids + quantities. The host rebuilds the total from the approved price list.
(() => {
  const ITEMS = [
    { id: "shirt_press", name: "Shirt, pressed", note: "on a hanger", price: 5 },
    { id: "trouser_press", name: "Trousers, pressed", note: "creased and hung", price: 7 },
    { id: "suit_jacket", name: "Suit jacket, pressed", note: "steam finish", price: 15 }
  ];
  const qty = {};
  ITEMS.forEach((i) => (qty[i.id] = 0));
  let sent = false;

  function draw() {
    document.getElementById("items").innerHTML = ITEMS.map((i) =>
      `<div class="box"><div><b>${i.name}</b><small>AED ${i.price} each · ${i.note}</small></div>
       <div class="step"><button data-id="${i.id}" data-d="-1" aria-label="Fewer">−</button><b>${qty[i.id]}</b><button data-id="${i.id}" data-d="1" aria-label="More">+</button></div></div>`).join("");
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
    const items = ITEMS.filter((i) => qty[i.id] > 0).map((i) => ({ id: i.id, qty: qty[i.id] }));
    Bridge.send("order.request", { items });
    setTimeout(() => { sent = false; draw(); }, 2000);
    draw();
  };

  draw();
  Bridge.send("app.ready", {});
})();
