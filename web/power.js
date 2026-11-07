/*
 * power.js — Power (claude, 2026-11-07, DEC-0125: Power on the phone, as the design canvas draws it).
 * Renders MIA.power() (core/web_power.py): two tabs, Energy Sources (each source with its meters' latest readings,
 * a fill when read in percent, when it was logged, and Log Reading) and Battery (this computer's). Adding, editing
 * and removing a source and logging a reading go through actions (energy_source.add/edit/delete, energy.reading).
 * Formatting only.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);
  const TABS = [["sources", "Energy Sources"], ["battery", "Battery"]];
  let tab = "sources";
  let data = null;

  async function addSource() {
    const v = await MIAShell.form("Add a Source", data.forms.source.fields, {});
    if (v) MIAShell.act({ kind: "energy_source.add", params: v });
  }
  async function editSource(s) {
    const v = await MIAShell.form("Edit " + s.name, data.forms.source.fields, s.values);
    if (v) MIAShell.act({ kind: "energy_source.edit", params: { ...v, source_id: s.id } });
  }
  async function logReading(s) {
    const last = s.meters[0] || {};
    const v = await MIAShell.form("Log a Reading · " + s.name, data.forms.reading, { meter_name: last.meter || "", unit: last.unit || "" });
    if (v) MIAShell.act({ kind: "energy.reading", params: { ...v, source_id: s.id } });
  }

  function meter(m) {
    const value = (Math.round(m.value * 100) / 100) + (m.unit ? (m.unit === "%" ? "%" : " " + m.unit) : "");
    const low = m.percent != null && m.percent <= 25;
    return el("div", { class: "pw-meter" },
      el("div", { class: "pw-row" }, el("span", { class: "pw-name" }, m.meter), el("span", { class: "pw-value" }, value)),
      m.percent != null ? el("div", { class: "meter", role: "meter", "aria-label": m.meter, "aria-valuenow": m.percent, "aria-valuemin": 0, "aria-valuemax": 100 },
        el("div", { class: "meter-fill" + (low ? " low" : ""), style: "width:" + m.percent + "%" })) : null,
      el("span", { class: "pw-when" }, "Logged " + m.when));
  }

  function sources() {
    const cards = data.sources.map((s) => el("section", { class: "glass pw-source", "aria-label": s.name },
      el("div", { class: "pw-row" }, el("h2", { class: "pw-title" }, s.name), el("span", { class: "label" }, s.kind)),
      s.meters.length ? el("div", { class: "pw-meters" }, s.meters.map(meter)) : el("p", { class: "pw-when" }, "No readings yet."),
      el("div", { class: "row-buttons" },
        button("Log Reading", () => logReading(s)),
        button("Edit", () => editSource(s)),
        button("Remove", () => MIAShell.act({ kind: "energy_source.delete", params: { source_id: s.id } })))));
    return [
      ...(cards.length ? cards : [el("p", { class: "empty" }, "No sources yet. Add your propane tank, solar array or generator.")]),
      el("p", { class: "pw-note" }, "Readings are entered by hand. No sensors are connected yet. Or tell MIA: \"log the propane at 60 percent\"."),
      el("button", { type: "button", class: "btn btn-big btn-ghost pw-add", onclick: addSource }, "Add a Source"),
    ];
  }

  function battery() {
    const b = data.battery;
    if (!b.present) return [el("section", { class: "glass pw-source" }, el("p", {}, "MIA's computer has no battery: it runs on the wall."))];
    const left = b.plugged_in ? "Plugged in" : (b.minutes_left ? "About " + b.minutes_left + " min left" : "On battery");
    return [el("section", { class: "glass pw-source", "aria-label": "Battery" },
      el("div", { class: "pw-row" }, el("h2", { class: "pw-title" }, "This computer"), el("span", { class: "pw-value" }, b.percent + "%")),
      el("div", { class: "meter", role: "meter", "aria-label": "Battery", "aria-valuenow": b.percent, "aria-valuemin": 0, "aria-valuemax": 100 },
        el("div", { class: "meter-fill" + (b.percent <= 20 && !b.plugged_in ? " low" : ""), style: "width:" + b.percent + "%" })),
      el("span", { class: "pw-when" }, left))];
  }

  function paint() {
    if (!data.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Power isn't available on this MIA.")); return; }
    $("power-sub").textContent = "Battery · Energy Sources";
    $("tabs").replaceChildren(...TABS.map(([id, label]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; paint(); } }, label)));
    $("panel").replaceChildren(...(tab === "battery" ? battery() : sources()));
  }

  MIAShell.start(async () => { data = await MIA.power(); paint(); }, { refreshOnChange: true });
})();
