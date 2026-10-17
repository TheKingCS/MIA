/*
 * business.js — Orders & Quotes (claude, 2026-10-17, DEC-0030 phase C).
 * Renders MIA.business() (core/web_business.py) in tabs: Orders (what's
 * owed, Payment, Start Build, Ready / Delivered), Quotes (what the price
 * is made of, Sent / Accepted / Declined), Customers, and the Portfolio of
 * finished builds (Feature). Every button proposes an action from
 * core/business_actions.py. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["orders", "Orders"], ["quotes", "Quotes"], ["customers", "Customers"], ["portfolio", "Portfolio"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "orders";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const STATUS = { Open: "", Building: "chip-soon", Ready: "chip-ok", Delivered: "chip-ok", Cancelled: "chip-bad",
    Draft: "", Sent: "chip-soon", Accepted: "chip-ok", Declined: "chip-bad" };

  async function add(key, title) {
    const v = await form(title, page.forms[key].fields, {}, page.picks);
    if (v) act({ kind: key + ".add", params: v });
  }
  async function edit(key, item, name) {
    const v = await form("Edit " + name, page.forms[key].fields, item.values, page.picks);
    if (v) act({ kind: key + ".edit", params: Object.assign({ [page.forms[key].id_param]: item.id }, v) });
  }
  const del = (key, item) => act({ kind: key + ".delete", params: { [page.forms[key].id_param]: item.id } });
  async function pay(o) {
    const v = await form("Payment On " + o.title, [{ name: "amount", label: "What they paid", type: "money", required: true, options: [], default: o.left_value || null }], {});
    if (v) act({ kind: "order.pay", params: { order_id: o.id, amount: v.amount } });
  }
  async function accept(q) {
    const v = await form("Accept " + q.title, [{ name: "due_date", label: "When it's due (optional)", type: "date", required: false, options: [], default: null }], {});
    if (v) act({ kind: "quote.accept", params: { quote_id: q.id, due_date: v.due_date } });
  }
  const status = (o, s) => act({ kind: "order.status", params: { order_id: o.id, status: s } });
  // MIA drafts the quote email; you check it and press Send (never sent by itself).
  async function emailQuote(q) {
    if (!(await act({ kind: "quote.email", params: { quote_id: q.id } }))) return;
    try {
      const all = await MIA.emailDrafts();
      const d = all.drafts.find((x) => x.subject === "Your quote: " + q.title) || all.drafts[0];
      if (d) MIAShell.showDraft(d, all.can_send);
    } catch (e) { MIAShell.say(e.message); }
  }

  function orderCard(o) {
    return el("article", { class: "glass craft-card" + (o.overdue ? " overdue" : "") },
      el("div", { class: "craft-head static" },
        el("div", {}, el("h3", {}, o.title), el("p", { class: "dim" },
          [o.customer, o.quantity > 1 ? o.quantity + " ×" : null, o.recipe, o.due ? "due " + day(o.due) : null].filter(Boolean).join(" · "))),
        chip(o.overdue ? "Past Due" : o.status, o.overdue ? "chip-bad" : STATUS[o.status])),
      el("div", { class: "craft-tiles" },
        el("div", { class: "craft-tile" }, el("span", { class: "dim" }, "Price"), el("strong", {}, o.price)),
        el("div", { class: "craft-tile ok" }, el("span", { class: "dim" }, "Paid"), el("strong", {}, o.paid)),
        el("div", { class: "craft-tile" + (o.left_value > 0 ? "" : " ok") }, el("span", { class: "dim" }, "Left"), el("strong", {}, o.left)),
        o.build && o.build.finished ? el("div", { class: "craft-tile ok" }, el("span", { class: "dim" }, "Build Profit"), el("strong", {}, o.build.profit)) : null),
      o.build && !o.build.finished ? el("p", { class: "dim" }, "Building" + (o.build.steps ? " · " + o.build.steps + " steps" : "") + " · ",
        el("a", { href: "workshop.html#builds" }, "open the build")) : null,
      o.notes ? el("p", { class: "dim" }, o.notes) : null,
      o.open ? buttons(o.left_value > 0 ? btn("Payment", "btn-green btn-small", () => pay(o)) : null,
        o.has_recipe && !o.build ? btn("Start Build", "btn-amber btn-small", () => act({ kind: "order.build", params: { order_id: o.id } })) : null,
        o.status !== "Ready" ? btn("Ready", "btn-ghost btn-small", () => status(o, "Ready")) : null,
        btn("Delivered", "btn-ghost btn-small", () => status(o, "Delivered")),
        btn("Edit", "btn-ghost btn-small", () => edit("order", o, o.title)),
        btn("Cancel Order", "btn-ghost btn-small", () => status(o, "Cancelled"))) : null);
  }

  function quoteCard(q) {
    return el("article", { class: "glass craft-card" },
      el("div", { class: "craft-head static" },
        el("div", {}, el("h3", {}, q.title), el("p", { class: "dim" },
          [q.customer, q.quantity > 1 ? q.quantity + " ×" : null, q.recipe, q.valid_until ? "good until " + day(q.valid_until) : null].filter(Boolean).join(" · "))),
        chip(q.status, STATUS[q.status])),
      el("div", { class: "craft-tiles" },
        el("div", { class: "craft-tile ok" }, el("span", { class: "dim" }, "Price"), el("strong", {}, q.price)),
        q.custom_price && q.suggested ? el("div", { class: "craft-tile" }, el("span", { class: "dim" }, "Suggested"), el("strong", {}, q.suggested)) : null),
      q.parts.length ? el("ul", { class: "craft-needs" }, q.parts.map(([label, value]) => el("li", {}, el("span", {}, label), el("span", { class: "dim" }, value)))) : null,
      q.notes ? el("p", { class: "dim" }, q.notes) : null,
      buttons(q.open ? btn("Email Quote", "btn-amber btn-small", () => emailQuote(q)) : null,
        q.open && q.status === "Draft" ? btn("Sent", "btn-ghost btn-small", () => act({ kind: "quote.send", params: { quote_id: q.id } })) : null,
        q.open ? btn("Accepted", "btn-green btn-small", () => accept(q)) : null,
        q.open ? btn("Declined", "btn-ghost btn-small", () => act({ kind: "quote.decline", params: { quote_id: q.id } })) : null,
        q.open ? btn("Edit", "btn-ghost btn-small", () => edit("quote", q, q.title)) : null,
        btn("Delete", "btn-ghost btn-small", () => del("quote", q))));
  }

  const mediaUrl = (p, m) => "/api/workshop/builds/" + encodeURIComponent(p.id) + "/media?name=" + encodeURIComponent(m.name);
  function portfolioCard(p) {
    const pics = p.photos.filter((m) => m.kind === "image");
    const shown = pics.filter((m) => m.tag === "after").concat(pics.filter((m) => m.tag !== "after")).slice(0, 4);
    return el("article", { class: "glass craft-card" + (p.featured ? " featured" : "") },
      el("div", { class: "craft-head static" }, el("div", {}, el("h3", {}, p.name),
        el("p", { class: "dim" }, [p.dimensions, p.sold ? "sold for " + p.sold : null].filter(Boolean).join(" · "))),
        p.featured ? chip("Featured", "chip-ok") : null),
      shown.length ? el("div", { class: "media-grid" }, shown.map((m) => {
        const img = el("img", { alt: p.name + (m.tag ? " (" + m.tag + ")" : ""), loading: "lazy" });
        MIA.image(mediaUrl(p, m)).then((src) => { if (src) img.src = src; });
        return el("div", { class: "media-tile kind-image" }, img, m.tag ? el("span", { class: "craft-tag tag-" + m.tag }, m.tag === "during" ? "Progress" : m.tag.charAt(0).toUpperCase() + m.tag.slice(1)) : null);
      })) : el("p", { class: "dim" }, "No photos yet: add before and after photos on the build."),
      p.description ? el("p", {}, p.description) : null,
      buttons(btn(p.featured ? "Unfeature" : "Feature", "btn-ghost btn-small", () => act({ kind: "portfolio.feature", params: { job_id: p.id } }))));
  }

  const VIEWS = {
    orders: () => {
      const open = page.orders.filter((o) => o.open), done = page.orders.filter((o) => !o.open);
      return [section("Orders", btn("Add Order", "btn-amber", () => add("order", "Add An Order")),
        open.length ? el("div", { class: "craft-grid" }, open.map(orderCard))
          : el("p", { class: "empty" }, "No open orders. Accept a quote, or add an order someone placed.")),
      done.length ? section("Done", null, el("div", { class: "craft-grid" }, done.map(orderCard))) : null].filter(Boolean);
    },
    quotes: () => section("Quotes", btn("Add Quote", "btn-amber", () => add("quote", "Add A Quote")),
      page.quotes.length ? el("div", { class: "craft-grid" }, page.quotes.map(quoteCard))
        : el("p", { class: "empty" }, "Price a job: pick a recipe and MIA adds up its materials, your time, extras and your margin.")),
    customers: () => section("Customers", btn("Add Customer", "btn-amber", () => add("customer", "Add A Customer")),
      page.customers.length ? el("div", { class: "rows" }, page.customers.map((c) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, c.name),
          el("div", { class: "row-sub" }, [c.phone, c.email, c.orders ? c.orders + (c.orders === 1 ? " order" : " orders") : null,
            c.spent ? "paid " + c.spent : null].filter(Boolean).join(" · "))),
        buttons(btn("Edit", "btn-ghost btn-small", () => edit("customer", c, c.name)), btn("Delete", "btn-ghost btn-small", () => del("customer", c))))))
        : el("p", { class: "empty" }, "No customers yet.")),
    portfolio: () => section("Portfolio", null,
      page.portfolio.length ? el("div", { class: "craft-grid" }, page.portfolio.map(portfolioCard))
        : el("p", { class: "empty" }, "Finished builds show here with their photos. Feature your best ones.")),
  };

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.open_orders), el("span", { class: "t" }, "Open Orders")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.open_quotes), el("span", { class: "t" }, "Open Quotes")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.owed), el("span", { class: "t" }, "Still Owed")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...[].concat(VIEWS[tab]()));
  }

  MIAShell.start(async () => {
    page = await MIA.business();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "Orders & Quotes isn't set up on this MIA."));
      return;
    }
    draw();
  });
})();
