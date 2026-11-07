/*
 * play.js — games and sports (claude, 2026-11-07, DEC-0098).
 * Renders MIA.play() (core/recreation.py): the training load by week as bars and
 * the latest games, as the design canvas has them (DEC-0113). Logging and taking one out go through actions (play.log,
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

  // The design canvas (DEC-0113): six weeks of play minutes as bars (this week lit), the week in a line, the latest
  // games (what, when and how hard in a word, minutes), and one big Log a Game.
  const weekday = (iso) => new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short" });
  function bars(weeks) {
    const most = Math.max(1, ...weeks.map((w) => w.play_minutes));
    return el("div", { class: "pl-bars", role: "img", "aria-label": "Minutes played per week: " + weeks.map((w) => w.play_minutes).join(", ") },
      weeks.map((w, i) => el("div", { class: "pl-bar" + (i === weeks.length - 1 ? " now" : "") },
        el("div", { class: "pl-fill", style: "height:" + Math.round(100 * w.play_minutes / most) + "%" }),
        el("span", { class: "pl-wk" }, new Date(w.week + "T00:00:00").toLocaleDateString(undefined, { month: "numeric", day: "numeric" })))));
  }
  function paint(data) {
    $("play-sub").textContent = data.played.length ? data.played.length + " games logged lately." : "Nothing logged yet.";
    const now = data.weeks.length ? data.weeks[data.weeks.length - 1] : null;
    $("panel").replaceChildren(...[
      data.weeks.length ? el("section", { class: "glass pl-panel", "aria-labelledby": "pl-load" },
        el("h2", { id: "pl-load", class: "pl-label" }, "Training Load · Last " + data.weeks.length + " Weeks"),
        bars(data.weeks),
        now ? el("p", { class: "pl-week" }, now.play_minutes + " min played this week" + (now.workouts ? ", " + now.workouts + " workout" + (now.workouts === 1 ? "" : "s") : "") + ".") : null) : null,
      el("section", { class: "glass pl-panel", "aria-labelledby": "pl-latest" },
        el("h2", { id: "pl-latest", class: "pl-label" }, "Latest"),
        data.played.length ? el("div", { class: "pl-games" }, data.played.slice(0, 8).map((g) => el("div", { class: "pl-game" },
          el("div", {}, el("div", { class: "pl-what" }, g.what + (g.with.length ? " with " + g.with.join(", ") : "")),
            el("div", { class: "pl-when" }, weekday(g.date) + " · " + (g.effort_word || "effort " + g.effort))),
          el("span", { class: "pl-min" }, g.minutes ? g.minutes + " min" : ""),
          button("Take Out", () => MIAShell.act({ kind: "play.delete", params: { entry_id: g.id } })))))
          : el("p", { class: "empty" }, "Nothing yet. Or just tell MIA: \"played pickleball for an hour with Sam, it was hard\".")),
      el("button", { type: "button", class: "btn btn-big btn-green pl-log", onclick: () => log(data.efforts || {}) }, "Log a Game"),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { paint(await MIA.play()); }, { refreshOnChange: true });
})();
