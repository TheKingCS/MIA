/*
 * sensors.js — Sensors (claude, 2026-11-09). Renders MIA.sensors() (core/sensors.py): each sensor that sends its own
 * readings, where they go (the Lab, Power or the Greenhouse), its last reading and when, and Remove (sensor.remove).
 * Add a Sensor asks which app, then its name and target there; MIA.sensorAdd returns the key, shown here once with
 * an example request for the device to send. The key is never an action (actions are logged). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null, fresh = null;  // fresh: the sensor just added, with its key (this view only)

  function when(iso) {
    if (!iso) return "no readings yet";
    const d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  }

  async function add() {
    const which = await form("Add a Sensor", [{ name: "app", label: "Its readings go to", type: "choice", required: true,
      options: page.apps.map((a) => a.name), default: page.apps[0].name }], {});
    if (!which) return;
    const app = page.apps.find((a) => a.name === which.app);
    // A target the engine has a list for (a Power source, a Greenhouse place or measure) is picked from it.
    const PICKED = ["source_id", "place", "measure"];
    const fields = [{ name: "name", label: "Name it (e.g. Tank 1 pH probe)", type: "text", required: true }].concat(app.fields.map((f) =>
      PICKED.includes(f.name) && (page.picks[f.name] || []).length
        ? { name: f.name, label: f.label, type: "pick", required: true, options: [f.name] }
        : { name: f.name, label: f.label.replace(" (optional)", ""), type: "text", required: !/optional/.test(f.label) }));
    const extra = {};
    PICKED.forEach((k) => { extra[k] = (page.picks[k] || []).map((p) => ({ id: p.value, name: p.label })); });
    const v = await form("A Sensor For " + app.name, fields, {}, extra);
    if (!v) return;
    const target = {};
    app.fields.forEach((f) => { target[f.name] = v[f.name] || ""; });
    try {
      fresh = await MIA.sensorAdd({ name: v.name, app: app.id, target });
      MIAShell.refresh();
    } catch (e) { say(e.message); }
  }

  function keyCard(f) {
    const origin = location.origin.replace(/^https?:\/\/(localhost|127\.0\.0\.1)/, "http://<this-computer>");
    const example = "curl -X POST " + origin + f.path + " -H \"" + f.header + ": " + f.key +
      "\" -H \"Content-Type: application/json\" -d '" + JSON.stringify(f.body) + "'";
    const copy = (text) => (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject())
      .then(() => say("Copied."), () => say(text));
    return el("section", { class: "glass sn-key", "aria-live": "polite" },
      el("p", { class: "pw-label" }, f.sensor.name + " · its key"),
      el("p", { class: "sn-warn" }, "This is the only time the key is shown. Put it in the sensor's settings now."),
      el("code", { class: "sn-code" }, f.key),
      el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-primary btn-small", onclick: () => copy(f.key) }, "Copy the Key"),
        el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => copy(example) }, "Copy an Example Request"),
        el("button", { type: "button", class: "btn btn-quiet btn-small", onclick: () => { fresh = null; paint(); } }, "Done")),
      el("p", { class: "dim" }, "The sensor sends one number at a time, at most one every " + page.min_gap + " seconds:"),
      el("code", { class: "sn-code small" }, example));
  }

  function card(s) {
    return el("article", { class: "glass sn-card" },
      el("div", { class: "sn-top" }, el("h2", {}, s.name), el("span", { class: "dim" }, s.goes_to)),
      el("p", { class: "sn-last" }, s.last_value != null ? el("b", {}, String(s.last_value)) : null,
        el("span", { class: "dim" }, (s.last_value != null ? " · " : "") + when(s.last_at) + (s.count ? " · " + s.count + " in all" : ""))),
      el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-quiet btn-small", "aria-label": "Remove " + s.name,
        onclick: () => act({ kind: "sensor.remove", params: { sensor_id: s.id } }) }, "Remove")));
  }

  function paint() {
    if (!page) return;
    $("sn-sub").textContent = page.sensors.length ? page.sensors.length + " sending readings" : "Sensors that send their own readings.";
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "dim" }, "Sensors aren't on this MIA.")); return; }
    $("panel").replaceChildren(...[
      fresh ? keyCard(fresh) : null,
      el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-primary", onclick: add }, "Add a Sensor")),
      ...(page.sensors.length ? page.sensors.map(card) : [el("p", { class: "empty" },
        "No sensors yet. A probe, a smart plug or a Raspberry Pi on your home network can send its readings to the Lab, " +
        "Power or the Greenhouse, logged exactly as if you'd typed them in.")]),
      el("p", { class: "dim sn-standard" }, page.standard),
    ].filter(Boolean));
  }

  MIAShell.start(async () => { page = await MIA.sensors(); paint(); }, { refreshOnChange: true });
})();
