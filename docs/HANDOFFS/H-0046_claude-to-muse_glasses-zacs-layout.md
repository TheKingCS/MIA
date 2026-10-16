# H-0046: The glasses, re-laid out to Zac's direction (orb alone, two moves, no scrolling)
- From: claude · To: muse (cc zac) · Date: 2026-10-16
- Related: H-0041, H-0042, H-0043, H-0045, DEC-0016, DEC-0024

## What Zac said (2026-10-16, with two phone screenshots)

"The first tab should just be the orb. No text bar, no one thing that's
next, just an animation when it's idle and a kind of similar animation
when it hears Hey MIA and starts listening … rings around it like
Saturn when it's listening. … the apps just show a single letter … I
can't see the words. The missions tab should show the active mission
and its objectives and maybe a Select Mission button that brings up the
mission list. I don't want to have to scroll down on any of these
screens. It needs to fit into the screen and be navigable with an action
that either moves to another screen or makes a selection." And: "remove
the chat bar on all screens too."

On his phone the 600×600 stage had been squeezed to the phone's width
with the orb zone fixed at 224 px, so the card was cut off under the
letter, and the XP bar, dots and demo voice bar crowded it.

## What changed (`web/glasses.html`, `glasses.css`, `glasses.js`)

- **One fixed 600×600 composition, scaled to the screen** (`--fit`), so
  it can't scroll or clip on any device. Type is glance-sized (app name
  54 px, status 25 px, rows 25 px).
- **Home is her orb alone.** No card, XP bar, dots, or chat bar (the demo
  voice console is gone everywhere). Idle: breathing plus the slow arcs.
  **Listening: Saturn rings**, a fixed tilted band with light travelling
  round it, the far half behind her and the near half in front.
  Thinking spins the band faster. Her answer shows under her for a few
  seconds, then she's alone again.
- **Two moves do everything.** Move (swipe, arrows, Neural Band scroll)
  and select (tap, Enter, pinch). Every list ends with a **Back** row;
  the orb sits between the last card and the first. Esc and swipe down
  stay as back shortcuts. Lists show a window of five rows that follows
  the selection (▲/▼ counts), never a scroll.
- **App cards:** the line icon large in its frame, the name, the status
  line, "2 / 6".
- **Missions card:** the mission shown, its objectives (✓ when done, n/N
  on tallies), a progress bar and a **Select mission** button. Select
  opens the menu with **Select mission** first (the full list; pick one
  and the card shows it, remembered on that device), then **Log
  progress** (Done / +1 per objective, Claim when ready), Today's
  missions, Ready to claim, Unpin.
- **Confirm** is a two-row choice, Approve (selected) or Cancel, so it's
  still two selects to change anything.
- Voice: select on the orb records (where the browser allows a mic) and
  sends it to MIA (`MIA.voice`). The real "Hey MIA" wake word comes with
  the phone companion (Phase 3), which will call `MIAGlasses.listen()`.
  The demo shows the listening animation and says talking needs MIA
  running.

Engine: `mission_focus()`, the `pick` and `progress` panels, `?mission=`
on `/api/glasses` and `/api/glasses/{app}/{item}` (core/glasses.py).

Yours to polish within those constraints (no scroll, two moves, orb alone).

## Follow-up (same day): Zac had to zoom out, and the orb screen was hard to leave

- The page can't zoom any more (`user-scalable=no`, `touch-action: none`);
  quick taps on the orb had been zooming it in. `--fit` reads the
  visual viewport.
- Taps and swipes are decided once per gesture (pointer events). Before,
  the tap after a swipe was swallowed.
- Faint ‹ › arrows at the stage's edges (tap to move) for touchscreens;
  the glasses use the Band's scroll. Moving while she listens cancels the
  listening instead of locking navigation.
