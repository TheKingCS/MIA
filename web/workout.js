/*
 * workout.js — the Workout screen (claude, 2026-10-06, DEC-0017/0018).
 * Renders MIA.workout() (core/web_screens.py): log a session right on the
 * page (an exercise, reps, sets, weight, how long, notes; or a whole
 * template), the latest entry, today's daily mission and streak, exercises
 * with personal records, templates, history and progress. Every change is a
 * workout action (core/workout_actions.py). Formatting only here.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["log", "Log Session"], ["exercises", "Exercises"], ["templates", "Templates"], ["history", "History"],
    ["progress", "Progress"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "log";
  let byTemplate = false;
  let draft = {};  // what's typed in the log form survives a live refresh

  const btn = (label, cls, onclick, type) => el("button", { type: type || "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }) : "";
  const lists = () => ({ exercises: page.exercises.map((e) => ({ id: e.id, name: e.name })),
    templates: page.templates.map((t) => ({ id: t.id, name: t.name })) });
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);

  async function add(key, title) {
    const v = await form(title, page.forms[key].fields, {});
    if (v) act({ kind: key + ".add", params: v });
  }
  async function edit(key, row) {
    const spec = page.forms[key];
    const v = await form("Edit " + spec.noun, spec.fields, row.values);
    if (v) act({ kind: key + ".edit", params: Object.assign({ [spec.id_param]: row.id }, v) });
  }
  const del = (key, row) => act({ kind: key + ".delete", params: { [page.forms[key].id_param]: row.id } });
  async function addToTemplate(t) {
    const v = await form("Add to " + t.name, page.forms.template_exercise.fields, {}, lists());
    if (v) act({ kind: "workout_template.exercise_add", params: Object.assign({ template_id: t.id }, v) });
  }

  // ------------------------------------------------------------ the inline log form (the concept's)
  function input(f) {
    const id = "log-" + f.name;
    let node;
    if (f.type === "pick") {
      node = el("select", { id, name: f.name }, el("option", { value: "" }, f.options[0] === "exercises" ? "Pick an exercise" : "Pick a template"),
        lists()[f.options[0]].map((x) => el("option", { value: x.id }, x.name)));
    } else if (f.type === "textarea") {
      node = el("textarea", { id, name: f.name, rows: "2", placeholder: "How did it feel?" });
    } else {
      const numeric = f.type !== "date";
      node = el("input", { id, name: f.name, type: numeric ? "number" : "date", min: numeric ? "0" : null,
        step: f.type === "int" ? "1" : numeric ? "any" : null, inputmode: numeric ? "decimal" : null });
      if (f.type === "int" && f.name === "sets") node.value = "1";
    }
    if (draft[f.name] != null) node.value = draft[f.name];
    node.addEventListener("input", () => { draft[f.name] = node.value; });
    return el("label", { class: "form-row log-" + f.name, for: id }, el("span", {}, f.label), node);
  }

  function logCard() {
    const spec = byTemplate ? page.forms.log_template : page.forms.log;
    const formNode = el("form", { class: "log-form", onsubmit: async (e) => {
      e.preventDefault();
      const params = {};
      new FormData(formNode).forEach((v, k) => { if (v !== "") params[k] = v; });
      const done = await act({ kind: "workout.log", params });
      if (done) { draft = {}; formNode.reset(); }
    } }, spec.fields.map(input),
    el("div", { class: "row-buttons" }, btn("Save session", "btn-green", null, "submit")));
    return section("Log session",
      el("div", { class: "ptabs mini", role: "tablist", "aria-label": "Log by" },
        [[false, "One exercise"], [true, "A template"]].map(([v, l]) => el("button", { type: "button", role: "tab",
          "aria-selected": String(byTemplate === v), disabled: v && !page.templates.length ? true : null,
          onclick: () => { byTemplate = v; draft = {}; draw(); } }, l))),
      page.exercises.length ? formNode
        : el("p", { class: "empty" }, el("strong", {}, "Add an exercise first."), btn("Add exercise", "btn-amber", () => add("exercise", "Add an exercise"))));
  }

  function latestCard() {
    const s = page.latest;
    return section("Latest entry", null, s
      ? el("div", { class: "latest" }, el("div", { class: "row-title" }, s.summary),
        el("div", { class: "row-sub" }, [day(s.date), s.minutes ? s.minutes + " min" : null].filter(Boolean).join(" · ")),
        s.notes ? el("p", { class: "dim" }, "“" + s.notes + "”") : null)
      : el("p", { class: "dim" }, "Nothing logged yet."));
  }

  function missionCard() {
    const list = page.daily_missions;
    if (!list.length) return null;
    return section("Daily mission", null, list.map((m) => {
      const pct = Math.min(100, Math.round((m.progress / m.target) * 100));
      return el("div", { class: "daily-mission" },
        el("div", { class: "row-title" }, (m.done ? "✓ " : "") + m.name),
        el("div", { class: "bar", role: "progressbar", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100" },
          el("div", { class: "bar-fill", style: "width:" + pct + "%" })),
        el("div", { class: "row-sub" }, m.progress + " / " + m.target + (m.streak ? " · 🔥 " + m.streak + "-day streak" : "")));
    }));
  }

  function sessionRow(s) {
    return el("div", { class: "row money-row" },
      el("div", {}, el("div", { class: "row-title" }, s.template || s.summary),
        el("div", { class: "row-sub" }, [day(s.date), s.template && s.summary !== s.template ? s.summary : null, s.minutes ? s.minutes + " min" : null, s.notes]
          .filter(Boolean).join(" · "))),
      buttons(btn("Remove", "btn-ghost", () => act({ kind: "workout.delete", params: { session_id: s.id } }))));
  }

  function spark(points) {
    if (points.length < 2) return null;
    const ws = points.map((p) => p[1]);
    const max = Math.max(...ws) || 1, min = Math.min(...ws);
    const span = max - min || 1;
    const d = points.map((p, i) => (i ? "L" : "M") + (i * 100 / (points.length - 1)).toFixed(1) + " " + (36 - ((p[1] - min) / span) * 32).toFixed(1)).join(" ");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 100 40");
    svg.setAttribute("class", "spark");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    svg.append(path);
    return svg;
  }

  const views = {
    log: () => [el("div", { class: "two-up" }, logCard(), el("div", { class: "stack" }, latestCard(), missionCard())),
      section("Recent history", null, page.sessions.length ? el("div", { class: "rows" }, page.sessions.slice(0, 5).map(sessionRow))
        : el("p", { class: "dim" }, "Your sessions show up here."))],
    exercises: () => [section("Exercises", buttons(btn("Add exercise", "btn-amber", () => add("exercise", "Add an exercise"))),
      page.exercises.length ? el("div", { class: "rows" }, page.exercises.map((e) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, e.name),
          el("div", { class: "row-sub" }, [e.category, e.equipment, e.pr ? "Best: " + (e.pr.weight ? e.pr.weight + " × " : "") + e.pr.reps + " reps" : null]
            .filter(Boolean).join(" · "))),
        buttons(btn("Edit", "btn-ghost", () => edit("exercise", e)), btn("Delete", "btn-ghost", () => del("exercise", e))))))
        : el("p", { class: "dim" }, "No exercises yet."))],
    templates: () => [section("Templates", buttons(btn("Add template", "btn-amber", () => add("workout_template", "Add a template"))),
      page.templates.length ? el("div", { class: "asset-grid" }, page.templates.map((t) => el("article", { class: "glass asset-card template-card" },
        el("div", { class: "asset-head" }, el("h3", {}, t.name)),
        t.notes ? el("p", { class: "dim" }, t.notes) : null,
        el("ul", { class: "asset-tasks" }, t.exercises.length ? t.exercises.map((x) => el("li", {},
          el("span", {}, x.name + ": " + x.sets + " × " + x.reps + (x.weight ? " at " + x.weight : "")),
          el("button", { type: "button", class: "btn btn-ghost btn-x", "aria-label": "Take " + x.name + " out",
            onclick: () => act({ kind: "workout_template.exercise_remove", params: { template_id: t.id, index: x.index } }) }, "×")))
          : el("li", { class: "dim" }, "No exercises yet")),
        buttons(btn("Add exercise", "btn-ghost", () => addToTemplate(t)),
          t.exercises.length ? btn("Log it", "btn-green", () => act({ kind: "workout.log", params: { template_id: t.id } })) : null,
          btn("Edit", "btn-ghost", () => edit("workout_template", t)), btn("Delete", "btn-ghost", () => del("workout_template", t))))))
        : el("p", { class: "dim" }, "A template is a routine you repeat, like “Upper body”."))],
    history: () => [section("History", null, page.sessions.length ? el("div", { class: "rows" }, page.sessions.map(sessionRow))
      : el("p", { class: "dim" }, "No sessions yet."))],
    progress: () => [section("Progress", null, page.exercises.some((e) => e.pr)
      ? el("div", { class: "asset-grid" }, page.exercises.filter((e) => e.pr).map((e) => el("article", { class: "glass asset-card" },
        el("div", { class: "asset-head" }, el("h3", {}, e.name), el("span", { class: "chip chip-ok" }, "PR")),
        el("p", {}, (e.pr.weight ? e.pr.weight + " × " : "") + e.pr.reps + " reps", el("span", { class: "dim" }, " · " + day(e.pr.date))),
        spark(e.progress))))
      : el("p", { class: "dim" }, "Log a few sessions and your personal records and progress show up here."))],
  };

  function draw() {
    const s = page.stats;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, s.this_week), el("span", { class: "t" }, "This week")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, Math.round(s.minutes_this_week)), el("span", { class: "t" }, "Minutes")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, (s.streak ? "🔥" : "") + s.streak), el("span", { class: "t" }, "Day streak")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) =>
      el("button", { type: "button", role: "tab", "aria-selected": String(id === tab), onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...views[tab]().filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.workout();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "Workouts aren't set up on this MIA."), ""));
      return;
    }
    if (byTemplate && !page.templates.length) byTemplate = false;
    draw();
  });
})();
