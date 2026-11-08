/*
 * equipment.js — Garage and Greenhouse (claude, 2026-10-06, DEC-0017;
 * Maintenance and Property folded in, Zac 2026-10-16). The page's
 * <body data-scope> picks the screen; tabs Assets, Past Due, Due Today, Due Soon;
 * everything comes from MIA.equipment(scope). Tasks are marked done, assets
 * and tasks added, edited and deleted, all as equipment actions. Each asset
 * opens its own page (asset.html). The Greenhouse also grows things
 * (Zac, 2026-10-17): each tank or bed is an asset, its card shows what's
 * growing there and its latest readings; tabs Assets (with what's due),
 * Growing, Water, Experiments and Harvests, the growing ones from grow.js
 * (window.MIAGrow).
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const scope = document.body.dataset.scope || "garage";
  let page = null;
  const grow = scope === "greenhouse" ? window.MIAGrow : null;
  let growPage = null;
  let tab = location.hash.slice(1) || (scope === "greenhouse" ? "today" : "assets");

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

  // The canvas's Garage card (DEC-0113): the machine and its meter, its condition, then its next tasks in plain due
  // words (amber when it needs you or is close, grey when it's a way off). The engine words them (web_equipment.due_words).
  function assetCard(a) {
    const pic = a.photo ? el("img", { class: "asset-thumb", alt: "", loading: "lazy" }) : null;
    if (pic) MIA.image(a.photo).then((url) => { if (url) pic.src = url; else pic.remove(); });
    return el("a", { class: "glass asset-card" + (a.overdue ? " attention" : ""), href: "asset.html?id=" + encodeURIComponent(a.id) },
      pic,
      el("div", { class: "asset-head" },
        el("h3", {}, a.name),
        a.meter ? el("span", { class: "asset-meter" }, a.meter) : el("span", { class: "asset-kind" }, a.category)),
      a.make_model ? el("p", { class: "dim asset-model" }, a.make_model) : null,
      MIAShell.conditionBar(a.condition),
      grow && growPage ? grow.summary(a.id) : null,
      el("ul", { class: "asset-tasks" }, a.tasks.length ? a.tasks.map((t) =>
        el("li", { class: t.needs_attention ? "overdue" : "" }, el("span", {}, t.title),
          el("span", { class: "asset-due" + (t.needs_attention || t.urgency === "due_soon" ? " soon" : "") }, t.due || t.text)))
        : el("li", { class: "dim" }, "No tasks yet")),
      a.quick_stats.length ? el("p", { class: "dim" }, a.quick_stats.map((q) => q.title + ": " + q.text).join(" · ")) : null,
      a.task_count > a.tasks.length ? el("p", { class: "dim" }, "+" + (a.task_count - a.tasks.length) + " more") : null);
  }

  function assetsView() {
    const kids = [];
    // The machines first, as the canvas has it; what needs you follows, each with its Done.
    kids.push(el("section", { class: "glass money-section" },
      el("div", { class: "sect" }, el("h2", {}, "Assets"), btn("Add", "btn-amber", addAsset)),
      page.assets.length ? el("div", { class: "asset-grid" }, page.assets.map(assetCard))
        : el("p", { class: "empty" }, el("strong", {}, "Nothing here yet."), grow ? "Add each grow bed and tank: its plants, water and harvests are kept under it."
          : "Add something, or tell MIA: “I bought a new lawn mower”.")));
    if (page.attention.length) {
      kids.push(el("section", { class: "attention-panel" },
        el("h3", {}, "Needs You"),
        el("div", { class: "rows" }, page.attention.map((r) => taskRow(r, true)))));
    }
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
      el("div", { class: "cell " + (page.attention.length ? "bad" : "ok") }, el("span", { class: "n" }, page.attention.length), el("span", { class: "t" }, "Needs You")),
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
    if (grow && growPage) return drawGreenhouse(BUCKETS, views);
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...[["assets", "Assets"], ...BUCKETS.map(([id, l]) => [id, l])].map(([id, l]) => {
      const n = id === "assets" ? page.assets.length : page.tasks.filter((r) => r.bucket === id).length;
      return el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
        onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l + (n ? " " + n : ""));
    }));
    if (!views[tab]) tab = "assets";
    $("panel").replaceChildren(...views[tab]());
  }

  // The canvas's Greenhouse (DEC-0113): Needs You first (upkeep due, with Done, and any reading out of range), then
  // what's growing, each with its stage meter (Planted, Sprouting, Growing, Picking) and harvest line from core
  // (web_grow.growth_stage).
  function greenhouseToday() {
    const needs = page.attention.map((r) => el("div", { class: "gh-need" },
      el("div", {}, el("span", { class: "gh-what" }, r.title), el("span", { class: "dim" }, [r.asset, r.text].filter(Boolean).join(" · "))),
      r.action ? btn("Done", "btn-ghost btn-small", () => done(r)) : null));
    growPage.alerts.forEach((a) => needs.push(el("div", { class: "gh-need" },
      el("div", {}, el("span", { class: "gh-what" }, a.label + " is " + a.side), el("span", { class: "dim" },
        a.system + " · read " + a.value + (a.unit ? " " + a.unit : "") + ", range " + a.low + " to " + a.high)),
      btn("Water", "btn-ghost btn-small", () => { tab = "water"; history.replaceState(null, "", "#water"); draw(); }))));
    const growing = growPage.batches.filter((b) => b.status === "Growing");
    return [
      needs.length ? el("section", { class: "glass gh-needs", "aria-label": "Needs you" }, el("p", { class: "pw-label attn" }, "Needs You"), ...needs) : null,
      el("p", { class: "pw-label" }, "Growing"),
      growing.length ? el("div", { class: "gh-beds" }, ...growing.map((b) => el("article", { class: "glass gh-bed" },
        el("div", { class: "gh-bed-top" }, el("span", { class: "gh-what" }, b.crop + (b.variety ? " · " + b.variety : "")), el("span", { class: "dim" }, b.system)),
        el("div", { class: "gh-stages", "aria-label": b.stage.label }, ...[0, 1, 2, 3].map((i) => el("span", { class: i <= b.stage.n ? "on" : "" }))),
        el("div", { class: "gh-bed-foot" }, el("span", { class: "gh-stage" }, b.stage.label), el("span", { class: "dim" }, b.stage.line)))))
        : el("p", { class: "empty" }, "Nothing growing yet. Add a planting under Growing, or tell MIA: \"I planted 12 lettuce in bed 1\"."),
    ].filter(Boolean);
  }

  function drawGreenhouse(BUCKETS, views) {
    const c = growPage.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.growing), el("span", { class: "t" }, "Growing")),
      el("div", { class: "cell " + (c.alerts ? "bad" : "ok") }, el("span", { class: "n" }, c.alerts), el("span", { class: "t" }, "Out Of Range")),
      el("div", { class: "cell " + (page.attention.length ? "bad" : "ok") }, el("span", { class: "n" }, page.attention.length), el("span", { class: "t" }, "Needs Attention")));
    const all = {
      today: greenhouseToday,
      assets: () => assetsView().concat(...BUCKETS.filter(([id]) => id !== "past_due" && page.tasks.some((r) => r.bucket === id)).map(([id]) => views[id]())),
      growing: grow.views.growing, water: grow.views.water,
      experiments: grow.views.experiments, harvests: grow.views.harvests, next: grow.views.next,
    };
    const TABS = [["today", "Today"], ["assets", "Assets"], ["growing", "Growing"], ["water", "Water"], ["experiments", "Experiments"], ["harvests", "Harvests"], ["next", "What's Next"]];
    if (!all[tab]) tab = "today";
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...[].concat(all[tab]()));
  }

  MIAShell.start(async () => {
    page = await MIA.equipment(scope);
    if (grow) {
      try { growPage = await grow.load(); } catch (e) { growPage = null; }  // the equipment still shows
    }
    draw();
  });
})();
