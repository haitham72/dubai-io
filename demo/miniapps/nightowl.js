// Night Owl mini-app. Sends only typed item ids + quantities (order.request); the host rebuilds the total.
(() => {
  const ITEMS = [
    { id: "paracetamol", name: "Paracetamol 500mg x24", price: 10 },
    { id: "throat_lozenges", name: "Throat lozenges x16", price: 14 },
    { id: "antacid", name: "Antacid tablets x20", price: 17 }
  ];
  const qty = {};
  ITEMS.forEach((i) => (qty[i.id] = 0));
  let sent = false;

  function draw() {
    document.getElementById("tiles").innerHTML = ITEMS.map((i) =>
      `<div class="tile"><div><b>${i.name}</b><span>AED ${i.price}</span></div>
       <div class="q"><button data-id="${i.id}" data-d="-1" aria-label="Fewer">−</button>${qty[i.id]}<button data-id="${i.id}" data-d="1" aria-label="More">+</button></div></div>`).join("");
    document.querySelectorAll("[data-id]").forEach((b) => (b.onclick = () => {
      qty[b.dataset.id] = Math.max(0, Math.min(20, qty[b.dataset.id] + Number(b.dataset.d)));
      draw();
    }));
    document.getElementById("go").disabled = ITEMS.every((i) => qty[i.id] === 0) || sent;
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
