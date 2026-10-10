// Bloom Care mini-app. Sends only a typed item id + quantity (order.request); the host rebuilds the total.
(() => {
  const KITS = [
    { id: "jetlag_kit", em: "🌙", name: "Jet-lag kit", d: "Eye mask, electrolytes, moisturiser", price: 79 },
    { id: "sun_kit", em: "☀️", name: "Sun care kit", d: "SPF 50, after-sun gel, lip balm", price: 95 },
    { id: "baby_kit", em: "🍼", name: "Baby travel kit", d: "Wipes, nappy cream, ORS for kids", price: 68 }
  ];
  let pick = null, sent = false;

  function draw() {
    document.getElementById("kits").innerHTML = KITS.map((k, i) =>
      `<div class="kit ${pick === i ? "on" : ""}" data-i="${i}"><div class="em">${k.em}</div><div><b>${k.name}</b><span>${k.d}</span></div><div class="p">AED ${k.price}</div></div>`).join("");
    document.querySelectorAll("[data-i]").forEach((el) => (el.onclick = () => { pick = Number(el.dataset.i); draw(); }));
    document.getElementById("go").disabled = pick === null || sent;
  }

  document.getElementById("go").onclick = () => {
    if (sent || pick === null) return;
    sent = true;
    Bridge.send("order.request", { items: [{ id: KITS[pick].id, qty: 1 }] });
    setTimeout(() => { sent = false; draw(); }, 2000);
    draw();
  };

  draw();
  Bridge.send("app.ready", {});
})();
