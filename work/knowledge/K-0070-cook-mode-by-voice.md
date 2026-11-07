---
id: K-0070
kind: implementation
title: Cook mode by voice
status: confirmed
by: claude
created: 2026-11-07T17:32:37+00:00
concerns: core/assistant_cooking_actions.py, core/cooking_actions.py
from: dec:DEC-0125, dec:DEC-0113
---
DEC-0125 asks every action to work by voice and on a screen. Cook mode had only its buttons, so core/assistant_cooking_actions.py adds four tools in the kitchen domain: cook_start (finds the recipe by the words said: exact name, contained, or most words in common), cook_step (next, back, a step number, or where you are), cook_timer (a named timer for some minutes, or stop it) and cook_finish (made it: meal.cook through cooking.made; or stop without logging). Each runs the same action kind the screen does (describe then execute), so a refusal comes back in the action's own words and undo works. Registered in core/application.py and core/core_runtime.py beside the goods tools.
