/*
 * toolbox.js — the Toolbox (claude, 2026-11-07, DEC-0125; the design
 * canvas's Toolbox, DEC-0113). Renders MIA.toolbox() (core/web_toolbox.py):
 * the open calculator (its boxes, and the answer core works out as you type,
 * MIA.toolboxCalc), the list of calculators, alarms (set, on/off, delete:
 * core/toolbox_actions.py) and the other tools. The stopwatch only counts on
 * the page. Formatting only: every number shown comes from core.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  let open = "ohms_law";
  let values = {};
  let timer = 0;
  let asked = 0;
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);

  function calcOf(id) { return page.calculators.find((c) => c.id === id) || page.calculators[0]; }

  // Ask core for the answer a moment after the last keystroke; only the newest answer is drawn.
  function work() {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const mine = ++asked;
      let r;
      try { r = await MIA.toolboxCalc(open, values); } catch (e) { r = { error: e.message }; }
      if (mine === asked) drawAnswer(r);
    }, 250);
  }

  function drawAnswer(r) {
    const box = $("tb-answer");
    if (!box) return;
    if (r.error) { box.replaceChildren(el("p", { class: "dim" }, r.error)); return; }
    box.replaceChildren(...[
      el("div", { class: "tb-answer-main" }, r.answer),
      r.lines && r.lines.length ? el("dl", { class: "tb-lines" }, ...r.lines.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)])) : null,
      r.note ? el("p", { class: "dim" }, r.note) : null,
      r.demo ? el("p", { class: "dim" }, "The demo shows the example's answer.") : null].filter(Boolean));
  }

  function input(c, f) {
    const id = "tb-" + f.name;
    let box;
    if (f.type === "choice") {
      const opts = c.id === "unit_converter" && f.name !== "category" ? c.units[values.category] || [] : f.options;
      box = el("select", { id, class: "tb-input" }, ...opts.map((o) => el("option", { value: o, selected: o === values[f.name] ? true : null }, o)));
      box.addEventListener("change", () => {
        values[f.name] = box.value;
        if (f.name === "category") {  // a new kind: its first two units
          const u = c.units[box.value] || [];
          values.from_unit = u[0]; values.to_unit = u[1] || u[0];
          drawCalc();
        }
        work();
      });
    } else {
      box = el("input", { id, class: "tb-input", type: "text", inputmode: "decimal", autocomplete: "off",
        value: values[f.name] == null ? "" : String(values[f.name]), placeholder: c.id === "ohms_law" ? "Leave one blank" : "" });
      box.addEventListener("input", () => { values[f.name] = box.value; work(); });
    }
    return el("label", { class: "tb-field", for: id }, el("span", { class: "tb-field-label" }, f.label), box);
  }

  // The canvas's calculator card: its boxes, then the answer.
  function drawCalc() {
    const c = calcOf(open);
    $("tb-calc").replaceChildren(
      el("div", { class: "tb-calc-head" }, el("h2", {}, c.name), el("span", { class: "tb-cat" }, c.category)),
      el("p", { class: "dim" }, c.about),
      el("div", { class: "tb-fields" }, ...c.fields.map((f) => input(c, f))),
      el("div", { class: "tb-answer", id: "tb-answer", "aria-live": "polite" }));
    work();
  }

  function choose(id) {
    open = id;
    values = Object.assign({}, calcOf(id).example);
    history.replaceState(null, "", "#" + id);
    draw();
  }

  function calcList() {
    return el("section", { class: "glass tb-list" }, el("p", { class: "pw-label" }, "Calculators"),
      ...page.calculators.map((c) => el("button", { type: "button", class: "tb-row" + (c.id === open ? " on" : ""), "aria-pressed": String(c.id === open),
        onclick: () => choose(c.id) }, el("span", { class: "tb-row-name" }, c.name), el("span", { class: "dim" }, c.category))));
  }

  // ------------------------------------------------------------ alarms
  async function addAlarm() {
    const v = await form("Set an Alarm", page.forms.alarm.fields, {});
    if (v) act({ kind: "alarm.add", params: v });
  }
  function alarmRow(a) {
    const box = el("input", { type: "checkbox", role: "switch", checked: a.on ? true : null, "aria-label": a.label + " on" });
    box.addEventListener("change", () => act({ kind: "alarm.switch", params: { alarm_id: a.id, on: box.checked ? "yes" : "no" } }));
    return el("div", { class: "tb-alarm" + (a.on ? "" : " off") },
      el("span", { class: "tb-alarm-time" }, a.time),
      el("span", { class: "tb-alarm-what" }, el("span", {}, a.label), el("span", { class: "dim" }, a.repeat)),
      el("span", { class: "switch" }, box, el("span", { "aria-hidden": "true" })),
      btn("Delete", "btn-ghost btn-small", () => act({ kind: "alarm.delete", params: { alarm_id: a.id } })));
  }
  function alarms() {
    if (!page.can_alarm) return null;
    return el("section", { class: "glass tb-list" }, el("p", { class: "pw-label" }, "Alarms"),
      ...(page.alarms.length ? page.alarms.map(alarmRow) : [el("p", { class: "dim" }, "No alarms set.")]),
      el("p", { class: "dim" }, "Alarms ring on the PC."),
      btn("Set an Alarm", "btn-ghost", addAlarm));
  }

  // ------------------------------------------------------------ the other tools
  const watch = { start: 0, total: 0, laps: [], tick: 0 };
  const fmt = (ms) => { const s = ms / 1000; const m = Math.floor(s / 60); return String(m).padStart(2, "0") + ":" + (s % 60).toFixed(1).padStart(4, "0"); };
  const elapsed = () => watch.total + (watch.start ? Date.now() - watch.start : 0);
  function stopwatch() {
    const face = el("div", { class: "tb-watch-face", "aria-live": "off" }, fmt(elapsed()));
    const laps = el("ol", { class: "tb-laps" }, ...watch.laps.map((l) => el("li", {}, fmt(l))));
    const go = btn(watch.start ? "Stop" : "Start", "btn-primary btn-small", () => {
      if (watch.start) { watch.total = elapsed(); watch.start = 0; clearInterval(watch.tick); } else { watch.start = Date.now(); watch.tick = setInterval(() => { const f = document.querySelector(".tb-watch-face"); if (f) f.textContent = fmt(elapsed()); }, 100); }
      $("tb-watch").replaceChildren(stopwatch());
    });
    return el("div", { class: "tb-watch" }, face,
      el("div", { class: "row-buttons" }, go,
        btn("Lap", "btn-ghost btn-small", () => { if (watch.start) { watch.laps.unshift(elapsed()); $("tb-watch").replaceChildren(stopwatch()); } }),
        btn("Reset", "btn-ghost btn-small", () => { clearInterval(watch.tick); Object.assign(watch, { start: 0, total: 0, laps: [] }); $("tb-watch").replaceChildren(stopwatch()); })),
      laps);
  }
  function tools() {
    return el("section", { class: "glass tb-list" }, el("p", { class: "pw-label" }, "Tools"),
      ...page.tools.map((t) => {
        const link = t.where === "here" ? null
          : t.where === "pc" ? el("a", { class: "btn btn-ghost btn-small", href: MIA.desktop ? "/desktop-open/toolbox" : "assistant.html?ask=" + encodeURIComponent(t.ask || t.name) }, MIA.desktop ? "Open" : "Ask MIA")
            : el("a", { class: "btn btn-ghost btn-small", href: t.where }, "Open");
        return el("div", { class: "tb-tool" }, el("div", { class: "tb-tool-top" },
          el("span", { class: "tb-row-name" }, t.name), link), el("span", { class: "dim" }, t.note),
          t.id === "stopwatch" ? el("div", { id: "tb-watch" }, stopwatch()) : null);
      }));
  }

  function draw() {
    if (window.MIAIcons) MIAIcons.badge($("hero-icon"), "toolbox");
    $("tb-sub").textContent = page.alarms_on ? page.alarms_on + (page.alarms_on === 1 ? " alarm on." : " alarms on.") : "Calculators and quick tools.";
    $("panel").replaceChildren(el("div", { class: "tb-grid" },
      el("div", { class: "tb-col" }, el("section", { class: "glass tb-calc", id: "tb-calc" }), calcList()),
      el("div", { class: "tb-col" }, alarms(), tools())));
    drawCalc();
  }

  MIAShell.start(async () => {
    page = await MIA.toolbox();
    const want = location.hash.slice(1);
    if (!page.calculators.some((c) => c.id === open) || (want && page.calculators.some((c) => c.id === want))) open = want || page.calculators[0].id;
    if (!Object.keys(values).length || !document.getElementById("tb-calc")) values = Object.assign({}, calcOf(open).example);
    draw();
  });
})();
