/*
 * biz.js — one business's own dashboard (claude, 2026-11-11, DEC-0153).
 * Renders MIA.oneBusiness(id) (core/web_businesses.business_dashboard): this month's and this year's money, where it
 * went, the latest income and expenses, its properties, its own Orders & Quotes (Zac: "a section under each business
 * with info specific to that business"; Add Quote and Add Order start in this business), its debts, and the apps it
 * uses. Formatting only; every change is an action (core/business_actions.py).
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const id = new URLSearchParams(location.search).get("id") || "";
  let page = null;

  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const row = (title, sub, right) => el("div", { class: "row money-row" },
    el("div", {}, el("div", { class: "row-title" }, title), sub ? el("div", { class: "row-sub" }, sub) : null), right || null);
  const empty = (text) => el("p", { class: "empty" }, text);

  // Add a quote or order already in this business; the rest of the form is Orders & Quotes' own (core).
  async function add(kind) {
    const book = await MIA.business(id).catch(() => null);
    if (!book || !book.available) { MIAShell.say("Orders & Quotes isn't set up on this MIA."); return; }
    const v = await form(kind === "quote" ? "New Quote" : "New Order", book.forms[kind].fields, { entity_id: id }, book.picks);
    if (v) act({ kind: kind + ".add", params: Object.assign({ entity_id: id }, v) });
  }

  function draw() {
    document.title = page.name + " — MIA";
    $("hero-name").textContent = page.name;
    $("biz-sub").textContent = page.type + (page.notes ? " · " + page.notes : "");
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.month.income), el("span", { class: "t" }, "In This Month")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, page.month.expenses), el("span", { class: "t" }, "Out This Month")),
      el("div", { class: "cell " + (page.year.net_value < 0 ? "bad" : "ok") }, el("span", { class: "n" }, page.year.net), el("span", { class: "t" }, "Net This Year")));
    const open = page.orders.filter((o) => o.open), quotes = page.quotes.filter((q) => q.open);
    $("panel").replaceChildren(...[
      section("Orders & Quotes", el("div", { class: "row-buttons" },
        el("button", { type: "button", class: "btn btn-small", onclick: () => add("quote") }, "Add Quote"),
        el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => add("order") }, "Add Order"),
        el("a", { class: "btn btn-ghost btn-small", href: page.orders_page }, "All of Them ›")),
        open.length || quotes.length ? el("div", { class: "rows" },
          open.map((o) => row(o.title, [o.customer, o.due ? "due " + day(o.due) : "", o.left_value ? o.left + " still owed" : ""].filter(Boolean).join(" · "),
            el("span", { class: "chip" + (o.overdue ? " chip-bad" : "") }, o.status))),
          quotes.map((q) => row("Quote: " + q.title, [q.customer, q.price].filter(Boolean).join(" · "), el("span", { class: "chip chip-soon" }, q.status))))
          : empty("No open orders or quotes for this business.")),
      page.properties.length ? section("Properties", el("a", { class: "btn btn-ghost btn-small", href: "real-estate.html" }, "Real Estate ›"),
        el("div", { class: "rows" }, page.properties.map((p) => row(p.name, [p.type, p.status, p.rent ? p.rent + " a month" : ""].filter(Boolean).join(" · "))))) : null,
      section("Where The Money Went This Year", null, page.spending.length
        ? el("div", { class: "rows" }, page.spending.map((s) => row(s.category, "", el("strong", {}, s.amount)))) : empty("No expenses tagged to it this year.")),
      section("Latest", el("a", { class: "btn btn-ghost btn-small", href: "money.html" }, "Money ›"),
        page.income.length || page.expenses.length ? el("div", { class: "rows" },
          page.income.map((r) => row(r.what, day(r.date) + " · " + r.category, el("strong", { class: "biz-in" }, "+" + r.amount))),
          page.expenses.map((r) => row(r.what, day(r.date) + " · " + r.category, el("strong", {}, "−" + r.amount))))
          : empty("Nothing tagged to it yet. Tag income and expenses to it in Money.")),
      page.debts.length ? section("What It Owes", null, el("div", { class: "rows" }, page.debts.map((d) => row(d.name, "", el("strong", {}, d.balance))))) : null,
      page.apps.length ? el("nav", { class: "hub-areas", "aria-label": "The apps it uses" },
        el("a", { class: "btn btn-ghost btn-small", href: "businesses.html" }, "‹ Businesses"),
        page.apps.map((a) => el("a", { class: "btn btn-ghost btn-small", href: a.page }, a.name)))
        : el("nav", { class: "hub-areas" }, el("a", { class: "btn btn-ghost btn-small", href: "businesses.html" }, "‹ Businesses")),
    ].filter(Boolean));
  }

  MIAShell.start(async () => {
    try { page = await MIA.oneBusiness(id); } catch (e) { page = null; }
    if (!page) {
      $("panel").replaceChildren(empty("That business isn't here. "), el("a", { class: "btn btn-ghost btn-small", href: "businesses.html" }, "‹ Businesses"));
      return;
    }
    draw();
  });
})();
