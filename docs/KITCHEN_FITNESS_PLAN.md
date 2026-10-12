# Kitchen + Workout + Missions: eat, train, see it working (plan)

*Claude, 2026-10-12, from Zac's request; approved as DEC-0020 with
Muse's H-0026. **Engine built 2026-10-12 (phases 1 to 7, H-0027);
the screens are Muse's next.***

## What Zac asked for

- Kitchen: track recipes, **meal prep**, **meal plans per day**, and
  **shopping lists from my preferences and goals**; **nutrition facts**
  stored for every meal.
- Workouts that **follow my goals and my nutrition**.
- **Log my weight** as I go, and see the trends: are the workouts and
  meal plans doing what I want?
- Meal prep, cooking the day's planned meals, and workouts are
  **missions**, daily and weekly.
- Just say it: "workout complete", "step one of today's workout
  complete", "today's lunch complete", "this week's meal plans complete".
  MIA logs it in the mission, Kitchen and Workout.

## What MIA has today

| Area | Today | Missing |
|---|---|---|
| Recipes | Ingredients, steps, servings, times; calories, protein, carbs, fat (typed in by hand); ratings, favorites; locked recipes as mission rewards | Nutrition without typing it; fiber, sugar, sodium |
| Pantry and groceries | Pantry, grocery list, "add what's missing" for a recipe | A list for the whole week's plan, scaled to servings, minus the pantry |
| Meals | A meal log (made a recipe on a date) | **Meal plans** (day × breakfast/lunch/dinner/snack), **prep sessions**, what you ate per day with its nutrition |
| Workouts | Exercises, templates, logged sessions with sets, personal records | A **weekly program**, today's workout as steps, goals |
| Body | — | **Weight log** and its trend |
| Goals | Missions; "why" goals (intents) | Fitness goals: target weight, calories, protein, workouts a week |
| Missions | One-off and repeating missions with objectives | Missions made **from the plans**, ticked by the logs |

## The design, in one rule

**The logs are the truth; missions and screens are views of them.**
Saying "today's lunch complete" logs that meal (Kitchen), which ticks
the lunch objective on today's meals mission (Missions). Logging a set
on the Workout screen ticks that step. Nothing is entered twice, and
undo works the same everywhere.

## Phases

1. **Body and goals.** A weight log (per person, private, in your
   country's units), its 7-day average and weekly trend. Fitness goals:
   target weight and date, daily calories and protein, workouts a week.
2. **Nutrition per day.** Every logged meal carries its nutrition
   (servings × the recipe's). Today's totals against your goals.
   Nutrition facts: typed in, or computed from the ingredients (see
   *Decision* below).
3. **Meal plans and prep.** A week plan: each day's meals, with recipe
   and servings. Prep sessions: "Sunday: cook venison chili × 6 servings"
   covers the plan's lunches. **Shopping list from the plan**: everything
   the week needs, scaled, minus the pantry, skipping what you don't eat
   (your preferences: dislikes, allergies, diet). MIA can suggest a week
   that fits your calories and protein from your own recipes.
4. **Workout program.** A weekly program (Mon: Push, Wed: Pull...), from
   your templates; today's workout as steps (each exercise with its
   sets); suggestions tied to the goal (losing, gaining, keeping).
5. **Missions from the plans.** Made automatically each day and week:
   - *Today's meals* (one objective per planned meal),
   - *Today's workout* (one objective per step),
   - *This week's meal prep* (each prep session),
   - *This week's workouts* (3 of 4, say), and *This week's meal plan*.
   Completing one logs it; logging one completes it. XP, skills (Body,
   Homestead) and streaks as for every mission.
6. **Say it.** Done in MIA's own code, instantly, with no AI model
   needed: "workout complete", "step 1 done", "finished my squats",
   "lunch done", "ate breakfast", "meal prep done", "this week's meals
   done", "I weigh 182". MIA says what it's about to log and you can undo.
   The model handles everything else (questions, planning, "what
   should I eat tonight?").
7. **Is it working?** A Progress screen: the weight line with its
   average, workouts done and meals on plan each week, average calories
   and protein against your goals, and one plain sentence computed in
   code: "4 weeks: 11 of 12 workouts, 2,180 kcal a day (goal 2,200),
   weight down 0.4 lb a week, on track for your goal by March."

## Decision for Zac (one)

**Where nutrition facts come from.**
- **A. Recommended:** a food table built into MIA (the US government's
  public food data, USDA FoodData Central, free to use, about 8,000
  everyday foods). MIA computes each recipe's nutrition from its
  ingredients, offline, and you can always type over it.
- B. Typed in by hand only (what MIA does today).

## Not in scope here

Barcode scanning, buying groceries online, wearables, and calories burned
from a watch come later. Medical advice stays out: MIA tracks and shows
numbers, and suggests a doctor for anything medical.
