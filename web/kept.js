/*
 * kept.js — Kept (claude, 2026-11-06, DEC-0054).
 * Renders MIA.lifeNotes() (core/life_notes.py): the promises, decisions,
 * ideas and goals set aside the person asked MIA to keep. Done and Forget
 * go through actions (life_note.done / .forget), so undo takes them back.
 * Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);

  function paint(data) {
    const count = data.kinds.reduce((n, k) => n + k.notes.length, 0);
    $("kept-sub").textContent = count ? "What you said you'd do, decided, want to try and set aside." : "Nothing kept yet.";
    const groups = data.kinds.filter((k) => k.notes.length).map((k) => el("section", { class: "glass money-section" },
      el("h2", {}, k.title),
      el("div", { class: "sync-rows" }, k.notes.map((n) => el("div", { class: "sync-row council-msg" },
        el("div", {}, el("p", { class: "council-text" }, n.line),
          el("p", { class: "dim" }, (n.status === "done" ? "Done · " : "") + "noted " + n.at + (n.due && n.status !== "done" ? " · due " + n.due : ""))),
        el("div", { class: "row-buttons" },
          n.status !== "done" && (k.kind === "commitment" || k.kind === "idea")
            ? button("Done", () => MIAShell.act({ kind: "life_note.done", params: { note_id: n.id } }, { quick: true }), "btn-amber") : null,
          button("Forget", () => MIAShell.act({ kind: "life_note.forget", params: { note_id: n.id } }))))))));
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, "When you mention a promise (\"I told Sam I'd fix his gate by Saturday\"), a decision, an idea or a goal you're setting " +
          "aside, MIA offers to keep it; say \"keep it\" and it's here. A promise with a day is mentioned the day before and on it. " +
          "Ask \"what did I promise?\" any time.")),
      ...groups);
  }

  MIAShell.start(async () => { paint(await MIA.lifeNotes()); }, { refreshOnChange: true });
})();
