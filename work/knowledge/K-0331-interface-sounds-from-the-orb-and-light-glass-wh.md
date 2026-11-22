---
id: K-0331
kind: implementation
title: Interface sounds from the orb, and light glass while a model generates
status: confirmed
by: claude
created: 2026-11-22T14:12:32+00:00
concerns: web/sound.js, web/shell.js
from: task:WP-06, dec:DEC-0240
---
WP-06 (DEC-0240, REQ-VIS-023/026/012). web/sound.js presence(state) plays a cue only on a real change of the orb's state: listening -> listenOn, leaving listening -> listenOff, needs-you -> needsYou, warning -> error; done and message are made but off (Q-84, OFF_BY_DEFAULT). They go through play(), so sound.on turns them off; nothing names an alarm. The visual twin is the orb's labelled state (WP-07). web/shell.js showPresence calls it, and generating(thinking or council) drops auto effects to light (kept in data-effects-before) and holds the ambient drift. The Light theme waits on Q-115: DEC-0136 forbids a theme to change the meaning colours, which are too light for a light field.
