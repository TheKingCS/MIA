# MIA OS: glasses and wearables (Prompt 11 §14)

*Claude (Opus), 2026-11-17. Planning only. Built: `web/glasses.js` (DEC-0016, DEC-0153).*

## 1. What exists

A fixed 600×600 composition scaled to the display; **black is see-through**; three screens: the orb (Home), the menu
(eight destinations and their apps), the Nexus (Living Worlds); two moves do everything (move, select), every list
ends with Back; app cards with one-line status and a quick menu (`core/glasses.py`); no Passwords card (no secrets on
the display).

## 2. Rules

| Rule | Why |
|---|---|
| Black background, light ink, accent sparingly | black is transparent: the world stays visible |
| One line per fact, ≤ 6 lines a panel | short glances |
| Large type, no thin weights | legibility outdoors |
| The orb's state as a flat ring and one word | state at a glance |
| No blur, no glass, no particles | not supported and distracting |
| Notifications: one line, the source, dismissed by a move | minimal distraction |
| Nothing private by default (passwords, journal) | others can't see it but he's in public |

**Platform limits** (verify per SDK release): the Display glasses show what the phone's app or a web app sends; no
arbitrary overlays on the world, no persistent display while idle, input through the touch strip or neural band. MIA
designs within that: the glasses show cards; the phone does the work.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-019 | Glasses screens shall be black-backed with at most six lines a panel, no blur or particles, and the orb's state as a ring with one word. | Should | R1 | Glasses | Partial | T | DEC-0234 → 11, 12 |
