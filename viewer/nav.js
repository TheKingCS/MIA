// MIA Homestead — shared viewer nav bar
// Injected at the top of every viewer/*.html page so the three pages
// (digital twin, dashboard, journal) are reachable from one another —
// each page previously had no way to get to the others except a typed URL.
(function () {
  const LINKS = [
    { href: "dashboard.html", label: "Dashboard" },
    { href: "digital_twin.html", label: "Digital Twin" },
    { href: "journal.html", label: "Journal" },
  ];

  const style = document.createElement("style");
  style.textContent = `
    .mh-nav {
      display: flex;
      gap: 4px;
      margin-bottom: 20px;
      font-family: 'IBM Plex Mono', ui-monospace, 'SF Mono', Consolas, monospace;
      pointer-events: auto;
    }
    .mh-nav a {
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-dim, #5C7180);
      text-decoration: none;
      padding: 7px 14px;
      border: 1px solid var(--line, #2A3B4A);
      border-radius: 2px;
      background: var(--panel, rgba(16, 22, 29, 0.9));
    }
    .mh-nav a:hover { color: var(--text, #C4D3DC); }
    .mh-nav a.active {
      color: var(--accent, #4FD1C5);
      border-color: rgba(79, 209, 197, 0.4);
    }
  `;
  document.head.appendChild(style);

  const current = location.pathname.split("/").pop() || "dashboard.html";
  const nav = document.createElement("div");
  nav.className = "mh-nav";
  for (const link of LINKS) {
    const a = document.createElement("a");
    a.href = link.href;
    a.textContent = link.label;
    if (link.href === current) a.classList.add("active");
    nav.appendChild(a);
  }

  const mount = document.getElementById("mh-nav-mount") || document.body;
  mount.insertBefore(nav, mount.firstChild);
})();
