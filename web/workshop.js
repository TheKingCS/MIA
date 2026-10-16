/*
 * workshop.js — the Workshop screen (claude, 2026-10-16; Zac: the app only
 * opened a chat). Renders MIA.workshop() (core/web_more.py) in tabs: Jobs
 * (what each used and made, its cost), Materials (low ones first), Products
 * (stock, Sell), Parts, and Money (sales and costs). Every button proposes
 * an action from core/more_actions.py. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["jobs", "Jobs"], ["materials", "Materials"], ["products", "Products"], ["parts", "Parts"], ["money", "Money"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "jobs";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const n = (x) => (Math.round(x * 100) / 100).toString();
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";

  async function add(key, title) {
    const v = await form(title, page.forms[key].fields, {});
    if (v) act({ kind: key + ".add", params: v });
  }
  async function edit(key, item) {
    const v = await form("Edit " + item.name, page.forms[key].fields, item.values);
    if (v) act({ kind: key + ".edit", params: Object.assign({ [page.forms[key].id_param]: item.id }, v) });
  }
  const del = (key, item) => act({ kind: key + ".delete", params: { [page.forms[key].id_param]: item.id } });
  async function adjust(key, item, title) {
    const v = await form(title, [{ name: "delta", label: "How many (use - to take away, e.g. -2)", type: "number", required: true, options: [], default: null }], {});
    if (v) act({ kind: key + ".adjust", params: { [key + "_id"]: item.id, delta: v.delta } });
  }
  async function pickAmount(title, listName, label) {
    const fields = [{ name: "pick", label, type: "pick", required: true, options: [listName], default: null },
      { name: "quantity", label: "How much", type: "amount", required: true, options: [], default: 1 }];
    return form(title, fields, {}, page.picks);
  }
  async function used(job) {
    const v = await pickAmount(job.name + ": Used Material", "materials", "Material");
    if (v) act({ kind: "job.use", params: { job_id: job.id, material_id: v.pick, quantity: v.quantity } });
  }
  async function made(job) {
    const v = await pickAmount(job.name + ": Made Product", "products", "Product");
    if (v) act({ kind: "job.make", params: { job_id: job.id, product_id: v.pick, quantity: v.quantity } });
  }
  async function sell(p) {
    const v = await form("Sell " + p.name, page.forms.product_sale.fields, {});
    if (v) act({ kind: "product.sell", params: Object.assign({ product_id: p.id }, v) });
  }

  const row = (title, sub, chips, actions, extra) => el("div", { class: "row money-row" + (extra || "") },
    el("div", {}, el("div", { class: "row-title" }, title, ...(chips || [])), sub ? el("div", { class: "row-sub" }, sub) : null),
    actions);
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const STATUS = { "In Progress": "chip-soon", Planned: "", Complete: "chip-ok", Cancelled: "chip-bad" };

  const VIEWS = {
    jobs: () => section("Jobs", btn("Add Job", "btn-amber", () => add("job", "Add Job")),
      page.jobs.length ? el("div", { class: "rows" }, page.jobs.map((j) => row(j.name,
        [j.description, j.used.length ? "Used: " + j.used.join(", ") : null, j.made.length ? "Made: " + j.made.join(", ") : null,
          j.hours ? n(j.hours) + " h" : null, j.cost ? "Cost " + j.cost : null].filter(Boolean).join(" · "),
        [chip(j.status, STATUS[j.status])],
        buttons(btn("Used Material", "btn-ghost btn-small", () => used(j)), btn("Made Product", "btn-ghost btn-small", () => made(j)),
          btn("Edit", "btn-ghost btn-small", () => edit("job", j)), btn("Delete", "btn-ghost btn-small", () => del("job", j))))))
        : el("p", { class: "empty" }, "No jobs yet. Add one, like “Birdhouse batch”.")),
    materials: () => section("Materials", btn("Add Material", "btn-amber", () => add("material", "Add Material")),
      page.materials.length ? el("div", { class: "rows" }, page.materials.map((m) => row(m.name,
        [n(m.on_hand) + (m.unit ? " " + m.unit : "") + " on hand", m.reorder_at ? "reorder at " + n(m.reorder_at) : null,
          m.cost ? m.cost + (m.unit ? " / " + m.unit : " each") : null, m.location].filter(Boolean).join(" · "),
        m.low ? [chip("Low", "chip-bad")] : [],
        buttons(btn("+ / −", "btn-green btn-small", () => adjust("material", m, "Change " + m.name)),
          btn("Edit", "btn-ghost btn-small", () => edit("material", m)), btn("Delete", "btn-ghost btn-small", () => del("material", m))),
        m.low ? " overdue" : "")))
        : el("p", { class: "empty" }, "No materials yet. Add what you build with: plywood, filament, screws.")),
    products: () => section("Products", btn("Add Product", "btn-amber", () => add("product", "Add Product")),
      page.products.length ? el("div", { class: "rows" }, page.products.map((p) => row(p.name,
        [n(p.stock) + " in stock", p.price, p.listings.length ? p.listings.map((l) => l.platform + " " + l.price).join(", ") : null]
          .filter(Boolean).join(" · "),
        p.stock <= 0 ? [chip("Out", "chip-bad")] : [],
        buttons(btn("Sell", "btn-green btn-small", () => sell(p)), btn("+ / −", "btn-ghost btn-small", () => adjust("product", p, "Change " + p.name + " stock")),
          btn("Edit", "btn-ghost btn-small", () => edit("product", p)), btn("Delete", "btn-ghost btn-small", () => del("product", p))))))
        : el("p", { class: "empty" }, "No products yet. Add what you make to sell.")),
    parts: () => section("Parts", btn("Add Part", "btn-amber", () => add("component", "Add Part")),
      page.parts.length ? el("div", { class: "rows" }, page.parts.map((c) => row(c.name,
        [c.detail, c.quantity + " on hand", c.location].filter(Boolean).join(" · "),
        c.empty ? [chip("None Left", "chip-bad")] : [],
        buttons(btn("+ / −", "btn-green btn-small", () => adjust("component", c, "Change " + c.name)),
          btn("Edit", "btn-ghost btn-small", () => edit("component", c)), btn("Delete", "btn-ghost btn-small", () => del("component", c))))))
        : el("p", { class: "empty" }, "No parts yet. Add the small stuff: resistors, bolts, connectors.")),
    money: () => [
      el("div", { class: "fact-tiles nw-row" },
        el("div", { class: "glass nw-tile" }, el("span", { class: "dim" }, "Sales"), el("strong", {}, page.totals.sales)),
        el("div", { class: "glass nw-tile" }, el("span", { class: "dim" }, "Costs"), el("strong", {}, page.totals.costs)),
        el("div", { class: "glass nw-tile" + (page.totals.profit_value < 0 ? " bad" : "") }, el("span", { class: "dim" }, "Profit"), el("strong", {}, page.totals.profit))),
      section("Sales And Costs", buttons(btn("Add Sale", "btn-green", () => add("sale", "Add Sale")), btn("Add Cost", "btn-amber", () => add("shop_expense", "Add Cost"))),
        page.money.length ? el("div", { class: "rows" }, page.money.map((r) => row(r.what, [day(r.date), r.kind === "sale" ? "Sale" : r.category].filter(Boolean).join(" · "),
          [chip((r.kind === "sale" ? "+" : "−") + r.amount, r.kind === "sale" ? "chip-ok" : "")],
          buttons(btn("Delete", "btn-ghost btn-small", () => act({ kind: (r.kind === "sale" ? "sale" : "shop_expense") + ".delete", params: { entry_id: r.id } }))))))
          : el("p", { class: "empty" }, "No sales or costs yet. Selling a product logs its sale here.")),
    ],
  };

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.open_jobs), el("span", { class: "t" }, "Open Jobs")),
      el("div", { class: "cell " + (c.low ? "bad" : "ok") }, el("span", { class: "n" }, c.low), el("span", { class: "t" }, "Low Materials")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.products), el("span", { class: "t" }, "Products")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    const view = VIEWS[tab]();
    $("panel").replaceChildren(...[].concat(view));
  }

  MIAShell.start(async () => {
    page = await MIA.workshop();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "The Workshop isn't set up on this MIA."));
      return;
    }
    draw();
  });
})();
