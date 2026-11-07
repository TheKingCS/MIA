/*
 * lab.js — The Lab (claude, 2026-11-07, DEC-0125; the design canvas's Lab,
 * DEC-0113). Renders MIA.lab() (core/web_lab.py): the series as chips, the
 * chosen one's chart (points placed by core, 0..1), its plain numbers and
 * readings newest first, and Add a Reading. Other apps' series (Power,
 * Garage) are listed apart, read only, with a link there. Logging and
 * deleting are actions (core/lab_reading_actions.py). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const SVG = "http://www.w3.org/2000/svg";
  let page = null;
  let chosen = decodeURIComponent(location.hash.slice(1));
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);

  async function addReading(series) {
    const c = page.chosen;
    const defaults = series ? { series, unit: c && c.id === series ? c.unit : "" } : {};
    const v = await form("Add a Reading", page.forms.reading.fields, defaults);
    if (v) { chosen = v.series; act({ kind: "lab_reading.add", params: v }); }
  }

  // The chart: one line through core's points, a dot on the newest, the low and high at the side.
  function chartOf(c) {
    if (!c.chart.points.length) return el("p", { class: "dim lab-chart-empty" }, "Two readings make a line.");
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 100 40");
    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("class", "lab-chart-svg");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", c.name + ": " + c.chart.points.map((p) => p.label).join(", "));
    const pts = c.chart.points.map((p) => [p.x * 100, 38 - p.y * 36]);
    [0, 0.5, 1].forEach((g) => {
      const line = document.createElementNS(SVG, "line");
      Object.entries({ x1: 0, x2: 100, y1: 38 - g * 36, y2: 38 - g * 36, class: "lab-grid" }).forEach(([k, v]) => line.setAttribute(k, v));
      svg.append(line);
    });
    const area = document.createElementNS(SVG, "polygon");
    area.setAttribute("points", "0,40 " + pts.map((p) => p.join(",")).join(" ") + " 100,40");
    area.setAttribute("class", "lab-area");
    const line = document.createElementNS(SVG, "polyline");
    line.setAttribute("points", pts.map((p) => p.join(",")).join(" "));
    line.setAttribute("class", "lab-line");
    svg.append(area, line);
    const last = pts[pts.length - 1];
    return el("div", { class: "lab-chart" },
      el("div", { class: "lab-axis" }, el("span", {}, c.chart.high), el("span", {}, c.chart.low)),
      el("div", { class: "lab-plot" }, svg, el("span", { class: "lab-dot", style: "left:" + last[0] + "%;top:" + (last[1] / 40 * 100) + "%" })));
  }

  function statsOf(s) {
    const cells = [["Latest", s.latest], ["Low", s.low], ["High", s.high], ["Average", s.average]].concat(s.change ? [["Change", s.change]] : []);
    return el("dl", { class: "lab-stats" }, ...cells.map(([k, v]) => el("div", {}, el("dt", {}, k), el("dd", {}, v))));
  }

  function readingRow(c, r) {
    return el("div", { class: "lab-reading" },
      el("span", { class: "lab-reading-value" }, r.text),
      el("span", { class: "lab-reading-what" }, el("span", {}, r.at), r.note ? el("span", { class: "dim" }, r.note) : null),
      c.own ? btn("Delete", "btn-ghost btn-small", () => act({ kind: "lab_reading.delete", params: { reading_id: r.id } })) : null);
  }

  function detail(c) {
    if (!c) return el("section", { class: "glass lab-detail" }, el("p", { class: "empty" },
      "No readings yet. Log anything you measure (soil moisture, a tank's pH, the shop's temperature) and it's charted here."),
      btn("Add a Reading", "btn-primary", () => addReading("")));
    return el("section", { class: "glass lab-detail" },
      el("div", { class: "lab-detail-head" }, el("h2", {}, c.name),
        c.own ? btn("Add a Reading", "btn-primary btn-small", () => addReading(c.id))
          : el("a", { class: "btn btn-ghost btn-small", href: c.page }, "Open " + c.app)),
      chartOf(c), statsOf(c.stats),
      el("p", { class: "pw-label" }, "Readings"),
      el("div", { class: "lab-readings" }, ...c.readings.slice(0, 50).map((r) => readingRow(c, r))),
      c.readings.length > 50 ? el("p", { class: "dim" }, "The newest 50 of " + c.readings.length + ".") : null);
  }

  function chip(s) {
    const on = page.chosen && page.chosen.id === s.id;
    return el("button", { type: "button", class: "lab-chip" + (on ? " on" : ""), "aria-pressed": String(!!on),
      onclick: () => { chosen = s.id; history.replaceState(null, "", "#" + encodeURIComponent(s.id)); load(); } },
      el("span", { class: "lab-chip-name" }, s.name), el("span", { class: "lab-chip-read" }, s.latest),
      el("span", { class: "dim" }, s.when + " · " + s.count));
  }

  function draw() {
    if (window.MIAIcons) MIAIcons.badge($("hero-icon"), "lab");
    const n = page.series.length;
    $("lab-sub").textContent = n ? n + (n === 1 ? " series" : " series") + " logged by hand." : "Experiments, sensors and readings.";
    $("panel").replaceChildren(...[
      el("div", { class: "lab-chips", role: "group", "aria-label": "Series" }, ...page.series.map(chip),
        btn("+ New Series", "btn-ghost btn-small lab-new", () => addReading(""))),
      detail(page.chosen),
      page.other_series.length ? el("section", { class: "glass tb-list" }, el("p", { class: "pw-label" }, "From other apps"),
        ...page.other_series.map((s) => el("button", { type: "button", class: "tb-row", onclick: () => { chosen = s.id; load(); } },
          el("span", { class: "tb-row-name" }, s.name), el("span", { class: "dim" }, s.latest + " · " + s.app)))) : null,
      el("p", { class: "dim pw-hand" }, "Readings are entered by hand. No sensors are connected yet."),
    ].filter(Boolean));
  }

  async function load() {
    page = await MIA.lab(chosen);
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The Lab isn't set up on this MIA.")); return; }
    draw();
  }

  MIAShell.start(load);
})();
