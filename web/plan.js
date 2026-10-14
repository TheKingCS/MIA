/*
 * plan.js — My plan (claude, 2026-10-14, DEC-0020, Muse's H-0028): one
 * screen, reached from both Kitchen and Workout. Goals, the training week
 * (which days, and what each training day is), skills to practice, meals
 * and preferences, milestones. Renders MIA.fitness() (plan, plan_text);
 * every save is a fitness.plan action, which checks and shapes what was
 * typed (core/fitness_actions.py). Formatting only here.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  let fit = null;
  let recipes = [];
  let draftDays = null;     // training days being picked, before Save
  let draftLunches = null;  // lunch rotation being picked, before Save

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const fact = (label, value) => el("div", { class: "acct-fact" }, el("span", { class: "dim" }, label), el("strong", {}, value == null || value === "" ? "—" : value));
  const save = (changes) => act({ kind: "fitness.plan", params: { changes } });
  const list = (xs) => (xs || []).join(", ");

  // Door: which app this was opened from colours the page and the way back.
  const from = new URLSearchParams(location.search).get("from") || "";
  if (/^(kitchen|workout)\.html(#[a-z-]+)?$/.test(from)) {
    const app = from.split(".")[0];
    document.body.dataset.app = app;
    document.body.className = "mod-" + app;
    $("back").href = from;
    $("back").textContent = "← " + (app === "kitchen" ? "Kitchen" : "Workout");
  }

  // ------------------------------------------------------------ goals
  async function editGoals() {
    const t = fit.plan.targets;
    const fields = [
      { name: "protein_g", label: "Protein a day (g)", type: "number" },
      { name: "calories", label: "Calories a day", type: "number" },
      { name: "workouts_per_week", label: "Workouts a week", type: "number" },
    ];
    if (!fit.child) {
      fields.push({ name: "target_weight", label: "Goal weight" + (fit.plan.units ? " (" + fit.plan.units + ")" : ""), type: "number" },
        { name: "target_date", label: "By", type: "date" },
        { name: "weigh_in_days", label: "Weigh-in days (e.g. Mon, Thu)", type: "text" },
        { name: "units", label: "Units", type: "choice", options: ["lb", "kg"], default: fit.plan.units || "lb" });
    }
    const v = await form("Your goals", fields, Object.assign({}, t, { weigh_in_days: list(t.weigh_in_days), units: fit.plan.units }));
    if (!v) return;
    const units = v.units;
    delete v.units;
    save(Object.assign({ targets: v }, units ? { units } : {}));
  }
  function goals() {
    const t = fit.plan.targets, u = fit.plan.units;
    return section("Goals", btn("Edit", "btn-ghost", editGoals),
      fact("Protein a day", t.protein_g != null ? t.protein_g + " g" : null),
      fact("Calories a day", t.calories != null ? Number(t.calories).toLocaleString() : null),
      fact("Workouts a week", t.workouts_per_week),
      fit.child ? null : fact("Goal weight", t.target_weight != null ? t.target_weight + " " + u + (t.target_date ? " by " + t.target_date : "") : null),
      fit.child ? null : fact("Weigh-in days", list(t.weigh_in_days)));
  }

  // ------------------------------------------------------------ training
  async function editDay(index) {
    const rotation = fit.plan_text.rotation.slice();
    const current = index == null ? { name: "", exercises: "" } : rotation[index];
    const v = await form(index == null ? "Add a training day" : "Edit " + current.name, [
      { name: "name", label: "Name (e.g. Push, Pull, Legs)", type: "text", required: true },
      { name: "exercises", label: "Exercises, one a line: Dips 3x8, L-sit 3x20s, Plank 60s", type: "textarea" }], current);
    if (!v) return;
    if (index == null) rotation.push(v); else rotation[index] = v;
    save({ training: { rotation } });
  }
  function moveDay(index, by) {
    const rotation = fit.plan_text.rotation.slice();
    const [day] = rotation.splice(index, 1);
    rotation.splice(index + by, 0, day);
    save({ training: { rotation } });
  }
  function removeDay(index) {
    const rotation = fit.plan_text.rotation.filter((_, i) => i !== index);
    save({ training: { rotation } });
  }
  function training() {
    const saved = fit.plan.training.days || [];
    const picked = draftDays || saved;
    const changed = draftDays && draftDays.join() !== saved.join();
    const rotation = fit.plan.training.rotation || [];
    return section("Training week", btn("Add a training day", "btn-amber", () => editDay(null)),
      el("p", { class: "dim" }, "Which days you train. Each training day does the next one in your rotation, in order."),
      el("div", { class: "chip-row day-picks" }, DAYS.map((d) => el("label", { class: "setup-chip" },
        el("input", { type: "checkbox", checked: picked.includes(d) || null,
          onchange: (e) => { const now = new Set(picked); e.target.checked ? now.add(d) : now.delete(d); draftDays = DAYS.filter((x) => now.has(x)); draw(); } }), d))),
      changed ? buttons(btn("Save days", "btn-green", async () => { if (await save({ training: { days: draftDays } })) draftDays = null; }),
        btn("Cancel", "btn-ghost", () => { draftDays = null; draw(); })) : null,
      rotation.length ? el("div", { class: "asset-grid plan-grid" }, rotation.map((day, i) => el("article", { class: "glass asset-card" },
        el("div", { class: "asset-head" }, el("h3", {}, (i + 1) + ". " + day.name)),
        (day.exercises || []).length ? el("ul", { class: "plan-list" }, fit.plan_text.rotation[i].exercises.split("\n").map((l) => el("li", {}, l)))
          : el("p", { class: "dim" }, "No exercises yet."),
        buttons(btn("Edit", "btn-ghost", () => editDay(i)),
          i ? btn("↑", "btn-ghost", () => moveDay(i, -1)) : null,
          i < rotation.length - 1 ? btn("↓", "btn-ghost", () => moveDay(i, 1)) : null,
          btn("Remove", "btn-ghost", () => removeDay(i))))))
        : el("p", { class: "empty" }, el("strong", {}, "No training days yet."), "Add one, like “Push: Dips 3x8, Push-ups 3x15”."));
  }

  // ------------------------------------------------------------ skills
  async function editSkill(index) {
    const skills = fit.plan_text.skills.slice();
    const current = index == null ? { skill: "", daily_minutes: "", practice: "", steps: "" } : skills[index];
    const v = await form(index == null ? "Add a skill" : "Edit " + current.skill, [
      { name: "skill", label: "Skill (e.g. Handstand)", type: "text", required: true },
      { name: "daily_minutes", label: "Minutes a day", type: "number" },
      { name: "practice", label: "Drills (comma between)", type: "text" },
      { name: "steps", label: "Steps, easiest first, one a line: Wall hold 60s, Tuck 10 reps", type: "textarea" }], current);
    if (!v) return;
    if (index == null) skills.push(v); else skills[index] = v;
    save({ skill_tree: skills });
  }
  function skills() {
    const tree = fit.plan.skill_tree || [];
    return section("Skills", btn("Add a skill", "btn-amber", () => editSkill(null)),
      tree.length ? el("div", { class: "asset-grid plan-grid" }, tree.map((k, i) => el("article", { class: "glass asset-card" },
        el("div", { class: "asset-head" }, el("h3", {}, k.skill), k.daily_minutes ? el("span", { class: "chip" }, k.daily_minutes + " min a day") : null),
        (k.practice || []).length ? el("p", { class: "dim" }, k.practice.join(" · ")) : null,
        (k.steps || []).length ? el("ol", { class: "plan-list" }, fit.plan_text.skills[i].steps.split("\n").map((l) => el("li", {}, l))) : null,
        buttons(btn("Edit", "btn-ghost", () => editSkill(i)),
          btn("Remove", "btn-ghost", () => save({ skill_tree: fit.plan_text.skills.filter((_, j) => j !== i) }))))))
        : el("p", { class: "dim" }, "Something you practise a little every day, like a handstand. MIA times it and celebrates each new best."));
  }

  // ------------------------------------------------------------ meals
  async function editMeals() {
    const m = fit.plan.meals, prefs = m.preferences;
    const v = await form("Meals", [
      { name: "packed_lunch", label: "Pack a lunch on work days", type: "choice", options: ["no", "yes"] },
      { name: "prep_day", label: "Meal prep day", type: "choice", options: ["", ...DAYS] },
      { name: "diet", label: "Diet (optional, e.g. high protein)", type: "text" },
      { name: "dislikes", label: "Foods you don't eat (comma between)", type: "text" },
      { name: "allergies", label: "Allergies (comma between)", type: "text" }],
      { packed_lunch: m.packed_lunch ? "yes" : "no", prep_day: m.prep_day, diet: prefs.diet, dislikes: list(prefs.dislikes), allergies: list(prefs.allergies) });
    if (!v) return;
    save({ meals: { packed_lunch: v.packed_lunch === "yes", prep_day: v.prep_day,
      preferences: { diet: v.diet, dislikes: v.dislikes, allergies: v.allergies } } });
  }
  function meals() {
    const m = fit.plan.meals, prefs = m.preferences;
    const saved = m.lunch_rotation || [];
    const picked = draftLunches || saved;
    const changed = draftLunches && draftLunches.join() !== saved.join();
    return section("Meals", btn("Edit", "btn-ghost", editMeals),
      fact("Packed lunch", m.packed_lunch ? "Yes" : "No"),
      fact("Meal prep day", m.prep_day),
      fact("Diet", prefs.diet),
      fact("Don't eat", list(prefs.dislikes)),
      fact("Allergies", list(prefs.allergies)),
      el("h3", { class: "mini-h" }, "Lunch rotation"),
      el("p", { class: "dim" }, "Lunches MIA plans in turn when it fills your week."),
      recipes.length ? el("div", { class: "chip-row" }, recipes.map((r) => el("label", { class: "setup-chip" },
        el("input", { type: "checkbox", checked: picked.includes(r.id) || null,
          onchange: (e) => { const now = picked.filter((x) => x !== r.id); if (e.target.checked) now.push(r.id); draftLunches = now; draw(); } }), r.name)))
        : el("p", { class: "dim" }, "Add recipes in the Kitchen to pick from."),
      changed ? buttons(btn("Save lunches", "btn-green", async () => { if (await save({ meals: { lunch_rotation: draftLunches } })) draftLunches = null; }),
        btn("Cancel", "btn-ghost", () => { draftLunches = null; draw(); })) : null);
  }

  // ------------------------------------------------------------ milestones
  async function addMilestone() {
    const v = await form("Add a milestone", [{ name: "name", label: "What (e.g. 60 s freestanding handstand)", type: "text", required: true }]);
    if (v) save({ milestones: (fit.plan.milestones || []).concat([{ name: v.name }]) });
  }
  function milestones() {
    const all = fit.plan.milestones || [];
    return section("Milestones", btn("Add", "btn-amber", addMilestone),
      all.length ? el("div", { class: "rows" }, all.map((m) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, (m.done_on ? "🏆 " : "") + m.name), m.done_on ? el("div", { class: "row-sub" }, "Reached " + m.done_on) : null),
        buttons(btn("Remove", "btn-ghost", () => save({ milestones: all.filter((x) => x.id !== m.id) }))))))
        : el("p", { class: "dim" }, "The big ones you're working toward. Mark them reached on Workout's Progress tab."));
  }

  function draw() {
    $("panel").replaceChildren(el("div", { class: "two-up" }, el("div", { class: "stack" }, goals(), meals(), milestones()),
      el("div", { class: "stack" }, training(), skills())));
  }

  MIAShell.start(async () => {
    const [f, k] = await Promise.all([MIA.fitness(), MIA.kitchen().catch(() => null)]);
    if (!f.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "Plans aren't set up on this MIA."), ""));
      return;
    }
    fit = f;
    recipes = k && k.available ? k.recipes.filter((r) => !r.locked).map((r) => ({ id: r.id, name: r.name })) : [];
    draw();
  });
})();
