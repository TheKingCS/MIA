# H-0027: The fitness + nutrition engine is ready for your screens (closes H-0026)
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-12
- Related: H-0026, DEC-0020, `docs/KITCHEN_FITNESS_PLAN.md`, DEC-0002, DEC-0014, DEC-0019

## What's built

All four gaps from H-0026, plus meal plans and the plain-word commands
Zac asked for. Engine only; the screens are yours.

| H-0026 asked | Built |
|---|---|
| Plan schema | `core/fitness_manager.py`: your schema as written (targets, training rotation, skill_tree, milestones, meals) plus `units` (lb/kg from the country). Per person, `fitness.json` on the device. |
| Nutrition tracking | Food logged per meal with calories, protein, carbs, fat (fiber, sugar, sodium when known). Recipes get their facts from a built-in USDA food table (`core/food_table.py`, 7,793 foods); typed values win; unknown is never shown as zero. |
| Skill sessions by time | `fitness.skill`: seconds (holds), reps or minutes; best hold per step. |
| Bodyweight trend | Weigh-ins, 7-day average, weekly rate (last 4 weeks), "on track for your goal by". |
| Plan → missions | `core/fitness_missions.py`: Training (each exercise), Skill practice (each practice item), Protein, Packed lunch, Meal prep (weekly, each prep session); also Today's meals, This week's meal plan, Workouts this week. Same mission path: one-tap +1, complete, XP, skills, undo. |

**The logs are the truth.** A mission's objectives are recomputed from
what was logged, so the Workout screen, Talk ("step one done") and +1 on
the mission all land the same.

**Non-punitive (DEC-0014).** A day that passes undone drops away quietly
(the logs keep what was done; the history says "nothing lost"). Rest
days aren't misses. "Is it working?" counts only from the first thing
logged, so nobody starts at "0 of 12".

## Data for the screens

- `GET /api/fitness`: `today` (training with `steps[]` and `done`,
  `rest_day`, skills with `best_seconds` and `minutes_today`, `food`
  totals against `targets`, `meals` planned today), `missions[]` (each with
  `objectives[]`, `done`/`total`, `cadence`), `weight` (latest,
  `average_7d`, `weekly_change`, `on_track_for`, `series[]` with a running
  average to draw), `milestones[]`, `progress` (the sentence, plus the
  numbers behind it and `days[]` of totals for charts), `plan`. A child's
  page has no `weight`.
- `GET /api/fitness/week?day=2026-10-12`: `days[]` (meals, totals,
  targets), `prep[]`, `planned`/`eaten`, `shopping` (`items[]` with
  `allergy` and `have_some`, plus what the pantry or the list already
  covers), `suggestion[]` (a week from the person's recipes), `recipes[]`.

## Actions (`MIAShell.act`)

`fitness.weigh_in` · `fitness.food` (a `recipe_id` with servings, or a
name and numbers) · `fitness.protein` · `fitness.training_done` ·
`fitness.step` (number or name) · `fitness.skill` · `fitness.habit`
(lunch / prep / protein) · `fitness.plan` (`changes`: any part of the
plan) · `fitness.milestone` · `meal.plan` · `meal.prep` (with `covers`) ·
`meal.prep_done` · `meal.suggest` (fill the week) · `meal.shop` (the
week's list onto the grocery list). Mission +1 on a fitness mission
also works and logs through these.

## Said in plain words (no model needed)

"workout complete", "step one of today's workout complete", "finished
my pull-ups", "today's lunch complete" (eats the planned lunch, with its
nutrition), "ate breakfast", "meal prep done", "this week's meal plans
complete", "I weigh 182.4", "had 40 g of protein", "hit my protein",
"handstand 45 seconds", "undo that". Instant on the phone, before any
model runs.

## Screens to build (yours)

Today (training steps, practice timer, protein bar, planned meals),
the week planner (drag a recipe into a meal, prep sessions, shopping
list), the weight line, "Is it working?", and the plan editor (targets,
rotation, skill tree, milestones). The look follows DEC-0018.

## Not built yet

Plan editor UI (the action takes any part of the plan); a guided "set
up my plan" interview; per-ingredient food choice when the table guesses
wrong (the engine supports `fdc_id` on an ingredient, no screen yet);
calories burned.
