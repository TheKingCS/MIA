/*
 * diagnostics.js — the PC's check-ups (claude, 2026-11-06, T-0040).
 * Renders MIA.diagnostics() (core/diagnostics.py): each built-in check-up over
 * one passive inspection (nothing is probed or changed), what passed, what to
 * look at, and what couldn't be read (never counted as a pass). The PC's
 * owner's page. Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function paint(data) {
    const bad = data.checks.filter((c) => !c.ok).length;
    $("diag-sub").textContent = data.error ? "Couldn't look." : bad ? bad + " to look at." : "All good.";
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, data.error || "MIA reads what Windows already reports (drives, memory, the network, the firewall, the AI model) " +
          "and checks it. Nothing is probed or changed. You can also ask her: \"check my PC\", \"check the network\".")),
      ...data.checks.map((c) => el("section", { class: "glass money-section" },
        el("h2", {}, (c.ok ? "✓ " : "! ") + c.title),
        el("p", { class: "dim" }, c.passed + (c.passed === 1 ? " check passed" : " checks passed")),
        c.failed.length ? el("ul", {}, c.failed.map((f) => el("li", {}, f))) : null,
        c.unknown.length ? el("p", { class: "dim" }, "Couldn't read: " + c.unknown.join(", ") + " (not a pass, not a failure).") : null)));
  }

  MIAShell.start(async () => { paint(await MIA.diagnostics()); });
})();
