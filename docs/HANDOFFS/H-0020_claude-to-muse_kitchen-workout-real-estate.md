# H-0020: Kitchen, Workout and Real Estate are working
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-06
- Related: DEC-0017, DEC-0018, H-0019, Zac's concept set (Kitchen, Workout, Real Estate panels)

## What landed (yours to restyle; please keep the data flow)

- **Kitchen (`kitchen.html`, `kitchen.js`)**, from `MIA.kitchen()`.
  - Tabs: Recipes, Pantry, Grocery List, Meal Log, Suggestions.
  - Recipe cards show the meal, minutes, servings, ingredients, and whether you can make it or how many are missing.
  - A locked recipe says which mission unlocks it.
  - View recipe opens it with Log meal, Add missing to list, Favorite, Ingredients (one per line, e.g. "2 cups rice"), Edit and Delete.
  - Pantry (with use-by chips) and the grocery list (checkboxes, Clear checked) sit side by side under the recipes, as in the concept.
- **Workout (`workout.html`, `workout.js`)**, from `MIA.workout()`.
  - The concept's inline Log Session: pick an exercise (reps, sets, weight, minutes, date, notes) or a whole template.
  - What's typed survives a live refresh.
  - Latest Entry, Daily Mission (progress bar and streak) and Recent History.
  - Tabs for Exercises (personal records), Templates (add or remove exercises, Log it), History and Progress (a small line per exercise).
- **Real Estate (`real-estate.html`, `real-estate.js`)**, from `MIA.realEstate()`.
  - Property cards show the status chip, location, rent per month, balance, equity, cash flow and this month's in and out.
  - Buttons: Record rent and Add expense (both land in Money), Track upkeep (gives the property its own Maintenance asset, opened on `asset.html`), Edit and Delete.
  - Maintenance and Missions tabs.
  - Grown-ups only.
- **Every change is an action with a confirm and undo.**
  - The new kinds are in `web/README.md`.
  - Forms come from the engine's field lists; `MIAShell.form` now also has a `pick` field, for exercises and templates.

## Notes for the look

- The styles are at the end of `concept.css` ("Kitchen, Workout, Real Estate"). Restyle freely.
- Recipes and properties have no photo field yet. The concept's food and house pictures need one. Say so in `QUESTIONS.md` and I'll add the field and an upload.
- The hero photos come from `web/img/kitchen.jpg`, `workout.jpg` and `real-estate.jpg`, per `docs/design/IMAGE_REQUESTS.md`.

## Acceptance criteria

- After a restyle, these all still work end to end, each with undo:
  - Kitchen: log a meal, add what's missing, check off and clear the grocery list, add a recipe and its ingredients.
  - Workout: log a session both ways, and add an exercise to a template.
  - Real Estate: record rent, add an expense, edit, track upkeep, mark an upkeep task done, and delete a property.
