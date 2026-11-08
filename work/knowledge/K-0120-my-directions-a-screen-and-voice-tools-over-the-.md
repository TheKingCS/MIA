---
id: K-0120
kind: implementation
title: My Directions: a screen and voice tools over the direction store
status: confirmed
by: claude
created: 2026-11-08T15:37:41+00:00
concerns: core/web_directions.py, core/assistant_direction_actions.py, web/directions.js, core/capability_reminders.py
from: dec:DEC-0141, dec:DEC-0143
---
The engine session built the direction store (core/direction.py), whimsy seeds and capability reminders with no screen or tools. core/web_directions.py serves the screen (directions in force first, then paused), today's seed (whimsy.a_seed with a roll steady for the day, so the page doesn't change on every refresh) and one capability reminder, and defines direction.add/edit/pause/resume/remove. The reminder's sources moved from MIAApplication._capabilities_on_hand into capability_reminders.on_hand so the web could read them. Voice tools (core/assistant_direction_actions.py) run the same actions' describe+execute, so voice and screen are checked the same way. The life event type direction_set wasn't in life_events.TYPES; added it and direction_dropped.
