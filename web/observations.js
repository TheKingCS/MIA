/*
 * observations.js — what MIA noticed (claude, 2026-11-06).
 * Renders MIA.observations() (core/observations_web.py): findings across apps
 * (each with why and one next step) and the open insights by where they came
 * from. Read only: each is resolved where it lives. Formatting only; the look
 * is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  const item = (title, lines) => el("div", { class: "sync-row council-msg" },
    el("div", {}, el("p", { class: "council-text" }, title), ...lines.filter(Boolean).map((l) => el("p", { class: "dim" }, l))));

  function paint(data) {
    const count = data.findings.length + data.insights.reduce((n, g) => n + g.items.length, 0);
    $("obs-sub").textContent = count ? count + " to look at." : "Nothing stands out.";
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, count ? "What MIA noticed by putting your apps together, and in each one. Ask her \"what have you noticed?\" any time."
          : "Nothing stands out right now: no bill before payday, no upkeep before a trip, no stalled mission.")),
      data.findings.length ? el("section", { class: "glass money-section" }, el("h2", {}, "Across your apps"),
        el("div", { class: "sync-rows" }, data.findings.map((f) => item(f.title, [f.claim, f.why, f.next ? "→ " + f.next : ""])))) : null,
      ...data.insights.map((g) => el("section", { class: "glass money-section" }, el("h2", {}, g.source),
        el("div", { class: "sync-rows" }, g.items.map((i) => item(i.title, [i.message, i.next ? "→ " + i.next : "",
          i.since ? "since " + i.since : ""]))))));
  }

  MIAShell.start(async () => { paint(await MIA.observations()); }, { refreshOnChange: true });
})();
