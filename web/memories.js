/*
 * memories.js — Memories (claude, 2026-11-06).
 * Renders MIA.memories() (core/memories_web.py): "On this day", then a recap
 * per expedition, newest first: how long, distance and pace by activity, the
 * places visited, the journal's highlights, the photo count (the photos are on
 * the Expeditions page). Read only. Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);

  function recap(r) {
    const when = r.start ? r.start + (r.end && r.end !== r.start ? " – " + r.end : "") : "";
    return el("section", { class: "glass money-section" },
      el("h2", {}, r.name),
      el("p", { class: "dim" }, [when, r.where, r.days ? r.days + (r.days === 1 ? " day" : " days") : "", r.km ? r.km + " km" : ""]
        .filter(Boolean).join(" · ")),
      r.activities.length ? el("ul", {}, r.activities.map((a) => el("li", {},
        a.kind + ": " + a.trips + (a.trips === 1 ? " trip" : " trips") + ", " + a.km + " km" + (a.kmh ? " at " + a.kmh + " km/h" : "")))) : null,
      r.places.length ? el("p", {}, "Places: " + r.places.map((p) => p.kind + " " + p.count).join(", ")) : null,
      r.highlights.length ? el("p", {}, "From the journal: " + r.highlights.join("; ")) : null,
      r.photos ? el("a", { href: "expeditions.html" }, "📷 " + r.photos + (r.photos === 1 ? " photo" : " photos")) : null);
  }

  function paint(data) {
    $("mem-sub").textContent = data.recaps.length ? data.recaps.length + (data.recaps.length === 1 ? " trip remembered" : " trips remembered")
      : "No trips yet.";
    $("panel").replaceChildren(
      ...(data.on_this_day.length ? [el("section", { class: "glass money-section" }, el("h2", {}, "On this day"),
        el("ul", {}, data.on_this_day.map((r) => el("li", {}, r.name + " began on this day, " + r.start.slice(0, 4) + "."))))] : []),
      ...(data.recaps.length ? data.recaps.map(recap) : [el("section", { class: "glass money-section" },
        el("p", {}, "Each expedition gets a recap here once it has trips. Start one on the Expeditions page."))]));
  }

  MIAShell.start(async () => { paint(await MIA.memories()); });
})();
