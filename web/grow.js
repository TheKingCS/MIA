/*
 * grow.js — the Grow Lab (claude, 2026-10-17, DEC-0030 phase D). Renders
 * MIA.grow() (core/web_grow.py), as tabs of the Greenhouse (Zac, 2026-10-17:
 * "Isn't Grow Lab essentially what the Greenhouse app is"): equipment.js
 * shows them beside the greenhouse's equipment through window.MIAGrow. Tabs: Growing (batches: Harvest, Lost
 * Some, days to harvest, yield per plant), Water (each place's latest
 * readings against your ranges, a small trend, Log Reading, Set Range;
 * MIA only warns, people run the equipment), Experiments (batches side by
 * side, Conclude) and Harvests (totals by crop). Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["growing", "Growing"], ["water", "Water"], ["experiments", "Experiments"], ["harvests", "Harvests"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "growing";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const f = (name, label, type, extra) => Object.assign({ name, label, type, required: false, options: [], default: null }, extra || {});
  const measureChoice = () => f("measure", "What you measured", "choice", { required: true, options: page.measures.map((m) => m.id), default: "ph" });
  const label = (id) => (page.measures.find((m) => m.id === id) || { label: id }).label;

  async function add(key, title) {
    const v = await form(title, page.forms[key].fields, {}, page.picks);
    if (v) act({ kind: key + ".add", params: v });
  }
  async function edit(key, item, name) {
    const v = await form("Edit " + name, page.forms[key].fields, item.values, page.picks);
    if (v) act({ kind: key + ".edit", params: Object.assign({ [page.forms[key].id_param]: item.id }, v) });
  }
  async function harvest(b) {
    const v = await form("Harvest " + b.crop, [f("amount", "How much", "amount", { required: true }), f("unit", "Unit (lb, heads, bunches…)", "text", { default: b.harvests[0] ? b.harvests[0].unit : "" }),
      f("note", "Notes", "text"), f("done", "Was that the last of it?", "choice", { options: ["no", "yes"], default: "no" })], {});
    if (v) act({ kind: "batch.harvest", params: Object.assign({ batch_id: b.id }, v) });
  }
  async function lost(b) {
    const v = await form("Lost Some " + b.crop, [f("how_many", "How many", "int"), f("why", "Why (if you know)", "text"),
      f("all", "All of it?", "choice", { options: ["no", "yes"], default: "no" })], {});
    if (v) act({ kind: "batch.lost", params: Object.assign({ batch_id: b.id }, v) });
  }
  async function reading(system) {
    const v = await form("Log A Reading", [f("system", "Where", "text", { required: true, default: system || (page.systems[0] || {}).name || "" }),
      measureChoice(), f("value", "The reading", "number", { required: true }), f("note", "Notes", "text")], {});
    if (v) act({ kind: "grow.reading", params: v });
  }
  async function range(system, row) {
    const v = await form("Your Range: " + label(row ? row.measure : "ph"), [f("system", "Where", "text", { required: true, default: system }),
      Object.assign(measureChoice(), { default: row ? row.measure : "ph" }),
      f("low", "Low end", "number", { default: row ? row.low : null }), f("high", "High end", "number", { default: row ? row.high : null })], {});
    if (v) act({ kind: "grow.range", params: v });
  }

  function batchCard(b) {
    const fig = b.figures;
    return el("article", { class: "glass craft-card" },
      el("div", { class: "craft-head static" },
        el("div", {}, el("h3", {}, b.crop + (b.variety ? " · " + b.variety : "")),
          el("p", { class: "dim" }, [b.system, b.method, b.count ? b.count + " planted" : null, "since " + day(b.planted)].filter(Boolean).join(" · "))),
        chip(b.status, b.status === "Growing" ? "chip-soon" : b.status === "Lost" ? "chip-bad" : "chip-ok")),
      el("div", { class: "craft-tiles" },
        fig.days_growing != null ? el("div", { class: "craft-tile" }, el("span", { class: "dim" }, "Days"), el("strong", {}, String(fig.days_growing))) : null,
        fig.days_to_harvest != null ? el("div", { class: "craft-tile" }, el("span", { class: "dim" }, "To Harvest"), el("strong", {}, fig.days_to_harvest + " d")) : null,
        fig.main_yield ? el("div", { class: "craft-tile ok" }, el("span", { class: "dim" }, "Yield"), el("strong", {}, fig.main_yield + " " + fig.main_unit)) : null,
        fig.per_plant != null ? el("div", { class: "craft-tile" }, el("span", { class: "dim" }, "Per Plant"), el("strong", {}, fig.per_plant + " " + fig.main_unit)) : null,
        fig.survival != null && b.lost ? el("div", { class: "craft-tile" }, el("span", { class: "dim" }, "Survived"), el("strong", {}, fig.survival + "%")) : null),
      b.loss_note ? el("p", { class: "dim" }, "Losses: " + b.loss_note) : null,
      b.notes ? el("p", { class: "dim" }, b.notes) : null,
      buttons(b.status === "Growing" ? btn("Harvest", "btn-green btn-small", () => harvest(b)) : null,
        b.status === "Growing" ? btn("Lost Some", "btn-ghost btn-small", () => lost(b)) : null,
        btn("Edit", "btn-ghost btn-small", () => edit("batch", b, b.crop)),
        btn("Delete", "btn-ghost btn-small", () => act({ kind: "batch.delete", params: { batch_id: b.id } }))));
  }

  function spark(values) {
    if (values.length < 2) return null;
    const lo = Math.min(...values), hi = Math.max(...values), span = hi - lo || 1;
    const pts = values.map((v, i) => (i * 100 / (values.length - 1)).toFixed(1) + "," + (28 - (v - lo) * 24 / span).toFixed(1)).join(" ");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 100 30"); svg.setAttribute("class", "grow-spark"); svg.setAttribute("aria-hidden", "true");
    const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    line.setAttribute("points", pts);
    svg.append(line);
    return svg;
  }

  function systemCard(s) {
    return el("article", { class: "glass craft-card" },
      el("div", { class: "craft-head static" }, el("div", {}, el("h3", {}, s.name), el("p", { class: "dim" }, s.growing === 1 ? "1 batch growing" : s.growing + " batches growing")),
        btn("Log Reading", "btn-amber btn-small", () => reading(s.name))),
      s.readings.length ? el("ul", { class: "craft-needs grow-readings" }, s.readings.map((r) => el("li", { class: r.side ? "missing" : "" },
        el("span", {}, r.label + ": ", el("strong", {}, r.value == null ? "—" : r.value + (r.unit ? " " + r.unit : "")),
          r.side ? " " : "", r.side ? chip(r.side === "high" ? "High" : "Low", "chip-bad") : null),
        spark(r.trend),
        el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => range(s.name, r) },
          (r.low != null ? r.low : "–") + " to " + (r.high != null ? r.high : "–") + (r.mine ? "" : " (starter)")))))
        : el("p", { class: "dim" }, "No readings yet."));
  }

  const VIEWS = {
    growing: () => {
      const now = page.batches.filter((b) => b.status === "Growing"), done = page.batches.filter((b) => b.status !== "Growing");
      return [section("Growing", btn("Plant A Batch", "btn-amber", () => add("batch", "Plant A Batch")),
        now.length ? el("div", { class: "craft-grid" }, now.map(batchCard))
          : el("p", { class: "empty" }, "Nothing growing yet. Plant a batch: what, where, how many.")),
      done.length ? section("Done", null, el("div", { class: "craft-grid" }, done.map(batchCard))) : null].filter(Boolean);
    },
    water: () => [
      page.alerts.length ? section("Outside Your Range", null, el("ul", { class: "craft-needs" }, page.alerts.map((a) => el("li", { class: "missing" },
        el("span", {}, a.system + ": " + a.label + " " + a.value + (a.unit ? " " + a.unit : "") + " is " + a.side),
        el("span", { class: "dim" }, "range " + (a.low != null ? a.low : "–") + " to " + (a.high != null ? a.high : "–") + (a.mine ? "" : " (starter)"))))),
        el("p", { class: "dim" }, "MIA only flags readings. You decide what to do with the fish, the plants and the equipment.")) : null,
      section("Tanks, Beds And Rooms", btn("Log Reading", "btn-amber", () => reading("")),
        page.systems.length ? el("div", { class: "craft-grid" }, page.systems.map(systemCard))
          : el("p", { class: "empty" }, "Log a reading for a tank or bed and it shows here. Starter ranges are common starting points: set your own.")),
    ].filter(Boolean),
    experiments: () => section("Experiments", btn("New Experiment", "btn-amber", () => add("experiment", "New Experiment")),
      page.experiments.length ? el("div", { class: "craft-grid" }, page.experiments.map((e) => el("article", { class: "glass craft-card" },
        el("div", { class: "craft-head static" }, el("h3", {}, e.question), chip(e.status, e.status === "Concluded" ? "chip-ok" : "chip-soon")),
        e.batches.length ? el("div", { class: "grow-compare" }, e.batches.map((b) => el("div", { class: "craft-tile" },
          el("strong", {}, b.crop + (b.variety ? " · " + b.variety : "")),
          el("span", { class: "dim" }, [b.system, b.figures.days_to_harvest != null ? b.figures.days_to_harvest + " d to harvest" : null,
            b.figures.main_yield ? b.figures.main_yield + " " + b.figures.main_unit : null,
            b.figures.per_plant != null ? b.figures.per_plant + " / plant" : null,
            b.figures.survival != null ? b.figures.survival + "% survived" : null].filter(Boolean).join(" · ")))))
          : el("p", { class: "dim" }, "Add the batches you're comparing."),
        e.conclusion ? el("p", {}, "Found: " + e.conclusion) : null,
        buttons(btn("Add A Batch", "btn-ghost btn-small", async () => {
          const v = await form("Add A Batch To The Experiment", [f("batch_id", "Batch", "pick", { required: true, options: ["batches"] })], {}, page.picks);
          if (v) act({ kind: "experiment.include", params: { experiment_id: e.id, batch_id: v.batch_id } });
        }), e.status !== "Concluded" ? btn("Conclude", "btn-green btn-small", async () => {
          const v = await form("What Did You Find?", [f("conclusion", "What you found", "textarea", { required: true })], {});
          if (v) act({ kind: "experiment.conclude", params: { experiment_id: e.id, conclusion: v.conclusion } });
        }) : null, btn("Delete", "btn-ghost btn-small", () => act({ kind: "experiment.delete", params: { experiment_id: e.id } }))))))
        : el("p", { class: "empty" }, "Ask a question, like which variety grows best in Tank A, and compare the batches that answer it.")),
    harvests: () => section("Harvests", null, page.harvests.length ? el("div", { class: "rows" }, page.harvests.map((h) =>
      el("div", { class: "row money-row" }, el("div", { class: "row-title" }, h.crop), chip(h.amount + (h.unit ? " " + h.unit : "")))))
      : el("p", { class: "empty" }, "No harvests yet.")),
  };

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.growing), el("span", { class: "t" }, "Growing")),
      el("div", { class: "cell " + (c.alerts ? "bad" : "ok") }, el("span", { class: "n" }, c.alerts), el("span", { class: "t" }, "Out Of Range")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.experiments), el("span", { class: "t" }, "Experiments")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) => el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
      onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...[].concat(VIEWS[tab]()));
  }

  // Inside the Greenhouse (equipment.js draws the frame, tabs and strip).
  if (document.body.dataset.scope === "greenhouse") {
    window.MIAGrow = {
      load: async () => { page = await MIA.grow(); return page; },
      views: VIEWS,
    };
    return;
  }

  MIAShell.start(async () => {
    page = await MIA.grow();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, "The Grow Lab isn't set up on this MIA."));
      return;
    }
    draw();
  });
})();
