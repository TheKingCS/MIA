---
id: K-0217
kind: debugging
title: A download cut short by a closing page looked like a pause on the next page
status: confirmed
by: claude
created: 2026-11-11T00:07:21+00:00
concerns: web/player.js, web/shell.js
from: file:web/player.js
---
In a plain browser the song didn't carry on after opening Home. Home's address redirects to the Nexus, so the first page lived for a moment: it began fetching the song, the browser closed it, the fetch failed, and the failure handler recorded 'not playing' for the tab. The next page read that and woke up paused. The fix in web/player.js keeps two things apart: `wanted` (what the person means, kept for the next page, changed only by Pause, Stop, or a browser refusing sound) and `stalled` (this page couldn't get the song; never kept). Found with a headless-browser check that plays a real tone and reads the player's state on each page, not by reading the code: the unit tests all passed while it was broken. Worth remembering for any state a page keeps for its successor: a page being closed fails its requests, and that failure must not be written down as the person's choice.
