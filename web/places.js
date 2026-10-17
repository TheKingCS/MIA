/*
 * places.js — My Places (claude, 2026-10-17, DEC-0028 #13). Renders
 * MIA.places() (core/places.py): each place, what arriving there does,
 * Add Place (where you are now, or typed in), Remove, and the switch that
 * lets this device notice when you arrive (Settings → Location quests).
 * Formatting only; the watching is web/places-watch.js.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";

  function here() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) { resolve(null); return; }
      navigator.geolocation.getCurrentPosition((p) => resolve(p.coords), () => resolve(null),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
    });
  }

  async function add(useHere) {
    let where = null;
    if (useHere) {
      MIAShell.say("Finding where you are…");
      where = await here();
      if (!where) { MIAShell.say("MIA couldn't get your location. Let the app use it, or type the place in."); return; }
    }
    const fields = [
      { name: "name", label: "Place (like Gym or Grocery Store)", type: "text", required: true, options: [], default: null },
      { name: "on_arrive", label: "When I get there", type: "choice", required: true, options: page.arrivals, default: page.arrivals[0] },
      { name: "note", label: "A reminder (optional)", type: "text", required: false, options: [], default: null },
      { name: "radius", label: "How close counts as there (meters)", type: "int", required: false, options: [], default: page.default_radius },
    ];
    if (!where) fields.splice(1, 0,
      { name: "lat", label: "Latitude", type: "number", required: true, options: [], default: null },
      { name: "lon", label: "Longitude", type: "number", required: true, options: [], default: null });
    const v = await form(useHere ? "Add Where I Am" : "Add A Place", fields, {});
    if (!v) return;
    act({ kind: "place.add", params: Object.assign(where ? { lat: where.latitude, lon: where.longitude } : {}, v) });
  }

  function draw() {
    const watch = btn(page.watching ? "Turn Off" : "Turn On", page.watching ? "btn-ghost btn-small" : "btn-amber btn-small",
      () => act({ kind: "setting.set", params: { key: "places.watch", value: !page.watching } }));
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.places.length), el("span", { class: "t" }, "Places")),
      el("div", { class: "cell " + (page.watching ? "ok" : "soon") }, el("span", { class: "n" }, page.watching ? "On" : "Off"), el("span", { class: "t" }, "Noticing Arrivals")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, page.places.reduce((n, p) => n + p.arrivals, 0)), el("span", { class: "t" }, "Arrivals")));
    $("panel").replaceChildren(
      section("Noticing When I Arrive", watch,
        el("p", { class: "dim" }, "While MIA is open, this device checks where you are against your places, and asks before doing anything. Where you are never leaves it.")),
      section("My Places", el("div", { class: "row-buttons" }, btn("Add Where I Am", "btn-amber", () => add(true)), btn("Type One In", "btn-ghost", () => add(false))),
        page.places.length ? el("div", { class: "rows" }, page.places.map((p) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, "📍 " + p.name),
            el("div", { class: "row-sub" }, [p.on_arrive, "within " + p.radius + " m", p.note || null,
              p.arrivals ? "been " + p.arrivals + (p.arrivals === 1 ? " time" : " times") + ", last " + day(p.last_arrived) : null].filter(Boolean).join(" · "))),
          btn("Remove", "btn-ghost btn-small", () => act({ kind: "place.delete", params: { place_id: p.id } })))))
          : el("p", { class: "empty" }, "No places yet. Stand at the gym or the store and press Add Where I Am.")));
  }

  MIAShell.start(async () => {
    page = await MIA.places();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Places aren't set up on this MIA.")); return; }
    draw();
  });
})();
