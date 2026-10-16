# H-0049: Calendar + recipe carousel polish (answers to H-0048)
- From: muse · To: claude (cc zac) · Date: 2026-10-16
- Related: H-0048, H-0047, H-0046, DEC-0024, DEC-0023

## What this is

Design answers to your H-0048 polish asks: the Calendar screen, the
recipe carousel and pages on the glasses. Everything Zac asked for in
H-0048 is accepted as built — Missions after the orb, the Sort row,
Kitchen order, Garage tabs, Title Case, the "a while" ask removed.
Notes below are polish only; nothing here re-opens a settled call.

## Calendar screen

**Dot palette — accepted, with two fills.** Upkeep amber, money green,
birthdays dim white, meals faint cyan, gold stays off the calendar
(gold = claim/celebration only, per H-0047). Two kinds had no color:
events = solid white (brighter than birthday dim white, so a real event
reads above a birthday), training = violet. So: Past Due red, Due Today
bright white + bold day number (not a dot color — the day itself carries
it), Due Soon no dot, just the list.

**Month grid rules.**
- Max 4 dots per day, then a "+n" micro-label. Dots ordered by urgency:
  past-due first, then money, upkeep, events, training, meals, birthdays.
- A day that is Past Due gets a thin red ring on its cell, so the grid
  reads at a glance even before tapping.
- Legend row under the grid, one line, dim: dot + word per kind, in the
  same order. No legend = nobody learns the palette.
- Tap a day → its list below the grid (or replacing it — your call),
  with Add Event at the top of that day list, pre-filled to that day.
  Add Event also lives on the Month tab header for "today".

**Tabs.** Order Past Due → Due Today → Due Soon → Month. Each tab shows
its count (Due Soon counts items, Month counts days with items — label
it so the number isn't a mystery). Empty states, one line each:
Past Due "Nothing past due — clean slate." / Due Today "Nothing due
today." / Due Soon "Nothing coming up in the next two weeks."

**Glasses card.** Past Due / Due Today / Due Soon only — no Month grid
on glass, per H-0048. Past Due items show their overdue age ("3d
overdue"), Due Soon shows the date. Select on an item goes to its home
app (bill → Money, upkeep → Garage, event → its detail) where one
exists; otherwise it opens the app Calendar screen.

## Recipe carousel and pages (glasses)

**Cover** (what select opens): photo top, Title Case title, one meta
line — time · servings · source if there is one. No photo → Kitchen
line icon stands in, same as the Kitchen cards. Keep the photo area a
fixed height so covers don't jump between recipes.

**Ingredient pages:** six per page, as built. Show a page marker
("Ingredients 1 of 2") and keep each line to one line with ellipsis —
no wrapping mid-measure. Checked-off state is out of scope until a real
cook-along ask comes; don't build it speculatively.

**Step pages:** one step per page, big step number ("Step 3 of 7"),
step text in full. Progress is the number, not a bar — bars lie about
remaining effort when steps vary in length.

**Back behavior:** select goes back, per H-0048 — confirm the chain is
step → ingredients → cover → carousel, one select per level, and the
Back row (dim, chevron, per H-0047) is present on every page. From the
cover, Back returns to the carousel at the same recipe, not the top.

**Kitchen order on glass — accepted:** Recipes, Today's Meal Plan,
My Pantry, Grocery List.
- Pantry: soonest-to-expire first, as built. Expiry color: expired =
  red, today/tomorrow = amber, else dim. "Expires in 2d" reads better
  than a bare date.
- Grocery List: select toggles checked; checked items dim with a
  strikethrough and sink to the bottom of the list. Unchecking brings
  them back up.

## Missions Sort row — one note

All → Past Due → Due Today → Due Soon with counts, select cycles it —
accepted. Sort within each filter: Past Due oldest first (the thing
most overdue is the thing to see first), Due Today and Due Soon by date
ascending. Done stays on due items, Show stays on missions — no change.

## Title Case — one caution, already handled

`text-transform: capitalize` only uppercases first letters and leaves
the rest as typed, so acronyms (MIA, DIY) survive it. Item text stays as
typed, mono spaced-capitals labels unchanged — both confirmed, no
action.

## Guardrail (DEC-0008)

Calendar, recipes, Sort row and tabs are engine-built (H-0048) and
exposed via `/api/calendar` and the existing stores — this handoff is
UI-only: dot colors, grid rules, page markers, back chains, expiry
colors. Nothing duplicates an existing system, nothing new enters Life
State, no new life events or links, no `/api/state` change. Status:
REAL (built) + polish.

## Acceptance

- Calendar month grid follows the dot palette + 4-dot cap + legend +
  red ring for past-due days; tabs carry counts and the empty-state
  lines above.
- Recipe cover / ingredient / step pages follow the layout above;
  Back chain is step → ingredients → cover → carousel at the same
  recipe.
- Pantry expiry colors and Grocery List checked behavior as above.
- Missions filters sort oldest-first for Past Due, date-ascending
  otherwise.
