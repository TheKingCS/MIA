/*
 * kept.js — Kept (claude, 2026-11-06, DEC-0054).
 * Renders MIA.lifeNotes() (core/life_notes.py): the promises, decisions,
 * ideas and goals set aside the person asked MIA to keep. Done and Forget
 * go through actions (life_note.done / .forget), so undo takes them back.
 * Formatting only; laid out as the design canvas's Kept (DEC-0113): a card per note.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);

  const day = (iso) => iso ? new Date(iso.slice(0, 10) + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";

  // The design canvas (DEC-0113): a label per kind, then a card per note: what was said, when, Done and Forget.
  function paint(data) {
    const count = data.kinds.reduce((n, k) => n + k.notes.length, 0);
    $("kept-sub").textContent = count ? "What you said you'd do, decided, want to try and set aside." : "Nothing kept yet.";
    const groups = data.kinds.filter((k) => k.notes.length).map((k) => el("section", { class: "kp-group" },
      el("p", { class: "pw-label" }, k.title),
      ...k.notes.map((n) => el("div", { class: "glass kp-note" + (n.status === "done" ? " done" : "") },
        el("p", { class: "kp-line" }, n.line),
        el("div", { class: "kp-foot" },
          el("span", { class: "dim" }, (n.status === "done" ? "Done · " : "") + "Kept " + day(n.at) +
            (n.due && n.status !== "done" ? " · due " + day(n.due) : "")),
          el("div", { class: "row-buttons" },
            n.status !== "done" && (k.kind === "commitment" || k.kind === "idea")
              ? button("Done", () => MIAShell.act({ kind: "life_note.done", params: { note_id: n.id } }, { quick: true })) : null,
            button("Forget", () => MIAShell.act({ kind: "life_note.forget", params: { note_id: n.id } }), "btn-quiet")))))));
    $("panel").replaceChildren(...groups,
      el("p", { class: "dim kp-how" }, "When you mention a promise (\"I told Sam I'd fix his gate by Saturday\"), a decision, an idea or a goal you're setting " +
        "aside, MIA offers to keep it; say \"keep it\" and it's here. A promise with a day is mentioned the day before and on it. " +
        "Ask \"what did I promise?\" any time."));
  }

  MIAShell.start(async () => { paint(await MIA.lifeNotes()); }, { refreshOnChange: true });
})();
