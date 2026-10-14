# Writing a plan MIA can read ("Paste a plan")

*2026-10-14 · claude. For anyone writing a fitness and meal plan for a
person to paste into MIA: Muse in a chat, a coach, the person themselves.
MIA reads it in **My plan → Paste a plan** (`core/plan_import.py`),
shows what it will set, and applies it as one change that "undo" takes
back.*

**Privacy (DEC-0002):** write a real person's plan in your chat with
them, never in this repo. The person copies it and pastes it on their
own phone; it goes from the chat straight into MIA on their device.

## The rules

- Sections start with a heading on its own line: `GOALS`, `TRAINING`,
  `MILESTONES`, `MEALS`, or a named one: `SKILL: Handstand`,
  `RECIPE: Turkey chili`, `Day: Push`. Case doesn't matter; Markdown
  `##` and bullets (`-`, `1.`, `- [ ]`) are fine.
- Inside a section, settings are `Name: value` lines; lists are one item
  a line.
- **Only what's in the text changes.** Leave out TRAINING and the
  training stays as it was. A TRAINING section with `Day:` blocks
  replaces the whole rotation. A recipe with the same name as one
  already in the Kitchen is updated, not duplicated. A milestone already
  reached stays reached.
- Anything MIA can't place (a greeting, a tip) is listed back to the
  person in the confirmation, never silently dropped and never saved.
- Daily numbers, not formulas: `Protein: 170 g`, not `1 g per lb`
  (MIA flags that line and asks for a number).

## What each section takes

| Section | Lines |
|---|---|
| `GOALS` | `Protein: 170 g` · `Calories: 2300` · `Goal weight: 175 lb by 2027-03-01` (lb or kg sets the units) · `Workouts a week: 3` · `Weigh-in days: Mon, Thu` · `Approach: maintenance` |
| `TRAINING` | `Days: Mon, Wed, Fri` (which days are training days), then each training day in rotation order: `Day: Push` followed by its exercises, one a line |
| Exercises | `Dips 3x8` (3 sets of 8) · `L-sit 3x20s` (3 holds of 20 s) · `Plank 60s` (one 60 s hold) · `Farmer carry` (just the name) |
| `SKILL: Handstand (12 min a day)` | `Minutes a day: 12` (or in the heading) · `Drills: Wrist prep, Wall walks` · then its steps, easiest first: `Wall hold 60s` · `Tuck 10 reps` · `Freestanding` |
| `MILESTONES` | one a line: `60 s wall handstand` |
| `MEALS` | `Packed lunch: yes` · `Prep day: Sunday` · `Diet: high protein` · `Allergies: peanuts` (or none) · `Don't eat: mushrooms` · `Lunch rotation: Turkey chili, Chicken rice bowl` (recipe names, from the Kitchen or this text) |
| `RECIPE: Turkey chili` | `Category: Lunch` · `Servings: 6` · `Prep: 15 min` · `Cook: 1 hr` · optional `Calories:`, `Protein:`, `Carbs:`, `Fat:` per serving (typed numbers win over MIA's own) · `Source:` · `Notes:` · then `Ingredients:` one a line (`2 lb ground turkey`, `1 (10 oz) can Rotel`, `Salt to taste`) and `Steps:` one a line |

MIA works out each recipe's nutrition from its ingredients (USDA food
data, built in) when no numbers are typed. Give amounts (`2 tbsp olive
oil`), or MIA can't count that ingredient; seasonings with no amount
count as a dash.

## A full example (placeholder person, "Robin")

```
GOALS
Protein: 150 g
Calories: 2100
Goal weight: 150 lb by 2027-05-01
Workouts a week: 3
Weigh-in days: Mon, Thu

TRAINING
Days: Mon, Wed, Fri
Day: Push
Push-ups 3x12
Pike push-ups 3x8
Plank 45s
Day: Pull
Australian rows 3x10
Dead hang 30s
Day: Legs
Goblet squats 3x12
Farmer carry 3x40s

SKILL: Handstand (10 min a day)
Drills: Wrist prep, Wall walks
Wall hold 30s
Wall hold 60s
Freestanding 10s

MILESTONES
60 s wall handstand
10 strict pull-ups

MEALS
Packed lunch: yes
Prep day: Sun
Diet: high protein
Allergies: none
Lunch rotation: Chicken rice bowl

RECIPE: Chicken rice bowl
Category: Lunch
Servings: 4
Prep: 15 min
Cook: 30 min
Ingredients:
2 lb chicken breast
2 cups rice
4 cups broccoli
2 tbsp olive oil
Salt and pepper to taste
Steps:
Cook the rice.
Roast the chicken and broccoli at 425°F for 20 minutes.
Divide into four containers.
```
