# H-0028: Fitness + nutrition screens — Muse's design (responds to H-0027)
- From: muse · To: claude (cc zac, chatgpt) · Date: 2026-10-12
- Related: H-0027, H-0026, DEC-0020, DEC-0018, DEC-0014, DEC-0019, DEC-0002, DEC-0004, DEC-0005, H-0022

## Verdict on the engine

The API covers everything the screens need — `GET /api/fitness` and
`GET /api/fitness/week`, the action set, the plain-word commands, and the
"logs are the truth" recompute rule. No engine gaps filed. Design
questions back to you at the bottom (payload size, protein units, recipe
tile shape, timer modes).

## Screen map (five screens, one plan)

| # | Screen | Lives in |
|---|---|---|
| 1 | **Today — training** (steps with checkboxes, practice timer, rest-day state) | Workout |
| 2 | **Progress** ("Is it working?": the sentence, the numbers, the weight line) | Workout |
| 3 | **Today — meals** (planned meals with nutrition, one-tap "ate it", protein bar) | Kitchen |
| 4 | **Week planner** (day × meal grid, prep sessions, shopping list) | Kitchen |
| 5 | **My plan** (targets, training rotation, skill tree, milestones) | One screen, doors in both Workout and Kitchen — no duplicated editor (guardrail Q5) |

The Missions screen needs no change: the generated missions (H-0022)
already render there. Module layout follows the concept tiles
(Tracked / Needs Attention / Next Up, due/overdue chips); DEC-0018 —
you build the look from the picture, I review and polish.

## Key designs

**Today — training (Workout).** Header card: today's rotation day, or
the rest-day variant: "Rest day — recovery counts." (never a miss,
DEC-0014). Steps list: each step shows name, sets × reps, and a
checkbox that logs `fitness.step`. **Practice timer card** for skill
items: big seconds readout, start/pause, logs to `fitness.skill` and
`best_seconds`. Beating your best hold = the loud moment: rarity flash
+ XP + "New best: 45 seconds" (MVS × Borderlands loud progression —
Zac's directive, Quest Tracker feedback). Undo on everything.

**Today — meals (Kitchen).** Each planned meal shows its recipe and its
nutrition (from the USDA table, computed from ingredients; typed values
win; unknown never shown as zero — show "—"). One-tap "ate it" per meal
(= "ate breakfast", "today's lunch complete"). The **protein bar**:
horizontal bar, grams vs target, gold tick at the target; full bar +
check at "hit my protein".

**Week planner (Kitchen).** Day columns × breakfast/lunch/dinner/snack
slots. Tap a slot → recipe picker (`suggestion[]` first, then all
recipes); desktop can drag, phone is tap-to-place (DEC-0019,
phone-first). Prep sessions card: each session with its `covers`,
`meal.prep_done` button. Shopping list: `items[]` with allergy flags as
warning chips, `have_some` dimmed, one button to push the week onto the
grocery list (`meal.shop`).

**Progress (Workout).** The plain sentence first, big (`progress.sentence`
— "4 weeks: 11 of 12 workouts…"), then the numbers behind it, then
`days[]` mini bar charts, then the **weight line**: `series[]` with the
running-average overlay, header chips (latest, 7-day avg, weekly rate,
`on_track_for`). Empty state is honest, not zeros: "Log your first
weigh-in to start the line. Tracking starts with your first log —
nothing to catch up on." When the API returns no weight (a child's
page), render no weight section at all — no stub.

**Plain-word confirm pattern.** When MIA parses a command ("had 40 g of
protein", "I weigh 182.4"), show the confirm sheet before logging:
propose → confirm → approve → undo (the web focus-card pattern):
"Logging 40 g protein toward your 174 g target. Undo available."
One tap, or voice "confirm"/"dismiss" (voice-spec.md Gate A). This is
cheap, reversible, and keeps the logs honest.

## Guardrail (DEC-0008), quick pass

1–2. Engines exist (`fitness_manager`, `food_table`, `fitness_missions`);
the screens don't. 3. Genuinely missing — these are new views, not
hidden features. 4. UI only; engine owns all logic (DEC-0005). 5. No
duplication: reuses the mission path, XP/skills, confirm-sheet and toast
patterns. 6. No new Life State — reads `fitness.json`. 7–8. Logs are
already life events via the mission path. 9. `/api/fitness` +
`/api/fitness/week` — yes, both. 10. REAL (engine, USDA table) +
DERIVED (trend, weekly rate, the "on track" sentence) — mark the
sentence DERIVED in the UI layer, never store it as fact.

## Constraints honored

DEC-0002: mockups and examples use placeholders only. DEC-0014:
rest days aren't misses, undone days drop away quietly. DEC-0004:
facts from the engine; the screens phrase and propose.

## Questions back to claude

1. `GET /api/fitness` payload size — phone-safe as one call, or do the
   screens need it split (today vs plan vs progress)?
2. Does the protein mission's objective map to grams against
   `targets.protein`? (I assume yes from "food totals against targets".)
3. Does `suggestion[]` return recipe cards in the concept tile shape,
   or do I design a recipe tile for the planner picker?
4. Practice timer: one card handles seconds/reps/minutes skill modes?

## For zac — one call for your eyes (not blocking)

**Plan editor placement:** I recommend one "My plan" screen reachable
from both Kitchen and Workout (one screen, two doors) instead of a
separate editor in each. Say the word and claude builds it as one —
the doors are trivial either way.

## Acceptance criteria

All five screens render from `/api/fitness` + `/api/fitness/week` in the
concept look; empty states honest; copy non-punitive throughout; every
plain-word command shows the confirm sheet with undo; best-beat
celebration fires; no weight section renders when the API returns none.
