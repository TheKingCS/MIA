# H-0073: Game Master and The Dungeon (DEC-0046), ready for a look

- From: claude
- To: muse, chat (cc zac)
- Date: 2026-10-27

## What Zac asked for

MIA as his Game Master for the game of life: real trouble (second shift
leaving the floor unstocked) reframed as the game, not the negative way
of thinking about it. Work as a dungeon he visits and loots every day,
stacking resources until he can advance to the next dungeon; loot
tracked with Plaid; overtime as boss battles with more loot; projected
loot from his hourly and overtime pay.

## What's built

- **Game Master mode in Talk** (`core/game_master.py`). Switched on by
  "GM this", "game master", "make it a game", or the fourth answer when
  MIA asks "just listen, figure it out, remind you why, or turn it into
  the game?". She says the trouble is real first, then frames it from
  code-built facts: the hard-mode modifier's game name, its XP, today's
  run, the week's loot, the next dungeon. "Make it a quest" makes a HARD
  mission. Other people are characters, never villains, never named.
- **The Dungeon app** (`web/dungeon.html`, MONEY group, after Freedom
  in the list order): tabs Today (clear the run with hard-mode chips,
  the overtime line, planned runs, "Did these happen?" for past planned
  runs, nothing lost), Loot (week earned / projected / boss bonus /
  take-home estimate, the month, a year at this pace, banked paychecks,
  the next dungeon = Freedom with its bar), Record (the hard-mode record
  with dates, Copy The Dates; recent runs), Setup.
- Hard-mode modifiers: Bare Shelves (unstocked), Thin Party
  (short-staffed), Cursed Room (left a mess), Supply Raid (a truck),
  Broken Gear (equipment down), Swarm (slammed), Uncharted Room
  (something new).

## For Muse

A look pass, please, when you can. Specifically:
1. The hard-mode chips on Today (`.dg-affix`, pressed = amber). Seven
   chips plus "Called-in overtime" wrap long on a phone.
2. Boss runs (`.dg-run.boss`, accent glow) vs hard-mode runs (amber
   edge): is that the right pairing in the Stark look?
3. The strip has four cells and wraps to two rows at 390 px, like
   Insurance.

The demo is in the preview (`docs/schema/dungeon.example.json`).

## For Chat

The Game Master's voice is one instruction plus a facts block. If you
have lines you'd like for the modifiers (`AFFIXES` in
`core/work_dungeon.py`: name, plain words, the framing line), send them;
the framing has to stay honest (the trouble is real) and never make a
person the villain.
