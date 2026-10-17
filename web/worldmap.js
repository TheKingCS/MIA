/*
 * worldmap.js — the World Map with fog of war (claude, 2026-10-17, DEC-0028).
 * Renders MIA.worldmap() (core/world_map.py): the cleared tiles over the
 * fog on a canvas, pins (photos where they were taken, places you reached,
 * "?" for waypoints nobody has reached yet), how much ground that is, and
 * the achievements. "I'm Here" reads the phone's location only when it's
 * pressed and proposes map.checkin. Formatting only.
 */
(function () {
  "use strict";
  const { el, act } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const rgba = (name, a) => "rgba(" + css(name) + "," + a + ")";
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  const PIN = { photo: "📷", checkin: "📍", arrival: "🚩", unknown: "?" };

  // Web Mercator at the page's zoom, in tile units (the same math as core/map_tile_math.py).
  function toTile(lat, lon, z) {
    const n = Math.pow(2, z), r = lat * Math.PI / 180;
    return [(lon + 180) / 360 * n, (1 - Math.asinh(Math.tan(r)) / Math.PI) / 2 * n];
  }

  function hereNow() {
    if (!navigator.geolocation) { MIAShell.say("This device can't share its location."); return; }
    MIAShell.say("Finding where you are…");
    navigator.geolocation.getCurrentPosition(
      (pos) => act({ kind: "map.checkin", params: { lat: pos.coords.latitude, lon: pos.coords.longitude } }),
      () => MIAShell.say("MIA couldn't get your location. Let the app use it, then try again."),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
  }

  function drawMap(canvas) {
    const z = page.zoom;
    const tiles = page.tiles;
    const pins = page.pins.map((p) => Object.assign({}, p, { t: toTile(p.lat, p.lon, z) }));
    const xs = tiles.map((t) => t[0]).concat(pins.map((p) => p.t[0]));
    const ys = tiles.map((t) => t[1]).concat(pins.map((p) => p.t[1]));
    const pad = 2;
    const minX = Math.floor(Math.min(...xs)) - pad, maxX = Math.ceil(Math.max(...xs)) + pad;
    const minY = Math.floor(Math.min(...ys)) - pad, maxY = Math.ceil(Math.max(...ys)) + pad;
    const w = canvas.clientWidth, spanX = maxX - minX, spanY = maxY - minY;
    const scale = Math.min(w / spanX, 520 / spanY);
    const h = Math.max(220, Math.round(spanY * scale));
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr; canvas.height = h * dpr; canvas.style.height = h + "px";
    const g = canvas.getContext("2d");
    g.scale(dpr, dpr);
    const ox = (w - spanX * scale) / 2, oy = (h - spanY * scale) / 2;
    const px = (tx) => ox + (tx - minX) * scale, py = (ty) => oy + (ty - minY) * scale;
    // The fog, with a faint survey grid.
    g.fillStyle = rgba("--rgb-panel-2", 1); g.fillRect(0, 0, w, h);
    g.strokeStyle = rgba("--rgb-line", 0.06); g.lineWidth = 1;
    for (let x = minX; x <= maxX; x++) { g.beginPath(); g.moveTo(px(x), 0); g.lineTo(px(x), h); g.stroke(); }
    for (let y = minY; y <= maxY; y++) { g.beginPath(); g.moveTo(0, py(y)); g.lineTo(w, py(y)); g.stroke(); }
    // Cleared ground: glowing tiles.
    g.shadowColor = rgba("--rgb-accent", 0.6); g.shadowBlur = scale * 0.6;
    g.fillStyle = rgba("--rgb-accent", 0.22);
    tiles.forEach(([x, y]) => g.fillRect(px(x), py(y), scale + 0.5, scale + 0.5));
    g.shadowBlur = 0;
    g.strokeStyle = rgba("--rgb-accent", 0.45);
    const lit = new Set(tiles.map((t) => t.join(",")));
    tiles.forEach(([x, y]) => {  // outline only the edge of the explored land
      [[0, -1, x, y, x + 1, y], [0, 1, x, y + 1, x + 1, y + 1], [-1, 0, x, y, x, y + 1], [1, 0, x + 1, y, x + 1, y + 1]].forEach(([dx, dy, x1, y1, x2, y2]) => {
        if (!lit.has((x + dx) + "," + (y + dy))) { g.beginPath(); g.moveTo(px(x1), py(y1)); g.lineTo(px(x2), py(y2)); g.stroke(); }
      });
    });
    // Pins.
    g.textAlign = "center"; g.textBaseline = "middle";
    const size = Math.max(14, Math.min(22, scale * 0.9));
    pins.forEach((p) => {
      const x = px(p.t[0]), y = py(p.t[1]);
      if (p.kind === "unknown") {
        g.fillStyle = rgba("--rgb-win", 0.18); g.strokeStyle = rgba("--rgb-win", 0.8);
        g.beginPath(); g.arc(x, y, size * 0.55, 0, Math.PI * 2); g.fill(); g.stroke();
        g.fillStyle = rgba("--rgb-win", 1); g.font = "700 " + Math.round(size * 0.7) + "px sans-serif"; g.fillText("?", x, y + 1);
      } else {
        g.font = size + "px sans-serif"; g.fillText(PIN[p.kind] || "•", x, y - size * 0.3);
      }
    });
    return pins;
  }

  function pinList(pins) {
    const photos = pins.filter((p) => p.kind === "photo");
    const places = pins.filter((p) => p.kind === "arrival" || p.kind === "checkin");
    const unknown = pins.filter((p) => p.kind === "unknown");
    return [
      photos.length ? el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, "Photos On The Map")),
        el("div", { class: "media-grid" }, photos.slice(0, 12).map((p) => {
          const img = el("img", { alt: p.label + " (" + p.name + ")", loading: "lazy" });
          MIA.image("/api/expeditions/" + encodeURIComponent(p.expedition_id) + "/media?ref=" + encodeURIComponent(p.ref))
            .then((src) => { if (src) img.src = src; });
          return el("div", { class: "media-tile kind-image" }, img, el("span", { class: "craft-tag" }, p.label));
        }))) : null,
      places.length ? el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, "Places You've Been")),
        el("div", { class: "rows" }, places.slice(0, 20).map((p) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, PIN[p.kind] + " " + p.label), el("div", { class: "row-sub" }, day(p.day))))))) : null,
      unknown.length ? el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, "Still In The Fog")),
        el("p", { class: "dim" }, "Waypoints nobody has reached yet: " + unknown.map((p) => p.label).join(", ") + ".")) : null,
    ].filter(Boolean);
  }

  function draw() {
    const s = page.stats;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.tiles), el("span", { class: "t" }, "Tiles Cleared")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.km2.toLocaleString()), el("span", { class: "t" }, "km² Explored")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, s.regions), el("span", { class: "t" }, "Regions")));
    const here = page.can_check_in ? el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-amber", onclick: hereNow }, "I'm Here"),
      el("a", { class: "btn btn-ghost", href: "places.html" }, "My Places")) : null;
    const parts = [];
    if (!page.tiles.length && !page.pins.length) {
      parts.push(el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, "All Fog So Far"), here),
        el("p", { class: "empty" }, "Finish a trip, tap “arrived” at a waypoint, add a photo taken outdoors, or press I'm Here, and the map starts to clear.")));
    } else {
      const canvas = el("canvas", { class: "world-canvas", role: "img",
        "aria-label": "Map: " + s.tiles + " tiles cleared, " + s.places + " places, " + s.photos + " photos, " + s.to_discover + " still to discover" });
      parts.push(el("section", { class: "glass money-section world-map" }, el("div", { class: "sect" }, el("h2", {}, "Your Map"), here), canvas,
        el("p", { class: "dim world-legend" }, "🚩 reached · 📍 checked in · 📷 photo · ? still in the fog")));
      requestAnimationFrame(() => drawMap(canvas));
    }
    parts.push(el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, "Achievements")),
      el("div", { class: "world-ranks" }, page.ranks.map((r) => el("div", { class: "world-rank" + (r.earned ? " earned" : "") },
        el("span", { class: "world-rank-icon", "aria-hidden": "true" }, r.icon),
        el("div", {}, el("strong", {}, r.name), el("p", { class: "dim" }, r.earned ? r.what : r.what + " · " + r.have + "/" + r.need)))))));
    if (page.discoveries.length) {
      parts.push(el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, "Newest Ground")),
        el("div", { class: "rows" }, page.discoveries.map((d) => el("div", { class: "row money-row" },
          el("div", { class: "row-title" }, day(d.day)), el("span", { class: "chip chip-ok" }, "+" + d.tiles + " tiles"))))));
    }
    $("panel").replaceChildren(...parts, ...pinList(page.pins));
  }

  MIAShell.start(async () => {
    page = await MIA.worldmap();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "The world map isn't set up on this MIA.")); return; }
    draw();
  });
  window.addEventListener("resize", () => { const c = document.querySelector(".world-canvas"); if (c && page) drawMap(c); });
})();
