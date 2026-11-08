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

  // The design canvas (DEC-0113): Passed / Look At / Unread as tiles, then one row per check-up with its dot (green
  // all passed, amber something to look at, grey something it couldn't read) and the line that matters, then Run Again.
  function row(c) {
    const state = c.failed.length ? "look" : c.unknown.length ? "unread" : "ok";
    const note = c.failed.length ? c.failed.join(" ") : c.unknown.length ? "Couldn't read: " + c.unknown.join(", ")
      : c.passed + (c.passed === 1 ? " check passed" : " checks passed");
    return el("div", { class: "dx-row" }, el("span", { class: "dx-dot " + state, "aria-hidden": "true" }),
      el("div", { class: "dx-text" }, el("span", {}, c.title), el("span", { class: "dx-note" }, note),
        c.failed.length && c.unknown.length ? el("span", { class: "dx-note" }, "Couldn't read: " + c.unknown.join(", ")) : null),
      el("span", { class: "sr-only" }, state === "ok" ? "passed" : state === "look" ? "to look at" : "couldn't read all of it"));
  }
  function paint(data) {
    const sum = (f) => data.checks.reduce((n, c) => n + f(c), 0);
    const passed = sum((c) => c.passed), look = sum((c) => c.failed.length), unread = sum((c) => c.unknown.length);
    $("diag-sub").textContent = data.error ? "Couldn't look." : look ? look + " to look at." : "All good.";
    const tile = (cls, label, n) => el("div", { class: "glass dx-tile " + cls }, el("span", { class: "dx-dot " + cls, "aria-hidden": "true" }),
      el("div", {}, el("div", { class: "dx-label" }, label), el("div", { class: "dx-n" }, String(n))));
    $("panel").replaceChildren(...[
      data.error ? el("p", { class: "empty" }, data.error) : null,
      el("div", { class: "dx-tiles" }, tile("ok", "Passed", passed), tile("look", "Look At", look), tile("unread", "Unread", unread)),
      el("section", { class: "glass dx-list", "aria-labelledby": "dx-checks" }, el("h2", { id: "dx-checks", class: "dx-label" }, "Check-Ups"),
        ...data.checks.map(row)),
      (data.hardware || []).length ? el("section", { class: "glass dx-list dx-hw", "aria-labelledby": "dx-hw" },
        el("h2", { id: "dx-hw", class: "dx-label" }, "This PC"),
        ...data.hardware.map((h) => el("div", { class: "dx-hw-row" }, el("span", { class: "dx-hw-name" }, h.name),
          el("span", { class: "dx-hw-value" }, h.value), el("span", { class: "dim" }, h.note)))) : null,
      el("details", { class: "glass dx-list dx-log" }, el("summary", { class: "dx-label" }, "Recent Problems In MIA's Log · " + (data.problems || []).length),
        ...((data.problems || []).length ? data.problems.map((p) => el("div", { class: "dx-log-row " + p.level },
          el("span", { class: "dx-dot " + (p.level === "error" ? "bad" : "look"), "aria-hidden": "true" }),
          el("div", {}, el("div", { class: "dx-log-text" }, p.text), el("div", { class: "dim" }, p.when + " · " + p.where))))
          : [el("p", { class: "dim" }, "No warnings or errors lately.")])),
      el("p", { class: "dim dx-foot" }, "Looks only. Nothing is probed or changed. Anything it couldn't read is never counted as a pass. "
        + "You can also ask her: \"check my PC\", \"check the network\"."),
      el("button", { type: "button", class: "btn btn-ghost", onclick: async () => paint(await MIA.diagnostics()) }, "Run Again"),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.diagnostics()); });
})();
