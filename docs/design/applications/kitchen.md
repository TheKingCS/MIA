# Kitchen: design brief

*Claude, 2026-11-07, for H-0087 (pilot two). A **brief**, grounded in what exists; Muse turns it into the spec after
Workout. Template: `TEMPLATE.md`.*

**Status:** brief · **Maturity now:** 3 (Integrated) · **Target:** 5 (Trusted: used for real meal planning and
cooking)

## 1. Purpose and intended experience

A cooking and meal companion that knows what's in the house, what's planned, what you like and what you're aiming
for, and can be cooked **with**: hands busy, screen propped up, talking to her. Menus only when you want them.

## 2. Existing functionality (preserve all of it)

- **Engine:** `core/kitchen_manager.py` (recipes, pantry with use-by, grocery, meal log, ratings, times made,
  favourites), `core/kitchen_actions.py`, `core/meal_plan.py` (the week, prep sessions, allergies and dislikes),
  `core/food_table.py` (USDA nutrition, offline), `core/nutrition.py`, the fitness plan's meals and lunch rotation,
  meal missions.
- **Screens:** `web/kitchen.html` (Today with planned meals and nutrition, Week Plan, Recipes, Pantry, Grocery List,
  Meal Log, Suggestions), `web/recipe.html` (rating, stats, nutrition, have / on the list / to buy, steps to tick,
  schedule, add to grocery, I made this).

## 3. Navigation (proposed)

Home view **Today** (what's planned, what can be made now, what's expiring) → **Cook** (full screen, one recipe) ·
**Week** · **Recipes** (and each recipe) · **Pantry and Grocery** · **Meal history** inside Today or Week.

## 4–8. Screens to design

1. **Today**: the day's meals with nutrition against the plan, one tap "ate it", what expires soon, what can be made
   from the pantry.
2. **Recipe**: designed for reading at a counter: ingredients with have / missing, servings scaling, nutrition,
   start cooking.
3. **Cook mode** (the flagship moment, the focus surface): one step in large type; the ingredients this step uses;
   timers named by step ("rice, 18 min") that keep running across steps; next and back as big targets; the orb small
   and listening; "I made this" at the end (logs the meal, uses pantry, rates).
4. **Week plan**: the week at a glance, slots to fill, MIA filling empty ones, prep sessions, the week's shopping list.
5. **Pantry and grocery**: what's here, what's low, what's on the list, check off in the store.

## 9. States

No recipes yet · recipe without steps or ingredients · cooking in progress (survives a refresh and a phone lock) ·
timers running · nothing planned · offline · child account · demo.

## 10. Voice (mostly to build)

"Start cooking the chili", "next step", "go back", "repeat that", "set a timer for 18 minutes", "how long on the
rice?", "what can I use instead of buttermilk?", "I'm out of cumin" (to the grocery list), "we ate it". Engine work:
a cooking session like the training session (one per person, shared by every surface, persisted), with its own
quick commands and actions; **built in core first**.

## 11–12. Memory and missions

Ratings and times made; dislikes and allergies never offered; meal missions from the plan; XP for cooking (the
Cooking skill exists, in the Social group); the Chronicle sees meals made.

## 13. Dependencies and engineering work

- **New in the engine:** `core/cooking_session.py` (current step, timers, pantry use on finish), `cooking.*` actions,
  quick commands; substitutions from a small curated table (and the specialists' notes), never guessed by the model
  unchecked.
- Recipe photos (the recipe page has the slot; images from the visual library or the person's own).
- Pantry updated by "I made this" (ingredient matching exists for the grocery list).

## 14–16. Devices

Tablet or phone propped up (cook mode first), desktop for planning the week, glasses for the current step and timers
(one panel: step, timer).

## 17. Accessibility

Very large type in cook mode; everything by voice (floury hands); timers heard, not only seen; high contrast in a
bright kitchen.

## 18. Acceptance criteria

- A whole recipe can be cooked by voice alone, timers included, with the screen locked and back.
- Nothing from today's Kitchen is lost (each tab's function has a home).
- A substitution is never suggested for an allergy, and always says where it comes from.
- Zac plans a real week and cooks at least five real meals with it; his changes are the refinement list; then level 5.
