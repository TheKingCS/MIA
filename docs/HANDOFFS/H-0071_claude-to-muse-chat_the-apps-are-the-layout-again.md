# H-0071: The apps are the layout again (DEC-0045)

- From: claude
- To: muse, chat (cc zac)
- Date: 2026-10-24

## What happened

Zac, 2026-10-24: "I dont like how we tried to fix MIA from just being a
collection of apps. It was better before and I think that the old form
was better. I really just wanted to fix MIAs feel of being a smart AI
capable of using all those apps without the user digging through
everything and her being more intuitive."

So DEC-0044's frame is undone (DEC-0045):

- **Gone:** the five places (Presence · Conversation · My Hero's Path ·
  World · System), Presence as Home, the World / Path / System pages
  (`path.html`, `world.html`, `system.html`, `web/hubs.js`,
  `core/web_hubs.py`, `/api/path|world|system`) and their CSS.
- **Back:** the sidebar of the person's apps, the phone's Home + Apps
  bottom bar, Home with Today's Focus and Upcoming, exactly as before
  2026-10-21.
- **Kept:** context in every turn (`core/presence.py` `context_lines`:
  goal and why, active missions, what needs them now), Home's wins being
  real wins (no "Spent $40"), and everything MIA knows about herself
  (DEC-0041).

## For Muse

H-0068 asked for a look at "Presence and the hubs": skip that part, the
screens are gone. Freedom, Compliance, Chickens and Goods are unchanged
and still want their look. H-0070 (Freedom look pass) is next on my list.

## For Chat

The lesson for handoffs: Zac wants MIA *smarter*, not rearranged. The
layout of apps is his; a change to it is asked of him on its own, never
inside a handoff about intelligence. The work now goes into MIA working
the apps for the person in Talk and by voice: understanding what they
mean, doing it across apps, and telling them what she did.
