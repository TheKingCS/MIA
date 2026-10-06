/*
 * apps.js — the Apps page (claude, 2026-10-06, DEC-0017). Renders MIA.apps();
 * filtering is only matching the words typed against what the engine sent.
 */
(function () {
  "use strict";
  const { el, act, talk } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let data = null;
  let filter = "all"; // all | web | ask
  let mode = "tiles"; // tiles (the concept's grid) | manage (every app in detail, show/hide)
  let view = location.hash === "#favorites" ? "favorites" : "all"; // the grid: every app, or only your favorites
  // The concept's tile colors (presentation only).
  const COLORS = { web_home: "74,222,128", dashboard: "74,222,128", greenhouse: "74,222,128", garage: "251,146,60",
    kitchen: "248,113,113", workout: "96,165,250", real_estate: "45,212,191", budget: "167,139,250", missions: "251,191,36",
    skills: "192,132,252", maintenance: "251,146,60", property: "45,212,191", assistant: "74,222,128" };
  const askHref = (app) => "assistant.html?draft=" + encodeURIComponent(app.ask || ("About " + app.name + ": "));

  const star = (app) => el("button", {
    type: "button", class: "tile-star" + (app.favorite ? " on" : ""), "aria-pressed": String(app.favorite),
    "aria-label": (app.favorite ? "Remove " : "Add ") + app.name + (app.favorite ? " from" : " to") + " favorites",
    onclick: (e) => { e.preventDefault(); e.stopPropagation(); act({ kind: "app.favorite", params: { module_id: app.id, favorite: !app.favorite } }); },
  }, app.favorite ? "★" : "☆");

  function tile(app) {
    return el("a", { class: "app-tile", href: app.on_web ? app.page : askHref(app), "data-id": app.id,
      style: "--tile-rgb:" + (COLORS[app.id] || "120,160,140") },
    star(app),
    el("span", { class: "tile-icon", "aria-hidden": "true" }, app.icon),
    el("span", { class: "tile-name" }, app.name),
    el("span", { class: "tile-tag" }, app.on_web ? app.tagline : "Ask MIA"));
  }

  function card(app) {
    const tools = app.tools.length
      ? el("details", { class: "app-tools" },
        el("summary", {}, "What MIA can do here (" + app.tools.length + ")"),
        el("ul", {}, app.tools.map((t) => el("li", { title: t.detail }, t.does))))
      : null;
    const open = app.on_web
      ? el("a", { class: "btn btn-green", href: app.page }, "Open")
      : el("a", { class: "btn btn-amber", href: askHref(app) }, "Ask MIA");
    const toggle = app.can_hide
      ? el("button", {
        type: "button", class: "btn btn-ghost",
        onclick: () => act({ kind: "app.visibility", params: { module_id: app.id, visible: !app.shown } }),
      }, app.shown ? "Hide" : "Show")
      : null;
    return el("article", { class: "glass app-card" + (app.shown ? "" : " is-hidden"), "data-id": app.id },
      el("div", { class: "app-head" },
        el("span", { class: "app-icon", "aria-hidden": "true" }, app.icon),
        el("div", {}, el("h3", {}, app.name), el("p", { class: "app-tag" }, app.tagline))),
      el("p", { class: "app-desc" }, app.description),
      el("div", { class: "app-chips" },
        el("span", { class: "chip " + (app.on_web ? "chip-ok" : "chip-soon") },
          app.on_web ? "On the web" : "In the PC app · ask MIA here"),
        app.shown ? null : el("span", { class: "chip" }, "Hidden from your apps")),
      app.ask ? el("p", { class: "app-ask" }, "Try: “" + app.ask + "”") : null,
      tools,
      el("div", { class: "app-actions" }, open, toggle));
  }

  function matches(app, words) {
    if (filter === "web" && !app.on_web) return false;
    if (filter === "ask" && app.on_web) return false;
    if (!words) return true;
    const text = [app.name, app.tagline, app.description, app.ask, ...app.tools.map((t) => t.does + " " + t.detail)]
      .join(" ").toLowerCase();
    return words.split(/\s+/).every((w) => text.includes(w));
  }

  function draw() {
    const words = $("find").value.trim().toLowerCase();
    let shown = 0;
    $("strip").hidden = mode !== "manage";
    $("mode").textContent = mode === "tiles" ? "Manage apps · what MIA can do in each" : "Back to the app grid";
    $("views").hidden = mode !== "tiles";
    $("views").replaceChildren(...[["all", "All apps"], ["favorites", "★ Favorites"]].map(([id, label]) => el("button", {
      type: "button", role: "tab", "aria-selected": String(view === id),
      onclick: () => { view = id; history.replaceState(null, "", id === "favorites" ? "#favorites" : location.pathname); draw(); },
    }, label)));
    if (mode === "tiles") {
      const all = data.groups.flatMap((g) => g.apps);
      let apps;
      if (view === "favorites") {
        // In the order you starred them.
        const byId = Object.fromEntries(all.map((a) => [a.id, a]));
        apps = data.favorites.map((id) => byId[id]).filter((a) => a && matches(a, words));
      } else {
        // The ones on the web first (the concept's grid), then the rest, reachable by asking MIA.
        apps = all.filter((a) => a.shown && matches(a, words)).sort((x, y) => (y.on_web ? 1 : 0) - (x.on_web ? 1 : 0));
      }
      shown = apps.length;
      $("groups").replaceChildren(el("div", { class: "tile-grid" }, apps.map(tile)));
      $("nothing").hidden = shown > 0 || (view === "favorites" && !words);
      $("no-favorites").hidden = !(view === "favorites" && !data.favorites.length && !words);
      return;
    }
    $("no-favorites").hidden = true;
    $("groups").replaceChildren(...data.groups.map((g) => {
      const apps = g.apps.filter((a) => matches(a, words));
      shown += apps.length;
      if (!apps.length) return "";
      return el("section", { class: "app-group" },
        el("div", { class: "sect" }, el("h2", {}, g.name), el("span", { class: "more" }, apps.length + "")),
        el("div", { class: "app-grid" }, apps.map(card)));
    }));
    $("nothing").hidden = shown > 0;
  }

  async function render() {
    data = await MIA.apps();
    const c = data.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.apps), el("span", { class: "t" }, "apps")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.on_web), el("span", { class: "t" }, "on the web so far")),
      el("div", { class: "cell" }, el("span", { class: "n" }, c.tools), el("span", { class: "t" }, "things MIA can do for you")));
    const tabs = [["all", "All"], ["web", "On the web"], ["ask", "Ask MIA"]];
    $("tabs").replaceChildren(...tabs.map(([id, label]) => el("button", {
      type: "button", role: "tab", "aria-selected": String(filter === id),
      onclick: () => { filter = id; render(); },
    }, label)));
    draw();
  }

  $("find").addEventListener("input", () => data && draw());
  $("search-button").addEventListener("click", () => { $("tools").hidden = !$("tools").hidden; if (!$("tools").hidden) $("find").focus(); });
  $("mode").addEventListener("click", () => { mode = mode === "tiles" ? "manage" : "tiles"; $("tools").hidden = mode === "tiles" && !$("find").value; draw(); });
  MIAShell.start(render);
})();
