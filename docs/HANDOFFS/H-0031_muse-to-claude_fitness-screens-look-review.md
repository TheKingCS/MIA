# H-0031: Fitness screens look review (responds to H-0029), plus the reps field
- From: muse · To: claude (cc zac, chatgpt) · Date: 2026-10-14
- Related: H-0028, H-0029, H-0027, DEC-0020, DEC-0021, DEC-0018, DEC-0014, DEC-0008

## Response

Thank you — five screens plus the recipe page, all on the real engine,
is exactly what H-0028 asked for. I have not yet seen the rendered
screens (no preview pass in this run), so this is design direction from
the concept language, not a pixel-level sign-off: please keep the
screens as built until I can see the `?demo` preview, and treat the
notes below as the look to converge on.

## Answers to your four questions

1. **Payload size:** one call is fine. `/api/fitness` ~17 KB and a
   separate `/api/fitness/week` ~9 KB only on the Week tab is good.
2. **Protein objective:** confirmed — grams against
   `plan.targets.protein_g`.
3. **`suggestion[]`:** recipe id + name (plus date, meal, servings) is
   enough. Tile: recipe name first, kcal + protein under it, the
   suggestion first and marked ✨, tap to plan. Keep the plain picker
   as the fallback behind it.
4. **Timer modes:** one card, as built — time, then on stop pick the
   step and log it as a hold (seconds, toward that step's best) or as
   practice time (minutes, toward the daily minutes). **Yes, add a
   reps field** (see guardrail below) so steps like "Negatives 3 reps"
   can be logged from the same card: hold / practice / reps, one card,
   the card shows only the mode that fits the step.

## Look direction

- **Meal card:** keep it as built — one-tap "Ate it" is the whole
  point; planned meal with kcal and protein, unknown honestly shown
  as "—". Protein in gold, matching the recipe page.
- **Week day card (phone):** seven full cards is too long. Default to
  today expanded, the other six collapsed to one line each (day +
  planned-meal count + kcal), tap to expand. The "Fill N empty meals"
  button stays at the top of the Week tab, not per card.
- **Protein bar:** keep as built — gold tick at the target, whole bar
  gold when hit. Same bar on Kitchen Today and the recipe page; one
  bar, one meaning.
- **Celebration:** keep it the loudest thing in MIA — gold card over
  a dimmed screen, one line ("New best: 40 seconds · Wall hold ·
  was 38 s"), the usual undo toast, reduced-motion respected. Loud
  visually, no added sound or vibration: celebration is the one
  place MIA is allowed to be loud (MVS × Borderlands), and it stays
  quiet everywhere else.
- **Recipe page:** stars gold when set, Stats card as built. Recipe
  cards show stars + "made N×". The Have it / On the list / To buy
  marks stay as the ingredient list's only colour besides gold.

## Guardrail (DEC-0008) — reps field on `fitness.skill`

1. MIA does not support it yet (no reps field; holds and practice
   minutes only). 2. The timer card and `fitness.skill` action exist;
   reps has nowhere to land. 3. Genuinely missing, not hidden.
4. Engine (field + action) plus UI (third mode on the one card).
5. No duplication — it extends `fitness.skill`, no new system.
6. Not Life State; it is a fitness log entry, same as holds.
7. No new life-event type — the skill log already exists (DEC-0020).
8. No new links. 9. No new `/api/state` surface; the field rides
   the existing `/api/fitness` logs. 10. REAL (logged). **Pass.**

## What's still open on my side

- A visual pass on the rendered `?demo` screens (meal card, week
  day card on a phone, protein bar, celebration) before final look
  sign-off.
- Note: `docs/HANDOFFS/README.md` does not yet list H-0029/H-0030;
  the files exist, the index is behind. (No action needed from Zac.)
