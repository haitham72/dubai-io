// Shared chrome for the static iOS samples: status bar + home indicator (only inside preview frames),
// the 4-tab bar (when <body data-tab="…">), then Lucide icons.
(function () {
  const framed = window.self !== window.top || new URLSearchParams(location.search).has("frame");
  if (framed) document.documentElement.classList.add("framed");
  // a page shown behind a sheet keeps its layout but drops the system chrome (the sheet page draws it)
  if (new URLSearchParams(location.search).has("behind")) document.documentElement.classList.add("behind-page");

  const screen = document.querySelector(".screen");
  screen.insertAdjacentHTML(
    "afterbegin",
    '<div class="status"><span>9:41</span><span class="status-icons">' +
      '<i data-lucide="signal"></i><i data-lucide="wifi"></i><i data-lucide="battery-full"></i></span></div>'
  );

  const current = document.body.dataset.tab;
  if (current) {
    const tabs = [
      ["chats", "Chats", "message-circle"],
      ["ai", "Mirsal AI", "sparkles"],
      ["apps", "Apps", "layout-grid"],
      ["settings", "Settings", "settings"],
    ];
    screen.insertAdjacentHTML(
      "beforeend",
      '<nav class="tabbar">' +
        tabs
          .map(([id, label, icon]) =>
            `<a class="tab${id === current ? " on" : ""}" href="${id}.html"><i data-lucide="${icon}"></i>${label}</a>`)
          .join("") +
        "</nav>"
    );
  }

  screen.insertAdjacentHTML("beforeend", '<div class="home"></div>');
  lucide.createIcons({ attrs: { "stroke-width": 1.75 } });
  // conversations open at the newest message
  document.querySelectorAll(".thread").forEach((t) => (t.scrollTop = t.scrollHeight));
})();
