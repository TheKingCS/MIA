/*
 * maps.js — Maps (claude, 2026-11-06).
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
      const values = await MIAShell.form("A waypoint here", [{ name: "name", label: "Name", type: "text", required: true }]);
      if (values) MIAShell.act({ kind: "waypoint.add", params: { name: values.name, lat: lat.toFixed(6), lon: lon.toFixed(6) } });
    });
    const button = (label, onclick) => el("button", { type: "button", class: "btn btn-ghost btn-small", onclick }, label);
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("div", { class: "row-buttons" }, button("+", () => setZoom(view, zoom + 1)), button("−", () => setZoom(view, zoom - 1)),
          data.waypoints.length ? button("Waypoints", () => { zoom = data.zoom; [cx, cy] = toTile(data.center.lat, data.center.lon, zoom); draw(view); }) : null),
        view,
        el("p", { class: "dim" }, "Tiles are kept on the PC once seen, so they work with no signal later. Tap the map to add a waypoint there, "
          + "or tell MIA: \"add a waypoint called Spring at 18S UJ 23478 06483\".")));
    draw(view);
  }

  MIAShell.start(async () => {
    const first = data === null;
    data = await MIA.maps();
    if (!first) { draw(document.querySelector(".map-view")); return; }  // a change elsewhere: new pins, same view
    zoom = data.zoom;
    [cx, cy] = toTile(data.center.lat, data.center.lon, zoom);
    paint();
  }, { refreshOnChange: true });
})();
