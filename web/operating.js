/*
 * operating.js — the Operating Journal (claude, 2026-11-07, DEC-0097).
 * Renders MIA.operatingJournal() (core/operating_journal.py): each line, how it's
 * checked, and its meter with how it's going, in plain numbers (DEC-0113). Adding, rating and taking
 * a line out go through actions (operating.add / .rate / .remove). Then How Your Good Runs Go (Natural Momentum,
 * DEC-0148, core/momentum.picture): what your runs of getting things done have in common, as counts; while you're on
 * one, only that you are.
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

  // The design canvas (DEC-0113): each line as a card (what you wrote, what checks it, its meter and the numbers),
  // grouped as you sorted them, then Add a Line. The numbers come from the engine (core/operating_journal.line_score).
  function lineCard(l) {
    const sc = l.score;
    return el("article", { class: "glass op-line" },
      el("p", { class: "op-text" }, l.text),
      el("p", { class: "op-how" }, l.how.charAt(0).toUpperCase() + l.how.slice(1)),
      el("div", { class: "op-meter" },
        el("div", { class: "meter" }, el("div", { class: "meter-fill", style: "width:" + (sc ? sc.pct : 0) + "%" })),
        el("span", { class: "op-score" }, sc ? sc.text : "Nothing yet")),
      el("div", { class: "row-buttons" },
        l.self_rated ? button("Rate This Week", () => rate(l)) : null,
        button("Take Out", () => MIAShell.act({ kind: "operating.remove", params: { line_id: l.id } }))));
  }
  // How your good runs go (DEC-0148): counts once she's seen a few, never a score; on a run now, nothing but that.
  function runsCard(m) {
    if (!m || (!m.findings && !m.words)) return null;
    return el("section", { class: "glass op-runs", "aria-label": "How your good runs go" },
      el("h2", { class: "op-label" }, "How Your Good Runs Go"),
      m.in_flow ? el("p", { class: "op-flow" }, "You're on a run right now. MIA's holding anything that can wait.") : null,
      (m.findings || []).length ? el("ul", { class: "op-findings" }, ...m.findings.map((f) => el("li", {}, f)))
        : el("p", { class: "dim" }, m.words),
      el("p", { class: "dim op-runs-note" }, m.standard || ""));
  }
  function paint(data) {
    $("operating-sub").textContent = data.lines.length ? "How you mean to live, and how you do." : "Nothing written yet.";
    const groups = Object.entries(data.sections || {}).map(([key, title]) => {
      const mine = data.lines.filter((l) => l.section === key);
      return mine.length ? el("section", { class: "op-group", "aria-label": title }, el("h2", { class: "op-label" }, title),
        ...mine.map(lineCard)) : null;
    });
    $("panel").replaceChildren(...[
      data.lines.length ? null : el("p", { class: "empty" }, "Write how you mean to operate, in your own words. MIA checks what she can against " +
        "your records (workouts, meals, people, tasks, spending); the rest you rate each week. Never a judgment: just the numbers."),
      ...groups,
      runsCard(data.momentum),
      el("div", { class: "row-buttons" }, button("Add a Line", () => add(data.sections || {})))].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.operatingJournal()); }, { refreshOnChange: true });
})();
