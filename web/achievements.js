/*
 * achievements.js — the Achievements page (claude, 2026-11-24, the game layer).
 * Renders MIA.achievements() (core/achievement_cards.py): how many are unlocked,
 * the structures built (and still to build), each chain's progress toward its
 * next tier, and the log of every unlock, newest first. A row in the log opens
 * its card again (MIAShell.cards via the frame). Read only: the one change,
 * marking cards seen, is the frame's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const RARITY = ["r-common", "r-uncommon", "r-rare", "r-epic", "r-legendary"];
  const section = (title, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title)), ...body);
  const bar = (pct) => el("div", { class: "bar" }, el("div", { class: "bar-fill", style: "width:" + Math.min(100, pct) + "%" }));
  const day = (when) => when ? new Date(when).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "Earlier";

  function structures(page) {
    return section("Built",
      el("div", { class: "rows" }, page.structures.map((s) => el("div", { class: "row rarity " + RARITY[s.rarity] + (s.earned ? "" : " locked") },
        el("div", {},
          el("div", { class: "row-title" }, (s.earned ? s.icon : "🔒") + " " + s.name),
          el("div", { class: "row-sub" }, el("span", { class: "rarity-tag" }, s.rarity_name), " " + s.description +
            (s.earned ? "" : " Mark its project Complete in the Workshop."))))) ));
  }

  function chains(page) {
    return section("On the way",
      el("div", { class: "rows" }, page.chains.map((c) => el("div", { class: "row chain-row rarity " + RARITY[(c.next || c.earned || {}).rarity || 0] },
        el("div", {},
          el("div", { class: "row-title" }, c.icon + " " + c.stat + " · " + c.value.toLocaleString() + (c.unit ? " " + c.unit : "")),
          c.next ? el("div", { class: "row-sub" }, "Next: " + c.next.icon + " " + c.next.name + " (" + c.next.rarity_name + ") · " +
            c.next.description) : el("div", { class: "row-sub" }, "Every tier earned"),
          c.next ? bar(c.next.percent) : null)))));
  }

  function logRows(page) {
    if (!page.earned.length) return section("Log", el("p", { class: "empty" }, "Nothing unlocked yet. Log a harvest, the eggs or a batch of jars, or finish a mission, and the first one comes quickly."));
    return section("Log",
      el("div", { class: "rows" }, page.earned.map((c) => el("div", { class: "row rarity " + RARITY[c.rarity], role: "button",
        tabindex: "0", "aria-label": c.name + ": show its card", onclick: () => MIAShell.achievementCard(c),
        onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); MIAShell.achievementCard(c); } } },
        el("div", {},
          el("div", { class: "row-title" }, c.icon + " " + c.name),
          el("div", { class: "row-sub" }, el("span", { class: "rarity-tag" }, c.rarity_name), " " + c.description + " · " + day(c.when)))))));
  }

  MIAShell.start(async () => {
    const page = await MIA.achievements();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "Achievements need a signed-in profile.")));
      return;
    }
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.counts.earned + "/" + page.counts.total), el("span", { class: "t" }, "Unlocked")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, page.structures.filter((s) => s.earned).length + "/" + page.structures.length), el("span", { class: "t" }, "Built")));
    $("panel").replaceChildren(logRows(page), chains(page), structures(page));
  });
})();
