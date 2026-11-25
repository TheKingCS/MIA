/*
 * bench.js — My Bench, the free build (claude, 2026-11-25; core/free_build.py, core/part_specs.py).
 * Renders MIA.bench(board): the board picker, the parts placed (kept in this browser, per board), Add A Part from every
 * spec MIA knows, his Component DB's parts for what he has, and Look Up A Part online (MIA.benchDraft, shown before
 * Add This Part, the approved action partspec.add). The breadboard is web/labsim.js's, checked by MIA.benchCheck as
 * he wires (no sketch to run). "Build me a…" (MIA.benchDesign, core/bench_designs.py) puts one of MIA's designs on
 * the bench for his goal. Formatting only: every rule is core's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const fill = (node, ...kids) => node.replaceChildren(...kids.flat().filter((k) => k != null));
  const store = (key, value) => {
    try {
      if (value === undefined) return JSON.parse(localStorage.getItem(key) || "null");
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) { /* this browser keeps nothing */ }
    return null;
  };
  let boardId = store("mia.bench.board") || "esp32dev";
  let lastSketch = "";  // the sketch of the design or saved build last put on the bench, kept with a save
  const partsKey = () => "mia.bench.parts." + boardId;
  const wiresKey = () => "bench." + boardId;  // web/labsim.js keeps the wires as mia.labsim.<this>

  const section = (title, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title)), ...body);

  function placedParts() { return (store(partsKey()) || []).filter((p) => p && p.id && p.spec); }

  function nextId(parts) {
    let n = 1;
    while (parts.some((p) => p.id === "p" + n)) n += 1;
    return "p" + n;
  }

  // Taking a part off also takes off the wires to it (they'd name a part that's gone).
  function removePart(id) {
    store(partsKey(), placedParts().filter((p) => p.id !== id));
    const wires = store("mia.labsim." + wiresKey()) || [];
    store("mia.labsim." + wiresKey(), wires.filter((w) => !w.some((t) => String(t).startsWith(id + "."))));
    MIAShell.refresh();
  }

  function lookup(data) {
    const input = el("input", { type: "text", class: "crs-ask-input", placeholder: "A part's name or model, like BME280 or HC-SR501",
      "aria-label": "A part to look up online", maxlength: "60" });
    const out = el("div", { class: "crs-ask-answer", "aria-live": "polite" });
    const go = el("button", { type: "submit", class: "btn btn-amber", disabled: data.lookup.allowed ? null : true }, "Look It Up");
    const form = el("form", { class: "crs-ask", onsubmit: async (e) => {
      e.preventDefault();
      if (!input.value.trim()) return;
      go.disabled = true;
      fill(out, el("p", { class: "dim" }, "Searching, then drafting its spec…"));
      try {
        const got = await MIA.benchDraft(input.value.trim());
        fill(out, el("p", {}, got.summary + "."), el("p", { class: "dim" }, got.source + ". Check it against the datasheet before you add it."),
          el("div", { class: "row-buttons" }, el("button", { type: "button", class: "btn btn-amber",
            onclick: () => MIAShell.act({ kind: "partspec.add", params: { spec: got.spec, source: got.source } }) }, "Add This Part")));
      } catch (err) {
        fill(out, el("p", {}, err.message));
      } finally { go.disabled = data.lookup.allowed ? null : true; }
    } }, el("div", { class: "crs-ask-row" }, input, go), out);
    return section("Look up a part", el("p", { class: "dim" }, data.lookup.allowed
      ? "For a part MIA doesn't know: she searches for its specs (only its name leaves this computer) and drafts them for you to check."
      : "Looking up online isn't available now: " + data.lookup.why), form);
  }

  // "Build me a ..." (core/bench_designs.py): a design for his goal on his board, its parts (what he has), wiring,
  // sketch and how to use it; Put It On The Bench places its parts and wires here, to check and change.
  function designer(data) {
    const input = el("input", { type: "text", class: "crs-ask-input", placeholder: "Build me a… motion light, temperature alarm, dry-soil alert, tank level gauge",
      "aria-label": "What to build", maxlength: "200" });
    const out = el("div", { class: "crs-ask-answer", "aria-live": "polite" });
    const go = el("button", { type: "submit", class: "btn btn-amber" }, "Design It");
    const reportBox = el("input", { type: "checkbox" });
    const reportLabel = el("label", { class: "sim-input" }, reportBox, el("span", {}, "Report its readings to MIA (ESP32, over Wi-Fi)"));
    const form = el("form", { class: "crs-ask", onsubmit: async (e) => {
      e.preventDefault();
      if (!input.value.trim()) return;
      go.disabled = true;
      try {
        const got = await MIA.benchDesign(input.value.trim(), data.board.id, reportBox.checked);
        if (!got.found) { fill(out, el("p", {}, "I don't have a design for that yet. I can do: " + got.designs.join(", ").toLowerCase() + ".")); return; }
        fill(out, el("h3", {}, got.name), el("p", {}, got.about),
          got.have.length ? el("p", { class: "dim" }, "You have: " + got.have.join(", ") + ".") : null,
          got.need.length ? el("p", { class: "dim" }, "You'd need: " + got.need.join(", ") + ".") : null,
          el("ol", { class: "crs-list" }, got.steps.map((s) => el("li", {}, s))),
          el("p", { class: "dim" }, got.use),
          got.libs.length ? el("p", { class: "dim" }, "Libraries: " + got.libs.join(", ")) : null,
          el("div", { class: "row-buttons" },
            el("button", { type: "button", class: "btn btn-amber", onclick: () => {
              store(partsKey(), got.parts);
              store("mia.labsim." + wiresKey(), got.wires);
              lastSketch = got.sketch;
              MIAShell.refresh();
            } }, "Put It On The Bench"),
            MIAShell.copyButton(got.sketch, "Copy The Sketch", "btn btn-ghost btn-small")),
          el("pre", { class: "crs-code" }, got.sketch),
          got.reports ? el("div", {}, el("h3", {}, "Reporting to MIA"),
            el("ol", { class: "crs-list" }, got.report_steps.map((s) => el("li", {}, s))),
            el("div", { class: "row-buttons" }, MIAShell.copyButton(got.secrets, "Copy secrets.h", "btn btn-ghost btn-small"),
              el("a", { class: "btn btn-ghost btn-small", href: "sensors.html" }, "Open Sensors")),
            el("pre", { class: "crs-code" }, got.secrets))
            : (reportBox.checked && !got.can_report ? el("p", { class: "dim" }, "Reporting to MIA needs Wi-Fi: choose the ESP32 board for that.") : null));
      } catch (err) {
        fill(out, el("p", {}, err.message));
      } finally { go.disabled = false; }
    } }, el("div", { class: "crs-ask-row" }, input, go), reportLabel, out);
    return section("Build me a…", el("p", { class: "dim" }, "Say what you want to make: MIA designs it for your board " +
      "from her tested designs, with what you have, and puts it on the bench to check and change."), form);
  }

  // His builds (core/bench_builds.py): Save This Build keeps what's on the board by name; each saved one can be opened
  // here again, marked built (his Component DB's counts go down: approved) or deleted.
  function builds(data, parts) {
    const name = el("input", { type: "text", class: "crs-ask-input", placeholder: "A name, like freezer alarm v1",
      "aria-label": "The build's name", maxlength: "80" });
    const save = el("form", { class: "crs-ask", onsubmit: (e) => {
      e.preventDefault();
      if (!name.value.trim()) { name.focus(); return; }
      MIAShell.act({ kind: "benchbuild.save", params: { name: name.value.trim(), board: data.board.id, parts,
        wires: store("mia.labsim." + wiresKey()) || [], sketch: lastSketch } });
    } }, el("div", { class: "crs-ask-row" }, name, el("button", { type: "submit", class: "btn btn-amber",
      disabled: parts.length ? null : true }, "Save This Build")));
    const list = (data.builds || []).length ? el("ul", { class: "crs-list" }, data.builds.map((b) => el("li", {},
      el("strong", {}, b.name), " (" + b.board + ", " + b.parts.length + " parts" + (b.built ? ", built " + b.built.slice(0, 10) : "") + ") ",
      el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => {
        boardId = b.board;
        store("mia.bench.board", boardId);
        store(partsKey(), b.parts);
        store("mia.labsim." + wiresKey(), b.wires);
        lastSketch = b.sketch || "";
        MIAShell.refresh();
      } }, "Open"),
      b.built ? null : el("button", { type: "button", class: "btn btn-ghost btn-small",
        onclick: () => MIAShell.act({ kind: "benchbuild.built", params: { build_id: b.id } }) }, "Mark It Built"),
      el("button", { type: "button", class: "btn btn-ghost btn-small",
        onclick: () => MIAShell.act({ kind: "benchbuild.remove", params: { build_id: b.id } }) }, "Delete")))) :
      el("p", { class: "dim" }, "Nothing saved yet.");
    return section("Your builds", save, list);
  }

  MIAShell.start(async () => {
    const data = await MIA.bench(boardId);
    if (!data.board) { fill($("panel"), el("p", { class: "empty" }, el("strong", {}, data.lookup.why))); return; }
    const specs = Object.fromEntries(data.specs.map((s) => [s.id, s]));
    const parts = placedParts().filter((p) => specs[p.spec]);
    // Wires only to what's here: a part taken off, or whose spec was removed, takes its wires with it.
    const here = new Set(data.board.left.concat(data.board.right).map((x) => x.id)
      .concat(["GND", "GND 2"], ...parts.map((p) => specs[p.spec].pins.map((x) => p.id + "." + x.id))));
    const saved = store("mia.labsim." + wiresKey()) || [];
    const kept = saved.filter((w) => Array.isArray(w) && w.every((t) => here.has(t)));
    if (kept.length !== saved.length) store("mia.labsim." + wiresKey(), kept);
    const picker = el("select", { "aria-label": "Your board", onchange: (e) => { boardId = e.target.value; store("mia.bench.board", boardId); MIAShell.refresh(); } },
      data.boards.map((b) => el("option", { value: b.id, selected: b.id === data.board.id ? true : null }, b.name)));
    const adding = el("select", { "aria-label": "A part to place" }, data.specs.map((s) => el("option", { value: s.id }, s.name + (s.builtin ? "" : " (yours)"))));
    const add = el("button", { type: "button", class: "btn btn-amber", onclick: () => {
      const now = placedParts();
      now.push({ id: nextId(now), spec: adding.value });
      store(partsKey(), now);
      MIAShell.refresh();
    } }, "Add To The Board");
    const placed = parts.length ? el("ul", { class: "crs-list" }, parts.map((p) => el("li", {},
      p.id + ": " + specs[p.spec].name + " (" + specs[p.spec].volts_min + " to " + specs[p.spec].volts_max + " V) ",
      el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => removePart(p.id) }, "Take It Off"))))
      : el("p", { class: "dim" }, "Nothing on the board yet: add a part.");
    const lab = { id: wiresKey(), circuit: { board: { id: data.board.id, name: data.board.name, label: data.board.label },
      left: data.board.left, right: data.board.right, steps: [], note: "",
      parts: parts.map((p) => ({ id: p.id, kind: p.spec, name: p.id + " " + specs[p.spec].name,
        pins: specs[p.spec].pins.map((x) => ({ id: p.id + "." + x.id, name: x.name })) })) } };
    const board = window.MIALabSim.render("bench", lab, { key: wiresKey(), noRun: true, title: "The breadboard", checkTitle: "MIA's check",
      intro: "Pick two dots to join them, pick a wire to take it out. MIA checks every wire against the parts' specs and the board's limits.",
      check: (wires) => MIA.benchCheck(data.board.id, parts, wires).then((r) => ({ sim: { problems: r.problems.length ? r.problems
        : (wires.length ? [{ level: "note", text: "Everything checks out so far." }] : []) }, build: { steps: [], next: null, done: false } })) });
    const mine = data.components.length ? el("ul", { class: "crs-list" }, data.components.map((c) =>
      el("li", {}, c.name + (c.value ? " " + c.value : "") + (c.quantity ? ", " + c.quantity + " on hand" : ""))))
      : el("p", { class: "dim" }, "Your Component DB is empty: add your parts in the Workshop, or tell MIA what you have.");
    fill($("panel"),
      section("Your board and parts", el("label", { class: "sim-input" }, el("span", {}, "Board"), picker), placed,
        el("div", { class: "row-buttons" }, adding, add)),
      designer(data),
      board,
      builds(data, parts),
      lookup(data),
      section("What you have", el("p", { class: "dim" }, "From your Component DB (the Workshop)."), mine));
  }, { refreshOnChange: true });
})();
