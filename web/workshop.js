/*
 * workshop.js — the Workshop screen (claude, 2026-10-16; Zac: the app only
 * opened a chat). Renders MIA.workshop() (core/web_more.py) in tabs:
 * Recipes and Builds (crafting recipes, DEC-0030: what a recipe needs and
 * what's short, the shopping list, Bought It, Start Build, steps, Finish,
 * photos, Sold It and the build's real profit; core/web_craft.py,
 * core/craft_actions.py), Jobs, Materials (low ones first), Products
 * (stock, Sell), Parts, and Money (sales and costs). Every button proposes
 * an action. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["recipes", "Recipes"], ["builds", "Builds"], ["materials", "Materials"], ["products", "Products"],
    ["jobs", "Jobs"], ["parts", "Parts"], ["money", "Money"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "recipes";
  let openRecipe = null;

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

  // ------------------------------------------------------------ crafting recipes (DEC-0030)
  const mediaUrl = (b, m) => "/api/workshop/builds/" + encodeURIComponent(b.id) + "/media?name=" + encodeURIComponent(m.name);
  const TAG = { before: "Before", during: "During", after: "After" };

  async function startBuild(r) {
    const v = await form("Build " + r.name, [{ name: "times", label: "How many", type: "int", required: true, options: [], default: 1 }], {});
    if (v && await act({ kind: "craft.start", params: { recipe_id: r.id, times: v.times } })) { tab = "builds"; history.replaceState(null, "", "#builds"); }
  }
  async function bought(r) {
    const v = await form("Bought For " + r.name, r.receive_fields, {});
    if (v) act({ kind: "craft.receive", params: Object.assign({ recipe_id: r.id }, v) });
  }
  async function copyList(r) {
    try { await navigator.clipboard.writeText(r.name + " shopping list\n" + r.shopping_list); MIAShell.say("Shopping list copied."); }
    catch (e) { MIAShell.say("Couldn't copy it here; select the list and copy it."); }
  }
  async function finish(b) {
    const v = await form("Finish " + b.name, [{ name: "hours", label: "Hours it took", type: "amount", required: false, options: [], default: b.hours || null }], {});
    if (v) act({ kind: "craft.finish", params: { job_id: b.id, hours: v.hours } });
  }
  async function sold(b) {
    const v = await form("Sold " + b.name, [{ name: "amount", label: "What it sold for", type: "money", required: true, options: [], default: null }], {});
    if (v) act({ kind: "craft.sell", params: { job_id: b.id, amount: v.amount } });
  }
  async function cost(b) {
    const v = await form("Add A Cost To " + b.name, [
      { name: "what", label: "What it was (the piece you bought, stain, delivery…)", type: "text", required: true, options: [], default: null },
      { name: "amount", label: "What it cost", type: "money", required: true, options: [], default: null },
      { name: "category", label: "Kind", type: "choice", required: true, options: ["Materials", "Tools", "Shipping", "Fees", "Overhead", "Other"], default: "Materials" }], {});
    if (v) act({ kind: "craft.cost", params: Object.assign({ job_id: b.id }, v) });
  }
  function addPhoto(b, tag) {
    const input = el("input", { type: "file", multiple: true, hidden: true, accept: "image/*,video/*" });
    input.addEventListener("change", async () => {
      for (const file of input.files) {
        if (file.size > 200 * 1024 * 1024) { MIAShell.say(file.name + " is over 200 MB."); continue; }
        try { MIAShell.say((await MIA.upload("/api/workshop/builds/" + encodeURIComponent(b.id) + "/media", file, { "X-Tag": tag })).message); }
        catch (e) { MIAShell.say("Couldn't add " + file.name + ": " + e.message); }
      }
      input.remove();
      page = await MIA.workshop();
      draw();
    });
    document.body.append(input);
    input.click();
  }
  async function viewPhoto(b, m) {
    let url;
    try { url = URL.createObjectURL(await MIA.download(mediaUrl(b, m))); } catch (e) { MIAShell.say("Couldn't open " + m.name + "."); return; }
    const dialog = el("dialog", { class: "confirm form-dialog file-view", "aria-label": m.name });
    const close = () => { dialog.close(); dialog.remove(); URL.revokeObjectURL(url); };
    dialog.append(el("h3", {}, (TAG[m.tag] ? TAG[m.tag] + ": " : "") + b.name),
      m.kind === "video" ? el("video", { src: url, controls: true, playsinline: true }) : el("img", { src: url, alt: m.name }),
      el("div", { class: "confirm-actions" },
        el("a", { class: "btn btn-ghost", href: url, download: m.name }, "Download"),
        btn("Delete", "btn-ghost", () => { close(); act({ kind: "craft.photo_delete", params: { job_id: b.id, name: m.name } }); }),
        btn("Close", "btn-ghost", close)));
    dialog.oncancel = (ev) => { ev.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }
  function photos(b) {
    const tiles = b.photos.map((m) => {
      const t = el("button", { type: "button", class: "media-tile kind-" + m.kind, "aria-label": "Open " + m.name, onclick: () => viewPhoto(b, m) });
      if (m.kind === "image") {
        const img = el("img", { alt: "", loading: "lazy" });
        MIA.image(mediaUrl(b, m)).then((src) => { if (src) img.src = src; });
        t.append(img);
      } else t.append(el("span", { class: "media-ico", "aria-hidden": "true" }, "▶"));
      if (TAG[m.tag]) t.append(el("span", { class: "craft-tag" }, TAG[m.tag]));
      return t;
    });
    return el("div", { class: "craft-photos" },
      tiles.length ? el("div", { class: "media-grid" }, tiles) : null,
      buttons(btn(b.finished ? "Add After Photo" : "Add Before Photo", "btn-ghost btn-small", () => addPhoto(b, b.finished ? "after" : "before")),
        btn("Add Progress Photo", "btn-ghost btn-small", () => addPhoto(b, "during"))));
  }
  const tiles = (...list) => el("div", { class: "craft-tiles" }, list.filter(Boolean).map(([label, value, cls]) =>
    el("div", { class: "craft-tile " + (cls || "") }, el("span", { class: "dim" }, label), el("strong", {}, value))));

  function recipeCard(r) {
    const open = openRecipe === r.id;
    const status = !r.rows.length ? chip("No Materials Yet") : r.ready ? chip("Ready To Build", "chip-ok") : chip("Short " + r.short, "chip-soon");
    const head = el("button", { type: "button", class: "craft-head", "aria-expanded": String(open),
      onclick: () => { openRecipe = open ? null : r.id; draw(); } },
      el("div", {}, el("h3", {}, r.name), el("p", { class: "dim" }, [r.category, r.dimensions, r.est_hours ? r.est_hours + " h" : null].filter(Boolean).join(" · "))),
      status);
    const summary = tiles(["Materials", r.est_cost_text + (r.unpriced ? "+" : "")], r.price_text ? ["Sells For", r.price_text] : null,
      r.est_profit_text ? ["Est. Profit", r.est_profit_text, r.est_profit < 0 ? "bad" : "ok"] : null,
      r.built ? ["Built", String(r.built)] : null);
    if (!open) return el("article", { class: "glass craft-card" }, head, summary);
    const needs = el("ul", { class: "craft-needs" }, r.rows.map((x) => el("li", { class: x.status },
      el("span", {}, x.line_text), el("span", { class: "dim" }, x.short ? "have " + x.have + " · need " + x.short + " more" : "✓ have it"))));
    return el("article", { class: "glass craft-card open" }, head, summary,
      r.description ? el("p", {}, r.description) : null,
      el("h4", {}, "What It Needs"), r.rows.length ? needs : el("p", { class: "dim" }, "Edit the recipe to list its materials, one per line."),
      r.shopping.length ? el("div", { class: "craft-shop" },
        el("h4", {}, "Shopping List" + (r.shopping_text ? " · about " + r.shopping_text : "")),
        el("pre", { class: "craft-list" }, r.shopping_list),
        buttons(btn("Copy List", "btn-ghost btn-small", () => copyList(r)), btn("Bought It", "btn-green btn-small", () => bought(r)))) : null,
      r.cut_list ? [el("h4", {}, "Cut List"), el("pre", { class: "craft-list" }, r.cut_list)] : null,
      r.tools ? [el("h4", {}, "Tools"), el("p", { class: "dim" }, r.tools)] : null,
      r.steps.length ? [el("h4", {}, "Steps"), el("ol", { class: "craft-steps" }, r.steps.map((s) => el("li", {}, s)))] : null,
      r.built ? [el("h4", {}, "How It's Gone"), tiles(["Built", String(r.built)], ["Sold", String(r.sold)],
        r.actual.cost ? ["Avg. Cost", r.actual.cost] : null, r.actual.profit ? ["Avg. Profit", r.actual.profit] : null,
        r.actual.per_hour ? ["Per Hour", r.actual.per_hour] : null)] : null,
      r.notes ? el("p", { class: "dim" }, r.notes) : null,
      buttons(btn("Start Build", "btn-amber", () => startBuild(r)), btn("Edit", "btn-ghost btn-small", () => edit("craft_recipe", r)),
        btn("Delete", "btn-ghost btn-small", () => del("craft_recipe", r))));
  }

  function buildCard(b) {
    const res = b.result;
    return el("article", { class: "glass craft-card open" },
      el("div", { class: "craft-head static" },
        el("div", {}, el("h3", {}, b.name), el("p", { class: "dim" }, "Started " + day(b.started) + (b.steps.length ? " · " + b.steps_done + "/" + b.steps.length + " steps" : ""))),
        chip(b.finished ? (res.is_sold ? "Sold" : "In Stock") : "Building", b.finished ? "chip-ok" : "chip-soon")),
      !b.finished && b.steps.length ? el("ul", { class: "gear-list" }, b.steps.map((s) => el("li", { class: s.done ? "done" : "" },
        el("button", { type: "button", class: "tick" + (s.done ? " on" : ""), "aria-pressed": String(s.done), "aria-label": (s.done ? "Untick " : "Done: ") + s.text,
          onclick: () => act({ kind: "craft.step", params: { job_id: b.id, index: s.index } }) }, s.done ? "✓" : ""),
        el("span", {}, s.text)))) : null,
      b.finished ? tiles(["Cost", res.cost_text], ["Sold For", res.is_sold ? res.sold_text : "—"],
        res.is_sold ? ["Profit", res.profit_text, res.profit < 0 ? "bad" : "ok"] : null,
        res.per_hour_text ? ["Per Hour", res.per_hour_text] : null, res.hours ? ["Hours", String(res.hours)] : null) : null,
      b.finished ? el("p", { class: "dim" }, "Materials " + res.materials_text + (res.other ? " · other costs " + res.other_text : "") +
        (res.after_labor_text ? " · after paying yourself " + res.after_labor_text : "")) : null,
      photos(b),
      buttons(!b.finished ? btn("Finish", "btn-green", () => finish(b)) : null,
        b.in_stock ? btn("Sold It", "btn-green", () => sold(b)) : null,
        btn("Add Cost", "btn-ghost btn-small", () => cost(b))));
  }

  const VIEWS = {
    recipes: () => section("Recipes", btn("Add Recipe", "btn-amber", () => add("craft_recipe", "Add A Recipe")),
      page.recipes.length ? el("div", { class: "craft-grid" }, page.recipes.map(recipeCard))
        : el("p", { class: "empty" }, "Save something you build as a recipe: what it needs, the cut list, the steps and what it sells for. MIA checks your materials and makes the shopping list.")),
    builds: () => {
      const active = page.builds.filter((b) => !b.finished), done = page.builds.filter((b) => b.finished);
      return [
        section("Building Now", null, active.length ? el("div", { class: "craft-grid" }, active.map(buildCard))
          : el("p", { class: "empty" }, "Nothing on the bench. Open a recipe and Start Build.")),
        done.length ? section("Finished", null, el("div", { class: "craft-grid" }, done.map(buildCard))) : null,
      ].filter(Boolean);
    },
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
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.recipes || 0), el("span", { class: "t" }, "Recipes")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.open_jobs), el("span", { class: "t" }, "Building")),
      el("div", { class: "cell " + (c.low ? "bad" : "ok") }, el("span", { class: "n" }, c.low), el("span", { class: "t" }, "Low Materials")),
    );
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
