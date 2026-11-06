/*
 * play.js — games and sports (claude, 2026-11-07, DEC-0098).
 * Renders MIA.play() (core/recreation.py): the latest games and the training
 * load by week. Logging and taking one out go through actions (play.log,
 * play.delete). Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);

  async function log(efforts) {
    const values = await MIAShell.form("Log a game", [
      { name: "what", label: "What you played", type: "text", required: true },
      { name: "minutes", label: "How long (minutes)", type: "number" },
      { name: "effort", label: "How hard", type: "choice", options: Object.keys(efforts), default: "moderate" },
      { name: "with", label: "Who with (commas between)", type: "text" },
      { name: "date", label: "When", type: "date" }]);
    if (!values) return;
    const people = String(values.with || "").split(",").map((p) => p.trim()).filter(Boolean);
    MIAShell.act({ kind: "play.log", params: { ...values, with: people } });
  }

  function paint(data) {
    $("play-sub").textContent = data.played.length ? data.played.length + " games logged lately." : "Nothing logged yet.";
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, "Or just tell MIA: \"played pickleball for an hour with Sam, it was hard\"."),
        el("div", { class: "row-buttons" }, button("Log a game", () => log(data.efforts || {}), "btn-amber")),
        ...data.lines.map((line) => el("p", { class: "dim" }, line))),
      el("section", { class: "glass money-section" }, el("h2", {}, "Lately"),
        data.played.length ? el("div", { class: "sync-rows" }, data.played.map((g) => el("div", { class: "sync-row" },
          el("span", {}, g.what + (g.minutes ? ", " + g.minutes + " min" : "") + (g.with.length ? " with " + g.with.join(", ") : "")),
          el("span", { class: "dim" }, g.date + " · effort " + g.effort + " · load " + g.load),
          button("Take out", () => MIAShell.act({ kind: "play.delete", params: { entry_id: g.id } })))))
          : el("p", { class: "empty" }, "Nothing yet.")));
  }

  MIAShell.start(async () => { paint(await MIA.play()); }, { refreshOnChange: true });
})();
