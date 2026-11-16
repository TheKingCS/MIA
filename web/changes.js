/*
 * changes.js — Recent Changes (claude, 2026-11-07, DEC-0125). Renders
 * MIA.changes() (core/web_changes.py): what MIA can still put back, newest
 * first, with Undo on the newest (the action undo.last, the same as saying
 * "undo that"), undo by time (history.undo, UI-3), then the last fortnight's
 * history by day, undone ones struck through. Formatting only.
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function draw(page) {
    if (window.MIAIcons) MIAIcons.badge($("hero-icon"), "issues");
    $("ch-sub").textContent = page.undoable.length ? page.undoable.length + " change" + (page.undoable.length === 1 ? "" : "s") + " MIA can put back"
      : "Nothing to undo right now.";
    $("panel").replaceChildren(...[
      el("section", { class: "glass ch-undo", "aria-label": "Changes MIA can put back" }, el("p", { class: "pw-label" }, "Can Be Undone"),
        ...(page.undoable.length ? page.undoable.map((c) => el("div", { class: "ch-change" + (c.newest ? " newest" : "") },
          el("div", { class: "ch-what" }, el("span", {}, c.what), el("span", { class: "dim" }, c.when + " · " + c.by)),
          c.newest ? el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => act({ kind: "undo.last", params: {} }) }, "Undo") : null))
          : [el("p", { class: "dim" }, "Nothing since MIA started. Changes made from now on show here.")]),
        el("p", { class: "dim ch-note" }, "Undo goes newest first, the same as saying “undo that”. MIA keeps the last 20 since she started.")),
      byTime(page),
      el("p", { class: "pw-label ch-label" }, "The Last " + page.history_days + " Days"),
      ...(page.history.length ? page.history.map((d) => el("section", { class: "glass ch-day" }, el("p", { class: "ch-day-name" }, d.day),
        ...d.events.map((e) => el("div", { class: "ch-event" + (e.undone ? " undone" : "") },
          el("span", { class: "ch-when" }, e.when), el("span", {}, e.what + (e.by_mia ? " · by MIA" : "")))))) :
        [el("p", { class: "empty" }, "Nothing in the history yet.")]),
    ].filter(Boolean));
  }

  // Undo by time (UI-3, core/change_history.py): a time and, if wanted, what it was about; the approval card lists
  // exactly which changes go back before anything does (the action history.undo).
  function byTime(page) {
    const choices = page.when_choices || [];
    if (!choices.length) return null;
    const when = el("select", { "aria-label": "When" }, ...choices.map((c) => el("option", { value: c.id }, c.name)));
    const what = el("input", { type: "text", maxlength: "80", placeholder: "About what? (optional: the greenhouse, the budget)",
      "aria-label": "What the changes were about" });
    return el("section", { class: "glass ch-undo ch-bytime", "aria-label": "Undo by time" },
      el("p", { class: "pw-label" }, "Undo By Time"),
      el("div", { class: "ch-bytime-row" }, when, what,
        el("button", { type: "button", class: "btn btn-small",
          onclick: () => act({ kind: "history.undo", params: { when: when.value, what: what.value.trim() } }) }, "Undo These…")),
      el("p", { class: "dim ch-note" }, "MIA keeps every change for 30 days. You'll see exactly which ones first; anything changed again since stays as it is."));
  }

  MIAShell.start(async () => draw(await MIA.changes()));
})();
