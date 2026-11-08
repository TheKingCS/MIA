/*
 * navigation.js — Navigation (claude, 2026-11-06).
 * Renders MIA.navigation(start, end) (core/navigation_web.py): the waypoints
 * with their grid references, the distance and bearing between two on a
 * compass (the design canvas, DEC-0113), and the sun and moon at the first. Read only; a waypoint is added by voice ("add a
 * waypoint called Spring at 18S UJ 23478 06483"). Formatting only; the look
 * is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let start = "", end = "";

  // The design canvas (DEC-0113): a compass with its needle on the bearing between two waypoints (the first two
  // until you pick), the distance; the waypoints with their grid; sunrise and sunset, and the moon.
  function compass(route) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 200 200"); svg.setAttribute("class", "nv-compass"); svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", route ? "Compass pointing " + Math.round(route.bearing) + " degrees, " + route.toward : "Compass");
    svg.innerHTML = '<circle cx="100" cy="100" r="92" class="ring"/><path class="ticks" d="M100 8v12M192 100h-12M100 192v-12M8 100h12"/>'
      + '<g class="dirs"><text x="100" y="38">N</text><text x="168" y="104">E</text><text x="100" y="172">S</text><text x="32" y="104">W</text></g>'
      + (route ? '<g transform="rotate(' + route.bearing + ' 100 100)"><path class="needle" d="M100 30 L110 100 L100 92 L90 100Z"/>'
        + '<path class="tail" d="M100 170 L110 100 L100 108 L90 100Z"/></g>' : "");
    return svg;
  }
  async function draw() {
    let data = await MIA.navigation(start, end);
    const pts = data.waypoints;
    if (pts.length >= 2 && (!start || !end)) {  // the first two, until you pick
      start = start || pts[0].id; end = end || pts[1].id;
      data = await MIA.navigation(start, end);
    }
    $("nav-sub").textContent = pts.length ? pts.length + (pts.length === 1 ? " waypoint" : " waypoints") : "No waypoints yet.";
    const route = data.route, sky = data.sky;
    const sel = (value, onchange) => el("select", { "aria-label": "Waypoint", onchange: (e) => onchange(e.target.value) },
      pts.map((w) => el("option", { value: w.id, selected: w.id === value ? "" : null }, w.name)));
    $("panel").replaceChildren(...[
      pts.length >= 2 ? el("section", { class: "glass nv-bearing", "aria-label": "Bearing" },
        compass(route),
        route ? el("div", { class: "nv-read" }, el("span", {}, String(Math.round(route.bearing)).padStart(3, "0") + "° " + route.toward),
          el("span", {}, route.miles + " mi"), el("span", { class: "dim" }, route.km + " km")) : null,
        el("div", { class: "nv-pick" }, "From", sel(start, (v) => { start = v; draw(); }), "to", sel(end, (v) => { end = v; draw(); }))) : null,
      el("section", { class: "glass nv-list", "aria-labelledby": "nv-wps" },
        el("h2", { id: "nv-wps", class: "nv-label" }, "Waypoints"),
        ...pts.map((w) => el("div", { class: "nv-wp" },
          el("div", {}, el("div", {}, w.name + (w.category ? " · " + w.category : "")), el("div", { class: "nv-grid" }, w.grid || (w.lat + ", " + w.lon))),
          el("div", { class: "row-buttons" },
            el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: async () => {
              const v = data.forms && await MIAShell.form("Change " + w.name, data.forms.waypoint.fields, w.values);
              if (v) MIAShell.act({ kind: "waypoint.edit", params: Object.assign({ waypoint_id: w.id }, v) });
            } }, "Edit"),
            el("button", { type: "button", class: "btn btn-ghost btn-small",
              onclick: () => MIAShell.act({ kind: "waypoint.delete", params: { waypoint_id: w.id } }) }, "Take Out")))),
        el("p", { class: "dim nv-hint" }, pts.length ? "Add one by voice: \"add a waypoint called Spring at …\", or tap the map in Maps."
          : "Tap the map (Maps) to add one, or tell MIA: \"add a waypoint called Spring at 18S UJ 23478 06483\".")),
      sky ? el("div", { class: "nv-sky" },
        el("div", { class: "glass nv-tile" }, el("span", { class: "nv-label" }, "Sunrise / Set"),
          el("strong", {}, sky.sunrise ? sky.sunrise + " · " + sky.sunset : "None today"), el("span", { class: "dim" }, sky.name)),
        el("div", { class: "glass nv-tile" }, el("span", { class: "nv-label" }, "Moon"), el("strong", {}, sky.moon || "—"),
          el("span", { class: "dim" }, data.day))) : null,
    ].filter(Boolean));
  }

  MIAShell.start(draw, { refreshOnChange: true });
})();
