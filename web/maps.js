/*
 * maps.js — Maps (claude, 2026-11-06).
 * Two kinds of map. Vector areas (core/offline_maps.py, cut from OpenStreetMap
 * into data/maps/, anywhere in the world, sharp at every zoom) are drawn by
 * MapLibre from web/vendor/, read in byte ranges with this tab's sign-in; the
 * topo map below needs no library.
 * Renders MIA.maps() (core/maps_web.py) as a tile map with no library: the
 * basemap tiles the PC keeps offline (USGS topo for detail, OpenStreetMap only
 * for the world overview), fetched with this tab's sign-in, and the waypoints
 * as pins. Drag to move, + and − to zoom. Formatting only; the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const SIZE = 256;
  let data = null, zoom = 4, cx = 0, cy = 0;  // the centre, in tile units at this zoom
  let vec = null, protocol = null;  // the vector map now shown, and MapLibre's pmtiles:// reader
  const VENDOR = location.href.replace(/[?#].*$/, "").replace(/[^/]*$/, "") + "vendor/";

  // Web Mercator: degrees to tile units at zoom z, and back.
  const toTile = (lat, lon, z) => {
    const n = 2 ** z, r = lat * Math.PI / 180;
    return [(lon + 180) / 360 * n, (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * n];
  };
  const toDeg = (x, y, z) => {
    const n = 2 ** z, lon = x / n * 360 - 180;
    return [Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) * 180 / Math.PI, lon];
  };
  const source = (z) => (z <= data.osm_max_zoom ? "osm" : "usgs_topo");

  function draw(view) {
    const w = view.clientWidth, h = view.clientHeight, n = 2 ** zoom;
    const kids = [];
    for (let tx = Math.floor(cx - w / 2 / SIZE); tx <= Math.floor(cx + w / 2 / SIZE); tx++) {
      for (let ty = Math.floor(cy - h / 2 / SIZE); ty <= Math.floor(cy + h / 2 / SIZE); ty++) {
        if (ty < 0 || ty >= n) continue;
        const x = ((tx % n) + n) % n;
        const img = el("img", { alt: "", style: `left:${Math.round((tx - cx) * SIZE + w / 2)}px;top:${Math.round((ty - cy) * SIZE + h / 2)}px` });
        MIA.image(`/api/maps/tile/${source(zoom)}/${zoom}/${x}/${ty}`).then((src) => { if (src) img.src = src; });
        kids.push(img);
      }
    }
    for (const p of data.waypoints) {
      const [px, py] = toTile(p.lat, p.lon, zoom);
      kids.push(el("span", { class: "map-pin", style: `left:${Math.round((px - cx) * SIZE + w / 2)}px;top:${Math.round((py - cy) * SIZE + h / 2)}px` }, p.name));
    }
    kids.push(el("span", { class: "map-attrib" }, zoom <= data.osm_max_zoom ? "© OpenStreetMap contributors" : "USGS The National Map"));
    view.replaceChildren(...kids);
    const sub = document.querySelector(".mp-head .mp-label");
    if (sub) sub.textContent = (zoom <= data.osm_max_zoom ? "Offline · OpenStreetMap" : "Offline · USGS Topo") + " · Zoom " + zoom;
    $("maps-sub").textContent = "Zoom " + zoom + " · " + data.waypoints.length + (data.waypoints.length === 1 ? " waypoint" : " waypoints");
  }

  function setZoom(view, z) {
    z = Math.max(0, Math.min(data.max_zoom, z));
    const [lat, lon] = toDeg(cx, cy, zoom);
    zoom = z;
    [cx, cy] = toTile(lat, lon, zoom);
    draw(view);
  }

  function paint() {
    const view = el("div", { class: "map-view", role: "img", "aria-label": "Map" });
    let drag = null;
    view.addEventListener("pointerdown", (e) => { drag = [e.clientX, e.clientY, cx, cy, false]; view.setPointerCapture(e.pointerId); });
    view.addEventListener("pointermove", (e) => {
      if (!drag) return;
      if (Math.abs(e.clientX - drag[0]) + Math.abs(e.clientY - drag[1]) > 6) drag[4] = true;  // moved: a drag, not a tap
      cx = drag[2] - (e.clientX - drag[0]) / SIZE;
      cy = drag[3] - (e.clientY - drag[1]) / SIZE;
      for (const child of view.children) {  // move what's there; the tiles are fetched again when the drag ends
        child.style.translate = `${e.clientX - drag[0]}px ${e.clientY - drag[1]}px`;
      }
    });
    view.addEventListener("pointerup", async (e) => {
      if (!drag) return;
      const tapped = !drag[4];
      drag = null;
      draw(view);
      if (!tapped) return;
      const box = view.getBoundingClientRect();  // a tap: a waypoint there, named first
      const [lat, lon] = toDeg(cx + (e.clientX - box.left - box.width / 2) / SIZE, cy + (e.clientY - box.top - box.height / 2) / SIZE, zoom);
      addAt(lat, lon);
    });
    vec = null;
    $("panel").replaceChildren(
      stage(view, "Topo", zoom <= data.osm_max_zoom ? "Offline · OpenStreetMap" : "Offline · USGS Topo", modes("topo"),
        [fab("+", "Zoom in", () => setZoom(view, zoom + 1)), fab("−", "Zoom out", () => setZoom(view, zoom - 1)),
          data.waypoints.length ? fab("⌖", "Show the waypoints", () => { zoom = data.zoom; [cx, cy] = toTile(data.center.lat, data.center.lon, zoom); draw(view); }) : null,
          fab("⤓", "Keep this area offline", () => {  // the box the map shows now, cut as a vector area on the PC
            const half = [view.clientWidth / 2 / SIZE, view.clientHeight / 2 / SIZE];
            const [north, west] = toDeg(cx - half[0], cy - half[1], zoom), [south, east] = toDeg(cx + half[0], cy + half[1], zoom);
            keep({ west, south, east, north });
          }),
          fab("▤", "Trail maps (park PDFs)", () => { location.href = "trails.html"; })]),
      el("p", { class: "dim mp-note" }, "Tiles are kept on the PC once seen, so they work with no signal later. Tap the map to add a waypoint there, "
        + "or tell MIA: \"add a waypoint called Spring at 18S UJ 23478 06483\". ⤓ keeps the area you see as an offline map; ▤ opens your park trail maps."));
    draw(view);
  }

  // The design canvas's route card (DEC-0113): from the first waypoint to the one picked, the distance and bearing
  // (core/navigation_web.py works them out) and the sunset there. No climb: MIA has no elevation for it yet.
  let routeTo = "";
  function routeCard() {
    const box = el("section", { class: "glass mp-route", "aria-label": "Route" });
    if (!data.waypoints || data.waypoints.length < 2) box.classList.add("mp-route-empty");
    const wps = data.waypoints || [];
    if (wps.length < 2) {
      box.append(el("p", { class: "dim" }, "Add two waypoints to see the distance and bearing between them."));
      return box;
    }
    const from = wps[0];
    if (!routeTo || !wps.some((w) => w.id === routeTo)) routeTo = wps[1].id;
    const pick = el("select", { "aria-label": "Route to", onchange: (e) => { routeTo = e.target.value; fill(); } },
      wps.slice(1).map((w) => el("option", { value: w.id, selected: w.id === routeTo ? true : null }, w.name)));
    const figs = el("div", { class: "prop-trio" });
    const head = el("div", { class: "mp-route-top" }, el("span", { class: "mp-label" }, "From " + from.name + " to"), pick,
      el("span", { class: "mp-label mp-bearing" }, ""));
    async function fill() {
      try {
        const nav = await MIA.navigation(from.id, routeTo);
        const r = nav.route, sky = nav.sky;
        head.querySelector(".mp-bearing").textContent = r ? "Bearing " + String(Math.round(r.bearing)).padStart(3, "0") + "° " + r.toward : "";
        figs.replaceChildren(
          el("div", { class: "prop-trio-cell" }, el("span", { class: "prop-trio-t" }, "Distance"),
            el("strong", {}, r ? r.miles + " mi" : "—"), r ? el("small", { class: "dim" }, r.km + " km") : null),
          el("div", { class: "prop-trio-cell" }, el("span", { class: "prop-trio-t" }, "Sunrise"), el("strong", {}, sky ? sky.sunrise : "—")),
          el("div", { class: "prop-trio-cell" }, el("span", { class: "prop-trio-t" }, "Sunset"), el("strong", {}, sky ? sky.sunset : "—")));
      } catch (e) { figs.replaceChildren(el("p", { class: "dim" }, e.message)); }
    }
    fill();
    box.append(head, figs, el("a", { class: "obs-open", href: "navigation.html" }, "More in Navigation →"));
    return box;
  }

  // The canvas's full-screen map (DEC-0113): the map fills the page; its name and kind float at the top, the
  // controls on the right, and the route card along the bottom.
  const fab = (label, aria, onclick) => el("button", { type: "button", class: "mp-fab", "aria-label": aria, title: aria, onclick }, label);
  function stage(view, name, sub, modeButtons, fabs) {
    return el("section", { class: "mp-stage" }, view,
      el("header", { class: "glass mp-head" },
        el("div", { class: "mp-head-t" }, el("h1", {}, name), el("span", { class: "mp-label" }, sub)),
        el("div", { class: "row-buttons mp-modes" }, ...modeButtons)),
      el("div", { class: "mp-fabs" }, ...fabs.filter(Boolean)),
      routeCard());
  }

  const button = (label, onclick, on) => el("button", { type: "button", class: "btn " + (on ? "btn-amber" : "btn-ghost") + " btn-small", onclick }, label);

  async function addAt(lat, lon) {  // a tap on either map: a waypoint there, named first
    const values = await MIAShell.form("A waypoint here", [{ name: "name", label: "Name", type: "text", required: true }]);
    if (values) MIAShell.act({ kind: "waypoint.add", params: { name: values.name, lat: lat.toFixed(6), lon: lon.toFixed(6) } });
  }

  async function keep(box) {
    const values = await MIAShell.form("Keep this area offline", [{ name: "name", label: "Call it", type: "text", required: true }]);
    if (values) MIAShell.act({ kind: "map.area_keep", params: { name: values.name, west: box.west.toFixed(5), south: box.south.toFixed(5),
      east: box.east.toFixed(5), north: box.north.toFixed(5) } });
  }

  // The map kinds to switch between: the topo tiles, and each vector area kept on this PC.
  const modes = (current) => [button("Topo", () => paint(), current === "topo"),
    ...data.vector.map((a) => button(a.name, () => paintVector(a), current === a.name))];

  function pins() {
    vec.markers.forEach((m) => m.remove());
    vec.markers = data.waypoints.map((p) => new maplibregl.Marker({ element: el("span", { class: "map-pin" }, p.name), anchor: "bottom" })
      .setLngLat([p.lon, p.lat]).addTo(vec.map));
  }

  function paintVector(area) {
    const view = el("div", { class: "map-view map-vector", role: "img", "aria-label": "Map of " + area.name });
    $("panel").replaceChildren(
      stage(view, area.name, "Offline · " + area.size_mb + " MB · Saved", modes(area.name),
        [fab("+", "Zoom in", () => vec && vec.map.zoomIn()), fab("−", "Zoom out", () => vec && vec.map.zoomOut()),
          fab("✕", "Take this area off the PC", () => MIAShell.act({ kind: "map.area_remove", params: { name: area.name } }))]),
      el("p", { class: "dim mp-note" }, area.name + ": " + area.size_mb + " MB on this PC, from OpenStreetMap, works with no signal. "
        + "Tap the map to add a waypoint there."));
    if (!window.maplibregl || !window.pmtiles || !window.basemaps) { view.textContent = "The map's code didn't load."; return; }
    if (!protocol) {
      protocol = new pmtiles.Protocol();
      maplibregl.addProtocol("pmtiles", protocol.tile);
    }
    const url = location.origin + "/api/maps/vector/" + encodeURIComponent(area.name);
    protocol.add(new pmtiles.PMTiles(new pmtiles.FetchSource(url, new Headers(MIA.authHeaders()))));
    const map = new maplibregl.Map({
      container: view, center: area.center, zoom: Math.max(area.center_zoom, Math.min(13, area.max_zoom)), maxZoom: area.max_zoom + 3,
      attributionControl: { compact: true },
      style: { version: 8, sources: { protomaps: { type: "vector", url: "pmtiles://" + url, attribution: "© OpenStreetMap contributors" } },
        // Place names and icons from web/vendor/ (Noto fonts for Latin script, Protomaps' sprite), so they work offline.
        glyphs: VENDOR + "fonts/{fontstack}/{range}.pbf", sprite: VENDOR + "sprites/dark",
        layers: basemaps.layers("protomaps", basemaps.namedFlavor("dark"), { lang: "en" }) },
    });
    map.on("click", (e) => addAt(e.lngLat.lat, e.lngLat.lng));
    vec = { map, markers: [], name: area.name };
    pins();
  }

  MIAShell.start(async () => {
    const first = data === null;
    data = await MIA.maps();
    if (!first) {  // a change elsewhere: new pins, same view; a kept or removed area: the switch changes
      const shown = vec && data.vector.find((a) => a.name === vec.name);
      if (vec && !shown) { if (data.vector.length) paintVector(data.vector[0]); else paint(); return; }
      if (vec) { pins(); $("panel").querySelector(".mp-modes").replaceChildren(...modes(vec.name)); }
      else paint();
      return;
    }
    zoom = data.zoom;
    [cx, cy] = toTile(data.center.lat, data.center.lon, zoom);
    if (data.vector.length) paintVector(data.vector[0]); else paint();
  }, { refreshOnChange: true });
})();
