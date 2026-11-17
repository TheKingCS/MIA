/*
 * specialists.js — Specialists (claude, 2026-11-17; the Specialist Forge's F1, core/specialist_roster.py).
 * Renders MIA.specialistRoster(): each specialist with its standing (added, built but not passing its bench, in
 * progress with what's missing), the model it runs on and its bench, then the planned ones. Read only: the bar is
 * checked in code, never decided here.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TONE = { "added": "ok", "built, not passing": "soon", "in progress": "soon" };

  function row(s) {
    const figures = s.disciplines.length
      ? s.disciplines.join(", ") + " · " + s.calculators + " calculators · " + s.tasks + " bench tasks"
      : "works from its notes";
    return el("li", { class: "glass step-row" }, ...[
      el("div", { class: "step-body" }, ...[
        el("p", { class: "step-text" }, s.name),
        el("p", { class: "dim step-meta" }, figures + (s.model ? " · " + s.model + (s.passed ? " (passed)" : " (not passing)") +
          (s.inspected === "pass" ? " · inspected by Claude" : s.inspected === "hold" ? " · held by Claude" : " · not inspected yet") : "")),
        s.missing.length ? el("p", { class: "dim" }, "Still needs: " + s.missing.join("; ") + ".") : null,
        s.status === "built, not passing" ? el("p", { class: "dim" }, s.why) : null,
      ].filter(Boolean)),
      el("span", { class: "chip " + (TONE[s.status] || "") }, s.status),
    ]);
  }

  function paint(r) {
    const c = r.counts || {};
    $("roster-sub").textContent = (c["added"] || 0) + " added · " + (c["built, not passing"] || 0) + " built, not passing · " +
      (c["in progress"] || 0) + " in progress · " + (c["planned"] || 0) + " planned";
    $("panel").replaceChildren(...[
      el("section", { class: "step-plan" }, el("h2", {}, "The Roster"),
        el("p", { class: "dim" }, "A specialist counts as added only with its charter, limits, starter questions and role, the caveat " +
          "its work needs, and, where its answers rest on figures, calculators and bench tasks with a local model that passed them."),
        el("ol", { class: "step-list" }, ...r.specialists.map(row))),
      r.planned.length ? el("section", { class: "step-plan" }, el("h2", {}, "Planned"),
        el("ul", { class: "step-finished" }, ...r.planned.map((p) => el("li", { class: "dim" }, p.name + " (" + p.department + ")")))) : null,
      el("p", { class: "dim shelf-say" }, "Say \"how are the specialists coming?\" or \"ask the greenhouse specialist ...\" any time."),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.specialistRoster()); }, { refreshOnChange: true });
})();
