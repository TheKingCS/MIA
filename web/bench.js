/*
 * bench.js — My Bench, the free build (claude, 2026-11-25; core/free_build.py, core/part_specs.py).
 * Renders MIA.bench(board): the board picker, the parts placed (kept in this browser, per board), Add A Part from every
 * spec MIA knows, his Component DB's parts for what he has, and Look Up A Part online (MIA.benchDraft, shown before
 * Add This Part, the approved action partspec.add). The breadboard is web/labsim.js's, checked by MIA.benchCheck as
 * he wires (no sketch to run). Formatting only: every rule is core's.
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
      board,
      lookup(data),
      section("What you have", el("p", { class: "dim" }, "From your Component DB (the Workshop)."), mine));
  }, { refreshOnChange: true });
})();
