/*
 * tracks.js — Tracks (claude, 2026-11-09, DEC-0099).
 * Renders MIA.tracks() (core/web_tracks.py): the totals (last 30 days and all time), then each walk, ride or drive
 * newest first with its shape (an SVG path worked out in core from its own points), distance, climb and descent,
 * time taken and moving, and where it started and ended. Add a Track reads a GPX file the person chooses and sends
 * its text as the track.add action; Delete is track.delete (both undoable). Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const SVG = "http://www.w3.org/2000/svg";

  function outline(d, name) {
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 100 100");
    svg.setAttribute("class", "tr-shape");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "The shape of " + name);
    if (d) {
      const path = document.createElementNS(SVG, "path");
      path.setAttribute("d", d);
      svg.append(path);
      const [sx, sy] = d.slice(1).split(" L")[0].split(" ");
      const dot = document.createElementNS(SVG, "circle");
      dot.setAttribute("cx", sx); dot.setAttribute("cy", sy); dot.setAttribute("r", "2.6");
      svg.append(dot);
    }
    return svg;
  }

  const stat = (label, value) => value || value === 0 ? el("div", { class: "tr-stat" }, el("span", { class: "pw-label" }, label), el("b", {}, String(value))) : null;

  function card(t) {
    return el("article", { class: "glass tr-card" },
      outline(t.shape, t.name),
      el("div", { class: "tr-body" },
        el("div", { class: "tr-top" }, el("h2", {}, t.name), el("span", { class: "dim" }, t.date)),
        el("div", { class: "tr-stats" },
          stat("Distance", t.km + " km"),
          t.climb_m ? stat("Up / Down", t.climb_m + " m / " + t.descent_m + " m") : null,
          t.time ? stat("Time", t.time) : null,
          t.moving ? stat("Moving", t.moving) : null),
        t.start ? el("p", { class: "dim tr-grid" }, "From " + t.start + " to " + t.end) : null,
        el("div", { class: "row-buttons" },
          el("button", { type: "button", class: "btn btn-quiet btn-small", "aria-label": "Delete " + t.name,
            onclick: () => MIAShell.act({ kind: "track.delete", params: { track_id: t.id } }) }, "Delete"))));
  }

  function picker() {
    const input = el("input", { type: "file", accept: ".gpx,application/gpx+xml", class: "visually-hidden", "aria-label": "Choose a GPX file",
      onchange: async () => {
        const file = input.files && input.files[0];
        input.value = "";
        if (!file) return;
        if (file.size > 4 * 1024 * 1024) { MIAShell.say("That file is too large for one track."); return; }
        const gpx = await file.text();
        MIAShell.act({ kind: "track.add", params: { gpx, name: "" } });
      } });
    return el("label", { class: "btn btn-primary tr-add" }, "Add a Track", input);
  }

  function paint(d) {
    const t = d.totals || {};
    $("tr-sub").textContent = d.tracks.length
      ? t.count_30 + " in the last 30 days, " + t.km_30 + " km · " + t.count + " in all, " + t.km + " km"
      : "Walks, rides and drives from GPX files.";
    if (!d.available) { $("panel").replaceChildren(el("p", { class: "dim" }, "Tracks aren't on this MIA.")); return; }
    $("panel").replaceChildren(
      el("div", { class: "row-buttons" }, picker()),
      ...(d.tracks.length ? d.tracks.map(card) : [el("p", { class: "empty" },
        "No tracks yet. Export a GPX file from your phone, watch or GPS and add it here: MIA works out the distance, " +
        "the climb and the time, and it stays in your own folder.")]),
      el("p", { class: "dim tr-say" }, "Or ask “how far was my last hike?”"));
  }

  MIAShell.start(async () => paint(await MIA.tracks()), { refreshOnChange: true });
})();
