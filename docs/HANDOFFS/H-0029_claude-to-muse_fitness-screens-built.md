# H-0029: Fitness screens built (responds to H-0028), plus Zac's recipe page
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-14
- Related: H-0028, H-0027, DEC-0020, DEC-0021, DEC-0018, DEC-0014

## What's built

Your five screens, working against the real engine, in the concept look
(DEC-0018: built by me from your spec; the look is yours to polish):

| # | Screen | Where |
|---|---|---|
| 1 | Today: training | `workout.html#today`: the plan's day as steps (tap a number to log `fitness.step`), "Workout complete", the rest-day state ("Recovery counts: it's part of the plan, not a miss"), the practice timer card per skill, the day's training missions |
| 2 | Progress | `workout.html#progress`: `progress.sentence` first and big, marked "Worked out from your logs" (DERIVED), the numbers, protein each day (bars, gold when the target is hit, dashed goal line), the weight line (weigh-ins as dots, the 7-day average as the line, the goal dashed; hover or focus a dot for its numbers), the four chips, every weigh-in with Remove, milestones with "Reached it". No weight section at all on a child's page. Empty state as you wrote it |
| 3 | Today: meals | `kitchen.html#today`: the protein bar (gold tick at the target, the whole bar gold when hit), a card per meal slot (planned meal with kcal and protein, unknown shown as "—"; one tap "Ate it"; an empty slot is a dashed "+ Plan lunch" card), other food eaten today, the day's meal missions |
| 4 | Week planner | `kitchen.html#week`: day cards (phone-first, tap a slot → recipe picker with MIA's suggestion first), "Fill N empty meals" (`meal.suggest`), prep sessions (Done, Remove), the shopping list (allergy chips, "you have some" dimmed, one button for `meal.shop`) |
| 5 | My plan | `plan.html`: one screen, two doors (Kitchen and Workout; it takes the colour of the door you came in by). Goals, training days and the rotation (exercises typed like "Dips 3x8", "L-sit 3x20s", "Plank 60s"; the engine parses them), skills with steps ("Wall hold 60s"), meals and preferences, lunch rotation, milestones |

The new-best moment: beat your best hold and a gold card pops ("New
best: 40 seconds · Wall hold · was 38 s") over a dimmed screen, with the
usual undo toast. It respects reduced motion. It's the loudest thing in
MIA right now; please make it louder or calmer as you see fit.

**Zac's addition (DEC-0021): a page for each recipe**, `recipe.html?id=`.
Every meal card and recipe card opens it: the macros (protein in gold),
**Schedule meal** and **Add to grocery list (N)** up top, ingredients
each marked Have it / On the list / To buy, nutrition per serving with
where it came from, the steps as a numbered list you can tick while
cooking, and when it's planned next. "Add to grocery list" adds only
what isn't in the pantry or already on the list; matching now ignores
plurals and words like "diced" ("Diced Onions" finds "onion").

## Zac's two calls (DEC-0021)

- One My plan screen: yes.
- Plain-word commands log **at once** with "undo that", not a confirm
  sheet first. Buttons on screens still propose → confirm → undo, as
  everywhere.

## Your four questions

1. **Payload size:** one call is fine. `/api/fitness` is about 17 KB with
   a month of logs; the week is a separate call (`/api/fitness/week`,
   about 9 KB) and only the Week tab needs it.
2. **Protein objective:** yes, grams against `plan.targets.protein_g`.
3. **`suggestion[]`:** recipe id and name only (plus date, meal,
   servings). Design the tile; I used the plain picker for now, with the
   suggestion first and marked ✨.
4. **Timer modes:** one card. It times; when you stop, you pick the step
   and log it as a hold (seconds, toward that step's best) or as practice
   time (minutes, toward the daily minutes). The engine also takes reps
   (`fitness.skill` has no reps field yet; say if you want it on the card).

## For your review (Look column)

Placeholder screenshots: run the preview with `?demo` (new examples:
`docs/schema/fitness.example.json`, `fitness_week.example.json`,
`recipe.example.json`). Things I'd most like your eye on: the meal card,
the week day card on a phone (it's long: seven cards), the protein bar,
and the celebration.
