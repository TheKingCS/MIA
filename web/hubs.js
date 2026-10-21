/*
 * hubs.js — My Hero's Path, World and System (claude, 2026-10-21, DEC-0044).
 * The places that replace the long app list: each shows what its apps
 * already know (core/web_hubs.py), and an app is opened only for detail.
 * Which hub is the page's data-app. Formatting only.
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const hub = document.body.dataset.app;

  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const card = (c, cls) => el("a", { class: "hub-card " + (cls || ""), href: c.href || "#" },
    el("strong", {}, el("span", { "aria-hidden": "true" }, c.icon || ""), c.name), c.line ? el("small", {}, c.line) : null);
  const icon = (id, fallback) => (window.MIAIcons && MIAIcons.svg(id)) || fallback || "";

  // ------------------------------------------------------------ My Hero's Path
  function path(p) {
    const level = el("div", { class: "glass home-level page-level" });
    MIAShell.levelCard(level, p.me);
    return [
      p.me ? level : null,
      section("Active Missions" + (p.active_count ? " · " + p.active_count : ""), el("a", { class: "btn btn-ghost btn-small", href: "missions.html" }, "All Missions"),
        p.missions.length ? el("ul", { class: "pres-list" }, p.missions.map((m) => el("li", { class: "pres-item progress" },
          el("span", { class: "pres-kind" }, "next"), el("span", { class: "what" }, el("a", { href: m.href }, m.title), el("small", {}, m.why)), null)))
          : el("p", { class: "empty" }, "No active missions. Tell MIA what you're working toward, or start one in Missions.")),
      section("Growing This Week", el("a", { class: "btn btn-ghost btn-small", href: "skills.html" }, "All Skills"),
        p.focus_skill ? el("p", {}, "Focus: ", el("strong", {}, p.focus_skill.icon + " " + p.focus_skill.name), " · " + p.focus_skill.to_next + " XP to the next level") : null,
        p.growing.length ? el("div", { class: "hub-grid" }, p.growing.map((s) => card({ name: s.name, icon: s.icon, line: "lvl " + s.level + " · +" + s.this_week + " XP this week", href: "skills.html" })))
          : el("p", { class: "dim" }, "No skill XP this week yet: everything you do in MIA trains one.")),
      p.wins.length ? section("Recent Wins", null, el("ul", { class: "pres-list" }, p.wins.map((w) =>
        el("li", { class: "pres-item progress" }, el("span", { class: "pres-kind" }, "win"), el("span", { class: "what" }, w.summary || w.title || ""), null)))) : null,
      section("The Path", null, el("div", { class: "hub-grid" }, p.screens.map((s) => card(s)))),
    ];
  }

  // ------------------------------------------------------------ World
  async function star(c) {
    await act({ kind: "app.favorite", params: { module_id: c.id, favorite: !c.favorite } });
  }
  function world(w) {
    return w.areas.map((area) => section(area.name + (area.needs ? " · " + area.needs + " need you" : ""), null,
      el("div", { class: "hub-grid" }, area.cards.map((c) => {
        const a = card({ name: c.name, icon: icon(c.id, c.icon), line: c.line + (c.on_web ? "" : " · desktop for now"), href: c.href || "apps.html" },
          (c.needs ? "needs" : "") + (c.on_web ? "" : " off"));
        const pin = el("button", { type: "button", class: "btn btn-ghost btn-small hub-star", "aria-pressed": String(c.favorite),
          "aria-label": (c.favorite ? "Unpin " : "Pin ") + c.name, title: c.favorite ? "Pinned to the sidebar" : "Pin to the sidebar",
          onclick: (e) => { e.preventDefault(); star(c); } }, c.favorite ? "★" : "☆");
        return el("div", { class: "hub-cell" }, a, pin);
      }))));
  }

  // ------------------------------------------------------------ System
  function system(s) {
    const c = s.capabilities;
    return [
      section("The Model", null, el("p", {}, s.model.line)),
      section("What MIA Can Do", el("a", { class: "btn btn-ghost btn-small", href: "apps.html" }, "Every App"),
        el("p", {}, c.apps + " apps (" + c.web + " on the web and phone) and " + c.tools + " things she can look up or do when you ask."),
        c.desktop_only.length ? el("p", { class: "dim" }, "Desktop only for now: " + c.desktop_only.join(", ") + ".") : null,
        el("p", { class: "dim" }, "Ask “What can you do?” or “Can you…?” in Conversation: she answers from this same list.")),
      section("Connections", null, el("ul", { class: "pres-list" }, s.connections.map((x) => el("li", { class: "pres-item" },
        el("span", { class: "pres-kind" }, "link"), el("span", { class: "what" }, el("a", { href: x.href }, x.name), el("small", {}, x.state)), null)))),
      section("Advanced", null, el("div", { class: "hub-grid" }, s.screens.map((x) => card(x)))),
    ];
  }

  MIAShell.start(async () => {
    const data = await (hub === "path" ? MIA.path() : hub === "world" ? MIA.world() : MIA.system());
    const view = hub === "path" ? path(data) : hub === "world" ? world(data) : system(data);
    $("panel").replaceChildren(...[].concat(view).filter(Boolean));
  });
})();
