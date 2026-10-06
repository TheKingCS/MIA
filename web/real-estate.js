/*
 * real-estate.js — the Real Estate screen (claude, 2026-10-06, DEC-0017/0018).
 * Renders MIA.realEstate() (core/web_screens.py): each property with its
 * status, where it is, rent, what's owed, equity and cash flow, its upkeep
 * (its own Maintenance asset, opened on asset.html) and related missions.
 * Rent and expenses are recorded into Money. Every change is a property
 * action (core/estate_actions.py) or a maintenance one. Formatting only here.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["properties", "Properties"], ["maintenance", "Maintenance"], ["missions", "Missions"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "properties";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const sym = () => page.currency_symbol || "$";
  const fmt = (n) => (n < 0 ? "-" : "") + sym() + Math.abs(Number(n || 0)).toLocaleString(undefined, { maximumFractionDigits: 0 });
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const STATUS_TONE = { "Rented": "chip-ok", "Owner Occupied": "chip-ok", "Vacant": "chip-bad", "For Sale": "chip-soon",
    "For Rent": "chip-soon", "Under Renovation": "chip-soon" };

  async function add() {
    const v = await form("Add a property", page.forms.property.fields, {});
    if (v) act({ kind: "property.add", params: v });
  }
  async function edit(p) {
    const v = await form("Edit " + p.name, page.forms.property.fields, p.values);
    if (v) act({ kind: "property.edit", params: Object.assign({ property_id: p.id }, v) });
  }
  async function rent(p) {
    const v = await form("Rent from " + p.name, page.forms.rent.fields, { amount: p.rent || "" });
    if (v) act({ kind: "property.rent", params: Object.assign({ property_id: p.id }, v) });
  }
  async function expense(p) {
    const v = await form("An expense on " + p.name, page.forms.expense.fields, {});
    if (v) act({ kind: "property.expense", params: Object.assign({ property_id: p.id }, v) });
  }

  function taskRow(row, property) {
    const tone = row.urgency === "overdue" || row.needs_attention ? "overdue" : row.urgency === "due_soon" ? "today" : "";
    return el("div", { class: "row money-row " + (row.needs_attention ? "overdue" : "") },
      el("div", {}, el("div", { class: "row-title" }, row.title),
        el("div", { class: "row-sub" }, [property ? property.name : null, row.predicted].filter(Boolean).join(" · "))),
      el("div", { class: "row-meta" }, el("span", { class: "when " + tone }, row.text),
        buttons(row.action && !row.action.asks_meter ? btn("Done", "btn-green", () => act(row.action)) : null,
          el("a", { class: "btn btn-ghost", href: "asset.html?id=" + encodeURIComponent(row.asset_id) }, "Open"))));
  }

  function figure(label, value, cls) {
    return el("div", { class: "prop-fig" + (cls ? " " + cls : "") }, el("small", {}, label), el("strong", {}, value));
  }

  function card(p) {
    const attention = p.tasks.filter((t) => t.needs_attention);
    return el("article", { class: "glass asset-card property-card" + (attention.length ? " attention" : "") },
      el("div", { class: "asset-head" }, el("h3", {}, p.name),
        p.status ? el("span", { class: "chip " + (STATUS_TONE[p.status] || "") }, p.status) : el("span", { class: "chip" }, p.type)),
      p.location ? el("p", { class: "dim" }, "📍 " + p.location) : null,
      el("div", { class: "prop-figs" },
        p.rent ? figure("Rent", fmt(p.rent) + "/mo") : null,
        p.owed ? figure("Balance", fmt(p.owed)) : null,
        figure("Equity", fmt(p.equity), p.equity >= 0 ? "good" : "bad"),
        p.cash_flow != null ? figure("Cash flow", fmt(p.cash_flow) + "/mo", p.cash_flow >= 0 ? "good" : "bad") : null,
        p.income_month || p.expenses_month ? figure("This month", "+" + fmt(p.income_month) + " / -" + fmt(p.expenses_month)) : null),
      attention.length ? el("p", { class: "attention-line" }, "⚠ " + attention.map((t) => t.title).join(", ")) : null,
      buttons(
        btn("Record rent", "btn-green", () => rent(p)),
        btn("Add expense", "btn-ghost", () => expense(p)),
        p.asset_id ? el("a", { class: "btn btn-ghost", href: "asset.html?id=" + encodeURIComponent(p.asset_id) }, "Upkeep")
          : btn("Track upkeep", "btn-ghost", () => act({ kind: "property.track_upkeep", params: { property_id: p.id } })),
        btn("Edit", "btn-ghost", () => edit(p)),
        btn("Delete", "btn-ghost", () => act({ kind: "property.delete", params: { property_id: p.id } }))));
  }

  const views = {
    properties: () => [section("Properties", buttons(btn("Add property", "btn-amber", add)),
      page.properties.length ? el("div", { class: "asset-grid" }, page.properties.map(card))
        : el("p", { class: "empty" }, el("strong", {}, "No properties yet."), "Add one to see its rent, equity and upkeep in one place."))],
    maintenance: () => {
      const rows = [];
      page.properties.forEach((p) => p.tasks.forEach((t) => rows.push([t, p])));
      rows.sort((a, b) => (b[0].needs_attention - a[0].needs_attention) || ((a[0].days ?? 1e4) - (b[0].days ?? 1e4)));
      const untracked = page.properties.filter((p) => !p.asset_id);
      return [section("Upkeep", null,
        rows.length ? el("div", { class: "rows" }, rows.map(([t, p]) => taskRow(t, p)))
          : el("p", { class: "dim" }, "No upkeep tasks yet. Track a property's upkeep, then add its tasks (filters, gutters, inspections)."),
        untracked.length ? el("div", { class: "rows untracked" }, untracked.map((p) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, p.name), el("div", { class: "row-sub" }, "Upkeep not tracked yet")),
          buttons(btn("Track upkeep", "btn-amber", () => act({ kind: "property.track_upkeep", params: { property_id: p.id } }))))))
          : null)];
    },
    missions: () => {
      const rows = [];
      page.properties.forEach((p) => p.missions.forEach((m) => rows.push([m, p])));
      return [section("Related missions", el("a", { class: "btn btn-ghost", href: "missions.html" }, "All missions"),
        rows.length ? el("div", { class: "rows" }, rows.map(([m, p]) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, m.name), el("div", { class: "row-sub" }, p.name)),
          el("span", { class: "chip" + (m.status === "completed" ? " chip-ok" : "") }, m.status))))
          : el("p", { class: "dim" }, "No missions linked to a property yet. Ask MIA: “make a mission to repaint the rental”."))];
    },
  };

  function draw() {
    const t = page.totals;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, fmt(t.equity)), el("span", { class: "t" }, "Equity")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, fmt(t.cash_flow)), el("span", { class: "t" }, "Cash flow /mo")),
      el("div", { class: "cell " + (t.attention ? "bad" : "ok") }, el("span", { class: "n" }, t.attention), el("span", { class: "t" }, "Needs attention")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) =>
      el("button", { type: "button", role: "tab", "aria-selected": String(id === tab), onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...views[tab]());
  }

  MIAShell.start(async () => {
    page = await MIA.realEstate();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "Real Estate isn't set up on this MIA."), ""));
      return;
    }
    draw();
  });
})();
