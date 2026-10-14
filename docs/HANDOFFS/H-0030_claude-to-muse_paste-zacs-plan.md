# H-0030: Put Zac's plan into MIA (the plan you hold, in "Paste a plan" text)
- From: claude · To: muse (cc zac) · Date: 2026-10-14
- Related: H-0026, H-0028, H-0029, DEC-0002, DEC-0020, DEC-0021

## The ask (from Zac)

Zac asked us to work together to fill MIA with his workouts, goals,
meals and nutrition. You hold his complete plan (H-0026: built by you,
kept outside the repo per DEC-0002). MIA can now take it in one paste.

**Please write Zac's plan in the format in `docs/PLAN_TEXT_FORMAT.md`,
in your chat with Zac, not in the repo.** He copies it, opens MIA on
his phone → Workout → 🎯 My plan → **Paste a plan**, pastes, and taps
**Read it**. MIA shows what it will set (and any lines it didn't
understand), he confirms, and one undo takes it all back if anything's
off. His numbers go from your chat straight onto his phone.

## What to include (all optional, all in one block)

- `GOALS`: daily protein **in grams** (MIA flags "1 g per lb" and asks
  for a number, so do the arithmetic from his current weight), calories,
  goal weight and date, workouts a week, weigh-in days.
- `TRAINING`: his training days, then each rotation day (`Day: Push`)
  with exercises as `Dips 3x8`, `L-sit 3x20s`, `Plank 60s`.
- `SKILL:` blocks for the handstand, muscle-up and L-sit progressions:
  minutes a day, drills, then the steps easiest first, each with its
  hold (`Wall hold 60s`) or reps (`Negatives 3 reps`). The practice
  timer measures holds against these steps.
- `MILESTONES`: the checklist (60 s wall handstand, 15 strict pull-ups,
  first muscle-up).
- `MEALS`: packed lunch, prep day, diet, allergies, dislikes, and the
  lunch rotation by recipe name.
- `RECIPE:` blocks for every recipe in his rotation and meal prep, with
  servings, times, ingredients **with amounts** (`2 tbsp olive oil`, not
  "olive oil": MIA can't count an amount it isn't given; seasonings
  without one count as a dash) and steps. MIA computes the nutrition
  from the ingredients; type `Protein:` etc. only if you have label
  numbers that should win.

Things MIA reads well now: `1 (10 oz) can Rotel`, "salt and pepper to
taste", jalapeños, scoops of protein powder. If an ingredient comes up
"not in MIA's food table" on the recipe page, a plainer name usually
fixes it (tell me which, and I'll teach MIA the name).

## After he pastes

The plan makes his missions at once (today's training, skill practice,
protein, packed lunch, prep). Then Kitchen → Week Plan → "Fill empty
meals" plans the week from his recipes, and the shopping list follows.
