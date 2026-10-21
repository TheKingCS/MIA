/*
 * workshop.js — the Workshop screen (claude, 2026-10-16; Zac: the app only
 * opened a chat). Renders MIA.workshop() (core/web_more.py) in tabs:
 * Recipes and Builds (crafting recipes, DEC-0030: what a recipe needs and
 * what's short, the shopping list, Bought It, Start Build, steps, Finish,
 * photos, Sold It and the build's real profit; core/web_craft.py,
 * core/craft_actions.py), Jobs, Materials (low ones first), Products
 * (stock, Sell), Parts, and Money (sales and costs). Every button proposes
 * an action. Formatting only.
 * Goods (DEC-0036, homestead goods; core/web_craft.py goods_section,
 * core/goods_actions.py): what's made and not sold, batch by batch with its
 * sell-by, the market day (one tap per sale: the tap is the approval, Undo in
 * the toast), the day's tally, and labels to print (web/label.html).
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["recipes", "Recipes"], ["goods", "Goods"], ["builds", "Builds"], ["materials", "Materials"], ["products", "Products"],
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
  const TAG = { before: "Before", during: "Progress", after: "After" };

  async function startBuild(r) {
    const v = await form((r.is_batch ? "Craft " : "Build ") + r.name,
      [{ name: "times", label: r.is_batch ? "How many batches (one makes " + r.makes_text + ")" : "How many", type: "int", required: true, options: [], default: 1 }], {});
    if (v && await act({ kind: "craft.start", params: { recipe_id: r.id, times: v.times } })) { tab = "builds"; history.replaceState(null, "", "#builds"); }
  }
  async function bought(r) {
    const v = await form("Bought For " + r.name, r.receive_fields, {});
    if (v) act({ kind: "craft.receive", params: Object.assign({ recipe_id: r.id }, v) });
  }
  // Bought It filled from a scanned receipt (core/receipt_match.py): pick the
  // receipt, MIA matches its lines to the recipe, you check and confirm.
  async function fromReceipt(r) {
    if (!(page.receipts || []).length) { MIAShell.say("No scanned receipts yet: share a receipt photo to MIA and file it, then try again."); return; }
    const pick = await form("Which Receipt?", [{ name: "receipt", label: "Receipt", type: "pick", required: true, options: ["receipts"], default: page.receipts[0].id }], {}, { receipts: page.receipts });
    if (!pick) return;
    let m;
    try { m = await MIA.receiptMatch(r.id, pick.receipt); } catch (e) { MIAShell.say(e.message); return; }
    if (!m.matched.length) { MIAShell.say("Nothing on that receipt matches this recipe's materials."); return; }
    const fields = r.rows.flatMap((row) => [
      { name: "q_" + row.index, label: row.name + ": how many" + (row.unit ? " " + row.unit : ""), type: "amount", required: false, options: [], default: m.values["q_" + row.index] ?? null },
      { name: "c_" + row.index, label: row.name + ": what you paid (total)", type: "money", required: false, options: [], default: m.values["c_" + row.index] ?? null }]);
    if (m.unmatched.length) MIAShell.say("Not matched: " + m.unmatched.slice(0, 4).join(", ") + (m.unmatched.length > 4 ? "…" : ""));
    const v = await form("Bought From The Receipt", fields, {});
    if (v) act({ kind: "craft.receive", params: Object.assign({ recipe_id: r.id, receipt: pick.receipt }, v) });
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
      if (TAG[m.tag]) t.append(el("span", { class: "craft-tag tag-" + m.tag }, TAG[m.tag]));
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
    const summary = tiles(["Materials", r.est_cost_text + (r.unpriced ? "+" : "")],
      r.is_batch ? ["Makes", r.makes_text] : null, r.per_piece_text ? ["Each Costs", r.per_piece_text] : null,
      r.price_text ? [r.is_batch ? "Sells For, Each" : "Sells For", r.price_text] : null,
      r.est_profit_text ? [r.is_batch ? "Est. Profit, Batch" : "Est. Profit", r.est_profit_text, r.est_profit < 0 ? "bad" : "ok"] : null,
      r.built ? ["Built", String(r.built)] : null);
    if (!open) return el("article", { class: "glass craft-card" }, head, summary);
    // The resources a craft takes, from what to what (the "system" readout).
    const needs = el("ul", { class: "craft-needs" }, r.rows.map((x) => el("li", { class: x.status },
      el("span", {}, x.recipe_text + " " + x.name),
      el("span", { class: "dim" }, x.mismatch ? "kept in " + (x.have_text || "another unit") + ": can't compare, change one unit"
        : x.short ? "have " + x.have_text + " · need " + n(x.short) + " more"
        : x.after_text ? "✓ " + x.have_text + " → " + x.after_text : "✓ have it"))));
    return el("article", { class: "glass craft-card open" }, head, summary,
      r.description ? el("p", {}, r.description) : null,
      el("h4", {}, "What It Needs"), r.rows.length ? needs : el("p", { class: "dim" }, "Edit the recipe to list its materials, one per line."),
      r.shopping.length ? el("div", { class: "craft-shop" },
        el("h4", {}, "Shopping List" + (r.shopping_text ? " · about " + r.shopping_text : "")),
        el("pre", { class: "craft-list" }, r.shopping_list),
        buttons(btn("Copy List", "btn-ghost btn-small", () => copyList(r)), btn("Bought It", "btn-green btn-small", () => bought(r)),
          btn("From A Receipt", "btn-ghost btn-small", () => fromReceipt(r)))) : null,
      r.cut_list ? [el("h4", {}, "Cut List"), el("pre", { class: "craft-list" }, r.cut_list)] : null,
      r.tools ? [el("h4", {}, "Tools"), el("p", { class: "dim" }, r.tools)] : null,
      r.steps.length ? [el("h4", {}, "Steps"), el("ol", { class: "craft-steps" }, r.steps.map((s) => el("li", {}, s)))] : null,
      r.built ? [el("h4", {}, "How It's Gone"), tiles(["Built", String(r.built)], ["Sold", String(r.sold)],
        r.actual.cost ? ["Avg. Cost", r.actual.cost] : null, r.actual.profit ? ["Avg. Profit", r.actual.profit] : null,
        r.actual.per_hour ? ["Per Hour", r.actual.per_hour] : null)] : null,
      r.notes ? el("p", { class: "dim" }, r.notes) : null,
      buttons(btn(r.is_batch ? "Begin Crafting" : "Start Build", "btn-amber", () => startBuild(r)), btn("Edit", "btn-ghost btn-small", () => edit("craft_recipe", r)),
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

  // ------------------------------------------------------------ homestead goods (DEC-0036)
  const FRESH = { fresh: ["Fresh", "chip-ok"], "sell first": ["Sell First", "chip-soon"], past: ["Past Sell-By", "chip-bad"], keeps: ["Keeps", ""] };
  const num = (name, def) => ({ name, type: "amount", required: false, options: [], default: def });

  const quickSell = (g, q) => act({ kind: "goods.sell", params: { recipe_id: g.recipe_id, quantity: q || 1 } }, { quick: true });
  async function sellSome(g) {
    const v = await form("Sold " + g.name, [
      { name: "quantity", label: "How many" + (g.unit ? " " + g.unit : ""), type: "amount", required: true, options: [], default: 1 },
      { name: "amount", label: "What they sold for in all (blank: " + (g.price_text || "the price") + " each)", type: "money", required: false, options: [], default: null }], {});
    if (v) act({ kind: "goods.sell", params: Object.assign({ recipe_id: g.recipe_id }, v) });
  }
  async function toss(g, lot) {
    const v = await form("Toss From The " + day(lot.made) + " Batch", [
      { name: "quantity", label: "How many (" + lot.left_text + " left)", type: "amount", required: true, options: [], default: lot.left }], {});
    if (v) act({ kind: "goods.toss", params: { job_id: lot.job_id, quantity: v.quantity } });
  }
  async function openMarket() {
    const fields = [{ name: "place", label: "Where (the stand, the farmers market…)", type: "text", required: false, options: [], default: null }]
      .concat(page.goods.filter((g) => g.on_hand > 0).map((g) => Object.assign(num("b_" + g.recipe_id, g.usual ? Math.min(g.usual.bring, g.on_hand) : g.on_hand),
        { label: g.name + ": how many you're taking (" + g.on_hand_text + " on hand" + (g.usual ? ", " + g.usual.text : "") + ")" })));
    const v = await form("Open A Market Day", fields, {});
    if (v) act({ kind: "market.start", params: v });
  }
  async function closeMarket(m) {
    const left = m.rows.filter((r) => r.left > 0);
    const fields = left.map((r) => Object.assign(num("t_" + r.recipe_id, null),
      { label: r.name + ": " + n(r.left) + " left; how many to toss (blank keeps them in stock)" }));
    const v = fields.length ? await form("Close The Day", fields, {}) : {};
    if (v) act({ kind: "market.close", params: Object.assign({ market_id: m.id }, v) });
  }
  async function labelSettings() {
    const v = await form("What Every Label Says", page.label_form, page.label || {});
    if (v) act({ kind: "goods.label", params: v });
  }
  const printLabels = (g, lot) => window.open("label.html?recipe=" + encodeURIComponent(g.recipe_id) + (lot ? "&job=" + encodeURIComponent(lot.job_id) : ""), "_blank");

  function marketPanel() {
    const m = page.market;
    if (!m) return section("Market Day", btn("Open Market Day", "btn-amber", openMarket),
      el("p", { class: "dim" }, "Taking goods to the stand or the market? Open the day, tap what sells, and close it for the tally."));
    const forSale = page.goods.filter((g) => g.on_hand > 0);
    return section("Market Day" + (m.place ? " · " + m.place : ""), btn("Close The Day", "btn-amber", () => closeMarket(m)),
      tiles(["Sold", n(m.sold)], ["Took In", m.revenue_text], ["Profit", m.profit_text, m.profit < 0 ? "bad" : "ok"]),
      el("div", { class: "market-taps" }, forSale.map((g) => {
        const today = m.rows.find((r) => r.recipe_id === g.recipe_id);
        return el("div", { class: "glass market-tap" },
          el("div", {}, el("strong", {}, g.name), el("div", { class: "dim" },
            (today ? n(today.sold) + " sold · " : "") + g.on_hand_text + " left" + (g.price_text ? " · " + g.price_text : ""))),
          buttons(btn("+1 Sold", "btn-green", () => quickSell(g, 1)), btn("Other…", "btn-ghost btn-small", () => sellSome(g))));
      })),
      !forSale.length ? el("p", { class: "empty" }, "Nothing left to sell. Close the day for the tally.") : null);
  }

  function goodsCard(g) {
    return el("article", { class: "glass craft-card open" },
      el("div", { class: "craft-head static" },
        el("div", {}, el("h3", {}, g.name), el("p", { class: "dim" }, [g.on_hand_text + " on hand", g.price_text ? g.price_text + " each" : null,
          g.usual ? g.usual.text : null].filter(Boolean).join(" · "))),
        g.sell_first ? chip("Sell First", "chip-soon") : g.on_hand ? chip("In Stock", "chip-ok") : chip("None Made")),
      g.lots.length ? el("ul", { class: "goods-lots" }, g.lots.map((lot) => el("li", { class: "goods-lot " + lot.state.replace(" ", "-") },
        el("div", {}, el("strong", {}, lot.left_text), el("span", { class: "dim" }, " · made " + day(lot.made) +
          (lot.sell_by ? " · sell by " + day(lot.sell_by) : "") + (lot.unit_cost_text ? " · " + lot.unit_cost_text + " each to make" : ""))),
        chip(...FRESH[lot.state]),
        buttons(btn("Labels", "btn-ghost btn-small", () => printLabels(g, lot)), btn("Toss", "btn-ghost btn-small", () => toss(g, lot))))))
        : el("p", { class: "dim" }, "None on hand. Open the recipe and Begin Crafting."),
      g.on_hand ? buttons(btn("Sold Some", "btn-green", () => sellSome(g))) : null);
  }

  function pastMarkets() {
    if (!page.markets.length) return null;
    return section("Past Market Days", null, el("div", { class: "rows" }, page.markets.map((m) => row(
      (m.place || "Market day") + " · " + day(m.date),
      m.rows.filter((r) => r.sold || r.brought).map((r) => r.name + " " + n(r.sold) + (r.brought ? "/" + n(r.brought) : "")).join(", "),
      [chip(m.revenue_text, "chip-ok")], el("span", { class: "dim" }, "profit " + m.profit_text)))));
  }

  const VIEWS = {
    recipes: () => section("Recipes", btn("Add Recipe", "btn-amber", () => add("craft_recipe", "Add A Recipe")),
      page.recipes.length ? el("div", { class: "craft-grid" }, page.recipes.map(recipeCard))
        : el("p", { class: "empty" }, "Save something you build as a recipe: what it needs, the cut list, the steps and what it sells for. MIA checks your materials and makes the shopping list.")),
    goods: () => [
      marketPanel(),
      section("Goods On Hand", btn("Label Info", "btn-ghost btn-small", labelSettings),
        page.goods.length ? el("div", { class: "craft-grid" }, page.goods.map(goodsCard))
          : el("p", { class: "empty" }, "Things you make in batches show here: hot honey, salve, bread. Add a recipe with what one batch makes (12 jars), then Begin Crafting.")),
      pastMarkets(),
    ].filter(Boolean),
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
    $("strip").replaceChildren(...[
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.recipes || 0), el("span", { class: "t" }, "Recipes")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.open_jobs), el("span", { class: "t" }, "Building")),
      el("div", { class: "cell " + (c.low ? "bad" : "ok") }, el("span", { class: "n" }, c.low), el("span", { class: "t" }, "Low Materials")),
      c.goods ? el("div", { class: "cell " + (c.sell_first ? "soon" : "ok") }, el("span", { class: "n" }, n(c.goods)),
        el("span", { class: "t" }, c.sell_first ? c.sell_first + " To Sell First" : "Goods On Hand")) : null,
    ].filter(Boolean));
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
