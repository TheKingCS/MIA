---
id: K-0076
kind: implementation
title: Recipe servings scaling, worked out in core; a demo page that was blank
status: confirmed
by: claude
created: 2026-11-07T18:12:42+00:00
concerns: core/web_screens.py, core/units.py, web/recipe.js, docs/schema/recipe.example.json
from: dec:DEC-0113
---
The recipe page has a − N + servings stepper (the canvas's recipe). The page asks /api/kitchen/recipe/{id}?servings=N and core scales each ingredient: web_screens.scale_factor (1 to 100 servings over the recipe's own; anything unreadable shows the recipe's own) and scaled_amount, said by core/units.kitchen_amount to the nearest kitchen fraction for cups, spoons, pounds and counts ('1 ½ cups', '⅓ cup', 'a pinch'), whole numbers for grams and anything over 20. The stepper is display only: the grocery list and cook mode still use the recipe as written. Found on the way: the demo recipe page was blank because its example lacked nutrition.no_amount / to_taste and MIAShell.start swallowed the TypeError into the status line, which the old error sweep (page errors only) never saw. The sweep now also watches the status line for anything but the demo notice; all 78 demo pages are clean.
