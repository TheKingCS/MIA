/*
 * asset.js — one asset's page (claude, 2026-10-06, DEC-0017). Renders
 * MIA.asset(id). Done, readings, tasks, the asset itself and its documents
 * all change through equipment actions (confirm, undo); files go through
 * MIA.upload / MIA.download.
 */
(function () {
  "use strict";
  const { el, act, form, say, talk } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const id = new URLSearchParams(location.search).get("id") || "";
  const ICONS = { "Vehicle": "🚗", "Power Equipment": "🚜", "Appliance": "🔌", "Property": "🏠", "Garden/Plant": "🌱",
    "Tool": "🔨", "Other": "🔧" };
  let TABS = [["overview", "Overview"], ["maintenance", "Maintenance"], ["missions", "Missions"],
    ["documents", "Documents"], ["costs", "Costs"], ["history", "History"], ["parts", "Parts"]];
  let page = null;
  let tab = location.hash.slice(1) || "";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const chip = (row) => el("span", { class: "when " + (row.needs_attention ? "overdue" : row.urgency === "due_soon" ? "today" : "") }, row.text);
  const sym = "$";
  const fmt = (n) => n == null ? "—" : sym + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const card = (title, ...kids) => el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title)), ...kids);

  // ------------------------------------------------------------ changes
  async function done(row) {
    if (row.action.asks_meter) {
      const values = await form("Done: " + row.title, page.forms.done.fields, {});
      if (values) act({ kind: "maintenance.done", params: { task_id: row.id, meter_value: values.meter_value } });
    } else act(row.action);
  }
  async function logTask(taskId, title) {
    const values = await form("Log a reading: " + title, page.forms.task_reading.fields, {});
    if (values) act({ kind: "maintenance.reading", params: Object.assign({ task_id: taskId }, values) });
  }
  async function logMeter(meter) {
    const values = await form("Log a reading", page.forms.asset_reading.fields, { meter_name: meter || "" });
    if (values) act({ kind: "asset.reading", params: Object.assign({ asset_id: page.id }, values) });
  }
  async function editTask(row) {
    const values = await form("Edit task", page.forms.maintenance_task.fields, row.values, { assets: [{ id: page.id, name: page.name }] });
    if (values) act({ kind: "maintenance_task.edit", params: Object.assign({ task_id: row.id }, values) });
  }
  async function addTask() {
    const values = await form("Add a task for " + page.name, page.forms.maintenance_task.fields, { asset_id: page.id },
      { assets: [{ id: page.id, name: page.name }] });
    if (values) act({ kind: "maintenance_task.add", params: values });
  }
  async function editAsset() {
    const values = await form("Edit " + page.name, page.forms.asset.fields, page.values);
    if (values) act({ kind: "asset.edit", params: Object.assign({ asset_id: page.id }, values) });
  }
  async function deleteAsset() {
    const result = await act({ kind: "asset.delete", params: { asset_id: page.id } });
    if (result) location.href = page.scope_page || "garage.html";
  }
  async function openDocument(name) {
    try {
      const blob = await MIA.download("/api/assets/" + encodeURIComponent(page.id) + "/documents/" + encodeURIComponent(name));
      const url = URL.createObjectURL(blob);
      const link = el("a", { href: url, download: name, target: "_blank", rel: "noopener" });
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { say(e.message); }
  }
  async function upload(input) {
    const file = input.files && input.files[0];
    if (!file) return;
    try {
      const result = await MIA.upload("/api/assets/" + encodeURIComponent(page.id) + "/documents", file);
      say(result.message);
      MIAShell.refresh();
    } catch (e) { say(e.message); }
    input.value = "";
  }

  // ------------------------------------------------------------ pieces
  function taskRow(row, compact) {
    const meterish = row.trigger !== "calendar";
    return el("div", { class: "row money-row " + (row.needs_attention ? "overdue" : "") },
      el("div", {}, el("div", { class: "row-title" }, row.title),
        el("div", { class: "row-sub" }, [row.trigger === "calendar" ? (row.interval_days ? "every " + row.interval_days + " days" : "one time")
          : row.trigger + (row.meter_interval ? " · every " + row.meter_interval + " " + (row.unit || "") : ""),
        row.last_completed ? "last done " + row.last_completed : null, row.predicted].filter(Boolean).join(" · "),
        row.series ? el("a", { class: "pw-hist", href: "lab.html#" + encodeURIComponent(row.series) }, " · Chart ›") : null)),
      el("div", { class: "row-meta" }, chip(row),
        el("div", { class: "row-buttons" },
          row.action ? btn("Done", "btn-green", () => done(row)) : null,
          compact ? null : [
            meterish ? btn("Log reading", "btn-ghost", () => logTask(row.id, row.title)) : null,
            btn("Edit", "btn-ghost", () => editTask(row)),
            btn("Delete", "btn-ghost danger", () => act({ kind: "maintenance_task.delete", params: { task_id: row.id } }))])));
  }
  function missionRow(m) {
    return el("div", { class: "row money-row" },
      el("div", {}, el("div", { class: "row-title" }, (m.icon ? m.icon + " " : "") + m.name),
        el("div", { class: "row-sub" }, [m.objectives ? m.objectives_done + " of " + m.objectives + " objectives" : null,
          m.reward_xp ? "+" + m.reward_xp + " XP" : null].filter(Boolean).join(" · "))),
      el("div", { class: "row-meta" }, el("span", { class: "chip " + (m.status === "completed" ? "chip-ok" : "chip-soon") }, m.status)));
  }
  function details() {
    return el("dl", { class: "details" }, page.details.flatMap((d) => [el("dt", {}, d.label), el("dd", {}, d.value)]),
      page.notes ? [el("dt", {}, "Notes"), el("dd", {}, page.notes)] : []);
  }
  function documentRow(d) {
    return el("div", { class: "row money-row" }, el("div", {}, el("div", { class: "row-title" }, "📄 " + d.name)),
      el("div", { class: "row-meta" }, el("div", { class: "row-buttons" },
        btn("Open", "btn-green", () => openDocument(d.name)),
        btn("Remove", "btn-ghost danger", () => act({ kind: "asset.document_remove", params: { asset_id: page.id, filename: d.name } })))));
  }
  function uploader() {
    const input = el("input", { type: "file", id: "doc-file", class: "visually-hidden", onchange: (e) => upload(e.target) });
    return el("label", { class: "btn btn-amber", for: "doc-file" }, "Add a document", input);
  }

  function partRow(p) {
    const state = p.state === "out" ? el("span", { class: "chip chip-soon" }, "Out") : p.state === "low" ? el("span", { class: "chip chip-soon" }, "Low") : null;
    return el("div", { class: "row money-row" },
      el("div", {}, el("div", { class: "row-title" }, p.name),
        el("div", { class: "row-sub" }, [p.have + (p.unit ? " " + p.unit : "") + " on hand", p.where].filter(Boolean).join(" · "))),
      el("div", { class: "row-meta" }, state, el("div", { class: "row-buttons" },
        btn("Remove", "btn-ghost", () => act({ kind: "asset.part_remove", params: { asset_id: page.id, part: p.ref } })))));
  }
  async function addPart() {
    if (!page.parts.choices.length) { say("Add it to your inventory or the Workshop's materials first."); return; }
    const v = await form("A part " + page.name + " uses", [{ name: "part", label: "Part, material or item", type: "pick", options: ["parts"], required: true }],
      {}, { parts: page.parts.choices });
    if (v && v.part) act({ kind: "asset.part_add", params: { asset_id: page.id, part: v.part } });
  }

  // ------------------------------------------------------------ tabs
  const VIEWS = {
    // A greenhouse tank or bed (Zac, 2026-10-17): what grows here, its water, its harvests (grow.js).
    growing: () => window.MIAGrow.place(page.id),
    overview: () => [el("div", { class: "asset-overview" },
      el("div", { class: "span-all" }, card("Current tasks", page.tasks.length
        ? el("div", { class: "rows" }, page.tasks.slice(0, 4).map((r) => taskRow(r, true))) : el("p", { class: "dim" }, "No tasks yet."))),
      card("Related missions", page.missions.length ? el("div", { class: "rows" }, page.missions.slice(0, 3).map(missionRow))
        : el("p", { class: "dim" }, "No missions about it yet.")),
      card("Details", page.details.length || page.notes ? details() : el("p", { class: "dim" }, "Add its make, model and serial number with Edit.")),
      card("Documents", page.documents.length ? el("div", { class: "rows" }, page.documents.slice(0, 4).map(documentRow))
        : el("p", { class: "dim" }, "No documents yet.")), spentLately())],
    maintenance: () => [card("Maintenance", btn("Add task", "btn-amber", addTask),
      page.tasks.length ? el("div", { class: "rows" }, page.tasks.map((r) => taskRow(r))) : el("p", { class: "dim" }, "No tasks yet. Add one, like an oil change every 50 hours."))],
    missions: () => [card("Missions", page.missions.length ? el("div", { class: "rows" }, page.missions.map(missionRow))
      : el("div", {}, el("p", { class: "dim" }, "No missions about " + page.name + " yet."),
        btn("Ask MIA for one", "btn-amber", () => talk(true, "Add a mission for the " + page.name + ": ")))) ],
    documents: () => [card("Documents", uploader(),
      page.documents.length ? el("div", { class: "rows" }, page.documents.map(documentRow)) : el("p", { class: "dim" }, "Manuals, receipts, warranties: add them here, or send them to MIA's inbox."))],
    costs: () => {
      const c = page.costs;
      if (!c) return [card("Costs", el("p", { class: "dim" }, "Costs need Money on this MIA."))];
      return [card("Cost of owning it",
        el("div", { class: "money-figures" },
          figure("Bought for", fmt(c.purchase)), figure("Upkeep", fmt(c.upkeep)), figure("Total", fmt(c.total)),
          c.per_hour != null ? figure("Per hour (" + c.hours + " h)", fmt(c.per_hour)) : null),
        c.by_category.length ? el("div", { class: "rows" }, c.by_category.map((b) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, b.category)), el("div", { class: "row-meta" }, el("span", { class: "money-amount" }, fmt(b.amount))))))
          : el("p", { class: "dim" }, "Expenses tagged to it show up here (tell MIA: “the oil was for the mower”)."),
        c.for_builds.length ? el("p", { class: "dim" }, "Bought for: " + c.for_builds.join(", ")) : null)];
    },
    history: () => [card("History", page.history.length ? el("div", { class: "rows" }, page.history.map((h) =>
      el("div", { class: "row money-row" }, el("div", {}, el("div", { class: "row-title" }, h.summary),
        el("div", { class: "row-sub" }, new Date(h.at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }))))))
      : el("p", { class: "dim" }, "What happens to it will show up here."))],
    // The parts it uses (core/asset_parts.py): from your inventory, materials and parts bins, with what's on hand;
    // out or low in amber (needs you). Add A Part / Remove are asset.part_add / asset.part_remove (by voice too).
    parts: () => [card("Parts", btn("Add a part", "btn-amber", addPart),
      page.parts.items.length ? el("div", { class: "rows" }, page.parts.items.map(partRow))
        : el("p", { class: "dim" }, page.parts.choices.length ? "The filters, blades, belts and fluids it takes. Add them from your inventory, materials or parts."
          : "Add the filters, blades and fluids to your inventory (Toolbox) or the Workshop's materials first, then list them here."))],
  };
  // Needs You (the canvas): the first thing waiting as one focus card with a big Done (asking the meter reading
  // when the task is on a meter), and anything else waiting as rows under it.
  function needsYou() {
    const [first, ...rest] = page.attention;
    if (!first) return [];
    const how = [first.trigger === "calendar" ? (first.interval_days ? "Every " + first.interval_days + " days" : null)
      : (first.meter_interval ? "Every " + first.meter_interval + " " + (first.unit || "") : null),
      first.last_completed ? "last done " + first.last_completed : null, first.predicted].filter(Boolean).join(" · ");
    return [el("section", { class: "glass surface-focus asset-focus", "aria-label": "Needs you" },
      el("span", { class: "kind attention" }, "Needs You"),
      el("h2", {}, first.title + (first.due ? " · " + first.due.toLowerCase() : "")),
      how ? el("p", { class: "dim" }, how) : null,
      first.action ? el("button", { type: "button", class: "btn btn-big btn-green", onclick: () => done(first) },
        first.action.asks_meter ? "Done · Asks the " + (first.unit || "reading") : "Done") : null,
      rest.length ? el("div", { class: "rows" }, rest.map((r) => taskRow(r, true))) : null)];
  }
  function spentLately() {
    const c = page.costs;
    if (!c || !c.recent || !c.recent.length) return null;
    return card("Spent on it lately", el("div", { class: "rows" }, c.recent.map((r) => el("div", { class: "row money-row asset-spend" },
      el("span", { class: "asset-when" }, day(r.date)), el("span", { class: "row-title" }, r.what),
      el("span", { class: "money-amount" }, fmt(r.amount))))));
  }
  function day(iso) {
    if (!iso) return "";
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString(undefined, { month: "short", day: "2-digit", year: d.getFullYear() === new Date().getFullYear() ? undefined : "numeric" });
  }
  function figure(label, value) {
    return el("div", { class: "figure" }, el("span", { class: "figure-n" }, value), el("span", { class: "figure-t" }, label));
  }

  // Its photo (2026-11-07, Q-0014): under the title, from the household's own folder (/api/garage/asset/<id>/photo);
  // Add Photo or Change Photo takes one from the camera or the files. The earlier photo is kept on the PC.
  const photoInput = el("input", { type: "file", accept: "image/jpeg,image/png,image/webp", hidden: true, onchange: async () => {
    const file = photoInput.files[0];
    photoInput.value = "";
    if (!file) return;
    try { MIAShell.say("Saving the photo…"); MIAShell.say((await MIA.upload("/api/garage/asset/" + encodeURIComponent(page.id) + "/photo", file)).message); MIAShell.refresh(); }
    catch (e) { MIAShell.say(e.message); }
  } });
  function pickPhoto() { photoInput.click(); }
  function showPhoto() {
    let box = $("asset-photo");
    if (!box) {
      box = el("figure", { id: "asset-photo", class: "asset-photo" });
      document.querySelector(".asset-hero").after(box, photoInput);
    }
    box.hidden = !page.photo;
    if (!page.photo) { box.replaceChildren(); return; }
    MIA.image(page.photo).then((url) => { if (url) box.replaceChildren(el("img", { src: url, alt: page.name })); else box.hidden = true; });
  }

  // A reading tile's trend (core/web_equipment.trend: the Lab's chart points, from two readings on): a small line,
  // low and high under it, opening the full chart in the Lab.
  function spark(s) {
    if (!s.chart || !s.chart.points.length) return null;
    const NS = "http://www.w3.org/2000/svg", W = 120, H = 32;
    const pic = document.createElementNS(NS, "svg");
    pic.setAttribute("viewBox", "0 0 " + W + " " + H);
    pic.setAttribute("class", "stat-spark");
    pic.setAttribute("preserveAspectRatio", "none");
    pic.setAttribute("role", "img");
    pic.setAttribute("aria-label", s.title + " from " + s.chart.points[0].label + " to " + s.chart.points[s.chart.points.length - 1].label);
    const line = document.createElementNS(NS, "polyline");
    line.setAttribute("points", s.chart.points.map((p) => (p.x * W).toFixed(1) + "," + (H - 2 - p.y * (H - 4)).toFixed(1)).join(" "));
    pic.append(line);
    return el("a", { class: "stat-trend", href: "lab.html#" + encodeURIComponent(s.series), title: "Open the chart in the Lab" },
      pic, el("span", { class: "stat-range" }, s.chart.low + " – " + s.chart.high));
  }

  function draw() {
    document.body.dataset.app = page.scope;
    document.title = page.name + " — MIA";
    $("back").href = page.scope_page || "garage.html";
    $("back").textContent = "← " + page.scope_name;
    $("hero-icon").textContent = ICONS[page.category] || "🔧";
    if (window.MIAIcons) {
      MIAIcons.badge($("hero-icon"), document.body.dataset.app);  // the line icon (DEC-0023)
      const motif = document.querySelector(".plate-motif"), drawing = MIAIcons.svg(page.scope);
      if (motif && drawing) motif.replaceChildren(drawing);  // the plate's art is this asset's area, not the Garage's
    }
    $("hero-name").textContent = page.name;
    const bought = (page.details.find((d) => d.label === "Bought on") || {}).value;
    $("hero-sub").textContent = [page.category, bought ? "Bought " + String(bought).slice(0, 4) : null,
      page.details.filter((d) => d.label === "Make" || d.label === "Model").map((d) => d.value).join(" ")]
      .filter(Boolean).join(" · ");
    $("hero-buttons").replaceChildren(btn("Edit", "btn-ghost", editAsset), btn(page.photo ? "Change Photo" : "Add Photo", "btn-ghost", pickPhoto),
      btn("Delete", "btn-ghost danger", deleteAsset));
    showPhoto();
    $("stats").replaceChildren(...page.quick_stats.map((s) => el("div", { class: "glass stat-tile" },
      el("span", { class: "stat-t" }, s.title), el("span", { class: "stat-n" }, s.text),
      spark(s),
      btn("Log", "btn-ghost", () => s.task_id ? logTask(s.task_id, s.title) : logMeter(s.meter)))),
      // The canvas's strip (DEC-0113): its readings, then what upkeep cost this year and its condition.
      page.costs ? el("div", { class: "glass stat-tile" }, el("span", { class: "stat-t" }, "Spent this year"),
        el("span", { class: "stat-n" }, fmt(page.costs.this_year))) : null,
      page.condition ? el("div", { class: "glass stat-tile" }, el("span", { class: "stat-t" }, "Condition"),
        el("span", { class: "stat-n tone-" + page.condition.tone }, page.condition.percent + "%"),
        el("span", { class: "stat-sub" }, page.condition.label)) : null,
      ...(page.scope === "greenhouse" ? []  // its water readings live in Growing (grow.js)
        : [el("button", { type: "button", class: "glass stat-tile stat-add", onclick: () => logMeter("") }, "+ Log a reading")]));
    $("attention").replaceChildren(...needsYou());
    $("tabs").replaceChildren(...TABS.map(([t, label]) => el("button", { type: "button", role: "tab", "aria-selected": String(t === tab),
      onclick: () => { tab = t; history.replaceState(null, "", location.search + "#" + t); draw(); } }, label)));
    $("panel").replaceChildren(...VIEWS[tab]());
  }

  MIAShell.start(async () => {
    try {
      page = await MIA.asset(id);
      if (page.scope === "greenhouse" && window.MIAGrow) {
        await window.MIAGrow.load();
        if (TABS[0][0] !== "growing") TABS = [["growing", "Growing"], ...TABS];
      }
      if (!TABS.some(([t]) => t === tab)) tab = TABS[0][0];
    }
    catch (e) {
      $("hero-name").textContent = e.status === 404 ? "This isn't here anymore" : "Couldn't open it";
      $("panel").replaceChildren(el("p", { class: "dim" }, e.message));
      return;
    }
    draw();
  });
})();
