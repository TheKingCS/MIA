/*
 * power.js — Power (claude, 2026-11-07, DEC-0125; the design canvas's Power,
 * DEC-0113). Renders MIA.power() (core/web_power.py): Energy Sources (each
 * with its latest reading per meter, a meter for a percent, when it was
 * logged, Log Reading) and Battery (this device's). Adding a source, logging
 * a reading and taking one out are actions (core/power_actions.py). Readings
 * are entered by hand; no sensors yet. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["sources", "Energy Sources"], ["battery", "Battery"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "sources";
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);

  async function addSource() {
    const v = await form("Add a Source", page.forms.energy_source.fields, {});
    if (v) act({ kind: "energy_source.add", params: v });
  }
  async function editSource(s) {
    const v = await form("Change " + s.name, page.forms.energy_source.fields, s.values);
    if (v) act({ kind: "energy_source.edit", params: Object.assign({ source_id: s.id }, v) });
  }
  async function logReading(s) {
    const last = s.meters[0];
    const defaults = last ? { meter: last.name, unit: last.unit } : {};
    const v = await form("Log a Reading: " + s.name, page.forms.reading.fields, defaults);
    if (v) act({ kind: "energy.reading", params: Object.assign({ source_id: s.id }, v) });
  }

  // The canvas's source card: the name and its reading, a meter for a percent (amber when low), when it was
  // logged, and Log Reading.
  function sourceCard(s) {
    const main = s.meters[0];
    return el("article", { class: "glass pw-src" + (s.needs_you ? " low" : "") },
      el("div", { class: "pw-src-top" }, el("span", { class: "pw-src-name" }, s.name),
        el("span", { class: "pw-src-read" + (main && main.meter && main.meter.tone === "attention" ? " low" : "") }, main ? main.text : "No reading yet")),
      main && main.meter ? el("div", { class: "meter" }, el("div", { class: "meter-fill " + main.meter.tone, style: "width:" + main.meter.pct + "%" })) : null,
      ...s.meters.slice(1).map((m) => el("div", { class: "pw-src-more" }, el("span", {}, m.name), el("span", {}, m.text + " · " + m.when))),
      el("div", { class: "pw-src-foot" }, el("span", { class: "dim" }, main ? "Logged " + main.when : s.type),
        el("div", { class: "row-buttons" }, btn("Log Reading", "btn-ghost btn-small", () => logReading(s)),
          btn("Change", "btn-ghost btn-small", () => editSource(s)),
          btn("Remove", "btn-ghost btn-small", () => act({ kind: "energy_source.delete", params: { source_id: s.id } })))));
  }

  function sources() {
    return [
      page.sources.length ? el("div", { class: "pw-srcs" }, page.sources.map(sourceCard))
        : el("p", { class: "empty" }, "Nothing tracked yet. Add your solar, generator, propane or a battery bank, then log a reading now and then."),
      el("p", { class: "dim pw-hand" }, "Readings are entered by hand. No sensors are connected yet."),
      btn("Add a Source", "btn-ghost", addSource),
    ];
  }

  function battery() {
    const b = page.battery;
    if (!b.available) return [el("p", { class: "empty" }, "This device has no battery to read (a desktop on mains power).")];
    return [el("section", { class: "glass pw-src" },
      el("div", { class: "pw-src-top" }, el("span", { class: "pw-src-name" }, "This device"),
        el("span", { class: "pw-src-read" + (b.meter.tone === "attention" ? " low" : "") }, b.percent + "%")),
      el("div", { class: "meter" }, el("div", { class: "meter-fill " + b.meter.tone, style: "width:" + b.meter.pct + "%" })),
      el("p", { class: "dim" }, b.plugged_in ? "Plugged in." : b.minutes_left ? "About " + b.minutes_left + " minutes left." : "On battery."))];
  }

  function draw() {
    if (window.MIAIcons) MIAIcons.badge($("hero-icon"), "power");
    $("power-sub").textContent = page.sources.length ? page.sources.length + (page.sources.length === 1 ? " source" : " sources") + " tracked."
      : "Battery and energy sources.";
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...(tab === "battery" ? battery() : sources()));
  }

  MIAShell.start(async () => {
    page = await MIA.power();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Energy tracking isn't set up on this MIA.")); return; }
    draw();
  });
})();
