/*
 * projects.js — Projects (claude, 2026-11-07; DEC-0125: projects and their tasks were voice-only).
 * Renders MIA.projects() (core/web_projects.py): underway first, each with its status, due date, budget, spent and
 * left (a meter, amber when over), what the money went on, tools bought, the reason it serves, and its tasks to tick.
 * Every change is an action (project.add/edit/delete/budget, task.add/done/reopen/delete), as "add a task to the
 * greenhouse: frame the door" does by voice. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  let open = decodeURIComponent(location.hash.slice(1)) || null;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const STATUS = { Active: "chip-soon", Planning: "", "On Hold": "", Complete: "chip-ok" };

  async function addProject() {
    const v = await form("Start A Project", page.forms.project.fields, {});
    if (v) act({ kind: "project.add", params: v });
  }
  async function editProject(p) {
    const v = await form("Edit " + p.name, page.forms.project.fields, p.values);
    if (v) act({ kind: "project.edit", params: Object.assign({ project_id: p.id }, v) });
  }
  async function setBudget(p) {
    const v = await form("Budget For " + p.name, [{ name: "budget", label: "How much (0 for none)", type: "money", default: p.budget || 0 }], { budget: p.budget || "" });
    if (v) act({ kind: "project.budget", params: { project_id: p.id, budget: v.budget || 0 } });
  }
  async function addTask(p) {
    const v = await form("A Task For " + p.name, page.forms.task.fields, {});
    if (v) act({ kind: "task.add", params: Object.assign({ project_id: p.id }, v) });
  }

  function money(p) {
    if (!p.budget_text && !p.spent_text) return el("p", { class: "dim" }, "No budget or spending yet.");
    const pct = p.percent == null ? null : Math.min(100, p.percent);
    return el("div", { class: "pj-money" },
      el("div", { class: "pj-figures" },
        el("div", {}, el("span", { class: "pw-label" }, "Spent"), el("strong", {}, p.spent_text || "—")),
        el("div", {}, el("span", { class: "pw-label" }, "Budget"), el("strong", {}, p.budget_text || "—")),
        el("div", {}, el("span", { class: "pw-label" }, p.over ? "Over" : "Left"), el("strong", { class: p.over ? "pj-over" : "" }, (p.left_text || "—").replace("-", "")))),
      pct != null ? el("div", { class: "meter" + (p.over ? " meter-attention" : "") }, el("div", { class: "meter-fill", style: "width:" + pct + "%" })) : null,
      p.by_category.length ? el("p", { class: "dim" }, "On " + p.by_category.map((c) => c.kind.toLowerCase() + " " + c.text).join(", ")) : null,
      p.tools.length ? el("p", { class: "dim" }, "Tools bought: " + p.tools.join(", ")) : null);
  }

  function task(t) {
    return el("li", { class: t.done ? "done" : "" },
      el("button", { type: "button", class: "tick" + (t.done ? " on" : ""), "aria-pressed": String(t.done),
        "aria-label": (t.done ? "Not done: " : "Done: ") + t.title,
        onclick: () => act({ kind: t.done ? "task.reopen" : "task.done", params: { task_id: t.id } }, { quick: true }) }, t.done ? "✓" : ""),
      el("span", {}, t.title, t.due && !t.done ? el("span", { class: "dim" }, " · by " + day(t.due)) : null),
      el("button", { type: "button", class: "btn btn-ghost btn-small", "aria-label": "Take off " + t.title,
        onclick: () => act({ kind: "task.delete", params: { task_id: t.id } }) }, "✕"));
  }

  function card(p) {
    const isOpen = open === p.id;
    const head = el("button", { type: "button", class: "pj-head", "aria-expanded": String(isOpen),
      onclick: () => { open = isOpen ? null : p.id; history.replaceState(null, "", isOpen ? location.pathname : "#" + encodeURIComponent(p.id)); draw(); } },
      el("span", { class: "pj-name" }, p.name),
      el("span", { class: "dim" }, [p.tasks_total ? p.tasks_done + "/" + p.tasks_total + " tasks" : null, p.due ? "due " + day(p.due) : null].filter(Boolean).join(" · ")),
      el("span", { class: "chip " + (STATUS[p.status] || "") }, p.status));
    return el("article", { class: "glass pj-card" + (p.status === "Complete" ? " finished" : "") }, head,
      isOpen ? [
        p.description ? el("p", { class: "trip-notes" }, p.description) : null,
        p.why ? el("p", { class: "dim" }, "For: ", el("a", { href: "why.html" }, p.why)) : null,
        money(p),
        el("h4", {}, "Tasks" + (p.tasks_total ? " " + p.tasks_done + "/" + p.tasks_total : "")),
        p.tasks.length ? el("ul", { class: "gear-list pj-tasks" }, p.tasks.map(task)) : el("p", { class: "dim" }, "No tasks yet."),
        el("div", { class: "row-buttons" },
          btn("Add A Task", "btn-amber", () => addTask(p)),
          btn(p.budget ? "Budget" : "Set A Budget", "btn-ghost", () => setBudget(p)),
          p.status !== "Complete" ? btn("Finished", "btn-green", () => act({ kind: "project.edit", params: Object.assign({ project_id: p.id }, p.values, { status: "Complete" }) })) : null,
          btn("Edit", "btn-ghost", () => editProject(p)),
          btn("Delete", "btn-ghost", () => act({ kind: "project.delete", params: { project_id: p.id } })))] : null);
  }

  function draw() {
    const c = page.counts;
    $("pj-sub").textContent = page.projects.length ? c.underway + " underway" + (c.open_tasks ? " · " + c.open_tasks + " open tasks" : "") : "Nothing here yet.";
    if (open && !page.projects.some((p) => p.id === open)) open = null;
    if (!open && page.projects.length && page.projects[0].status !== "Complete") open = page.projects[0].id;
    $("panel").replaceChildren(
      ...(page.projects.length ? page.projects.map(card)
        : [el("p", { class: "empty" }, "A project is something you're building or getting done: the greenhouse, the fence, a new shed. Give it tasks and a budget, and tag spending to it in Money.")]),
      el("p", { class: "dim" }, "Or say “add a task to the greenhouse: frame the door” or “how much have I spent on the greenhouse?”"),
      el("div", { class: "row-buttons" }, btn("Start A Project", "btn-amber", addProject)));
  }

  MIAShell.start(async () => {
    page = await MIA.projects();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Projects aren't on this MIA.")); return; }
    draw();
  }, { refreshOnChange: true });
})();
