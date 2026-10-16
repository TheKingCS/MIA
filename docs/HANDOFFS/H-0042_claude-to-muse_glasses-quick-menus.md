# H-0042: Glasses quick action menus are in (H-0041 Phase 2), for every app
- From: claude · To: muse (cc zac) · Date: 2026-10-16
- Related: H-0041, H-0008, H-0012, DEC-0016, DEC-0023

## What Zac asked (2026-10-16)

"Work with Muse to develop quick action menus for each module to be used
for the Glasses. … boot up to the orb for MIA and then let me flip
through the app cards and then if I select one have the quick action
menu for each one."

That is your approved H-0041 plan, widened from the first four apps to
**every app that makes sense on the glasses**. I built the engine side
(your Phase 2 ask) and wired it into your carousel, so it works end to
end today. **The look is yours to polish.**

## How it works now (`web/glasses.html`)

1. **Boot:** her orb and the one thing that's next (your glance, unchanged).
2. **Swipe** (→, or a swipe on the preview): the app cards. Each card shows
   the app's name, a live status line (e.g. "4 tracked · 3 need
   attention · next: Test run (Generator)"), and "3 of 28".
3. **Select:** that app's quick action menu (2–4 items).
4. **Select an item:** a short panel, up to 5 lines plus "+ N more on
   your phone". Lines that can be acted on carry their verb (ATE IT,
   DONE, GOT IT, CLAIM); swiping moves between those only.
5. **Select a line:** MIA's own sentence ("Log breakfast: Protein oats
   (640 kcal, 44 g protein)"); **select again approves** (your
   two-gesture rule), **back cancels**. After it runs: the result, then
   back shows the panel refreshed.
6. **Back** steps out one level each time, to the orb at the end.

Ask-only apps: selecting an item hands MIA that question, as if said
aloud (`MIA.talk`), and shows her answer.

Keys in the preview: ← → ↑ ↓ move, Enter selects, Esc/Backspace goes back.
On a touchscreen: swipe left/right moves, tap selects, swipe down goes back. The demo (`?demo`) reads the new placeholder
examples; actions there say they're off in the demo.

## The menus (engine: `core/glasses.py`, `/api/glasses`, `/api/glasses/{app}/{item}`)

| App (card order) | Menu |
|---|---|
| Today | What's next (due items; DONE on upkeep) · Coming up · Recent wins |
| Missions | Today's missions (DONE on one-step ones) · Ready to claim (CLAIM) · Active missions |
| Kitchen | Today's meals (ATE IT, protein so far) · Grocery list (GOT IT) · Use soon · What can I make |
| Workout | Today's training (DONE per exercise, TRAINING DONE) · Skill practice (best vs target; PRACTICED 12 MIN) · Weight · Milestones (REACHED IT) |
| Money | This month · What's due · Debts (**readouts only**, as you asked) |
| Garage / Maintenance / Greenhouse / Property | Needs attention (DONE) · Next up |
| Rentals (Real Estate) | Properties (cash flow) · Upkeep (DONE) |
| Skills | Focus · This week |
| Character | Your story · Top skills |
| Household, Workshop, Power, Observations, People, Notes, Classroom, Inbox, Expeditions, Memories, Maps, Navigation, The Lab, Field Kit, Music, Diagnostics | 1–2 questions to MIA each (e.g. "What chores are due?", "When is sunset today?") |

Not on the glasses: Home and the Assistant (the orb *is* both), Apps,
Settings, Files. Children see only their apps; tucked-away apps don't
show.

**What the glasses may change** (`GLASSES_KINDS`): ate it, an exercise
or training done, skill practice minutes, a milestone, a mission claimed
or a one-step objective done, upkeep done (not tasks that need a meter
reading typed in), a grocery item checked, a chore/routine done, prep
done. Never a delete, never money, never anything needing a typed
number. No new action kinds were needed. Asks are always questions, so
selecting one can't accidentally make a note or start a trip.

## Yours to polish (I kept to your language and touched only what the menus needed)

- `glasses.css` v5 block: `#stage.compact` (inside an app the orb shrinks
  to a small mark at the top so five lines fit the 600×600 stage),
  `.g-menu`, `.g-rows` (text, detail, the verb at the right; the selected
  one gets a cyan inset bar), `.g-tag` (ASK), `.g-attn`, `.g-confirm`.
- The card badge is still your letter. `web/icons.js` has a line icon
  for every app if you want them here (it isn't loaded on this page yet).
- 28 cards is a lot to flip through. Ideas, your call with Zac: a
  "favorites first" order (the `app.favorite` action already exists), or
  a glasses-only pin list.

## Questions for you

1. Card order: I put Today, Missions, Kitchen, Workout, Money first (your
   four, after Today), then equipment, then the rest. Change it in
   `FIRST` (core/glasses.py) or tell me.
2. Which ask-only apps deserve real panels next? My guess: Household
   (chores due, DONE), People (next birthday), Inbox (waiting items).

Screenshots of the flow on the test data are in my session; the demo URL
shows the same thing with the placeholder person.
