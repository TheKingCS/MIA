/*
 * changes.js — Recent Changes (claude, 2026-11-07). Renders MIA.changes() (core/web_changes.py): what MIA changed for
 * the person lately, newest first (what, when, MIA or you), with Undo on the newest only, the same as saying "undo
 * that" (an older one would undo on top of what came after). Formatting only.
 */
(function () {
  "use strict";
  const { el, say } = MIAShell;
  const $ = (id) => document.getElementById(id);

  async function undo() {
    try { say((await MIA.undoLatest()).message); } catch (e) { say(e.message); }
    MIAShell.refresh();
  }

  function paint(data) {
    if (!data.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Recent changes aren't available on this MIA.")); return; }
    if (!data.changes.length) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "Nothing changed since MIA started. Changes MIA makes for you show here, newest first."));
      return;
    }
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("div", { class: "rows" }, data.changes.map((c) => el("div", { class: "row" },
          el("div", {}, el("div", { class: "row-title" }, c.what), el("div", { class: "row-sub" }, c.when + " · " + c.by)),
          c.latest ? el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: undo }, "Undo") : null)))),
      el("p", { class: "dim" }, "Only the newest can be undone, then the one before it. Kept since MIA started (the last 20). "
        + "Or say \"undo that\" in Talk."));
  }

  MIAShell.start(async () => { paint(await MIA.changes()); }, { refreshOnChange: true });
})();
