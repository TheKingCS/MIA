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

  function card(r) {
    return el("article", { class: "glass shop-card" + (r.affordable ? " ready" : "") + (r.available ? "" : " claimed") },
      el("div", { class: "shop-head" },
        el("span", { class: "shop-icon", "aria-hidden": "true" }, r.icon),
        el("div", { class: "shop-title" }, el("h3", {}, r.name), r.note ? el("p", { class: "dim" }, r.note) : null),
        el("span", { class: "shop-cost" }, n(r.cost), el("small", {}, " cr"))),
      r.available && !r.affordable ? el("div", { class: "shop-progress" },
        el("div", { class: "bar" }, el("div", { class: "bar-fill", style: "width:" + r.percent + "%" })),
        el("span", { class: "dim" }, n(r.to_go) + " to go")) : null,
      el("div", { class: "shop-foot" },
        el("span", { class: "dim" }, r.available ? (r.bought ? "Bought " + r.bought + "×" : r.repeatable ? "Any time" : "Just once")
          : "Claimed"),
        buttons(r.affordable ? btn("Buy", "btn-green", () => act({ kind: "shop.buy", params: { reward_id: r.id } })) : null,
          btn("Edit", "btn-ghost btn-small", () => edit(r)),
          btn("Delete", "btn-ghost btn-small", () => act({ kind: "shop_reward.delete", params: { reward_id: r.id } })))));
  }

  function draw() {
    const c = page.credits;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, n(c.left)), el("span", { class: "t" }, "Credits To Spend")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, page.counts.ready), el("span", { class: "t" }, "Ready To Buy")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, n(c.earned)), el("span", { class: "t" }, "Earned All Time")));
    $("panel").replaceChildren(...[
      section("Your Rewards", btn("Add Reward", "btn-amber", () => add()),
        page.rewards.length ? el("div", { class: "shop-grid" }, page.rewards.map(card))
          : el("p", { class: "empty" }, "Your shop is empty. Add the rewards you'd love to earn: a treat, a night off, new gear.")),
      page.ideas.length ? section("Ideas", null, el("p", { class: "dim" }, "Tap one to add it, then make it yours."),
        el("div", { class: "chip-row" }, page.ideas.map((i) =>
          el("button", { type: "button", class: "chip chip-button", onclick: () => add({ name: i.name, cost: i.cost, icon: i.icon }) },
            i.icon + " " + i.name + " · " + n(i.cost))))) : null,
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
