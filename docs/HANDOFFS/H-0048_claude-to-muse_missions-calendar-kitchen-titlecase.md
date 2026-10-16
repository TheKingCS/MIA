# H-0048: Missions after the orb, sorted due lists, a real Calendar, recipe photos, Title Case
- From: claude · To: muse (cc zac) · Date: 2026-10-16
- Related: H-0046, H-0047, DEC-0024, DEC-0023

## Zac's asks (2026-10-16), all built

1. **Missions comes right after the orb**, before any pin. The Today card
   is gone from the glasses: what it showed (past due, due today, due
   soon) now lives in Missions → **Select Mission**, with a **Sort** row
   on top (All → Past Due → Due Today → Due Soon; select cycles it, with
   counts). Due items keep their Done; missions keep Show.
2. **Calendar, filled, in the app and on the glasses.** `web/calendar.html`
   (`core/calendar_view.py`, `/api/calendar`): your events (with repeats),
   upkeep, bills and pay, planned meals and prep, training days and
   birthdays, read live from their own stores. Tabs Past Due, Due Today,
   Due Soon (next two weeks by day) and Month (a grid with a dot per kind;
   tap a day for its list and Add Event). The Calendar shortcut on Home
   and the Dashboard opens it (it used to ask MIA, who only knew typed-in
   events). Glasses card: Past Due, Due Today, Due Soon. New actions:
   `event.add`, `event.delete`.
3. **Kitchen on the glasses:** Recipes first (one recipe per screen with
   its photo; select opens a cover, ingredient pages of six and one step
   per page; select goes back), then **Today's Meal Plan**, **My Pantry**
   (soonest to expire first), **Grocery List**.
4. **Recipe photos:** Add Photo / Change Photo on each recipe page (camera
   or gallery on a phone); shown on the recipe page, the Kitchen cards and
   the glasses. Without one, the Kitchen line icon stands in.
5. **Garage (and Maintenance, Greenhouse, Property, Rentals):** Assets,
   Past Due, Due Today, Due Soon.
6. **Title Case** for buttons, tabs and headers everywhere (CSS
   `text-transform: capitalize` in concept.css and glasses.css; the mono
   spaced-capitals labels are unchanged). Item text (a task, a recipe's
   ingredients) stays as typed.

## Your H-0047 notes

All done: the Saturn band's near half dims, her answer is two lines, Back
is dim with a chevron, the pin row has the ★, the Missions card shows 3 +
"n more" past four objectives, status lines are one line with an
ellipsis. **"A while":** there's no rule for it in Life State, so the
"Who haven't I talked to in a while?" ask is removed rather than left to
free text. People keeps Next Birthdays.

Yours to polish: the Calendar screen (month grid dot colors: upkeep amber,
money green, birthdays dim white, meals faint cyan; gold stays off it),
the recipe carousel and pages on the glasses.
