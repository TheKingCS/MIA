/*
 * equipment.js — Garage and Greenhouse (claude, 2026-10-06, DEC-0017;
 * Maintenance and Property folded in, Zac 2026-10-16). The page's
 * <body data-scope> picks the screen; tabs Assets, Past Due, Due Today, Due Soon;
 * everything comes from MIA.equipment(scope). Tasks are marked done, assets
 * and tasks added, edited and deleted, all as equipment actions. Each asset
 * opens its own page (asset.html).
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const scope = document.body.dataset.scope || "garage";
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
    kids.push(el("section", { class: "glass money-section" },
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

  function draw() {
    $("hero-icon").textContent = page.icon;
    if (window.MIAIcons) MIAIcons.badge($("hero-icon"), document.body.dataset.app);  // the line icon (DEC-0023)
    $("hero-name").textContent = page.name;
    $("hero-tagline").textContent = page.tagline;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.assets.length), el("span", { class: "t" }, "Tracked")),
      el("div", { class: "cell " + (page.attention.length ? "bad" : "ok") }, el("span", { class: "n" }, page.attention.length), el("span", { class: "t" }, "Needs attention")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, page.next_up.length), el("span", { class: "t" }, "Next up")));
    // Past Due / Due Today / Due Soon (Zac, 2026-10-16), from every task's bucket.
    const BUCKETS = [["past_due", "Past Due", "Nothing past due. Everything's cared for."],
      ["due_today", "Due Today", "Nothing due today."], ["due_soon", "Due Soon", "Nothing coming due."]];
    const views = { assets: assetsView };
    BUCKETS.forEach(([id, label, empty]) => {
      views[id] = () => {
        const rows = page.tasks.filter((r) => r.bucket === id);
        return [el("section", { class: "glass money-section" },
          el("div", { class: "sect" }, el("h2", {}, label), btn("Add Task", "btn-amber", addTask)),
          rows.length ? el("div", { class: "rows" }, rows.map((r) => taskRow(r, true))) : el("p", { class: "dim" }, empty))];
      };
    });
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...[["assets", "Assets"], ...BUCKETS.map(([id, l]) => [id, l])].map(([id, l]) => {
      const n = id === "assets" ? page.assets.length : page.tasks.filter((r) => r.bucket === id).length;
      return el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
        onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l + (n ? " " + n : ""));
    }));
    if (!views[tab]) tab = "assets";
    $("panel").replaceChildren(...views[tab]());
  }

  MIAShell.start(async () => { page = await MIA.equipment(scope); draw(); });
})();
