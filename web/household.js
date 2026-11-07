/*
 * household.js — the household's routines (claude, 2026-11-06; the design
 * canvas's Household, DEC-0113, 2026-11-07).
 * Renders MIA.household() (core/household_routines.py): Done Today with its
 * meter, then a card per routine (what it is, daily or this week, its streak
 * in words) with Did It, or Done; what's still to do comes first. Add a
 * Routine, Pause and Resume are routine.add / routine.pause / routine.resume
 * (core/routine_actions.py); "Did it" is routine.log, so undo takes it
 * back. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let data = null;
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);

  async function addRoutine() {
    const v = await form("Add a Routine", data.forms.routine.fields, {});
    if (v) act({ kind: "routine.add", params: v });
  }

  function routineCard(r) {
    return el("div", { class: "glass hh-row" + (r.done ? " done" : "") },
      el("div", { class: "hh-main" }, el("span", { class: "hh-name" }, r.name),
        el("span", { class: "dim" }, r.when + " · " + (r.target > 1 ? r.progress + " of " + r.target + " · " : "") + r.streak_text)),
      r.done ? el("span", { class: "hh-done" }, "Done")
        : btn("Did It", "btn-ghost hh-did", () => act({ kind: "routine.log", params: { template_id: r.id } }, { quick: true })),
      el("details", { class: "row-more" }, el("summary", { "aria-label": "More for " + r.name }, "⋯"),
        el("div", { class: "row-more-menu" }, btn("Pause", "btn-ghost btn-small", () => act({ kind: "routine.pause", params: { template_id: r.id } })))));
  }

  function paint() {
    if (window.MIAIcons) MIAIcons.badge(document.querySelector(".hero h1 > span[aria-hidden]"), "household");
    $("house-sub").textContent = data.total ? data.done + " of " + data.total + " done today" : "No routines yet.";
    $("panel").replaceChildren(...[
      data.total ? el("section", { class: "glass hh-today", "aria-label": "Done today" },
        el("div", { class: "hh-today-top" }, el("span", { class: "pw-label" }, "Done Today"), el("span", { class: "hh-count" }, data.done + " / " + data.total)),
        el("div", { class: "meter" }, el("div", { class: "meter-fill " + (data.done === data.total ? "gold" : "ok"), style: "width:" + data.pct + "%" }))) : null,
      data.total ? el("div", { class: "hh-list" }, ...data.routines.map(routineCard))
        : el("p", { class: "empty" }, "No routines yet. Add one (dishes, laundry, the trash) or tell MIA: \"add a daily routine to do the dishes\"."),
      data.paused.length ? el("section", { class: "glass tb-list" }, el("p", { class: "pw-label" }, "Paused"),
        ...data.paused.map((r) => el("div", { class: "fk-row" }, el("div", { class: "fk-row-main" }, el("span", { class: "tb-row-name" }, r.name),
          el("span", { class: "dim" }, r.when + " · its streak and history are kept")),
          btn("Resume", "btn-ghost btn-small", () => act({ kind: "routine.resume", params: { template_id: r.id } }))))) : null,
      el("div", { class: "row-buttons" }, btn("Add a Routine", "btn-ghost", addRoutine)),
      el("p", { class: "dim hh-say" }, "Or just tell MIA: \"I did the dishes\", \"pause the vacuum routine\"."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { data = await MIA.household(); paint(); }, { refreshOnChange: true });
})();
