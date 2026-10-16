/*
 * kitchen.js — the Kitchen screen (claude, 2026-10-06, DEC-0017/0018).
 * Renders MIA.kitchen() (core/web_screens.py): recipes (with what's missing
 * and which mission unlocks a locked one), the pantry, the grocery list, the
 * meal log and suggestions. Every button proposes a kitchen action
 * (core/kitchen_actions.py) and the engine decides. Formatting only here.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["today", "Today"], ["week", "Week Plan"], ["recipes", "Recipes"], ["pantry", "Pantry"], ["grocery", "Grocery List"],
    ["meals", "Meal Log"], ["suggestions", "Suggestions"]];
  const MEALS = ["breakfast", "lunch", "dinner", "snack"];
  let page = null;
  let fit = null;   // MIA.fitness(): today (null where fitness isn't set up)
  let week = null;  // MIA.fitnessWeek(weekDay)
  let weekDay = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : null;

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const day = (iso) => iso ? new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }) : "";
  const qty = (i) => [i.quantity ? Number(i.quantity).toLocaleString() : "", i.unit].filter(Boolean).join(" ");

  // ------------------------------------------------------------ changes
  async function add(key, title, values) {
    const v = await form(title, page.forms[key].fields, values || {});
    if (v) act({ kind: key + ".add", params: v });
  }
  async function edit(key, row) {
    const spec = page.forms[key];
    const v = await form("Edit " + spec.noun, spec.fields, row.values);
    if (v) act({ kind: key + ".edit", params: Object.assign({ [spec.id_param]: row.id }, v) });
  }
  const del = (key, row) => act({ kind: key + ".delete", params: { [page.forms[key].id_param]: row.id } });
  async function logMeal(r) {
    const v = await form("Log a meal: " + r.name, page.forms.meal.fields, {});
    if (v) act({ kind: "meal.log", params: Object.assign({ recipe_id: r.id }, v) });
  }

  // ------------------------------------------------------------ a recipe, opened (its own page)
  const recipeHref = (id) => "recipe.html?id=" + encodeURIComponent(id) + "&from=" + encodeURIComponent("kitchen.html#" + tab);
  const recipeLink = (id, label, cls) => el("a", { class: cls || "recipe-link", href: recipeHref(id) }, label);

  // ------------------------------------------------------------ pieces
  function meta(r) {
    return [r.category, r.minutes ? r.minutes + "m" : null, r.servings ? r.servings + " serving" + (r.servings === 1 ? "" : "s") : null,
      r.calories ? Math.round(r.calories) + " cal" : null].filter(Boolean).join(" · ");
  }

  function recipeCard(r) {
    const status = r.locked ? el("span", { class: "chip" }, "🔒 Locked")
      : r.makeable ? el("span", { class: "chip chip-ok" }, "You can make this")
      : r.missing.length ? el("span", { class: "chip chip-soon" }, r.missing.length + " missing") : null;
    const pic = r.photo ? el("div", { class: "recipe-thumb" }) : null;
    if (pic) MIA.image(r.photo).then((url) => { if (url) pic.append(el("img", { src: url, alt: "" })); });
    return el("article", { class: "glass recipe-card" + (r.locked ? " locked" : "") }, pic,
      el("div", { class: "asset-head" }, recipeLink(r.id, el("h3", {}, (r.favorite ? "★ " : "") + r.name)), status),
      el("p", { class: "dim" }, meta(r) || "No details yet"),
      r.rating || r.times_made ? el("p", { class: "recipe-stats" }, r.rating ? el("span", { class: "card-stars", "aria-label": r.rating + " of 5 stars" }, "★".repeat(Math.round(r.rating)) + "☆".repeat(5 - Math.round(r.rating))) : null,
        r.times_made ? el("span", { class: "dim" }, "made " + r.times_made + "×") : null) : null,
      r.locked && r.unlocked_by_mission ? el("p", { class: "locked-note" }, "Unlock: " + r.unlocked_by_mission) : null,
      r.ingredients.length ? el("p", { class: "recipe-line" }, r.ingredients.slice(0, 5).join(", ") + (r.ingredients.length > 5 ? "…" : "")) : null,
      buttons(recipeLink(r.id, "View recipe", "btn btn-ghost"), r.locked ? null : btn("Log meal", "btn-green", () => logMeal(r))));
  }

  function pantryRow(p) {
    const when = p.expires_in == null ? null : p.expires_in < 0 ? "expired" : p.expires_in === 0 ? "use today" : "use in " + p.expires_in + "d";
    return el("div", { class: "row money-row" + (p.expiring ? " today" : "") },
      el("div", {}, el("div", { class: "row-title" }, p.name), el("div", { class: "row-sub" }, [qty(p), p.category].filter(Boolean).join(" · "))),
      el("div", { class: "row-meta" },
        when ? el("span", { class: "when " + (p.expires_in < 0 ? "overdue" : p.expiring ? "today" : "") }, when) : null,
        buttons(btn("Edit", "btn-ghost", () => edit("pantry", p)), btn("Remove", "btn-ghost", () => del("pantry", p)))));
  }

  function groceryRow(g) {
    const box = el("input", { type: "checkbox", "aria-label": "Got " + g.name, checked: g.checked || null,
      onchange: () => { box.checked = g.checked; act({ kind: "grocery.check", params: { item_id: g.id, checked: !g.checked } }); } });
    return el("div", { class: "row money-row grocery-row" + (g.checked ? " checked" : "") },
      el("label", { class: "grocery-check" }, box,
        el("span", {}, el("span", { class: "row-title" }, g.name),
          el("span", { class: "row-sub" }, [qty(g), g.for_recipe ? "for " + g.for_recipe : null].filter(Boolean).join(" · ")))),
      buttons(btn("Remove", "btn-ghost", () => del("grocery", g))));
  }

  function section(title, actions, body) {
    return el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), body);
  }

  // ------------------------------------------------------------ views
  function pantryCard() {
    return section("Pantry", buttons(btn("Add item", "btn-amber", () => add("pantry", "Add to the pantry"))),
      page.pantry.length ? el("div", { class: "rows" }, page.pantry.map(pantryRow))
        : el("p", { class: "empty" }, el("strong", {}, "The pantry is empty."), "Add what you have, and MIA can tell you what you can make."));
  }
  function groceryCard() {
    const anyChecked = page.grocery.some((g) => g.checked);
    return section("Grocery list", buttons(
      anyChecked ? btn("Clear checked", "btn-ghost", () => act({ kind: "grocery.clear_checked", params: {} })) : null,
      btn("Add item", "btn-amber", () => add("grocery", "Add to the grocery list"))),
      page.grocery.length ? el("div", { class: "rows" }, page.grocery.map(groceryRow)) : el("p", { class: "dim" }, "Nothing on the list."));
  }

  // ------------------------------------------------------------ Today and Week (DEC-0020, H-0028)
  const cap = (x) => x.charAt(0).toUpperCase() + x.slice(1);
  const g = (v) => v == null ? "—" : Math.round(v).toLocaleString();  // unknown is "—", never 0
  const plural = (n, w) => n + " " + w + (n === 1 ? "" : "s");
  const planLink = () => el("a", { class: "btn btn-ghost", href: "plan.html?from=" + encodeURIComponent("kitchen.html#" + tab) }, "My plan");
  const isoDay = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const shift = (iso, days) => { const d = new Date(iso + "T00:00:00"); d.setDate(d.getDate() + days); return isoDay(d); };
  const recipeList = () => (week ? week.recipes : page.recipes.filter((r) => !r.locked)).map((r) => ({ id: r.recipe_id || r.id, name: r.name }));

  /** Tap a slot → pick a recipe (MIA's suggestion for that slot first) → meal.plan. */
  async function planSlot(dayIso, meal, current) {
    const suggested = week && week.suggestion.find((x) => x.date === dayIso && x.meal === meal);
    const list = recipeList();
    const picks = suggested ? [{ id: suggested.recipe_id, name: "Suggested: " + suggested.name }].concat(list.filter((r) => r.id !== suggested.recipe_id)) : list;
    if (!picks.length) { MIAShell.say("Add a recipe first (Recipes tab)."); return; }
    const v = await form(cap(meal) + ", " + day(dayIso), [
      { name: "recipe_id", label: "Recipe", type: "pick", options: ["recipes"], required: true },
      { name: "servings", label: "Servings", type: "number", required: true, default: current ? current.servings : 1 },
    ], { recipe_id: current ? current.recipe_id : (picks[0] || {}).id }, { recipes: picks });
    if (v) act({ kind: "meal.plan", params: { date: dayIso, meal, recipe_id: v.recipe_id, servings: v.servings } });
  }
  const clearSlot = (dayIso, meal) => act({ kind: "meal.plan", params: { date: dayIso, meal, recipe_id: "" } });
  const ateIt = (dayIso, m) => act({ kind: "fitness.food", params: { meal: m.meal, recipe_id: m.recipe_id, servings: m.servings,
    date: dayIso, planned_id: dayIso + ":" + m.meal } });

  function proteinBar(totals, targets) {
    const have = totals.protein_g || 0, want = targets.protein_g;
    if (!want) return el("p", { class: "dim" }, "Protein today: " + g(totals.protein_g) + " g. Set a protein target in My plan to see the bar.");
    const pct = Math.min(100, Math.round((100 * have) / want));
    return el("div", { class: "protein" + (have >= want ? " hit" : "") },
      el("div", { class: "protein-head" }, el("strong", {}, Math.round(have) + " g protein"), el("span", { class: "dim" }, "goal " + want + " g" + (have >= want ? " ✓" : ""))),
      el("div", { class: "protein-track", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(want), "aria-valuenow": String(Math.round(have)) },
        el("div", { class: "protein-fill", style: "width:" + pct + "%" }), el("span", { class: "protein-tick", "aria-hidden": "true" })));
  }

  function mealCard(dayIso, m, today) {
    return el("article", { class: "glass meal-card" + (m.eaten ? " eaten" : "") },
      el("div", { class: "meal-slot" }, cap(m.meal) + (m.prep_id ? " · prepped" : "")),
      recipeLink(m.recipe_id, el("h3", {}, m.name)),
      el("p", { class: "dim" }, [plural(m.servings, "serving"), g(m.kcal) + " kcal", g(m.protein_g) + " g protein"].join(" · ")),
      el("div", { class: "row-buttons" },
        m.eaten ? el("span", { class: "chip chip-ok" }, "✓ Eaten")
          : today ? btn("Ate it", "btn-green", () => ateIt(dayIso, m)) : null,
        recipeLink(m.recipe_id, "Recipe", "btn btn-ghost"),
        m.eaten ? null : btn("Change", "btn-ghost", () => planSlot(dayIso, m.meal, m))));
  }

  async function logOther() {
    const v = await form("Log something you ate", [
      { name: "name", label: "What was it", type: "text", required: true },
      { name: "meal", label: "Meal", type: "choice", options: MEALS, default: "snack" },
      { name: "kcal", label: "Calories", type: "number" }, { name: "protein_g", label: "Protein (g)", type: "number" }]);
    if (v) act({ kind: "fitness.food", params: v });
  }
  async function addProtein() {
    const v = await form("Add protein", [{ name: "grams", label: "Grams", type: "number", required: true },
      { name: "name", label: "What (a shake, a snack)", type: "text" }]);
    if (v) act({ kind: "fitness.protein", params: v });
  }

  function todayView() {
    if (!fit) return [section("Today", null, el("p", { class: "dim" }, "Meal plans aren't set up on this MIA."))];
    const t = fit.today, plan = t.meals, food = t.food;
    const planned = new Set(plan.meals.map((m) => m.meal));
    const missions = fit.missions.filter((m) => ["meals", "lunch", "protein", "prep", "meal_plan"].includes(m.kind));
    const extra = food.entries.filter((e) => !(e.planned_id && planned.has(e.meal)));
    return [
      section("Today", buttons(planLink()),
        proteinBar(food.totals, food.targets),
        el("p", { class: "dim" }, g(food.totals.kcal) + " kcal eaten" + (food.targets.kcal ? " of " + food.targets.kcal.toLocaleString() : "") +
          " · " + g(plan.totals.kcal) + " kcal planned")),
      el("div", { class: "asset-grid meal-grid" }, MEALS.map((meal) => {
        const m = plan.meals.find((x) => x.meal === meal);
        return m ? mealCard(plan.date, m, true)
          : el("button", { type: "button", class: "glass meal-card meal-empty", onclick: () => planSlot(plan.date, meal) },
            el("div", { class: "meal-slot" }, cap(meal)), el("span", { class: "dim" }, "+ Plan " + meal));
      })),
      el("div", { class: "two-up" },
        section("Also eaten today", buttons(btn("+ Protein", "btn-ghost", addProtein), btn("Log food", "btn-amber", logOther)),
          extra.length ? el("div", { class: "rows" }, extra.map((e) => el("div", { class: "row money-row" },
            el("div", {}, el("div", { class: "row-title" }, e.name), el("div", { class: "row-sub" }, [cap(e.meal), g(e.kcal) + " kcal", g(e.protein_g) + " g protein"].join(" · "))),
            buttons(btn("Remove", "btn-ghost", () => act({ kind: "fitness.food_delete", params: { entry_id: e.id } }))))))
            : el("p", { class: "dim" }, "Nothing else logged. Or just tell MIA: “had a 40 g protein shake”.")),
        section("Today's missions", null, missions.length ? el("div", { class: "rows" }, missions.map((m) => el("div", { class: "row money-row" },
          el("div", {}, el("div", { class: "row-title" }, m.icon + " " + m.name), el("div", { class: "row-sub" }, m.done + " of " + m.total + (m.cadence === "weekly" ? " this week" : ""))),
          m.status === "completed" ? el("span", { class: "chip chip-ok" }, "✓ Done") : null)))
          : el("p", { class: "dim" }, "Plan a meal or set a protein target, and MIA makes today's meal missions."))),
    ];
  }

  // Phones (Muse, H-0031): today open, the other days one line each until tapped.
  const opened = new Set();
  const narrow = () => window.matchMedia("(max-width: 720px)").matches;

  function dayCard(d) {
    const isToday = d.date === fit.as_of;
    const t = d.totals, want = d.targets;
    const closed = narrow() && !isToday && !opened.has(d.date);
    const toggle = () => { opened.has(d.date) ? opened.delete(d.date) : opened.add(d.date); draw(); };
    const summary = g(t.kcal) + (want.kcal ? "/" + want.kcal.toLocaleString() : "") + " kcal · " + g(t.protein_g) + (want.protein_g ? "/" + want.protein_g : "") + " g";
    const head = el("div", { class: "week-day-head" }, el("h3", {}, isToday ? "Today" : day(d.date)),
      el("span", { class: "dim" }, (closed ? plural(d.meals.length, "meal") + " · " : "") + summary));
    if (closed) {
      return el("article", { class: "glass week-day collapsed" },
        el("button", { type: "button", class: "week-day-toggle", "aria-expanded": "false", onclick: toggle }, head));
    }
    return el("article", { class: "glass week-day" + (isToday ? " is-today" : "") },
      narrow() && !isToday ? el("button", { type: "button", class: "week-day-toggle", "aria-expanded": "true", onclick: toggle }, head) : head,
      MEALS.map((meal) => {
        const m = d.meals.find((x) => x.meal === meal);
        return el("div", { class: "week-slot" + (m ? "" : " empty") + (m && m.eaten ? " eaten" : "") },
          el("span", { class: "meal-slot" }, cap(meal)),
          m ? recipeLink(m.recipe_id, m.name + (m.servings !== 1 ? " ×" + m.servings : "") + (m.eaten ? " ✓" : ""))
            : el("button", { type: "button", class: "slot-add", onclick: () => planSlot(d.date, meal) }, "+ add"),
          m && !m.eaten ? el("button", { type: "button", class: "slot-x", "aria-label": "Clear " + meal, onclick: () => clearSlot(d.date, meal) }, "×") : null);
      }));
  }

  async function planPrep() {
    const v = await form("Plan a prep session", [
      { name: "date", label: "Prep day", type: "date", required: true, default: week.days[0].date <= fit.as_of && fit.as_of <= week.days[6].date ? fit.as_of : week.days[0].date },
      { name: "recipe_id", label: "What to cook", type: "pick", options: ["recipes"], required: true },
      { name: "servings", label: "Servings", type: "number", required: true, default: 4 }], {}, { recipes: recipeList() });
    if (!v) return;
    // It covers this week's meals of that recipe from the prep day on.
    const covers = week.days.filter((d) => d.date >= v.date).flatMap((d) => d.meals
      .filter((m) => m.recipe_id === v.recipe_id && !m.eaten).map((m) => d.date + ":" + m.meal));
    act({ kind: "meal.prep", params: Object.assign(v, { covers: covers.join(",") }) });
  }

  function weekView() {
    if (!fit || !week) return [section("Week plan", null, el("p", { class: "dim" }, "Meal plans aren't set up on this MIA."))];
    const first = week.days[0].date;
    const go = async (iso) => { weekDay = iso; week = await MIA.fitnessWeek(weekDay); draw(); };
    const shop = week.shopping;
    return [
      section("Week of " + day(first), buttons(
        btn("‹", "btn-ghost", () => go(shift(first, -7))), btn("This week", "btn-ghost", () => go(fit.as_of)), btn("›", "btn-ghost", () => go(shift(first, 7))),
        week.suggestion.length ? btn("Fill " + plural(week.suggestion.length, "empty meal"), "btn-amber", () => act({ kind: "meal.suggest", params: { date: first } })) : null,
        planLink()),
        el("p", { class: "dim" }, week.planned ? week.eaten + " of " + plural(week.planned, "planned meal") + " eaten." : "Nothing planned yet. Tap “+ add” on a day, or let MIA fill the week from your recipes.")),
      el("div", { class: "week-grid" }, week.days.map(dayCard)),
      el("div", { class: "two-up" },
        section("Meal prep", buttons(btn("Plan prep", "btn-amber", planPrep)),
          week.prep.length ? el("div", { class: "rows" }, week.prep.map((x) => el("div", { class: "row money-row" },
            el("div", {}, el("div", { class: "row-title" }, recipeLink(x.recipe_id, x.name)),
              el("div", { class: "row-sub" }, [day(x.date), plural(x.servings, "serving"), x.covers.length ? "covers " + plural(x.covers.length, "meal") : null].filter(Boolean).join(" · "))),
            buttons(x.done ? el("span", { class: "chip chip-ok" }, "✓ Cooked") : btn("Done", "btn-green", () => act({ kind: "meal.prep_done", params: { prep_id: x.id } })),
              btn("Remove", "btn-ghost", () => act({ kind: "meal.prep_delete", params: { prep_id: x.id } }))))))
            : el("p", { class: "dim" }, "Cook ahead: plan a prep session and it covers that recipe's meals for the rest of the week.")),
        section("Shopping for this week", shop.items.length ? buttons(btn("Add " + plural(shop.items.length, "item") + " to the list", "btn-amber",
          () => act({ kind: "meal.shop", params: { date: first } }))) : null,
          shop.items.length ? el("div", { class: "rows" }, shop.items.map((i) => el("div", { class: "row money-row" + (i.have_some ? " dimmed" : "") },
            el("div", {}, el("div", { class: "row-title" }, i.name), el("div", { class: "row-sub" }, [qty(i), "for " + i.recipes.join(", "), i.have_some ? "you have some" : null].filter(Boolean).join(" · "))),
            i.allergy ? el("span", { class: "chip chip-bad" }, "⚠ allergy") : null)))
            : el("p", { class: "dim" }, week.planned ? "Nothing to buy: the house has it, or it's on the list." : "Plan some meals and the shopping list makes itself."),
          shop.in_pantry.length || shop.on_list.length ? el("p", { class: "dim" }, [shop.in_pantry.length ? plural(shop.in_pantry.length, "thing") + " already in the pantry" : null,
            shop.on_list.length ? shop.on_list.length + " already on the list" : null].filter(Boolean).join(" · ") + ".") : null)),
    ];
  }

  const views = {
    today: todayView,
    week: weekView,
    recipes: () => [
      section("Recipes", buttons(btn("Add recipe", "btn-amber", () => add("recipe", "Add a recipe"))),
        page.recipes.length ? el("div", { class: "asset-grid recipe-grid" }, page.recipes.map(recipeCard))
          : el("p", { class: "empty" }, el("strong", {}, "No recipes yet."), "Add one, or tell MIA: “save my chili recipe”.")),
      el("div", { class: "two-up" }, pantryCard(), groceryCard()),
    ],
    pantry: () => [pantryCard()],
    grocery: () => [groceryCard()],
    meals: () => [section("Meal log", null, page.meals.length ? el("div", { class: "rows" }, page.meals.map((m) =>
      el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, m.recipe_id ? recipeLink(m.recipe_id, m.recipe) : m.recipe), el("div", { class: "row-sub" }, [day(m.date), m.notes].filter(Boolean).join(" · "))),
        buttons(btn("Remove", "btn-ghost", () => act({ kind: "meal.delete", params: { entry_id: m.id } }))))))
      : el("p", { class: "dim" }, "No meals logged in the last two months. Open a recipe and press Log meal."))],
    suggestions: () => [section("What you can make", null, page.suggestions.length
      ? el("div", { class: "asset-grid recipe-grid" }, page.suggestions.map(recipeCard))
      : el("p", { class: "dim" }, "Add ingredients to your recipes and stock the pantry, and MIA will suggest what's closest to ready."))],
  };

  function draw() {
    const c = page.counts;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, c.recipes), el("span", { class: "t" }, "Recipes")),
      el("div", { class: "cell " + (c.expiring ? "bad" : "ok") }, el("span", { class: "n" }, c.expiring), el("span", { class: "t" }, "Expiring soon")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, c.grocery), el("span", { class: "t" }, "To buy")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) =>
      el("button", { type: "button", role: "tab", "aria-selected": String(id === tab), onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    $("panel").replaceChildren(...views[tab]());
  }

  MIAShell.start(async () => {
    [page, fit, week] = await Promise.all([MIA.kitchen(), MIA.fitness().catch(() => null), MIA.fitnessWeek(weekDay).catch(() => null)]);
    if (fit && !fit.available) fit = null;
    if (week && !week.available) week = null;
    if (!tab) tab = fit ? "today" : "recipes";
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "The kitchen isn't set up on this MIA."), ""));
      return;
    }
    draw();
  });
})();
