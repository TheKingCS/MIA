/*
 * memories.js — Memories (claude, 2026-11-06).
 * Renders MIA.memories() (core/memories_web.py): "On this day", then a recap
 * per expedition, newest first: how long, distance and pace by activity, the
 * places visited, the journal's highlights, the photo count (the photos are on
 * the Expeditions page). Read only. Formatting only; laid out as the design
 * canvas's Memories (DEC-0113).
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const stat = (label, value) => el("div", {}, el("div", { class: "pw-label" }, label), el("div", { class: "mm-v" }, value || "—"));

  // The design canvas (DEC-0113): a card per trip, its name and date, three figures, a line from the journal, and
  // the places and photos.
  function recap(r) {
    const a = r.activities[0];
    return el("article", { class: "glass mm-card" },
      el("div", { class: "mm-top" }, el("span", { class: "mm-name" }, r.name), el("span", { class: "pw-label" }, day(r.start))),
      el("div", { class: "mm-stats" }, stat("Time", r.days ? r.days + (r.days === 1 ? " day" : " days") : ""),
        stat("Distance", r.km ? r.km + " km" : ""), stat("Pace", a && a.kmh ? a.kmh + " km/h" : "")),
      r.highlights.length ? el("p", { class: "mm-quote" }, "\u201c" + r.highlights[0] + "\u201d") : null,
      el("p", { class: "dim mm-foot" }, [r.where, r.places.map((p) => p.count + " " + p.kind.toLowerCase()).join(", "),
        r.photos ? el("a", { href: "expeditions.html" }, r.photos + (r.photos === 1 ? " photo" : " photos")) : null].filter(Boolean)
        .flatMap((x, i) => i ? [" · ", x] : [x])));
  }

  function paint(data) {
    $("mem-sub").textContent = data.recaps.length ? data.recaps.length + (data.recaps.length === 1 ? " trip remembered" : " trips remembered")
      : "No trips yet.";
    $("panel").replaceChildren(
      ...data.on_this_day.map((r) => el("section", { class: "glass mm-today", "aria-label": "On this day" },
        el("span", { class: "pw-label" }, "On This Day · " + r.start.slice(0, 4)),
        el("span", { class: "mm-name" }, r.highlights[0] || r.name + " began"),
        el("span", { class: "dim" }, [r.name, r.km ? r.km + " km" : "", r.photos ? r.photos + " photos" : ""].filter(Boolean).join(" · ")))),
      ...(data.recaps.length ? data.recaps.map(recap) : [el("p", { class: "empty" },
        "Each expedition gets a recap here once it has trips. Start one on the Expeditions page.")]));
  }

  MIAShell.start(async () => { paint(await MIA.memories()); });
})();
