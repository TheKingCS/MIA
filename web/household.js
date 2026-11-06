/*
 * household.js — the household's routines (claude, 2026-11-06).
 * Renders MIA.household() (core/household_routines.py): each routine's
 * current occurrence (today's, or this week's), how far along it is, its
 * streak, and the day's total. "Did it" is routine.log, so undo takes it
 * back. Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function paint(data) {
    $("house-sub").textContent = data.total ? data.done + " of " + data.total + " done" : "No routines yet.";
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, data.total ? "Laundry, dishes and the rest: tick one when it's done, or just tell MIA (\"I did the dishes\")."
          : "Ask MIA to add one: \"add a daily routine to do the dishes\"."),
        data.total ? el("progress", { max: String(data.total), value: String(data.done), "aria-label": "Done today" }) : null),
      data.total ? el("section", { class: "glass money-section" },
        el("div", { class: "sync-rows" }, data.routines.map((r) => el("div", { class: "sync-row council-msg" },
          el("div", {}, el("p", { class: "council-text" }, (r.done ? "✓ " : "") + r.name),
            el("p", { class: "dim" }, (r.target > 1 ? r.progress + " of " + r.target + " · " : "")
              + (r.streak ? r.streak + "-" + r.every + " streak" : "a new streak starts") + (r.every === "week" ? " · weekly" : ""))),
          r.done ? null : el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-amber btn-small",
            onclick: () => MIAShell.act({ kind: "routine.log", params: { template_id: r.id } }, { quick: true }) }, "Did it")))))) : null);
  }

  MIAShell.start(async () => { paint(await MIA.household()); }, { refreshOnChange: true });
})();
