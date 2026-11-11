/*
 * businesses.js — Finances › Businesses (claude, 2026-11-11, DEC-0153).
 * Renders MIA.businesses() (core/web_businesses.businesses_page): a card per business with this month's and this
 * year's money, what it owes, its properties and open orders and quotes, each opening its own dashboard (biz.html);
 * the orders and quotes with no business yet; then the apps the businesses use. Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function card(b) {
    const facts = [b.properties ? b.properties + (b.properties === 1 ? " property" : " properties") : null,
      b.open_orders ? b.open_orders + (b.open_orders === 1 ? " open order" : " open orders") : null,
      b.open_quotes ? b.open_quotes + (b.open_quotes === 1 ? " open quote" : " open quotes") : null].filter(Boolean);
    return el("a", { class: "glass hub-tile biz-card", href: b.page },
      el("span", { class: "hub-ico", "aria-hidden": "true" }, (window.MIAIcons && MIAIcons.svg("business")) || "•"),
      el("span", { class: "hub-name" }, b.name, el("small", { class: "dim" }, " · " + b.type)),
      el("span", { class: "hub-line" },
        el("span", { class: "biz-net" + (b.month.net_value < 0 ? " neg" : "") }, b.month.net + " this month"),
        " · " + b.year.net + " this year" + (b.owes_value > 0 ? " · owes " + b.owes : ""),
        facts.length ? el("small", { class: "biz-facts" }, facts.join(" · ")) : null));
  }

  MIAShell.start(async () => {
    const [page, hub] = await Promise.all([MIA.businesses(), MIA.hub("businesses").catch(() => null)]);
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "Businesses come from Money, which isn't set up on this MIA."));
      return;
    }
    $("biz-sub").textContent = page.businesses.length
      ? "Each business at a glance. Open one for its own dashboard."
      : "No businesses yet.";
    const t = page.totals;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.businesses.length), el("span", { class: "t" }, "Businesses")),
      el("div", { class: "cell " + (t.month_net_value < 0 ? "bad" : "ok") }, el("span", { class: "n" }, t.month_net), el("span", { class: "t" }, "Net This Month")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, t.open_orders), el("span", { class: "t" }, "Open Orders")));
    $("panel").replaceChildren(...[
      page.businesses.length ? el("div", { class: "hub-grid biz-grid" }, page.businesses.map(card))
        : el("p", { class: "empty" }, "Add a business in Money (Businesses) and tag its income and expenses; it shows here with its own dashboard."),
      page.unsorted ? el("a", { class: "glass biz-unsorted", href: page.unsorted.page },
        page.unsorted.count + (page.unsorted.count === 1 ? " order or quote has" : " orders and quotes have") + " no business yet. Sort them ›") : null,
      hub && hub.apps.length ? el("section", { class: "hub-shortcuts" }, el("h2", { class: "hub-head" }, "The Apps They Use"),
        el("div", { class: "hub-grid" }, hub.apps.map((a) => el("a", { class: "glass hub-tile", href: a.page },
          el("span", { class: "hub-ico", "aria-hidden": "true" }, (window.MIAIcons && (MIAIcons.svg(a.id) || MIAIcons.svg(a.icon))) || "•"),
          el("span", { class: "hub-name" }, a.name), el("span", { class: "hub-line" }, a.tagline || ""))))) : null,
    ].filter(Boolean));
  });
})();
