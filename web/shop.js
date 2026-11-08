/*
 * shop.js — the Reward Shop (claude, 2026-10-17, DEC-0028). Renders
 * MIA.shop() (core/game_layer.py): credits earned / spent / left, the
 * rewards you set (ready to buy first, then how far off the rest are),
 * ideas to start with, and what you've bought. Buy proposes shop.buy;
 * undo gives the credits back. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const n = (x) => Number(x).toLocaleString();
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";

  async function add(values) {
    const v = await form("Add A Reward", page.forms.shop_reward.fields, values || {});
    if (v) act({ kind: "shop_reward.add", params: v });
  }
  async function edit(r) {
    const v = await form("Edit " + r.name, page.forms.shop_reward.fields, r.values);
    if (v) act({ kind: "shop_reward.edit", params: Object.assign({ reward_id: r.id }, v) });
  }

  // ⋯ for Edit and Delete, so each card leads with what it's for (the canvas, DEC-0113).
  const more = (r) => el("details", { class: "row-more" }, el("summary", { "aria-label": "More for " + r.name }, "⋯"),
    el("div", { class: "row-more-menu" }, btn("Edit", "btn-ghost btn-small", () => edit(r)),
      btn("Delete", "btn-ghost btn-small", () => act({ kind: "shop_reward.delete", params: { reward_id: r.id } }))));

  function readyRow(r) {
    return el("div", { class: "glass sh-ready" },
      el("div", { class: "sh-main" }, el("span", { class: "sh-name" }, r.name), el("span", { class: "sh-cost" }, n(r.cost) + " credits"
        + (r.bought ? " · bought " + r.bought + "×" : r.repeatable ? "" : " · just once"))),
      btn("Buy", "btn-green sh-buy", () => act({ kind: "shop.buy", params: { reward_id: r.id } })), more(r));
  }
  function savingCard(r) {
    return el("div", { class: "glass sh-saving" },
      el("div", { class: "sh-top" }, el("span", { class: "sh-name" }, r.name), el("span", { class: "sh-cost" }, n(r.cost)), more(r)),
      el("div", { class: "meter" }, el("div", { class: "meter-fill", style: "width:" + r.percent + "%" })),
      el("span", { class: "dim" }, n(r.to_go) + " more credits"));
  }

  function draw() {
    const c = page.credits;
    $("strip").hidden = true;
    const ready = page.rewards.filter((r) => r.available && r.affordable);
    const saving = page.rewards.filter((r) => r.available && !r.affordable);
    const claimed = page.rewards.filter((r) => !r.available);
    $("panel").replaceChildren(...[
      el("div", { class: "sh-tiles" },
        el("div", { class: "glass sh-tile" }, el("span", { class: "pw-label" }, "Earned"), el("strong", {}, n(c.earned))),
        el("div", { class: "glass sh-tile" }, el("span", { class: "pw-label" }, "Spent"), el("strong", {}, n(c.spent))),
        el("div", { class: "glass sh-tile left" }, el("span", { class: "pw-label" }, "Left"), el("strong", {}, n(c.left)))),
      ready.length ? el("p", { class: "pw-label sh-label" }, "Ready to Buy") : null,
      ...ready.map(readyRow),
      saving.length ? el("p", { class: "pw-label sh-label" }, "Saving Toward") : null,
      ...saving.map(savingCard),
      !page.rewards.length ? el("p", { class: "empty" }, "Your shop is empty. Add the rewards you'd love to earn: a treat, a night off, new gear.") : null,
      btn("Add a Reward", "btn-ghost sh-add", () => add()),
      page.ideas.length ? section("Ideas", null, el("p", { class: "dim" }, "Tap one to add it, then make it yours."),
        el("div", { class: "chip-row" }, page.ideas.map((i) =>
          el("button", { type: "button", class: "chip chip-button", onclick: () => add({ name: i.name, cost: i.cost, icon: i.icon }) },
            i.icon + " " + i.name + " · " + n(i.cost))))) : null,
      claimed.length ? section("Claimed", null, el("div", { class: "rows" }, claimed.map((r) => el("div", { class: "row money-row" },
        el("div", { class: "row-title" }, r.icon + " " + r.name), more(r))))) : null,
      page.bought.length ? section("Bought", null, el("div", { class: "rows" }, page.bought.map((b) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, b.icon + " " + b.name), el("div", { class: "row-sub" }, day(b.when))),
        el("span", { class: "chip" }, "−" + n(b.cost) + " cr"))))) : null,
      el("p", { class: "dim" }, "Credits come from missions and challenges. Spending never lowers your level: XP and your all-time credits stay."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.shop();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "The Reward Shop isn't set up on this MIA."));
      return;
    }
    draw();
  });
})();
