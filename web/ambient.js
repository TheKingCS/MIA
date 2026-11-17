/*
 * ambient.js: the ambient view (claude, 2026-11-17, DEC-0231, Zac's Q-80). Renders MIA.ambient()
 * (core/ambient.py): the clock (this device's own, once a second), the date and weather, what's due now and the next
 * thing, what's playing, the mission in play and what MIA is doing. Re-read on the live signal like every page;
 * no sidebar and no Talk (it's for glancing). Formatting only: what's shown is decided in core.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function tick() {
    const now = new Date();
    $("clock").textContent = now.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  }

  function row(item) {
    return el("div", { class: "amb-row" },
      el("span", { class: "amb-row-title" }, item.title),
      el("span", { class: "amb-row-when" }, [item.when, item.time].filter(Boolean).join(" · ")));
  }

  function block(label, ...kids) {
    return el("div", { class: "amb-block" }, el("h2", { class: "amb-label" }, label), ...kids);
  }

  function paint(v) {
    $("date").textContent = v.date || "";
    $("weather").textContent = v.weather ? v.weather.text + (v.weather.place ? " · " + v.weather.place : "") : "";
    $("due").replaceChildren(block("Due",
      ...(v.due.length ? v.due.map(row) : [el("p", { class: "amb-quiet" }, "Nothing due right now.")]),
      v.next ? el("p", { class: "amb-next" }, "Next: " + v.next.title + (v.next.when ? " · " + v.next.when : "")) : null));
    const side = [];
    if (v.music) side.push(block(v.music.playing ? "Playing" : "Paused",
      el("p", { class: "amb-big" }, v.music.title), el("p", { class: "amb-quiet" }, v.music.artist || "")));
    if (v.mission) side.push(block("Mission",
      el("p", { class: "amb-big" }, v.mission.name),
      el("p", { class: "amb-quiet" }, (v.mission.next ? "Next: " + v.mission.next + " · " : "") + v.mission.done + " of " + v.mission.total)));
    $("side").replaceChildren(...side);
    $("doing").textContent = v.activity.length ? "MIA: " + v.activity.map((a) => a.what).join(" · ") : "MIA is here.";
  }

  tick();
  setInterval(tick, 1000);
  MIAShell.start(async () => { paint(await MIA.ambient()); }, { talk: false });
})();
