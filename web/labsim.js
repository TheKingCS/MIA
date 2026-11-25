/*
 * labsim.js — the ESP32 simulator on a course's page (claude, 2026-11-25; core/esp32_sim.py, web/course.html).
 * MIALabSim.render(course, lab) gives the Simulator section for a lab with a circuit: the board's pins and the lab's
 * parts drawn as a breadboard, where a wire is made by picking two terminals (a click, or Enter on one) and taken out
 * by picking it; the build in steps beside it, each ticked as his wires make it and the next one lit on the board
 * (building along with MIA); what's wrong with the circuit as he wires it; the inputs the lab reads (the knob, the
 * room, the soil, presses, requests); and Run It, which plays back what the board would print and what the LED and
 * relay would do, with whether the lab's check would pass. All judging is core's (POST /api/labs/{course}/sim): this
 * draws and plays it back. His wires are kept in this browser only (localStorage), per lab. The free build
 * (web/bench.js) uses the same breadboard with its own check (core/free_build.py) and no run.
 */
(function () {
  "use strict";
  const SVG = "http://www.w3.org/2000/svg";
  const RAIL = { "3V3": "pwr", "5V": "pwr", VIN: "vin", GND: "gnd", "GND 2": "gnd" };

  function svgEl(tag, attrs, ...kids) {
    const node = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null) continue;
      if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    }
    for (const kid of kids.flat()) if (kid != null) node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    return node;
  }
  const key = (lesson) => "mia.labsim." + lesson;
  function load(lesson) {
    try { return (JSON.parse(localStorage.getItem(key(lesson)) || "[]") || []).filter((w) => Array.isArray(w) && w.length === 2); }
    catch (e) { return []; }
  }
  function keep(lesson, wires) { try { localStorage.setItem(key(lesson), JSON.stringify(wires)); } catch (e) { /* this browser keeps nothing */ } }

  // The inputs a lab reads, as controls; inputs() turns them into what the simulator takes for a run of `seconds`.
  function controls(id) {
    const { el } = MIAShell;
    const range = (label, value) => {
      const input = el("input", { type: "range", min: "0", max: "100", value: String(value) });
      return [input, el("label", { class: "sim-input" }, el("span", {}, label), input)];
    };
    const number = (label, value, step) => {
      const input = el("input", { type: "number", value: String(value), step: step || "1", class: "sim-number" });
      return [input, el("label", { class: "sim-input" }, el("span", {}, label), input)];
    };
    const tick = (label, on) => {
      const input = el("input", { type: "checkbox", checked: on || null });
      return [input, el("label", { class: "sim-input" }, input, el("span", {}, label))];
    };
    if (id === "pot") {
      const [knob, a] = range("Knob", 50), [sweep, b] = tick("Turn it end to end while it runs", true);
      return { seconds: 6, view: [a, b], inputs: (s) => ({ pot: sweep.checked ? [[0, 0], [s, 1]] : knob.value / 100 }) };
    }
    if (id === "dht") {
      const [t, a] = number("Room °C", 21.5, "0.5"), [h, b] = number("Humidity %", 45);
      return { seconds: 10, view: [a, b], inputs: () => ({ temp: Number(t.value), humidity: Number(h.value) }) };
    }
    if (id === "soil" || id === "sleep" || id === "web") {
      const [wet, a] = range("Dry ↔ wet", 30), [water, b] = tick("Water it partway through", id === "soil");
      const seconds = id === "sleep" ? 31 : id === "soil" ? 8 : 6;
      const extra = id === "web" ? number("Browser requests", 1) : null;
      return { seconds, view: [a, b, extra && extra[1]], inputs: (s) => {
        const level = wet.value / 100;
        const out = { moisture: water.checked ? [[0, level], [s / 2, level], [s / 2 + 1, 1]] : level };
        if (extra) out.requests = Array.from({ length: Math.max(0, Math.min(20, Number(extra[0].value) || 0)) }, (_, i) => 2 + i * 0.5);
        return out;
      } };
    }
    if (id === "light") {
      const [level, a] = range("Light", 50), [swing, b] = tick("Cover it, then light it, while it runs", true);
      return { seconds: 7, view: [a, b], inputs: (s) => ({ light: swing.checked ? [[0, 0.05], [s / 2, 0.05], [s / 2 + 1, 0.95]] : level.value / 100 }) };
    }
    if (id === "distance") {
      const [cm, a] = number("Your hand at (cm)", 30), [move, b] = tick("Move it from 10 to 60 cm while it runs", true);
      return { seconds: 5, view: [a, b], inputs: (s) => ({ distance: move.checked ? [[0, 10], [s, 60]] : Number(cm.value) }) };
    }
    if (id === "button") {
      const [n, a] = number("Press BOOT", 3);
      return { seconds: 6, view: [a], inputs: () => ({ presses: Array.from({ length: Math.max(0, Math.min(20, Number(n.value) || 0)) }, (_, i) => 1 + i * 0.4) }) };
    }
    if (id === "watchdog") {
      // what he'd type in the serial monitor (hb, dose) and BOOT; then the quiet that makes it go safe
      const [hb, a] = number("Heartbeats from the PC", 2), [d, b] = number("Doses asked for", 1);
      const [press, c] = tick("Press BOOT near the end", true);
      const many = (input) => Math.max(0, Math.min(10, Number(input.value) || 0));
      return { seconds: 20, view: [a, b, c], inputs: (s) => ({
        heartbeats: Array.from({ length: many(hb) }, (_, i) => 1 + i),
        doses: Array.from({ length: many(d) }, (_, i) => 1.5 + i * 1.5),
        presses: press.checked ? [s - 0.5] : [] }) };
    }
    return { seconds: id === "relay" ? 9 : 6, view: [], inputs: () => ({}) };
  }

  // opts (the free build, web/bench.js): check(wires, inputs, seconds) in place of the lab's simulator, key for the
  // wires kept, noRun (no sketch to run: the check alone), title and intro, and checkTitle (the problems alone under
  // it, no build steps).
  function render(course, lab, opts) {
    opts = opts || {};
    const c = lab.circuit;
    if (!c) return null;
    const { el } = MIAShell;
    const key = opts.key || lab.id;
    const check = opts.check || ((w, inputs, seconds) => MIA.courseSim(course, lab.id, w, inputs, seconds, c.board && c.board.id));
    let wires = load(key);
    let picked = null;
    let build = { steps: c.steps.map((s) => Object.assign({ done: false }, s)), next: c.steps.length ? 1 : null, done: false };
    let timers = [];
    const ctl = controls(lab.id);

    // Where each terminal sits: the board's pins down its two sides, the parts stacked to the right.
    const PIN = 22, TOP = 50, LEFT = 74, RIGHT = 226, PART = 388;
    const at = {}, out = {};
    c.left.forEach((p, i) => { at[p.id] = [LEFT, TOP + i * PIN]; out[p.id] = -1; });
    c.right.forEach((p, i) => { at[p.id] = [RIGHT, TOP + i * PIN]; out[p.id] = 1; });
    let y = TOP - 10;
    const placed = c.parts.map((part) => {
      const top = y;
      part.pins.forEach((t, i) => { at[t.id] = [PART, top + 34 + i * 26]; out[t.id] = -1; });
      y += 46 + part.pins.length * 26;
      return [part, top];
    });
    const height = Math.max(TOP + c.left.length * PIN + 24, y + 10);
    const names = {};
    c.left.forEach((p) => { names[p.id] = p.label === "GND" ? "GND, left side" : p.label; });
    c.right.forEach((p) => { names[p.id] = p.label === "GND" ? "GND, right side" : p.label; });
    c.parts.forEach((part) => part.pins.forEach((t) => { names[t.id] = part.name + " " + t.name; }));

    const svg = svgEl("svg", { viewBox: "0 0 640 " + height, class: "sim-board", role: "group",
      "aria-label": "The breadboard: pick two terminals to wire them, pick a wire to take it out" });
    const steps = el("ol", { class: "sim-steps" });
    const problems = el("ul", { class: "sim-problems", "aria-live": "polite" });
    const monitor = el("pre", { class: "crs-monitor sim-monitor", "aria-live": "polite" }, "Run it to see what the board prints.");
    const verdict = el("p", { class: "dim" });
    const leds = [], relays = [];
    let onboard = null;

    const stepEnds = () => {
      const s = build.steps.find((x) => x.n === build.next);
      return s ? [s.a, s.b] : [];
    };

    function terminal(id, x, y2, label, side) {
      const lit = stepEnds().includes(id);
      const used = wires.some((w) => w.includes(id));
      const dot = svgEl("circle", { cx: x, cy: y2, r: 6, tabindex: "0", role: "button", "aria-label": names[id] || id,
        class: "sim-pin" + (picked === id ? " picked" : "") + (lit ? " step" : "") + (used ? " used" : ""),
        onclick: () => pick(id), onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(id); } } });
      const text = svgEl("text", { x: x + side * 11, y: y2 + 4, class: "sim-pin-label", "text-anchor": side > 0 ? "start" : "end" }, label);
      return [dot, text];
    }

    function draw() {
      svg.replaceChildren();
      leds.length = 0; relays.length = 0;
      svg.append(svgEl("rect", { x: LEFT - 22, y: TOP - 34, width: RIGHT - LEFT + 44, height: c.left.length * PIN + 50, rx: 10, class: "sim-chip" }));
      svg.append(svgEl("text", { x: (LEFT + RIGHT) / 2, y: TOP - 14, class: "sim-chip-name", "text-anchor": "middle" }, (c.board && c.board.label) || "ESP32"));
      onboard = svgEl("circle", { cx: (LEFT + RIGHT) / 2, cy: TOP + 6, r: 5, class: "sim-onboard" });
      svg.append(onboard, svgEl("text", { x: (LEFT + RIGHT) / 2, y: TOP + 24, class: "sim-pin-label", "text-anchor": "middle" }, "LED"));
      svg.append(svgEl("rect", { x: (LEFT + RIGHT) / 2 - 16, y: TOP + c.left.length * PIN - 6, width: 32, height: 12, rx: 3, class: "sim-usb" }));
      // The wires under the pins, so a wire crossing a pin never blocks picking it.
      const wireLayer = svgEl("g", { class: "sim-wires" });
      svg.append(wireLayer);
      c.left.forEach((p) => svg.append(...terminal(p.id, ...at[p.id], p.label, 1)));
      c.right.forEach((p) => svg.append(...terminal(p.id, ...at[p.id], p.label, -1)));
      placed.forEach(([part, top]) => {
        svg.append(svgEl("rect", { x: PART + 14, y: top + 8, width: 600 - PART, height: 20 + part.pins.length * 26, rx: 8, class: "sim-part" }));
        svg.append(svgEl("text", { x: PART + 26, y: top + 24, class: "sim-part-name" }, part.name));
        part.pins.forEach((t) => {
          const [x, ty] = at[t.id];
          svg.append(svgEl("line", { x1: x, y1: ty, x2: PART + 14, y2: ty, class: "sim-lead" }));
          svg.append(...terminal(t.id, x, ty, t.name, 1).map((n, i) => (i ? svgEl("text", { x: PART + 26, y: ty + 4, class: "sim-pin-label" }, t.name) : n)));
        });
        if (part.kind === "led") {
          const glow = svgEl("circle", { cx: 572, cy: top + 40, r: 11, class: "sim-led" });
          leds.push(glow);
          svg.append(glow);
        }
        if (part.kind === "relay" || part.kind === "servo" || part.kind === "buzzer") {
          const box = svgEl("rect", { x: 558, y: top + 30, width: 26, height: 18, rx: 3, class: "sim-relay" });
          relays.push(box);
          svg.append(box);
        }
      });
      wires.forEach((w, i) => {
        const [a, b] = w;
        if (!at[a] || !at[b]) return;
        const [ax, ay] = at[a], [bx, by] = at[b];
        const bend = Math.max(40, Math.abs(bx - ax) / 3);
        const d = "M" + ax + " " + ay + " C" + (ax + out[a] * bend) + " " + ay + " " + (bx + out[b] * bend) + " " + by + " " + bx + " " + by;
        const kind = RAIL[a] || RAIL[b] || "sig";
        wireLayer.append(svgEl("path", { d, class: "sim-wire " + kind, tabindex: "0", role: "button",
          "aria-label": "Wire from " + (names[a] || a) + " to " + (names[b] || b) + ": take it out",
          onclick: () => unwire(i), onkeydown: (e) => { if (e.key === "Enter") unwire(i); } }, svgEl("title", {}, (names[a] || a) + " – " + (names[b] || b))));
      });
      steps.replaceChildren(...(build.steps.length ? build.steps.map((s) => el("li", {
        class: s.done ? "done" : s.n === build.next ? "now" : "" }, el("strong", {}, (s.done ? "✓ " : "") + s.words), el("span", { class: "dim" }, s.why)))
        : [el("li", {}, c.note || "Nothing to wire.")]));
    }

    function pick(id) {
      if (!picked) picked = id;
      else if (picked === id) picked = null;
      else {
        if (!wires.some((w) => w.includes(picked) && w.includes(id))) wires.push([picked, id]);
        picked = null;
        changed();
      }
      draw();
    }
    function unwire(i) { wires.splice(i, 1); changed(); draw(); }

    // After every change: where the build is and what's wrong, from core (a one-second run).
    async function changed() {
      keep(key, wires);
      try {
        const got = await check(wires, {}, 1);
        build = got.build;
        showProblems(got.sim.problems);
        draw();
      } catch (e) { problems.replaceChildren(el("li", {}, e.message)); }
    }
    function showProblems(list) {
      problems.replaceChildren(...list.map((p) => el("li", { class: "sim-" + p.level }, p.text)));
    }

    function stop() { timers.forEach(clearTimeout); timers = []; }
    function light(o) {
      if ("onboard" in o && onboard) onboard.style.opacity = String(0.15 + 0.85 * o.onboard);
      if ("led" in o) leds.forEach((g) => { g.style.opacity = String(0.15 + 0.85 * o.led); g.classList.toggle("lit", o.led > 0); });
      if ("relay" in o || "box" in o) relays.forEach((r) => r.classList.toggle("on", !!(o.relay || o.box)));
    }
    async function run() {
      stop();
      const seconds = ctl.seconds;
      monitor.textContent = "";
      verdict.textContent = "Running…";
      try {
        const got = await check(wires, ctl.inputs(seconds), seconds);
        build = got.build;
        draw();
        const sim = got.sim;
        showProblems(sim.problems);
        if (!sim.ran) { monitor.textContent = "(it didn't run)"; verdict.textContent = sim.said; return; }
        const speed = Math.max(1, seconds / 10);  // a long run plays back faster
        sim.trace.forEach((x) => timers.push(setTimeout(() => {
          monitor.textContent += x.line + "\n";
          monitor.scrollTop = monitor.scrollHeight;
        }, x.t * 1000 / speed)));
        sim.outputs.forEach((o) => timers.push(setTimeout(() => light(o), o.t * 1000 / speed)));
        timers.push(setTimeout(() => {
          verdict.textContent = sim.said;
          if (!sim.trace.length) monitor.textContent = "(the board printed nothing)";
        }, seconds * 1000 / speed + 200));
      } catch (e) { verdict.textContent = e.message; }
    }

    draw();
    if (wires.length) changed();
    const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
    return el("section", { class: "glass money-section sim" },
      el("div", { class: "sect" }, el("h2", {}, opts.title || "Simulator")),
      el("p", { class: "dim" }, opts.intro || ("Build it here first, wire for wire, alongside your real breadboard: pick two dots to " +
        "join them, pick a wire to take it out. MIA checks each one as you go. " + (lab.try || ""))),
      c.note ? el("p", { class: "dim" }, c.note) : null,
      el("div", { class: "sim-grid" }, el("div", { class: "sim-canvas" }, svg),
        el("div", {}, el("h3", {}, opts.checkTitle || "Build it with MIA"), opts.checkTitle ? null : steps, problems)),
      !opts.noRun && ctl.view.length ? el("div", { class: "sim-inputs" }, ...ctl.view) : null,
      el("div", { class: "row-buttons" },
        opts.noRun ? null : btn("Run It", "btn-amber", run),
        c.steps.length ? btn("Show The Finished Circuit", "btn-ghost", () => { wires = c.steps.map((s) => [s.a, s.b]); changed(); draw(); }) : null,
        wires.length || c.steps.length ? btn("Clear The Wires", "btn-ghost", () => {
          stop(); wires = []; picked = null; light({ onboard: 0, led: 0, relay: false });
          monitor.textContent = "Run it to see what the board prints."; verdict.textContent = ""; changed(); draw();
        }) : null),
      opts.noRun ? null : monitor, opts.noRun ? null : verdict);
  }

  window.MIALabSim = { render };
})();
