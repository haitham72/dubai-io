// The one Dubai-io mini-app template. A shop that joins from a price-list photo gets this page
// filled from its extracted catalog (passed by the host in ?cfg=...). Merchant-authored HTML is out of scope.
(() => {
  const c = Bridge.cfg() || { name: "Shop", line: "", color: "#0A9CC2", logo: "?", items: [] };
  const ITEMS = Array.isArray(c.items) ? c.items : [];
  const qty = {};
  ITEMS.forEach((i) => (qty[i.id] = 0));
  let sent = false;

  document.documentElement.style.setProperty("--brand", /^#[0-9A-Fa-f]{6}$/.test(c.color) ? c.color : "#0A9CC2");
  document.title = String(c.name);
  document.getElementById("name").textContent = String(c.name);      // textContent: never parsed as HTML
  document.getElementById("line").textContent = String(c.line || "");
  document.getElementById("logo").textContent = String(c.logo || "");

  function draw() {
    const list = document.getElementById("list");
    list.textContent = "";
    ITEMS.forEach((i) => {
      const row = document.createElement("div");
      row.className = "row";
      const left = document.createElement("div");
      const nm = document.createElement("b"); nm.textContent = String(i.name);
      const pr = document.createElement("span"); pr.textContent = "AED " + Number(i.price);
      left.append(nm, pr);
      const q = document.createElement("div"); q.className = "q";
      const minus = document.createElement("button"); minus.textContent = "−"; minus.setAttribute("aria-label", "Fewer");
      const n = document.createElement("b"); n.textContent = String(qty[i.id]);
      const plus = document.createElement("button"); plus.textContent = "+"; plus.setAttribute("aria-label", "More");
      minus.onclick = () => { qty[i.id] = Math.max(0, qty[i.id] - 1); draw(); };
      plus.onclick = () => { qty[i.id] = Math.min(20, qty[i.id] + 1); draw(); };
      q.append(minus, n, plus);
      row.append(left, q);
      list.append(row);
    });
    const t = ITEMS.reduce((s, i) => s + Number(i.price) * qty[i.id], 0);
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
