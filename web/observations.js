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

  // The design canvas's card (DEC-0113): its kind (Needs You amber, Noticed or Pattern calm) and the apps it drew
  // on, what was noticed, why, and a link to settle it where it lives. All from the engine (observations_web.card).
  function obsCard(o, what, why, next) {
    return el("article", { class: "glass obs-card tone-" + (o.kind === "Needs You" ? "attention" : "calm") },
      el("div", { class: "obs-top" }, el("span", { class: "obs-kind" }, o.kind), o.used ? el("span", { class: "obs-used" }, "· " + o.used) : null),
      el("p", { class: "obs-what" }, what),
      why ? el("p", { class: "obs-why" }, "Why: " + why) : null,
      next ? el("p", { class: "obs-next" }, next) : null,
      o.open ? el("a", { class: "obs-open", href: o.open.href }, o.open.label + " →") : null);
  }

  function paint(data) {
    const insights = data.insights.flatMap((g) => g.items);
    const count = data.findings.length + insights.length;
    $("obs-sub").textContent = count ? count + " to look at." : "Nothing stands out.";
    const cards = [
      ...data.findings.filter((f) => f.kind === "Needs You").map((f) => obsCard(f, f.claim, f.why, f.next)),
      ...data.findings.filter((f) => f.kind !== "Needs You").map((f) => obsCard(f, f.claim, f.why, f.next)),
      ...insights.map((i) => obsCard(i, i.title + ": " + i.message, "", i.next))];
    $("panel").replaceChildren(
      count ? el("div", { class: "obs-list" }, cards)
        : el("p", { class: "empty" }, "Nothing stands out right now: no bill before payday, no upkeep before a trip, no stalled mission."),
      el("p", { class: "dim obs-note" }, "Read only. Each one is settled in the app it came from. Ask MIA \"what have you noticed?\" any time."));
  }

  MIAShell.start(async () => { paint(await MIA.observations()); }, { refreshOnChange: true });
})();
