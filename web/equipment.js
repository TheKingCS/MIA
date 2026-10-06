/*
 * equipment.js — Garage, Property, Greenhouse and Maintenance (claude,
 * 2026-10-06, DEC-0017). The page's <body data-scope> picks the screen;
 * everything comes from MIA.equipment(scope). Tasks are marked done, assets
 * and tasks added, edited and deleted, all as equipment actions. Each asset
 * opens its own page (asset.html).
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const scope = document.body.dataset.scope || "maintenance";
  let page = null;
  let tab = location.hash.slice(1) || "assets";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const chip = (row) => el("span", { class: "when " + (row.urgency === "overdue" || row.needs_attention ? "overdue" : row.urgency === "due_soon" ? "today" : "") }, row.text);

  async function done(row) {
    if (row.action.asks_meter) {
      const values = await form("Done: " + row.title, page.forms.done.fields, {});
      if (!values) return;
      return act({ kind: "maintenance.done", params: { task_id: row.id, meter_value: values.meter_value } });
    }
    return act(row.action);
  }
  async function addAsset() {
    const values = await form("Add to " + page.name, page.forms.asset.fields, { category: page.default_category });
    if (values) act({ kind: "asset.add", params: values });
  }
  async function addTask() {
    const fields = page.forms.maintenance_task.fields;
    const values = await form("Add a maintenance task", fields, {}, { assets: page.all_assets });
    if (values) act({ kind: "maintenance_task.add", params: values });
  }

  function taskRow(row, showAsset) {
    return el("div", { class: "row money-row " + (row.needs_attention ? "overdue" : "") },
      el("div", {},
        el("div", { class: "row-title" }, row.title),
        el("div", { class: "row-sub" }, [showAsset ? row.asset : null, row.predicted, row.priority !== "normal" ? row.priority + " priority" : null]
          .filter(Boolean).join(" · "))),
      el("div", { class: "row-meta" }, chip(row),
        el("div", { class: "row-buttons" },
          row.action ? btn("Done", "btn-green", () => done(row)) : null,
          el("a", { class: "btn btn-ghost", href: "asset.html?id=" + encodeURIComponent(row.asset_id) }, "Open"))));
  }

  function assetCard(a) {
    return el("a", { class: "glass asset-card" + (a.overdue ? " attention" : ""), href: "asset.html?id=" + encodeURIComponent(a.id) },
      el("div", { class: "asset-head" },
        el("h3", {}, a.name),
        el("span", { class: "chip" }, a.category)),
      a.make_model ? el("p", { class: "dim" }, a.make_model) : null,
      el("ul", { class: "asset-tasks" }, a.tasks.length ? a.tasks.map((t) =>
        el("li", { class: t.needs_attention ? "overdue" : "" }, el("span", {}, t.title), chip(t)))
        : el("li", { class: "dim" }, "No tasks yet")),
      a.quick_stats.length ? el("p", { class: "dim" }, a.quick_stats.map((q) => q.title + ": " + q.text).join(" · ")) : null,
      a.task_count > a.tasks.length ? el("p", { class: "dim" }, "+" + (a.task_count - a.tasks.length) + " more") : null);
  }

  function assetsView() {
    const kids = [];
    if (page.attention.length) {
      kids.push(el("section", { class: "attention-panel" },
        el("h3", {}, "⚠ Needs attention"),
        el("div", { class: "rows" }, page.attention.map((r) => taskRow(r, true)))));
    }
    kids.push(el("section", { class: "money-section" },
      el("div", { class: "sect" }, el("h2", {}, "Assets"), btn("Add", "btn-amber", addAsset)),
      page.assets.length ? el("div", { class: "asset-grid" }, page.assets.map(assetCard))
        : el("p", { class: "empty" }, el("strong", {}, "Nothing here yet."), "Add something, or tell MIA: “I bought a new lawn mower”.")));
    if (page.next_up.length) {
      kids.push(el("section", { class: "glass money-section" },
        el("div", { class: "sect" }, el("h2", {}, "Next up")),
        el("div", { class: "rows" }, page.next_up.map((r) => taskRow(r, true)))));
    }
    return kids;
  }

  function tasksView() {
    return [el("section", { class: "glass money-section" },
      el("div", { class: "sect" }, el("h2", {}, "Every task"), btn("Add task", "btn-amber", addTask)),
      page.tasks.length ? el("div", { class: "rows" }, page.tasks.map((r) => taskRow(r, true))) : el("p", { class: "dim" }, "No tasks yet."))];
  }

  function calendarView() {
    const days = {};
    page.calendar.forEach((c) => { (days[c.date] = days[c.date] || []).push(c); });
    const label = (iso) => new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
    return [el("section", { class: "glass money-section" },
      el("div", { class: "sect" }, el("h2", {}, "The next two months")),
      Object.keys(days).length ? el("div", { class: "rows" }, Object.entries(days).map(([d, items]) =>
        el("div", { class: "row money-row" + (items.some((i) => i.overdue) ? " overdue" : "") },
          el("div", {}, el("div", { class: "row-title" }, label(d)),
            el("div", { class: "row-sub" }, items.map((i) => i.title + " (" + i.asset + ")").join(" · "))))))
        : el("p", { class: "dim" }, "Nothing scheduled in the next two months."))];
  }

  function draw() {
    $("hero-icon").textContent = page.icon;
    $("hero-name").textContent = page.name;
    $("hero-tagline").textContent = page.tagline;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.assets.length), el("span", { class: "t" }, "Tracked")),
      el("div", { class: "cell " + (page.attention.length ? "bad" : "ok") }, el("span", { class: "n" }, page.attention.length), el("span", { class: "t" }, "Needs attention")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, page.next_up.length), el("span", { class: "t" }, "Next up")));
    const views = { assets: assetsView };
    if (scope === "maintenance") {
      Object.assign(views, { tasks: tasksView, calendar: calendarView });
      $("tabs").hidden = false;
      $("tabs").replaceChildren(...[["assets", "Assets"], ["tasks", "Tasks"], ["calendar", "Calendar"]].map(([id, l]) =>
        el("button", { type: "button", role: "tab", "aria-selected": String(id === tab), onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    }
    if (!views[tab]) tab = "assets";
    $("panel").replaceChildren(...views[tab]());
  }

  MIAShell.start(async () => { page = await MIA.equipment(scope); draw(); });
})();
