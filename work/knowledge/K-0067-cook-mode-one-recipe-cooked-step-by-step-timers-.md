---
id: K-0067
kind: implementation
title: Cook mode: one recipe cooked step by step, timers that keep running
status: confirmed
by: claude
created: 2026-11-07T14:52:43+00:00
concerns: core/cooking_session.py, core/cooking_actions.py, web/cook.js
from: dec:DEC-0113
---
What: core/cooking_session.py (a personal store, context.cooking) holds the recipe being cooked: its steps (recipe_steps of the instructions), the step in focus, and named timers that keep running across steps. Pure logic reads each step: step_timer finds the time a step asks for (a range takes the low end) and step_uses lists the recipe ingredients the step names (whole name or last word). core/cooking_actions.py puts it on the action contract: cooking.start/next/back/go_to/timer/timer_cancel/made/stop; cooking.made runs the kitchen own meal.cook (meal logged, pantry used up) then closes the session. web/cook.js draws cook mode as a full-screen layer on the Kitchen and recipe pages. How: the same shape as the live workout (core/training_session.py) so every surface moves one session. Why: DEC-0113 approved with the canvas as the reference; kitchen.md 13 asks for the engine first. Watch: nothing here guesses with a model; voice commands and the glasses panel are not built yet.
