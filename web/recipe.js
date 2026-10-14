/*
 * recipe.js — one recipe, opened from a meal or recipe card (claude,
 * 2026-10-14, Zac's idea). Renders MIA.recipe(id) (core/web_screens.
 * recipe_page): nutrition per serving, each ingredient with whether the
 * house has it, the steps (tick them off while cooking; that stays on
 * this screen), when it's planned, and the buttons. Every change is an
 * action through MIAShell.act. Formatting only here.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const query = new URLSearchParams(location.search);
  const id = query.get("id") || "";
  let page = null;
  const cooked = new Set();  // steps ticked while cooking (this visit only)
  let showAll = false;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const num = (v, unit) => v == null ? "—" : Math.round(v).toLocaleString() + (unit || "");
  const today = () => page.as_of;
  const dayName = (iso) => iso === today() ? "Today"
    : new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const amount = (i) => [i.quantity ? Number(i.quantity).toLocaleString() : "", i.unit].filter(Boolean).join(" ");

  // ------------------------------------------------------------ the buttons
  async function schedule() {
    const v = await form("Schedule " + page.name, [
      { name: "date", label: "Day", type: "date", required: true, default: today() },
      { name: "meal", label: "Meal", type: "choice", options: page.meals, default: page.default_meal },
      { name: "servings", label: "Servings", type: "number", required: true, default: 1 },
    ]);
    if (v) act({ kind: "meal.plan", params: Object.assign({ recipe_id: page.id }, v) });
  }
  const toList = () => act({ kind: "grocery.from_recipe", params: { recipe_id: page.id } });
  const ate = (s) => act({ kind: "fitness.food", params: { meal: s.meal, recipe_id: page.id, servings: s.servings,
    date: s.date, planned_id: s.date + ":" + s.meal } });
  const unschedule = (s) => act({ kind: "meal.plan", params: { date: s.date, meal: s.meal, recipe_id: "" } });
  async function logMeal() {
    const v = await form("I made " + page.name, page.forms.meal.fields, {});
    if (v) act({ kind: "meal.log", params: Object.assign({ recipe_id: page.id }, v) });
  }
  async function edit() {
    const v = await form("Edit recipe", page.forms.recipe.fields, page.values);
    if (v) act({ kind: "recipe.edit", params: Object.assign({ [page.forms.recipe.id_param]: page.id }, v) });
  }
  async function ingredients() {
    const v = await form(page.name + ": ingredients", page.forms.ingredients.fields, { ingredients: page.ingredients_text });
    if (v) act({ kind: "recipe.ingredients", params: { recipe_id: page.id, ingredients: v.ingredients } });
  }
  async function remove() {
    const done = await act({ kind: "recipe.delete", params: { [page.forms.recipe.id_param]: page.id } });
    if (done) location.href = $("back").href;
  }

  // ------------------------------------------------------------ pieces
  function top() {
    const n = page.nutrition;
    const minutes = page.prep_minutes + page.cook_minutes;
    const chips = [page.category, minutes ? minutes + " min" : null,
      page.servings ? page.servings + " serving" + (page.servings === 1 ? "" : "s") : null,
      page.times_made ? "made " + page.times_made + "×" : null].filter(Boolean);
    const buyCount = page.to_buy.length;
    return el("section", { class: "glass money-section recipe-top" },
      el("div", { class: "chip-row" }, chips.map((c) => el("span", { class: "chip" }, c)), page.favorite ? el("span", { class: "chip chip-ok" }, "★ Favorite") : null),
      page.locked ? el("p", { class: "locked-note" }, "🔒 Locked" + (page.unlocked_by_mission ? ": finish “" + page.unlocked_by_mission + "” to unlock it." : ".")) : null,
      el("div", { class: "recipe-macros" },
        [["kcal", "Calories", ""], ["protein_g", "Protein", " g"], ["carbs_g", "Carbs", " g"], ["fat_g", "Fat", " g"]].map(([k, label, unit]) =>
          el("div", { class: "macro" + (k === "protein_g" ? " macro-protein" : "") }, el("strong", {}, num(n[k], unit)), el("small", {}, label)))),
      el("div", { class: "recipe-cta" },
        page.can_schedule ? btn("📅 Schedule meal", "btn-green", schedule) : null,
        buyCount ? btn("🛒 Add to grocery list (" + buyCount + ")", "btn-amber", toList)
          : el("span", { class: "chip chip-ok" }, page.ingredients.length ? "✓ You have everything (or it's on the list)" : "No ingredients yet")));
  }

  function nutrition() {
    const n = page.nutrition;
    const where = { typed: "From your recipe.", computed: "Worked out from the ingredients (USDA food data).",
      mixed: "Your numbers, the rest worked out from the ingredients.", unknown: "MIA can't work these out yet." }[n.source];
    const rows = [["Calories", n.kcal, ""], ["Protein", n.protein_g, " g"], ["Carbs", n.carbs_g, " g"], ["Fat", n.fat_g, " g"],
      ["Fiber", n.fiber_g, " g"], ["Sugar", n.sugar_g, " g"], ["Sodium", n.sodium_mg, " mg"]];
    return section("Nutrition, per serving", null,
      el("div", {}, rows.map(([label, v, unit]) => el("div", { class: "acct-fact" }, el("span", { class: "dim" }, label), el("strong", {}, num(v, unit))))),
      el("p", { class: "dim" }, where + (n.not_found.length ? " Not in the food table: " + n.not_found.join(", ") + " (type the numbers into the recipe to fill the gaps)." : "")));
  }

  function ingredientList() {
    const label = { have: ["✓ Have it", "chip-ok"], on_list: ["On the list", "chip"], to_buy: ["To buy", "chip-soon"] };
    return section("Ingredients", btn("Edit", "btn-ghost", ingredients),
      page.ingredients.length ? el("div", { class: "rows" }, page.ingredients.map((i) =>
        el("div", { class: "row money-row ingredient-" + i.status },
          el("div", {}, el("div", { class: "row-title" }, i.name), amount(i) ? el("div", { class: "row-sub" }, amount(i)) : null),
          el("span", { class: "chip " + label[i.status][1] }, label[i.status][0]))))
        : el("p", { class: "dim" }, "No ingredients yet. Add them, one per line, and MIA works out the nutrition and the shopping."));
  }

  function steps() {
    if (!page.steps.length) return section("Steps", null, el("p", { class: "dim" }, "No steps written down yet. Edit the recipe to add them."));
    return section("Steps", cooked.size ? el("span", { class: "dim" }, cooked.size + " of " + page.steps.length + " done") : null,
      el("ol", { class: "recipe-step-list" }, page.steps.map((text, i) =>
        el("li", { class: cooked.has(i) ? "done" : "" },
          el("button", { type: "button", class: "step-tick", "aria-pressed": String(cooked.has(i)), "aria-label": "Step " + (i + 1) + " done",
            onclick: () => { cooked.has(i) ? cooked.delete(i) : cooked.add(i); draw(); } }, String(i + 1)),
          el("span", {}, text)))));
  }

  function planned() {
    if (!page.can_schedule) return null;
    return section("Planned", btn("Schedule", "btn-ghost", schedule),
      page.scheduled.length ? el("div", { class: "rows" }, (showAll ? page.scheduled : page.scheduled.slice(0, 3)).map((s) =>
        el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, dayName(s.date) + " · " + cap(s.meal)),
            el("div", { class: "row-sub" }, s.servings + " serving" + (s.servings === 1 ? "" : "s") + (s.eaten ? " · eaten ✓" : ""))),
          el("div", { class: "row-buttons" },
            s.date === today() && !s.eaten ? btn("Ate it", "btn-green", () => ate(s)) : null,
            s.eaten ? null : btn("Remove", "btn-ghost", () => unschedule(s))))))
        : el("p", { class: "dim" }, "Not planned in the next two weeks."),
      page.scheduled.length > 3 && !showAll ? btn("Show all " + page.scheduled.length, "btn-ghost", () => { showAll = true; draw(); }) : null);
  }

  function more() {
    return el("div", { class: "row-buttons recipe-more" },
      page.locked ? null : btn("I made this", "btn-ghost", logMeal),
      btn(page.favorite ? "Unfavorite" : "★ Favorite", "btn-ghost", () => act({ kind: "recipe.favorite", params: { recipe_id: page.id, favorite: !page.favorite } })),
      btn("Edit recipe", "btn-ghost", edit),
      btn("Delete", "btn-ghost", remove));
  }

  function draw() {
    document.title = page.name + " — MIA";
    $("hero-name").textContent = page.name;
    $("hero-tagline").textContent = page.notes || page.source || "";
    $("panel").replaceChildren(top(), el("div", { class: "two-up" }, el("div", { class: "stack" }, ingredientList(), nutrition()),
      el("div", { class: "stack" }, steps(), planned())), more());
  }

  const from = query.get("from");
  if (from && /^[a-z-]+\.html(#[a-z-]+)?$/.test(from)) {
    $("back").href = from;
    $("back").textContent = "← " + (from.startsWith("workout") ? "Workout" : from.startsWith("plan") ? "My plan" : "Kitchen");
  }

  MIAShell.start(async () => {
    try {
      page = await MIA.recipe(id);
    } catch (e) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "That recipe isn't here."), "It may have been deleted. Go back to the Kitchen."));
      return;
    }
    draw();
  });
})();
