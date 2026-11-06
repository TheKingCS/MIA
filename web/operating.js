/*
 * operating.js — the Operating Journal (claude, 2026-11-07, DEC-0097).
 * Renders MIA.operatingJournal() (core/operating_journal.py): each line, how it's
 * checked, and how it's going, in plain numbers. Adding, rating and taking
 * a line out go through actions (operating.add / .rate / .remove).
 * Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);

  async function add(sections) {
    const values = await MIAShell.form("Add a line", [
      { name: "text", label: "How you mean to operate", type: "text", required: true },
      { name: "section", label: "Where it goes", type: "choice", options: Object.keys(sections), default: "rules" }]);
    if (values) MIAShell.act({ kind: "operating.add", params: values });
  }

  async function rate(line) {
    const values = await MIAShell.form("This week: " + line.text, [
      { name: "score", label: "1 to 5", type: "choice", options: ["1", "2", "3", "4", "5"], default: "4" }]);
    if (values) MIAShell.act({ kind: "operating.rate", params: { line_id: line.id, score: Number(values.score) } }, { quick: true });
  }

  function paint(data) {
    $("operating-sub").textContent = data.lines.length ? "How you mean to live, and how you do." : "Nothing written yet.";
    const groups = Object.entries(data.sections || {}).map(([key, title]) => {
      const mine = data.lines.filter((l) => l.section === key);
      return mine.length ? el("section", { class: "glass money-section" }, el("h2", {}, title),
        el("div", { class: "sync-rows" }, mine.map((l) => el("div", { class: "sync-row council-msg" },
          el("div", {}, el("p", { class: "council-text" }, l.text), el("p", { class: "dim" }, l.how), l.now ? el("p", { class: "dim" }, l.now) : null),
          el("div", { class: "row-buttons" },
            l.self_rated ? button("Rate", () => rate(l), "btn-amber") : null,
            button("Take out", () => MIAShell.act({ kind: "operating.remove", params: { line_id: l.id } }))))))) : null;
    });
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, "Write how you mean to operate, in your own words. MIA checks what she can against your records (workouts, meals, people, " +
          "tasks, spending); the rest you rate each week. Never a judgment: just the numbers."),
        el("div", { class: "row-buttons" }, button("Add a line", () => add(data.sections || {}), "btn-amber"))),
      ...groups);
  }

  MIAShell.start(async () => { paint(await MIA.operatingJournal()); }, { refreshOnChange: true });
})();
