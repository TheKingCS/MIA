/*
 * navigation.js — Navigation (claude, 2026-11-06).
 * Renders MIA.navigation(start, end) (core/navigation_web.py): the waypoints
 * with their grid references, the distance and bearing between two, and the
 * sun and moon at the first. Read only; a waypoint is added by voice ("add a
 * waypoint called Spring at 18S UJ 23478 06483"). Formatting only; the look
 * is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let start = "", end = "";

  function pick(label, value, points, onchange) {
    return el("label", { class: "form-row" }, label,
      el("select", { onchange: (e) => onchange(e.target.value) },
        el("option", { value: "" }, "—"),
        ...points.map((w) => el("option", { value: w.id, selected: w.id === value ? "" : null }, w.name))));
  }

  async function draw() {
    const data = await MIA.navigation(start, end);
    const pts = data.waypoints;
    $("nav-sub").textContent = pts.length ? pts.length + (pts.length === 1 ? " waypoint" : " waypoints") : "No waypoints yet.";
    const route = data.route;
    $("panel").replaceChildren(
      pts.length ? el("section", { class: "glass money-section" }, el("h2", {}, "Distance and bearing"),
        pick("From", start, pts, (v) => { start = v; draw(); }), pick("To", end, pts, (v) => { end = v; draw(); }),
        route ? el("p", { class: "council-text" }, route.km + " km (" + route.miles + " mi), bearing " + route.bearing + "° " + route.toward)
          : el("p", { class: "dim" }, "Pick two waypoints.")) : null,
      data.sky ? el("section", { class: "glass money-section" }, el("h2", {}, "Sun and moon at " + data.sky.name),
        el("p", {}, data.sky.sunrise ? "Sunrise " + data.sky.sunrise + " · sunset " + data.sky.sunset : "The sun doesn't rise or set there today."),
        el("p", { class: "dim" }, data.sky.moon + " · " + data.day)) : null,
      el("section", { class: "glass money-section" }, el("h2", {}, "Waypoints"),
        pts.length ? el("div", { class: "sync-rows" }, pts.map((w) => el("div", { class: "sync-row council-msg" },
          el("div", {}, el("p", { class: "council-text" }, w.name + (w.category ? " · " + w.category : "")),
            el("p", { class: "dim" }, (w.grid || "") + "  (" + w.lat + ", " + w.lon + ")")))))
          : el("p", { class: "dim" }, "Tell MIA: \"add a waypoint called Spring at 18S UJ 23478 06483\", or mark one on the map.")));
  }

  MIAShell.start(draw, { refreshOnChange: true });
})();
