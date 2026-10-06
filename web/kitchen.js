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
  const TABS = [["recipes", "Recipes"], ["pantry", "Pantry"], ["grocery", "Grocery List"], ["meals", "Meal Log"],
    ["suggestions", "Suggestions"]];
  let page = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "recipes";

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
  async function ingredients(r) {
    const v = await form(r.name + ": ingredients", page.forms.ingredients.fields, { ingredients: r.ingredients_text });
    if (v) act({ kind: "recipe.ingredients", params: { recipe_id: r.id, ingredients: v.ingredients } });
  }
  async function logMeal(r) {
    const v = await form("Log a meal: " + r.name, page.forms.meal.fields, {});
    if (v) act({ kind: "meal.log", params: Object.assign({ recipe_id: r.id }, v) });
  }
  const favorite = (r) => act({ kind: "recipe.favorite", params: { recipe_id: r.id, favorite: !r.favorite } });
  const addMissing = (r) => act({ kind: "grocery.from_recipe", params: { recipe_id: r.id } });

  // ------------------------------------------------------------ a recipe, opened
  function openRecipe(r) {
    const dialog = el("dialog", { class: "confirm form-dialog recipe-sheet", "aria-label": r.name });
    const close = () => { dialog.close(); dialog.remove(); };
    const then = (fn) => () => { close(); fn(r); };
    dialog.append(...[
      el("h3", {}, (r.favorite ? "★ " : "") + r.name),
      el("p", { class: "dim" }, meta(r)),
      r.locked ? el("p", { class: "locked-note" }, "🔒 Locked" + (r.unlocked_by_mission ? ": finish “" + r.unlocked_by_mission + "” to unlock it." : ".")) : null,
      el("h4", {}, "Ingredients"),
      r.ingredients.length ? el("ul", { class: "recipe-ingredients" }, r.ingredients.map((name) =>
        el("li", { class: r.missing.includes(name) ? "missing" : "" }, name + (r.missing.includes(name) ? " (not in the pantry)" : ""))))
        : el("p", { class: "dim" }, "No ingredients yet."),
      r.instructions ? el("h4", {}, "Steps") : null,
      r.instructions ? el("p", { class: "recipe-steps" }, r.instructions) : null,
      r.notes ? el("p", { class: "dim" }, r.notes) : null,
      r.times_made ? el("p", { class: "dim" }, "Made " + r.times_made + "×" + (r.last_made ? ", last on " + day(r.last_made) : "")) : null,
      el("div", { class: "confirm-actions recipe-actions" },
        r.locked ? null : btn("Log meal", "btn-green", then(logMeal)),
        r.missing.length ? btn("Add missing to list", "btn-amber", then(addMissing)) : null,
        btn(r.favorite ? "Unfavorite" : "Favorite", "btn-ghost", then(favorite)),
        btn("Ingredients", "btn-ghost", then(ingredients)),
        btn("Edit", "btn-ghost", then((x) => edit("recipe", x))),
        btn("Delete", "btn-ghost", then((x) => del("recipe", x))),
        btn("Close", "btn-ghost", close))].filter(Boolean));
    dialog.oncancel = (e) => { e.preventDefault(); close(); };
    document.body.append(dialog);
    dialog.showModal();
  }

  // ------------------------------------------------------------ pieces
  function meta(r) {
    return [r.category, r.minutes ? r.minutes + "m" : null, r.servings ? r.servings + " serving" + (r.servings === 1 ? "" : "s") : null,
      r.calories ? Math.round(r.calories) + " cal" : null].filter(Boolean).join(" · ");
  }

  function recipeCard(r) {
    const status = r.locked ? el("span", { class: "chip" }, "🔒 Locked")
      : r.makeable ? el("span", { class: "chip chip-ok" }, "You can make this")
      : r.missing.length ? el("span", { class: "chip chip-soon" }, r.missing.length + " missing") : null;
    return el("article", { class: "glass recipe-card" + (r.locked ? " locked" : "") },
      el("div", { class: "asset-head" }, el("h3", {}, (r.favorite ? "★ " : "") + r.name), status),
      el("p", { class: "dim" }, meta(r) || "No details yet"),
      r.locked && r.unlocked_by_mission ? el("p", { class: "locked-note" }, "Unlock: " + r.unlocked_by_mission) : null,
      r.ingredients.length ? el("p", { class: "recipe-line" }, r.ingredients.slice(0, 5).join(", ") + (r.ingredients.length > 5 ? "…" : "")) : null,
      buttons(btn("View recipe", "btn-ghost", () => openRecipe(r)), r.locked ? null : btn("Log meal", "btn-green", () => logMeal(r))));
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

  const views = {
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
        el("div", {}, el("div", { class: "row-title" }, m.recipe), el("div", { class: "row-sub" }, [day(m.date), m.notes].filter(Boolean).join(" · "))),
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
    page = await MIA.kitchen();
    if (!page.available) {
      $("panel").replaceChildren(el("p", { class: "empty" }, el("strong", {}, "The kitchen isn't set up on this MIA."), ""));
      return;
    }
    draw();
  });
})();
